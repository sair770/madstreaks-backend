from supabase import create_client, Client
from app.config import settings, logger


class Database:
    def __init__(self):
        self.client: Client = create_client(
            settings.supabase_url,
            settings.supabase_service_key
        )
        logger.info("Supabase client initialized")

    async def get_active_alerts(self) -> list:
        try:
            response = self.client.table("watchlist_alerts").select("*").eq("is_active", True).execute()
            return response.data
        except Exception as e:
            logger.error(f"Error fetching active alerts: {e}")
            return []

    async def get_alert_by_id(self, alert_id: str) -> dict | None:
        try:
            response = self.client.table("watchlist_alerts").select("*").eq("id", alert_id).single().execute()
            return response.data
        except Exception as e:
            logger.error(f"Error fetching alert {alert_id}: {e}")
            return None

    async def update_alert_price(self, alert_id: str, current_price: float, last_checked_at: str):
        try:
            self.client.table("watchlist_alerts").update({
                "current_price": current_price,
                "last_checked_at": last_checked_at
            }).eq("id", alert_id).execute()
        except Exception as e:
            logger.error(f"Error updating alert {alert_id}: {e}")

    async def mark_alert_triggered(self, alert_id: str, alert_sent_at: str):
        try:
            self.client.table("watchlist_alerts").update({
                "alert_triggered": True,
                "alert_sent_at": alert_sent_at
            }).eq("id", alert_id).execute()
        except Exception as e:
            logger.error(f"Error marking alert {alert_id} as triggered: {e}")

    async def insert_alert(self, data: dict):
        try:
            self.client.table("watchlist_alerts").insert(data).execute()
        except Exception as e:
            logger.error(f"Error inserting alert: {e}")

    async def delete_alert(self, alert_id: str):
        try:
            self.client.table("watchlist_alerts").delete().eq("id", alert_id).execute()
        except Exception as e:
            logger.error(f"Error deleting alert {alert_id}: {e}")


db = Database()
