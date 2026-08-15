"""
YERİNDE SOC AI
AI Response Parser

Ollama çıktısını güvenli ve standart SOC formatına dönüştürür.
Hem standart Türkçe formatı hem de Wazuh fine-tuned model formatını destekler.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class AIAnalysis:
    """Validated AI security analysis."""

    risk: str
    reason: str
    recommendation: str

    def format(self) -> str:
        """Return standardized SOC output."""

        return (
            f'RİSK: "{self.risk}"\n'
            f'SEBEP: "{self.reason}"\n'
            f'ÖNERİ: "{self.recommendation}"'
        )


class AIResponseParser:
    """Validate and normalize Ollama responses."""

    REQUIRED_FIELDS = (
        "RİSK",
        "SEBEP",
        "ÖNERİ",
    )

    EXTRA_SECTIONS = (
        "Analiz",
        "Analysis",
        "Açıklama",
        "Explanation",
        "Detay",
        "Detail",
        "Investigation Guidance",
        "Investigation",
        "Guidance",
    )

    # ---------------------------------------------------------
    # Public API
    # ---------------------------------------------------------

    @classmethod
    def parse(cls, response: str) -> AIAnalysis:
        """
        Parse and normalize Ollama response.

        Supported formats:

        1. Standard SOC format:

            RİSK: ORTA
            SEBEP: ...
            ÖNERİ: ...

        2. Wazuh model format:

            Risk Assessment: ORTA
            Detailed Reasoning: ...
            Recommended Actions: ...
        """

        if not isinstance(response, str):
            raise ValueError(
                "AI cevabı metin değil."
            )

        text = response.strip()

        if not text:
            raise ValueError(
                "AI cevabı boş."
            )

        # -----------------------------------------------------
        # First: our standard format
        # -----------------------------------------------------

        risk = cls._extract(
            text,
            "RİSK",
        )

        reason = cls._extract(
            text,
            "SEBEP",
        )

        recommendation = cls._extract(
            text,
            "ÖNERİ",
        )

        # -----------------------------------------------------
        # Second: Wazuh fine-tuned model format
        # -----------------------------------------------------

        if not risk:
            risk = cls._extract_wazuh(
                text,
                (
                    "Risk Assessment",
                    "Risk",
                ),
            )

        if not reason:
            reason = cls._extract_wazuh(
                text,
                (
                    "Detailed Reasoning",
                    "Reasoning",
                    "Detailed Reason",
                ),
            )

        if not recommendation:
            recommendation = cls._extract_wazuh(
                text,
                (
                    "Recommended Actions",
                    "Recommended Action",
                    "Recommendation",
                ),
            )

        # -----------------------------------------------------
        # Validate
        # -----------------------------------------------------

        risk = cls._clean(risk)
        reason = cls._clean(reason)
        recommendation = cls._clean(
            recommendation
        )

        # -----------------------------------------------------
        # Normalize risk
        # -----------------------------------------------------

        risk = cls._normalize_risk(risk)

        if not risk:
            raise ValueError(
                "AI cevabında geçerli RİSK bulunamadı."
            )

        if not reason:
            raise ValueError(
                "AI cevabında SEBEP bulunamadı."
            )

        if not recommendation:
            raise ValueError(
                "AI cevabında ÖNERİ bulunamadı."
            )

        return AIAnalysis(
            risk=risk,
            reason=reason,
            recommendation=recommendation,
        )

    # ---------------------------------------------------------
    # Standard format extraction
    # ---------------------------------------------------------

    @classmethod
    def _extract(
        cls,
        text: str,
        field: str,
    ) -> str:
        """Extract standard SOC field."""

        next_fields = (
            r"RİSK"
            r"|SEBEP"
            r"|ÖNERİ"
        )

        extra_sections = "|".join(
            re.escape(section)
            for section in cls.EXTRA_SECTIONS
        )

        pattern = rf"""
            {re.escape(field)}
            \s*:
            \s*
            (.+?)
            (?=

\s*
                (?:{next_fields})
                \s*:
                |

\s*
                (?:{extra_sections})
                \s*:
                |
                $
            )
        """

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
            | re.VERBOSE
            | re.DOTALL,
        )

        if not match:
            return ""

        return match.group(1).strip()

    # ---------------------------------------------------------
    # Wazuh model extraction
    # ---------------------------------------------------------

    @classmethod
    def _extract_wazuh(
        cls,
        text: str,
        fields: tuple[str, ...],
    ) -> str:
        """Extract field from Wazuh fine-tuned model output."""

        escaped_fields = "|".join(
            re.escape(field)
            for field in fields
        )

        all_wazuh_fields = (
            "Rule Level",
            "Event Type",
            "Detailed Reasoning",
            "Risk Assessment",
            "Recommended Actions",
            "MITRE ATT&CK",
            "MITRE Technique",
            "Risk",
            "Reasoning",
            "Recommended Action",
            "Recommendation",
        )

        next_fields = "|".join(
            re.escape(field)
            for field in all_wazuh_fields
        )

        pattern = rf"""
            (?:{escaped_fields})
            \s*:
            \s*
            (.+?)
            (?=

\s*
                (?:{next_fields})
                \s*:
                |
                $
            )
        """

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
            | re.VERBOSE
            | re.DOTALL,
        )

        if not match:
            return ""

        return match.group(1).strip()

    # ---------------------------------------------------------
    # Risk normalization
    # ---------------------------------------------------------

    @staticmethod
    def _normalize_risk(
        value: str,
    ) -> str:
        """Normalize risk level."""

        value = value.strip()

        # Remove surrounding quotes.
        value = value.strip('"').strip("'").strip()

        # Remove accidental prefixes.
        value = re.sub(
            r"^(Risk Assessment|Risk)\s*:\s*",
            "",
            value,
            flags=re.IGNORECASE,
        ).strip()

        value_upper = value.upper()

        allowed = (
            "DÜŞÜK",
            "ORTA",
            "YÜKSEK",
            "KRİTİK",
        )

        for risk in allowed:
            if value_upper == risk:
                return risk

        # English model output fallback.
        english_map = {
            "LOW": "DÜŞÜK",
            "MEDIUM": "ORTA",
            "MODERATE": "ORTA",
            "HIGH": "YÜKSEK",
            "CRITICAL": "KRİTİK",
        }

        return english_map.get(
            value_upper,
            "",
        )

    # ---------------------------------------------------------
    # Cleaning
    # ---------------------------------------------------------

    @staticmethod
    def _clean(
        value: str,
    ) -> str:
        """Clean AI-generated field."""

        value = value.strip()

        if not value:
            return ""

        # -----------------------------------------------------
        # Remove known section if it starts on same line.
        # -----------------------------------------------------

        value = re.split(
            r"\s+(?:Analiz|Analysis|"
            r"Açıklama|Explanation|"
            r"Detay|Detail|"
            r"Investigation Guidance|"
            r"Investigation|Guidance)"
            r"\s*:",
            value,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]

        # -----------------------------------------------------
        # Remove markdown bullets.
        # -----------------------------------------------------

        value = re.sub(
            r"^\s*[-*#]+\s*",
            "",
            value,
        )

        # -----------------------------------------------------
        # If the AI returns a quoted sentence followed by
        # an extra explanation, keep only the quoted sentence.
        #
        # Example:
        # "Hata kodunu kontrol edin." Bu cevap ...
        #
        # becomes:
        # Hata kodunu kontrol edin.
        # -----------------------------------------------------

        value = value.strip()

        if len(value) >= 2 and value.startswith('"'):
            closing_quote = value.find('"', 1)

            if closing_quote > 0:
                value = value[1:closing_quote]

        elif len(value) >= 2 and value.startswith("'"):
            closing_quote = value.find("'", 1)

            if closing_quote > 0:
                value = value[1:closing_quote]

        # -----------------------------------------------------
        # Collapse whitespace.
        # -----------------------------------------------------

        value = re.sub(
            r"\s+",
            " ",
            value,
        )

        return value.strip()
