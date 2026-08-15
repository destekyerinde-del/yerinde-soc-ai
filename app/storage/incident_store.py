"""
YERİNDE SOC AI
Incident Store

Correlation sonucunda oluşan SOC incident kayıtlarını
SQLite üzerinde yönetir.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class IncidentStore:
    """Persistent SQLite storage for SOC incidents."""

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
        """Create SQLite connection."""

        connection = sqlite3.connect(
            self.database_path
        )

        connection.row_factory = sqlite3.Row

        return connection

    # ---------------------------------------------------------
    # Initialization
    # ---------------------------------------------------------

    def _initialize(self) -> None:
        """Create incident schema."""

        with self._connect() as connection:

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS incidents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    source_host TEXT NOT NULL,
                    rule_id TEXT NOT NULL,

                    status TEXT NOT NULL DEFAULT 'OPEN',

                    first_seen TEXT NOT NULL,
                    last_seen TEXT NOT NULL,

                    alert_count INTEGER NOT NULL DEFAULT 1,

                    correlation_window_seconds
                        INTEGER NOT NULL DEFAULT 600,

                    created_at TEXT NOT NULL
                )
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_incidents_source_rule
                ON incidents(source_host, rule_id)
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_incidents_status
                ON incidents(status)
                """
            )

            connection.commit()

    # ---------------------------------------------------------
    # Create
    # ---------------------------------------------------------

    def create_incident(
        self,
        *,
        source_host: str,
        rule_id: str,
        first_seen: str,
        last_seen: str,
        alert_count: int = 1,
        correlation_window_seconds: int = 600,
    ) -> int:
        """Create a new open incident."""

        created_at = datetime.now(
            timezone.utc
        ).isoformat()

        with self._connect() as connection:

            cursor = connection.execute(
                """
                INSERT INTO incidents (
                    source_host,
                    rule_id,
                    status,
                    first_seen,
                    last_seen,
                    alert_count,
                    correlation_window_seconds,
                    created_at
                )
                VALUES (?, ?, 'OPEN', ?, ?, ?, ?, ?)
                """,
                (
                    source_host,
                    rule_id,
                    first_seen,
                    last_seen,
                    alert_count,
                    correlation_window_seconds,
                    created_at,
                ),
            )

            connection.commit()

            return int(
                cursor.lastrowid
            )

    # ---------------------------------------------------------
    # Find open incident
    # ---------------------------------------------------------

    def get_open_incident(
        self,
        *,
        source_host: str,
        rule_id: str,
    ) -> sqlite3.Row | None:
        """Return the latest open incident for host/rule."""

        with self._connect() as connection:

            return connection.execute(
                """
                SELECT *
                FROM incidents
                WHERE source_host = ?
                  AND rule_id = ?
                  AND status = 'OPEN'
                ORDER BY id DESC
                LIMIT 1
                """,
                (
                    source_host,
                    rule_id,
                ),
            ).fetchone()

    # ---------------------------------------------------------
    # Update
    # ---------------------------------------------------------

    def update_incident(
        self,
        incident_id: int,
        *,
        last_seen: str,
        alert_count: int,
    ) -> None:
        """Update an existing incident."""

        with self._connect() as connection:

            connection.execute(
                """
                UPDATE incidents
                SET
                    last_seen = ?,
                    alert_count = ?
                WHERE id = ?
                """,
                (
                    last_seen,
                    alert_count,
                    incident_id,
                ),
            )

            connection.commit()

    # ---------------------------------------------------------
    # Get
    # ---------------------------------------------------------

    def get_incident(
        self,
        incident_id: int,
    ) -> sqlite3.Row | None:
        """Return incident by ID."""

        with self._connect() as connection:

            return connection.execute(
                """
                SELECT *
                FROM incidents
                WHERE id = ?
                """,
                (incident_id,),
            ).fetchone()

    # ---------------------------------------------------------
    # Close
    # ---------------------------------------------------------

    def close_incident(
        self,
        incident_id: int,
    ) -> None:
        """Close an incident."""

        with self._connect() as connection:

            connection.execute(
                """
                UPDATE incidents
                SET status = 'CLOSED'
                WHERE id = ?
                """,
                (incident_id,),
            )

            connection.commit()

    # ---------------------------------------------------------
    # Close stale incidents
    # ---------------------------------------------------------

    def close_stale_incidents(
        self,
        *,
        now: datetime | None = None,
    ) -> int:
        """
        Close open incidents whose last_seen is older than
        their configured correlation window.

        Returns the number of incidents closed.
        """

        if now is None:
            now = datetime.now(
                timezone.utc
            )

        if now.tzinfo is None:
            now = now.replace(
                tzinfo=timezone.utc
            )

        closed_count = 0

        with self._connect() as connection:

            rows = connection.execute(
                """
                SELECT
                    id,
                    last_seen,
                    correlation_window_seconds
                FROM incidents
                WHERE status = 'OPEN'
                """
            ).fetchall()

            for row in rows:

                try:

                    last_seen = datetime.fromisoformat(
                        str(row["last_seen"])
                    )

                except ValueError:

                    continue

                if last_seen.tzinfo is None:
                    last_seen = last_seen.replace(
                        tzinfo=timezone.utc
                    )

                elapsed_seconds = (
                    now - last_seen
                ).total_seconds()

                window_seconds = int(
                    row["correlation_window_seconds"]
                )

                if elapsed_seconds > window_seconds:

                    connection.execute(
                        """
                        UPDATE incidents
                        SET status = 'CLOSED'
                        WHERE id = ?
                          AND status = 'OPEN'
                        """,
                        (
                            int(row["id"]),
                        ),
                    )

                    closed_count += 1

            connection.commit()

        return closed_count

    # ---------------------------------------------------------
    # Alert relation
    # ---------------------------------------------------------

    def attach_alert(
        self,
        alert_id: int,
        incident_id: int,
    ) -> None:
        """Attach an alert to an incident."""

        with self._connect() as connection:

            connection.execute(
                """
                UPDATE alerts
                SET incident_id = ?
                WHERE id = ?
                """,
                (
                    incident_id,
                    alert_id,
                ),
            )

            connection.commit()

    # ---------------------------------------------------------
    # Incident alerts
    # ---------------------------------------------------------

    def get_incident_alerts(
        self,
        incident_id: int,
    ) -> list[sqlite3.Row]:
        """Return alerts belonging to an incident."""

        with self._connect() as connection:

            return connection.execute(
                """
                SELECT *
                FROM alerts
                WHERE incident_id = ?
                ORDER BY created_at ASC
                """,
                (incident_id,),
            ).fetchall()

# ---------------------------------------------------------
# AI Risk
# ---------------------------------------------------------

    def update_ai_risk(
        self,
        incident_id: int,
        *,
        ai_risk: str,
        risk_score: int,
    ) -> None:
        """Update incident AI risk and normalized risk score."""

        with self._connect() as connection:

            connection.execute(
                """
                UPDATE incidents
                SET
                    ai_risk = ?,
                    risk_score = ?
                WHERE id = ?
                """,
                (
                    ai_risk,
                    risk_score,
                    incident_id,
                ),
            )

            connection.commit()
