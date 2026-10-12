import os
import uuid
from typing import Dict, List, Optional
import stripe
from models.schema import CreditPackage, CheckoutResponse
from .ledger import BillingLedger

# Available Ultra-Accessible Credit Packages for NexusLeadEngine
PACKAGES: Dict[str, CreditPackage] = {
    "pack_micro_15": CreditPackage(
        package_id="pack_micro_15",
        name="Pack Micro (15 Leads Calificados)",
        credits=15,
        price_usd=9.0,
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

class StripeService:
    """Manages Stripe Checkout Sessions and autonomous webhook payment fulfillment."""

    def __init__(self, ledger: BillingLedger):
        self.ledger = ledger
        self.api_key = os.getenv("STRIPE_SECRET_KEY")
        self.webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

        if self.api_key:
            stripe.api_key = self.api_key

    def get_packages(self) -> List[CreditPackage]:
        return list(PACKAGES.values())

    def create_checkout_session(
        self,
        client_id: str,
        package_id: str,
        success_url: str = "https://tu-dominio.com/billing/success",
        cancel_url: str = "https://tu-dominio.com/billing/cancel"
    ) -> CheckoutResponse:
        package = PACKAGES.get(package_id)
        if not package:
            raise ValueError(f"Paquete no válido: {package_id}. Opciones: {list(PACKAGES.keys())}")

        # Ensure account exists in ledger
        account = self.ledger.get_by_client_id(client_id)
        if not account:
            account = self.ledger.create_account(client_id)

        # 1. Real Stripe Integration if API key is present
        if self.api_key and not self.api_key.startswith("mock_"):
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[{
                    "price_data": {
                        "currency": "usd",
                        "unit_amount": int(package.price_usd * 100),
                        "product_data": {
                            "name": package.name,
                            "description": package.description,
                        },
                    },
                    "quantity": 1,
                }],
                mode="payment",
                client_reference_id=client_id,
                metadata={
                    "client_id": client_id,
                    "package_id": package.package_id,
                    "credits": str(package.credits)
                },
                success_url=f"{success_url}?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=cancel_url,
            )
            return CheckoutResponse(
                checkout_url=session.url,
                session_id=session.id,
                credits_to_add=package.credits,
                price_usd=package.price_usd,
                mode="stripe_live"
            )

        # 2. Seamless PayPal.me & Local Sandbox Mode (Instant Checkout Link for testing)
        # Direct PayPal payment link formatted as https://www.paypal.com/paypalme/NexusLeadEngine/{amount}USD
        paypal_direct_url = f"{PAYPAL_ME_BASE}/{int(package.price_usd)}USD"

        return CheckoutResponse(
            checkout_url=paypal_direct_url,
            session_id=f"pp_session_{uuid.uuid4().hex[:12]}",
            credits_to_add=package.credits,
            price_usd=package.price_usd,
            mode="paypal_me"
        )

    def handle_webhook_event(self, payload: dict, signature: Optional[str] = None) -> dict:
        """
        Ingests Stripe Webhook events and credits accounts automatically.
        Triggered when 'checkout.session.completed' fires.
        """
        event_type = payload.get("type")
        data_object = payload.get("data", {}).get("object", {})

        if event_type == "checkout.session.completed":
            metadata = data_object.get("metadata", {})
            client_id = metadata.get("client_id") or data_object.get("client_reference_id")
            credits = int(metadata.get("credits", 0))

            if client_id and credits > 0:
                updated_account = self.ledger.add_credits(client_id, credits)
                return {
                    "status": "PROCESSED",
                    "client_id": client_id,
                    "credits_added": credits,
                    "new_balance": updated_account.credits_balance
                }

        return {"status": "IGNORED", "event_type": event_type}
