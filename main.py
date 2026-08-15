import logging
import signal
import sys
import threading
import time

import uvicorn

from app.pipeline.runner import main as pipeline_main


# ============================================================
# YERİNDE SOC AI
# ANA SİSTEM
# ============================================================

APP_NAME = "YERİNDE SOC AI"

HOST = "0.0.0.0"
PORT = 8000

LOGGER = logging.getLogger("yerinde-soc-main")


# ============================================================
# LOGGING
# ============================================================

def configure_logging():
    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s | "
            "%(levelname)-8s | "
            "%(name)s | "
            "%(message)s"
        ),
    )


# ============================================================
# SIGNAL CONTROL
# ============================================================

_shutdown_event = threading.Event()


def handle_signal(signum, frame):
    LOGGER.info(
        "%s durdurma sinyali aldı: %s",
        APP_NAME,
        signum,
    )

    _shutdown_event.set()


# ============================================================
# PIPELINE
# ============================================================

def run_pipeline():
    """
    Gmail -> Parser -> Incident -> Ollama -> Telegram
    pipeline'ını çalıştırır.
    """

    LOGGER.info(
        "SOC Pipeline başlatılıyor."
    )

    while not _shutdown_event.is_set():

        try:
            pipeline_main()

        except KeyboardInterrupt:
            LOGGER.info(
                "SOC Pipeline kullanıcı tarafından durduruldu."
            )
            break

        except Exception:
            LOGGER.exception(
                "SOC Pipeline beklenmeyen hata ile durdu."
            )

            if _shutdown_event.wait(5):
                break

    LOGGER.info(
        "SOC Pipeline kapatıldı."
    )


# ============================================================
# DASHBOARD
# ============================================================

def run_dashboard():
    """
    Web Dashboard.
    """

    LOGGER.info(
        "SOC Dashboard başlatılıyor: "
        "http://0.0.0.0:%s",
        PORT,
    )

    try:

        uvicorn.run(
            "app.web.main:app",
            host=HOST,
            port=PORT,
            log_level="info",
            access_log=True,
        )

    except Exception:
        LOGGER.exception(
            "Dashboard başlatılamadı."
        )

        raise


# ============================================================
# HEALTH
# ============================================================

def pipeline_monitor(thread):
    """
    Pipeline thread'inin canlı olup olmadığını izler.
    """

    while not _shutdown_event.is_set():

        if not thread.is_alive():

            LOGGER.error(
                "KRİTİK: SOC Pipeline thread'i çalışmıyor."
            )

            # Pipeline tekrar başlatılıyor.
            LOGGER.warning(
                "SOC Pipeline yeniden başlatılıyor."
            )

            new_thread = threading.Thread(
                target=run_pipeline,
                name="soc-pipeline",
                daemon=True,
            )

            new_thread.start()

            thread = new_thread

            LOGGER.info(
                "SOC Pipeline yeniden aktif."
            )

        _shutdown_event.wait(10)


# ============================================================
# MAIN
# ============================================================

def main():

    configure_logging()

    signal.signal(
        signal.SIGINT,
        handle_signal,
    )

    signal.signal(
        signal.SIGTERM,
        handle_signal,
    )

    LOGGER.info("=" * 70)
    LOGGER.info(
        "%s ANA SİSTEM BAŞLATILIYOR",
        APP_NAME,
    )
    LOGGER.info("=" * 70)

    # --------------------------------------------------------
    # PIPELINE THREAD
    # --------------------------------------------------------

    pipeline_thread = threading.Thread(
        target=run_pipeline,
        name="soc-pipeline",
        daemon=True,
    )

    pipeline_thread.start()

    LOGGER.info(
        "SOC Pipeline aktif."
    )

    # --------------------------------------------------------
    # PIPELINE MONITOR
    # --------------------------------------------------------

    monitor_thread = threading.Thread(
        target=pipeline_monitor,
        args=(pipeline_thread,),
        name="soc-pipeline-monitor",
        daemon=True,
    )

    monitor_thread.start()

    LOGGER.info(
        "SOC Pipeline monitor aktif."
    )

    # --------------------------------------------------------
    # DASHBOARD
    # --------------------------------------------------------

    try:

        run_dashboard()

    except KeyboardInterrupt:

        LOGGER.info(
            "%s kullanıcı tarafından durduruldu.",
            APP_NAME,
        )

    except Exception:

        LOGGER.exception(
            "%s Dashboard sonlandı.",
            APP_NAME,
        )

        _shutdown_event.set()

        raise

    finally:

        _shutdown_event.set()

        LOGGER.info(
            "%s ana süreç kapatılıyor.",
            APP_NAME,
        )

        # Thread'lerin kapanması için kısa süre.
        time.sleep(1)

        LOGGER.info(
            "%s tamamen durduruldu.",
            APP_NAME,
        )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    try:
        main()

    except KeyboardInterrupt:
        LOGGER.info(
            "%s kapatıldı.",
            APP_NAME,
        )

        sys.exit(0)

    except Exception:
        LOGGER.exception(
            "%s başlatılamadı.",
            APP_NAME,
        )

        sys.exit(1)
