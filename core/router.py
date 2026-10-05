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
        """Processes a query through LiteLLM across Groq, Gemini, and DeepInfra with fallbacks."""
        full_system_prompt = self.context_loader.get_full_system_prompt(system_prompt)
        history = self.memory.get_history(user_id)

        messages = [{"role": "system", "content": full_system_prompt}]
        for item in history:
            messages.append({"role": item["role"], "content": item["content"]})
        messages.append({"role": "user", "content": user_input})

        assistant_response = None
        import litellm

        # 1. Try Router
        if self.router:
            try:
                response = self.router.completion(
                    model=model,
                    messages=messages,
                    temperature=0.15
                )
                assistant_response = response.choices[0].message.content
            except Exception as e:
                logger.error(f"[VirtualAssistant] Router error with model {model}: {e}")

        # 2. Try direct Groq completion fallback
        if not assistant_response and os.environ.get("GROQ_API_KEY"):
            try:
                groq_key = os.environ.get("GROQ_API_KEY")
                resp = litellm.completion(
                    model="groq/openai/gpt-oss-20b",
                    messages=messages,
                    api_key=groq_key
                )
                assistant_response = resp.choices[0].message.content
                logger.info("✅ Direct Groq completion succeeded.")
            except Exception as e:
                logger.error(f"[VirtualAssistant] Groq fallback failed: {e}")

        # 3. Try direct Gemini completion fallback
        if not assistant_response and os.environ.get("GEMINI_API_KEY"):
            try:
                gemini_key = os.environ.get("GEMINI_API_KEY")
                resp = litellm.completion(
                    model="gemini/gemini-flash-latest",
                    messages=messages,
                    api_key=gemini_key
                )
                assistant_response = resp.choices[0].message.content
                logger.info("✅ Direct Gemini completion succeeded.")
            except Exception as e:
                logger.error(f"[VirtualAssistant] Gemini fallback failed: {e}")

        # 4. Local fallback if all API calls failed
        if not assistant_response:
            assistant_response = self._generate_local_fallback(user_input)

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

# Global singleton instance
assistant = VirtualAssistant()
