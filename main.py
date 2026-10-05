import os
import logging
from datetime import datetime
from flask import Flask, request, jsonify
from dotenv import load_dotenv

from core.router import assistant
from skills.skill_router import skill_router
from integrations.telegram import setup_telegram_bot
from integrations.twilio_whatsapp import process_whatsapp_request

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("VirtualAssistantServer")

app = Flask(__name__)

def handle_incoming_message(user_input: str, user_id: str = "default") -> str:
    """Central processing logic for messages from Telegram, WhatsApp, or Web."""
    try:
        # Try routing to custom skills first
        skill_response = skill_router.execute(user_input, user_id)
        if skill_response:
            return skill_response

        # Fallback to general Assistant with LiteLLM & context memory
        return assistant.query(user_input, user_id)
    except Exception as e:
        logger.error(f"Error processing message for user {user_id}: {e}")
        return f"❌ Lo siento, ocurrió un error al procesar tu solicitud: {e}"

# Start Telegram Bot polling in background thread if configured
telegram_active = setup_telegram_bot(handle_incoming_message)

@app.route("/", methods=["GET"])
def health_check():
    """Health check endpoint for Railway and web probes."""
    return jsonify({
        "status": "online",
        "service": "Virtual Assistant Claudia OS API",
        "timestamp": datetime.now().isoformat(),
        "telegram_active": telegram_active,
        "environment": os.environ.get("ENVIRONMENT", "development")
    }), 200

@app.route("/chat", methods=["POST"])
def web_chat():
    """HTTP API endpoint for local web or CLI client integration."""
    data = request.get_json(silent=True) or {}
    user_input = data.get("message", "").strip()
    user_id = data.get("user_id", "default")

    if not user_input:
        return jsonify({"error": "Parámetro 'message' es requerido."}), 400

    response = handle_incoming_message(user_input, user_id)
    return jsonify({
        "user_id": user_id,
        "response": response,
        "timestamp": datetime.now().isoformat()
    }), 200

@app.route("/whatsapp", methods=["POST"])
def whatsapp_webhook():
    """Twilio WhatsApp webhook endpoint."""
    return process_whatsapp_request(request.values, handle_incoming_message)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"🚀 Iniciando servidor de Asistente Virtual en http://0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
