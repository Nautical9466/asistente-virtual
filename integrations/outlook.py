import os
import logging
import requests
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class OutlookIntegration:
    """Microsoft Graph API Integration for Outlook Calendar Events, Outlook To-Do Tasks, and Outlook Emails."""

    def __init__(self):
        self.client_id = os.environ.get("OUTLOOK_CLIENT_ID")
        self.client_secret = os.environ.get("OUTLOOK_CLIENT_SECRET")
        self.tenant_id = os.environ.get("OUTLOOK_TENANT_ID", "common")
        self.refresh_token = os.environ.get("OUTLOOK_REFRESH_TOKEN")
        self.access_token = None

    def _get_access_token(self) -> str:
        """Refreshes Microsoft OAuth2 access token."""
        if not self.client_id or not self.client_secret or not self.refresh_token:
            return None

        url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "scope": "https://graph.microsoft.com/.default"
        }
        try:
            res = requests.post(url, data=data)
            if res.status_code == 200:
                self.access_token = res.json().get("access_token")
                return self.access_token
            else:
                logger.error(f"[Outlook API] Refresh Token Error: {res.text}")
                return None
        except Exception as e:
            logger.error(f"[Outlook API] Connection Error: {e}")
            return None

    def create_event(self, title: str, date_str: str, duration_minutes: int = 30) -> str:
        """Creates an Event in Outlook Calendar."""
        token = self._get_access_token()
        if not token:
            return f"📅 **Evento Outlook agendado (Modo Simulación)**: '{title}' para {date_str} ({duration_minutes} min)."

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        start_dt = datetime.now() + timedelta(days=1)
        end_dt = start_dt + timedelta(minutes=duration_minutes)

        payload = {
            "subject": title,
            "start": {"dateTime": start_dt.isoformat(), "timeZone": "Central America Standard Time"},
            "end": {"dateTime": end_dt.isoformat(), "timeZone": "Central America Standard Time"}
        }

        url = "https://graph.microsoft.com/v1.0/me/events"
        res = requests.post(url, headers=headers, json=payload)
        if res.status_code in [200, 201]:
            event_data = res.json()
            link = event_data.get("webLink", "#")
            return f"✅ **Evento Creado en Outlook Calendar**: [{title}]({link})"
        else:
            return f"❌ Error creando evento en Outlook: {res.text}"

    def create_task(self, title: str, description: str = "") -> str:
        """Creates a Task in Outlook To-Do / Microsoft Tasks."""
        token = self._get_access_token()
        if not token:
            return f"☑️ **Tarea Outlook To-Do creada (Modo Simulación)**: '{title}'."

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        payload = {
            "title": title,
            "body": {"content": description, "contentType": "text"}
        }

        url = "https://graph.microsoft.com/v1.0/me/todo/lists/tasks/tasks"
        res = requests.post(url, headers=headers, json=payload)
        if res.status_code in [200, 201]:
            return f"✅ **Tarea Guardada en Outlook To-Do / Microsoft Tasks**: '{title}'"
        else:
            return f"❌ Error creando tarea en Outlook To-Do: {res.text}"

    def send_email(self, recipient: str, subject: str, body_content: str) -> str:
        """Drafts and sends an Email via Outlook Mail API."""
        token = self._get_access_token()
        if not token:
            return f"✉️ **Borrador de Correo Outlook (Modo Simulación)**\n- **Para**: {recipient}\n- **Asunto**: {subject}\n- **Cuerpo**: {body_content}"

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        payload = {
            "message": {
                "subject": subject,
                "body": {"contentType": "Text", "content": body_content},
                "toRecipients": [{"emailAddress": {"address": recipient}}]
            }
        }

        url = "https://graph.microsoft.com/v1.0/me/sendMail"
        res = requests.post(url, headers=headers, json=payload)
        if res.status_code in [200, 202]:
            return f"📧 **Correo Enviado con Éxito vía Outlook** a `{recipient}`."
        else:
            return f"❌ Error enviando correo vía Outlook: {res.text}"
