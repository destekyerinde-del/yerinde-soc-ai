"""
YERİNDE SOC AI
Configuration Manager
"""

from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv

# Proje kök dizini
BASE_DIR = Path(__file__).resolve().parents[2]

# .env dosyası
ENV_FILE = BASE_DIR / ".env"

# .env yükle
load_dotenv(dotenv_path=ENV_FILE)


@dataclass(frozen=True)
class Config:
    """Application configuration."""

    # -------------------------
    # Gmail
    # -------------------------
    gmail_host: str = os.getenv("GMAIL_HOST", "imap.gmail.com")
    gmail_user: str = os.getenv("GMAIL_USER", "")
    gmail_pass: str = os.getenv("GMAIL_PASS", "")

    # -------------------------
    # Telegram
    # -------------------------
    telegram_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_chat_id: str = os.getenv("TELEGRAM_CHAT_ID", "")

    # -------------------------
    # Ollama
    # -------------------------
    ollama_host: str = os.getenv(
        "OLLAMA_HOST",
        "http://127.0.0.1:11434"
    )

    ollama_model: str = os.getenv(
        "OLLAMA_MODEL",
        "OpenNix/wazuh-llama-3.1-8B-v1"
    )

    ai_timeout: int = int(
        os.getenv("AI_TIMEOUT", "180")
    )

    # -------------------------
    # Application
    # -------------------------
    check_interval: int = int(
        os.getenv("CHECK_INTERVAL", "30")
    )

    log_level: str = os.getenv(
        "LOG_LEVEL",
        "INFO"
    ).upper()

    # -------------------------
    # Validation
    # -------------------------
    def validate(self) -> None:
        """Validate required configuration."""

        required = {
            "GMAIL_USER": self.gmail_user,
            "GMAIL_PASS": self.gmail_pass,
            "TELEGRAM_BOT_TOKEN": self.telegram_token,
            "TELEGRAM_CHAT_ID": self.telegram_chat_id,
        }

        missing = [
            key
            for key, value in required.items()
            if not value.strip()
        ]

        if missing:
            raise RuntimeError(
                "\nMissing environment variables:\n\n"
                + "\n".join(missing)
            )


CONFIG = Config()
