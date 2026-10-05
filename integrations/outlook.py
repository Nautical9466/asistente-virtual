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

    def get_calendar_events(self, days_ahead: int = 14) -> str:
        """Retrieves upcoming calendar events from Outlook via Microsoft Graph API."""
        token = self._get_access_token()
        if not token:
            return "📅 **Agenda Outlook (Modo Simulación)**: Conecta tu token de Outlook en Render para ver eventos reales."

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        now = datetime.now()
        start_str = now.strftime("%Y-%m-%dT00:00:00Z")
        end_str = (now + timedelta(days=days_ahead)).strftime("%Y-%m-%dT23:59:59Z")

        url = f"https://graph.microsoft.com/v1.0/me/calendarView?startDateTime={start_str}&endDateTime={end_str}&$orderby=start/dateTime&$top=25"
        try:
            res = requests.get(url, headers=headers)
            if res.status_code == 200:
                events = res.json().get("value", [])
                if not events:
                    return f"📅 **Agenda Outlook**: No tienes eventos agendados para los próximos {days_ahead} días."

                lines = [f"📅 **Tus próximos eventos en Outlook (próximos {days_ahead} días)**:\n"]
                for e in events:
                    subject = e.get("subject", "Sin título")
                    start_data = e.get("start", {})
                    dt_str = start_data.get("dateTime", "")
                    try:
                        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                        date_fmt = dt.strftime("%d/%m/%Y a las %H:%M")
                    except Exception:
                        date_fmt = dt_str[:16]
                    link = e.get("webLink", "")
                    if link:
                        lines.append(f"• **[{subject}]({link})** — `{date_fmt}`")
                    else:
                        lines.append(f"• **{subject}** — `{date_fmt}`")
                return "\n".join(lines)
            else:
                logger.error(f"[Outlook API] Fetch events error: {res.text}")
                return f"❌ Error al obtener eventos de Outlook ({res.status_code}): {res.text}"
        except Exception as e:
            logger.error(f"[Outlook API] Fetch events exception: {e}")
            return f"❌ Error de conexión al consultar Outlook: {e}"
