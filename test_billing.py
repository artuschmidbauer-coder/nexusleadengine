import sys
import os
import time
import hmac
import hashlib
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from api.main import app, stripe_service
from billing.ledger import BillingLedger
import api.main as main


def test_automated_billing_system(tmp_path, monkeypatch):
    test_ledger = BillingLedger(str(tmp_path / "billing_ledger.json"))
    monkeypatch.setattr(main, "ledger", test_ledger)
    monkeypatch.setattr(stripe_service, "ledger", test_ledger)
    monkeypatch.setattr(stripe_service, "webhook_secret", "whsec_test")
    client = TestClient(app)

    print("\n--- 1. CONSULTAR PAQUETES DISPONIBLES ---")
    resp = client.get("/v1/billing/packages")
    assert resp.status_code == 200
    packages = resp.json()
    assert len(packages) >= 3
    print(f"✅ Paquetes cargados correctamente ({len(packages)} opciones)")

    print("\n--- 2. CREAR CUENTA ---")
    account = test_ledger.create_account("empresa_bot_saas")
    assert account.client_id == "empresa_bot_saas"

    print("\n--- 3. SIMULAR PAGO AUTOMÁTICO VÍA STRIPE WEBHOOK ---")
    webhook_event = {
        "id": "evt_test_12345",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_session_99",
                "payment_status": "paid",
                "client_reference_id": "empresa_bot_saas",
                "metadata": {
                    "client_id": "empresa_bot_saas",
                    "package_id": "pack_pro_200",
                    "credits": "200"
                }
            }
        }
    }
    raw_body = json.dumps(webhook_event).encode("utf-8")
    ts = int(time.time())
    sig = hmac.new(b"whsec_test", f"{ts}.".encode() + raw_body, hashlib.sha256).hexdigest()
    headers = {"Stripe-Signature": f"t={ts},v1={sig}"}

    resp = client.post("/v1/billing/stripe-webhook", content=raw_body, headers=headers)
    assert resp.status_code == 200
    res = resp.json()
    assert res["status"] == "PROCESSED"
    assert res["credits_added"] == 200

    print("\n--- 4. CONSULTAR SALDO CON LA API KEY DEL CLIENTE ---")
    acc_headers = {"x-api-key": account.api_key}
    resp = client.get("/v1/billing/balance", headers=acc_headers)
    assert resp.status_code == 200
    bal_data = resp.json()
    assert bal_data["credits_balance"] >= 200

    print("\n--- 5. CONSUMO AUTOMÁTICO DE LEADS (METERED USAGE) ---")
    scan_req = {
        "niche": "implantes dentales",
        "location": "Madrid",
        "country_code": "ES",
        "max_leads": 2,
        "min_score": 60,
        "auto_dispatch_webhooks": False
    }
    resp = client.post("/v1/leads/trigger-scan", json=scan_req, headers=acc_headers)
    assert resp.status_code == 200
    leads = resp.json()
    assert len(leads) > 0

    resp = client.get("/v1/billing/balance", headers=acc_headers)
    new_bal = resp.json()["credits_balance"]
    assert new_bal == bal_data["credits_balance"] - len(leads)
    print(f"✅ Saldo actualizado automáticamente: {new_bal} créditos.")
