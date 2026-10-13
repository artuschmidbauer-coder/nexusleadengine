import hmac
import os
import uuid
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from fastapi import FastAPI, HTTPException, status, Header, Request
from pydantic import BaseModel, EmailStr
from typing import List, Dict, Any, Optional
from models.schema import (
    ScanRequest,
    EnrichedLead,
    WebhookSubscription,
    CreditPackage,
    CreateCheckoutRequest,
    CheckoutResponse,
    CreditBalanceResponse,
    TopupDevRequest,
    PayPalActivationRequest,
)
from collectors.business_finder import BusinessFinder
from analyzers.web_auditor import WebAuditor
from analyzers.ai_qualifier import AIQualifier
from dispatchers.webhook_sender import WebhookDispatcher
from billing.ledger import BillingLedger
from billing.stripe_service import StripeService, PACKAGES, PaymentsNotConfigured
from billing.polar_service import PolarService
from billing.nowpayments_service import NowPaymentsService
from billing.guard import get_or_create_account, deduct_credit_for_delivery
from analytics.tracker import AnalyticsTracker


def require_admin(token: Optional[str]) -> None:
    """Blocks admin endpoints unless ADMIN_TOKEN is set and matches (constant-time compare)."""
    expected = os.getenv("ADMIN_TOKEN")
    if not expected or not token or not hmac.compare_digest(token, expected):
        raise HTTPException(status_code=403, detail="Acceso restringido.")

app = FastAPI(
    title="NexusLeadEngine.io - M2M Lead Intelligence API",
    description="Motor Autónomo de Inteligencia y Comercialización de Leads B2B para Agentes de IA, Bots y CRMs. Contacto: hola@nexusleadengine.io",
    version="2.0.0"
)

from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import os

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")

# Core singletons
finder = BusinessFinder(use_live_search=False)
auditor = WebAuditor(timeout=3)
qualifier = AIQualifier()
dispatcher = WebhookDispatcher()
ledger = BillingLedger()
stripe_service = StripeService(ledger)
polar_service = PolarService(ledger)
nowpayments_service = NowPaymentsService(ledger)
tracker = AnalyticsTracker()

# In-memory store for recent generated leads
processed_leads: List[EnrichedLead] = []

@app.get("/", include_in_schema=False)
def serve_landing_page(request: Request):
    """Serves the modern SaaS Landing Page and records visitor telemetry."""
    client_ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown").split(",")[0].strip()
    tracker.record_visit(ip_hash=client_ip, path="/")
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "NexusLeadEngine API is running. Visit /docs for Swagger UI."}

@app.get("/dashboard", include_in_schema=False)
def serve_telemetry_dashboard(request: Request):
    """Serves the Real-Time Telemetry and Measurement Dashboard."""
    client_ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown").split(",")[0].strip()
    tracker.record_visit(ip_hash=client_ip, path="/dashboard")
    dashboard_file = os.path.join(STATIC_DIR, "dashboard.html")
    if os.path.exists(dashboard_file):
        return FileResponse(dashboard_file)
    return {"message": "Dashboard file not found."}

@app.get("/billing/success", include_in_schema=False)
def serve_billing_success():
    """Post-payment page: shows the API key once Stripe confirms the payment."""
    return FileResponse(os.path.join(STATIC_DIR, "success.html"))

