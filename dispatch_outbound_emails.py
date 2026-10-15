#!/usr/bin/env python3
"""
NexusLeadEngine.io - Outbound Email Dispatcher & Campaign Manager
================================================================
Manages cold outreach campaigns sent from hola@nexusleadengine.io to targeted marketing agencies.

Supports:
  1. 1-Click Launch in default Mac Mail / Webmail via pre-filled mailto URLs.
  2. Direct SMTP delivery (if SMTP_HOST, SMTP_USER, SMTP_PASSWORD are in .env).
  3. Interactive preview and tracking of contacted agencies.

Usage:
  python dispatch_outbound_emails.py --list
  python dispatch_outbound_emails.py --preview 1
  python dispatch_outbound_emails.py --open-mail 1
"""

import os
import sys
import csv
import json
import smtplib
import urllib.parse
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any, Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_FILE = os.path.join(BASE_DIR, "prospecting_campaign_agencies.csv")
TRACKING_FILE = os.path.join(BASE_DIR, "analytics", "outbound_tracking.json")

def load_agencies() -> List[Dict[str, str]]:
    if not os.path.exists(CSV_FILE):
        return []
    agencies = []
    with open(CSV_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            agencies.append(row)
    return agencies

def load_tracking() -> Dict[str, Any]:
    if os.path.exists(TRACKING_FILE):
        try:
            with open(TRACKING_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"contacted": {}, "stats": {"total_sent": 0}}

def save_tracking(data: Dict[str, Any]):
    os.makedirs(os.path.dirname(TRACKING_FILE), exist_ok=True)
    with open(TRACKING_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def generate_email_content(agency: Dict[str, str]) -> Dict[str, str]:
    name = agency.get("agencia", "Equipo")
    niche = agency.get("nicho_objetivo", "servicios de alto ticket")
    city = agency.get("ciudad", "su ciudad")
    email = agency.get("email", "").strip()

    subject = f"Plantilla n8n lista + 10 leads de {niche} para {name}"
    
    body = f"""Hola equipo de {name},

Estuve revisando su trabajo en {city} y el gran enfoque que tienen captando clientes para el sector de {niche}.

Les escribo desde NexusLeadEngine.io (hola@nexusleadengine.io). Desarrollamos una API de prospección B2B que audita sitios web en tiempo real: detecta si las empresas no tienen Píxel de Meta, si carecen de botón de WhatsApp o si tienen fugas de conversión, y les redacta automáticamente el mensaje de apertura listo para su CRM o sales bot.

Armamos una plantilla oficial de n8n (blueprint .JSON) lista para importar en 1 clic que se conecta a la API y les entrega los prospectos ya calificados por $0.48 USD por lead (mucho más económico y predecible que pujar en Google Ads).

Pueden descargar el flujo y probar 10 créditos gratis en su zona directamente desde:
👉 https://nexusleadengine.io

¿Les resultaría útil para alimentar las campañas de sus clientes o equipo comercial esta semana?

Quedo a su disposición si quieren ver una prueba en vivo.

Un saludo cordial,
Mauro Schmidbauer
Equipo de Crecimiento & APIs
NexusLeadEngine.io • hola@nexusleadengine.io
"""
    return {
        "to": email,
        "subject": subject,
        "body": body,
        "agency_name": name,
        "city": city,
        "niche": niche
    }

def generate_mailto_link(email_data: Dict[str, str]) -> str:
    params = {
        "subject": email_data["subject"],
        "body": email_data["body"]
    }
    query_string = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    return f"mailto:{email_data['to']}?{query_string}"

def send_via_smtp(email_data: Dict[str, str]) -> bool:
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", 587))
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    sender = os.getenv("SMTP_FROM", "hola@nexusleadengine.io")

    if not host or not user or not password:
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = email_data["subject"]
    msg["From"] = f"NexusLeadEngine.io <{sender}>"
    msg["To"] = email_data["to"]
    msg.attach(MIMEText(email_data["body"], "plain", "utf-8"))

    try:
        with smtplib.SMTP(host, port) as server:
            server.starttls()
            server.login(user, password)
            server.sendmail(sender, [email_data["to"]], msg.as_string())
        return True
    except Exception as e:
        print(f"[Error SMTP] {e}", file=sys.stderr)
        return False

def main():
    agencies = load_agencies()
    tracking = load_tracking()

    if len(sys.argv) < 2 or sys.argv[1] == "--list":
        print("\n📋 LISTADO DE AGENCIAS PARA CAMPAÑA OUTBOUND (hola@nexusleadengine.io):")
        print("=" * 80)
        for i, a in enumerate(agencies):
            email = a.get("email", "sin email")
            status = "✅ CONTACTADA" if email in tracking["contacted"] else "⏳ PENDIENTE"
            print(f"[{i+1}] {a.get('agencia')} ({a.get('ciudad')}) - {email} - {status}")
        print("\nComandos útiles:")
        print("  python dispatch_outbound_emails.py --preview <NUM>   # Ver el correo exacto")
        print("  python dispatch_outbound_emails.py --open-mail <NUM> # Abrir en Apple Mail / Webmail listo")
        return

    cmd = sys.argv[1]
    
    if cmd == "--preview" and len(sys.argv) > 2:
        idx = int(sys.argv[2]) - 1
        if 0 <= idx < len(agencies):
            content = generate_email_content(agencies[idx])
            print("\n" + "="*70)
            print(f"DE:      hola@nexusleadengine.io")
            print(f"PARA:    {content['to']}")
            print(f"ASUNTO:  {content['subject']}")
            print("="*70)
            print(content["body"])
            print("="*70)
            print("\nPara abrirlo directamente en tu cliente de correo:")
            print(f"python dispatch_outbound_emails.py --open-mail {idx+1}")
        return

    if cmd == "--open-mail" and len(sys.argv) > 2:
        idx = int(sys.argv[2]) - 1
        if 0 <= idx < len(agencies):
            content = generate_email_content(agencies[idx])
            mailto = generate_mailto_link(content)
            print(f"Abriendo cliente de correo para {content['to']}...")
            import subprocess
            subprocess.run(["open", mailto])
            tracking["contacted"][content["to"]] = {
                "agency": content["agency_name"],
                "timestamp": int(os.path.getmtime(CSV_FILE))
            }
            save_tracking(tracking)
            print("✅ Marcado como despachado en analytics/outbound_tracking.json")
        return

if __name__ == "__main__":
    main()
