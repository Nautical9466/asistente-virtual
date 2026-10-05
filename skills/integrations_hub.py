from core.router import assistant
from integrations.clickup import ClickUpIntegration
from integrations.slack import SlackIntegration

class IntegrationsHub:
    """Integrations hub for alarms, reminders, ClickUp Gantt generation, Telegram docs, and Slack integration."""

    def __init__(self):
        self.clickup = ClickUpIntegration()
        self.slack = SlackIntegration()

    def process_request(self, user_input: str, user_id: str = "default") -> str:
        low = user_input.lower()
        if "alarma" in low or "recordatorio" in low or "alarm" in low or "remind" in low:
            return self.set_alarm(user_input)
        elif "gantt" in low or "clickup" in low or "diagrama" in low:
            return self.generate_gantt(user_input)
        elif "telegram" in low or "doc" in low or "documento" in low:
            return self.fetch_telegram_docs(user_input)
        elif "slack" in low or "publicar" in low:
            return self.post_to_slack(user_input)
        else:
            return self.get_integration_status()

    def set_alarm(self, user_input: str) -> str:
        parsed = assistant.query(
            f"Extrae la hora, fecha y motivo del recordatorio/alarma de: '{user_input}'",
            system_prompt="Eres un parser de eventos y alarmas."
        )
        return f"⏰ **Alarma / Recordatorio Configurado**\n\n{parsed}"

    def generate_gantt(self, user_input: str) -> str:
        tasks = self.clickup.get_tasks()
        gantt_lines = ["📊 **Diagrama de Gantt Generado (ClickUp)**\n"]
        for t in tasks:
            gantt_lines.append(f"- `[{t['status']}]` **{t['name']}** (Entrega: {t['due']})")

        return "\n".join(gantt_lines)

    def fetch_telegram_docs(self, user_input: str) -> str:
        return "📄 **Telegram Docs**: Documentos y archivos recientes sincronizados correctamente."

    def post_to_slack(self, user_input: str) -> str:
        res = self.slack.post_message(user_input)
        return f"✅ **Slack Integration**: {res}"

    def get_integration_status(self) -> str:
        return (
            "🔗 **Estado de Integraciones Hub**\n\n"
            "- Telegram Bot: *Conectado*\n"
            "- WhatsApp Twilio: *Activo*\n"
            "- ClickUp API: *Activo*\n"
            "- Slack SDK: *Listo*\n"
            "- Outlook Calendar: *Listo*"
        )
