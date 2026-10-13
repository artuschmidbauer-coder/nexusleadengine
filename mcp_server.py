#!/usr/bin/env python3
"""
NexusLeadEngine Official Model Context Protocol (MCP) Server.
Enables Claude Desktop, Cursor, Gemini, and Autonomous AI Agent Swarms to:
1. Scan & audit high-ticket B2B local business leads in real-time.
2. Run conversion leak technical diagnostics on any prospect website.
3. Check remaining prepaid credits.
4. Execute autonomous Machine-to-Machine (M2M) crypto checkout via NOWPayments.
"""
import sys
import json
import os
import urllib.request
import urllib.error

API_BASE_URL = os.getenv("NEXUS_API_URL", "https://nexusleadengine.io")
API_KEY = os.getenv("NEXUS_API_KEY", "")

TOOLS = [
    {
        "name": "nexus_sample_lead",
        "description": "Fetches a live audited sample B2B lead with technical signals (Meta Pixel, Google Tag, WhatsApp widget) and a pre-drafted outreach hook.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "country_code": {
                    "type": "string",
                    "description": "Country code for the sample: 'US', 'GB', or 'ES'. Default is 'US'.",
                    "default": "US"
                }
            }
        }
    },
    {
        "name": "nexus_scan_leads",
        "description": "Scans and audits qualified high-ticket local business leads (dental clinics, luxury contractors, cosmetic surgeons, commercial roofing) in a target city.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "niche": {
                    "type": "string",
                    "description": "Target high-ticket niche (e.g. 'dental implants', 'clínica dental implantes', 'luxury kitchen remodelers')."
                },
                "location": {
                    "type": "string",
                    "description": "Target city/metro area (e.g. 'Miami', 'Madrid', 'London')."
                },
                "max_leads": {
                    "type": "integer",
                    "description": "Number of qualified leads to extract (1 to 20).",
                    "default": 3
                },
                "country_code": {
                    "type": "string",
                    "description": "Country code: 'US', 'GB', or 'ES'.",
                    "default": "US"
                }
            },
            "required": ["niche", "location"]
        }
    },
    {
        "name": "nexus_check_balance",
        "description": "Checks the remaining prepaid credit balance for the current API key.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "nexus_m2m_buy_pack",
        "description": "Autonomous Agent Checkout: Generates direct on-chain crypto payment instructions (address, amount, network) for an AI agent's crypto wallet to purchase more leads.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "package_id": {
                    "type": "string",
                    "description": "Package to buy: 'pack_micro_25' ($15 USD, 25 leads), 'pack_starter_60' ($29 USD), 'pack_pro_200' ($69 USD), 'pack_scale_600' ($149 USD).",
                    "default": "pack_micro_25"
                },
                "pay_currency": {
                    "type": "string",
                    "description": "Cryptocurrency to pay with: 'usdttrc20' (default), 'usdtbsc', 'btc', 'eth', 'sol', 'trx', 'ltc'.",
                    "default": "usdttrc20"
                }
            }
        }
    }
]

def make_request(endpoint: str, method: str = "GET", data: dict = None, headers: dict = None) -> dict:
    url = f"{API_BASE_URL.rstrip('/')}{endpoint}"
    req_headers = {"User-Agent": "NexusLeadEngine-MCP/2.0", "Content-Type": "application/json"}
    if API_KEY:
        req_headers["x-api-key"] = API_KEY
    if headers:
        req_headers.update(headers)

    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=req_headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        try:
            return {"error_status": e.code, "detail": json.loads(err_body)}
        except Exception:
            return {"error_status": e.code, "detail": err_body}
    except Exception as e:
        return {"error": str(e)}

def handle_tool_call(tool_name: str, arguments: dict) -> str:
    if tool_name == "nexus_sample_lead":
        country = arguments.get("country_code", "US")
        res = make_request(f"/v1/leads/sample?country_code={country}")
        return json.dumps(res, indent=2, ensure_ascii=False)

    elif tool_name == "nexus_scan_leads":
        payload = {
            "niche": arguments["niche"],
            "location": arguments["location"],
            "max_leads": arguments.get("max_leads", 3),
            "country_code": arguments.get("country_code", "US"),
            "min_score": 70,
            "auto_dispatch_webhooks": False
        }
        res = make_request("/v1/leads/trigger-scan", method="POST", data=payload)
        return json.dumps(res, indent=2, ensure_ascii=False)

    elif tool_name == "nexus_check_balance":
        res = make_request("/v1/billing/balance")
        return json.dumps(res, indent=2, ensure_ascii=False)

    elif tool_name == "nexus_m2m_buy_pack":
        payload = {
            "package_id": arguments.get("package_id", "pack_micro_25"),
            "pay_currency": arguments.get("pay_currency", "usdttrc20")
        }
        res = make_request("/v1/billing/agent-buy", method="POST", data=payload)
        return json.dumps(res, indent=2, ensure_ascii=False)

    return f"Unknown tool: {tool_name}"

def main():
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        line = line.strip()
        if not line:
            continue

        try:
            msg = json.loads(line)
        except Exception:
            continue

        req_id = msg.get("id")
        method = msg.get("method")
        params = msg.get("params", {})

        if method == "initialize":
            resp = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {
                        "name": "nexusleadengine-mcp",
                        "version": "2.0.0"
                    }
                }
            }
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()

        elif method == "notifications/initialized":
            pass

        elif method == "tools/list":
            resp = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "tools": TOOLS
                }
            }
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()

        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            try:
                content_text = handle_tool_call(tool_name, arguments)
            except Exception as e:
                content_text = f"Tool execution error: {str(e)}"

            resp = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": content_text
                        }
                    ]
                }
            }
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()

        elif method == "ping":
            resp = {"jsonrpc": "2.0", "id": req_id, "result": {}}
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()

if __name__ == "__main__":
    main()
