import os
import logging
import requests
from datetime import datetime
from flask import Flask, request, jsonify, redirect, url_for
from dotenv import load_dotenv

from core.router import assistant
from integrations.telegram import setup_telegram_bot
from integrations.twilio_whatsapp import process_whatsapp_request

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("VirtualAssistantServer")

app = Flask(__name__)

# Fallback Client ID for Azure Microsoft OAuth
REAL_CLIENT_ID = "f6e2f39f-26b6-4339-827f-771c5f8e0e1a"

def get_outlook_client_id() -> str:
    cid = os.environ.get("OUTLOOK_CLIENT_ID")
    if not cid or cid.startswith("e3b9") or cid.startswith("OB78Q"):
        return REAL_CLIENT_ID
    return cid

def handle_incoming_message(user_input: str, user_id: str = "default", origin_metadata: dict = None) -> str:
    """Central processing logic for messages from Telegram, WhatsApp, or Web."""
    try:
        return assistant.query(user_input, user_id, origin_metadata=origin_metadata)
    except Exception as e:
        logger.error(f"Error processing message for user {user_id}: {e}")
        return f"❌ Lo siento, ocurrió un error al procesar tu solicitud: {e}"

# Start Telegram Bot polling in background thread if configured and not disabled
telegram_active = False
if not os.environ.get("DISABLE_TELEGRAM_BOT") and os.environ.get("TELEGRAM_BOT_TOKEN"):
    telegram_active = setup_telegram_bot(handle_incoming_message)

@app.route("/", methods=["GET"])
def health_check():
    """Health check endpoint for Railway, Render, and web probes."""
    return jsonify({
        "status": "online",
        "service": "Virtual Assistant Claudia OS API",
        "timestamp": datetime.now().isoformat(),
        "telegram_active": telegram_active,
        "environment": os.environ.get("ENVIRONMENT", "development")
    }), 200

@app.route("/auth/outlook", methods=["GET"])
def outlook_auth_login():
    """Redirects user to Microsoft OAuth login page."""
    client_id = get_outlook_client_id()
    tenant_id = os.environ.get("OUTLOOK_TENANT_ID", "common")
    redirect_uri = request.host_url.rstrip("/") + "/auth/callback"
    scope = "offline_access Calendars.ReadWrite Tasks.ReadWrite Mail.Send"

    auth_url = (
        f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize?"
        f"client_id={client_id}&response_type=code&redirect_uri={redirect_uri}"
        f"&response_mode=query&scope={scope}"
    )
    return redirect(auth_url)

@app.route("/auth/callback", methods=["GET"])
def outlook_auth_callback():
    """Handles Microsoft OAuth callback code and exchanges it for OUTLOOK_REFRESH_TOKEN."""
    code = request.args.get("code")
    error = request.args.get("error_description") or request.args.get("error")

    if error:
        return f"❌ Error de autenticación en Microsoft: {error}", 400
    if not code:
        return "⚠️ No se recibió código de autorización de Microsoft.", 400

    client_id = get_outlook_client_id()
    client_secret = os.environ.get("OUTLOOK_CLIENT_SECRET")
    tenant_id = os.environ.get("OUTLOOK_TENANT_ID", "common")

    if not client_secret:
        return "⚠️ Falta la variable `OUTLOOK_CLIENT_SECRET` en el panel de Render -> Environment.", 400

    redirect_uri = request.host_url.rstrip("/") + "/auth/callback"
    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"

    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "scope": "offline_access Calendars.ReadWrite Tasks.ReadWrite Mail.Send"
    }

    res = requests.post(token_url, data=payload)
    if res.status_code == 200:
        token_data = res.json()
        refresh_token = token_data.get("refresh_token")
        return f"""
        <html>
        <body style="font-family: sans-serif; padding: 40px; background: #0f172a; color: #f8fafc;">
            <h2>🎉 ¡Autenticación de Microsoft Outlook Exitosa!</h2>
            <p>Copia el siguiente <b>OUTLOOK_REFRESH_TOKEN</b> y pégalo en tu archivo <code>.env</code> y en Render Environment:</p>
            <textarea style="width: 100%; height: 120px; font-size: 14px; background: #1e293b; color: #38bdf8; border: 1px solid #334155; padding: 10px;">{refresh_token}</textarea>
        </body>
        </html>
        """
    else:
        return f"❌ Error canjeando token de Microsoft: {res.text}", 400

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
