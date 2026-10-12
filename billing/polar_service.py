import os
import hmac
import base64
import hashlib
import json
import uuid
import requests
from typing import Dict, List, Optional
from models.schema import CreditPackage, CheckoutResponse
from .ledger import BillingLedger

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

PACKAGES: Dict[str, CreditPackage] = {
    "pack_micro_15": CreditPackage(
        package_id="pack_micro_15",
        name="Pack Micro (15 Qualified Diagnostics)",
        credits=15,
        price_usd=9.0,
        unit_price_usd=0.60,
        description="Ideal for fast testing in Make or n8n. Instant activation."
    ),
    "pack_starter_60": CreditPackage(
        package_id="pack_starter_60",
        name="Pack Starter (60 Qualified Diagnostics)",
        credits=60,
        price_usd=29.0,
        unit_price_usd=0.48,
        description="Weekly prospecting and audit flow for digital agencies."
    ),
    "pack_pro_200": CreditPackage(
        package_id="pack_pro_200",
        name="Pack Pro (200 Qualified Diagnostics)",
        credits=200,
        price_usd=69.0,
        unit_price_usd=0.34,
        description="Steady high-ticket audit flow for active agency outbound."
    ),
    "pack_scale_600": CreditPackage(
        package_id="pack_scale_600",
        name="Pack Scale (600 Qualified Diagnostics)",
        credits=600,
        price_usd=149.0,
        unit_price_usd=0.24,
        description="Maximum volume at $0.24 per verified diagnostic."
    )
}

PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "https://nexusleadengine.io").rstrip("/")

