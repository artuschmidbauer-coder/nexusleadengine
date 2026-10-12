from typing import Tuple, List
from models.schema import (
    ProspectRaw,
    TechSignal,
    EnrichedLead,
    LeadScoreTier,
    BotActionPayload,
    ChannelType,
)

# High-ticket benchmarks
HIGH_TICKET_BENCHMARKS = {
    "dental": {"ticket_usd": 1800, "weight": 35, "label": "Implantes / Odontología de Alta Gama"},
    "implante": {"ticket_usd": 2200, "weight": 35, "label": "Implantología / Cirugía Maxilofacial"},
    "estetica": {"ticket_usd": 1200, "weight": 32, "label": "Medicina Estética / Cirugía Plástica"},
    "reforma": {"ticket_usd": 5500, "weight": 35, "label": "Reformas Integrales / Construcción"},
    "solar": {"ticket_usd": 6000, "weight": 35, "label": "Energía Solar / Paneles"},
    "climatizacion": {"ticket_usd": 2500, "weight": 30, "label": "Climatización / HVAC"},
    "abogado": {"ticket_usd": 1500, "weight": 30, "label": "Servicios Legales / Derecho Corporativo"},
    "asesoria": {"ticket_usd": 1000, "weight": 28, "label": "Asesoría Fiscal / Contable B2B"},
}

DEFAULT_BENCHMARK = {"ticket_usd": 800, "weight": 20, "label": "Servicios Generales"}

