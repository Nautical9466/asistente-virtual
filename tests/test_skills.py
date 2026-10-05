import unittest
import os
from main import handle_incoming_message
from skills.skill_router import skill_router

class TestVirtualAssistant(unittest.TestCase):

    def test_tiktok_skill_routing(self):
        msg = "transcribir video de tiktok sobre python"
        res = handle_incoming_message(msg, "test_user")
        self.assertIn("TikTok", res)

    def test_learning_tutor_routing(self):
        msg = "necesito preparar un ensayo sobre inteligencia artificial"
        res = handle_incoming_message(msg, "test_user")
        self.assertIn("Ensayo", res)

    def test_micro_goals_routing(self):
        msg = "dame 3 micro goals de 15 min para hoy"
        res = handle_incoming_message(msg, "test_user")
        self.assertIn("Micro-Objetivos", res)

    def test_linkedin_hunter_routing(self):
        msg = "buscar empleo de desarrollo en linkedin"
        res = handle_incoming_message(msg, "test_user")
        self.assertIn("LinkedIn", res)

    def test_integrations_hub_routing(self):
        msg = "generar diagrama gantt de clickup"
        res = handle_incoming_message(msg, "test_user")
        self.assertIn("Gantt", res)

    def test_claudia_research_routing(self):
        msg = "investigacion profunda sobre modelos de lenguaje"
        res = handle_incoming_message(msg, "test_user")
        self.assertIn("Investigación", res)

if __name__ == "__main__":
    unittest.main()
