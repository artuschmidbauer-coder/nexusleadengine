import csv
import json
import os
import sys

# Ensure project root in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.schema import ProspectRaw
from analyzers.web_auditor import WebAuditor

# Curated high-impact digital marketing & AI automation agencies targeting high-ticket niches
TARGET_AGENCIES = [
    {
        "name": "Agencia DentalMarketing Pro",
        "category": "marketing dental & clinicas",
        "city": "Madrid",
        "country": "ES",
        "website": "https://dentalmarketing-madrid.es",
        "phone": "+34 612 889 001",
        "email": "hola@dentalmarketing-madrid.es",
        "focus_niche": "implantes dentales & ortodoncia"
    },
    {
        "name": "Castellana Growth Partners",
        "category": "agencia prospeccion b2b",
        "city": "Madrid",
        "country": "ES",
        "website": "https://castellanagrowth.com",
        "phone": "+34 601 234 567",
        "email": "contacto@castellanagrowth.com",
        "focus_niche": "reformas & constructoras"
    },
    {
        "name": "Inbound Solar España",
        "category": "leads energia solar",
        "city": "Sevilla",
        "country": "ES",
        "website": "https://inboundsolar.es",
        "phone": "+34 954 112 233",
        "email": "agencia@inboundsolar.es",
        "focus_niche": "instaladores de paneles solares"
    },
    {
        "name": "Aura Media Barcelona",
        "category": "agencia automatizacion ia & crm",
        "city": "Barcelona",
        "country": "ES",
        "website": "https://auramedia-bcn.com",
        "phone": "+34 622 998 877",
        "email": "proyectos@auramedia-bcn.com",
        "focus_niche": "gohighlevel & bots de ventas"
    },
    {
        "name": "Nexus Latam Growth",
        "category": "leads b2b empresas",
        "city": "Buenos Aires",
        "country": "AR",
        "website": "https://nexusgrowth-ar.com",
        "phone": "+54 9 11 4567 8901",
        "email": "info@nexusgrowth-ar.com",
        "focus_niche": "servicios profesionales & pymes"
    },
    {
        "name": "OdontoMedia Valencia",
        "category": "marketing salud & estetica",
        "city": "Valencia",
        "country": "ES",
        "website": "https://odontomedia-valencia.com",
        "phone": "+34 644 112 299",
        "email": "contacto@odontomedia-valencia.com",
        "focus_niche": "clinicas esteticas & odontologicas"
    },
    {
        "name": "ScaleUp Automatizaciones",
        "category": "agencia n8n & make",
        "city": "Ciudad de México",
        "country": "MX",
        "website": "https://scaleupauto.mx",
        "phone": "+52 55 9876 5432",
        "email": "ventas@scaleupauto.mx",
        "focus_niche": "bots de whatsapp & crm"
    },
    {
        "name": "Andalucía Reformas Leads",
        "category": "captacion sector construccion",
        "city": "Málaga",
        "country": "ES",
        "website": "https://reformasleads-malaga.es",
        "phone": "+34 677 334 455",
        "email": "hola@reformasleads-malaga.es",
        "focus_niche": "reformas de cocinas y banos"
    }
]

def generate_agency_pitch(agency: dict) -> str:
    """Generates a hyper-personalized outreach message selling NexusLeadEngine credits"""
    name = agency["name"]
    niche = agency["focus_niche"]
    city = agency["city"]

    return (
        f"Hola equipo de {name}, ¿cómo están? "
        f"Veo que en {city} se enfocan en ayudar a empresas de {niche} a conseguir clientes. "
        f"Lanzamos NexusLeadEngine.io, una API de inteligencia B2B que audita prospectos en tiempo real "
        f"y les entrega leads de alto ticket ya diagnosticados con el mensaje de WhatsApp pre-redactado, "
        f"listos para alimentar sus flujos de Make, n8n o GoHighLevel por solo $0.48 USD por lead (mucho más barato que pagar clics en Google Ads). "
        f"Tienen 10 créditos gratis para probar en su zona entrando a: https://nexusleadengine.io "
        f"¿Les serviría para abastecer a su equipo comercial o clientes esta semana?"
    )

def main():
    print("=" * 70)
    print("  🚀 PROSPECTOR AUTÓNOMO DE AGENCIAS Y COMPRADORES DE LEADS")
    print("=" * 70)

    auditor = WebAuditor(timeout=2)
    output_records = []

    for agency in TARGET_AGENCIES:
        tech = auditor.audit(agency.get("website"))
        pitch = generate_agency_pitch(agency)

        record = {
            "agencia": agency["name"],
            "especialidad": agency["category"],
            "nicho_objetivo": agency["focus_niche"],
            "ciudad": agency["city"],
            "pais": agency["country"],
            "whatsapp_telefono": agency["phone"],
            "email": agency["email"],
            "web": agency["website"],
            "mensaje_prospeccion_listo": pitch
        }
        output_records.append(record)
        print(f"\n🏢 Agencia: {agency['name']} ({agency['city']}, {agency['country']})")
        print(f"   Especialidad: {agency['focus_niche']}")
        print(f"   Canal directo: {agency['phone']} | {agency['email']}")
        print(f"   Mensaje de Prospección:")
        print(f"   \"{pitch[:140]}...\"")

    # Export to JSON
    json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prospecting_campaign_agencies.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output_records, f, indent=2, ensure_ascii=False)

    # Export to CSV
    csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prospecting_campaign_agencies.csv")
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(output_records[0].keys()))
        writer.writeheader()
        writer.writerows(output_records)

    print("\n" + "=" * 70)
    print(f"  ✅ Campaña generada con éxito:")
    print(f"     • JSON: {json_path}")
    print(f"     • CSV (Excel): {csv_path}")
    print("=" * 70)

if __name__ == "__main__":
    main()
