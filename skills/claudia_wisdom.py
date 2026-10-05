from core.router import assistant

class ClaudiaWisdomSkill:
    """Claudia OS Wisdom Skill: Extracts actionable wisdom and insights from text, articles, or video links."""

    def process_request(self, user_input: str, user_id: str = "default") -> str:
        synthesis = assistant.query(
            f"Extrae la sabiduría accionable, conceptos fundamentales y lecciones clave del siguiente contenido o enlace: '{user_input}'",
            system_prompt="Eres un sintetizador de conocimiento al estilo Claudia OS Wisdom."
        )
        return f"💡 **Sabiduría Sintetizada (Claudia Wisdom)**\n\n{synthesis}"
