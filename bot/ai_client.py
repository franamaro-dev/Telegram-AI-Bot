import httpx
from openai import AsyncOpenAI
from bot.config import settings
import logging

logger = logging.getLogger(__name__)

# Reusable Async Client connected to OpenAI
client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

async def generate_ai_response(user_message: str) -> str:
    """
    Calls the OpenAI API asynchronously to prevent blocking the FastAPI event loop.
    Demonstrates handling of third-party LLM providers.
    """
    try:
        completion = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful and concise Telegram assistant. You answer all questions perfectly but in less than 3 sentences."},
                {"role": "user", "content": user_message}
            ],
            timeout=15.0 # Failsafe timeout for external APIs
        )
        return completion.choices[0].message.content
        
    except httpx.TimeoutException:
        logger.error("OpenAI API timeout error.")
        return "Sorry, my brain (OpenAI) is taking too long to respond right now."
    except Exception as e:
        logger.error(f"Error communicating with OpenAI: {str(e)}")
        return "Sorry, I encountered an internal error while thinking."

async def send_telegram_message(chat_id: int, text: str):
    """
    Sends a response back to the user via Telegram's REST API.
    """
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    
    async with httpx.AsyncClient() as http_client:
        response = await http_client.post(url, json=payload)
        if response.status_code != 200:
            logger.error(f"Failed to send Telegram message: {response.text}")
