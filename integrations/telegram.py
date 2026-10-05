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

        receipt_manager = FinanceReceiptManager()
        outlook = OutlookIntegration()

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
            user_text = update.message.text
            low = user_text.lower().strip()

            # Direct explicit commands for Outlook
            if low.startswith("agendar evento:") or low.startswith("crear evento:"):
                event_title = user_text.split(":", 1)[1].strip()
                response = outlook.create_event(event_title, "Mañana 10:00")
            elif low.startswith("crear tarea:") or low.startswith("agendar tarea:"):
                task_title = user_text.split(":", 1)[1].strip()
                response = outlook.create_task(task_title)
            elif low.startswith("crear lista:") or low.startswith("nueva lista:"):
                list_title = user_text.split(":", 1)[1].strip()
                response = outlook.create_todo_list(list_title)
            elif low.startswith("enviar correo:") or low.startswith("mandar mail:"):
                mail_details = user_text.split(":", 1)[1].strip()
                response = outlook.send_email("destinatario@ejemplo.com", "Mensaje desde Asistente", mail_details)
            elif any(w in low for w in ["listas", "mis listas", "todas las listas", "lista extra", "crear una lista"]):
                response = outlook.get_all_lists_grouped()
            elif any(w in low for w in ["expirada", "expiradas", "vencida", "vencidas", "vencio", "venció", "vencido", "vencidos", "atrasada", "atrasadas", "atrasado", "atrasados", "oct 1", "1 de octubre", "1 oct", "octubre 1"]):
                response = outlook.get_overdue_tasks()
            elif low.startswith("buscar tarea:") or low.startswith("busca tarea:"):
                search_q = user_text.split(":", 1)[1].strip()
                response = outlook.search_tasks(search_q)
            elif any(w in low for w in ["seguridad del terreno", "seguridad terreno", "pago de la seguridad", "sugerencia", "sugerencias"]):
                response = outlook.search_tasks("seguridad")
            elif "desactivar recurrencia" in low or "quitar recurrencia" in low:
                response = outlook.set_task_recurrence(user_text, enable=False)
            elif "activar recurrencia" in low or "hacer recurrente" in low:
                response = outlook.set_task_recurrence(user_text, enable=True)
            elif any(w in low for w in ["cambiar fecha", "poner fecha", "vencer el", "vencer en", "fecha limite"]):
                response = outlook.set_task_due_date(user_text, user_text)
            elif any(w in low for w in ["completar", "completada", "completadas", "marcar como completada", "marca como completada", "marcar completada", "marcar tarea", "completar tarea"]):
                response = outlook.complete_task(user_text)
            elif any(w in low for w in ["tarea", "tareas", "todo", "todos", "pendiente", "pendientes"]):
                response = outlook.get_tasks()
            elif any(w in low for w in ["evento", "eventos", "calendario", "agenda", "agendado", "programado"]) and any(w in low for w in ["tengo", "ver", "revisar", "mostrar", "cuál", "cual", "cuáles", "cuales", "próxima", "proxima", "semana", "mes", "hay", "que tengo", "mis"]):
                days = 30 if "mes" in low else 14
                response = outlook.get_calendar_events(days_ahead=days)
            else:
                # All conversational questions & queries are answered intelligently by AI (Groq/Gemini/Qwen)
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
