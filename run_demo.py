#!/usr/bin/env python3
"""
LeadStream M2M Engine - Live End-to-End Demonstration
Simulates:
1. Client Bot registering a Webhook endpoint
2. Autonomous Scanner searching high-ticket targets
3. AI Evaluation & Tech Signal Extraction
4. JSON Payload Generation (Machine-to-Machine format)
5. Delivery dispatch
"""

import json
import sys
import os

# Ensure package root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.schema import ScanRequest, WebhookSubscription
from collectors.business_finder import BusinessFinder
from analyzers.web_auditor import WebAuditor
from analyzers.ai_qualifier import AIQualifier
from dispatchers.webhook_sender import WebhookDispatcher

def print_banner(text: str):
    print("\n" + "=" * 70)
    print(f"  ⚡ {text}")
    print("=" * 70)

def main():
    print_banner("INICIANDO MOTOR AUTÓNOMO DE LEADS M2M (AGENT-TO-AGENT)")

    finder = BusinessFinder()
    auditor = WebAuditor()
    qualifier = AIQualifier()
    dispatcher = WebhookDispatcher()

    # Step 1: Simulate a client bot subscribing
    print("\n[PASO 1] 🤖 Un bot externo (Make.com / GoHighLevel / WhatsApp AI) se suscribe:")
    mock_sub = WebhookSubscription(
        client_id="agencia_dental_bot_01",
        endpoint_url="https://api.crm-del-cliente.com/webhooks/inbound-leads",
        secret_key="secret_token_secure_987",
        target_niches=["*"],
        min_score_threshold=70
    )
    dispatcher.register_subscriber(mock_sub)
    print(f"  -> Bot registrado con éxito: {mock_sub.client_id}")
    print(f"  -> Webhook de destino: {mock_sub.endpoint_url}")
    print(f"  -> Umbral de calidad mínimo: {mock_sub.min_score_threshold}/100")

    # Step 2: Autonomous discovery & scoring
    print("\n[PASO 2] 🛰️ Escaneo automático de oportunidades de Ticket Alto:")
    niche = "implantes dentales"
    location = "Madrid"
    print(f"  -> Nicho objetivo: {niche.upper()}")
    print(f"  -> Ubicación: {location}")

    prospects = finder.search(niche, location, limit=2)
    print(f"  -> Encontrados {len(prospects)} prospectos base para auditar.\n")

    for idx, prospect in enumerate(prospects, start=1):
        print("-" * 70)
        print(f"🏢 [{idx}] Analizando: {prospect.name}")
        print(f"    Web: {prospect.website} | Tel: {prospect.phone}")
        print(f"    Reputación: {prospect.rating} ⭐ ({prospect.reviews_count} opiniones)")

        # Step 3: Web Tech Audit
        tech_signal = auditor.audit(prospect.website)
        print("    [Auditoría Técnica]")
        print(f"      • SSL Seguro: {'✅' if tech_signal.has_ssl else '❌'}")
        print(f"      • Meta Pixel Instalado: {'✅' if tech_signal.has_meta_pixel else '❌ (Oportunidad)'}")
        print(f"      • Botón WhatsApp Directo: {'✅' if tech_signal.has_whatsapp_widget else '❌ (Punto de dolor)'}")

        # Step 4: AI Qualification & Payload Creation
        enriched = qualifier.qualify(prospect, tech_signal)
        print(f"\n    [Calificación IA]")
        print(f"      • Score de Calidad: {enriched.score}/100 ({enriched.tier.value})")
        print(f"      • Ticket Estimado: ${enriched.bot_action.estimated_ticket_value_usd:,.0f} USD")
        print(f"      • Canal sugerido: {enriched.bot_action.recommended_channel.value}")
        print(f"      • Diagnóstico de pérdida: {enriched.bot_action.loss_hypothesis}")

        print("\n    [Mensaje Hiper-Personalizado para el Bot del Cliente]:")
        print(f'      "{enriched.bot_action.pre_drafted_outreach_hook}"')

        # Step 5: Machine-to-Machine Delivery
        delivery = dispatcher.dispatch(enriched)
        print(f"\n    [Entrega M2M]")
        for d in delivery:
            print(f"      -> Despachado a {d['client_id']} (Firma HMAC-SHA256 validada)")

    print_banner("PAYLOAD JSON REAL ENTREGADO AL BOT (ESTRUCTURA DE MÁQUINA)")
    # Show the clean JSON output of the first enriched lead
    sample_json = json.loads(enriched.model_dump_json())
    print(json.dumps(sample_json, indent=2, ensure_ascii=False))

    print("\n" + "=" * 70)
    print("  ✅ Demostración completada. El pipeline corre sin intervención humana.")
    print("=" * 70)

if __name__ == "__main__":
    main()
