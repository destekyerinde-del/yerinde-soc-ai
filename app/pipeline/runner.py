"""
YERİNDE SOC AI
SOC Pipeline Runner

Gmail -> Wazuh Parser -> Level Filter
-> SQLite -> Duplicate Filter
-> Correlation -> Incident Manager
-> Ollama AI -> SQLite
-> Telegram -> SQLite -> Processed

Parser tarafından çıkarılan teknik kanıtlar
Telegram bildiriminin içine de eklenir.
"""

from __future__ import annotations

import logging
import time

from app.ai.ollama_client import OllamaClient
from app.ai.response_parser import AIResponseParser
from app.clients.gmail_client import GmailClient
from app.clients.telegram_client import TelegramClient
from app.parsers.wazuh_parser import WazuhParser
from app.storage.alert_store import AlertStore
from app.services.incident_manager import IncidentManager
from app.core.config import CONFIG
from app.core.logger import LOGGER


class SOCPipeline:
    """Main YERİNDE SOC AI processing pipeline."""

    def __init__(self) -> None:

        self.logger = logging.getLogger(
            "yerinde-soc-ai.pipeline"
        )

        self.logger.setLevel(
            LOGGER.level
        )

        if not self.logger.handlers:
            for handler in LOGGER.handlers:
                self.logger.addHandler(handler)

        self.parser = WazuhParser()
        self.ai = OllamaClient()
        self.telegram = TelegramClient()
        self.store = AlertStore()
        self.incidents = IncidentManager()

    # ---------------------------------------------------------
    # TECHNICAL EVIDENCE FORMAT
    # ---------------------------------------------------------

    @staticmethod
    def _technical_evidence(alert) -> str:
        """
        Format parser-extracted technical evidence.

        Only values actually present in the Wazuh alert
        are displayed.
        """

        fields = [
            ("Event ID", alert.event_id),
            ("Username", alert.username),
            ("Source IP", alert.source_ip),
            ("Source Port", alert.source_port),
            ("Logon Type", alert.logon_type),
            ("Authentication", alert.authentication_package),
            ("Logon Process", alert.logon_process),
            ("Workstation", alert.workstation),
            ("Status", alert.status),
            ("Sub Status", alert.sub_status),
            ("CVE", alert.cve),
        ]

        lines = []

        for label, value in fields:

            if value is not None:
                lines.append(
                    f"🔹 {label:<15}: {value}"
                )

        if not lines:
            return "🔹 Teknik kanıt bulunamadı."

        return "\n".join(lines)

    # ---------------------------------------------------------
    # ONE CYCLE
    # ---------------------------------------------------------

    def run_once(self) -> None:
        """Process currently unread Gmail messages."""

        self.logger.info(
            "SOC pipeline başlatılıyor."
        )

        # -----------------------------------------------------
        # INCIDENT LIFECYCLE
        # -----------------------------------------------------

        try:

            closed_incidents = (
                self.incidents.close_stale_incidents()
            )

            self.logger.info(
                "Stale incident temizliği tamamlandı: "
                "kapatılan=%s",
                closed_incidents,
            )

        except Exception:

            self.logger.exception(
                "Stale incident temizliği başarısız."
            )

        # -----------------------------------------------------
        # OLLAMA HEALTH
        # -----------------------------------------------------

        if not self.ai.health():

            self.logger.error(
                "Ollama hazır değil. Pipeline durduruldu."
            )

            return

        self.logger.info(
            "Ollama hazır."
        )

        # -----------------------------------------------------
        # TELEGRAM HEALTH
        # -----------------------------------------------------

        if not self.telegram.health():

            self.logger.error(
                "Telegram hazır değil. Pipeline durduruldu."
            )

            return

        self.logger.info(
            "Telegram hazır."
        )

        # -----------------------------------------------------
        # GMAIL
        # -----------------------------------------------------

        with GmailClient() as gmail:

            messages = (
                gmail.fetch_unread_messages()
            )

            self.logger.info(
                "Okunmamış Gmail sayısı: %d",
                len(messages),
            )

            # -------------------------------------------------
            # PROCESS MESSAGES
            # -------------------------------------------------

            for message in messages:

                alert = self.parser.parse(
                    message
                )

                self.logger.info(
                    "Wazuh alarmı bulundu: "
                    "mail_id=%s level=%s",
                    alert.mail_id,
                    alert.rule_level,
                )

                # ---------------------------------------------
                # LEVEL FILTER
                # ---------------------------------------------

                if not self.parser.is_accepted(
                    alert
                ):

                    self.logger.info(
                        "Level < %d, AI analizi "
                        "yapılmayacak: %s",
                        self.parser.MIN_LEVEL,
                        alert.mail_id,
                    )

                    gmail.mark_seen(
                        alert.mail_id
                    )

                    continue

                # ---------------------------------------------
                # SQLITE DUPLICATE CHECK
                # ---------------------------------------------

                alert_key = (
                    alert.message_id
                    or alert.mail_id
                )

                existing_alert_id = (
                    self.store.get_existing_alert_id(
                        message_id=alert.message_id,
                        mail_id=alert.mail_id,
                    )
                )

                if existing_alert_id is not None:

                    existing_alert = (
                        self.store.get_alert(
                            existing_alert_id
                        )
                    )

                    if not existing_alert:
                        self.logger.warning(
                            "Mevcut SQLite kaydı bulunamadı: "
                            "db_id=%s mail_id=%s",
                            existing_alert_id,
                            alert.mail_id,
                        )

                        gmail.mark_seen(
                            alert.mail_id
                        )

                        continue

                    existing_ai_status = (
                        existing_alert["ai_status"]
                    )

                    existing_processed = (
                        existing_alert["processed"]
                    )

                    if (
                        existing_ai_status == "FAILED"
                        and not existing_processed
                    ):

                        sqlite_alert_id = (
                            existing_alert_id
                        )

                        self.logger.warning(
                            "SQLite FAILED alarm yeniden "
                            "işlenecek: db_id=%s mail_id=%s",
                            sqlite_alert_id,
                            alert.mail_id,
                        )

                    else:

                        self.logger.info(
                            "SQLite duplicate alarm atlandı: "
                            "db_id=%s mail_id=%s ai=%s "
                            "processed=%s",
                            existing_alert_id,
                            alert.mail_id,
                            existing_ai_status,
                            existing_processed,
                        )

                        gmail.mark_seen(
                            alert.mail_id
                        )

                        continue

                else:
                    # ---------------------------------------------
                    # SQLITE CREATE ALERT
                    # ---------------------------------------------

                    try:

                        sqlite_alert_id = (
                            self.store.create_alert(
                                mail_id=str(alert.mail_id),
                                message_id=alert.message_id,
                                subject=alert.subject,
                                rule_level=alert.rule_level,
                                alert_body=alert.body,
                                source_host=alert.source_host,
                                rule_id=alert.rule_id,
                                rule_description=alert.rule_description,
                            )
                        )

                        self.logger.info(
                            "SQLite alarm kaydı oluşturuldu: "
                            "db_id=%s mail_id=%s",
                            sqlite_alert_id,
                            alert.mail_id,
                        )

                    except Exception:

                        self.logger.exception(
                            "SQLite alarm kaydı başarısız: %s",
                            alert.mail_id,
                        )

                        continue

                # ---------------------------------------------
                # CORRELATION
                # ---------------------------------------------

                try:

                    correlation_count = (
                        self.store.get_correlation_count(
                            sqlite_alert_id,
                            window_seconds=600,
                        )
                    )

                    self.store.save_correlation(
                        sqlite_alert_id,
                        correlation_count=correlation_count,
                        window_seconds=600,
                    )

                    self.logger.info(
                        "Alarm correlation: "
                        "db_id=%s mail_id=%s "
                        "source=%s rule=%s count=%s "
                        "window=%ss",
                        sqlite_alert_id,
                        alert.mail_id,
                        alert.source_host,
                        alert.rule_id,
                        correlation_count,
                        600,
                    )

                except Exception:

                    self.logger.exception(
                        "Correlation hesaplanamadı: %s",
                        alert.mail_id,
                    )

                    continue

                # ---------------------------------------------
                # INCIDENT MANAGER
                # ---------------------------------------------

                try:

                    alert_record = self.store.get_alert(
                        sqlite_alert_id
                    )

                    if not alert_record:
                        raise RuntimeError(
                            "SQLite alarm kaydı bulunamadı."
                        )

                    incident_id = (
                        self.incidents.process_alert(
                            alert_id=sqlite_alert_id,
                            source_host=alert.source_host,
                            rule_id=alert.rule_id,
                            created_at=(
                                alert_record["created_at"]
                            ),
                            correlation_window_seconds=600,
                        )
                    )

                    self.logger.info(
                        "Incident oluşturuldu/güncellendi: "
                        "db_id=%s incident_id=%s",
                        sqlite_alert_id,
                        incident_id,
                    )

                except Exception:

                    self.logger.exception(
                        "Incident işlemi başarısız: %s",
                        alert.mail_id,
                    )

                    continue

                # ---------------------------------------------
                # AI ANALYSIS
                # ---------------------------------------------

                self.logger.info(
                    "AI analizi başlıyor: %s",
                    alert.mail_id,
                )

                try:

                    raw_result = (
                        self.ai.analyze_wazuh_alert(
                            alert,
                            correlation_count=correlation_count,
                            correlation_window_seconds=600,
                        )
                    )

                    analysis = (
                        AIResponseParser.parse(
                            raw_result
                        )
                    )

                    result = analysis.format()

                    # -----------------------------------------
                    # SAVE AI RESULT
                    # -----------------------------------------

                    self.store.save_ai_analysis(
                        sqlite_alert_id,
                        risk=analysis.risk,
                        reason=analysis.reason,
                        recommendation=analysis.recommendation,
                    )

                    # -----------------------------------------
                    # SAVE INCIDENT AI RISK
                    # -----------------------------------------

                    risk_scores = {
                        "DÜŞÜK": 25,
                        "ORTA": 50,
                        "YÜKSEK": 75,
                        "KRİTİK": 100,
                    }

                    risk_score = risk_scores.get(
                        analysis.risk,
                        0,
                    )

                    self.incidents.update_ai_risk(
                        incident_id,
                        ai_risk=analysis.risk,
                        risk_score=risk_score,
                    )

                    self.logger.info(
                        "Incident AI riski güncellendi: "
                        "incident_id=%s risk=%s score=%s",
                        incident_id,
                        analysis.risk,
                        risk_score,
                    )

                except Exception:

                    self.store.mark_ai_failed(
                        sqlite_alert_id
                    )

                    self.logger.exception(
                        "AI analizi başarısız: %s",
                        alert.mail_id,
                    )

                    continue

                # TECHNICAL EVIDENCE
                # ---------------------------------------------

                technical_evidence = (
                    self._technical_evidence(alert)
                )

                # ---------------------------------------------
                # TELEGRAM MESSAGE
                # ---------------------------------------------

                telegram_message = (
    "🛡️ YERİNDE SOC AI\n\n"
    "🚨 WAZUH ALARMI\n"
    "━━━━━━━━━━━━━━━━━━\n"
  		 f"🆔 Incident ID    : {incident_id}\n"
   		 f"🖥️ Etkilenen PC  : {alert.source_host}\n"
  		 f"🌐 Etkileyen IP  : {alert.source_ip or 'UNKNOWN'}\n"
  		 f"💻 Etkileyen PC  : {alert.workstation or 'UNKNOWN'}\n"
		 f"🔢 Rule Level    : {alert.rule_level}\n"
		 f"📋 Rule ID       : {alert.rule_id}\n"
		 f"⚠️ Rule          : {alert.rule_description}\n"
		 f"📧 Mail ID       : {alert.mail_id}\n\n"
                    "🔎 TEKNİK KANITLAR\n"
                    "━━━━━━━━━━━━━━━━━━\n"
                    f"{technical_evidence}\n\n"
                    "🤖 AI ANALİZİ\n"
                    "━━━━━━━━━━━━━━━━━━\n"
                    f"{result}\n"
                    "━━━━━━━━━━━━━━━━━━"
                )

                self.logger.info(
                    "Telegram bildirimi gönderiliyor: %s",
                    alert.mail_id,
                )

                telegram_ok = (
                    self.telegram.send_message(
                        telegram_message
                    )
                )

                # ---------------------------------------------
                # TELEGRAM FAILURE
                # ---------------------------------------------

                if not telegram_ok:

                    self.store.mark_telegram_failed(
                        sqlite_alert_id
                    )

                    self.logger.error(
                        "Telegram bildirimi başarısız: %s",
                        alert.mail_id,
                    )

                    continue

                # ---------------------------------------------
                # SQLITE TELEGRAM STATUS
                # ---------------------------------------------

                try:

                    self.store.mark_telegram_sent(
                        sqlite_alert_id
                    )

                except Exception:

                    self.logger.exception(
                        "Telegram durumu SQLite'a "
                        "kaydedilemedi: %s",
                        alert.mail_id,
                    )

                    continue

                self.logger.info(
                    "Telegram bildirimi başarılı: %s",
                    alert.mail_id,
                )

                # ---------------------------------------------
                # CONSOLE OUTPUT
                # ---------------------------------------------

                print()
                print("=" * 70)
                print(
                    "YERİNDE SOC AI - WAZUH ANALİZ"
                )
                print("=" * 70)
                print()
                print(
                    f"DB ID       : {sqlite_alert_id}"
                )
                print(
                    f"Incident ID : {incident_id}"
                )
                print(
                    f"Mail ID     : {alert.mail_id}"
                )
                print(
                    f"Rule Level  : {alert.rule_level}"
                )
                print(
                    f"Source PC   : {alert.source_host}"
                )
                print(
                    f"Subject     : {alert.subject}"
                )
                print()
                print(
                    "TEKNİK KANITLAR"
                )
                print(
                    technical_evidence
                )
                print()
                print(
                    "AI ANALİZİ"
                )
                print(
                    result
                )
                print()
                print(
                    "Telegram    : GÖNDERİLDİ"
                )
                print()
                print(
                    "=" * 70
                )
                print()

                # ---------------------------------------------
                # SUCCESS
                # ---------------------------------------------

                try:

                    self.store.mark_processed(
                        sqlite_alert_id
                    )

                    gmail.mark_seen(
                        alert.mail_id
                    )

                except Exception:

                    self.logger.exception(
                        "Alarm başarıyla işlendi ancak "
                        "son kayıt aşamasında hata oluştu: %s",
                        alert.mail_id,
                    )

                    continue

                self.logger.info(
                    "Alarm başarıyla işlendi: %s",
                    alert.mail_id,
                )


# -------------------------------------------------------------
# CONTINUOUS MODE
# -------------------------------------------------------------

def main() -> None:
    """Run SOC pipeline continuously."""

    pipeline = SOCPipeline()

    LOGGER.info(
        "YERİNDE SOC AI sürekli çalışma modu başlatıldı."
    )

    while True:

        try:

            pipeline.run_once()

        except KeyboardInterrupt:

            LOGGER.info(
                "YERİNDE SOC AI durduruldu."
            )

            break

        except Exception:

            LOGGER.exception(
                "Pipeline döngüsünde beklenmeyen hata."
            )

        LOGGER.info(
            "Sonraki kontrol %d saniye sonra.",
            CONFIG.check_interval,
        )

        time.sleep(
            CONFIG.check_interval
        )


if __name__ == "__main__":
    main()
