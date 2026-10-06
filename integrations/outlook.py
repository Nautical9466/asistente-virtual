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

    def find_best_time_slot(self, target_date: datetime, duration_minutes: int = 60) -> datetime:
        """Scans Outlook Calendar on target_date and finds the first open time slot between 8:00 AM and 5:00 PM."""
        token = self._get_access_token()
        if not token:
            return target_date.replace(hour=9, minute=0, second=0)

        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        start_day_str = target_date.strftime("%Y-%m-%dT00:00:00Z")
        end_day_str = target_date.strftime("%Y-%m-%dT23:59:59Z")

        url = f"https://graph.microsoft.com/v1.0/me/calendarView?startDateTime={start_day_str}&endDateTime={end_day_str}&$orderby=start/dateTime"
        try:
            res = requests.get(url, headers=headers, timeout=10)
            events = res.json().get("value", []) if res.status_code == 200 else []

            for hour in range(8, 18):
                candidate_start = target_date.replace(hour=hour, minute=0, second=0)
                candidate_end = candidate_start + timedelta(minutes=duration_minutes)

                is_busy = False
                for e in events:
                    e_start_str = e.get("start", {}).get("dateTime", "")
                    e_end_str = e.get("end", {}).get("dateTime", "")
                    try:
                        e_start = datetime.fromisoformat(e_start_str.replace("Z", "+00:00")).replace(tzinfo=None)
                        e_end = datetime.fromisoformat(e_end_str.replace("Z", "+00:00")).replace(tzinfo=None)
                        if not (candidate_end <= e_start or candidate_start >= e_end):
                            is_busy = True
                            break
                    except Exception:
                        pass

                if not is_busy:
                    return candidate_start

            return target_date.replace(hour=9, minute=0, second=0)
        except Exception:
            return target_date.replace(hour=9, minute=0, second=0)

    def _parse_event_datetime(self, date_str: str) -> datetime:
        """Helper to convert standard date/time string, ISO format, or relative time into a datetime object in user's local timezone (Central America CST, UTC-6)."""
        import pytz
        try:
            tz_cst = pytz.timezone("America/Managua")
            now = datetime.now(tz_cst).replace(tzinfo=None)
        except Exception:
            now = datetime.utcnow() - timedelta(hours=6)

        if not date_str or not str(date_str).strip():
            return now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)

        clean = str(date_str).lower().strip()
        
        # Direct ISO format
        try:
            return datetime.fromisoformat(clean.replace("z", "+00:00")).replace(tzinfo=None)
        except Exception:
            pass

        import re

        # Extract time (HH:MM or HH AM/PM)
        hr, mn = 9, 0
        has_time = False

        pm_match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)', clean)
        if pm_match:
            hr = int(pm_match.group(1))
            mn = int(pm_match.group(2)) if pm_match.group(2) else 0
            ampm = pm_match.group(3)
            if ampm == "pm" and hr < 12:
                hr += 12
            elif ampm == "am" and hr == 12:
                hr = 0
            has_time = True
        else:
            t_match = re.search(r'(\d{1,2}):(\d{2})', clean)
            if t_match:
                hr = int(t_match.group(1))
                mn = int(t_match.group(2))
                has_time = True

        # Extract date (YYYY-MM-DD, DD/MM/YYYY, or relative 'mañana')
        base_date = now

        m_iso = re.search(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})', clean)
        if m_iso:
            base_date = datetime(int(m_iso.group(1)), int(m_iso.group(2)), int(m_iso.group(3)))
        else:
            m_lat = re.search(r'(\d{1,2})[-/](\d{1,2})[-/](\d{4})', clean)
            if m_lat:
                base_date = datetime(int(m_lat.group(3)), int(m_lat.group(2)), int(m_lat.group(1)))
            elif "mañana" in clean or "manana" in clean:
                base_date = now + timedelta(days=1)

        if has_time:
            return base_date.replace(hour=hr, minute=mn, second=0, microsecond=0)
        else:
            return base_date.replace(hour=9, minute=0, second=0, microsecond=0)

    def create_event(
        self,
        title: str,
        date_str: str,
        duration_minutes: int = 60,
        reminder_minutes: int = 1440,
        is_teams_meeting: bool = False,
        attendees: list = None,
        categories: list = None,
        description: str = "",
        auto_find_best_time: bool = False
    ) -> str:
        """Creates an Event in Outlook Calendar via Microsoft Graph API using parameters parsed by the LLM."""
        token = self._get_access_token()
        if not token:
            return f"📅 **Evento Outlook agendado (Modo Simulación)**: '{title}' para {date_str} ({duration_minutes} min)."

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        clean_title = (title or "").strip()
        if not clean_title:
            clean_title = description[:50].strip() if description else "Reunión Agendada"

        base_dt = self._parse_event_datetime(date_str)
        if auto_find_best_time:
            start_dt = self.find_best_time_slot(base_dt, duration_minutes)
        else:
            start_dt = base_dt

        end_dt = start_dt + timedelta(minutes=duration_minutes)

        payload = {
            "subject": clean_title,
            "start": {"dateTime": start_dt.strftime("%Y-%m-%dT%H:%M:%S"), "timeZone": "Central America Standard Time"},
            "end": {"dateTime": end_dt.strftime("%Y-%m-%dT%H:%M:%S"), "timeZone": "Central America Standard Time"},
            "isReminderOn": True,
            "reminderMinutesBeforeStart": reminder_minutes
        }

        if description:
            payload["body"] = {"contentType": "Text", "content": description}

        if is_teams_meeting:
            payload["isOnlineMeeting"] = True
            payload["onlineMeetingProvider"] = "teamsForBusiness"

        if categories:
            payload["categories"] = categories if isinstance(categories, list) else [str(categories)]

        if attendees:
            att_list = attendees if isinstance(attendees, list) else [str(attendees)]
            payload["attendees"] = [
                {"emailAddress": {"address": a.strip()}, "type": "required"}
                for a in att_list if a and a.strip()
            ]

        url = "https://graph.microsoft.com/v1.0/me/events"
        res = requests.post(url, headers=headers, json=payload)
        if res.status_code in [200, 201]:
            event_data = res.json()
            link = event_data.get("webLink", "#")
            fmt_date = start_dt.strftime("%d/%m/%Y a las %H:%M hs")

            if reminder_minutes >= 1440:
                rem_text = f"{reminder_minutes // 1440} día(s) antes"
            elif reminder_minutes >= 60:
                rem_text = f"{reminder_minutes // 60} hora(s) antes"
            else:
                rem_text = f"{reminder_minutes} min antes"

            details_list = [f"✅ **Evento Creado en Outlook Calendar**: [{clean_title}]({link})"]
            details_list.append(f"⏰ *Fecha y Hora*: `{fmt_date}`")
            details_list.append(f"⏱️ *Duración*: `{duration_minutes} min`")
            details_list.append(f"🔔 *Recordatorio*: `{rem_text}`")

            if is_teams_meeting:
                details_list.append("💻 *Reunión de Microsoft Teams*: `Activada`")
            else:
                details_list.append("💻 *Reunión de Microsoft Teams*: `No activada`")

            if categories:
                cat_str = ", ".join(categories) if isinstance(categories, list) else str(categories)
                details_list.append(f"🏷️ *Etiquetas/Categorías*: `{cat_str}`")

            if attendees:
                att_str = ", ".join(attendees) if isinstance(attendees, list) else str(attendees)
                details_list.append(f"👥 *Invitaciones enviadas*: `{att_str}`")

            return "\n".join(details_list)
        else:
            return f"❌ Error creando evento en Outlook ({res.status_code}): {res.text}"



    def create_task(self, title: str, description: str = "", list_name: str = None) -> str:
        """Creates a Task in Outlook To-Do / Microsoft Tasks, optionally in a specific list."""
        token = self._get_access_token()
        if not token:
            return f"☑️ **Tarea Outlook To-Do creada (Modo Simulación)**: '{title}'."

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        list_id = "tasks"
        target_list_title = "Tareas"

        if list_name and list_name.strip():
            lists_url = "https://graph.microsoft.com/v1.0/me/todo/lists"
            l_res = requests.get(lists_url, headers=headers, timeout=10)
            if l_res.status_code == 200:
                todo_lists = l_res.json().get("value", [])
                clean_target = list_name.lower().strip()
                matched = None
                for l in todo_lists:
                    if clean_target in l.get("displayName", "").lower():
                        matched = l
                        break
                if matched:
                    list_id = matched.get("id")
                    target_list_title = matched.get("displayName")
                else:
                    c_res = requests.post(lists_url, headers=headers, json={"displayName": list_name.strip()})
                    if c_res.status_code in [200, 201]:
                        matched = c_res.json()
                        list_id = matched.get("id")
                        target_list_title = matched.get("displayName")

        payload = {
            "title": title,
            "body": {"content": description, "contentType": "text"} if description else {"content": "", "contentType": "text"}
        }

        url = f"https://graph.microsoft.com/v1.0/me/todo/lists/{list_id}/tasks"
        res = requests.post(url, headers=headers, json=payload)
        if res.status_code in [200, 201]:
            desc_text = f"\n   📝 *Nota*: {description}" if description else ""
            return f"✅ **Tarea Guardada en Outlook To-Do**: '{title}' (en lista **\"{target_list_title}\"**){desc_text}"
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

    def delete_calendar_event(self, event_query: str) -> str:
        """Deletes matching calendar events or recurring series by title/query from Outlook Calendar via Microsoft Graph API."""
        token, err_detail = self._get_access_token_detail()
        if not token:
            return f"❌ No se pudo conectar a Outlook:\n{err_detail}"

        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        import re
        url_events = "https://graph.microsoft.com/v1.0/me/events?$top=250"
        try:
            res = requests.get(url_events, headers=headers, timeout=10)
            events = res.json().get("value", []) if res.status_code == 200 else []

            clean_q = event_query.lower().strip()
            raw_names = re.split(r'[,y&]\s*', clean_q)
            target_names = [n.strip() for n in raw_names if len(n.strip()) > 2]
            if not target_names:
                target_names = [clean_q]

            deleted_events = []
            for name in target_names:
                matched = [e for e in events if name in e.get("subject", "").lower()]
                if matched:
                    for me in matched:
                        eid = me.get("id")
                        sub = me.get("subject")
                        del_res = requests.delete(f"https://graph.microsoft.com/v1.0/me/events/{eid}", headers=headers)
                        if del_res.status_code in [200, 204] and sub not in deleted_events:
                            deleted_events.append(sub)
                else:
                    now_year = datetime.now().year
                    url_v = f"https://graph.microsoft.com/v1.0/me/calendarView?startDateTime={now_year}-01-01T00:00:00Z&endDateTime={now_year}-12-31T23:59:59Z&$top=250"
                    res_v = requests.get(url_v, headers=headers, timeout=10)
                    v_events = res_v.json().get("value", []) if res_v.status_code == 200 else []
                    cv_matched = [ve for ve in v_events if name in ve.get("subject", "").lower()]
                    for ve in cv_matched:
                        sm_id = ve.get("seriesMasterId") or ve.get("id")
                        sub = ve.get("subject")
                        del_res = requests.delete(f"https://graph.microsoft.com/v1.0/me/events/{sm_id}", headers=headers)
                        if del_res.status_code in [200, 204] and sub not in deleted_events:
                            deleted_events.append(sub)

            if deleted_events:
                lines = ["🗑️ **EVENTOS DE CALENDARIO ELIMINADOS EN OUTLOOK**", "───────────────────────────\n"]
                for d in deleted_events:
                    lines.append(f"❌ Eliminado: **\"{d}\"**")
                lines.append("\n───────────────────────────")
                lines.append(f"🎉 Total de eventos eliminados: `{len(deleted_events)}`")
                return "\n".join(lines)
            else:
                return f"⚠️ No se encontraron eventos en tu calendario que coincidan con: \"{event_query}\"."
        except Exception as e:
            return f"❌ Error eliminando evento de calendario: {e}"

    def get_recurring_calendar_events(self, year: int = 2026) -> str:
        """Retrieves all recurring/repetitive events from Outlook Calendar for the specified year via Microsoft Graph API."""
        token, err_detail = self._get_access_token_detail()
        if not token:
            return f"❌ No se pudo conectar a Outlook:\n{err_detail}"

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        url = "https://graph.microsoft.com/v1.0/me/events?$top=100&$select=subject,recurrence,type,start,end,webLink"
        try:
            res = requests.get(url, headers=headers, timeout=12)
            if res.status_code != 200:
                return f"❌ Error al consultar eventos de Outlook ({res.status_code}): {res.text}"

            events = res.json().get("value", [])
            recurring = [e for e in events if e.get("recurrence") is not None or e.get("type") == "seriesMaster"]

            start_str = f"{year}-01-01T00:00:00Z"
            end_str = f"{year}-12-31T23:59:59Z"
            url_view = f"https://graph.microsoft.com/v1.0/me/calendarView?startDateTime={start_str}&endDateTime={end_str}&$top=100&$select=subject,type,start,end"
            res_view = requests.get(url_view, headers=headers, timeout=12)
            view_events = res_view.json().get("value", []) if res_view.status_code == 200 else []

            series_titles = set()
            for ve in view_events:
                if ve.get("type") in ["occurrence", "exception", "seriesMaster"] or ve.get("seriesMasterId"):
                    series_titles.add(ve.get("subject", "").strip())

            lines = [
                f"🗓️ **EVENTOS REPETITIVOS Y RECURRENTES EN TU CALENDARIO ({year})**",
                "───────────────────────────\n"
            ]

            if not recurring and not series_titles:
                return f"🗓️ **EVENTOS REPETITIVOS ({year})**\n\n✨ No se encontraron eventos recurrentes configurados en tu calendario."

            monthly_items = []
            yearly_items = []
            other_items = []

            for r in recurring:
                subject = r.get("subject", "Sin título").strip()
                rec = r.get("recurrence", {}) or {}
                pattern = rec.get("pattern", {}) or {}
                p_type = pattern.get("type", "")
                day_m = pattern.get("dayOfMonth", "")
                month_val = pattern.get("month", "")

                if "monthly" in p_type.lower():
                    day_str = f"Día {day_m} de cada mes" if day_m else "Mensual"
                    monthly_items.append(f"📌 **{subject}** — `{day_str}`")
                elif "yearly" in p_type.lower():
                    yearly_items.append(f"🎂/🎉 **{subject}** — `Anual ({day_m}/{month_val})`" if day_m and month_val else f"🎉 **{subject}** — `Anual`")
                else:
                    other_items.append(f"📌 **{subject}**")

            existing_subs = {r.get("subject", "").strip().lower() for r in recurring}
            for title in sorted(series_titles):
                if title.lower() not in existing_subs and title:
                    if "cumple" in title.lower() or "aniversario" in title.lower():
                        yearly_items.append(f"🎂 **{title}** — `Anual`")
                    else:
                        other_items.append(f"📌 **{title}** — `Recurrente`")

            if monthly_items:
                lines.append("💳 **PAGOS Y COMPROMISOS MENSUALES RECURRENTES:**")
                for item in monthly_items:
                    lines.append(f"  {item}")
                lines.append("")

            if yearly_items:
                lines.append("🎂 **CUMPLEAÑOS Y ANIVERSARIOS ANUALES:**")
                for item in yearly_items:
                    lines.append(f"  {item}")
                lines.append("")

            if other_items:
                lines.append("🔄 **OTROS EVENTOS REPETITIVOS:**")
                for item in other_items:
                    lines.append(f"  {item}")
                lines.append("")

            total_count = len(monthly_items) + len(yearly_items) + len(other_items)
            lines.append("───────────────────────────")
            lines.append(f"💡 *Total de Eventos Repetitivos en {year}*: `{total_count}`")

            return "\n".join(lines)
        except Exception as e:
            return f"❌ Error al consultar eventos repetitivos en Outlook: {e}"

    def _fetch_all_outlook_tasks(self, headers: dict) -> tuple:
        """Fetches pending tasks across ALL Outlook To-Do lists in parallel via ThreadPoolExecutor."""
        from concurrent.futures import ThreadPoolExecutor, as_completed

        lists_url = "https://graph.microsoft.com/v1.0/me/todo/lists"
        try:
            res = requests.get(lists_url, headers=headers, timeout=8)
            if res.status_code != 200:
                return self._fetch_outlook_tasks(headers, top=50)

            todo_lists = res.json().get("value", [])
            all_tasks = []

            def fetch_single_list(l):
                lid = l.get("id")
                lname = l.get("displayName", "Tareas")
                url_expand = f"https://graph.microsoft.com/v1.0/me/todo/lists/{lid}/tasks?$filter=status ne 'completed'&$expand=checklistItems&$top=50"
                url_simple = f"https://graph.microsoft.com/v1.0/me/todo/lists/{lid}/tasks?$filter=status ne 'completed'&$top=50"

                tasks_in_list = []
                try:
                    t_res = requests.get(url_expand, headers=headers, timeout=5)
                    if t_res.status_code == 200:
                        tasks_in_list = t_res.json().get("value", [])
                    else:
                        t_res2 = requests.get(url_simple, headers=headers, timeout=5)
                        if t_res2.status_code == 200:
                            tasks_in_list = t_res2.json().get("value", [])
                except Exception as e:
                    logger.warning(f"[Outlook API] List {lname} fetch exception: {e}")

                for t in tasks_in_list:
                    t["_list_name"] = lname
                    t["_list_id"] = lid
                return tasks_in_list

            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(fetch_single_list, l) for l in todo_lists]
                for future in as_completed(futures):
                    try:
                        tasks = future.result()
                        if tasks:
                            all_tasks.extend(tasks)
                    except Exception as ex:
                        logger.warning(f"[Outlook Parallel Task Fetch Warning]: {ex}")

            return 200, all_tasks, ""

        except Exception as e:
            logger.error(f"[Outlook API] Fetch all lists exception: {e}")
            return self._fetch_outlook_tasks(headers, top=50)

    def get_groups_explanation(self) -> str:
        """Explains Microsoft Graph API limitations regarding List Groups vs Task Lists."""
        token, err_detail = self._get_access_token_detail()
        if not token:
            return f"❌ No se pudo conectar a Outlook:\n{err_detail}"

        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        lists_url = "https://graph.microsoft.com/v1.0/me/todo/lists"
        try:
            res = requests.get(lists_url, headers=headers, timeout=10)
            todo_lists = res.json().get("value", []) if res.status_code == 200 else []

            lines = [
                "📂 **EXPLICACIÓN SOBRE LOS GRUPOS DE LISTAS EN OUTLOOK TO-DO**",
                "───────────────────────────\n",
                "💡 **¿Qué son los Grupos de Listas?**",
                "En la interfaz gráfica de Microsoft To-Do (como tu grupo *Negocios* que colapsa *Capitalero* y *Gorditas*), Microsoft permite crear agrupaciones de listas.\n",
                "⚠️ **Limitación Técnica Oficial de Microsoft Graph API**:",
                "Microsoft permite crear y gestionar **Listas de Tareas** y **Subtareas**, pero **NO ha publicado un endpoint en la API oficial** (`listGroups`) para crear o mover carpetas de 'Grupos de Listas' mediante código externo.\n",
                "🎯 **Solución de Agrupamiento Recomendada**:",
                "Para agrupar tus listas en la aplicación, usamos nombres estructurados con prefijos (ej: `Compras - MaxiPali`, `Compras - Mercado Ivan`, `Negocios - Capitalero`). Esto hace que Microsoft To-Do las ordene juntas automáticamente en tu barra lateral.\n",
                "───────────────────────────",
                f"📊 *Total de Listas individuales registradas*: `{len(todo_lists)}`"
            ]
            return "\n".join(lines)
        except Exception as e:
            return f"❌ Error al consultar listas: {e}"

    def delete_subtasks_from_list(self, list_name: str) -> str:
        """Deletes all checklist items / subtasks from tasks inside a specific list."""
        token, err_detail = self._get_access_token_detail()
        if not token:
            return f"❌ No se pudo conectar a Outlook:\n{err_detail}"

        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        lists_url = "https://graph.microsoft.com/v1.0/me/todo/lists"
        l_res = requests.get(lists_url, headers=headers, timeout=10)
        if l_res.status_code != 200:
            return f"❌ Error consultando listas: {l_res.text}"

        todo_lists = l_res.json().get("value", [])
        clean_target = list_name.lower().strip()
        target_list = None
        for l in todo_lists:
            if clean_target in l.get("displayName", "").lower():
                target_list = l
                break

        if not target_list:
            return f"⚠️ No encontré la lista \"{list_name}\"."

        lid = target_list.get("id")
        lname = target_list.get("displayName")

        t_res = requests.get(f"https://graph.microsoft.com/v1.0/me/todo/lists/{lid}/tasks", headers=headers)
        tasks = t_res.json().get("value", []) if t_res.status_code == 200 else []

        deleted_count = 0
        for t in tasks:
            tid = t.get("id")
            chk_res = requests.get(f"https://graph.microsoft.com/v1.0/me/todo/lists/{lid}/tasks/{tid}/checklistItems", headers=headers)
            chks = chk_res.json().get("value", []) if chk_res.status_code == 200 else []
            for chk in chks:
                chkid = chk.get("id")
                requests.delete(f"https://graph.microsoft.com/v1.0/me/todo/lists/{lid}/tasks/{tid}/checklistItems/{chkid}", headers=headers)
                deleted_count += 1

        return f"🗑️ **Subtareas Eliminadas**: Se eliminaron `{deleted_count}` subtareas de la lista **\"{lname}\"**."


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

    def get_full_context_for_llm(self) -> str:
        """Retrieves complete context (all lists, pending tasks, completed tasks, and upcoming calendar events) for LLM analysis."""
        token, err_detail = self._get_access_token_detail()
        if not token:
            return f"(No se pudo conectar a Outlook: {err_detail})"

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        lines = ["### CONTEXTO REAL Y EN VIVO DE MICROSOFT OUTLOOK (EVENTOS Y TAREAS REALES DEL USUARIO):"]

        # 1. Fetch Calendar Events (Next 14 Days)
        try:
            now = datetime.now()
            start_str = now.strftime("%Y-%m-%dT00:00:00Z")
            end_str = (now + timedelta(days=14)).strftime("%Y-%m-%dT23:59:59Z")
            cal_url = f"https://graph.microsoft.com/v1.0/me/calendarView?startDateTime={start_str}&endDateTime={end_str}&$orderby=start/dateTime&$top=25"
            cal_res = requests.get(cal_url, headers=headers, timeout=8)
            events = cal_res.json().get("value", []) if cal_res.status_code == 200 else []
            
            lines.append("\n🗓️ **EVENTOS REALES EN OUTLOOK CALENDAR (Próximos 14 días)**:")
            if not events:
                lines.append("  - (No hay ningún evento agendado en el calendario de Outlook en los próximos 14 días)")
            else:
                for e in events:
                    subject = e.get("subject", "Sin título").strip()
                    dt_str = e.get("start", {}).get("dateTime", "")[:16].replace("T", " ")
                    lines.append(f"  • {subject} [Fecha/Hora: {dt_str}]")
        except Exception as ce:
            logger.warning(f"[Outlook Context] Fetch calendar exception: {ce}")

        # 2. Fetch To-Do Lists and Tasks
        lists_url = "https://graph.microsoft.com/v1.0/me/todo/lists"
        try:
            res = requests.get(lists_url, headers=headers, timeout=10)
            if res.status_code == 200:
                todo_lists = res.json().get("value", [])
                lines.append("\n📋 **TAREAS REALES EN OUTLOOK TO-DO**:")

                for l in todo_lists:
                    lid = l.get("id")
                    lname = l.get("displayName", "Sin nombre")

                    # Pending tasks
                    url_pending = f"https://graph.microsoft.com/v1.0/me/todo/lists/{lid}/tasks?$filter=status ne 'completed'&$top=50"
                    p_res = requests.get(url_pending, headers=headers, timeout=8)
                    p_tasks = p_res.json().get("value", []) if p_res.status_code == 200 else []

                    lines.append(f"\n  📂 Lista: '{lname}'")
                    lines.append(f"    • Tareas Pendientes ({len(p_tasks)}):")
                    if not p_tasks:
                        lines.append("      - (Sin tareas pendientes en esta lista)")
                    else:
                        for t in p_tasks:
                            title = t.get("title", "Sin título").strip()
                            due = t.get("dueDateTime", {}).get("dateTime", "")
                            due_str = f" [Vence: {due[:10]}]" if due else ""
                            lines.append(f"      - {title}{due_str}")

            return "\n".join(lines)
        except Exception as e:
            return f"(Error al extraer contexto de Outlook: {e})"

    def create_todo_list(self, list_name: str) -> str:

        """Creates a new task list in Outlook To-Do / Microsoft Tasks."""
        token, err_detail = self._get_access_token_detail()
        if not token:
            return f"❌ No se pudo conectar a Outlook To-Do:\n{err_detail}"

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        url = "https://graph.microsoft.com/v1.0/me/todo/lists"
        payload = {"displayName": list_name.strip()}
        try:
            res = requests.post(url, headers=headers, json=payload)
            if res.status_code in [200, 201]:
                return f"📁 **NUEVA LISTA CREADA EN OUTLOOK TO-DO**\n\n✨ Se creó con éxito la lista: **\"{list_name.strip()}\"**.\n\nYa puedes agregarle tareas usando: `crear tarea: Nombre de la tarea`"
            else:
                return f"❌ Error creando lista en Outlook ({res.status_code}): {res.text}"
        except Exception as e:
            return f"❌ Error de conexión al crear lista: {e}"

    def delete_todo_list(self, list_name_or_id: str) -> str:
        """Deletes a task list in Outlook To-Do / Microsoft Tasks."""
        token, err_detail = self._get_access_token_detail()
        if not token:
            return f"❌ No se pudo conectar a Outlook To-Do:\n{err_detail}"

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        lists_url = "https://graph.microsoft.com/v1.0/me/todo/lists"
        l_res = requests.get(lists_url, headers=headers, timeout=10)
        if l_res.status_code != 200:
            return f"❌ Error al consultar listas: {l_res.text}"

        todo_lists = l_res.json().get("value", [])
        clean_name = list_name_or_id.lower().strip()
        target_list = None
        for l in todo_lists:
            if l.get("id") == list_name_or_id or clean_name in l.get("displayName", "").lower():
                target_list = l
                break

        if not target_list:
            return f"⚠️ No encontré la lista \"{list_name_or_id}\" para eliminar."

        lid = target_list.get("id")
        lname = target_list.get("displayName")
        del_url = f"https://graph.microsoft.com/v1.0/me/todo/lists/{lid}"
        del_res = requests.delete(del_url, headers=headers)
        if del_res.status_code in [200, 204]:
            return f"🗑️ **Lista Eliminada**: **\"{lname}\"**"
        else:
            return f"❌ Error eliminando lista ({del_res.status_code}): {del_res.text}"

    def delete_duplicate_lists(self) -> str:
        """Finds and deletes duplicate lists ending with (1), (2), etc."""
        token, err_detail = self._get_access_token_detail()
        if not token:
            return f"❌ No se pudo conectar a Outlook To-Do:\n{err_detail}"

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        lists_url = "https://graph.microsoft.com/v1.0/me/todo/lists"
        l_res = requests.get(lists_url, headers=headers, timeout=10)
        if l_res.status_code != 200:
            return f"❌ Error al consultar listas: {l_res.text}"

        todo_lists = l_res.json().get("value", [])
        deleted = []
        import re
        for l in todo_lists:
            lname = l.get("displayName", "")
            if re.search(r'\(\d+\)$', lname.strip()):
                lid = l.get("id")
                del_res = requests.delete(f"https://graph.microsoft.com/v1.0/me/todo/lists/{lid}", headers=headers)
                if del_res.status_code in [200, 204]:
                    deleted.append(lname)

        if not deleted:
            return "🎉 No se encontraron listas duplicadas con '(1)' para eliminar."

        lines = ["🗑️ **LISTAS DUPLICADAS ELIMINADAS EN OUTLOOK TO-DO**", "───────────────────────────\n"]
        for d in deleted:
            lines.append(f"❌ Eliminada: **\"{d}\"**")
        lines.append("\n───────────────────────────")
        lines.append("🎉 ¡Tus listas están limpias y sin duplicados!")
        return "\n".join(lines)


    def move_task(self, task_input: str, destination_list_name: str) -> str:
        """Moves a task from its current list to a destination list by list name."""
        token, err_detail = self._get_access_token_detail()
        if not token:
            return f"❌ No se pudo conectar a Outlook To-Do:\n{err_detail}"

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        lists_url = "https://graph.microsoft.com/v1.0/me/todo/lists"
        l_res = requests.get(lists_url, headers=headers, timeout=10)
        if l_res.status_code != 200:
            return f"❌ Error al consultar listas ({l_res.status_code}): {l_res.text}"

        todo_lists = l_res.json().get("value", [])
        clean_dest = destination_list_name.lower().strip()
        dest_list = None

        for l in todo_lists:
            if clean_dest in l.get("displayName", "").lower():
                dest_list = l
                break

        if not dest_list:
            c_res = requests.post(lists_url, headers=headers, json={"displayName": destination_list_name.strip()})
            if c_res.status_code in [200, 201]:
                dest_list = c_res.json()
            else:
                return f"⚠️ No encontré ni pude crear la lista destino \"{destination_list_name}\"."

        dest_id = dest_list.get("id")
        dest_name = dest_list.get("displayName")

        status_code, tasks, err_msg = self._fetch_all_outlook_tasks(headers)
        if status_code != 200:
            return f"❌ Error al consultar tareas ({status_code}): {err_msg}"

        clean_input = task_input.lower().strip()
        target_task = None
        for t in tasks:
            if clean_input in t.get("title", "").lower():
                target_task = t
                break

        if not target_task:
            return f"⚠️ No encontré ninguna tarea pendiente que coincida con \"{task_input}\"."

        src_id = target_task.get("_list_id")
        tid = target_task.get("id")
        title = target_task.get("title", "Sin título")

        payload = {
            "title": title,
            "body": target_task.get("body", {}),
            "dueDateTime": target_task.get("dueDateTime"),
            "recurrence": target_task.get("recurrence")
        }
        create_url = f"https://graph.microsoft.com/v1.0/me/todo/lists/{dest_id}/tasks"
        res = requests.post(create_url, headers=headers, json=payload)
        if res.status_code in [200, 201]:
            del_url = f"https://graph.microsoft.com/v1.0/me/todo/lists/{src_id}/tasks/{tid}"
            requests.delete(del_url, headers=headers)
            return f"✅ **Tarea Movida**: *\"{title}\"* ➔ **{dest_name}**"
        else:
            return f"❌ Error moviendo tarea a {dest_name} ({res.status_code}): {res.text}"


    def rename_list(self, old_name: str, new_name: str) -> str:
        """Renames an existing Outlook To-Do list."""
        token, err_detail = self._get_access_token_detail()
        if not token:
            return f"❌ No se pudo conectar a Outlook To-Do:\n{err_detail}"

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        lists_url = "https://graph.microsoft.com/v1.0/me/todo/lists"
        l_res = requests.get(lists_url, headers=headers, timeout=10)
        if l_res.status_code != 200:
            return f"❌ Error al consultar listas: {l_res.text}"

        todo_lists = l_res.json().get("value", [])
        clean_old = old_name.lower().strip()
        target_list = None
        for l in todo_lists:
            if clean_old in l.get("displayName", "").lower():
                target_list = l
                break

        if not target_list:
            return f"⚠️ No encontré la lista \"{old_name}\" para renombrar."

        lid = target_list.get("id")
        patch_url = f"https://graph.microsoft.com/v1.0/me/todo/lists/{lid}"
        patch_res = requests.patch(patch_url, headers=headers, json={"displayName": new_name.strip()})
        if patch_res.status_code in [200, 204]:
            return f"✏️ **Lista Renombrada**: *\"{target_list.get('displayName')}\"* ➔ **\"{new_name.strip()}\"**"
        else:
            return f"❌ Error al renombrar lista ({patch_res.status_code}): {patch_res.text}"


    def get_all_lists_grouped(self, hide_empty: bool = True) -> str:
        """Retrieves all Outlook To-Do lists and groups tasks by list (omitting empty lists if hide_empty is True)."""
        token, err_detail = self._get_access_token_detail()
        if not token:
            return f"📋 **Listas de Outlook (Modo Simulación)**:\n{err_detail}"

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        lists_url = "https://graph.microsoft.com/v1.0/me/todo/lists"
        try:
            res = requests.get(lists_url, headers=headers, timeout=8)
            if res.status_code != 200:
                return f"❌ Error consultando listas ({res.status_code}): {res.text}"

            todo_lists = res.json().get("value", [])
            if not todo_lists:
                return "📁 No tienes listas registradas en tu cuenta de Outlook To-Do."

            # Parallel fetch tasks across all lists
            status_code, all_tasks, err_msg = self._fetch_all_outlook_tasks(headers)
            if status_code != 200:
                return f"❌ Error al consultar tareas de Outlook ({status_code}): {err_msg}"

            # Group tasks by list ID
            tasks_by_list = {}
            for t in all_tasks:
                lid = t.get("_list_id")
                if lid not in tasks_by_list:
                    tasks_by_list[lid] = []
                tasks_by_list[lid].append(t)

            output_lines = [
                "📁 **TUS LISTAS DE OUTLOOK TO-DO Y TAREAS PENDIENTES**",
                "───────────────────────────\n"
            ]

            total_all_tasks = 0
            active_lists_count = 0

            for l_idx, l in enumerate(todo_lists, start=1):
                lid = l.get("id")
                lname = l.get("displayName", "Sin nombre")
                tasks = tasks_by_list.get(lid, [])

                if not tasks and hide_empty:
                    continue

                total_all_tasks += len(tasks)
                active_lists_count += 1

                output_lines.append(f"📂 **Lista {l_idx}: {lname}** (`{len(tasks)} pendientes`)")
                if not tasks:
                    output_lines.append("   └─ *(Sin tareas pendientes en esta lista)*\n")
                else:
                    for t_idx, t in enumerate(tasks, start=1):
                        title = t.get("title", "Sin título").strip()
                        output_lines.append(f"   {l_idx}.{t_idx} {title}")
                    output_lines.append("")

            if total_all_tasks == 0:
                return "📋 **TUS TAREAS PENDIENTES (Outlook To-Do)**:\n\n🎉 ¡Excelente! No tienes tareas pendientes en ninguna de tus listas."

            output_lines.append("───────────────────────────")
            output_lines.append(f"💡 *Listas con Pendientes*: `{active_lists_count}` | *Total Pendientes*: `{total_all_tasks}`")
            output_lines.append("\n💡 *Tip para gestionar rápidamente:* Puedes decirme: *\"Elimina las tareas 1 y 2 de la lista 1\"* o *\"Mueve la tarea 3 de la lista 1 a la lista 2\"*.")

            return "\n".join(output_lines)
        except Exception as e:
            return f"❌ Error al consultar listas: {e}"

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

    def delete_task(self, task_input: str, list_name_or_number: str = None) -> str:
        """Permanently deletes one or more tasks in Outlook To-Do via Microsoft Graph API."""
        token, err_detail = self._get_access_token_detail()
        if not token:
            return f"❌ No se pudo conectar a Outlook To-Do:\n{err_detail}"

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        import re
        lists_url = "https://graph.microsoft.com/v1.0/me/todo/lists"
        l_res = requests.get(lists_url, headers=headers, timeout=10)
        if l_res.status_code != 200:
            return f"❌ Error al consultar listas ({l_res.status_code}): {l_res.text}"

        todo_lists = l_res.json().get("value", [])

        # 1. Filter by specific list if provided
        target_list = None
        if list_name_or_number is not None and str(list_name_or_number).strip():
            clean_lname = str(list_name_or_number).strip().lower()
            if clean_lname.isdigit():
                l_idx = int(clean_lname) - 1
                if 0 <= l_idx < len(todo_lists):
                    target_list = todo_lists[l_idx]
            if not target_list:
                for l in todo_lists:
                    if clean_lname in l.get("displayName", "").lower():
                        target_list = l
                        break

        # 2. Fetch tasks in target list or across all lists
        target_tasks = []
        if target_list:
            lid = target_list.get("id")
            lname = target_list.get("displayName")
            url_t = f"https://graph.microsoft.com/v1.0/me/todo/lists/{lid}/tasks?$filter=status ne 'completed'&$top=100"
            t_res = requests.get(url_t, headers=headers, timeout=10)
            tasks_in_list = t_res.json().get("value", []) if t_res.status_code == 200 else []
            for t in tasks_in_list:
                t["_list_id"] = lid
                t["_list_name"] = lname
                target_tasks.append(t)
        else:
            status_code, target_tasks, err_msg = self._fetch_all_outlook_tasks(headers)
            if status_code != 200:
                return f"❌ Error al consultar las tareas de Outlook ({status_code}): {err_msg}"

        if not target_tasks:
            return "ℹ️ No se encontraron tareas pendientes."

        # Parse task numbers or title matches
        numbers = [int(n) for n in re.findall(r'\b\d+\b', task_input)]
        matched_tasks = []

        if numbers:
            for num in numbers:
                if 1 <= num <= len(target_tasks):
                    matched_tasks.append(target_tasks[num - 1])
        else:
            clean_input = task_input.lower().strip()
            for t in target_tasks:
                if clean_input in t.get("title", "").lower():
                    matched_tasks.append(t)

        if not matched_tasks:
            return f"⚠️ No encontré ninguna tarea pendiente que coincida con `{task_input}`."

        deleted_titles = []
        failed_titles = []

        for t in matched_tasks:
            tid = t.get("id")
            lid = t.get("_list_id")
            title = t.get("title", "Sin título")
            del_url = f"https://graph.microsoft.com/v1.0/me/todo/lists/{lid}/tasks/{tid}"
            del_res = requests.delete(del_url, headers=headers)
            if del_res.status_code in [200, 204]:
                deleted_titles.append(title)
            else:
                failed_titles.append(title)

        lines = ["🗑️ **TAREAS ELIMINADAS EN OUTLOOK TO-DO**", "───────────────────────────\n"]
        for title in deleted_titles:
            lines.append(f"❌ ~{title}~\n")

        if failed_titles:
            lines.append("\n⚠️ **No se pudieron eliminar:**")
            for title in failed_titles:
                lines.append(f"• {title}\n")

        lines.append("───────────────────────────")
        lines.append(f"🎉 Total de tareas eliminadas permanentemente: `{len(deleted_titles)}`")
        return "\n".join(lines)

    def complete_task(self, task_input: str, list_name_or_number: str = None) -> str:
        """Marks one or more tasks as completed in Outlook To-Do via Microsoft Graph API."""
        token, err_detail = self._get_access_token_detail()
        if not token:
            return f"❌ No se pudo conectar a Outlook To-Do:\n{err_detail}"

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        import re
        lists_url = "https://graph.microsoft.com/v1.0/me/todo/lists"
        l_res = requests.get(lists_url, headers=headers, timeout=10)
        if l_res.status_code != 200:
            return f"❌ Error al consultar listas: {l_res.text}"

        todo_lists = l_res.json().get("value", [])

        target_list = None
        if list_name_or_number is not None and str(list_name_or_number).strip():
            clean_lname = str(list_name_or_number).strip().lower()
            if clean_lname.isdigit():
                l_idx = int(clean_lname) - 1
                if 0 <= l_idx < len(todo_lists):
                    target_list = todo_lists[l_idx]
            if not target_list:
                for l in todo_lists:
                    if clean_lname in l.get("displayName", "").lower():
                        target_list = l
                        break

        target_tasks = []
        if target_list:
            lid = target_list.get("id")
            lname = target_list.get("displayName")
            url_t = f"https://graph.microsoft.com/v1.0/me/todo/lists/{lid}/tasks?$filter=status ne 'completed'&$top=100"
            t_res = requests.get(url_t, headers=headers, timeout=10)
            tasks_in_list = t_res.json().get("value", []) if t_res.status_code == 200 else []
            for t in tasks_in_list:
                t["_list_id"] = lid
                t["_list_name"] = lname
                target_tasks.append(t)
        else:
            status_code, target_tasks, err_msg = self._fetch_all_outlook_tasks(headers)
            if status_code != 200:
                return f"❌ Error al consultar las tareas de Outlook ({status_code}): {err_msg}"

        if not target_tasks:
            return "ℹ️ No hay tareas pendientes para completar."

        numbers = [int(n) for n in re.findall(r'\b\d+\b', task_input)]
        targets = []
        if numbers:
            for num in numbers:
                if 1 <= num <= len(target_tasks):
                    targets.append(target_tasks[num - 1])
        else:
            clean_input = task_input.lower().strip()
            for t in target_tasks:
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
            lines.append(f"✔️ ~{title}~\n")

        if failed_titles:
            lines.append("\n❌ **No se pudieron completar:**")
            for title in failed_titles:
                lines.append(f"• {title}\n")

        lines.append("───────────────────────────")
        lines.append("🎉 ¡Sincronizado con tu cuenta de Microsoft Outlook!")
        return "\n".join(lines)
