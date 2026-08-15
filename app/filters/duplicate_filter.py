"""
YERİNDE SOC AI
Duplicate Alert Filter

Aynı Wazuh alarmının tekrar AI analizine gönderilmesini engeller.
"""

from __future__ import annotations

import logging
from pathlib import Path


class DuplicateFilter:
    """Persistent duplicate alert filter."""

    def __init__(
        self,
        storage_file: str | Path = "logs/processed_alerts.txt",
    ) -> None:
        self.storage_file = Path(storage_file)
        self.logger = logging.getLogger(
            "yerinde-soc-ai.duplicate"
        )

        self.processed: set[str] = set()

        self._load()

    # ---------------------------------------------------------
    # Load
    # ---------------------------------------------------------

    def _load(self) -> None:
        """Load previously processed alert IDs."""

        if not self.storage_file.exists():
            return

        try:
            lines = self.storage_file.read_text(
                encoding="utf-8"
            ).splitlines()

            self.processed = {
                line.strip()
                for line in lines
                if line.strip()
            }

            self.logger.info(
                "Duplicate Filter: %d kayıt yüklendi.",
                len(self.processed),
            )

        except Exception:
            self.logger.exception(
                "Duplicate Filter kayıtları okunamadı."
            )

    # ---------------------------------------------------------
    # Save
    # ---------------------------------------------------------

    def _save(self, alert_id: str) -> None:
        """Persist a processed alert ID."""

        self.storage_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with self.storage_file.open(
            "a",
            encoding="utf-8",
        ) as file:
            file.write(alert_id + "\n")

    # ---------------------------------------------------------
    # Check
    # ---------------------------------------------------------

    def is_duplicate(
        self,
        alert_id: str,
    ) -> bool:
        """Return True if alert was already processed."""

        if not alert_id:
            return False

        return alert_id in self.processed

    # ---------------------------------------------------------
    # Register
    # ---------------------------------------------------------

    def mark_processed(
        self,
        alert_id: str,
    ) -> None:
        """Mark alert as processed."""

        if not alert_id:
            return

        if alert_id in self.processed:
            return

        self.processed.add(alert_id)
        self._save(alert_id)

        self.logger.info(
            "Alert processed olarak kaydedildi: %s",
            alert_id,
        )

    # ---------------------------------------------------------
    # Accept
    # ---------------------------------------------------------

    def check_and_mark(
        self,
        alert_id: str,
    ) -> bool:
        """
        Check alert and immediately mark it as processed.

        Returns:
            True  -> yeni alarm
            False -> duplicate alarm
        """

        if self.is_duplicate(alert_id):
            self.logger.info(
                "Duplicate alarm engellendi: %s",
                alert_id,
            )
            return False

        self.mark_processed(alert_id)
        return True

    # ---------------------------------------------------------
    # Count
    # ---------------------------------------------------------

    def count(self) -> int:
        """Return number of processed alerts."""

        return len(self.processed)

    # ---------------------------------------------------------
    # Clear
    # ---------------------------------------------------------

    def clear(self) -> None:
        """Clear all processed alert records."""

        self.processed.clear()

        if self.storage_file.exists():
            self.storage_file.unlink()

        self.logger.info(
            "Duplicate Filter kayıtları temizlendi."
        )
