import os

class SlackIntegration:
    """Slack integration helper."""

    def __init__(self):
        self.bot_token = os.environ.get("SLACK_BOT_TOKEN")

    def post_message(self, text: str, channel: str = "#general") -> str:
        return f"💬 Mensaje publicado en Slack ({channel}): {text}"
