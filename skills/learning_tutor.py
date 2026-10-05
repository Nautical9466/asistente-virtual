import os
from core.router import assistant
from integrations.outlook import OutlookIntegration

class LearningTutor:
    """Learning tutor for academic essays, 15-minute micro-goals, skill strategies, and notebook scoring."""

    def __init__(self):
        self.outlook = OutlookIntegration()

    def process_request(self, user_input: str, user_id: str = "default") -> str:
        low = user_input.lower()
        if "ensayo" in low or "essay" in low or "redac" in low:
            return self.start_essay_challenge(user_input, user_id)
        elif "goal" in low or "meta" in low or "micro" in low or "15" in low:
            return self.create_daily_micro_goals(user_input, user_id)
        elif "eststrategia" in low or "crear contenido" in low:
            return self.propose_tiktok_strategy(user_input)
        elif "evalua" in low or "revisa" in low or "nota" in low or "score" in low:
            return self.review_notebook(user_input, user_id)
        else:
            return self.get_learning_status(user_id)

    def start_essay_challenge(self, user_input: str, user_id: str) -> str:
        plan = assistant.query(
            f"El usuario quiere redactar un ensayo o artículo sobre: '{user_input}'. "
            "Crea una estructura dividida en fases pequeñas con fechas recomendadas y plantilla de tesis.",
            system_prompt="Eres un profesor de escritura académica y claridad de pensamiento."
        )
        outlook_status = self.outlook.create_event("📝 Ensayo: Inicio de Fase 1", "Mañana 09:00", 30)
        return (
            "📝 **Desafío de Ensayo Iniciado**\n\n"
            f"{plan}\n\n"
            f"📌 {outlook_status}"
        )

    def create_daily_micro_goals(self, user_input: str, user_id: str) -> str:
        goals = assistant.query(
            f"Diseña 3 micro-objetivos de 15 minutos exactos para hoy basados en la solicitud: '{user_input}'. "
            "Cada objetivo debe ser claro, medible y realizable de inmediato.",
            system_prompt="Eres un coach de productividad extrema enfocado en micro-bloques de 15 minutos."
        )
        return f"⏱️ **Micro-Objetivos Diarios (15 Mins cada uno)**\n\n{goals}"

    def propose_tiktok_strategy(self, user_input: str) -> str:
        return assistant.query(
            f"Propón 3 ideas de videos TikTok para enseñar hard/soft skills aprendidas recientemente: '{user_input}'",
            system_prompt="Eres un estratega de contenido educativo para redes sociales."
        )

    def review_notebook(self, user_input: str, user_id: str) -> str:
        review = assistant.query(
            f"Evalúa estas notas de estudio o cuaderno del usuario y asigna un puntaje de 0 a 100 con retroalimentación: '{user_input}'",
            system_prompt="Eres un profesor evaluador y mentor de técnicas de estudio (Feynman, Active Recall)."
        )
        return f"🎓 **Evaluación de Cuaderno de Estudio**\n\n{review}"

    def get_learning_status(self, user_id: str) -> str:
        return (
            "📚 **Estado de Tutoría de Aprendizaje**\n\n"
            "- Metodología activa: *Micro-bloques de 15 minutos & Feynman Method*\n"
            "- Próximo paso: Escribe 'ensayo sobre [tema]' o 'micro metas de hoy'."
        )
