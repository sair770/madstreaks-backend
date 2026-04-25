"""
Helper script for briefing agents to create alerts from research findings.

Usage in nse-briefing or stock-briefing:
    from briefing_alerts_helper import BriefingAlertHelper

    helper = BriefingAlertHelper(backend_url="https://web-production-f47c1.up.railway.app")

    alerts = [
        {
            "symbol": "NIFTY",
            "alert_type": "above",
            "target_price": 24500,
            "description": "ORB Breakout Level",
            "notes": "If breaks above, expect 25000"
        },
        {
            "symbol": "NIFTY",
            "alert_type": "above",
            "target_price": 25000,
            "description": "First Target",
            "notes": "Resistance from previous high"
        }
    ]

    result = helper.create_alerts_from_research(alerts)
    print(f"Created: {len(result['created'])} alerts")
"""

import httpx
import json


class BriefingAlertHelper:
    def __init__(self, backend_url: str = "http://localhost:8000", api_key: str = None):
        self.backend_url = backend_url.rstrip("/")
        self.api_key = api_key or self._get_api_key_from_env()

        if not self.api_key:
            raise ValueError(
                "API key required. Pass api_key parameter or set BRIEFING_API_KEY env var"
            )

    @staticmethod
    def _get_api_key_from_env() -> str | None:
        import os
        return os.getenv("BRIEFING_API_KEY")

    def create_alerts_from_research(
        self,
        alerts: list[dict],
        user_id: str = "2d620133-08e5-49c1-ae8b-94e85adf29b1"
    ) -> dict:
        """
        Create multiple alerts from briefing research findings.

        Args:
            alerts: List of alert dicts with:
                - symbol (str): Stock/index symbol (e.g., "NIFTY", "TCS")
                - alert_type (str): "above", "below", or "pct_change"
                - target_price (float): Price level to watch
                - description (str, optional): Human-readable level name
                - notes (str, optional): Additional context

            user_id (str): Supabase user_id (defaults to main user)

        Returns:
            Response dict with "created" and "skipped" lists
        """
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            response = httpx.post(
                f"{self.backend_url}/alerts/from-briefing",
                json=alerts,
                params={"user_id": user_id},
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            result = response.json()

            if result.get("created"):
                print(f"✅ Created {len(result['created'])} alerts from briefing")
                for alert in result["created"]:
                    print(f"  - {alert['symbol']} {alert['alert_type']} {alert['target_price']}")

            if result.get("skipped"):
                print(f"⚠️  Skipped {len(result['skipped'])} alerts:")
                for skip in result["skipped"]:
                    print(f"  - {skip.get('reason', 'Unknown error')}")

            return result
        except httpx.RequestError as e:
            print(f"❌ Failed to create alerts: {e}")
            return {"created": [], "skipped": [], "error": str(e)}


# Example: Using in nse-briefing workflow
if __name__ == "__main__":
    helper = BriefingAlertHelper(
        backend_url="http://localhost:8000",
        api_key="sk-briefing-dev-key-change-in-prod"  # or set BRIEFING_API_KEY env var
    )

    # Example research findings
    research_alerts = [
        {
            "symbol": "NIFTY",
            "alert_type": "above",
            "target_price": 24500,
            "description": "ORB Breakout",
            "notes": "If breaks above with volume, target 25000"
        },
        {
            "symbol": "NIFTY",
            "alert_type": "above",
            "target_price": 25000,
            "description": "First Target",
            "notes": "Resistance from previous high"
        },
        {
            "symbol": "NIFTY",
            "alert_type": "below",
            "target_price": 23500,
            "description": "Support/SL",
            "notes": "If breaks below, potential reversal"
        }
    ]

    result = helper.create_alerts_from_research(research_alerts)
    print(json.dumps(result, indent=2))
