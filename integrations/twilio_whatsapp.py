import os
import logging
from typing import Callable

logger = logging.getLogger(__name__)

def process_whatsapp_request(request_values: dict, message_handler_callback: Callable[[str, str], str]) -> str:
    """Processes incoming WhatsApp Webhook request from Twilio and returns TwiML string."""
    try:
        from twilio.twiml.messaging_response import MessagingResponse

        incoming_msg = request_values.get("Body", "").strip()
        sender = request_values.get("From", "whatsapp:default")
        user_id = sender.replace("whatsapp:", "")

        if not incoming_msg:
            resp = MessagingResponse()
            resp.message("Por favor envía un mensaje de texto válido.")
            return str(resp)

        response_text = message_handler_callback(incoming_msg, user_id)
        resp = MessagingResponse()
        resp.message(response_text)
        return str(resp)

    except Exception as e:
        logger.error(f"[WhatsApp Error]: {e}")
        try:
            from twilio.twiml.messaging_response import MessagingResponse
            resp = MessagingResponse()
            resp.message("❌ Error al procesar mensaje en WhatsApp.")
            return str(resp)
        except Exception:
            return "<Response><Message>Error</Message></Response>"
