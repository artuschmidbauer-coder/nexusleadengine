from fastapi import FastAPI, HTTPException, status, Header, Request
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
from billing.stripe_service import StripeService, PACKAGES
from billing.guard import get_or_create_account, deduct_credit_for_delivery
from analytics.tracker import AnalyticsTracker

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

@app.get("/v1/analytics/dashboard", tags=["Telemetry"])
def get_analytics_metrics():
    """Returns live throughput, conversion rates, revenues and activity feed."""
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

@app.post("/v1/billing/create-checkout", response_model=CheckoutResponse, tags=["Billing"])
def create_checkout_session(req: CreateCheckoutRequest):
    """
    Generates an automated Stripe Checkout Session link.
    When paid, Stripe webhooks will automatically credit the account 24/7.
    """
    try:
        return stripe_service.create_checkout_session(
            client_id=req.client_id,
            package_id=req.package_id,
            success_url=req.success_url or "https://tu-dominio.com/billing/success",
            cancel_url=req.cancel_url or "https://tu-dominio.com/billing/cancel"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/v1/billing/stripe-webhook", tags=["Billing"])
async def process_stripe_webhook(request: Request):
    """
    Autonomous Stripe Webhook Receiver.
    Fires when a client completes a payment and adds credits to their API account instantly.
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    result = stripe_service.handle_webhook_event(body)
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

@app.post("/v1/billing/paypal-activate", tags=["Billing"])
def activate_paypal_purchase(req: PayPalActivationRequest):
    """
    Activación Inmediata de Créditos tras pago en PayPal.me/NexusLeadEngine:
    El cliente o bot envía los datos de pago y recibe su API Key activa con los créditos acreditados al instante.
    """
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

@app.post("/v1/billing/topup-dev", tags=["Billing"])
def topup_development_credits(req: TopupDevRequest):
    """Testing/Dev helper: Add instant credits to a client without going through Stripe."""
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

    prospects = finder.search(req.niche, req.location, limit=req.max_leads)
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
def get_sample_lead():
    """Generates an instant sample high-ticket lead to preview payload structure."""
    prospects = finder.search("implantes dentales", "Madrid", limit=1)
    if not prospects:
        raise HTTPException(status_code=404, detail="No prospect found")

    tech = auditor.audit(prospects[0].website)
    return qualifier.qualify(prospects[0], tech)

@app.get("/v1/dispatch/logs", tags=["M2M Delivery"])
def get_delivery_logs():
    return {"deliveries": dispatcher.get_logs()}
