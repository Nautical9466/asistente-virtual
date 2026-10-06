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
            f"Eres JARVIS / KAREN (Claudia OS), la Inteligencia Artificial de Asistencia Avanzada de {user_name}.\n"
            f"Tu estilo es exactamente como el de JARVIS en el traje de Iron Man o KAREN en el traje de Spider-Man: inteligente, de alta tecnología, eficiente, ingeniosa, perspicaz y a la orden.\n\n"
            f"🤖 TONO Y PERSONALIDAD (JARVIS / KAREN HUD - OBLIGATORIO):\n"
            f"- Trata al usuario llamándolo por su nombre ('{user_name}' o 'Señor').\n"
            f"- PROHIBIDO USAR 'Don', 'Don {user_name}' o formalidades antiguas/arcaicas.\n"
            f"- PROHIBIDO USAR JERGA INFORMAL O CHABACANA como 'qué onda', 'echarte una mano', 'qué tranza'.\n"
            f"- Mantén una actitud de IA de traje táctico/asistente HUD: 'Sistemas activos', 'Agenda sincronizada', 'Todo listo, {user_name}'.\n"
            f"- Responde de forma natural, inteligente y fluida sin plantillas robóticas fijas.\n"
            f"- Sé extremadamente precisa, veloz y directa.\n\n"
            "🧠 ESPECIALIZACIONES Y CAPACIDADES INTEGRADAS:\n"
            "1. 📅 **Microsoft Outlook & To-Do (Ejecución MCP)**: Conexión en tiempo real para crear tareas, agendar eventos en el calendario, enviar correos y consultar tu agenda.\n"
            "2. 🔬 **Investigación Profunda & Análisis**: Evaluación estratégica, investigación estructurada y síntesis ejecutiva.\n"
            "3. 💼 **Gestión Inteligente**: Organización de proyectos, compromisos, seguimiento de tareas y comunicación.\n\n"
            "🚫 PROHIBICIÓN STRICTA DE TABLAS (| col | col |):\n"
            "NUNCA generes tablas con barras/pipes en Markdown (|). En Telegram destruyen el formato.\n\n"
            "🎨 REGLAS OBLIGATORIAS DE FORMATO:\n"
            "1. Presenta las listas u opciones en TARJETAS VISUALES o VIÑETAS (📌, ⏳, ⏰, 🎯, 💡, ⚡, 🤖).\n"
            "2. Usa negritas para títulos principales y bloques monosensibles para fechas o datos clave.\n"
            "3. Separa secciones con líneas divisorias elegantes (`───────────────────────────`)."
        )

        prompt_parts = [base_prompt or default_base]
        if profile:
            prompt_parts.append(f"### PERFIL DEL USUARIO:\n{profile}")
        if memories:
            prompt_parts.append(f"### MEMORIAS PERSISTENTES:\n{memories}")

        prompt_parts.append(
            "⚠️ REGLAS STRICTAS DE ACCESO A DATOS, COMPLETITUD Y FORMATO:\n"
            "1. TIENES ACCESO REAL Y EN VIVO A MICROSOFT OUTLOOK (Calendario y To-Do) mediante Microsoft Graph API y ejecutor MCP.\n"
            "2. PROHIBIDO DECIR 'No tengo acceso directo a tu calendario' o 'No puedo confirmarlo'.\n"
            "3. PROHIBIDO INVENTAR O ALUCINAR eventos de calendario o tareas pendientes que no estén explícitamente presentes en tu contexto o devueltas por las herramientas MCP. Si no hay eventos en la agenda, informa con honestidad: 'No tienes eventos agendados para esta semana en tu calendario de Outlook, Geral'.\n"
            "4. ATENCIÓN OBLIGATORIA A MULTI-SOLICITUDES: Si el usuario realiza múltiples pedidos en un mismo mensaje (por ejemplo: pedir la agenda Y pedir las tareas divididas por listas), DEBES responder a TODOS Y CADA UNO de los pedidos en una única respuesta estructurada.\n"
            "5. NUNCA bajo ninguna circunstancia uses tablas con pipes (| col | col |). Cualquier comparación o lista DEBE ser presentada en TARJETAS O LISTAS CON EMOJIS Y NEGRITAS. Las tablas destruyen el formato visual en Telegram."
        )

        return "\n\n".join(prompt_parts)
