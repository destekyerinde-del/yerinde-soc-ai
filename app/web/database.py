import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = BASE_DIR / "logs" / "yerinde-soc.db"


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def get_dashboard_summary() -> dict:
    with get_connection() as connection:

        incidents = connection.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN status = 'OPEN' THEN 1 ELSE 0 END) AS open_count,
                SUM(CASE WHEN status = 'CLOSED' THEN 1 ELSE 0 END) AS closed_count,
                SUM(CASE WHEN ai_risk = 'KRİTİK' THEN 1 ELSE 0 END) AS critical_count,
                SUM(CASE WHEN ai_risk = 'YÜKSEK' THEN 1 ELSE 0 END) AS high_count,
                SUM(CASE WHEN ai_risk = 'ORTA' THEN 1 ELSE 0 END) AS medium_count,
                SUM(CASE WHEN ai_risk = 'DÜŞÜK' THEN 1 ELSE 0 END) AS low_count
            FROM incidents
            """
        ).fetchone()

        recent_incidents = connection.execute(
            """
            SELECT
                id,
                source_host,
                rule_id,
                status,
                alert_count,
                ai_risk,
                risk_score,
                first_seen,
                last_seen
            FROM incidents
            ORDER BY id DESC
            LIMIT 20
            """
        ).fetchall()

    return {
        "summary": dict(incidents),
        "recent_incidents": [
            dict(row)
            for row in recent_incidents
        ],
    }


def get_incident_detail(incident_id: int) -> dict | None:
    with get_connection() as connection:

        incident = connection.execute(
            """
            SELECT
                id,
                source_host,
                rule_id,
                status,
                first_seen,
                last_seen,
                alert_count,
                correlation_window_seconds,
                created_at,
                ai_risk,
                risk_score
            FROM incidents
            WHERE id = ?
            """,
            (incident_id,),
        ).fetchone()

        if incident is None:
            return None

        alerts = connection.execute(
            """
            SELECT
                id,
                mail_id,
                subject,
                rule_level,
                alert_body,
                ai_risk,
                ai_reason,
                ai_recommendation,
                ai_status,
                telegram_status,
                source_host,
                rule_id,
                rule_description,
                correlation_count,
                correlation_window_seconds,
                created_at,
                processed_at
            FROM alerts
            WHERE incident_id = ?
            ORDER BY id DESC
            """,
            (incident_id,),
        ).fetchall()

    return {
        "incident": dict(incident),
        "alerts": [dict(row) for row in alerts],
    }
