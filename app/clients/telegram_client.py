"""
YERİNDE SOC AI
Telegram Client

SOC AI analiz sonuçlarını Telegram'a gönderir.
"""

from __future__ import annotations

import json
import logging
import urllib.parse
import urllib.request

from app.core.config import CONFIG


class TelegramClient:
    """Telegram Bot API client."""

    def __init__(
        self,
        token: str | None = None,
        chat_id: str | None = None,
    ) -> None:
        self.token = (
            token
            or CONFIG.telegram_token
        )

        self.chat_id = (
            chat_id
            or CONFIG.telegram_chat_id
        )

        self.logger = logging.getLogger(
            "yerinde-soc-ai.telegram"
        )

    # ---------------------------------------------------------
    # Validation
    # ---------------------------------------------------------

    def _validate(self) -> None:
        """Validate Telegram configuration."""

        if not self.token:
            raise ValueError(
                "Telegram bot token tanımlı değil."
            )

        if not self.chat_id:
            raise ValueError(
                "Telegram chat ID tanımlı değil."
            )

    # ---------------------------------------------------------
    # API
    # ---------------------------------------------------------

    def _api(
        self,
        method: str,
        data: dict[str, str] | None = None,
    ) -> dict:
        """Call Telegram Bot API."""

        self._validate()

        url = (
            f"https://api.telegram.org/"
            f"bot{self.token}/{method}"
        )

        encoded = urllib.parse.urlencode(
            data or {}
        ).encode()

        request = urllib.request.Request(
            url,
            data=encoded,
            method="POST",
        )

        with urllib.request.urlopen(
            request,
            timeout=15,
        ) as response:

            result = json.loads(
                response.read().decode()
            )

        if not result.get("ok"):
            raise RuntimeError(
                f"Telegram API hatası: {result}"
            )

        return result

    # ---------------------------------------------------------
    # Health
    # ---------------------------------------------------------

    def health(self) -> bool:
        """Check Telegram bot connectivity."""

        try:

            result = self._api(
                "getMe"
            )

            return bool(
                result.get("ok")
            )

        except Exception:

            self.logger.exception(
                "Telegram bağlantısı başarısız."
            )

            return False

    # ---------------------------------------------------------
    # Send message
    # ---------------------------------------------------------

    def send_message(
        self,
        text: str,
    ) -> bool:
        """Send a text message to configured chat."""

        if not text.strip():
            return False

        try:

            self._api(
                "sendMessage",
                {
                    "chat_id": self.chat_id,
                    "text": text,
                },
            )

            self.logger.info(
                "Telegram mesajı gönderildi."
            )

            return True

        except Exception:

            self.logger.exception(
                "Telegram mesajı gönderilemedi."
            )

            return False
