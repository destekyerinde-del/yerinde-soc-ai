"""
YERİNDE SOC AI
SQLite Alert Store

Wazuh alarm geçmişini, kaynak bilgisini, AI analizini
ve Telegram bildirim durumunu kalıcı olarak saklar.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class AlertStore:
    """Persistent SQLite storage for SOC alerts."""

    def __init__(
        self,
        database_path: str | Path = "logs/yerinde-soc.db",
    ) -> None:

        self.database_path = Path(
            database_path
        )

        self.database_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._initialize()

    # ---------------------------------------------------------
    # Connection
    # ---------------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        """Create a SQLite connection."""

        connection = sqlite3.connect(
            self.database_path
        )

        connection.row_factory = sqlite3.Row

        return connection

    # ---------------------------------------------------------
    # Initialization
    # ---------------------------------------------------------

    def _initialize(self) -> None:
        """Create or migrate database schema."""

        with self._connect() as connection:

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    mail_id TEXT NOT NULL,
                    message_id TEXT,

                    subject TEXT,
                    source_host TEXT NOT NULL DEFAULT 'UNKNOWN',

                    rule_level INTEGER NOT NULL,
                    alert_body TEXT,

                    ai_risk TEXT,
                    ai_reason TEXT,
                    ai_recommendation TEXT,

                    ai_status TEXT NOT NULL DEFAULT 'PENDING',
                    telegram_status TEXT NOT NULL DEFAULT 'PENDING',

                    processed INTEGER NOT NULL DEFAULT 0,

                    created_at TEXT NOT NULL,
                    processed_at TEXT
                )
                """
            )

            # -------------------------------------------------
            # Existing database migration
            # -------------------------------------------------

            columns = connection.execute(
                "PRAGMA table_info(alerts)"
            ).fetchall()

            column_names = {
                row["name"]
                for row in columns
            }

            if "source_host" not in column_names:

                connection.execute(
                    """
                    ALTER TABLE alerts
                    ADD COLUMN source_host
                    TEXT NOT NULL DEFAULT 'UNKNOWN'
                    """
                )

            if "rule_id" not in column_names:

                connection.execute(
                    """
                    ALTER TABLE alerts
                    ADD COLUMN rule_id
                    TEXT NOT NULL DEFAULT 'UNKNOWN'
                    """
                )

            if "correlation_count" not in column_names:
                connection.execute(
                    """
                    ALTER TABLE alerts
                    ADD COLUMN correlation_count
                    INTEGER NOT NULL DEFAULT 1
                    """
                )

            if "correlation_window_seconds" not in column_names:
                connection.execute(
                    """
                    ALTER TABLE alerts
                    ADD COLUMN correlation_window_seconds
                    INTEGER NOT NULL DEFAULT 600
                    """
                )

            if "rule_description" not in column_names:

                connection.execute(
                    """
                    ALTER TABLE alerts
                    ADD COLUMN rule_description
                    TEXT NOT NULL DEFAULT 'UNKNOWN'
                    """
                )

            # -------------------------------------------------
            # Indexes
            # -------------------------------------------------

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_alerts_mail_id
                ON alerts(mail_id)
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_alerts_message_id
                ON alerts(message_id)
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_alerts_rule_level
                ON alerts(rule_level)
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_alerts_source_host
                ON alerts(source_host)
                """
            )

            connection.commit()

    # ---------------------------------------------------------
    # Create
    # ---------------------------------------------------------

    def create_alert(
        self,
        *,
        mail_id: str,
        message_id: str,
        subject: str,
        rule_level: int,
        alert_body: str,
        source_host: str = "UNKNOWN",
        rule_id: str = "UNKNOWN",
        rule_description: str = "UNKNOWN",
    ) -> int:
        """Create a new alert record."""

        created_at = datetime.now(
            timezone.utc
        ).isoformat()

        source_host = (
            source_host.strip()
            if source_host
            else "UNKNOWN"
        )

        rule_id = (
            rule_id.strip()
            if rule_id
            else "UNKNOWN"
        )

        rule_description = (
            rule_description.strip()
            if rule_description
            else "UNKNOWN"
        )

        with self._connect() as connection:

            cursor = connection.execute(
                """
                INSERT INTO alerts (
                    mail_id,
                    message_id,
                    subject,
                    source_host,
                    rule_id,
                    rule_description,
                    rule_level,
                    alert_body,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    mail_id,
                    message_id,
                    subject,
                    source_host,
                    rule_id,
                    rule_description,
                    rule_level,
                    alert_body,
                    created_at,
                ),
            )

            connection.commit()

            return int(
                cursor.lastrowid
            )

    # ---------------------------------------------------------
    # AI result
    # ---------------------------------------------------------

    def save_ai_analysis(
        self,
        alert_id: int,
        *,
        risk: str,
        reason: str,
        recommendation: str,
    ) -> None:
        """Save successful AI analysis."""

        with self._connect() as connection:

            connection.execute(
                """
                UPDATE alerts
                SET
                    ai_risk = ?,
                    ai_reason = ?,
                    ai_recommendation = ?,
                    ai_status = 'SUCCESS'
                WHERE id = ?
                """,
                (
                    risk,
                    reason,
                    recommendation,
                    alert_id,
                ),
            )

            connection.commit()

    # ---------------------------------------------------------
    # AI failure
    # ---------------------------------------------------------

    def mark_ai_failed(
        self,
        alert_id: int,
    ) -> None:
        """Mark AI analysis as failed."""

        with self._connect() as connection:

            connection.execute(
                """
                UPDATE alerts
                SET ai_status = 'FAILED'
                WHERE id = ?
                """,
                (alert_id,),
            )

            connection.commit()

    # ---------------------------------------------------------
    # Telegram
    # ---------------------------------------------------------

    def mark_telegram_sent(
        self,
        alert_id: int,
    ) -> None:
        """Mark Telegram notification as successful."""

        with self._connect() as connection:

            connection.execute(
                """
                UPDATE alerts
                SET telegram_status = 'SENT'
                WHERE id = ?
                """,
                (alert_id,),
            )

            connection.commit()

    def mark_telegram_failed(
        self,
        alert_id: int,
    ) -> None:
        """Mark Telegram notification as failed."""

        with self._connect() as connection:

            connection.execute(
                """
                UPDATE alerts
                SET telegram_status = 'FAILED'
                WHERE id = ?
                """,
                (alert_id,),
            )

            connection.commit()

    # ---------------------------------------------------------
    # Processed
    # ---------------------------------------------------------

    def mark_processed(
        self,
        alert_id: int,
    ) -> None:
        """Mark alert as completely processed."""

        processed_at = datetime.now(
            timezone.utc
        ).isoformat()

        with self._connect() as connection:

            connection.execute(
                """
                UPDATE alerts
                SET
                    processed = 1,
                    processed_at = ?
                WHERE id = ?
                """,
                (
                    processed_at,
                    alert_id,
                ),
            )

            connection.commit()

    # ---------------------------------------------------------
    # Query
    # ---------------------------------------------------------

    def get_alert(
        self,
        alert_id: int,
    ) -> dict[str, Any] | None:
        """Return one alert."""

        with self._connect() as connection:

            row = connection.execute(
                """
                SELECT *
                FROM alerts
                WHERE id = ?
                """,
                (alert_id,),
            ).fetchone()

        if row is None:
            return None

        return dict(row)

    def count(self) -> int:
        """Return total alert count."""

        with self._connect() as connection:

            row = connection.execute(
                """
                SELECT COUNT(*)
                FROM alerts
                """
            ).fetchone()

        return int(row[0])

    # ---------------------------------------------------------
    # Duplicate lookup
    # ---------------------------------------------------------

    def exists(
        self,
        *,
        message_id: str = "",
        mail_id: str = "",
    ) -> bool:
        """Check whether an alert already exists."""

        with self._connect() as connection:

            if message_id:

                row = connection.execute(
                    """
                    SELECT 1
                    FROM alerts
                    WHERE message_id = ?
                    LIMIT 1
                    """,
                    (message_id,),
                ).fetchone()

                if row is not None:
                    return True

            if mail_id:

                row = connection.execute(
                    """
                    SELECT 1
                    FROM alerts
                    WHERE mail_id = ?
                    LIMIT 1
                    """,
                    (mail_id,),
                ).fetchone()

                if row is not None:
                    return True

        return False

    # ---------------------------------------------------------
    # Existing alert lookup
    # ---------------------------------------------------------

    def get_existing_alert_id(
        self,
        *,
        message_id: str = "",
        mail_id: str = "",
    ) -> int | None:
        """Return existing alert ID by message_id or mail_id."""

        with self._connect() as connection:

            if message_id:
                row = connection.execute(
                    """
                    SELECT id
                    FROM alerts
                    WHERE message_id = ?
                    LIMIT 1
                    """,
                    (message_id,),
                ).fetchone()

                if row is not None:
                    return int(row["id"])

            if mail_id:
                row = connection.execute(
                    """
                    SELECT id
                    FROM alerts
                    WHERE mail_id = ?
                    LIMIT 1
                    """,
                    (mail_id,),
                ).fetchone()

                if row is not None:
                    return int(row["id"])

        return None

    # ---------------------------------------------------------
    # Correlation
    # ---------------------------------------------------------

    def get_correlation_count(
        self,
        alert_id: int,
        window_seconds: int = 600,
    ) -> int:
        """Return recent matching alert count for an alert."""

        with self._connect() as connection:

            row = connection.execute(
                """
                SELECT COUNT(*) AS correlation_count
                FROM alerts AS current_alert
                JOIN alerts AS related_alert
                  ON related_alert.source_host =
                     current_alert.source_host
                 AND related_alert.rule_id =
                     current_alert.rule_id
                 AND julianday(
                        related_alert.created_at
                     ) >=
                     julianday(
                        current_alert.created_at
                     ) - (? / 86400.0)
                 AND julianday(
                        related_alert.created_at
                     ) <=
                     julianday(
                        current_alert.created_at
                     )
                WHERE current_alert.id = ?
                """,
                (
                    window_seconds,
                    alert_id,
                ),
            ).fetchone()

        return int(row["correlation_count"])

    def save_correlation(
        self,
        alert_id: int,
        *,
        correlation_count: int,
        window_seconds: int = 600,
    ) -> None:
        """Save correlation information for an alert."""

        with self._connect() as connection:

            connection.execute(
                """
                UPDATE alerts
                SET
                    correlation_count = ?,
                    correlation_window_seconds = ?
                WHERE id = ?
                """,
                (
                    correlation_count,
                    window_seconds,
                    alert_id,
                ),
            )

            connection.commit()
