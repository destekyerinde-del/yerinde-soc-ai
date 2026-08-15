"""
YERİNDE SOC AI
Gmail Client

Gmail IMAP bağlantısı, okunmamış mail alma,
mail parse etme, Seen işaretleme ve Trash işlemlerini yönetir.
"""

from __future__ import annotations

import email
import imaplib
import logging
import re
from email.header import decode_header
from email.message import Message
from html import unescape
from typing import Any

from app.core.config import CONFIG


class GmailClient:
    """Gmail IMAP client."""

    def __init__(
        self,
        host: str | None = None,
        username: str | None = None,
        password: str | None = None,
    ) -> None:
        self.host = host or CONFIG.gmail_host
        self.username = username or CONFIG.gmail_user
        self.password = password or CONFIG.gmail_pass

        self.mail: imaplib.IMAP4_SSL | None = None

        self.logger = logging.getLogger("yerinde-soc-ai.gmail")

    # ---------------------------------------------------------
    # Connection
    # ---------------------------------------------------------

    def connect(self) -> None:
        """Connect to Gmail IMAP and select INBOX."""

        if self.mail is not None:
            return

        if not self.host:
            raise ValueError("Gmail host tanımlı değil.")

        if not self.username:
            raise ValueError("Gmail kullanıcı adı tanımlı değil.")

        if not self.password:
            raise ValueError("Gmail şifresi tanımlı değil.")

        try:
            self.logger.info("Gmail bağlantısı kuruluyor...")

            self.mail = imaplib.IMAP4_SSL(
                self.host,
                timeout=30,
            )

            self.mail.login(
                self.username,
                self.password,
            )

            status, _ = self.mail.select("INBOX")

            if status != "OK":
                raise RuntimeError(
                    "Gmail INBOX seçilemedi."
                )

            self.logger.info(
                "Gmail bağlantısı başarılı."
            )

        except Exception:
            self.logger.exception(
                "Gmail bağlantısı başarısız."
            )

            self.mail = None
            raise

    # ---------------------------------------------------------
    # Disconnect
    # ---------------------------------------------------------

    def disconnect(self) -> None:
        """Close Gmail IMAP connection."""

        if self.mail is None:
            return

        try:
            try:
                self.mail.close()
            except Exception:
                pass

            self.mail.logout()

            self.logger.info(
                "Gmail bağlantısı kapatıldı."
            )

        except Exception:
            self.logger.exception(
                "Gmail bağlantısı kapatılırken hata oluştu."
            )

        finally:
            self.mail = None

    # ---------------------------------------------------------
    # Context manager
    # ---------------------------------------------------------

    def __enter__(self) -> GmailClient:
        """Open connection for context manager usage."""

        self.connect()
        return self

    def __exit__(
        self,
        exc_type: Any,
        exc_value: Any,
        traceback: Any,
    ) -> None:
        """Close connection for context manager usage."""

        self.disconnect()

    # ---------------------------------------------------------
    # Connection check
    # ---------------------------------------------------------

    def _ensure_connected(self) -> imaplib.IMAP4_SSL:
        """Return active IMAP connection."""

        if self.mail is None:
            self.connect()

        if self.mail is None:
            raise RuntimeError(
                "Gmail bağlantısı kurulamadı."
            )

        return self.mail

    # ---------------------------------------------------------
    # Fetch unread mail IDs
    # ---------------------------------------------------------

    def fetch_unread_ids(self) -> list[str]:
        """Return IDs of unread messages in INBOX."""

        mail = self._ensure_connected()

        status, data = mail.search(
            None,
            "UNSEEN",
        )

        if status != "OK":
            raise RuntimeError(
                "Okunmamış mailler aranamadı."
            )

        if not data or not data[0]:
            return []

        return data[0].decode(
            "utf-8",
            errors="ignore",
        ).split()

    # ---------------------------------------------------------
    # Fetch message
    # ---------------------------------------------------------

    def fetch_message(
        self,
        mail_id: str,
    ) -> dict[str, Any] | None:
        """Fetch and parse a single Gmail message."""

        mail = self._ensure_connected()

        status, data = mail.fetch(
            mail_id,
            "(RFC822)",
        )

        if status != "OK":
            self.logger.error(
                "Mail alınamadı: %s",
                mail_id,
            )
            return None

        raw_message = self._extract_raw_message(
            data
        )

        if raw_message is None:
            self.logger.error(
                "Mail içeriği boş: %s",
                mail_id,
            )
            return None

        message = email.message_from_bytes(
            raw_message
        )

        return {
            "id": mail_id,
            "message_id": self._get_message_id(
                message
            ),
            "subject": self.decode_subject(
                message.get("Subject")
            ),
            "from": self.decode_header_value(
                message.get("From")
            ),
            "to": self.decode_header_value(
                message.get("To")
            ),
            "date": message.get("Date", ""),
            "body": self.extract_body(message),
            "raw": message,
        }

    # ---------------------------------------------------------
    # Fetch unread messages
    # ---------------------------------------------------------

    def fetch_unread_messages(
        self,
    ) -> list[dict[str, Any]]:
        """Fetch all unread messages."""

        messages: list[dict[str, Any]] = []

        for mail_id in self.fetch_unread_ids():

            try:
                message = self.fetch_message(
                    mail_id
                )

                if message is not None:
                    messages.append(message)

            except Exception:
                self.logger.exception(
                    "Mail işlenemedi: %s",
                    mail_id,
                )

        return messages

    # ---------------------------------------------------------
    # Extract raw RFC822 message
    # ---------------------------------------------------------

    @staticmethod
    def _extract_raw_message(
        data: Any,
    ) -> bytes | None:
        """Extract raw email bytes from IMAP response."""

        if not data:
            return None

        for item in data:

            if not isinstance(item, tuple):
                continue

            if len(item) < 2:
                continue

            raw_message = item[1]

            if isinstance(raw_message, bytes):
                return raw_message

        return None

    # ---------------------------------------------------------
    # Decode subject
    # ---------------------------------------------------------

    @staticmethod
    def decode_subject(
        subject: str | None,
    ) -> str:
        """Decode MIME encoded email subject."""

        if not subject:
            return ""

        decoded_parts = decode_header(subject)

        result: list[str] = []

        for part, encoding in decoded_parts:

            if isinstance(part, bytes):

                try:
                    result.append(
                        part.decode(
                            encoding or "utf-8",
                            errors="replace",
                        )
                    )

                except (LookupError, UnicodeDecodeError):

                    result.append(
                        part.decode(
                            "utf-8",
                            errors="replace",
                        )
                    )

            else:
                result.append(part)

        return "".join(result).strip()

    # ---------------------------------------------------------
    # Decode generic header
    # ---------------------------------------------------------

    @staticmethod
    def decode_header_value(
        value: str | None,
    ) -> str:
        """Decode a MIME encoded email header."""

        if not value:
            return ""

        decoded_parts = decode_header(value)

        result: list[str] = []

        for part, encoding in decoded_parts:

            if isinstance(part, bytes):

                try:
                    result.append(
                        part.decode(
                            encoding or "utf-8",
                            errors="replace",
                        )
                    )

                except (LookupError, UnicodeDecodeError):

                    result.append(
                        part.decode(
                            "utf-8",
                            errors="replace",
                        )
                    )

            else:
                result.append(part)

        return "".join(result).strip()

    # ---------------------------------------------------------
    # Extract body
    # ---------------------------------------------------------

    def extract_body(
        self,
        message: Message,
    ) -> str:
        """Extract readable text from email."""

        plain_parts: list[str] = []
        html_parts: list[str] = []

        if message.is_multipart():

            for part in message.walk():

                content_type = part.get_content_type()
                disposition = str(
                    part.get(
                        "Content-Disposition",
                        "",
                    )
                )

                if "attachment" in disposition.lower():
                    continue

                payload = part.get_payload(
                    decode=True
                )

                if not isinstance(payload, bytes):
                    continue

                charset = (
                    part.get_content_charset()
                    or "utf-8"
                )

                text = payload.decode(
                    charset,
                    errors="replace",
                )

                if content_type == "text/plain":
                    plain_parts.append(text)

                elif content_type == "text/html":
                    html_parts.append(text)

        else:

            payload = message.get_payload(
                decode=True
            )

            if isinstance(payload, bytes):

                charset = (
                    message.get_content_charset()
                    or "utf-8"
                )

                text = payload.decode(
                    charset,
                    errors="replace",
                )

                if message.get_content_type() == "text/html":
                    html_parts.append(text)

                else:
                    plain_parts.append(text)

        if plain_parts:
            return self.clean_text(
                "\n".join(plain_parts)
            )

        if html_parts:
            return self.clean_html(
                "\n".join(html_parts)
            )

        return ""

    # ---------------------------------------------------------
    # Clean HTML
    # ---------------------------------------------------------

    @staticmethod
    def clean_html(html: str) -> str:
        """Convert basic HTML into readable plain text."""

        text = re.sub(
            r"(?is)<(script|style).*?>.*?</\1>",
            " ",
            html,
        )

        text = re.sub(
            r"(?i)<br\s*/?>",
            "\n",
            text,
        )

        text = re.sub(
            r"(?i)</p\s*>",
            "\n",
            text,
        )

        text = re.sub(
            r"<[^>]+>",
            " ",
            text,
        )

        text = unescape(text)

        return GmailClient.clean_text(text)

    # ---------------------------------------------------------
    # Clean plain text
    # ---------------------------------------------------------

    @staticmethod
    def clean_text(text: str) -> str:
        """Normalize whitespace in message body."""

        text = text.replace(
            "\r\n",
            "\n",
        )

        text = text.replace(
            "\r",
            "\n",
        )

        text = re.sub(
            r"[ \t]+",
            " ",
            text,
        )

        text = re.sub(
            r"\n{3,}",
            "\n\n",
            text,
        )

        return text.strip()

    # ---------------------------------------------------------
    # Message-ID
    # ---------------------------------------------------------

    @staticmethod
    def _get_message_id(
        message: Message,
    ) -> str:
        """Return Message-ID header."""

        return (
            message.get(
                "Message-ID",
                "",
            ).strip()
        )

    # ---------------------------------------------------------
    # Mark as seen
    # ---------------------------------------------------------

    def mark_seen(
        self,
        mail_id: str,
    ) -> bool:
        """Mark a message as read."""

        mail = self._ensure_connected()

        status, _ = mail.store(
            mail_id,
            "+FLAGS",
            "\\Seen",
        )

        if status != "OK":

            self.logger.error(
                "Mail okundu olarak işaretlenemedi: %s",
                mail_id,
            )

            return False

        self.logger.info(
            "Mail okundu: %s",
            mail_id,
        )

        return True

    # ---------------------------------------------------------
    # Move to trash
    # ---------------------------------------------------------

    def move_to_trash(
        self,
        mail_id: str,
    ) -> bool:
        """
        Move a Gmail message to Trash.

        Gmail IMAP supports the special \\Trash label.
        """

        mail = self._ensure_connected()

        try:

            status, _ = mail.store(
                mail_id,
                "+X-GM-LABELS",
                "\\Trash",
            )

            if status != "OK":

                self.logger.error(
                    "Trash etiketi eklenemedi: %s",
                    mail_id,
                )

                return False

            status, _ = mail.store(
                mail_id,
                "-X-GM-LABELS",
                "\\Inbox",
            )

            if status != "OK":

                self.logger.error(
                    "Inbox etiketi kaldırılamadı: %s",
                    mail_id,
                )

                return False

            self.logger.info(
                "Mail Trash klasörüne taşındı: %s",
                mail_id,
            )

            return True

        except Exception:

            self.logger.exception(
                "Mail Trash'a taşınamadı: %s",
                mail_id,
            )

            return False

    # ---------------------------------------------------------
    # Find Wazuh level
    # ---------------------------------------------------------

    @staticmethod
    def get_level(
        body: str,
    ) -> int:
        """Extract Wazuh rule level from message body."""

        patterns = [
            r"Rule\s+Level[:\s=]+(\d+)",
            r"Level[:\s=]+(\d+)",
            r"level=(\d+)",
        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                body,
                re.IGNORECASE,
            )

            if match:
                return int(
                    match.group(1)
                )

        return 0
