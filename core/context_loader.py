import os
import glob

class ContextLoader:
    """Loads user profile and Claudia OS markdown memories into system context."""

    def __init__(self, user_dir="user"):
        self.user_dir = user_dir

    def load_profile(self) -> str:
        profile_path = os.path.join(self.user_dir, "PROFILE.md")
        if os.path.exists(profile_path):
            with open(profile_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def load_critical_memories(self) -> str:
        memory_dir = os.path.join(self.user_dir, "memory")
        if not os.path.exists(memory_dir):
            return ""

        memories = []
        md_files = glob.glob(os.path.join(memory_dir, "*.md"))
        for filepath in md_files:
            if os.path.basename(filepath) == "MEMORY.md":
                continue
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                memories.append(content)

        return "\n\n---\n\n".join(memories)

    def get_full_system_prompt(self, base_prompt: str = None) -> str:
        profile = self.load_profile()
        memories = self.load_critical_memories()

        default_base = (
            "Eres un Asistente Virtual 24/7 personal, inteligente, empático y estructurado.\n"
            "Tus capacidades principales abarcan:\n"
            "- 📅 **Outlook & Calendario**: Tienes integración REAL y SEGURA por Microsoft Graph API. Puedes consultar eventos, agendar reuniones, tareas en To-Do y enviar correos directamente. NUNCA sugieras publicar el calendario en internet ni compartir enlaces iCal públicos, ya que tu servidor procesa todo de forma privada y cifrada por OAuth2.\n"
            "- 📱 Organización, transcripción y scoring de videos TikTok.\n"
            "- 📚 Tutoría de aprendizaje, retos de ensayos y micro-objetivos diarios de 15 min.\n"
            "- 💼 Búsqueda de empleo en LinkedIn, optimización de perfil y CV.\n"
            "- 🔗 Hub de integraciones (Alarmas, Gantt ClickUp, Telegram, Slack, Outlook, Obsidian).\n"
            "- 🧠 Investigación profunda y síntesis de sabiduría estilo Claudia OS.\n\n"
            "Mantén un tono profesional, motivador y directo."
        )

        prompt_parts = [base_prompt or default_base]
        if profile:
            prompt_parts.append(f"### PERFIL DEL USUARIO:\n{profile}")
            prompt_parts.append(f"### MEMORIAS Persistentes:\n{memories}")

        return "\n\n".join(prompt_parts)
