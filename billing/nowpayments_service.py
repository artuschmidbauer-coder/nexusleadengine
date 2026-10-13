import os
import hmac
import hashlib
import json
import uuid
from typing import Dict, List, Optional
import requests
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
        name="Pack Micro (15 Web Diagnostics)",
        credits=15,
        price_usd=9.0,
        unit_price_usd=0.60,
        description="Ideal for fast testing in Make or n8n. Instant activation."
    ),
    "pack_starter_60": CreditPackage(
        package_id="pack_starter_60",
        name="Pack Starter (60 Web Diagnostics)",
        credits=60,
        price_usd=29.0,
        unit_price_usd=0.48,
        description="Weekly prospecting and audit flow for digital agencies."
    ),
    "pack_pro_200": CreditPackage(
        package_id="pack_pro_200",
        name="Pack Pro (200 Web Diagnostics)",
        credits=200,
        price_usd=69.0,
        unit_price_usd=0.34,
        description="Steady high-ticket audit flow for active agency outbound."
    ),
    "pack_scale_600": CreditPackage(
        package_id="pack_scale_600",
        name="Pack Scale (600 Web Diagnostics)",
        credits=600,
        price_usd=149.0,
        unit_price_usd=0.24,
        description="Maximum volume at $0.24 per verified diagnostic."
    )
}

PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "https://nexusleadengine.io").rstrip("/")

