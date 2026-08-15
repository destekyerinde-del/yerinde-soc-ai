"""
YERİNDE SOC AI
Incident Manager

Wazuh alarmını mevcut açık incident ile ilişkilendirir
veya yeni incident oluşturur.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.storage.incident_store import IncidentStore


class IncidentManager:
    """Manage SOC incident lifecycle."""

    def __init__(
        self,
        store: IncidentStore | None = None,
    ) -> None:

        self.store = (
            store
            if store is not None
            else IncidentStore()
        )


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
        """Update AI risk information for an incident."""

        self.store.update_ai_risk(
            incident_id,
            ai_risk=ai_risk,
            risk_score=risk_score,
        )


    # ---------------------------------------------------------
    # Process alert
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

        return self.store.close_stale_incidents(
            now=now
        )

    # ---------------------------------------------------------
    # Process alert
    # ---------------------------------------------------------

    def process_alert(
        self,
        *,
        alert_id: int,
        source_host: str,
        rule_id: str,
        created_at: str,
        correlation_window_seconds: int = 600,
    ) -> int:
        """
        Attach an alert to an existing open incident
        when it is inside the correlation window.

        Otherwise create a new incident.
        """

        incident = self.store.get_open_incident(
            source_host=source_host,
            rule_id=rule_id,
        )

        # -----------------------------------------------------
        # Check existing incident
        # -----------------------------------------------------

        if incident is not None:

            incident_last_seen = str(
                incident["last_seen"]
            )

            try:

                current_time = datetime.fromisoformat(
                    created_at
                )

                last_seen_time = datetime.fromisoformat(
                    incident_last_seen
                )

                difference_seconds = abs(
                    (
                        current_time
                        - last_seen_time
                    ).total_seconds()
                )

            except ValueError:

                difference_seconds = (
                    correlation_window_seconds + 1
                )

            # -------------------------------------------------
            # Existing incident is inside window
            # -------------------------------------------------

            if difference_seconds <= (
                correlation_window_seconds
            ):

                incident_id = int(
                    incident["id"]
                )

                alert_count = int(
                    incident["alert_count"]
                ) + 1

                # Never move last_seen backwards.
                new_last_seen = max(
                    current_time,
                    last_seen_time,
                ).isoformat()

                self.store.update_incident(
                    incident_id,
                    last_seen=new_last_seen,
                    alert_count=alert_count,
                )

                self.store.attach_alert(
                    alert_id,
                    incident_id,
                )

                return incident_id

        # -----------------------------------------------------
        # Create new incident
        # -----------------------------------------------------

        incident_id = (
            self.store.create_incident(
                source_host=source_host,
                rule_id=rule_id,
                first_seen=created_at,
                last_seen=created_at,
                alert_count=1,
                correlation_window_seconds=(
                    correlation_window_seconds
                ),
            )
        )

        # -----------------------------------------------------
        # Attach alert
        # -----------------------------------------------------

        self.store.attach_alert(
            alert_id,
            incident_id,
        )

        return incident_id
