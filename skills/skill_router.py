import inspect
from skills.tiktok_manager import TikTokManager
from skills.learning_tutor import LearningTutor
from skills.linkedin_hunter import LinkedInHunter
from skills.integrations_hub import IntegrationsHub
from skills.claudia_research import ClaudiaResearchSkill
from skills.claudia_wisdom import ClaudiaWisdomSkill

class SkillRouter:
    """Detects message intent and routes requests automatically to specialized skills."""

    def __init__(self):
        self.tiktok = TikTokManager()
        self.tutor = LearningTutor()
        self.linkedin = LinkedInHunter()
        self.hub = IntegrationsHub()
        self.research = ClaudiaResearchSkill()
        self.wisdom = ClaudiaWisdomSkill()

        self.keyword_map = {
            # TikTok keywords
            "tiktok": self.tiktok,
            "video": self.tiktok,
            "transcrib": self.tiktok,
            "scoring": self.tiktok,

            # Learning Tutor keywords
            "ensayo": self.tutor,
            "essay": self.tutor,
            "goal": self.tutor,
            "micro": self.tutor,
            "cuaderno": self.tutor,
            "estudio": self.tutor,
            "15 min": self.tutor,

            # LinkedIn Hunter keywords
            "linkedin": self.linkedin,
            "empleo": self.linkedin,
            "trabajo": self.linkedin,
            "job": self.linkedin,
            "vacante": self.linkedin,
            "cv": self.linkedin,
            "curriculum": self.linkedin,

            # Integrations Hub keywords
            "alarma": self.hub,
            "recordatorio": self.hub,
            "gantt": self.hub,
            "clickup": self.hub,
            "slack": self.hub,
            "telegram doc": self.hub,

            # Claudia OS Research & Wisdom
            "investig": self.research,
            "red team": self.research,
            "council": self.research,
            "sabiduria": self.wisdom,
            "wisdom": self.wisdom,
            "sintesis": self.wisdom,
        }

    def route_message(self, user_input: str):
        low = user_input.lower()
        # Bypass skill router if user is managing Outlook tasks, lists, or calendar events
        if any(w in low for w in ["tarea", "tareas", "lista", "listas", "todo", "outlook", "calendario", "evento"]):
            return None

        for kw, skill in self.keyword_map.items():
            if kw in low:
                return skill
        return None


    def execute(self, user_input: str, user_id: str = "default"):
        skill = self.route_message(user_input)
        if skill is None:
            return None

        if hasattr(skill, "process_request"):
            return skill.process_request(user_input, user_id)

        return None

# Global singleton router
skill_router = SkillRouter()