@app.get("/billing/cancel", include_in_schema=False)
def billing_cancel():
    """Checkout cancelled: send the visitor back to the pricing section."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/#pricing")

@app.get("/templates/n8n", include_in_schema=False)
def download_n8n_template():
    """Download the ready-to-import n8n lead automation workflow."""
    template_path = os.path.join(STATIC_DIR, "templates", "nexus_n8n_lead_workflow.json")
    if os.path.exists(template_path):
        return FileResponse(template_path, media_type="application/json", filename="nexus_n8n_lead_workflow.json")
    raise HTTPException(status_code=404, detail="Template not found")

@app.get("/v1/analytics/dashboard", tags=["Telemetry"])
def get_analytics_metrics(
    x_admin_token: Optional[str] = Header(None),
    token: Optional[str] = None
):
    """Returns live throughput, conversion rates, revenues and activity feed (Admin Only)."""
    require_admin(x_admin_token or token)
    return tracker.get_dashboard_metrics(active_accounts_count=len(ledger._accounts))

@app.get("/v1/status")
def root_api_status():
    return {
        "service": "LeadStream M2M Engine & Automated Billing",
        "status": "online",
        "description": "Autonomous lead intelligence pipeline for AI bots, CRMs, and webhooks with automated billing",
        "endpoints": {
            "landing_page": "GET /",
            "billing_packages": "GET /v1/billing/packages",
            "create_checkout": "POST /v1/billing/create-checkout",
            "stripe_webhook": "POST /v1/billing/stripe-webhook",
            "check_balance": "GET /v1/billing/balance",
            "subscribe_bot": "POST /v1/webhooks/subscribe",
            "trigger_scan": "POST /v1/leads/trigger-scan",
            "sample_lead": "GET /v1/leads/sample",
            "delivery_logs": "GET /v1/dispatch/logs",
            "docs": "/docs"
        }
    }

# -------------------------------------------------------------
# BILLING ENDPOINTS (STRIPE & AUTOMATED METERED USAGE)
# -------------------------------------------------------------

@app.get("/v1/billing/packages", response_model=List[CreditPackage], tags=["Billing"])
def get_credit_packages():
    """Returns available prepaid credit packs for bots and clients."""
    return stripe_service.get_packages()

class BuyRequest(BaseModel):
    package_id: str
    email: EmailStr
    api_key: Optional[str] = None  # present when an existing customer tops up
    payment_method: Optional[str] = "crypto"  # "crypto" (NOWPayments / Binance) or "card" (Polar / Stripe)


@app.post("/v1/billing/buy", tags=["Billing"])
def buy_credits(req: BuyRequest):
    """
    Starts a Checkout for a credit pack.
    - Default: NOWPayments (USDT / Binance / Crypto + Card)
    - Fallback: Polar or Stripe
    """
    if req.package_id not in PACKAGES:
        raise HTTPException(status_code=400, detail=f"Paquete inválido. Opciones: {list(PACKAGES.keys())}")

    client_id: Optional[str] = None
    if req.api_key:
        existing = ledger.get_by_api_key(req.api_key)
        if not existing:
            raise HTTPException(status_code=401, detail="API key inválida.")
        client_id = existing.client_id
    else:
        client_id = f"cli_{uuid.uuid4().hex[:12]}"

    try:
        if req.payment_method == "card" and polar_service.is_configured:
            checkout = polar_service.create_checkout_session(
                client_id=client_id,
                package_id=req.package_id,
                customer_email=str(req.email)
            )
        elif nowpayments_service.is_configured:
            checkout = nowpayments_service.create_invoice(
                client_id=client_id,
                package_id=req.package_id,
                customer_email=str(req.email)
            )
        elif polar_service.is_configured:
            checkout = polar_service.create_checkout_session(
                client_id=client_id,
                package_id=req.package_id,
                customer_email=str(req.email)
            )
        else:
            checkout = stripe_service.create_checkout_session(
                client_id=client_id,
                package_id=req.package_id,
                customer_email=str(req.email),
            )
    except (PaymentsNotConfigured, RuntimeError, ValueError) as e:
        raise HTTPException(
            status_code=503,
            detail={"error": "PAYMENTS_UNAVAILABLE", "message": str(e), "contact": "hola@nexusleadengine.io"},
        )
    return checkout


class AgentBuyRequest(BaseModel):
    package_id: str = "pack_micro_25"
    pay_currency: str = "usdttrc20"  # usdttrc20, usdtbsc, btc, eth, sol, trx, ltc
    email: Optional[EmailStr] = None
    api_key: Optional[str] = None  # if top-up of existing key


@app.post("/v1/billing/agent-buy", tags=["Agentic Commerce / M2M"])
def agent_buy_credits(req: AgentBuyRequest):
    """
    Autonomous Machine-to-Machine (M2M) Checkout for AI Agents, Bots and Smart Wallets.
    Returns exact crypto deposit address, amount and network instructions for direct on-chain signing.
    No browser or human interaction required.
    """
    if req.package_id not in PACKAGES:
        raise HTTPException(status_code=400, detail=f"Paquete inválido. Opciones: {list(PACKAGES.keys())}")

    if not nowpayments_service.is_configured:
        raise HTTPException(status_code=503, detail="NOWPayments M2M Crypto gateway not configured.")

    client_id: Optional[str] = None
    if req.api_key:
        existing = ledger.get_by_api_key(req.api_key)
        if not existing:
            raise HTTPException(status_code=401, detail="API key inválida.")
        client_id = existing.client_id
    else:
        client_id = f"cli_agent_{uuid.uuid4().hex[:10]}"

    try:
        return nowpayments_service.create_direct_payment(
            client_id=client_id,
            package_id=req.package_id,
            pay_currency=req.pay_currency,
            customer_email=str(req.email) if req.email else None
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error initializing M2M payment: {str(e)}")


@app.get("/v1/billing/session/{session_id}", tags=["Billing"])
def get_checkout_result(session_id: str):
    """
    Called by the success page. Asks NOWPayments, Polar, or Stripe whether the session was paid
    (never trusts the browser), credits it once, and returns the API key.
    """
    try:
        if session_id.startswith("np_"):
            result = nowpayments_service.retrieve_and_fulfill(session_id)
        elif polar_service.is_configured and not session_id.startswith("cs_"):
            result = polar_service.retrieve_and_fulfill(session_id)
        else:
            result = stripe_service.retrieve_and_fulfill(session_id)
    except (PaymentsNotConfigured, RuntimeError, ValueError) as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception:
        raise HTTPException(status_code=404, detail="Sesión de pago no encontrada.")

    if result["status"] == "PENDING":
        return {"status": "PENDING", "message": "El pago aún no se ha confirmado."}
    if result["status"] not in ("PROCESSED", "ALREADY_PROCESSED", "PAID"):
        raise HTTPException(status_code=400, detail="Sesión de pago inválida.")

    account = ledger.get_by_client_id(result["client_id"])
    if result["status"] == "PROCESSED":
        tracker.record_revenue(result["price_usd"], result.get("customer_email") or "nowpayments_binance", result["credits_added"])

    return {
        "status": "PAID",
        "credits_added": result.get("credits_added", 0),
        "new_balance": account.credits_balance if account else 0,
        "api_key": account.api_key if account else "",
    }


@app.post("/v1/billing/stripe-webhook", tags=["Billing"])
async def process_stripe_webhook(request: Request, stripe_signature: Optional[str] = Header(None)):
    """
    Stripe webhook receiver. The Stripe-Signature header is verified against
    STRIPE_WEBHOOK_SECRET; unsigned or forged events are rejected with 400.
    """
    raw_body = await request.body()
    try:
        result = stripe_service.handle_webhook_event(raw_body, stripe_signature)
    except PermissionError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if result.get("status") == "PROCESSED":
        tracker.record_revenue(result["price_usd"], result.get("customer_email") or "stripe", result["credits_added"])
    return result


@app.post("/v1/billing/polar-webhook", tags=["Billing"])
async def process_polar_webhook(request: Request):
    """
    Polar.sh Standard Webhook Receiver.
    Fires on order.created / checkout.updated to automatically credit customer accounts.
    """
    raw_body = await request.body()
    headers = dict(request.headers)
    try:
        polar_service.verify_webhook_signature(raw_body, headers)
    except PermissionError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        import json
        payload = json.loads(raw_body.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_type = payload.get("type")
    if event_type in ("order.created", "checkout.updated"):
        order_data = payload.get("data", {})
        result = polar_service.fulfill_order(order_data)
        if result.get("status") == "PROCESSED":
            tracker.record_revenue(result["price_usd"], result.get("customer_email") or "polar", result["credits_added"])
        return result

    return {"status": "IGNORED", "event_type": event_type}


@app.post("/v1/billing/nowpayments-webhook", tags=["Billing"])
async def process_nowpayments_webhook(
    request: Request,
    x_nowpayments_sig: Optional[str] = Header(None)
):
    """
    NOWPayments Instant Payment Notification (IPN) Receiver.
    Fires on payment state change (finished/confirmed) to automatically credit customer account in Binance USDT.
    """
    raw_body = await request.body()
    try:
        nowpayments_service.verify_ipn_signature(raw_body, x_nowpayments_sig)
    except PermissionError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        import json
        payload = json.loads(raw_body.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    result = nowpayments_service.fulfill_payment(payload)
    if result.get("status") == "PROCESSED":
        tracker.record_revenue(
            result["price_usd"],
            payload.get("customer_email") or "nowpayments_crypto",
            result["credits_added"]
        )
    return result

@app.get("/v1/billing/balance", response_model=CreditBalanceResponse, tags=["Billing"])
def check_balance(
    client_id: Optional[str] = "demo_client",
    x_api_key: Optional[str] = Header(None)
):
    """Check credit balance, total leads consumed, and account status."""
    acc = get_or_create_account(ledger, api_key=x_api_key, client_id=client_id)
    if not acc:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")

    masked_key = f"{acc.api_key[:10]}...{acc.api_key[-4:]}"
    status_str = "ACTIVE" if acc.credits_balance > 0 else "EXHAUSTED"

    return CreditBalanceResponse(
        client_id=acc.client_id,
        api_key_masked=masked_key,
        credits_balance=acc.credits_balance,
        total_consumed=acc.total_consumed,
        total_purchased=acc.total_purchased,
        status=status_str
    )

@app.post("/v1/billing/paypal-activate", tags=["Billing (admin)"])
def activate_paypal_purchase(req: PayPalActivationRequest, x_admin_token: Optional[str] = Header(None)):
    """
    ADMIN ONLY. Manual credit activation after the owner has confirmed a PayPal payment
    in their own PayPal account. Requires the X-Admin-Token header (env ADMIN_TOKEN).
    """
    require_admin(x_admin_token)

    package = PACKAGES.get(req.package_id)
    if not package:
        raise HTTPException(
            status_code=400,
            detail=f"Paquete inválido: {req.package_id}. Opciones: {list(PACKAGES.keys())}"
        )

    # Automatically credit or create account
    account = ledger.get_by_client_id(req.client_id)
    if not account:
        account = ledger.create_account(req.client_id)

    updated_account = ledger.add_credits(req.client_id, package.credits)

    # Record in Analytics Tracker
    tracker.record_revenue(package.price_usd, req.payer_email, package.credits)

    return {
        "status": "ACTIVATED",
        "message": f"¡Pago registrado exitosamente! Se han acreditado +{package.credits} créditos.",
        "client_id": updated_account.client_id,
        "payer_email": req.payer_email,
        "package_name": package.name,
        "credits_added": package.credits,
        "new_balance": updated_account.credits_balance,
        "api_key": updated_account.api_key,
        "next_steps": {
            "subscribe_webhook": "POST /v1/webhooks/subscribe (con tu API Key)",
            "docs": "/docs",
            "support": "hola@nexusleadengine.io"
        }
    }

@app.post("/v1/billing/topup-dev", tags=["Billing (admin)"])
def topup_development_credits(req: TopupDevRequest, x_admin_token: Optional[str] = Header(None)):
    """ADMIN ONLY. Add credits to a client manually. Requires the X-Admin-Token header."""
    require_admin(x_admin_token)
    updated = ledger.add_credits(req.client_id, req.credits_to_add)
    return {
        "status": "TOPUP_SUCCESSFUL",
        "client_id": updated.client_id,
        "new_balance": updated.credits_balance,
        "api_key": updated.api_key
    }

# -------------------------------------------------------------
# CORE LEAD INTELLIGENCE & M2M DELIVERY
# -------------------------------------------------------------

@app.post("/v1/webhooks/subscribe", status_code=status.HTTP_201_CREATED, tags=["M2M Delivery"])
def subscribe_webhook(sub: WebhookSubscription):
    """Allows client bots (Make, n8n, GoHighLevel, Zapier) to subscribe their webhook."""
    dispatcher.register_subscriber(sub)
    return {
        "status": "subscribed",
        "client_id": sub.client_id,
        "endpoint_url": sub.endpoint_url,
        "min_score_threshold": sub.min_score_threshold,
        "message": "Bot successfully registered. Will receive real-time M2M JSON payloads."
    }

@app.get("/v1/webhooks/subscribers", tags=["M2M Delivery"])
def get_subscribers():
    return {"active_subscribers": dispatcher.list_subscribers()}

@app.post("/v1/leads/trigger-scan", response_model=List[EnrichedLead], tags=["Lead Engine"])
def trigger_scan(
    req: ScanRequest,
    x_api_key: Optional[str] = Header(None)
):
    """
    Full Autonomous Pipeline with Metered Credit Deduction:
    1. Authenticates client and validates credit balance.
    2. Discovers prospects in target high-ticket sector.
    3. Runs technical audit & AI scoring.
    4. Deducts 1 credit per qualified lead delivered.
    5. Dispatches M2M payloads to subscribed bots.
    """
    account = get_or_create_account(ledger, api_key=x_api_key, client_id="demo_client")

    prospects = finder.search(req.niche, req.location, limit=req.max_leads, country=req.country_code)
    tracker.record_scan_event(req.niche, req.location, len(prospects))
    new_leads: List[EnrichedLead] = []

    for prospect in prospects:
        # Check credit balance before processing
        if account.credits_balance <= 0:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "error": "INSUFFICIENT_CREDITS",
                    "message": f"Te has quedado sin créditos ({account.credits_balance} restantes). Recarga para continuar.",
                    "reload_url": "POST /v1/billing/create-checkout",
                    "client_id": account.client_id
                }
            )

        tech_signal = auditor.audit(prospect.website)
        enriched = qualifier.qualify(prospect, tech_signal)

        if enriched.score >= req.min_score:
            # Deduct 1 credit for the verified high-ticket lead
            deduct_credit_for_delivery(ledger, account.api_key, leads_count=1)

            # Record in Telemetry
            tracker.record_qualified_lead(enriched)

            new_leads.append(enriched)
            processed_leads.append(enriched)

            # Auto-deliver to subscribed bots
            if req.auto_dispatch_webhooks:
                dispatcher.dispatch(enriched)

    return new_leads

@app.get("/v1/leads/sample", response_model=EnrichedLead, tags=["Lead Engine"])
def get_sample_lead(country_code: Optional[str] = "US"):
    """Generates an instant sample high-ticket lead to preview payload structure."""
    cc = (country_code or "US").upper()
    if cc == "GB":
        niche, city = "dental implants", "London"
    elif cc == "ES":
        niche, city = "implantes dentales", "Madrid"
    else:
        niche, city = "dental implants", "Miami"
        cc = "US"

    prospects = finder.search(niche, city, limit=1, country=cc)
    if not prospects:
        prospects = finder.search("dental implants", "Miami", limit=1, country="US")
    if not prospects:
        raise HTTPException(status_code=404, detail="No prospect found")

    tech = auditor.audit(prospects[0].website)
    return qualifier.qualify(prospects[0], tech)

@app.get("/v1/dispatch/logs", tags=["M2M Delivery"])
def get_delivery_logs():
    return {"deliveries": dispatcher.get_logs()}
