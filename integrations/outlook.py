import os

class OutlookIntegration:
    """Helper for Outlook Calendar & Task integration."""

    def __init__(self):
        self.client_id = os.environ.get("OUTLOOK_CLIENT_ID")

    def create_event(self, title: str, date: str, duration_minutes: int = 30) -> str:
        # Stub/Production API call wrapper
        return f"📅 Evento '{title}' programado para {date} ({duration_minutes} mins) en Outlook Calendar."
