from core.router import assistant

class ClaudiaResearchSkill:
    """Claudia OS Deep Research Skill: Quick, Standard, and Deep Multi-perspective research."""

    def process_request(self, user_input: str, user_id: str = "default") -> str:
        low = user_input.lower()
        if "profunda" in low or "deep" in low or "red team" in low or "council" in low:
            return self.deep_research(user_input)
        else:
            return self.standard_research(user_input)

    def standard_research(self, query: str) -> str:
        report = assistant.query(
            f"Realiza una investigación estructurada y directa sobre: '{query}'. "
            "Incluye resumen ejecutivo, puntos clave, pros/contras y conclusiones.",
            system_prompt="Eres un investigador analítico senior al estilo Claudia OS."
        )
        return f"🔍 **Informe de Investigación (Estándar)**\n\n{report}"

    def deep_research(self, query: str) -> str:
        report = assistant.query(
            f"Realiza una investigación PROFUNDA multi-perspectiva sobre: '{query}'.\n"
            "Aplica tres ángulos:\n"
            "1. **Council**: Deliberación estratégica multi-perspectiva.\n"
            "2. **Red Team**: Evaluación de fallas, riesgos y sesgos.\n"
            "3. **First Principles**: Reconstrucción desde los axiomas fundamentales.",
            system_prompt="Eres el motor de pensamiento crítico y profundo de Claudia OS."
        )
        return f"🧠 **Investigación Profunda (Claudia OS Deep Research)**\n\n{report}"
