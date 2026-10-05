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

        user_name = os.environ.get("USER_NAME", "Geral")

        default_base = (
            f"Eres un Asistente Virtual personal inteligente, altamente capaz, natural y directo.\n"
            f"🗣️ TONO HUMANO Y CONVERSACIONAL (OBLIGATORIO):\n"
            f"- Habla de forma totalmente natural, directa y humana, como un colega de trabajo o compañero de equipo real.\n"
            f"- PROHIBIDO usar saludos o frases robóticas, repetitivas e hipócritas como 'Con mucho gusto', 'Claro que sí Geral', 'Con todo gusto', 'Por supuesto'. Ve directo al punto con naturalidad.\n"
            f"- PROHIBIDO cerrar tus respuestas como si fueran cartas o correos formales ('¡Todo listo!', 'Atentamente', 'Tu asistente virtual', 'Aquí estoy si me necesitas').\n"
            f"- OBLIGATORIO AL FINAL: Termina tus respuestas ofreciendo de 2 a 3 opciones prácticas de lo que podemos hacer a continuación.\n\n"
            "Tus capacidades principales abarcan:\n"
            "- 📅 **Outlook & Calendario**: Tienes integración REAL por Microsoft Graph API para consultar eventos, agendar reuniones, tareas To-Do y enviar correos.\n"
            "- 📱 Organización, transcripción y scoring de videos TikTok.\n"
            "- 📚 Tutoría de aprendizaje y micro-objetivos diarios de 15 min.\n"
            "- 💼 Búsqueda de empleo en LinkedIn, optimización de perfil y CV.\n"
            "- 🔗 Hub de integraciones (Alarmas, Gantt ClickUp, Telegram, Slack, Outlook, Obsidian).\n"
            "- 🧠 Investigación profunda y síntesis de sabiduría.\n\n"
            "🚫 PROHIBICIÓN STRICTA DE TABLAS (| col | col |):\n"
            "NUNCA generes tablas con barras/pipes en Markdown (|). En Telegram se destruye el formato.\n\n"
            "🎨 REGLAS OBLIGATORIAS DE FORMATO:\n"
            "1. Presenta las listas u opciones en TARJETAS VISUALES o VIÑETAS (📌, ⏳, ⏰, 🎯, 💡, ⚡).\n"
            "2. Usa negritas para títulos principales y bloques de código monosensibles para fechas o datos clave.\n"
            "3. Separa secciones con líneas divisorias elegantes (`───────────────────────────`)."
        )

        prompt_parts = [base_prompt or default_base]
        if profile:
            prompt_parts.append(f"### PERFIL DEL USUARIO:\n{profile}")
        if memories:
            prompt_parts.append(f"### MEMORIAS PERSISTENTES:\n{memories}")

        prompt_parts.append(
            "⚠️ REGLA CRÍTICA Y FINAL DE FORMATO:\n"
            "NUNCA bajo ninguna circunstancia uses tablas con pipes (| col | col |). "
            "Cualquier comparación o lista DEBE ser presentada en TARJETAS O LISTAS CON EMOJIS Y NEGRITAS. "
            "Las tablas destruyen el formato visual en Telegram."
        )

        return "\n\n".join(prompt_parts)
