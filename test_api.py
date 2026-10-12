import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from api.main import app

def test_api_pipeline():
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

    print("\n🎉 Todas las pruebas de la API han pasado exitosamente.")

if __name__ == "__main__":
    test_api_pipeline()
