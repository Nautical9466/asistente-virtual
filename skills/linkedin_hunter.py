from datetime import datetime
from core.router import assistant
from integrations.linkedin import LinkedInIntegration

class LinkedInHunter:
    """LinkedIn job search hunter, profile & CV optimizer, and weekly Saturday summary alert."""

    def __init__(self):
        self.linkedin = LinkedInIntegration()

    def process_request(self, user_input: str, user_id: str = "default") -> str:
        low = user_input.lower()
        if "buscar" in low or "empleo" in low or "job" in low or "vacante" in low:
            return self.search_relevant_jobs(user_input)
        elif "perfil" in low or "linkedin" in low or "titular" in low:
            return self.update_profile(user_input)
        elif "cv" in low or "curriculum" in low or "resumen" in low:
            return self.update_cv(user_input)
        elif "sabado" in low or "semanal" in low or "top" in low:
            return self.send_weekly_jobs()
        else:
            return self.get_application_status()

    def search_relevant_jobs(self, user_input: str) -> str:
        jobs = self.linkedin.search_jobs(user_input)
        analysis = assistant.query(
            f"El usuario busca empleo relacionado a: '{user_input}'. "
            f"Aquí están las vacantes encontradas: {jobs}. "
            "Recomienda cómo aplicar estratégicamente a cada una.",
            system_prompt="Eres un Job Matcher y reclutador tech experto."
        )
        return f"🎯 **Búsqueda de Empleo LinkedIn**\n\n{analysis}"

    def update_profile(self, user_input: str) -> str:
        advice = assistant.query(
            f"Revisa y sugiere mejoras para el perfil de LinkedIn basado en: '{user_input}'",
            system_prompt="Eres un LinkedIn Brand Strategist para profesionales tech."
        )
        return f"✨ **Optimización de Perfil LinkedIn**\n\n{advice}"

    def update_cv(self, user_input: str) -> str:
        cv_feedback = assistant.query(
            f"Optimiza estas secciones del CV para pasar filtros ATS: '{user_input}'",
            system_prompt="Eres un experto en optimización de CVs y formato ATS."
        )
        return f"📄 **Mejora de CV (Filtros ATS)**\n\n{cv_feedback}"

    def send_weekly_jobs(self) -> str:
        weekday = datetime.now().weekday()
        jobs = self.linkedin.search_jobs("Python AI Remote")
        if weekday == 5: # Saturday
            return (
                "🎯 **Top 5 Vacantes Seleccionadas de la Semana (Sábado)**\n\n"
                f"1. {jobs[0]['title']} en {jobs[0]['company']} ({jobs[0]['location']})\n"
                f"2. {jobs[1]['title']} en {jobs[1]['company']} ({jobs[1]['location']})\n"
                f"3. {jobs[2]['title']} en {jobs[2]['company']} ({jobs[2]['location']})\n\n"
                "💡 Escribe 'actualizar mi CV' para preparar tu postulación."
            )
        else:
            return (
                "📅 El reporte automático de vacantes semanales se envía cada **sábado**.\n"
                "Sin embargo, puedes solicitar una búsqueda en vivo en cualquier momento escribiendo 'buscar trabajo [tecnología/rol]'."
            )

    def get_application_status(self) -> str:
        return (
            "📊 **Estado del Módulo LinkedIn Hunter**\n\n"
            "- Conexión API: *Ready*\n"
            "- Búsquedas configuradas: *Python, AI, Automation, Fullstack*\n"
            "- Próxima alerta de vacantes: *Sábado 09:00 AM*"
        )
