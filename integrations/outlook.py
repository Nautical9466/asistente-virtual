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

    def _get_access_token_detail(self) -> tuple:
        """Refreshes Microsoft OAuth2 access token and returns detailed status."""
        missing = []
        if not self.client_id: missing.append("OUTLOOK_CLIENT_ID")
        if not self.client_secret: missing.append("OUTLOOK_CLIENT_SECRET")
        if not self.refresh_token: missing.append("OUTLOOK_REFRESH_TOKEN")

        if missing:
            return None, f"Falta configurar en Render: `{', '.join(missing)}`."

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
                return self.access_token, "OK"
            else:
                err_data = res.json() if res.headers.get("content-type", "").startswith("application/json") else {}
                err_desc = err_data.get("error_description", res.text[:150])
                logger.error(f"[Outlook API] Refresh Token Error: {res.text}")
                return None, f"Microsoft denegó el token (HTTP {res.status_code}): {err_desc}"
        except Exception as e:
            logger.error(f"[Outlook API] Connection Error: {e}")
            return None, f"Error de conexión con Microsoft: {e}"

    def _get_access_token(self) -> str:
        token, _ = self._get_access_token_detail()
        return token

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
        token, err_detail = self._get_access_token_detail()
        if not token:
            return f"📅 **Agenda Outlook (Modo Simulación)**:\n{err_detail}"

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
                    return f"🗓️ **AGENDA OUTLOOK (Próximos {days_ahead} días)**\n\n✨ No tienes eventos agendados."

                lines = [
                    f"🗓️ **AGENDA DE EVENTOS (Próximos {days_ahead} días)**",
                    "───────────────────────────\n"
                ]
                for e in events:
                    subject = e.get("subject", "Sin título")
                    start_data = e.get("start", {})
                    dt_str = start_data.get("dateTime", "")
                    try:
                        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                        date_fmt = dt.strftime("%d/%m/%Y • %H:%M hs")
                    except Exception:
                        date_fmt = dt_str[:16]
                    link = e.get("webLink", "")
                    if link:
                        lines.append(f"📌 **[{subject}]({link})**\n   ⏰ `{date_fmt}`\n")
                    else:
                        lines.append(f"📌 **{subject}**\n   ⏰ `{date_fmt}`\n")

                lines.append("───────────────────────────")
                lines.append(f"💡 *Total de eventos*: `{len(events)}`")
                return "\n".join(lines)
            else:
                logger.error(f"[Outlook API] Fetch events error: {res.text}")
                return f"❌ Error al obtener eventos de Outlook ({res.status_code}): {res.text}"
        except Exception as e:
            logger.error(f"[Outlook API] Fetch events exception: {e}")
            return f"❌ Error de conexión al consultar Outlook: {e}"

    def get_tasks(self) -> str:
        """Retrieves pending Outlook To-Do tasks from Microsoft Graph API."""
        token, err_detail = self._get_access_token_detail()
        if not token:
            return f"📋 **Tareas Outlook To-Do (Modo Simulación)**:\n{err_detail}"

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        url = "https://graph.microsoft.com/v1.0/me/todo/lists/tasks/tasks?$filter=status ne 'completed'&$top=25"
        try:
            res = requests.get(url, headers=headers)
            if res.status_code == 200:
                tasks = res.json().get("value", [])
                if not tasks:
                    return "📋 **TUS TAREAS PENDIENTES (Outlook To-Do)**:\n\n🎉 ¡Excelente! No tienes tareas pendientes registradas."

                lines = [
                    "📋 **TUS TAREAS PENDIENTES (Outlook To-Do)**",
                    "───────────────────────────\n"
                ]
                for idx, t in enumerate(tasks, start=1):
                    title = t.get("title", "Sin título")
                    status = t.get("status", "notStarted")
                    status_emoji = "⏳" if status == "inProgress" else "📌"
                    due = t.get("dueDateTime", {}).get("dateTime", None)
                    if due:
                        try:
                            dt = datetime.fromisoformat(due.replace("Z", "+00:00"))
                            due_fmt = f" (Vence: `{dt.strftime('%d/%m/%Y')}`)"
                        except Exception:
                            due_fmt = f" (Vence: `{due[:10]}`)"
                    else:
                        due_fmt = ""

                    lines.append(f"{status_emoji} **{idx}. {title}**{due_fmt}\n")

                lines.append("───────────────────────────")
                lines.append(f"💡 *Total de pendientes*: `{len(tasks)} tareas`")
                return "\n".join(lines)
            else:
                logger.error(f"[Outlook API] Fetch tasks error: {res.text}")
                return f"❌ Error al consultar tareas de Outlook ({res.status_code}): {res.text}"
        except Exception as e:
            logger.error(f"[Outlook API] Fetch tasks exception: {e}")
            return f"❌ Error de conexión al consultar tareas: {e}"

    def complete_task(self, task_input: str) -> str:
        """Marks one or more tasks as completed in Outlook To-Do via Microsoft Graph API."""
        token, err_detail = self._get_access_token_detail()
        if not token:
            return f"❌ No se pudo conectar a Outlook To-Do:\n{err_detail}"

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        url = "https://graph.microsoft.com/v1.0/me/todo/lists/tasks/tasks?$filter=status ne 'completed'&$top=50"
        try:
            res = requests.get(url, headers=headers)
            if res.status_code != 200:
                return f"❌ Error al consultar las tareas de Outlook ({res.status_code}): {res.text}"

            tasks = res.json().get("value", [])
            if not tasks:
                return "ℹ️ No hay tareas pendientes para completar."

            import re
            numbers = [int(n) for n in re.findall(r'\b\d+\b', task_input)]

            targets = []
            if numbers:
                for num in numbers:
                    if 1 <= num <= len(tasks):
                        targets.append(tasks[num - 1])
            else:
                clean_input = task_input.lower().strip()
                for t in tasks:
                    if clean_input in t.get("title", "").lower():
                        targets.append(t)

            if not targets:
                return f"⚠️ No encontré ninguna tarea pendiente que coincida con `{task_input}`."

            completed_titles = []
            failed_titles = []

            for t in targets:
                tid = t.get("id")
                title = t.get("title", "Sin título")
                patch_url = f"https://graph.microsoft.com/v1.0/me/todo/lists/tasks/tasks/{tid}"
                patch_res = requests.patch(patch_url, headers=headers, json={"status": "completed"})
                if patch_res.status_code in [200, 204]:
                    completed_titles.append(title)
                else:
                    failed_titles.append(title)

            lines = ["✅ **TAREAS MARCADAS COMO COMPLETADAS EN OUTLOOK**", "───────────────────────────\n"]
            for title in completed_titles:
                lines.append(f"✔️ **{title}**\n")

            if failed_titles:
                lines.append("\n❌ **No se pudieron completar:**")
                for title in failed_titles:
                    lines.append(f"• {title}\n")

            lines.append("───────────────────────────")
            lines.append("🎉 ¡Sincronizado con tu cuenta de Microsoft Outlook!")
            return "\n".join(lines)

        except Exception as e:
            logger.error(f"[Outlook API] Complete task exception: {e}")
            return f"❌ Error al marcar tarea como completada: {e}"