class PolarService:
    """
    Manages Polar.sh Checkout Sessions and webhook payment fulfillment (Merchant of Record).
    Supports both Sandbox (testing) and Production.
    """

    def __init__(self, ledger: BillingLedger):
        self.ledger = ledger
        self.access_token = os.getenv("POLAR_ACCESS_TOKEN")
        self.webhook_secret = os.getenv("POLAR_WEBHOOK_SECRET")
        self.is_sandbox = os.getenv("POLAR_ENVIRONMENT", "production").lower() == "sandbox"
        
        self.api_base = "https://sandbox-api.polar.sh/v1" if self.is_sandbox else "https://api.polar.sh/v1"
        
        # Product IDs created in Polar Dashboard (one per pack)
        self.product_id_map: Dict[str, str] = {
            "pack_micro_15": os.getenv("POLAR_PRODUCT_MICRO_15", ""),
            "pack_starter_60": os.getenv("POLAR_PRODUCT_STARTER_60", ""),
            "pack_pro_200": os.getenv("POLAR_PRODUCT_PRO_200", ""),
            "pack_scale_600": os.getenv("POLAR_PRODUCT_SCALE_600", ""),
        }

    @property
    def is_configured(self) -> bool:
        return bool(self.access_token)

    def get_packages(self) -> List[CreditPackage]:
        return list(PACKAGES.values())

    def create_checkout_session(
        self,
        client_id: str,
        package_id: str,
        customer_email: Optional[str] = None,
        success_url: Optional[str] = None
    ) -> CheckoutResponse:
        package = PACKAGES.get(package_id)
        if not package:
            raise ValueError(f"Invalid package: {package_id}. Valid: {list(PACKAGES.keys())}")

        if not self.is_configured:
            raise RuntimeError("POLAR_ACCESS_TOKEN not configured. Payments temporarily unavailable.")

        success_url = success_url or f"{PUBLIC_BASE_URL}/billing/success?session_id={{CHECKOUT_ID}}"

        if not self.ledger.get_by_client_id(client_id):
            self.ledger.create_account(client_id)

        polar_product_id = self.product_id_map.get(package_id)
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        payload = {
            "success_url": success_url,
            "metadata": {
                "client_id": client_id,
                "package_id": package.package_id
            }
        }
        if customer_email:
            payload["customer_email"] = customer_email

        if polar_product_id:
            payload["product_id"] = polar_product_id
        else:
            payload["products"] = [polar_product_id] if polar_product_id else []

        resp = requests.post(f"{self.api_base}/checkouts/custom/", json=payload, headers=headers, timeout=10)
        if resp.status_code not in (200, 201):
            raise RuntimeError(f"Error communicating with Polar API ({resp.status_code}): {resp.text}")

        data = resp.json()
        checkout_url = data.get("url")
        session_id = data.get("id")

        return CheckoutResponse(
            checkout_url=checkout_url,
            session_id=session_id,
            credits_to_add=package.credits,
            price_usd=package.price_usd,
            mode="polar_live" if not self.is_sandbox else "polar_sandbox"
        )

    def verify_webhook_signature(self, raw_body: bytes, headers: dict) -> bool:
        """
        Validates Polar Standard Webhook signature (webhook-id, webhook-timestamp, webhook-signature).
        """
        if not self.webhook_secret:
            raise PermissionError("POLAR_WEBHOOK_SECRET not configured.")

        webhook_id = headers.get("webhook-id") or headers.get("Webhook-Id")
        webhook_timestamp = headers.get("webhook-timestamp") or headers.get("Webhook-Timestamp")
        webhook_signature = headers.get("webhook-signature") or headers.get("Webhook-Signature")

        if not (webhook_id and webhook_timestamp and webhook_signature):
            raise PermissionError("Missing required Polar webhook headers.")

        to_sign = f"{webhook_id}.{webhook_timestamp}.".encode("utf-8") + raw_body
        
        # Secret can be prefixed with whsec_
        secret_clean = self.webhook_secret
        if secret_clean.startswith("whsec_"):
            secret_clean = secret_clean[6:]

        try:
            secret_bytes = base64.b64decode(secret_clean)
        except Exception:
            secret_bytes = self.webhook_secret.encode("utf-8")

        expected_sig = base64.b64encode(hmac.new(secret_bytes, to_sign, hashlib.sha256).digest()).decode("utf-8")

        # Signatures in header can be formatted as v1,signature
        signatures_given = [s.replace("v1,", "").strip() for s in webhook_signature.split()]
        if any(hmac.compare_digest(expected_sig, sig) for sig in signatures_given):
            return True

        raise PermissionError("Invalid Polar webhook signature.")

    def fulfill_order(self, order_data: dict) -> dict:
        """
        Credits account for a paid order or completed checkout. Idempotent.
        """
        order_id = order_data.get("id")
        if not order_id:
            return {"status": "IGNORED", "reason": "missing_id"}

        metadata = order_data.get("metadata") or order_data.get("checkout", {}).get("metadata") or {}
        client_id = metadata.get("client_id")
        package_id = metadata.get("package_id")

        if not client_id or not package_id or package_id not in PACKAGES:
            # Check by product id if metadata is absent
            product_id = order_data.get("product_id")
            for pkg_id, pid in self.product_id_map.items():
                if pid and pid == product_id:
                    package_id = pkg_id
                    break

        package = PACKAGES.get(package_id or "")
        if not client_id or not package:
            return {"status": "IGNORED", "reason": "unknown_client_or_package", "order_id": order_id}

        if self.ledger.is_session_processed(order_id):
            account = self.ledger.get_by_client_id(client_id)
            return {
                "status": "ALREADY_PROCESSED",
                "order_id": order_id,
                "client_id": client_id,
                "credits_added": 0,
                "new_balance": account.credits_balance if account else 0
            }

        self.ledger.mark_session_processed(order_id)
        account = self.ledger.add_credits(client_id, package.credits)
        return {
            "status": "PROCESSED",
            "order_id": order_id,
            "client_id": client_id,
            "package_id": package.package_id,
            "credits_added": package.credits,
            "price_usd": package.price_usd,
            "customer_email": order_data.get("customer_email") or order_data.get("user", {}).get("email"),
            "new_balance": account.credits_balance
        }

    def retrieve_and_fulfill(self, session_id: str) -> dict:
        """
        Retrieves a custom checkout session from Polar API.
        If status is confirmed/succeeded, fulfills the order and returns status info.
        If still open, returns PENDING.
        """
        if not self.is_configured:
            raise RuntimeError("Polar is not configured.")

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json"
        }
        resp = requests.get(f"{self.api_base}/checkouts/custom/{session_id}", headers=headers, timeout=10)
        if resp.status_code == 404:
            raise ValueError(f"Polar checkout session {session_id} not found.")
        if resp.status_code not in (200, 201):
            raise RuntimeError(f"Error querying Polar API: {resp.text}")

        data = resp.json()
        checkout_status = data.get("status")

        if checkout_status in ("open", "incomplete"):
            return {"status": "PENDING", "session_id": session_id}

        if checkout_status in ("confirmed", "succeeded", "paid"):
            return self.fulfill_order(data)

        return {"status": "FAILED", "checkout_status": checkout_status}