class NowPaymentsService:
    """
    Manages NOWPayments Crypto & Binance payments (USDT, USDC, BTC, Cards).
    Settles directly into the user's Binance account.
    """

    def __init__(self, ledger: BillingLedger):
        self.ledger = ledger
        self.api_key = os.getenv("NOWPAYMENTS_API_KEY")
        self.ipn_secret = os.getenv("NOWPAYMENTS_IPN_SECRET")
        self.api_base = "https://api.nowpayments.io/v1"

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    def get_packages(self) -> List[CreditPackage]:
        return list(PACKAGES.values())

    def create_invoice(
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
            raise RuntimeError("NOWPAYMENTS_API_KEY not configured. Crypto payments unavailable.")

        if not self.ledger.get_by_client_id(client_id):
            self.ledger.create_account(client_id)

        # Unique order id encoding client_id and package_id unambiguously
        unique_order_id = f"np__{client_id}__{package_id}__{uuid.uuid4().hex[:8]}"
        callback_url = f"{PUBLIC_BASE_URL}/v1/billing/nowpayments-webhook"
        redirect_success = success_url or f"{PUBLIC_BASE_URL}/billing/success?session_id={unique_order_id}"

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }

        payload = {
            "price_amount": package.price_usd,
            "price_currency": "usd",
            "order_id": unique_order_id,
            "order_description": f"{package.name} - NexusLeadEngine",
            "ipn_callback_url": callback_url,
            "success_url": redirect_success,
            "cancel_url": f"{PUBLIC_BASE_URL}/#pricing"
        }
        if customer_email:
            payload["customer_email"] = customer_email

        resp = requests.post(f"{self.api_base}/invoice", json=payload, headers=headers, timeout=10)
        if resp.status_code not in (200, 201):
            raise RuntimeError(f"Error communicating with NOWPayments API ({resp.status_code}): {resp.text}")

        data = resp.json()
        invoice_url = data.get("invoice_url")

        return CheckoutResponse(
            checkout_url=invoice_url,
            session_id=unique_order_id,
            credits_to_add=package.credits,
            price_usd=package.price_usd,
            mode="nowpayments_binance"
        )

    def verify_ipn_signature(self, raw_body: bytes, received_sig: Optional[str]) -> bool:
        """
        Verifies NOWPayments HMAC-SHA512 signature against the IPN secret key.
        NOWPayments canonical format: sorted keys with compact json serialization.
        """
        if not self.ipn_secret:
            raise PermissionError("NOWPAYMENTS_IPN_SECRET not configured.")

        if not received_sig:
            raise PermissionError("Missing x-nowpayments-sig header.")

        try:
            body_dict = json.loads(raw_body.decode("utf-8"))
        except Exception:
            raise PermissionError("Invalid JSON in IPN body.")

        def sort_dict(item):
            if isinstance(item, dict):
                return {k: sort_dict(v) for k, v in sorted(item.items())}
            if isinstance(item, list):
                return [sort_dict(i) for i in item]
            return item

        sorted_body = sort_dict(body_dict)
        serialized = json.dumps(sorted_body, separators=(',', ':'), sort_keys=True)
        expected_sig = hmac.new(
            self.ipn_secret.encode("utf-8"),
            serialized.encode("utf-8"),
            hashlib.sha512
        ).hexdigest()

        if hmac.compare_digest(expected_sig, received_sig.strip()):
            return True

        raise PermissionError("Invalid NOWPayments IPN signature.")

    def fulfill_payment(self, ipn_data: dict) -> dict:
        """
        Fulfills customer credit balance when payment is finished or confirmed. Idempotent.
        """
        order_id = ipn_data.get("order_id")
        payment_id = ipn_data.get("payment_id") or ipn_data.get("id") or order_id
        payment_status = str(ipn_data.get("payment_status", "")).lower()

        # NOWPayments successful states: finished, confirmed, sending
        if payment_status not in ("finished", "confirmed", "sending"):
            return {
                "status": "PENDING" if payment_status in ("waiting", "confirming") else "IGNORED",
                "payment_status": payment_status,
                "order_id": order_id
            }

        # Parse client_id and package_id from order_id: np__{client_id}__{package_id}__{rand}
        client_id = None
        package_id = None
        if order_id and order_id.startswith("np__"):
            parts = order_id.split("__")
            if len(parts) >= 3:
                client_id = parts[1]
                package_id = parts[2]
        elif order_id and order_id.startswith("np_"):
            for pkg_key in PACKAGES.keys():
                if pkg_key in order_id:
                    package_id = pkg_key
                    break
            parts = order_id.split("_")
            client_id = parts[1] if len(parts) > 1 else None

        package = PACKAGES.get(package_id or "")
        if not client_id or not package:
            return {"status": "IGNORED", "reason": "unknown_client_or_package", "order_id": order_id}

        dedup_id = f"np_{payment_id}"
        if self.ledger.is_session_processed(dedup_id):
            account = self.ledger.get_by_client_id(client_id)
            return {
                "status": "ALREADY_PROCESSED",
                "order_id": order_id,
                "client_id": client_id,
                "credits_added": 0,
                "new_balance": account.credits_balance if account else 0
            }

        self.ledger.mark_session_processed(dedup_id)
        account = self.ledger.add_credits(client_id, package.credits)
        return {
            "status": "PROCESSED",
            "order_id": order_id,
            "client_id": client_id,
            "package_id": package.package_id,
            "credits_added": package.credits,
            "price_usd": package.price_usd,
            "pay_currency": ipn_data.get("pay_currency", "usdt"),
            "new_balance": account.credits_balance
        }

    def retrieve_and_fulfill(self, session_id: str) -> dict:
        """
        Polls payment status for a session. If already processed, returns confirmed.
        """
        if not session_id.startswith("np_"):
            return {"status": "PENDING"}

        parts = session_id.split("_")
        client_id = f"{parts[1]}_{parts[2]}" if len(parts) >= 3 and parts[1] == "cli" else (parts[1] if len(parts) >= 2 else None)
        account = self.ledger.get_by_client_id(client_id) if client_id else None

        if any(self.ledger.is_session_processed(f"np_{k}") for k in [session_id]):
            return {
                "status": "PAID",
                "client_id": client_id,
                "new_balance": account.credits_balance if account else 0,
                "api_key": account.api_key if account else ""
            }

        return {"status": "PENDING"}
