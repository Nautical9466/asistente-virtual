import os
import yaml
from datetime import datetime
from core.memory import MemoryManager
from core.context_loader import ContextLoader

class VirtualAssistant:
    """Core Virtual Assistant engine with multi-model LiteLLM routing & fallbacks."""

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

            # Check if any LLM API key is set
            has_keys = any(os.environ.get(k) for k in ["GROQ_API_KEY", "GEMINI_API_KEY", "DEEPINFRA_API_KEY"])

            if os.path.exists(self.config_path) and has_keys:
                self.router = Router.from_yaml(self.config_path)
                print("[VirtualAssistant] LiteLLM Router initialized successfully.")
            else:
                print("[VirtualAssistant] No LLM API keys found or config missing. Local fallback mode enabled.")
        except Exception as e:
            print(f"[VirtualAssistant] LiteLLM Router initialization warning: {e}")
            self.router = None

    def query(self, user_input: str, user_id: str = "default", model: str = "cerebro-deepinfra-qwen", system_prompt: str = None) -> str:
        """Processes a query through LiteLLM or fallback response system."""
        full_system_prompt = self.context_loader.get_full_system_prompt(system_prompt)
        history = self.memory.get_history(user_id)

        messages = [{"role": "system", "content": full_system_prompt}]
        for item in history:
            messages.append({"role": item["role"], "content": item["content"]})
        messages.append({"role": "user", "content": user_input})

        assistant_response = None

        if self.router:
            try:
                response = self.router.completion(
                    model=model,
                    messages=messages,
                    temperature=0.15
                )
                assistant_response = response.choices[0].message.content
            except Exception as e:
                print(f"[VirtualAssistant] Error querying {model}: {e}. Retrying fallback...")
                # Attempt direct LiteLLM completion fallback if router failed
                try:
                    import litellm
                    if os.environ.get("GEMINI_API_KEY"):
                        resp = litellm.completion(model="gemini/gemini-2.0-flash", messages=messages)
                        assistant_response = resp.choices[0].message.content
                    elif os.environ.get("GROQ_API_KEY"):
                        resp = litellm.completion(model="groq/llama-3.3-70b-versatile", messages=messages)
                        assistant_response = resp.choices[0].message.content
                except Exception as ex:
                    print(f"[VirtualAssistant] Fallback completion error: {ex}")

        if not assistant_response:
            # Smart local response generator when API keys are not yet configured
            assistant_response = self._generate_local_fallback(user_input)

        # Store interaction in memory
        self.memory.add_interaction(user_id, user_input, assistant_response)
        return assistant_response

    def _generate_local_fallback(self, user_input: str) -> str:
        """Generates structured local response when API key is unconfigured."""
        return (
            "🤖 **Modo Asistente Virtual Local**\n\n"
            f"He recibido tu mensaje: *\"{user_input}\"*\n\n"
            "💡 *Sugerencia*: Para respuestas completas generadas por IA, configura tus API keys en `.env`:\n"
            "- `GROQ_API_KEY` (Llama-3.3-70b gratis)\n"
            "- `GEMINI_API_KEY` (Gemini-2.0 Flash gratis)\n"
            "- `DEEPINFRA_API_KEY` (Qwen-2.5 32B)\n\n"
            "Los módulos de Skills e Integraciones locales están 100% operativos."
        )

# Global singleton instance
assistant = VirtualAssistant()
