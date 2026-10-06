import os
import logging
import asyncio
from threading import Thread
from typing import Callable, Optional

logger = logging.getLogger(__name__)

telegram_app = None

async def send_telegram_chunked_message(update, text: str):
    """Splits long response text into Telegram-friendly chunks (max 3800 chars) and sends them sequentially."""
    if not text or not str(text).strip():
        return

    MAX_LENGTH = 3800
    if len(text) <= MAX_LENGTH:
        try:
            await update.message.reply_text(text, parse_mode="Markdown")
        except Exception:
            await update.message.reply_text(text)
        return

    lines = text.split("\n")
    current_chunk = []
    current_len = 0

    for line in lines:
        if current_len + len(line) + 1 > MAX_LENGTH:
            chunk_text = "\n".join(current_chunk)
            if chunk_text.strip():
                try:
                    await update.message.reply_text(chunk_text, parse_mode="Markdown")
                except Exception:
                    await update.message.reply_text(chunk_text)
            current_chunk = [line]
            current_len = len(line)
        else:
            current_chunk.append(line)
            current_len += len(line) + 1

    if current_chunk:
        chunk_text = "\n".join(current_chunk)
        if chunk_text.strip():
            try:
                await update.message.reply_text(chunk_text, parse_mode="Markdown")
            except Exception:
                await update.message.reply_text(chunk_text)

async def send_telegram_topic_messages(update, response: str):
    """Sends each goal/topic in its OWN dedicated Telegram message.
    If a single topic exceeds 3800 chars, chunk it. Never mix different topics into the same Telegram message."""
    if not response or not str(response).strip():
        return

    topics = response.split("\n\n---TOPIC_BREAK---\n\n")
    for topic in topics:
        topic_text = topic.strip()
        if not topic_text:
            continue
        await send_telegram_chunked_message(update, topic_text)

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

        receipt_manager = FinanceReceiptManager()

        async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
            await update.message.reply_text(
                "👋 **¡Hola! Soy Claudia OS, tu Asistente Virtual 24/7.**\n\n"
                "Puedo ayudarte en lenguaje natural con:\n"
                "📅 **Outlook & To-Do**: Crear eventos, tareas, ver tu agenda y enviar correos con MCP.\n"
                "🧾 **Finanzas**: Procesar fotos de recibos, analizarlos con IA y organizarlos.\n"
                "🧠 **Investigación & Tutoría**: Micro-objetivos, síntesis, redacción y evaluación."
            )

        async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if not update.message or not update.message.text:
                return

            user_id = str(update.message.from_user.id)
            user_text = update.message.text

            chat_type = update.message.chat.type if update.message and update.message.chat else "private"
            chat_title = (update.message.chat.title if update.message and update.message.chat else None) or update.message.from_user.first_name or "Chat Directo"

            origin_metadata = {
                "chat_type": chat_type,
                "chat_title": chat_title,
                "user_id": user_id
            }

            response = message_handler_callback(user_text, user_id, origin_metadata)
            if not response or not str(response).strip():
                response = "⚠️ No se obtuvo respuesta para esta consulta."

            await send_telegram_topic_messages(update, response)


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
