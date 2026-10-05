import re
import json
import logging
from typing import Tuple, Optional
from integrations.outlook import OutlookIntegration

logger = logging.getLogger(__name__)

class OutlookIntentParser:
    """Smart Natural Language Intent Parser and Executor for Outlook To-Do, Calendar, and Mail."""

    def __init__(self, outlook: OutlookIntegration):
        self.outlook = outlook

    def parse_and_execute(self, user_text: str, user_name: str = "Geral") -> Tuple[bool, str]:
        """
        Parses natural language requests and executes real Outlook Graph API operations.
        Returns (handled: bool, response_text: str).
        """
        raw = user_text.strip()
        low = raw.lower()

        # 1. LIST CREATION
        # Examples: "quiero que crees una lista que se llame 'Tareas por la noche'", "crear lista: Casa", "nueva lista Compras"
        if ("lista" in low and any(w in low for w in ["crees", "crear", "crea", "nueva", "hacer"])) and not ("tarea" in low and any(w in low for w in ["añade", "agrega", "a;ade", "pon"])):
            list_title = ""
            if ":" in raw and any(low.startswith(p) for p in ["crear lista:", "nueva lista:", "crea lista:"]):
                list_title = raw.split(":", 1)[1].strip()
            else:
                m = re.search(r'(?:crees|crear|crea|nueva|hacer)\s+(?:una\s+)?lista(?:\s+que\s+se\s+llame|\s+llamada|\s+titulada|\s+de)?[\s,:\'\"]+([^\'\"]+)', raw, re.IGNORECASE)
                if m:
                    list_title = m.group(1).strip()

            # Clean trailing quotes/escapes
            list_title = re.sub(r'[\'\"\\]+$', '', list_title).strip()
            if list_title:
                res = self.outlook.create_todo_list(list_title)
                return True, f"Con mucho gusto, {user_name}.\n\n{res}"

        # 2. TASK CREATION WITH OPTIONAL TARGET LIST AND NOTE
        # Examples: "a;ade una tarea llamada 'Comprar el telefono de Rouse' a Tareas por la noche list ponle como nota 'Ir al maxipali'", "crear tarea: Comprar pan"
        task_kw = any(w in low for w in ["añade una tarea", "a;ade una tarea", "añadir tarea", "a;adir tarea", "agrega una tarea", "agreges una tarea", "crea una tarea", "pon una tarea", "crear tarea:", "agendar tarea:"])
        if task_kw:
            title = ""
            list_name = None
            note = ""

            # Check quotes first
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

            # Extract list name
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

            # Extract note if not extracted from quotes
            if not note:
                nm = re.search(r'(?:nota|descripción|descripcion)\s*(?:que|:)?\s*[\'\"]?([^\'\"]+)[\'\"]?', raw, re.IGNORECASE)
                if nm:
                    note = nm.group(1).strip()

            title = re.sub(r'[\'\"\\]+$', '', title).strip()
            if title:
                res = self.outlook.create_task(title=title, description=note, list_name=list_name)
                return True, f"Con mucho gusto, {user_name}.\n\n{res}"

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
                return True, f"Claro que sí, {user_name}.\n\n{res}"

        # 4. SUBTASK DELETION
        if "subtarea" in low and any(w in low for w in ["elimina", "borra", "quitar", "remover"]):
            res_parts = []
            if "maxipali" in low:
                res_parts.append(self.outlook.delete_subtasks_from_list("Compras - MaxiPali"))
            if "colonia" in low:
                res_parts.append(self.outlook.delete_subtasks_from_list("Compras - Colonia"))
            if not res_parts:
                res_parts.append(self.outlook.delete_subtasks_from_list(raw))
            return True, f"Claro que sí, {user_name}.\n\n" + "\n".join(res_parts)

        # 5. DUPLICATE LIST CLEANUP & CONSOLIDATION
        if any(w in low for w in ["duplicada", "duplicadas", "consolida", "consolidar", "consolidation", "solo deberia haber una", "unificar", "fusionar"]):
            res = self.outlook.delete_duplicate_lists()
            return True, f"Por supuesto, {user_name}.\n\n{res}"

        # 6. RECURRING / ANNUAL CALENDAR QUERY
        if any(w in low for w in ["repetitivos", "recurrentes", "calendario anual", "eventos del año", "eventos de este año", "agenda anual"]):
            res = self.outlook.get_recurring_calendar_events(2026)
            return True, f"Con mucho gusto, {user_name}.\n\n{res}"

        # 7. CALENDAR EVENT DELETION
        if any(w in low for w in ["elimines los cumplea", "eliminar los cumplea", "borrar los cumplea", "elimina los cumplea", "elimina el evento", "eliminar evento", "borra el evento", "borrar evento"]):
            res = self.outlook.delete_calendar_event(raw)
            return True, f"Con mucho gusto, {user_name}.\n\n{res}"

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
            return True, f"Claro que sí, {user_name}.\n\n{res}"

        return False, ""
