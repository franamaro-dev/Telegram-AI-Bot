from fastapi import FastAPI, Request, BackgroundTasks
from pydantic import BaseModel
import logging

from bot.ai_client import generate_ai_response, send_telegram_message

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Telegram AI Assistant Webhook",
    description="Listen and respond asynchronously to Telegram messages via OpenAI."
)

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "Telegram-AI-Bot"}

async def process_telegram_message(chat_id: int, message_text: str):
    """
    Background worker function. We process the AI response here
    so we can return a HTTP 200 OK immediately back to Telegram's Webhook
    (Telegram requires response within seconds or it will retry).
    """
    try:
        # 1. Ask OpenAI
        ai_reply = await generate_ai_response(message_text)
        
        # 2. Forward result back to the user via Telegram REST API
        await send_telegram_message(chat_id, ai_reply)
    except Exception as e:
        logger.error(f"Failed to process message: {str(e)}")


@app.post("/webhook")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    The main receiving port for Telegram updates.
    """
    data = await request.json()
    
    # Telegram payloads can contain different things (channels, edits, etc)
    # We only care about explicit text messages sent directly to the bot.
    if "message" in data and "text" in data["message"]:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"]["text"]
        
        # Offload the heavy AI processing to a Background Task to free the HTTP thread instantly
        background_tasks.add_task(process_telegram_message, chat_id, text)
        
    return {"status": "accepted"}
