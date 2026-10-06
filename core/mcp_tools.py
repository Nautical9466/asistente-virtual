import json
import logging
from typing import Dict, Any, List
from integrations.outlook import OutlookIntegration

logger = logging.getLogger(__name__)

class MCPToolRegistry:
    """Model Context Protocol (MCP) Tool Registry and Execution Engine for Claudia OS."""

    def __init__(self):
        self.outlook = OutlookIntegration()

    def get_tools_schema(self) -> List[Dict[str, Any]]:
        """Returns standard MCP/OpenAI-compatible tool definitions."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "create_outlook_task",
                    "description": "Crea una nueva tarea en Outlook To-Do / Microsoft Tasks en una lista específica con nota opcional.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "Título claro de la tarea"},
                            "description": {"type": "string", "description": "Nota o descripción adicional de la tarea"},
                            "list_name": {"type": "string", "description": "Nombre de la lista objetivo (ej: Compras, Trabajo, Tareas por la noche)"}
                        },
                        "required": ["title"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "delete_outlook_task",
                    "description": "Elimina permanentemente una o varias tareas de Outlook To-Do por título o por número de tarea y número de lista (ej: tareas 1 y 2 de la lista 1).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task_query": {"type": "string", "description": "Título de la tarea o números de tarea (ej: '1 y 2', 'la quiero creada', '7 8 9')"},
                            "list_name_or_number": {"type": "string", "description": "Nombre de la lista o número de la lista (ej: '1', 'Tareas', '8', 'Gorditas')"}
                        },
                        "required": ["task_query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "complete_outlook_task",
                    "description": "Marca una o varias tareas pendientes como completadas en Outlook To-Do por título o por número de tarea y lista.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task_query": {"type": "string", "description": "Título de la tarea o números (ej: '1', 'Revisar precios')"},
                            "list_name_or_number": {"type": "string", "description": "Nombre o número de la lista (ej: '1', 'Tareas')"}
                        },
                        "required": ["task_query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "move_outlook_task",
                    "description": "Mueve una o varias tareas a otra lista en Outlook To-Do.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task_query": {"type": "string", "description": "Título de la tarea o número (ej: '3' o 'Revisar precios de Dry-Clean')"},
                            "destination_list_name": {"type": "string", "description": "Nombre de la lista destino (ej: 'Tareas por la noche')"},
                            "src_list_name_or_number": {"type": "string", "description": "Nombre o número de la lista origen"}
                        },
                        "required": ["task_query", "destination_list_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_outlook_tasks",
                    "description": "Obtiene la lista completa de tareas pendientes detalladas en todas las listas de Outlook To-Do.",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "create_calendar_event",
                    "description": "Agenda un evento o reunión en el Calendario de Outlook con personalización completa (Teams, etiquetas/categorías, invitados, recordatorios).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "Título claro del evento o reunión"},
                            "date_str": {"type": "string", "description": "Fecha y hora objetivo (ej: Hoy 16:00, Mañana 15:00, 2026-10-10 10:00)"},
                            "time_str": {"type": "string", "description": "Alias para fecha y hora objetivo"},
                            "duration_minutes": {"type": "integer", "description": "Duración en minutos (default 60)"},
                            "is_teams_meeting": {"type": "boolean", "description": "Si debe incluir enlace a reunión de Microsoft Teams (default false)"},
                            "categories": {"type": "array", "items": {"type": "string"}, "description": "Lista de etiquetas o categorías de color (ej: ['Trabajo', 'Importante'])"},
                            "attendees": {"type": "array", "items": {"type": "string"}, "description": "Lista de correos de invitados"},
                            "description": {"type": "string", "description": "Detalles o notas del evento"}
                        },
                        "required": ["title"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_calendar_events",
                    "description": "Obtiene la agenda de eventos del usuario en Outlook Calendar para los próximos días.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "days_ahead": {"type": "integer", "description": "Días a consultar hacia adelante (default 14)"}
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "send_email",
                    "description": "Envía un correo electrónico a través de Microsoft Outlook.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "recipient": {"type": "string", "description": "Dirección de correo del destinatario"},
                            "subject": {"type": "string", "description": "Asunto del correo"},
                            "body_content": {"type": "string", "description": "Cuerpo del correo"}
                        },
                        "required": ["recipient", "subject", "body_content"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "manage_todo_lists",
                    "description": "Crea, elimina o consolida listas duplicadas en Outlook To-Do.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "action": {"type": "string", "enum": ["create", "delete", "consolidate_duplicates"], "description": "Acción a realizar"},
                            "list_name": {"type": "string", "description": "Nombre de la lista (requerido para create y delete)"}
                        },
                        "required": ["action"]
                    }
                }
            }
        ]

    def execute_tool(self, name: str, args: Dict[str, Any]) -> str:
        """Executes the specified tool and returns formatted output."""
        try:
            if name == "create_outlook_task":
                return self.outlook.create_task(
                    title=args.get("title", ""),
                    description=args.get("description", ""),
                    list_name=args.get("list_name")
                )
            elif name == "delete_outlook_task":
                return self.outlook.delete_task(
                    task_input=args.get("task_query", ""),
                    list_name_or_number=args.get("list_name_or_number")
                )
            elif name == "complete_outlook_task":
                return self.outlook.complete_task(
                    task_input=args.get("task_query", ""),
                    list_name_or_number=args.get("list_name_or_number")
                )
            elif name == "move_outlook_task":
                return self.outlook.move_task(
                    task_input=args.get("task_query", ""),
                    destination_list_name=args.get("destination_list_name", "")
                )
            elif name == "get_outlook_tasks":
                include_details = args.get("include_details", False)
                if include_details:
                    return self.outlook.get_tasks()
                else:
                    return self.outlook.get_all_lists_grouped()
            elif name == "create_calendar_event":
                date_val = args.get("date_str") or args.get("time_str") or args.get("timestr") or args.get("time") or "Hoy 16:00"
                return self.outlook.create_event(
                    title=args.get("title", ""),
                    date_str=date_val,
                    duration_minutes=args.get("duration_minutes", 60),
                    reminder_minutes=args.get("reminder_minutes", 1440),
                    is_teams_meeting=args.get("is_teams_meeting", False),
                    attendees=args.get("attendees", None),
                    categories=args.get("categories", None),
                    description=args.get("description", ""),
                    auto_find_best_time=args.get("auto_find_best_time", False)
                )
            elif name == "get_calendar_events":
                return self.outlook.get_calendar_events(
                    days_ahead=args.get("days_ahead", 14)
                )
            elif name == "send_email":
                return self.outlook.send_email(
                    recipient=args.get("recipient", ""),
                    subject=args.get("subject", ""),
                    body_content=args.get("body_content", "")
                )
            elif name == "manage_todo_lists":
                action = args.get("action")
                list_name = args.get("list_name", "")
                if action == "create":
                    return self.outlook.create_todo_list(list_name)
                elif action == "delete":
                    return self.outlook.delete_todo_list(list_name)
                elif action == "consolidate_duplicates":
                    return self.outlook.delete_duplicate_lists()
                else:
                    return f"❌ Acción '{action}' no soportada."
            else:
                return f"❌ Herramienta '{name}' no reconocida."
        except Exception as e:
            logger.error(f"[MCP Tool Execution Error] {name}: {e}")
            return f"❌ Error ejecutando herramienta {name}: {e}"

mcp_registry = MCPToolRegistry()
