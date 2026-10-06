import os
import yaml
import logging
from datetime import datetime
from core.memory import MemoryManager
from core.context_loader import ContextLoader

logger = logging.getLogger(__name__)

class VirtualAssistant:
    """Core Virtual Assistant engine with robust multi-model LiteLLM routing & fallbacks."""

    def __init__(self, config_path="config/litellm_config.yaml", data_file="data/context.json"):
        self.config_path = config_path
        self.memory = MemoryManager(data_file=data_file)
        self.context_loader = ContextLoader()
        self.router = None
        self._setup_router()

    def _setup_router(self):
        """Initializes LiteLLM Router if available and configured."""
        try:
            import litellm
            from litellm import Router

            has_keys = any(os.environ.get(k) for k in ["GROQ_API_KEY", "GEMINI_API_KEY", "DEEPINFRA_API_KEY"])

            if os.path.exists(self.config_path) and has_keys:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    config = yaml.safe_load(f)
                model_list = config.get("model_list", [])
                self.router = Router(model_list=model_list)
                logger.info("[VirtualAssistant] LiteLLM Router initialized successfully.")
            else:
                logger.warning("[VirtualAssistant] No LLM API keys found or config missing.")
        except Exception as e:
            logger.warning(f"[VirtualAssistant] LiteLLM Router initialization warning: {e}")
            self.router = None

    def query(self, user_input: str, user_id: str = "default", model: str = "cerebro-groq", system_prompt: str = None) -> str:
        """Processes a query through LLMs with MCP Tool execution and multi-provider fallbacks."""
        from core.mcp_tools import mcp_registry

        full_system_prompt = self.context_loader.get_full_system_prompt(system_prompt)

        # Inject real-time Outlook context for task/list/calendar/agenda queries
        low = user_input.lower()
        if any(w in low for w in ["tarea", "tareas", "lista", "listas", "todo", "outlook", "cerrad", "completad", "pendiente", "mover", "analiz", "agenda", "evento", "eventos", "calendario", "semana", "reunion", "reunión"]):
            try:
                from integrations.outlook import OutlookIntegration
                outlook_ctx = OutlookIntegration().get_full_context_for_llm()
                full_system_prompt += f"\n\n{outlook_ctx}"
            except Exception as e:
                logger.warning(f"[Router] Outlook context injection failed: {e}")

        history = self.memory.get_history(user_id)

        messages = [{"role": "system", "content": full_system_prompt}]
        for item in history:
            messages.append({"role": item["role"], "content": item["content"]})
        messages.append({"role": "user", "content": user_input})

        tools_schema = mcp_registry.get_tools_schema()
        assistant_response = None
        import litellm
        import json

        def extract_response(response) -> str:
            if not response or not response.choices:
                return None
            msg = response.choices[0].message
            # Check for tool call execution
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                tool_results = []
                for tool_call in msg.tool_calls:
                    fn_name = tool_call.function.name
                    try:
                        fn_args = json.loads(tool_call.function.arguments or "{}")
                    except Exception:
                        fn_args = {}
                    logger.info(f"🛠️ [MCP Tool Call] Invoking tool '{fn_name}' with args {fn_args}")
                    tool_res = mcp_registry.execute_tool(fn_name, fn_args)
                    tool_results.append(tool_res)
                return "\n\n".join(tool_results)
            return msg.content

        # 1. Try LiteLLM Router
        if self.router:
            try:
                response = self.router.completion(
                    model=model,
                    messages=messages,
                    tools=tools_schema,
                    temperature=0.15
                )
                assistant_response = extract_response(response)
            except Exception as e:
                logger.warning(f"[VirtualAssistant] Router tool completion warning: {e}")

        # 2. Try direct Groq completion fallback
        if not assistant_response and os.environ.get("GROQ_API_KEY"):
            try:
                groq_key = os.environ.get("GROQ_API_KEY")
                resp = litellm.completion(
                    model="groq/llama-3.3-70b-versatile",
                    messages=messages,
                    tools=tools_schema,
                    api_key=groq_key
                )
                assistant_response = extract_response(resp)
                logger.info("✅ Direct Groq completion succeeded.")
            except Exception as e:
                logger.warning(f"[VirtualAssistant] Groq fallback warning: {e}")

        # 3. Try direct Gemini completion fallback
        if not assistant_response and os.environ.get("GEMINI_API_KEY"):
            try:
                gemini_key = os.environ.get("GEMINI_API_KEY")
                resp = litellm.completion(
                    model="gemini/gemini-3.8-flash",
                    messages=messages,
                    tools=tools_schema,
                    api_key=gemini_key
                )
                assistant_response = extract_response(resp)
                logger.info("✅ Direct Gemini completion succeeded.")
            except Exception as e:
                logger.warning(f"[VirtualAssistant] Gemini fallback warning: {e}")

        # 4. Standard completion without tools if tool completion returned empty
        if not assistant_response and os.environ.get("GEMINI_API_KEY"):
            try:
                gemini_key = os.environ.get("GEMINI_API_KEY")
                resp = litellm.completion(
                    model="gemini/gemini-3.8-flash",
                    messages=messages,
                    api_key=gemini_key
                )
                assistant_response = resp.choices[0].message.content
            except Exception as e:
                logger.error(f"[VirtualAssistant] Standard fallback failed: {e}")

        # 5. Local fallback if all API calls failed
        if not assistant_response:
            assistant_response = self._generate_local_fallback(user_input)

        if assistant_response:
            assistant_response = clean_markdown_formatting(assistant_response)

        self.memory.add_interaction(user_id, user_input, assistant_response)
        return assistant_response

    def _generate_local_fallback(self, user_input: str) -> str:
        """Generates structured local response when API key is unconfigured or failing."""
        return (
            "🤖 **Modo Asistente Virtual Local**\n\n"
            f"He recibido tu mensaje: *\"{user_input}\"*\n\n"
            "💡 *Nota de Conexión*: Las API keys están configuradas en Render, pero los servidores de los proveedores (Groq/Gemini/DeepInfra) no pudieron completar la respuesta.\n"
            "Verifica que tu `GROQ_API_KEY` (empieza con `gsk_...`) o `GEMINI_API_KEY` (empieza con `AIzaSy...`) estén activas."
        )

def clean_markdown_formatting(text: str) -> str:
    """Post-processor that cleans Telegram-incompatible Markdown (headings #, pipe tables)."""
    if not text:
        return text

    import re
    lines = text.split('\n')
    new_lines = []
    in_table = False
    headers = []

    for line in lines:
        stripped = line.strip()
        # 1. Clean Markdown headings (# ## ### ####) into bold text for Telegram
        if stripped.startswith('#'):
            h_clean = re.sub(r'^#+\s*', '', stripped).strip()
            new_lines.append(f"📌 **{h_clean}**")
            continue

        # 2. Clean pipe tables (| col | col |)
        if stripped.startswith('|') and stripped.endswith('|'):
            if re.match(r'^\|[\s:\-|\-]+\|$', stripped):
                in_table = True
                continue
            cells = [c.strip() for c in stripped.strip('|').split('|')]
            if not in_table and not headers:
                headers = cells
                in_table = True
                continue
            if headers:
                new_lines.append(f"\n📌 **{cells[0]}**:")
                for h, val in zip(headers[1:], cells[1:]):
                    if val and val != '-':
                        new_lines.append(f"  • **{h}**: {val}")
            else:
                new_lines.append(f"• {', '.join(cells)}")
        else:
            if in_table:
                in_table = False
                headers = []
            new_lines.append(line)

    return '\n'.join(new_lines)

# Global singleton instance
assistant = VirtualAssistant()
