# Script de despliegue para el webhook de Telegram.
import httpx
import asyncio
from bot.config import settings

async def setup():
    """
    Registra la URL pública de este FastApi en los servidores de Telegram.
    Sustituye 'settings.PUBLIC_WEBHOOK_URL' con tu URL real (ej: tunnel de ngrok).
    """
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/setWebhook"
    payload = {"url": settings.PUBLIC_WEBHOOK_URL}
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload)
        print(f"Set Webhook result: {response.json()}")

if __name__ == "__main__":
    asyncio.run(setup())
