from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "Telegram AI Assistant Webhook"
    
    # Required External API Keys
    TELEGRAM_BOT_TOKEN: str = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11" # Dummy token for Github Showcase
    OPENAI_API_KEY: str = "sk-proj-dummy-key"
    
    # Webhook configuration
    PUBLIC_WEBHOOK_URL: str = "https://your-domain.ngrok-free.app/webhook"

    class Config:
        env_file = ".env"

settings = Settings()
