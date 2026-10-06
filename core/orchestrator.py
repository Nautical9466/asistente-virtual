import os
import json
import logging
from typing import Dict, Any, List, Optional
import litellm
from core.mcp_tools import mcp_registry
from core.context_loader import ContextLoader

logger = logging.getLogger("Orchestrator")

class GoalOrchestrator:
    """Multi-Goal Orchestrator & Natural Language Task Planner for Claudia OS (N8N-style execution pipeline)."""

    def __init__(self):
        self.context_loader = ContextLoader()

    def process_request(self, user_input: str, user_id: str = "default", origin_metadata: Optional[Dict[str, Any]] = None) -> str:
        """Central pipeline:
        1. Context & Metadata Parser
        2. LLM Goal Classifier (Pure LLM natural language intent extraction)
        3. Orchestrated MCP Tool Execution Loop
        4. Evaluator & Closing Summarizer
        """
        if origin_metadata is None:
            origin_metadata = {}

        chat_type = origin_metadata.get("chat_type", "private")
        chat_title = origin_metadata.get("chat_title", "Chat Directo")

        # 1. Classify & Decompose Request into Structured Goals via LLM Reasoning
        classification = self._classify_and_decompose(user_input, chat_type, chat_title)

        goals = classification.get("goals", [])
        if not goals:
            goals = [{
                "goal_id": 1,
                "priority": 1,
                "intent_name": "general_query",
                "target_tool": "general_query",
                "action_summary": "Responder consulta conversacional general",
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
        """Node 1: Pure LLM reasoning engine to decompose any natural language input into structured goals JSON."""
        system_prompt = (
            "Eres el Orquestador Inteligente y Analista de Lenguaje Natural de Claudia OS / Jarvis.\n"
            "Tu tarea es analizar la intención del usuario entendiendo su lenguaje natural (incluso con modismos, frases casuales o peticiones múltiples) "
            "y mapearla a las herramientas MCP adecuadas en un JSON ESTRUCTURADO.\n\n"
            "HERRAMIENTAS MCP DISPONIBLES:\n"
            "- get_calendar_events (para consultar la agenda, eventos programados, citas, fechas del mes/semana)\n"
            "- create_calendar_event (title, time_str, duration_minutes, description)\n"
            "- get_outlook_tasks (para consultar pendientes, tareas activas, listas de tareas, compromisos)\n"
            "- create_outlook_task (title, description, list_name)\n"
            "- complete_outlook_task (task_query, list_name_or_number)\n"
            "- delete_outlook_task (task_query, list_name_or_number)\n"
            "- move_outlook_task (task_query, destination_list_name, src_list_name_or_number)\n"
            "- manage_todo_lists (action: create/delete/consolidate_duplicates, list_name)\n"
            "- send_email (recipient, subject, body_content)\n"
            "- general_query (para saludos simples como 'hola', preguntas generales, investigación o conversación habitual)\n\n"
            "REGLAS DE CLASIFICACIÓN LINGÜÍSTICA:\n"
            "1. Si el usuario realiza un saludo simple o conversación general (ej: 'hola', 'buenos días', 'quién eres'), asigna target_tool: general_query.\n"
            "2. Si el mensaje contiene múltiples intenciones (ej: pedir la agenda Y pedir las tareas pendientes), DEBES crear un elemento independiente en 'goals' para CADA INTENCIÓN.\n"
            "3. Responde ÚNICAMENTE con un JSON plano estructurado válido."
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

        def _valid_json(content: str) -> Optional[Dict[str, Any]]:
            try:
                data = json.loads(content)
                if isinstance(data, dict) and "goals" in data and isinstance(data["goals"], list) and len(data["goals"]) > 0:
                    return data
            except Exception:
                pass
            return None

        # 1. Try DeepInfra FIRST (unlimited capacity, high speed Llama-3.3 70B)
        if os.environ.get("DEEPINFRA_API_KEY"):
            try:
                resp = litellm.completion(
                    model="deepinfra/meta-llama/Llama-3.3-70B-Instruct",
                    messages=messages,
                    api_key=os.environ.get("DEEPINFRA_API_KEY"),
                    response_format={"type": "json_object"}
                )
                if resp and resp.choices and resp.choices[0].message.content:
                    parsed = _valid_json(resp.choices[0].message.content)
                    if parsed:
                        return parsed
            except Exception as e:
                logger.warning(f"[Orchestrator Classifier DeepInfra Warning]: {e}")

        # 2. Try Groq
        if os.environ.get("GROQ_API_KEY"):
            try:
                resp = litellm.completion(
                    model="groq/openai/gpt-oss-20b",
                    messages=messages,
                    api_key=os.environ.get("GROQ_API_KEY"),
                    response_format={"type": "json_object"}
                )
                if resp and resp.choices and resp.choices[0].message.content:
                    parsed = _valid_json(resp.choices[0].message.content)
                    if parsed:
                        return parsed
            except Exception as e:
                logger.warning(f"[Orchestrator Classifier Groq Warning]: {e}")

        # 3. Try Gemini
        if os.environ.get("GEMINI_API_KEY"):
            try:
                resp = litellm.completion(
                    model="gemini/gemini-3.8-flash",
                    messages=messages,
                    api_key=os.environ.get("GEMINI_API_KEY"),
                    response_format={"type": "json_object"}
                )
                if resp and resp.choices and resp.choices[0].message.content:
                    parsed = _valid_json(resp.choices[0].message.content)
                    if parsed:
                        return parsed
            except Exception as ex:
                logger.warning(f"[Orchestrator Classifier Gemini Warning]: {ex}")

        # 4. Fallback default goal if all API classification calls failed
        return {
            "has_multiple_goals": False,
            "total_goals": 1,
            "goals": [{
                "goal_id": 1,
                "priority": 1,
                "intent_name": "general_query",
                "target_tool": "general_query",
                "action_summary": "Responder consulta conversacional",
                "parameters": {"query": user_input}
            }]
        }

    def _execute_general_query(self, query: str, user_id: str) -> str:
        """Executes general conversational query via Assistant engine."""
        from core.router import assistant
        return assistant.direct_llm_query(query, user_id)

    def _evaluate_and_summarize(self, user_input: str, execution_results: List[Dict[str, Any]], chat_type: str, chat_title: str, total_goals: int) -> str:
        """Node 3: Evaluates completion of all goals and formats Telegram output."""
        from core.router import clean_markdown_formatting
        formatted_outputs = []

        for item in execution_results:
            res = item.get("result", "").strip()
            if res:
                cleaned_res = clean_markdown_formatting(res)
                formatted_outputs.append(cleaned_res)

        final_text = "\n\n---TOPIC_BREAK---\n\n".join(formatted_outputs)
        return final_text

orchestrator = GoalOrchestrator()
