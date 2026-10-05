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

    def _fetch_all_outlook_tasks(self, headers: dict) -> tuple:
        """Fetches pending tasks across ALL Outlook To-Do lists (Tareas, Repetitivos, Casa, etc.)."""
        lists_url = "https://graph.microsoft.com/v1.0/me/todo/lists"
        try:
            res = requests.get(lists_url, headers=headers, timeout=10)
            if res.status_code != 200:
                return self._fetch_outlook_tasks(headers, top=50)

            todo_lists = res.json().get("value", [])
            all_tasks = []

            for l in todo_lists:
                lid = l.get("id")
                lname = l.get("displayName", "Tareas")

                url_expand = f"https://graph.microsoft.com/v1.0/me/todo/lists/{lid}/tasks?$filter=status ne 'completed'&$expand=checklistItems&$top=50"
                url_simple = f"https://graph.microsoft.com/v1.0/me/todo/lists/{lid}/tasks?$filter=status ne 'completed'&$top=50"

                tasks_in_list = []
                try:
                    t_res = requests.get(url_expand, headers=headers, timeout=8)
                    if t_res.status_code == 200:
                        tasks_in_list = t_res.json().get("value", [])
                    else:
                        t_res2 = requests.get(url_simple, headers=headers, timeout=8)
                        if t_res2.status_code == 200:
                            tasks_in_list = t_res2.json().get("value", [])
                except Exception as e:
                    logger.warning(f"[Outlook API] List {lname} fetch exception: {e}")

                for t in tasks_in_list:
                    t["_list_name"] = lname
                    t["_list_id"] = lid
                    all_tasks.append(t)

            return 200, all_tasks, ""

        except Exception as e:
            logger.error(f"[Outlook API] Fetch all lists exception: {e}")
            return self._fetch_outlook_tasks(headers, top=50)

    def _fetch_outlook_tasks(self, headers: dict, top: int = 25) -> tuple:
        """Fetches tasks from Microsoft Graph API with automatic retry fallback if 502 Bad Gateway occurs."""
        url_with_expand = f"https://graph.microsoft.com/v1.0/me/todo/lists/tasks/tasks?$filter=status ne 'completed'&$expand=checklistItems&$top={top}"
        url_simple = f"https://graph.microsoft.com/v1.0/me/todo/lists/tasks/tasks?$filter=status ne 'completed'&$top={top}"

        try:
            res = requests.get(url_with_expand, headers=headers, timeout=10)
            if res.status_code == 200:
                return 200, res.json().get("value", []), ""
            elif res.status_code in [500, 502, 503, 504]:
                logger.warning(f"[Outlook API] HTTP {res.status_code} on expand checklistItems, retrying simple endpoint...")
        except Exception as e:
            logger.warning(f"[Outlook API] Exception on expand checklistItems: {e}")

        try:
            res = requests.get(url_simple, headers=headers, timeout=10)
            if res.status_code == 200:
                return 200, res.json().get("value", []), ""
            else:
                return res.status_code, [], res.text
        except Exception as e:
            return 500, [], str(e)

    def get_tasks(self) -> str:
        """Retrieves pending Outlook To-Do tasks across ALL lists with subtasks, notes, due dates, and recurrence via Microsoft Graph API."""
        token, err_detail = self._get_access_token_detail()
        if not token:
            return f"📋 **Tareas Outlook To-Do (Modo Simulación)**:\n{err_detail}"

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        status_code, tasks, err_msg = self._fetch_all_outlook_tasks(headers)
        if status_code != 200:
            return f"❌ Error al consultar tareas de Outlook ({status_code}): {err_msg}"

        if not tasks:
            return "📋 **TUS TAREAS PENDIENTES (Outlook To-Do)**:\n\n🎉 ¡Excelente! No tienes tareas pendientes registradas."

        lines = [
            "📋 **TUS TAREAS DETALLADAS (Todas las Listas de Outlook)**",
            "───────────────────────────\n"
        ]

        import re
        now = datetime.now()

        for idx, t in enumerate(tasks, start=1):
            title = t.get("title", "Sin título").strip()
            lname = t.get("_list_name", "")
            status = t.get("status", "notStarted")
            status_emoji = "⏳" if status == "inProgress" else "📌"

            tag = f" `[{lname}]`" if lname and lname != "Tareas" else ""
            card_lines = [f"{status_emoji} **{idx}. {title}**{tag}"]

            # 1. Due Date / Expiration
            due = t.get("dueDateTime", {}).get("dateTime", None)
            if due:
                try:
                    dt = datetime.fromisoformat(due.replace("Z", "+00:00")).replace(tzinfo=None)
                    if dt < now:
                        card_lines.append(f"   🚨 *EXPIRADA / VENCIDA*: `{dt.strftime('%d/%m/%Y')}`")
                    else:
                        card_lines.append(f"   ⏰ *Vence*: `{dt.strftime('%d/%m/%Y')}`")
                except Exception:
                    card_lines.append(f"   ⏰ *Vence*: `{due[:10]}`")
            else:
                card_lines.append("   ⏰ *Vence*: _Sin fecha de expiración_")

            # 2. Recurrence
            rec = t.get("recurrence")
            if rec:
                rec_type = rec.get("pattern", {}).get("type", "")
                day = rec.get("pattern", {}).get("dayOfMonth", "")
                if "Monthly" in rec_type:
                    card_lines.append(f"   🔄 *Recurrencia*: Mensual (Día {day})" if day else "   🔄 *Recurrencia*: Mensual")
                elif "Weekly" in rec_type:
                    card_lines.append("   🔄 *Recurrencia*: Semanal")
                elif "Daily" in rec_type:
                    card_lines.append("   🔄 *Recurrencia*: Diaria")
                else:
                    card_lines.append(f"   🔄 *Recurrencia*: Activa ({rec_type})")
            else:
                card_lines.append("   🔄 *Recurrencia*: _Sin recurrencia (No recurrente)_")

            # 3. Notes / Description
            body_content = t.get("body", {}).get("content", "").strip()
            if body_content:
                clean_notes = re.sub(r'<[^>]+>', '', body_content).strip()
                if clean_notes:
                    card_lines.append(f"   📝 *Nota*: _{clean_notes}_")

            # 4. Subtasks / Checklist Items
            checklists = t.get("checklistItems", [])
            if checklists:
                card_lines.append("   🔹 *Subtareas:*")
                for item in checklists:
                    sub_title = item.get("displayName", "").strip()
                    is_checked = item.get("isChecked", False)
                    icon = "☑️" if is_checked else "▫️"
                    card_lines.append(f"     {icon} {sub_title}")

            lines.append("\n".join(card_lines) + "\n")

        lines.append("───────────────────────────")
        lines.append(f"💡 *Total de pendientes en todas tus listas*: `{len(tasks)} tareas`")
        return "\n".join(lines)

    def get_overdue_tasks(self) -> str:
        """Retrieves overdue/expired Outlook To-Do tasks across ALL lists."""
        token, err_detail = self._get_access_token_detail()
        if not token:
            return f"📋 **Tareas Expiradas (Modo Simulación)**:\n{err_detail}"

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        status_code, tasks, err_msg = self._fetch_all_outlook_tasks(headers)
        if status_code != 200:
            return f"❌ Error al consultar las tareas ({status_code}): {err_msg}"

        now = datetime.now()
        overdue_tasks = []
        for t in tasks:
            due = t.get("dueDateTime", {}).get("dateTime", None)
            if due:
                try:
                    dt = datetime.fromisoformat(due.replace("Z", "+00:00")).replace(tzinfo=None)
                    if dt < now:
                        overdue_tasks.append((t, dt))
                except Exception:
                    pass

        if not overdue_tasks:
            return "🎉 ¡Excelente! No tienes ninguna tarea expirada o vencida en Outlook To-Do."

        lines = [
            "🚨 **TAREAS EXPIRADAS / VENCIDAS (Todas las Listas)**",
            "───────────────────────────\n"
        ]
        import re
        for idx, (t, dt) in enumerate(overdue_tasks, start=1):
            title = t.get("title", "Sin título").strip()
            lname = t.get("_list_name", "")
            date_fmt = dt.strftime("%d/%m/%Y")
            tag = f" `[{lname}]`" if lname and lname != "Tareas" else ""
            card_lines = [
                f"⚠️ **{idx}. {title}**{tag}",
                f"   🚨 *Expiró el*: `{date_fmt}`"
            ]

            body_content = t.get("body", {}).get("content", "").strip()
            if body_content:
                clean_notes = re.sub(r'<[^>]+>', '', body_content).strip()
                if clean_notes:
                    card_lines.append(f"   📝 *Nota*: _{clean_notes}_")

            lines.append("\n".join(card_lines) + "\n")

        lines.append("───────────────────────────")
        lines.append(f"💡 *Total de tareas expiradas*: `{len(overdue_tasks)}`")
        return "\n".join(lines)

    def search_tasks(self, query: str) -> str:
        """Searches tasks across all lists by title or list name."""
        token, err_detail = self._get_access_token_detail()
        if not token:
            return f"📋 **Búsqueda de Tareas (Modo Simulación)**:\n{err_detail}"

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        status_code, tasks, err_msg = self._fetch_all_outlook_tasks(headers)
        if status_code != 200:
            return f"❌ Error al consultar tareas de Outlook ({status_code}): {err_msg}"

        clean_query = query.lower().strip()
        matching_tasks = [t for t in tasks if clean_query in t.get("title", "").lower() or clean_query in t.get("_list_name", "").lower()]

        if not matching_tasks:
            return f"🔍 No encontré tareas que coincidan con *\"{query}\"* en tu cuenta de Outlook To-Do."

        lines = [
            f"🔍 **TAREAS ENCONTRADAS PARA: \"{query}\"**",
            "───────────────────────────\n"
        ]
        import re
        now = datetime.now()
        for idx, t in enumerate(matching_tasks, start=1):
            title = t.get("title", "Sin título").strip()
            lname = t.get("_list_name", "")
            tag = f" `[{lname}]`" if lname and lname != "Tareas" else ""
            card_lines = [f"📌 **{idx}. {title}**{tag}"]

            due = t.get("dueDateTime", {}).get("dateTime", None)
            if due:
                try:
                    dt = datetime.fromisoformat(due.replace("Z", "+00:00")).replace(tzinfo=None)
                    if dt < now:
                        card_lines.append(f"   🚨 *EXPIRADA / VENCIDA*: `{dt.strftime('%d/%m/%Y')}`")
                    else:
                        card_lines.append(f"   ⏰ *Vence*: `{dt.strftime('%d/%m/%Y')}`")
                except Exception:
                    card_lines.append(f"   ⏰ *Vence*: `{due[:10]}`")
            else:
                card_lines.append("   ⏰ *Vence*: _Sin fecha de expiración_")

            rec = t.get("recurrence")
            if rec:
                rec_type = rec.get("pattern", {}).get("type", "")
                day = rec.get("pattern", {}).get("dayOfMonth", "")
                if "Monthly" in rec_type:
                    card_lines.append(f"   🔄 *Recurrencia*: Mensual (Día {day})" if day else "   🔄 *Recurrencia*: Mensual")
                else:
                    card_lines.append(f"   🔄 *Recurrencia*: Activa ({rec_type})")
            else:
                card_lines.append("   🔄 *Recurrencia*: _Sin recurrencia (No recurrente)_")

            body_content = t.get("body", {}).get("content", "").strip()
            if body_content:
                clean_notes = re.sub(r'<[^>]+>', '', body_content).strip()
                if clean_notes:
                    card_lines.append(f"   📝 *Nota*: _{clean_notes}_")

            lines.append("\n".join(card_lines) + "\n")

        lines.append("───────────────────────────")
        lines.append(f"💡 *Coincidencias encontradas*: `{len(matching_tasks)} tareas`")
        return "\n".join(lines)


    def set_task_due_date(self, task_input: str, date_str: str) -> str:
        """Sets or updates due date for a task in Outlook To-Do."""
        token, err_detail = self._get_access_token_detail()
        if not token:
            return f"❌ No se pudo conectar a Outlook To-Do:\n{err_detail}"

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        import re
        try:
            if "mañana" in date_str.lower():
                target_dt = datetime.now() + timedelta(days=1)
            elif "hoy" in date_str.lower():
                target_dt = datetime.now()
            else:
                d_match = re.search(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})', date_str)
                if d_match:
                    target_dt = datetime(int(d_match.group(1)), int(d_match.group(2)), int(d_match.group(3)))
                else:
                    d_match2 = re.search(r'(\d{1,2})[-/](\d{1,2})[-/](\d{4})', date_str)
                    if d_match2:
                        target_dt = datetime(int(d_match2.group(3)), int(d_match2.group(2)), int(d_match2.group(1)))
                    else:
                        target_dt = datetime.now() + timedelta(days=7)
        except Exception:
            target_dt = datetime.now() + timedelta(days=7)

        iso_date = target_dt.strftime("%Y-%m-%dT00:00:00.0000000")
        fmt_date = target_dt.strftime("%d/%m/%Y")

        status_code, tasks, err_msg = self._fetch_all_outlook_tasks(headers)
        if status_code != 200:
            return f"❌ Error al consultar las tareas ({status_code}): {err_msg}"

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
            return f"⚠️ No encontré ninguna tarea que coincida con `{task_input}`."

        updated = []
        for t in targets:
            tid = t.get("id")
            lid = t.get("_list_id")
            title = t.get("title", "Sin título")
            patch_url = f"https://graph.microsoft.com/v1.0/me/todo/lists/{lid}/tasks/{tid}" if lid else f"https://graph.microsoft.com/v1.0/me/todo/lists/tasks/tasks/{tid}"
            patch_res = requests.patch(patch_url, headers=headers, json={"dueDateTime": {"dateTime": iso_date, "timeZone": "UTC"}})
            if patch_res.status_code in [200, 204]:
                updated.append(title)

        lines = ["⏰ **FECHA DE EXPIRACIÓN ACTUALIZADA EN OUTLOOK**", "───────────────────────────\n"]
        for title in updated:
            lines.append(f"📌 **{title}**\n   ⏰ *Nueva fecha de expiración*: `{fmt_date}`\n")
        lines.append("───────────────────────────")
        lines.append("🎉 ¡Sincronizado con Microsoft Outlook!")
        return "\n".join(lines)

    def set_task_recurrence(self, task_input: str, enable: bool = True, freq: str = "monthly") -> str:
        """Activates or deactivates recurrence for a task in Outlook To-Do."""
        token, err_detail = self._get_access_token_detail()
        if not token:
            return f"❌ No se pudo conectar a Outlook To-Do:\n{err_detail}"

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        status_code, tasks, err_msg = self._fetch_all_outlook_tasks(headers)
        if status_code != 200:
            return f"❌ Error al consultar las tareas ({status_code}): {err_msg}"

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
            return f"⚠️ No encontré ninguna tarea que coincida con `{task_input}`."

        if enable:
            rec_payload = {
                "pattern": {
                    "type": "absoluteMonthly" if "mes" in freq or "monthly" in freq else "weekly",
                    "interval": 1,
                    "dayOfMonth": 1
                },
                "range": {
                    "type": "noEnd",
                    "startDate": datetime.now().strftime("%Y-%m-%d")
                }
            }
            status_msg = "🔄 Recurrencia ACTIVADA (Mensual)"
        else:
            rec_payload = None
            status_msg = "🚫 Recurrencia DESACTIVADA"

        updated = []
        for t in targets:
            tid = t.get("id")
            lid = t.get("_list_id")
            title = t.get("title", "Sin título")
            patch_url = f"https://graph.microsoft.com/v1.0/me/todo/lists/{lid}/tasks/{tid}" if lid else f"https://graph.microsoft.com/v1.0/me/todo/lists/tasks/tasks/{tid}"
            patch_res = requests.patch(patch_url, headers=headers, json={"recurrence": rec_payload})
            if patch_res.status_code in [200, 204]:
                updated.append(title)

        lines = ["🔄 **ESTADO DE RECURRENCIA ACTUALIZADO EN OUTLOOK**", "───────────────────────────\n"]
        for title in updated:
            lines.append(f"📌 **{title}**\n   {status_msg}\n")
        lines.append("───────────────────────────")
        lines.append("🎉 ¡Sincronizado con Microsoft Outlook!")
        return "\n".join(lines)

    def complete_task(self, task_input: str) -> str:
        """Marks one or more tasks as completed in Outlook To-Do via Microsoft Graph API."""
        token, err_detail = self._get_access_token_detail()
        if not token:
            return f"❌ No se pudo conectar a Outlook To-Do:\n{err_detail}"

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        status_code, tasks, err_msg = self._fetch_all_outlook_tasks(headers)
        if status_code != 200:
            return f"❌ Error al consultar las tareas de Outlook ({status_code}): {err_msg}"

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
            lid = t.get("_list_id")
            title = t.get("title", "Sin título")
            patch_url = f"https://graph.microsoft.com/v1.0/me/todo/lists/{lid}/tasks/{tid}" if lid else f"https://graph.microsoft.com/v1.0/me/todo/lists/tasks/tasks/{tid}"
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
