import os
import logging
import asyncio
from threading import Thread
from typing import Callable, Optional

logger = logging.getLogger(__name__)

telegram_app = None

def setup_telegram_bot(message_handler_callback: Callable[[str, str], str]) -> bool:
    """Configures Telegram Bot with photo receipt processing, smart AI intent routing, and Outlook integrations."""
    global telegram_app
    token = os.environ.get("TELEGRAM_BOT_TOKEN")

    if not token or token.startswith("your_"):
        logger.warning("[Telegram] TELEGRAM_BOT_TOKEN non-existent or unconfigured. Bot disabled.")
        return False

    try:
        from telegram import Update
        from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
        from skills.finance_receipt_manager import FinanceReceiptManager
        from integrations.outlook import OutlookIntegration
        from integrations.intent_handler import OutlookIntentParser

        receipt_manager = FinanceReceiptManager()
        outlook = OutlookIntegration()
        intent_parser = OutlookIntentParser(outlook)

        async def send_delayed_telegram_reminder(bot, chat_id: int, user_name: str, reason: str, delay_sec: int):
            await asyncio.sleep(delay_sec)
            msg = (
                f"⏰ **¡RECORDATORIO PARA {user_name.upper()}!**\n"
                f"───────────────────────────\n"
                f"📌 **Recordatorio**: {reason}\n\n"
                f"¡Es la hora programada! Cuídate mucho. 😊"
            )
            try:
                await bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown")
            except Exception as e:
                logger.warning(f"[Telegram] Delayed reminder send failed: {e}")
                await bot.send_message(chat_id=chat_id, text=f"⏰ ¡RECORDATORIO! Es hora de: {reason}")

        async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
            await update.message.reply_text(
                "👋 **¡Hola! Soy tu Asistente Virtual 24/7.**\n\n"
                "Puedo ayudarte con:\n"
                "📅 **Outlook**: Crear Eventos de Calendario, Tareas To-Do o redactar Correos.\n"
                "🧾 **Finanzas**: Procesar fotos de recibos, analizarlos con IA y guardarlos organizados por carpeta en Google Drive.\n"
                "📱 **TikTok & Aprendizaje**: Transcribir, agendar metas de 15 min y responder tus dudas."
            )

        async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if not update.message or not update.message.text:
                return

            user_id = str(update.message.from_user.id)
            user_first_name = update.message.from_user.first_name or os.environ.get("USER_NAME", "Geral")
            user_text = update.message.text

            # 1. Parse natural language intent for Outlook or direct Telegram message reminders
            handled, response_data = intent_parser.parse_and_execute(user_text, user_first_name)

            if handled and isinstance(response_data, tuple):
                response, delay_sec, reason = response_data
                asyncio.create_task(
                    send_delayed_telegram_reminder(context.bot, update.effective_chat.id, user_first_name, reason, delay_sec)
                )
            elif handled:
                response = response_data
            else:
                # 2. Conversational fallback answered by AI LLM (Groq/Gemini)
                response = message_handler_callback(user_text, user_id)



            try:
                await update.message.reply_text(response, parse_mode="Markdown")
            except Exception as e:
                logger.warning(f"[Telegram] Markdown send failed ({e}), sending plain text fallback.")
                await update.message.reply_text(response)


        async def handle_photo_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if not update.message or not update.message.photo:
                return

            topic_name = "General"
            if update.message.is_topic_message and update.message.reply_to_message:
                if hasattr(update.message.reply_to_message, 'forum_topic_created'):
                    topic_name = update.message.reply_to_message.forum_topic_created.name

            caption = update.message.caption or ""
            if not topic_name or topic_name == "General":
                if "walmart" in caption.lower():
                    topic_name = "Recibos de tarjeta Walmart"
                elif "bachaso" in caption.lower():
                    topic_name = "Bachasos"
                elif "constancia" in caption.lower():
                    topic_name = "Fotos de constancias"
                elif "receta" in caption.lower():
                    topic_name = "Recetas médicas"
                else:
                    thread_id = getattr(update.message, 'message_thread_id', None)
                    topic_name = f"Canal_Topic_{thread_id}" if thread_id else "General"

            await update.message.reply_text(f"⏳ Procesando recibo en canal `{topic_name}` con IA...")

            photo = update.message.photo[-1]
            photo_file = await context.bot.get_file(photo.file_id)
            file_bytes = await photo_file.download_as_bytearray()

            filename = f"recibo_{photo.file_unique_id}.jpg"
            result_msg = receipt_manager.process_receipt_image(bytes(file_bytes), topic_name, filename)

            await update.message.reply_text(result_msg, parse_mode="Markdown")

        telegram_app = Application.builder().token(token).build()
        telegram_app.add_handler(CommandHandler("start", start))
        telegram_app.add_handler(MessageHandler(filters.PHOTO, handle_photo_message))
        telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))

        def run_polling():
            logger.info("🚀 [Telegram Bot] Polling con AI Intent Routing activo.")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            telegram_app.run_polling(drop_pending_updates=True, stop_signals=None)

        thread = Thread(target=run_polling, daemon=True)
        thread.start()
        return True

    except Exception as e:
        logger.error(f"[Telegram Setup Failed]: {e}")
        return False
