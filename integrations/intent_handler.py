import re
import json
import logging
from datetime import datetime, timedelta
from typing import Tuple, Optional, Any
from integrations.outlook import OutlookIntegration

logger = logging.getLogger(__name__)

def parse_reminder_time(text: str) -> Tuple[Optional[datetime], str]:
    """Extracts target datetime and reason for a Telegram message reminder."""
    now = datetime.now()
    
    # 1. "en X minutos" / "en X horas"
    m_rel = re.search(r'en\s+(\d+)\s+(minuto|minutos|min|hora|horas|h)\b', text, re.IGNORECASE)
    if m_rel:
        num = int(m_rel.group(1))
        unit = m_rel.group(2).lower()
        if 'h' in unit:
            target_dt = now + timedelta(hours=num)
        else:
            target_dt = now + timedelta(minutes=num)
        
        reason = re.sub(r'en\s+\d+\s+(minuto|minutos|min|hora|horas|h)', '', text, flags=re.IGNORECASE).strip()
        reason = re.sub(r'(quiero que|me mandes|un mensaje|recordandome|recordarme|eso|por aca|por aquí|por aqui)', '', reason, flags=re.IGNORECASE).strip()
        reason = re.sub(r'^[\s,:\'\"]+|[\s,:\'\"]+$', '', reason).strip()
        return target_dt, reason.capitalize() if reason else "Recordatorio"

    # 2. "a las HH:MM PM/AM" or "a las HH:MM"
    m_abs = re.search(r'a\s+las\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?', text, re.IGNORECASE)
    if m_abs:
        hour = int(m_abs.group(1))
        minute = int(m_abs.group(2)) if m_abs.group(2) else 0
        ampm = m_abs.group(3).lower() if m_abs.group(3) else None
        
        if ampm == "pm" and hour < 12:
            hour += 12
        elif ampm == "am" and hour == 12:
            hour = 0
            
        target_dt = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target_dt < now:
            target_dt += timedelta(days=1)
            
        reason = re.sub(r'a\s+las\s+\d{1,2}(?::\d{2})?\s*(am|pm)?', '', text, flags=re.IGNORECASE).strip()
        reason = re.sub(r'(me tengo que|tengo que|quiero que|me mandes|un mensaje|recordandome|recordarme|eso|por aca|por aquí|por aqui|hoy)', '', reason, flags=re.IGNORECASE).strip()
        reason = re.sub(r'^[\s,:\'\"]+|[\s,:\'\"]+$', '', reason).strip()
        return target_dt, reason.capitalize() if reason else "Recordatorio"

    return None, ""

