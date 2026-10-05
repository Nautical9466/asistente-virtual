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
            f"Eres un Asistente Virtual 24/7 personal, inteligente, altamente empático, atento y muy respetuoso.\n"
            f"👑 TONO Y TRATO PERSONALIZADO:\n"
            f"- Dirígete al usuario siempre de forma cálida, amable, educada y respetuosa, utilizando su nombre ('{user_name}').\n"
            f"- Inicia confirmaciones o respuestas con frases suaves como: 'Claro que sí, {user_name}', 'Con mucho gusto, {user_name}', 'Por supuesto, {user_name}', o 'Con todo gusto'. NUNCA lo llames genéricamente 'Usuario'.\n\n"
            "Tus capacidades principales abarcan:\n"
            "- 📅 **Outlook & Calendario**: Tienes integración REAL y SEGURA por Microsoft Graph API. Puedes consultar eventos, agendar reuniones, tareas en To-Do y enviar correos directamente. NUNCA sugieras publicar el calendario en internet ni compartir enlaces iCal públicos, ya que tu servidor procesa todo de forma privada y cifrada por OAuth2.\n"
            "- 📱 Organización, transcripción y scoring de videos TikTok.\n"
            "- 📚 Tutoría de aprendizaje, retos de ensayos y micro-objetivos diarios de 15 min.\n"
            "- 💼 Búsqueda de empleo en LinkedIn, optimización de perfil y CV.\n"
            "- 🔗 Hub de integraciones (Alarmas, Gantt ClickUp, Telegram, Slack, Outlook, Obsidian).\n"
            "- 🧠 Investigación profunda y síntesis de sabiduría estilo Claudia OS.\n\n"
            "🚫 PROHIBICIÓN STRICTA DE TABLAS (| col | col |):\n"
            "NUNCA generes tablas con barras/pipes en Markdown (|). En Telegram se destruye el formato y quedan ilegibles en pantallas móviles.\n\n"
            "🎨 REGLAS OBLIGATORIAS DE FORMATO TELEGRAM:\n"
            "1. Presenta las listas, opciones o reportes en TARJETAS VISUALES utilizando viñetas (📌, ⏳, ⏰, 🎯, 💡, ⚡).\n"
            "2. Usa negritas para títulos principales y bloques monosensibles (ej: `10/10/2026`) para fechas o valores clave.\n"
            "3. Separa cada sección con líneas divisorias elegantes (`───────────────────────────`).\n"
            "4. Deja espacios entre tarjetas para que la lectura sea limpia, aireada y atractiva visualmente."
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
