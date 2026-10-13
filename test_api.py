import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from api.main import app, ledger

def test_api_pipeline():
    demo_acc = ledger.get_by_client_id("demo_client")
    if not demo_acc or demo_acc.credits_balance < 5:
        ledger.add_credits("demo_client", 20)

    client = TestClient(app)

    # 1. Test status
    resp = client.get("/v1/status")
    assert resp.status_code == 200
    assert resp.json()["status"] == "online"
    print("✅ GET /v1/status: OK")

    # 2. Test subscribe bot
    sub_payload = {
        "client_id": "test_bot_zapier_01",
        "endpoint_url": "https://hooks.zapier.com/hooks/catch/12345/abcde",
        "secret_key": "my_webhook_secret_key",
        "target_niches": ["implantes dentales"],
        "min_score_threshold": 75,
        "is_active": True
    }
    resp = client.post("/v1/webhooks/subscribe", json=sub_payload)
    assert resp.status_code == 201
    assert resp.json()["status"] == "subscribed"
    print("✅ POST /v1/webhooks/subscribe: OK")

    # 3. Test list subscribers
    resp = client.get("/v1/webhooks/subscribers")
    assert resp.status_code == 200
    assert len(resp.json()["active_subscribers"]) >= 1
    print("✅ GET /v1/webhooks/subscribers: OK")

    # 4. Test trigger scan
    scan_req = {
        "niche": "implantes dentales",
        "location": "Madrid",
        "max_leads": 2,
        "min_score": 70,
        "auto_dispatch_webhooks": False
    }
    resp = client.post("/v1/leads/trigger-scan", json=scan_req)
    assert resp.status_code == 200
    leads = resp.json()
    assert len(leads) > 0
    assert "bot_action" in leads[0]
    assert "pre_drafted_outreach_hook" in leads[0]["bot_action"]
    print(f"✅ POST /v1/leads/trigger-scan: OK ({len(leads)} leads generados y calificados)")

    # 5. Test sample lead
    resp = client.get("/v1/leads/sample")
    assert resp.status_code == 200
    sample = resp.json()
    assert sample["score"] >= 70
    print(f"✅ GET /v1/leads/sample: OK (Lead ID: {sample['lead_id']})")

    # 6. Test analytics dashboard security (Admin Only)
    # 6a. Unauthenticated -> 403 Forbidden
    resp = client.get("/v1/analytics/dashboard")
    assert resp.status_code == 403
    print("✅ GET /v1/analytics/dashboard sin token: 403 Forbidden (Bloqueado a clientes)")

    # 6b. Wrong token -> 403 Forbidden
    resp = client.get("/v1/analytics/dashboard", headers={"x-admin-token": "token_invalido_hacker"})
    assert resp.status_code == 403
    print("✅ GET /v1/analytics/dashboard con token inválido: 403 Forbidden")

    # 6c. Valid token in header
    admin_token = os.getenv("ADMIN_TOKEN", "nexus_sec_admin_992147ae67bc10")
    resp = client.get("/v1/analytics/dashboard", headers={"x-admin-token": admin_token})
    assert resp.status_code == 200
    data = resp.json()
    assert "financial_allocation" in data
    assert "owner_profit_70" in data["financial_allocation"]
    print("✅ GET /v1/analytics/dashboard con x-admin-token válido: 200 OK")

    # 6d. Valid token in query param
    resp = client.get(f"/v1/analytics/dashboard?token={admin_token}")
    assert resp.status_code == 200
    print("✅ GET /v1/analytics/dashboard?token=...: 200 OK")

    print("\n🎉 Todas las pruebas de la API han pasado exitosamente.")

if __name__ == "__main__":
    test_api_pipeline()

