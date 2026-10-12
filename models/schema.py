from __future__ import annotations
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import uuid
import time

class LeadScoreTier(str, Enum):
    ULTRA_HIGH = "ULTRA_HIGH"  # Score 85-100: Top budget, high-ticket, immediate conversion opportunity
    HIGH = "HIGH"              # Score 70-84: High-ticket, clear technological gap
    MEDIUM = "MEDIUM"          # Score 50-69: Potential but lower urgency
    DISQUALIFIED = "DISQUALIFIED"  # Score < 50: Low ticket or no contact channel

class ChannelType(str, Enum):
    WHATSAPP = "WHATSAPP"
    COLD_EMAIL = "COLD_EMAIL"
    PHONE = "PHONE"
    API_AUTO_BOOK = "API_AUTO_BOOK"

class ProspectRaw(BaseModel):
    """Raw business data retrieved from scrapers/directories/maps"""
    name: str
    category: str
    city: str
    country: str = "ES"
    website: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    rating: Optional[float] = None
    reviews_count: Optional[int] = None
    claimed: Optional[bool] = True

class TechSignal(BaseModel):
    """Signals detected by visiting the prospect's digital footprint"""
    has_ssl: bool = False
    has_meta_pixel: bool = False
    has_google_tag: bool = False
    has_whatsapp_widget: bool = False
    has_contact_form: bool = False
    is_mobile_friendly: bool = True
    page_load_seconds: float = 0.0
    detected_cms: Optional[str] = None
    social_profiles: List[str] = Field(default_factory=list)

class BotActionPayload(BaseModel):
    """The machine payload: exact intelligence for the client's automated bot"""
    recommended_channel: ChannelType
    estimated_ticket_value_usd: int = Field(description="Estimated deal size for this client")
    pain_points: List[str]
    loss_hypothesis: str = Field(description="Estimated revenue lost by client due to missing automations")
    pre_drafted_outreach_hook: str = Field(description="Personalized icebreaker text ready for bot sending")
    service_pitch_angle: str = Field(description="The exact solution angle to present")

class EnrichedLead(BaseModel):
    """The final product delivered M2M (Machine to Machine)"""
    lead_id: str = Field(default_factory=lambda: f"lead_{uuid.uuid4().hex[:10]}")
    timestamp_utc: int = Field(default_factory=lambda: int(time.time()))
    score: int = Field(ge=0, le=100, description="Overall Lead Quality Score")
    tier: LeadScoreTier
    business_name: str
    category: str
    location: Dict[str, str]
    contact_channels: Dict[str, Optional[str]]
    tech_signals: TechSignal
    bot_action: BotActionPayload
    raw_metadata: Dict[str, Any] = Field(default_factory=dict)

class WebhookSubscription(BaseModel):
    """Client bot registers its endpoint to receive live lead streaming"""
    client_id: str
    endpoint_url: str
    secret_key: str
    target_niches: List[str] = Field(default_factory=lambda: ["*"])
    min_score_threshold: int = 70
    is_active: bool = True

class CreditPackage(BaseModel):
    package_id: str
    name: str
    credits: int
    price_usd: float
    unit_price_usd: float
    description: str

class ApiKeyAccount(BaseModel):
    api_key: str
    client_id: str
    credits_balance: int = 0
    total_consumed: int = 0
    total_purchased: int = 0
    created_at_utc: int = Field(default_factory=lambda: int(time.time()))
    stripe_customer_id: Optional[str] = None

class CreateCheckoutRequest(BaseModel):
    client_id: str
    package_id: str = "pack_starter_50"
    success_url: Optional[str] = "https://tu-dominio.com/billing/success"
    cancel_url: Optional[str] = "https://tu-dominio.com/billing/cancel"

class CheckoutResponse(BaseModel):
    checkout_url: str
    session_id: str
    credits_to_add: int
    price_usd: float
    mode: str = "stripe_live"  # or "simulation"

class CreditBalanceResponse(BaseModel):
    client_id: str
    api_key_masked: str
    credits_balance: int
    total_consumed: int
    total_purchased: int
    status: str

class TopupDevRequest(BaseModel):
    client_id: str
    credits_to_add: int = 50

class PayPalActivationRequest(BaseModel):
    client_id: str = Field(description="Nombre o ID del bot/cliente que usará la API")
    payer_email: str = Field(description="Correo con el que realizaste el pago en PayPal")
    package_id: str = Field(default="pack_micro_15", description="ID del paquete adquirido")
    transaction_id: Optional[str] = Field(default=None, description="ID o comprobante de transacción de PayPal")


class ScanRequest(BaseModel):
    """Parameters to trigger an autonomous prospecting run"""
    niche: str = Field(example="implantes dentales", description="Target industry or high-ticket service")
    location: str = Field(example="Madrid", description="City or region")
    max_leads: int = Field(default=5, ge=1, le=50)
    min_score: int = Field(default=60, ge=0, le=100)
    auto_dispatch_webhooks: bool = Field(default=True)

