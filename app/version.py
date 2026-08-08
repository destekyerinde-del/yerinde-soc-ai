"""
YERİNDE SOC AI
Version Information

Bu modül uygulamanın sürüm ve kimlik bilgilerini içerir.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class AppInfo:
    """Application metadata."""

    name: str = "YERİNDE SOC AI"
    description: str = "AI Powered Security Operations Center"

    version: str = "2.2.0"
    codename: str = "Stable"

    author: str = "Yerinde POM"
    company: str = "Yerinde SOC"

    license: str = "MIT"

    github: str = "https://github.com/yerindepom/yerinde-soc"

    ai_model: str = "qingmian/Qwen2.5-7B-CyberSecurity"

    python: str = "Python 3.12+"


APP = AppInfo()