class AIQualifier:
    """Evaluates business viability and generates actionable machine intelligence."""

    def qualify(self, prospect: ProspectRaw, tech: TechSignal) -> EnrichedLead:
        score = 0
        pain_points: List[str] = []

        # 1. High ticket evaluation
        cat_lower = f"{prospect.category} {prospect.name}".lower()
        benchmark = DEFAULT_BENCHMARK
        for keyword, data in HIGH_TICKET_BENCHMARKS.items():
            if keyword in cat_lower:
                benchmark = data
                break

        score += benchmark["weight"]

        # 2. Contactability
        has_phone = bool(prospect.phone)
        has_email = bool(prospect.email)
        has_web = bool(prospect.website)

        if has_phone:
            score += 20
        if has_email or has_web:
            score += 10

        # 3. Social proof / Existing customers
        rating = prospect.rating or 4.0
        reviews = prospect.reviews_count or 0

        if reviews >= 20 and rating >= 4.2:
            score += 15
        elif reviews >= 5 and rating >= 4.0:
            score += 10
        elif reviews > 0:
            score += 5

        # 4. Marketing Gap / Pain Points (Golden opportunity for marketing bots)
        if not tech.has_whatsapp_widget:
            pain_points.append("Falta de botón directo o bot de WhatsApp (fuga estimada del 30% del tráfico móvil)")
            score += 10  # High opportunity to sell them lead-capture bots

        if not tech.has_meta_pixel:
            pain_points.append("No tiene Meta Pixel activo (no hacen retargeting a visitantes interesados)")
            score += 5

        if not tech.has_google_tag:
            pain_points.append("Sin medición avanzada de analítica/Google Tag")

        if tech.page_load_seconds > 2.5:
            pain_points.append(f"Web con carga lenta ({tech.page_load_seconds}s), riesgo de rebote alto")

        if not pain_points:
            pain_points.append("Presencia digital establecida; potencial para aceleración de pauta y automatización de citas")

        # Clamp score between 0 and 100
        final_score = min(100, max(0, score))

        # Assign Tier
        if final_score >= 80:
            tier = LeadScoreTier.ULTRA_HIGH
        elif final_score >= 65:
            tier = LeadScoreTier.HIGH
        elif final_score >= 45:
            tier = LeadScoreTier.MEDIUM
        else:
            tier = LeadScoreTier.DISQUALIFIED

        # Determine best channel
        best_channel = ChannelType.WHATSAPP if has_phone else (ChannelType.COLD_EMAIL if has_email else ChannelType.PHONE)

        # Detect locale from country
        is_english = (prospect.country or "US").upper() in ("US", "GB", "CA", "AU", "UK")

        # Generate pre-drafted personalized hook for their bot
        hook = self._generate_bot_hook(prospect, tech, benchmark, pain_points, is_english=is_english)

        # Estimated financial loss
        estimated_ticket = benchmark["ticket_usd"]
        if is_english:
            loss_hypothesis = (
                f"Lacking instant mobile conversion triggers causes an estimated leak of "
                f"3 to 6 high-ticket clients monthly (approx. ${estimated_ticket * 3:,.0f} - ${estimated_ticket * 6:,.0f} USD)."
            )
            pitch_angle = f"Deploy automated lead capture & instant booking workflow for {prospect.category}"
        else:
            loss_hypothesis = (
                f"Al no tener captura rápida por WhatsApp ni retargeting, pierden un estimado de "
                f"3 a 6 cotizaciones mensuales (aprox. ${estimated_ticket * 3:,.0f} - ${estimated_ticket * 6:,.0f} USD)."
            )
            pitch_angle = f"Implementar embudo de captación automatizada y atención en WhatsApp para {prospect.category}"

        bot_action = BotActionPayload(
            recommended_channel=best_channel,
            estimated_ticket_value_usd=estimated_ticket,
            pain_points=pain_points,
            loss_hypothesis=loss_hypothesis,
            pre_drafted_outreach_hook=hook,
            service_pitch_angle=pitch_angle
        )

        return EnrichedLead(
            score=final_score,
            tier=tier,
            business_name=prospect.name,
            category=prospect.category,
            location={"city": prospect.city, "country": prospect.country, "address": prospect.address or ""},
            contact_channels={
                "whatsapp": prospect.phone,
                "phone": prospect.phone,
                "email": prospect.email,
                "website": prospect.website
            },
            tech_signals=tech,
            bot_action=bot_action,
            raw_metadata={"benchmark_applied": benchmark["label"], "reviews_count": reviews, "rating": rating}
        )

    def _generate_bot_hook(self, p: ProspectRaw, t: TechSignal, b: dict, pain_points: List[str], is_english: bool = False) -> str:
        """Generates a hyper-personalized icebreaker formatted for the client's automated bot"""
        if is_english:
            reviews_mention = f"with strong reviews ({p.reviews_count} ratings)" if (p.reviews_count and p.reviews_count > 10) else ""
            if not t.has_whatsapp_widget:
                return (
                    f"Hi {p.name} team, I was reviewing your website {reviews_mention}. "
                    f"Noticed prospective clients searching for {p.category} in {p.city} cannot initiate an instant consultation from mobile. "
                    f"Over 65% of high-intent patients bounce to competitors if not engaged within 5 minutes. "
                    f"Would you be open to seeing a 60-second preview of how our automated booking widget captures these leads?"
                )
            else:
                return (
                    f"Hi {p.name} team, love what you've built in {p.city} for {p.category}. "
                    f"We run automated website diagnostics for local businesses and noticed strong organic search intent in your area. "
                    f"Does your team have capacity to handle 10-15 qualified high-ticket consultations this month?"
                )

        reviews_mention = f"con excelentes reseñas ({p.reviews_count} opiniones)" if (p.reviews_count and p.reviews_count > 10) else ""
        if not t.has_whatsapp_widget:
            return (
                f"Hola equipo de {p.name}, estuve revisando su sitio web {reviews_mention}. "
                f"Noté que reciben visitas interesadas en sus servicios de {p.category}, pero no tienen un botón o bot directo "
                f"de WhatsApp para responder al instante. Muchos pacientes/clientes que buscan presupuestos se van a la competencia si no reciben respuesta en menos de 5 minutos. "
                f"¿Tienen 2 minutos para ver cómo conectarles un sistema que agenda automáticamente?"
            )
        else:
            return (
                f"Hola equipo de {p.name}, veo que tienen una sólida reputación en {p.city} para {p.category}. "
                f"Estamos entregando un flujo de prospectos calificados que buscan activamente cotizaciones de ticket alto en su zona. "
                f"¿Su equipo comercial tendría capacidad para recibir entre 10 y 15 contactos calificados adicionales esta semana?"
            )
