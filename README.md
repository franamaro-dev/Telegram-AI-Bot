# Telegram AI Assistant (Webhook Integration)

> **Demostración técnica de integraciones asíncronas con APIs de terceros (Telegram, OpenAI) y patrones orientados a eventos.**

<div align="center">
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/OpenAI-412991?style=for-the-badge&logo=openai&logoColor=white" />
  <img src="https://img.shields.io/badge/Telegram-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white" />
</div>

## 📌 Descripción del Proyecto
Este repositorio demuestra cómo construir un bot de Telegram robusto y escalable sin necesidad de *"Long Polling"*.
Implementa un servidor **Webhooks** en `FastAPI` que reacciona instantáneamente a los eventos generados por Telegram y delega las operaciones pesadas (generación de texto con ChatGPT) a tareas en segundo plano.

## ⚙️ Arquitectura Técnica y Capacidades
- **Framework Asíncrono:** FastAPI (Python 3.11+) asegurando tiempos de respuesta sub-milisegundo.
- **Background Tasks:** Las peticiones lentas a la API de OpenAI no bloquean el Hilo Web Principal, cumpliendo con la estricta limitación de *Timeout* que exige la API oficial de Telegram.
- **Seguridad Inyectada:** Configuración validada y ofuscada mediante `pydantic-settings` (API Keys nunca expuestas).
- **HTTP/X Clients:** Consumo directo de `httpx` para integraciones eficientes de capa REST.

## 🚀 Despliegue

```bash
# 1. Clona el proyecto
git clone https://github.com/franamaro-dev/Telegram-AI-Bot.git

# 2. Configura las variables seguras
export TELEGRAM_BOT_TOKEN="tu-token-aqui"
export OPENAI_API_KEY="sk-tu-key-aqui"

# 3. Levántalo con Docker
docker build -t app-bot .
docker run -p 8000:8000 -e TELEGRAM_BOT_TOKEN -e OPENAI_API_KEY app-bot
```

> **Nota:** Para entornos de producción, se recomienda exponer el puerto `8000` detrás de un proxy reverso (Nginx/Traefik) con soporte HTTPS.
