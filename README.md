# 🤖 Asistente Virtual 24/7 (Claudia OS + LiteLLM + Railway)

Un asistente personal inteligente, autónomo y multi-modelo diseñado para integrarse con tu flujo diario a través de **Telegram**, **WhatsApp (Twilio)**, **CLI local** y servidor HTTP en **Railway**.

---

## 🌟 Características Principales

1. **Routing Multi-Modelo con LiteLLM**:
   - Integración nativa con **Groq** (`llama-3.3-70b`), **Gemini** (`gemini-2.0-flash`) y **DeepInfra** (`Qwen2.5-32B-Instruct`).
   - Fallback automático si un modelo o API no responde.

2. **Memoria Persistente al estilo Claudia OS**:
   - Lectura dinámica del contexto de usuario (`user/PROFILE.md`) y memorias en Markdown (`user/memory/`).
   - Guardado automático de historial por usuario en `data/context.json`.

3. **Skills Especializadas**:
   - 📱 **TikTok Manager**: Transcripción de audio, scoring de contenido y sugerencias de práctica.
   - 📚 **Learning Tutor**: Retos de ensayos académicos, micro-objetivos de 15 minutos y revisión de cuadernos.
   - 💼 **LinkedIn Hunter**: Búsqueda estratégica de vacantes, optimización de perfil, formato de CV ATS y alerta sabatina.
   - 🔗 **Integraciones Hub**: Diagramas Gantt de ClickUp, alarmas/recordatorios, bot de Slack y Telegram docs.
   - 🧠 **Claudia OS Deep Research & Wisdom**: Investigación multi-perspectiva (Council, Red Team, First Principles) y extracción de sabiduría.

4. **Multi-Canal & Despliegue en 1-Click**:
   - Servidor Flask + Gunicorn listo para **Railway**.
   - Dockerfile y `railway.json` preconfigurados.
   - Script CLI para testing local inmediato en terminal.

---

## 🚀 Inicio Rápido (Local)

### 1. Requisitos
- Python 3.10+
- Dependencias indicadas en `requirements.txt`

### 2. Probar en Terminal (CLI Mode)
```bash
python run_cli.py
```

### 3. Ejecutar los Tests Unitarios
```bash
python -m unittest tests/test_skills.py
```

### 4. Iniciar Servidor Web Local
```bash
python main.py
```

---

## ☁️ Despliegue en Railway (GitHub → Railway CI/CD)

1. Sube tu código a GitHub:
   ```bash
   git add .
   git commit -m "Initial commit: Virtual Assistant Claudia OS"
   git push origin main
   ```
2. En Railway:
   - Crea un nuevo proyecto desde el repositorio de GitHub.
   - Agrega las variables de entorno en Railway Dashboard (`GROQ_API_KEY`, `TELEGRAM_BOT_TOKEN`, etc.).
   - Railway detectará el `Dockerfile` y `railway.json` desplegando automáticamente en menos de 3 minutos.
