import json
import os
import time
from typing import Dict, List, Any
from models.schema import EnrichedLead

ANALYTICS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "analytics_data.json")

class AnalyticsTracker:
    """Tracks live metrics, conversion rates, revenues, visitors and pipeline throughput."""

    def __init__(self, file_path: str = ANALYTICS_FILE):
        self.file_path = file_path
        self.total_pageviews: int = 0
        self.unique_visitors: List[str] = []
        self.total_scans: int = 0
        self.total_scanned: int = 0
        self.total_qualified: int = 0
        self.total_credits_consumed: int = 0
        self.total_revenue_usd: float = 0.0
        self.leads_by_niche: Dict[str, int] = {}
        self.recent_activity: List[Dict[str, Any]] = []
        self._load()

    def _load(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.total_pageviews = data.get("total_pageviews", 0)
                    self.unique_visitors = data.get("unique_visitors", [])
                    self.total_scans = data.get("total_scans", 0)
                    self.total_scanned = data.get("total_scanned", 0)
                    self.total_qualified = data.get("total_qualified", 0)
                    self.total_credits_consumed = data.get("total_credits_consumed", 0)
                    self.total_revenue_usd = data.get("total_revenue_usd", 0.0)
                    self.leads_by_niche = data.get("leads_by_niche", {})
                    self.recent_activity = data.get("recent_activity", [])
            except Exception as e:
                print(f"Error loading analytics: {e}")

    def _save(self):
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                data = {
                    "total_pageviews": self.total_pageviews,
                    "unique_visitors": self.unique_visitors[-500:],
                    "total_scans": self.total_scans,
                    "total_scanned": self.total_scanned,
                    "total_qualified": self.total_qualified,
                    "total_credits_consumed": self.total_credits_consumed,
                    "total_revenue_usd": self.total_revenue_usd,
                    "leads_by_niche": self.leads_by_niche,
                    "recent_activity": self.recent_activity[:50]
                }
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving analytics: {e}")

    def record_visit(self, ip_hash: str, path: str = "/"):
        self.total_pageviews += 1
        if ip_hash not in self.unique_visitors:
            self.unique_visitors.append(ip_hash)
        self._save()

    def record_scan_event(self, niche: str, location: str, total_found: int):
        self.total_scans += 1
        self.total_scanned += total_found
        self._save()

    def record_qualified_lead(self, lead: EnrichedLead):
        self.total_qualified += 1
        self.total_credits_consumed += 1

        niche_key = lead.category.lower()
        self.leads_by_niche[niche_key] = self.leads_by_niche.get(niche_key, 0) + 1

        event = {
            "timestamp": int(time.time()),
            "time_str": time.strftime("%H:%M:%S", time.localtime()),
            "lead_id": lead.lead_id,
            "business_name": lead.business_name,
            "category": lead.category,
            "city": lead.location.get("city", "N/A"),
            "score": lead.score,
            "tier": lead.tier.value,
            "channel": lead.bot_action.recommended_channel.value,
            "ticket_estimate_usd": lead.bot_action.estimated_ticket_value_usd,
            "hook_snippet": lead.bot_action.pre_drafted_outreach_hook[:90] + "..."
        }
        self.recent_activity.insert(0, event)
        self.recent_activity = self.recent_activity[:50]
        self._save()

    def record_revenue(self, amount_usd: float, payer: str, credits_added: int):
        self.total_revenue_usd += amount_usd
        event = {
            "timestamp": int(time.time()),
            "time_str": time.strftime("%H:%M:%S", time.localtime()),
            "type": "PAYMENT",
            "amount_usd": amount_usd,
            "payer": payer,
            "credits_added": credits_added,
            "business_name": f"💰 Recarga de Saldo: +{credits_added} créditos (${amount_usd} USD)",
            "score": 100,
            "tier": "PAYMENT"
        }
        self.recent_activity.insert(0, event)
        self.recent_activity = self.recent_activity[:50]
        self._save()

    def get_dashboard_metrics(self, active_accounts_count: int = 1) -> Dict[str, Any]:
        qualification_rate = (
            round((self.total_qualified / self.total_scanned) * 100, 1)
            if self.total_scanned > 0 else 0.0
        )
        return {
            "total_pageviews": self.total_pageviews,
            "unique_visitors_count": len(self.unique_visitors),
            "total_scans": self.total_scans,
            "total_prospects_scanned": self.total_scanned,
            "total_qualified_leads": self.total_qualified,
            "qualification_rate_percent": qualification_rate,
            "total_revenue_usd": round(self.total_revenue_usd, 2),
            "total_credits_consumed": self.total_credits_consumed,
            "active_clients_count": active_accounts_count,
            "leads_by_niche": self.leads_by_niche,
            "recent_activity": self.recent_activity[:25]
        }
