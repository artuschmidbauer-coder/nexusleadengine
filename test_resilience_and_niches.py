import json
import os
import tempfile
from analytics.tracker import AnalyticsTracker
from fastapi.testclient import TestClient
from api.main import app

def test_analytics_tracker_resilience():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
        temp_path = tf.name

    try:
        # Write corrupted / invalid types into the file
        corrupt_data = {
            "total_pageviews": "invalid_string",
            "unique_visitors": [123, None, "safe_ip_hash"],
            "total_scans": -50,
            "total_scanned": None,
            "total_qualified": "corrupt",
            "total_revenue_usd": "not_a_float",
            "leads_by_niche": "not_a_dict",
            "recent_activity": ["invalid_event", {"valid": "event"}]
        }
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(corrupt_data, f)

        # Loading must not raise an exception and should sanitize defaults
        tracker = AnalyticsTracker(file_path=temp_path)
        assert tracker.total_pageviews == 0
        assert tracker.unique_visitors == ["safe_ip_hash"]
        assert tracker.total_scans == 0
        assert tracker.total_scanned == 0
        assert tracker.total_qualified == 0
        assert tracker.total_revenue_usd == 0.0
        assert isinstance(tracker.leads_by_niche, dict)
        assert tracker.recent_activity == [{"valid": "event"}]

        # Saving must be atomic and succeed
        tracker.record_visit("new_visitor_ip")
        assert tracker.total_pageviews == 1
        assert "new_visitor_ip" in tracker.unique_visitors

        # Re-load
        reloaded = AnalyticsTracker(file_path=temp_path)
        assert reloaded.total_pageviews == 1
        assert "new_visitor_ip" in reloaded.unique_visitors
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

def test_sample_lead_all_niches():
    client = TestClient(app)
    countries = ["US", "GB", "ES"]
    niches = ["dental", "remodeling", "solar", "legal"]

    for country in countries:
        for niche in niches:
            resp = client.get(f"/v1/leads/sample?country_code={country}&niche_id={niche}")
            assert resp.status_code == 200
            data = resp.json()
            assert data["score"] >= 0
            assert "business_name" in data
            assert "category" in data
            assert data["location"]["country"] == country

def test_n8n_lead_capture():
    client = TestClient(app)
    resp = client.post("/v1/leads/capture-n8n", json={"email": "prospect_agency@growthstack.com"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "download_url" in data