class OutlookIntentParser:
    """Smart Natural Language Intent Parser and Executor for Outlook To-Do, Calendar, Mail, and Direct Telegram Reminders."""

    def __init__(self, outlook: OutlookIntegration):
        self.outlook = outlook

    def parse_and_execute(self, user_text: str, user_name: str = "Geral") -> Tuple[bool, Any]:
        """
        Parses natural language requests and executes real operations.
        Returns (handled: bool, response_data: str or tuple).
        """
        raw = user_text.strip()
        low = raw.lower()

        # 0. DIRECT TELEGRAM CHAT MESSAGE REMINDER (NO OUTLOOK, NO TO-DO)
        # Examples: "me tengo que tomar una pastilla hoy a las 3:47 PM quiero que me mandes un mensaje recordandome eso por aca"
        if any(w in low for w in ["mensaje", "por aca", "por aquí", "por aqui", "por chat", "por este chat"]) and any(w in low for w in ["recordando", "recuérdame", "recuerdame", "recordar", "pastilla", "alarma", "avísame", "avisame"]):
            target_dt, reason = parse_reminder_time(raw)
            if target_dt:
                now = datetime.now()
                delay_sec = max(1, int((target_dt - now).total_seconds()))
                time_fmt = target_dt.strftime("%H:%M")
                
                res_msg = (
                    f"⏰ **Recordatorio por Mensaje Programado**\n"
                    f"───────────────────────────\n"
                    f"📌 **Motivo**: {reason}\n"
                    f"⏰ **Hora programada**: `{time_fmt} hs`\n"
                    f"💬 **Canal**: Mensaje directo por este chat de Telegram.\n\n"
                    f"*(Se enviará únicamente como un mensaje directo por este chat)*\n\n"
                    f"💡 **¿Qué deseas hacer a continuación?**\n"
                    f"1. Si quieres ajustar la hora o cambiar el motivo, dime el nuevo horario.\n"
                    f"2. Si prefieres convertirlo también en evento de Outlook o tarea To-Do, avísame."
                )
                return True, (res_msg, delay_sec, reason)

        # 1. LIST CREATION
        if ("lista" in low and any(w in low for w in ["crees", "crear", "crea", "nueva", "hacer"])) and not ("tarea" in low and any(w in low for w in ["añade", "agrega", "a;ade", "pon"])):
            list_title = ""
            if ":" in raw and any(low.startswith(p) for p in ["crear lista:", "nueva lista:", "crea lista:"]):
                list_title = raw.split(":", 1)[1].strip()
            else:
                m = re.search(r'(?:crees|crear|crea|nueva|hacer)\s+(?:una\s+)?lista(?:\s+que\s+se\s+llame|\s+llamada|\s+titulada|\s+de)?[\s,:\'\"]+([^\'\"]+)', raw, re.IGNORECASE)
                if m:
                    list_title = m.group(1).strip()

            list_title = re.sub(r'[\'\"\\]+$', '', list_title).strip()
            if list_title:
                res = self.outlook.create_todo_list(list_title)
                next_opts = "\n\n💡 **Opciones a continuación:**\n1. Añadir tareas a esta nueva lista.\n2. Renombrar o reorganizar otras listas."
                return True, f"{res}{next_opts}"

        # 2. TASK CREATION WITH OPTIONAL TARGET LIST AND NOTE
        task_kw = any(w in low for w in ["añade una tarea", "a;ade una tarea", "añadir tarea", "a;adir tarea", "agrega una tarea", "agreges una tarea", "crea una tarea", "pon una tarea", "crear tarea:", "agendar tarea:"])
        if task_kw:
            title = ""
            list_name = None
            note = ""

            q_matches = re.findall(r'[\'\"]([^\'\"]+)[\'\"]', raw)
            if q_matches:
                title = q_matches[0]
                if len(q_matches) > 1 and any(w in low for w in ["nota", "descripción", "descripcion"]):
                    note = q_matches[1]

            if not title:
                if ":" in raw and (low.startswith("crear tarea:") or low.startswith("agendar tarea:")):
                    title = raw.split(":", 1)[1].strip()
                else:
                    tm = re.search(r'(?:tarea|llamada|titulada)\s+([^\n,]+)', raw, re.IGNORECASE)
                    if tm:
                        title = tm.group(1).strip()
                        title = re.split(r'\s+a\s+|\s+en\s+la\s+lista|\s+list\b', title, flags=re.IGNORECASE)[0].strip()

            lm = re.search(r'(?:a|en)\s+(?:la\s+lista\s+)?[\'\"]?([^\'\"]+?)[\'\"]?\s*(?:list|lista)\b', raw, re.IGNORECASE)
            if lm:
                cand = lm.group(1).strip()
                if cand.lower() not in ["que", "una", "la", "tarea"]:
                    list_name = cand
            elif "a " in low:
                lm2 = re.search(r'\ba\s+([A-ZÁÉÍÓÚa-záéíóú0-9\s]+?)\s+(?:list|lista|ponle|con|nota|$)', raw, re.IGNORECASE)
                if lm2:
                    cand2 = lm2.group(1).strip()
                    if cand2.lower() not in ["que", "una", "la", "tarea", "mi"]:
                        list_name = cand2

            if not note:
                nm = re.search(r'(?:nota|descripción|descripcion)\s*(?:que|:)?\s*[\'\"]?([^\'\"]+)[\'\"]?', raw, re.IGNORECASE)
                if nm:
                    note = nm.group(1).strip()

            title = re.sub(r'[\'\"\\]+$', '', title).strip()
            if title:
                res = self.outlook.create_task(title=title, description=note, list_name=list_name)
                next_opts = "\n\n💡 **Opciones a continuación:**\n1. Establecer fecha de vencimiento a la tarea.\n2. Agregar más tareas o subtareas."
                return True, f"{res}{next_opts}"

        # 3. LIST DELETION
        if ("lista" in low and any(w in low for w in ["elimina", "borra", "quitar", "remover"])) and not "subtarea" in low:
            list_name = ""
            if ":" in raw:
                list_name = raw.split(":", 1)[1].strip()
            else:
                m = re.search(r'(?:elimina|borra|quitar|remover)\s+(?:la\s+lista\s+)?[\'\"]?([^\'\"]+)[\'\"]?', raw, re.IGNORECASE)
                if m:
                    list_name = m.group(1).strip()
            
            list_name = re.sub(r'[\'\"\\]+$', '', list_name).strip()
            if list_name:
                res = self.outlook.delete_todo_list(list_name)
                next_opts = "\n\n💡 **Opciones a continuación:**\n1. Ver la lista actualizada de tus listas To-Do.\n2. Limpiar otras listas duplicadas."
                return True, f"{res}{next_opts}"

        # 4. SUBTASK DELETION
        if "subtarea" in low and any(w in low for w in ["elimina", "borra", "quitar", "remover"]):
            res_parts = []
            if "maxipali" in low:
                res_parts.append(self.outlook.delete_subtasks_from_list("Compras - MaxiPali"))
            if "colonia" in low:
                res_parts.append(self.outlook.delete_subtasks_from_list("Compras - Colonia"))
            if not res_parts:
                res_parts.append(self.outlook.delete_subtasks_from_list(raw))
            next_opts = "\n\n💡 **Opciones a continuación:**\n1. Ver tus tareas pendientes consolidadas.\n2. Agregar nuevos productos a tus compras."
            return True, "\n".join(res_parts) + next_opts

        # 5. DUPLICATE LIST CLEANUP & CONSOLIDATION
        if any(w in low for w in ["duplicada", "duplicadas", "consolida", "consolidar", "consolidation", "solo deberia haber una", "unificar", "fusionar"]):
            res = self.outlook.delete_duplicate_lists()
            next_opts = "\n\n💡 **Opciones a continuación:**\n1. Revisar las tareas dentro de la lista consolidada.\n2. Crear nuevas agrupaciones de listas."
            return True, f"{res}{next_opts}"

        # 6. RECURRING / ANNUAL CALENDAR QUERY
        if any(w in low for w in ["repetitivos", "recurrentes", "calendario anual", "eventos del año", "eventos de este año", "agenda anual"]):
            res = self.outlook.get_recurring_calendar_events(2026)
            next_opts = "\n\n💡 **Opciones a continuación:**\n1. Convertir eventos de pagos en tareas de To-Do con nomenclatura limpia.\n2. Eliminar eventos de calendario antiguos o duplicados."
            return True, f"{res}{next_opts}"

        # 7. CALENDAR EVENT DELETION
        if any(w in low for w in ["elimines los cumplea", "eliminar los cumplea", "borrar los cumplea", "elimina los cumplea", "elimina el evento", "eliminar evento", "borra el evento", "borrar evento"]):
            res = self.outlook.delete_calendar_event(raw)
            next_opts = "\n\n💡 **Opciones a continuación:**\n1. Consultar tu agenda de eventos actualizada.\n2. Programar nuevos recordatorios o tareas."
            return True, f"{res}{next_opts}"

        # 8. CALENDAR EVENT CREATION
        if any(w in low for w in ["agendar evento", "crear evento", "nuevo evento", "agenda un evento"]):
            event_title = ""
            if ":" in raw:
                event_title = raw.split(":", 1)[1].strip()
            else:
                m = re.search(r'(?:evento|reunión|reunion)\s+[\'\"]?([^\'\"]+)[\'\"]?', raw, re.IGNORECASE)
                if m:
                    event_title = m.group(1).strip()
                else:
                    event_title = raw

            res = self.outlook.create_event(event_title, raw)
            next_opts = "\n\n💡 **Opciones a continuación:**\n1. Ajustar el recordatorio previo (ej: 1 día antes).\n2. Agregar invitados o enlace de reunión de Teams."
            return True, f"{res}{next_opts}"

        return False, ""
