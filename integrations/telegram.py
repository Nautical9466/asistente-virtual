import os
import logging
from threading import Thread
from typing import Callable, Optional

logger = logging.getLogger(__name__)

telegram_app = None

def setup_telegram_bot(message_handler_callback: Callable[[str, str], str]) -> bool:
    """Configures and starts Telegram Bot polling in a background thread."""
    global telegram_app
    token = os.environ.get("TELEGRAM_BOT_TOKEN")

    if not token or token.startswith("your_"):
        logger.warning("[Telegram] TELEGRAM_BOT_TOKEN non-existent or unconfigured. Bot disabled.")
        return False

    try:
        from telegram import Update
        from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

        async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
            await update.message.reply_text(
                "👋 **¡Hola! Soy tu Asistente Virtual 24/7.**\n\n"
                "Puedo ayudarte con:\n"
                "📱 **TikTok**: Organizar, transcribir y puntuar videos.\n"
                "📚 **Aprendizaje**: Retos de ensayos, micro-objetivos diarios (15 min).\n"
                "💼 **LinkedIn**: Búsqueda de empleo, mejora de CV y perfil.\n"
                "🔗 **Integraciones**: Alarmas, Gantt ClickUp, Slack y más.\n\n"
                "¿En qué trabajamos hoy?"
            )

        async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if not update.message or not update.message.text:
                return
            user_id = str(update.message.from_user.id)
            user_text = update.message.text

            try:
                response = message_handler_callback(user_text, user_id)
                await update.message.reply_text(response, parse_mode="Markdown")
            except Exception as e:
                logger.error(f"[Telegram Error]: {e}")
                await update.message.reply_text("❌ Ocurrió un error al procesar tu solicitud.")

        telegram_app = Application.builder().token(token).build()
        telegram_app.add_handler(CommandHandler("start", start))
        telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        def run_polling():
            logger.info("🚀 [Telegram] Iniciando bot en modo polling...")
            telegram_app.run_polling(drop_pending_updates=True)

        thread = Thread(target=run_polling, daemon=True)
        thread.start()
        return True

    except Exception as e:
        logger.error(f"[Telegram Setup Failed]: {e}")
        return False
