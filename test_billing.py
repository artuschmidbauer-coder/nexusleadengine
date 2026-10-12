import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from api.main import app, ledger

def test_automated_billing_system():
    client = TestClient(app)

    print("\n--- 1. CONSULTAR PAQUETES DISPONIBLES ---")
    resp = client.get("/v1/billing/packages")
    assert resp.status_code == 200
    packages = resp.json()
    assert len(packages) == 3
    print(f"✅ Paquetes cargados correctamente ({len(packages)} opciones):")
    for p in packages:
        print(f"   • {p['name']}: ${p['price_usd']} USD (${p['unit_price_usd']}/lead)")

    print("\n--- 2. CREAR CUENTA Y GENERAR LINK DE STRIPE CHECKOUT ---")
    checkout_req = {
        "client_id": "empresa_bot_saas",
        "package_id": "pack_growth_200"
    }
    resp = client.post("/v1/billing/create-checkout", json=checkout_req)
    assert resp.status_code == 200
    checkout_data = resp.json()
    print(f"✅ Checkout generado:")
    print(f"   • Session ID: {checkout_data['session_id']}")
    print(f"   • Créditos a acreditar: {checkout_data['credits_to_add']}")
    print(f"   • URL de pago: {checkout_data['checkout_url'][:50]}...")

    print("\n--- 3. SIMULAR PAGO AUTOMÁTICO VÍA STRIPE WEBHOOK ---")
    webhook_event = {
        "id": "evt_test_12345",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": checkout_data["session_id"],
                "client_reference_id": "empresa_bot_saas",
                "metadata": {
                    "client_id": "empresa_bot_saas",
                    "package_id": "pack_growth_200",
                    "credits": "200"
                }
            }
        }
    }
    resp = client.post("/v1/billing/stripe-webhook", json=webhook_event)
    assert resp.status_code == 200
    res = resp.json()
    assert res["status"] == "PROCESSED"
    assert res["credits_added"] == 200
    print(f"✅ Webhook de Stripe procesado en milisegundos:")
    print(f"   • Cliente: {res['client_id']}")
    print(f"   • Créditos agregados: +{res['credits_added']}")
    print(f"   • Nuevo saldo total: {res['new_balance']}")

    print("\n--- 4. CONSULTAR SALDO CON LA API KEY DEL CLIENTE ---")
    account = ledger.get_by_client_id("empresa_bot_saas")
    headers = {"x-api-key": account.api_key}
    resp = client.get("/v1/billing/balance", headers=headers)
    assert resp.status_code == 200
    bal_data = resp.json()
    assert bal_data["credits_balance"] >= 200
    print(f"✅ Saldo verificado para API Key {bal_data['api_key_masked']}: {bal_data['credits_balance']} créditos activos.")

    print("\n--- 5. CONSUMO AUTOMÁTICO DE LEADS (METERED USAGE) ---")
    scan_req = {
        "niche": "energia solar",
        "location": "Sevilla",
        "max_leads": 2,
        "min_score": 60,
        "auto_dispatch_webhooks": False
    }
    resp = client.post("/v1/leads/trigger-scan", json=scan_req, headers=headers)
    assert resp.status_code == 200
    leads = resp.json()
    print(f"✅ Entregados {len(leads)} leads calificados.")

    # Check that credits decreased by exactly len(leads)
    resp = client.get("/v1/billing/balance", headers=headers)
    new_bal = resp.json()["credits_balance"]
    assert new_bal == bal_data["credits_balance"] - len(leads)
    print(f"✅ Saldo actualizado automáticamente tras consumo:")
    print(f"   • Saldo anterior: {bal_data['credits_balance']}")
    print(f"   • Leads entregados: {len(leads)}")
    print(f"   • Saldo actual: {new_bal} créditos.")

    print("\n🎉 ¡Flujo de Cobro y Facturación Automática 100% Validado!")

if __name__ == "__main__":
    test_automated_billing_system()
