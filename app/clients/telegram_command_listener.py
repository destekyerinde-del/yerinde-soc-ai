"""
YERİNDE SOC AI
Telegram Command Listener

/full_log <incident_id> komutunu dinler ve ilgili
incident'a ait ham alarm loglarını Telegram'a gönderir.
"""

from __future__ import annotations

import logging
import re
import time

from app.clients.telegram_client import TelegramClient
from app.core.config import CONFIG
from app.storage.incident_store import IncidentStore

LOGGER = logging.getLogger("yerinde-soc-ai.telegram-listener")

TELEGRAM_MESSAGE_LIMIT = 4000  # 4096 sınırına güvenlik payı


class TelegramCommandListener:
    """Listens for Telegram commands via long polling."""

    def __init__(self) -> None:
        self.telegram = TelegramClient()
        self.incidents = IncidentStore()
        self._offset: int | None = None

    # -----------------------------------------------------
    # Chunk helper
    # -----------------------------------------------------

    @staticmethod
    def _chunks(text: str, size: int) -> list[str]:
        return [text[i:i + size] for i in range(0, len(text), size)]

    # -----------------------------------------------------
    # Command: /full_log <incident_id>
    # -----------------------------------------------------

    def _handle_full_log(self, incident_id_raw: str) -> None:
        try:
            incident_id = int(incident_id_raw.strip())
        except ValueError:
            self.telegram.send_message(
                "❌ Geçersiz Incident ID. Kullanım: /full_log <incident_id>"
            )
            return

        alerts = self.incidents.get_incident_alerts(incident_id)

        if not alerts:
            self.telegram.send_message(
                f"❌ Incident ID {incident_id} için kayıt bulunamadı."
            )
            return

        header = f"📄 FULL LOG — Incident #{incident_id} ({len(alerts)} alarm)\n"
        header += "━━━━━━━━━━━━━━━━━━\n\n"

        body_parts = []

        for i, alert in enumerate(alerts, start=1):
            body_parts.append(
                f"[{i}/{len(alerts)}] Mail ID: {alert['mail_id']} "
                f"| {alert['created_at']}\n"
                f"{alert['alert_body']}\n"
                "──────────────────\n"
            )

        full_text = header + "\n".join(body_parts)

        for chunk in self._chunks(full_text, TELEGRAM_MESSAGE_LIMIT):
            self.telegram.send_message(chunk)
            time.sleep(0.5)  # Telegram rate limit için

        LOGGER.info("Full log gönderildi: incident_id=%s", incident_id)

    # -----------------------------------------------------
    # Dispatch
    # -----------------------------------------------------

    def _dispatch(self, text: str) -> None:
        match = re.match(r"^/full_log\s+(\d+)", text.strip())

        if match:
            self._handle_full_log(match.group(1))

    # -----------------------------------------------------
    # Poll loop
    # -----------------------------------------------------

    def run(self) -> None:
        LOGGER.info("Telegram komut dinleyici başlatıldı.")

        while True:
            try:
                updates = self.telegram.get_updates(
                    offset=self._offset, timeout=30
                )

                for update in updates:
                    self._offset = update["update_id"] + 1

                    message = update.get("message", {})
                    chat_id = str(message.get("chat", {}).get("id", ""))
                    text = message.get("text", "")

                    # Sadece yapılandırılmış chat_id'den gelen komutları kabul et
                    if chat_id != str(CONFIG.telegram_chat_id):
                        continue

                    if text.startswith("/full_log"):
                        self._dispatch(text)

            except Exception:
                LOGGER.exception("Telegram komut dinleyicide hata.")
                time.sleep(5)


def main() -> None:
    TelegramCommandListener().run()


if __name__ == "__main__":
    main()
