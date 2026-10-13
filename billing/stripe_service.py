import os
import uuid
from typing import Dict, List, Optional
import stripe
from models.schema import CreditPackage, CheckoutResponse
from .ledger import BillingLedger

# Available Ultra-Accessible Credit Packages for NexusLeadEngine
PACKAGES: Dict[str, CreditPackage] = {
    "pack_micro_25": CreditPackage(
        package_id="pack_micro_25",
        name="Pack Micro (25 Leads Calificados)",
        credits=25,
        price_usd=15.0,
        unit_price_usd=0.60,
        description="Precio de impulso para probar en 30 segundos. Sin fricción ni preguntas."
    ),
    "pack_micro_15": CreditPackage(
        package_id="pack_micro_15",
        name="Pack Micro (25 Leads Calificados)",
        credits=25,
        price_usd=15.0,
        unit_price_usd=0.60,
        description="Precio de impulso para probar en 30 segundos. Sin fricción ni preguntas."
    ),
    "pack_starter_60": CreditPackage(
        package_id="pack_starter_60",
        name="Pack Starter (60 Leads Calificados)",
        credits=60,
        price_usd=29.0,
        unit_price_usd=0.48,
        description="Ideal para automatizaciones de prospección semanal en Make o n8n."
    ),
    "pack_pro_200": CreditPackage(
        package_id="pack_pro_200",
        name="Pack Pro (200 Leads Calificados)",
        credits=200,
        price_usd=69.0,
        unit_price_usd=0.34,
        description="Flujo constante para bots y agencias activas. El preferido por volumen."
    ),
    "pack_scale_600": CreditPackage(
        package_id="pack_scale_600",
        name="Pack Scale (600 Leads Calificados)",
        credits=600,
        price_usd=149.0,
        unit_price_usd=0.24,
        description="Máximo volumen a solo $0.24 por lead calificado de alto ticket."
    )
}

PAYPAL_ME_BASE = "https://www.paypal.com/paypalme/NexusLeadEngine"
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "https://nexusleadengine.io").rstrip("/")


class PaymentsNotConfigured(Exception):
    """Raised when live Stripe credentials are missing."""


class StripeService:
    """Manages Stripe Checkout Sessions and verified, idempotent payment fulfillment."""

    def __init__(self, ledger: BillingLedger):
        self.ledger = ledger
        self.api_key = os.getenv("STRIPE_SECRET_KEY")
        self.webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

        if self.api_key:
            stripe.api_key = self.api_key

    @property
    def live_enabled(self) -> bool:
        return bool(self.api_key) and not self.api_key.startswith("mock_")

    def get_packages(self) -> List[CreditPackage]:
        return list(PACKAGES.values())

    def create_checkout_session(
        self,
        client_id: str,
        package_id: str,
        success_url: Optional[str] = None,
        cancel_url: Optional[str] = None,
        customer_email: Optional[str] = None,
    ) -> CheckoutResponse:
        package = PACKAGES.get(package_id)
        if not package:
            raise ValueError(f"Paquete no válido: {package_id}. Opciones: {list(PACKAGES.keys())}")

        if not self.live_enabled:
            raise PaymentsNotConfigured("Los pagos con tarjeta no están configurados todavía.")

        success_url = success_url or f"{PUBLIC_BASE_URL}/billing/success"
        cancel_url = cancel_url or f"{PUBLIC_BASE_URL}/billing/cancel"

        # Ensure account exists in ledger
        if not self.ledger.get_by_client_id(client_id):
            self.ledger.create_account(client_id)

        params = dict(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "unit_amount": int(round(package.price_usd * 100)),
                    "product_data": {
                        "name": package.name,
                        "description": package.description,
                    },
                },
                "quantity": 1,
            }],
            mode="payment",
            client_reference_id=client_id,
            metadata={"client_id": client_id, "package_id": package.package_id},
            success_url=f"{success_url}?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=cancel_url,
        )
        if customer_email:
            params["customer_email"] = customer_email

        session = stripe.checkout.Session.create(**params)
        return CheckoutResponse(
            checkout_url=session.url,
            session_id=session.id,
            credits_to_add=package.credits,
            price_usd=package.price_usd,
            mode="stripe_live",
        )

    def fulfill_session(self, session: dict) -> dict:
        """
        Credits an account for a PAID Checkout Session. Idempotent per session id:
        the webhook and the success page can both call this safely.
        """
        if hasattr(session, "to_dict"):
            session = session.to_dict()
        session_id = session.get("id")
        if not session_id:
            return {"status": "IGNORED", "reason": "missing_session_id"}
        if session.get("payment_status") != "paid":
            return {"status": "PENDING", "session_id": session_id}

        metadata = session.get("metadata") or {}
        client_id = metadata.get("client_id") or session.get("client_reference_id")
        package = PACKAGES.get(metadata.get("package_id", ""))
        if not client_id or not package:
            return {"status": "IGNORED", "reason": "invalid_metadata", "session_id": session_id}

        if self.ledger.is_session_processed(session_id):
            account = self.ledger.get_by_client_id(client_id)
            return {
                "status": "ALREADY_PROCESSED",
                "session_id": session_id,
                "client_id": client_id,
                "credits_added": 0,
                "new_balance": account.credits_balance if account else 0,
            }

        # Mark first, credit second: a crash can never double-credit.
        self.ledger.mark_session_processed(session_id)
        account = self.ledger.add_credits(client_id, package.credits)
        return {
            "status": "PROCESSED",
            "session_id": session_id,
            "client_id": client_id,
            "package_id": package.package_id,
            "credits_added": package.credits,
            "price_usd": package.price_usd,
            "customer_email": (session.get("customer_details") or {}).get("email")
                              or session.get("customer_email"),
            "new_balance": account.credits_balance,
        }

    def retrieve_and_fulfill(self, session_id: str) -> dict:
        """Used by the success page: asks Stripe directly (never trusts the browser)."""
        if not self.live_enabled:
            raise PaymentsNotConfigured("Los pagos con tarjeta no están configurados todavía.")
        session = stripe.checkout.Session.retrieve(session_id)
        return self.fulfill_session(session.to_dict() if hasattr(session, "to_dict") else dict(session))

    def handle_webhook_event(self, raw_body: bytes, signature: Optional[str] = None) -> dict:
        """
        Ingests Stripe webhook events. The signature is ALWAYS verified against
        STRIPE_WEBHOOK_SECRET; unsigned events are rejected.
        """
        if not self.webhook_secret:
            raise PermissionError("STRIPE_WEBHOOK_SECRET no configurado: webhook deshabilitado.")
        if not signature:
            raise PermissionError("Falta la cabecera Stripe-Signature.")
        try:
            event = stripe.Webhook.construct_event(raw_body, signature, self.webhook_secret)
        except Exception as e:  # invalid payload or signature
            raise PermissionError(f"Firma de Stripe inválida: {e}")

        event_type = event["type"]
        if event_type in ("checkout.session.completed", "checkout.session.async_payment_succeeded"):
            return self.fulfill_session(event["data"]["object"])
        return {"status": "IGNORED", "event_type": event_type}
