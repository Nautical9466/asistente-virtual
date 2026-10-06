import os
import json
import logging
from typing import Dict, Any, List, Optional
import litellm
from core.mcp_tools import mcp_registry
from core.context_loader import ContextLoader

logger = logging.getLogger("Orchestrator")

class GoalOrchestrator:
    """Multi-Goal Orchestrator & Task Planner for Claudia OS (N8N-style execution pipeline)."""

    def __init__(self):
        self.context_loader = ContextLoader()

    def process_request(self, user_input: str, user_id: str = "default", origin_metadata: Optional[Dict[str, Any]] = None) -> str:
        """Central pipeline:
        1. Context & Metadata Parser
        2. Classifier LLM (Extract goals, tool mappings, parameters, priority)
        3. Orchestrated MCP Tool Execution Loop
        4. Evaluator & Closing Summarizer LLM
        """
        if origin_metadata is None:
            origin_metadata = {}

        chat_type = origin_metadata.get("chat_type", "private")
        chat_title = origin_metadata.get("chat_title", "Chat Directo")

        # 1. Classify & Decompose Request into Structured Goals
        classification = self._classify_and_decompose(user_input, chat_type, chat_title)

        goals = classification.get("goals", [])
        if not goals:
            goals = [{
                "goal_id": 1,
                "priority": 1,
                "intent_name": "general_query",
                "target_tool": "general_query",
                "action_summary": "Responder consulta general",
                "parameters": {"query": user_input}
            }]

        # 2. Execute each goal in order of priority
        execution_results = []
        for goal in sorted(goals, key=lambda x: x.get("priority", 1)):
            tool_name = goal.get("target_tool", "general_query")
            params = goal.get("parameters", {})
            action_summary = goal.get("action_summary", "")

            logger.info(f"🎯 [Orchestrator Goal #{goal.get('goal_id')}] Tool: {tool_name} | Params: {params}")

            if tool_name == "general_query":
                res = self._execute_general_query(params.get("query", user_input), user_id)
            else:
                try:
                    res = mcp_registry.execute_tool(tool_name, params)
                except Exception as e:
                    logger.error(f"[Orchestrator Execution Error] Goal #{goal.get('goal_id')} ({tool_name}): {e}")
                    res = f"❌ Error al ejecutar {action_summary}: {e}"

            execution_results.append({
                "goal_id": goal.get("goal_id", 1),
                "intent_name": goal.get("intent_name", ""),
                "action_summary": action_summary,
                "tool_name": tool_name,
                "result": res
            })

        # 3. Verify & Synthesize final summary
        total_goals = len(execution_results)
        final_response = self._evaluate_and_summarize(user_input, execution_results, chat_type, chat_title, total_goals)

        return final_response

    def _classify_and_decompose(self, user_input: str, chat_type: str, chat_title: str) -> Dict[str, Any]:
        """Node 1: Uses LLM to decompose input into structured goals JSON."""
        system_prompt = (
            "Eres el Orquestador Inteligente y Clasificador de Metas de Claudia OS.\n"
            "Tu único trabajo es analizar el mensaje del usuario y sus metadatos de origen (chat privado, grupo o canal) "
            "y devolver un JSON ESTRUCTURADO con las metas/solicitudes identificadas, ordenadas por prioridad de ejecución.\n\n"
            "HERRAMIENTAS MCP DISPONIBLES:\n"
            "- get_calendar_events (días a consultar, default 14 o 30)\n"
            "- create_calendar_event (title, time_str, duration_minutes, description)\n"
            "- get_outlook_tasks (obtiene todas las tareas pendientes agrupadas por lista)\n"
            "- create_outlook_task (title, description, list_name)\n"
            "- complete_outlook_task (task_query, list_name_or_number)\n"
            "- delete_outlook_task (task_query, list_name_or_number)\n"
            "- move_outlook_task (task_query, destination_list_name, src_list_name_or_number)\n"
            "- manage_todo_lists (action: create/delete/consolidate_duplicates, list_name)\n"
            "- send_email (recipient, subject, body_content)\n"
            "- general_query (para responder preguntas, conversar, investigar o redactar textos)\n\n"
            "REGLAS ESTRUCTURALES:\n"
            "1. Si el usuario pide varias cosas en un mismo mensaje (ej: 'dame la agenda y borra la tarea 2 de la lista 1'), DEBES crear un objeto independiente en la lista 'goals' para CADA SOLICITUD.\n"
            "2. Asigna 'priority': 1 al objetivo más urgente/primario, 'priority': 2 al siguiente, etc.\n"
            "3. Responde ÚNICAMENTE en formato JSON plano válido con la clave principal 'goals'."
        )

        user_prompt = (
            f"METADATOS DE ORIGEN:\n"
            f"- Tipo de Chat: {chat_type}\n"
            f"- Nombre del Grupo/Canal: {chat_title}\n\n"
            f"MENSAJE DEL USUARIO:\n\"{user_input}\"\n\n"
            "Devuelve el JSON con la estructura exacta:\n"
            "{\n"
            "  \"has_multiple_goals\": true,\n"
            "  \"total_goals\": 2,\n"
            "  \"goals\": [\n"
            "    {\n"
            "      \"goal_id\": 1,\n"
            "      \"priority\": 1,\n"
            "      \"intent_name\": \"...\",\n"
            "      \"target_tool\": \"get_calendar_events\",\n"
            "      \"action_summary\": \"Obtener agenda\",\n"
            "      \"parameters\": { \"days_ahead\": 30 }\n"
            "    }\n"
            "  ]\n"
            "}"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        from core.router import assistant
        if assistant.router:
            try:
                resp = assistant.router.completion(
                    model="cerebro-groq",
                    messages=messages,
                    response_format={"type": "json_object"}
                )
                content = resp.choices[0].message.content
                return json.loads(content)
            except Exception as e:
                logger.warning(f"[Orchestrator Classifier Router Warning]: {e}")

        try:
            resp = litellm.completion(
                model="groq/openai/gpt-oss-20b",
                messages=messages,
                api_key=os.environ.get("GROQ_API_KEY"),
                response_format={"type": "json_object"}
            )
            content = resp.choices[0].message.content
            return json.loads(content)
        except Exception as e:
            logger.warning(f"[Orchestrator Classifier Fallback] Groq JSON failed: {e}. Trying Gemini...")
            try:
                resp = litellm.completion(
                    model="gemini/gemini-3.8-flash",
                    messages=messages,
                    api_key=os.environ.get("GEMINI_API_KEY"),
                    response_format={"type": "json_object"}
                )
                content = resp.choices[0].message.content
                return json.loads(content)
            except Exception as ex:
                logger.error(f"[Orchestrator Classifier Error]: {ex}")
                return self._fallback_heuristic_classifier(user_input)

    def _fallback_heuristic_classifier(self, user_input: str) -> Dict[str, Any]:
        """Heuristic fallback when JSON LLM classification is unavailable."""
        low = user_input.lower()
        goals = []
        gid = 1

        if any(w in low for w in ["agenda", "calendario", "evento", "reunión"]):
            goals.append({
                "goal_id": gid,
                "priority": gid,
                "intent_name": "consultar_agenda",
                "target_tool": "get_calendar_events",
                "action_summary": "Consultar eventos del calendario",
                "parameters": {"days_ahead": 30}
            })
            gid += 1

        if any(w in low for w in ["tarea", "tareas", "lista", "listas", "todo"]):
            if any(w in low for w in ["elimin", "borra"]):
                goals.append({
                    "goal_id": gid,
                    "priority": gid,
                    "intent_name": "eliminar_tarea",
                    "target_tool": "delete_outlook_task",
                    "action_summary": "Eliminar tareas en Outlook To-Do",
                    "parameters": {"task_query": user_input}
                })
            elif any(w in low for w in ["complet", "cerr", "hech"]):
                goals.append({
                    "goal_id": gid,
                    "priority": gid,
                    "intent_name": "completar_tarea",
                    "target_tool": "complete_outlook_task",
                    "action_summary": "Completar tareas en Outlook To-Do",
                    "parameters": {"task_query": user_input}
                })
            else:
                goals.append({
                    "goal_id": gid,
                    "priority": gid,
                    "intent_name": "consultar_tareas",
                    "target_tool": "get_outlook_tasks",
                    "action_summary": "Consultar todas las tareas por lista",
                    "parameters": {}
                })
            gid += 1

        if not goals:
            goals.append({
                "goal_id": 1,
                "priority": 1,
                "intent_name": "consulta_general",
                "target_tool": "general_query",
                "action_summary": "Responder consulta general",
                "parameters": {"query": user_input}
            })

        return {
            "has_multiple_goals": len(goals) > 1,
            "total_goals": len(goals),
            "goals": goals
        }

    def _execute_general_query(self, query: str, user_id: str) -> str:
        """Executes general conversational query via Assistant engine."""
        from core.router import assistant
        return assistant.direct_llm_query(query, user_id)

    def _evaluate_and_summarize(self, user_input: str, execution_results: List[Dict[str, Any]], chat_type: str, chat_title: str, total_goals: int) -> str:
        """Node 3: Evaluates completion of all goals and formats Telegram output."""
        formatted_outputs = []
        for item in execution_results:
            formatted_outputs.append(item.get("result", ""))

        combined_text = "\n\n".join(formatted_outputs)

        # Custom closing phrase requested by user:
        if total_goals == 1:
            closing_phrase = "\n\n✨ *Se ha completado la tarea solicitada.*"
        elif total_goals == 2:
            closing_phrase = "\n\n✨ *Se han completado las dos tareas solicitadas.*"
        else:
            closing_phrase = f"\n\n✨ *Se han completado las {total_goals} tareas solicitadas.*"

        from core.router import clean_markdown_formatting
        final_text = clean_markdown_formatting(combined_text + closing_phrase)
        return final_text

orchestrator = GoalOrchestrator()
