"""
=============================================================
YERİNDE SOC AI
Banner & Console UI Manager

Version : 2.2 Stable
Author  : Yerinde POM
=============================================================
"""

from __future__ import annotations

import os
import platform
import shutil
import time

from app.version import APP


LINE = "═"


def terminal_width() -> int:
    """Return terminal width."""

    try:
        return shutil.get_terminal_size().columns
    except Exception:
        return 70


def separator() -> None:
    """Print separator line."""

    print(LINE * terminal_width())


def clear() -> None:
    """Clear console."""

    os.system("cls" if os.name == "nt" else "clear")


def pause(seconds: float = 0.25) -> None:
    """Small animation delay."""

    time.sleep(seconds)


def banner() -> None:
    """Show application banner."""

    clear()

    separator()

    print(
        r"""
██╗   ██╗███████╗██████╗ ██╗███╗   ██╗██████╗ ███████╗
╚██╗ ██╔╝██╔════╝██╔══██╗██║████╗  ██║██╔══██╗██╔════╝
 ╚████╔╝ █████╗  ██████╔╝██║██╔██╗ ██║██║  ██║█████╗
  ╚██╔╝  ██╔══╝  ██╔══██╗██║██║╚██╗██║██║  ██║██╔══╝
   ██║   ███████╗██║  ██║██║██║ ╚████║██████╔╝███████╗
   ╚═╝   ╚══════╝╚═╝  ╚═╝╚═╝╚═╝  ╚═══╝╚═════╝ ╚══════╝
"""
    )

    print("               SOC AI")
    print("     AI Powered Security Operations Center\n")

    print(f"Version  : {APP.version}")
    print(f"Codename : {APP.codename}")
    print(f"AI Model : {APP.ai_model}")
    print(f"Python   : {platform.python_version()}")
    print(f"Platform : {platform.system()} {platform.release()}")

    separator()


def boot_step(title: str, delay: float = 0.20) -> None:
    """Display boot progress."""

    print(f"[BOOT] {title:.<42} OK")
    pause(delay)


def boot_screen() -> None:
    """Display startup sequence."""

    separator()

    boot_step("Loading Configuration")
    boot_step("Initializing Logger")
    boot_step("Loading Templates")
    boot_step("Connecting Gmail")
    boot_step("Connecting Telegram")
    boot_step("Connecting Ollama")
    boot_step("Loading AI Engine")
    boot_step("Preparing Duplicate Filter")

    separator()


def system_status(
    gmail: bool,
    telegram: bool,
    ollama: bool,
    duplicate: bool,
) -> None:
    """Show current component status."""

    separator()

    print("SYSTEM STATUS\n")

    print(f"Gmail ................. {'READY' if gmail else 'FAILED'}")
    print(f"Telegram .............. {'READY' if telegram else 'FAILED'}")
    print(f"Ollama ............... {'READY' if ollama else 'FAILED'}")
    print(f"Duplicate Filter ...... {'READY' if duplicate else 'FAILED'}")

    separator()


def alert_header() -> None:
    """Show alert section header."""

    separator()

    print("NEW SECURITY ALERT")

    separator()


def summary(stats: dict) -> None:
    """Display runtime summary."""

    separator()

    print("SESSION SUMMARY\n")

    print(f"Total Alerts     : {stats.get('total',0)}")
    print(f"AI Analysis      : {stats.get('ai',0)}")
    print(f"System Alerts    : {stats.get('system',0)}")
    print(f"Duplicates       : {stats.get('duplicate',0)}")
    print(f"Telegram         : {stats.get('telegram',0)}")

    separator()


def goodbye() -> None:
    """Display shutdown message."""

    separator()

    print("YERİNDE SOC AI")
    print("Session Finished Successfully")

    separator()
