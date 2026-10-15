#!/usr/bin/env python3
"""
NexusLeadEngine.io - Autonomous AI Council Periodic Audit Loop
==============================================================
Orchestrates an autonomous review loop between local reasoning models (DeepSeek-R1 / Qwen2.5-Coder)
and telemetry metrics from analytics_data.json.

Evaluates:
  1. Funnel CRO & Conversion Leaks (Traffic -> Lead Magnet -> Purchases)
  2. $0 Spend Traffic Acquisition Channels (Reddit, Outbound, Directories)
  3. Data Integrity & API Health
  4. Immediate 24-hour Actionable Directives

Usage:
  python council_audit_loop.py --run-once
  python council_audit_loop.py --interval 3600 --daemon
"""

import os
import sys
import time
import json
import argparse
import urllib.request
import urllib.error
from typing import Dict, Any, Optional

ANALYTICS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "analytics_data.json")
REPORT_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "analytics", "council_report.json")
REPORT_MD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs", "COUNCIL_AUDIT_REPORT.md")
OLLAMA_ENDPOINT = "http://127.0.0.1:11434/api/generate"

def load_telemetry() -> Dict[str, Any]:
    """Loads current live telemetry data from disk with defensive fallbacks."""
    if not os.path.exists(ANALYTICS_FILE):
        return {
            "total_pageviews": 0,
            "unique_visitors": [],
            "captured_prospects": [],
            "total_scans": 0,
            "total_qualified": 0,
            "total_revenue_usd": 0.0,
            "leads_by_niche": {}
        }
    try:
        with open(ANALYTICS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception as e:
        print(f"[Council] Error reading telemetry: {e}", file=sys.stderr)
        return {}

def query_ollama(prompt: str, model: str = "deepseek-r1:8b", timeout_sec: int = 35) -> Optional[str]:
    """Queries local Ollama instance with fallback to qwen2.5-coder:7b."""
    candidates = [model, "qwen2.5-coder:7b", "llama3.1:latest"]
    for candidate in candidates:
        payload = {
            "model": candidate,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.2,
                "top_p": 0.9,
                "num_predict": 512
            }
        }
        try:
            req = urllib.request.Request(
                OLLAMA_ENDPOINT,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                # Ollama deepseek-r1 returns final text in 'response' and thoughts in 'thinking'
                text = result.get("response", "").strip()
                if text:
                    return text
        except Exception as e:
            # Try next model
            continue
    return None

def generate_heuristic_report(telemetry: Dict[str, Any]) -> Dict[str, Any]:
    """Generates deterministic CRO & marketing audit when LLM is unavailable."""
    pageviews = telemetry.get("total_pageviews", 0)
    unique_visitors = len(telemetry.get("unique_visitors", []))
    captured = len(telemetry.get("captured_prospects", []))
    revenue = telemetry.get("total_revenue_usd", 0.0)
    
    conversion_rate = round((captured / max(1, unique_visitors)) * 100, 2)
    
    findings = []
    actions = []
    
    if unique_visitors < 50:
        findings.append("Tráfico frío insuficiente: La landing page tiene menos de 50 visitantes únicos. La prioridad #1 no es alterar el código sino inyectar tráfico calificado de $0 spend.")
        actions.append("Publicar el Blueprint oficial de n8n en r/n8n y r/Integromat utilizando el copy probado en LAUNCH_KIT.md.")
        actions.append("Disparar campaña outbound de WhatsApp/Email a las primeras 10 agencias de prospecting_campaign_agencies.csv.")
    else:
        findings.append(f"Tráfico activo ({unique_visitors} visitantes). Tasa de captura de leads n8n: {conversion_rate}%.")
    
    if captured > 0 and revenue == 0:
        findings.append(f"Hay {captured} prospectos que descargaron el Lead Magnet pero no completaron la compra de créditos.")
        actions.append("Configurar un correo automatizado de seguimiento a los 60 minutos de descargar el flujo ofreciendo un cupón de 10 créditos gratis adicionales con su primera recarga de $15.")
    
    return {
        "status": "HEALTHY",
        "timestamp": int(time.time()),
        "date_str": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "model_used": "deterministic-rules-engine",
        "telemetry_summary": {
            "pageviews": pageviews,
            "unique_visitors": unique_visitors,
            "captured_leads": captured,
            "total_revenue_usd": revenue,
            "conversion_rate_pct": conversion_rate
        },
        "diagnosis": findings,
        "actionable_directives": actions
    }

def run_council_audit(model: str = "deepseek-r1:8b", force_heuristic: bool = False) -> Dict[str, Any]:
    """Executes a complete AI Council audit cycle, writes to disk, and returns the report."""
    telemetry = load_telemetry()
    pageviews = telemetry.get("total_pageviews", 0)
    unique_visitors = len(telemetry.get("unique_visitors", []))
    captured_prospects = telemetry.get("captured_prospects", [])
    captured_count = len(captured_prospects)
    revenue = telemetry.get("total_revenue_usd", 0.0)
    leads_by_niche = telemetry.get("leads_by_niche", {})
    
    conv_magnet = round((captured_count / max(1, unique_visitors)) * 100, 2)
    
    if force_heuristic:
        ai_verdict = None
    else:
        prompt = f"""Eres el Consejo Directivo de IA (CRO, Marketing B2B y Arquitectura) auditando la plataforma SaaS nexusleadengine.io.
El objetivo fundacional del proyecto es generar facturación constante y flujo de caja positivo ("hacer dinero, no tenerlo parado sin facturar").

MÉTRICAS REALES EN TIEMPO REAL:
- Visitas totales: {pageviews}
- Visitantes únicos: {unique_visitors}
- Prospectos de agencias capturados (Lead Magnet n8n): {captured_count}
- Tasa de captura de visitantes a Lead Magnet: {conv_magnet}%
- Facturación total registrada: ${revenue:.2f} USD
- Distribución de nichos más demandados: {json.dumps(leads_by_niche)}
- Últimos prospectos capturados: {captured_prospects[-5:] if captured_prospects else 'Ninguno aún'}

INSTRUCCIÓN:
Genera un dictamen conciso, directo al grano y pragmático en Markdown estructurado en EXACTAMENTE 4 secciones cortas:
1. 📊 Estado Financiero y Embudo: Diagnóstico de fugas del embudo de ventas.
2. 🎯 Eje de Adquisición de Tráfico $0 Spend: Top 2 canales y tácticas para traer tráfico hoy sin pauta.
3. ⚙️ Eje de Conversión (CRO): 2 cambios para convertir visitantes en compradores de packs de $15 a $69 USD.
4. 🚀 Plan de Choque Inmediato: Las 3 tareas indispensables a ejecutar en las próximas 24 horas.

Responde directamente con el análisis sin rodeos."""

    print(f"[Council] Requesting evaluation from AI model ({model})...")
    ai_verdict = query_ollama(prompt, model=model)
    
    if not ai_verdict:
        print("[Council] Local Ollama did not return a response. Using deterministic audit engine...")
        report = generate_heuristic_report(telemetry)
        markdown_content = f"""# 🏛️ Dictamen Autónomo del Consejo de IA - NexusLeadEngine.io
**Fecha:** {report['date_str']}  
**Motor:** {report['model_used']}  

## 📊 Métricas de Embudo
- **Visitantes Únicos:** {unique_visitors}
- **Leads Capturados (n8n Blueprint):** {captured_count} (Conv: {conv_magnet}%)
- **Facturación Total:** ${revenue:.2f} USD

## 🔍 Hallazgos Principales
""" + "\n".join(f"- {f}" for f in report["diagnosis"]) + """

## 🚀 Acciones Inmediatas (Próximas 24 Horas)
""" + "\n".join(f"{i+1}. {a}" for i, a in enumerate(report["actionable_directives"]))
    else:
        report = {
            "status": "COMPLETED",
            "timestamp": int(time.time()),
            "date_str": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "model_used": model,
            "telemetry_summary": {
                "pageviews": pageviews,
                "unique_visitors": unique_visitors,
                "captured_leads": captured_count,
                "total_revenue_usd": revenue,
                "conversion_rate_pct": conv_magnet
            },
            "ai_verdict": ai_verdict
        }
        markdown_content = f"""# 🏛️ Dictamen Autónomo del Consejo de IA - NexusLeadEngine.io
**Fecha:** {report['date_str']}  
**Auditor:** {model}  

{ai_verdict}
"""

    # Persist JSON report
    os.makedirs(os.path.dirname(REPORT_JSON), exist_ok=True)
    with open(REPORT_JSON, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    # Persist Markdown document
    os.makedirs(os.path.dirname(REPORT_MD), exist_ok=True)
    with open(REPORT_MD, "w", encoding="utf-8") as f:
        f.write(markdown_content)

    print(f"[Council] Audit completed successfully. Written to {REPORT_MD}")
    return report

def main():
    parser = argparse.ArgumentParser(description="NexusLeadEngine AI Council Autonomous Loop")
    parser.add_argument("--run-once", action="store_true", help="Run a single audit cycle and exit")
    parser.add_argument("--interval", type=int, default=3600, help="Interval in seconds between audits in daemon mode")
    parser.add_argument("--model", type=str, default="deepseek-r1:8b", help="Ollama model to use")
    parser.add_argument("--daemon", action="store_true", help="Run continuously in the background")
    args = parser.parse_args()

    if args.run_once or not args.daemon:
        run_council_audit(model=args.model)
        return

    print(f"[Council] Starting autonomous periodic audit loop every {args.interval}s...")
    while True:
        try:
            run_council_audit(model=args.model)
        except Exception as e:
            print(f"[Council] Error during cycle: {e}", file=sys.stderr)
        time.sleep(args.interval)

if __name__ == "__main__":
    main()
