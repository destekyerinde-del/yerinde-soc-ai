"""
YERİNDE SOC AI
Ollama AI Client

Wazuh alarmını Ollama üzerinden analiz eder.
Parser tarafından çıkarılan teknik kanıtları
AI analizine doğrudan aktarır.
"""

from __future__ import annotations

import logging
import re
from typing import Any

import requests

from app.core.config import CONFIG


class OllamaClient:
    """Ollama API client."""

    def __init__(
        self,
        host: str | None = None,
        model: str | None = None,
        timeout: int | None = None,
    ) -> None:

        self.host = (
            host or CONFIG.ollama_host
        ).rstrip("/")

        self.model = (
            model or CONFIG.ollama_model
        )

        self.timeout = (
            timeout
            if timeout is not None
            else CONFIG.ai_timeout
        )

        self.logger = logging.getLogger(
            "yerinde-soc-ai.ollama"
        )

    # ---------------------------------------------------------
    # HEALTH
    # ---------------------------------------------------------

    def health(self) -> bool:
        """Check whether Ollama is reachable."""

        try:
            response = requests.get(
                f"{self.host}/api/tags",
                timeout=10,
            )

            return response.ok

        except requests.RequestException:

            self.logger.exception(
                "Ollama bağlantısı kontrol edilemedi."
            )

            return False

    # ---------------------------------------------------------
    # GENERATE
    # ---------------------------------------------------------

    def generate(
        self,
        prompt: str,
    ) -> str:
        """Generate an AI response."""

        if not prompt.strip():
            raise ValueError(
                "AI prompt boş olamaz."
            )

        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "keep_alive": "30m",
            "think": False,
            "options": {
                "temperature": 0,
                "num_predict": 128,
                "num_ctx": 4096,
            },
        }

        self.logger.info(
            "Ollama AI analizi başlatılıyor: %s",
            self.model,
        )

        try:

            response = requests.post(
                f"{self.host}/api/generate",
                json=payload,
                timeout=self.timeout,
            )

            response.raise_for_status()

            data = response.json()

            result = data.get(
                "response",
                "",
            )

            if not isinstance(result, str):
                raise RuntimeError(
                    "Ollama geçersiz response döndürdü."
                )

            result = result.strip().replace('"', "")

            if not result:

                self.logger.error(
                    "Ollama boş response: model=%s "
                    "done=%s done_reason=%s "
                    "thinking_len=%s",
                    data.get("model"),
                    data.get("done"),
                    data.get("done_reason"),
                    len(
                        data.get(
                            "thinking",
                            "",
                        )
                    ),
                )

                raise RuntimeError(
                    "Ollama boş response döndürdü."
                )

            self.logger.info(
                "Ollama AI analizi tamamlandı."
            )

            return result

        except requests.RequestException:

            self.logger.exception(
                "Ollama API bağlantı hatası."
            )

            raise

    # ---------------------------------------------------------
    # VALUE HELPERS
    # ---------------------------------------------------------

    @staticmethod
    def _evidence(
        value: Any,
    ) -> str:
        """
        Convert missing technical evidence to YOK.
        """

        if value is None:
            return "YOK"

        value = str(value).strip()

        return value if value else "YOK"

    # ---------------------------------------------------------
    # AI OUTPUT CLEANUP
    # ---------------------------------------------------------

    @staticmethod
    def _clean_ai_result(
        result: str,
    ) -> str:
        """
        Normalize AI output to exactly:

        RİSK:
        SEBEP:
        ÖNERİ:

        Also removes accidental quotation marks.
        """

        if not result:
            return (
                "RİSK: ORTA\n"
                "SEBEP: Alarm için yeterli teknik değerlendirme üretilemedi.\n"
                "ÖNERİ: Alarmdaki mevcut teknik kanıtlar incelenmelidir."
            )

        result = result.strip()

        # Markdown code fence temizliği
        result = re.sub(
            r"^```(?:text)?\s*",
            "",
            result,
            flags=re.IGNORECASE,
        )

        result = re.sub(
            r"\s*```$",
            "",
            result,
            flags=re.IGNORECASE,
        )

        # Sadece gerekli satırları bul
        risk_match = re.search(
            r"R[İI]SK\s*:\s*[\"']?\s*"
            r"(DÜŞÜK|ORTA|YÜKSEK|KRİTİK)"
            r"\s*[\"']?",
            result,
            flags=re.IGNORECASE,
        )

        reason_match = re.search(
            r"SEBEP\s*:\s*(.+)",
            result,
            flags=re.IGNORECASE,
        )

        recommendation_match = re.search(
            r"ÖNER[İI]\s*:\s*(.+)",
            result,
            flags=re.IGNORECASE,
        )

        risk = (
            risk_match.group(1).upper()
            if risk_match
            else "ORTA"
        )

        reason = (
            reason_match.group(1).strip()
            if reason_match
            else
            "Alarm için mevcut teknik kanıtlar değerlendirilmelidir."
        )

        recommendation = (
            recommendation_match.group(1).strip()
            if recommendation_match
            else
            "Mevcut teknik kanıtlar üzerinden inceleme yapılmalıdır."
        )

        # Tırnak temizliği
        reason = reason.strip(
            " \"'`"
        )

        recommendation = recommendation.strip(
            " \"'`"
        )

        # Satır sonlarını tek satıra indir
        reason = " ".join(
            reason.split()
        )

        recommendation = " ".join(
            recommendation.split()
        )

        # AI bazen fazladan alan ekler
        reason = re.sub(
            r"\s*(?:ÖNER[İI]|R[İI]SK)\s*:.*$",
            "",
            reason,
            flags=re.IGNORECASE,
        ).strip()

        recommendation = re.sub(
            r"\s*(?:R[İI]SK|SEBEP)\s*:.*$",
            "",
            recommendation,
            flags=re.IGNORECASE,
        ).strip()

        return (
            f"RİSK: {risk}\n"
            f"SEBEP: {reason}\n"
            f"ÖNERİ: {recommendation}"
        )

    # ---------------------------------------------------------
    # WAZUH ANALYSIS
    # ---------------------------------------------------------

    def analyze_wazuh_alert(
        self,
        alert: Any,
        *,
        correlation_count: int = 1,
        correlation_window_seconds: int = 600,
    ) -> str:
        """
        Analyze a Wazuh alert using grounded
        alert data and parser-extracted evidence.
        """

        event_id = self._evidence(
            getattr(alert, "event_id", None)
        )

        username = self._evidence(
            getattr(alert, "username", None)
        )

        source_ip = self._evidence(
            getattr(alert, "source_ip", None)
        )

        source_port = self._evidence(
            getattr(alert, "source_port", None)
        )

        logon_type = self._evidence(
            getattr(alert, "logon_type", None)
        )

        authentication = self._evidence(
            getattr(
                alert,
                "authentication_package",
                None,
            )
        )

        logon_process = self._evidence(
            getattr(
                alert,
                "logon_process",
                None,
            )
        )

        workstation = self._evidence(
            getattr(alert, "workstation", None)
        )

        status = self._evidence(
            getattr(alert, "status", None)
        )

        sub_status = self._evidence(
            getattr(alert, "sub_status", None)
        )

        source_pc = self._evidence(
            getattr(alert, "source_host", None)
        )

        rule_id = self._evidence(
            getattr(alert, "rule_id", None)
        )

        rule_description = self._evidence(
            getattr(
                alert,
                "rule_description",
                None,
            )
        )

        rule_level = self._evidence(
            getattr(alert, "rule_level", None)
        )

        cve = self._evidence(
            getattr(alert, "cve", None)
        )

        # -----------------------------------------------------
        # EXPLICIT SECURITY ROLES
        # -----------------------------------------------------
        #
        # Çok önemli:
        #
        # source_host  = ETKİLENEN PC
        # source_ip    = ETKİLEYEN IP
        # workstation  = ETKİLEYEN PC
        #
        # Özellikle Windows 4625 için bu ayrım korunur.
        # -----------------------------------------------------

        prompt = f"""
Sen deneyimli bir SOC analistisin.

Görevin, verilen Wazuh alarmını SADECE mevcut kanıtlara dayanarak
kısa ve doğru şekilde değerlendirmektir.

================ ALARM =================

Etkilenen PC:
{self._evidence(alert.source_host)}

Rule ID:
{self._evidence(alert.rule_id)}

Rule Level:
{alert.rule_level}

Rule:
{self._evidence(alert.rule_description)}

================ ETKİLEYEN TARAF =================

Etkileyen IP:
{self._evidence(getattr(alert, "source_ip", None))}

Etkileyen PC:
{self._evidence(getattr(alert, "workstation", None))}

Kullanıcı:
{self._evidence(getattr(alert, "username", None))}

================ TEKNİK KANIT =================

Event ID:
{self._evidence(getattr(alert, "event_id", None))}

Source Port:
{self._evidence(getattr(alert, "source_port", None))}

Logon Type:
{self._evidence(getattr(alert, "logon_type", None))}

Authentication:
{self._evidence(getattr(alert, "authentication_package", None))}

Logon Process:
{self._evidence(getattr(alert, "logon_process", None))}

Status:
{self._evidence(getattr(alert, "status", None))}

Sub Status:
{self._evidence(getattr(alert, "sub_status", None))}

CVE:
{self._evidence(getattr(alert, "cve", None))}

================ CORRELATION =================

Aynı kaynak PC ve Rule ID için son
{correlation_window_seconds} saniyedeki alarm sayısı:

{correlation_count}

================ ALARM METNİ =================

{alert.body}

================================================

ANALİZ KURALLARI

1. Etkilenen PC, alarmın geldiği Wazuh Agent bilgisidir.
2. Etkileyen IP, Source IP alanıdır.
3. Etkileyen PC, Workstation alanıdır.
4. Bu üç alanı birbirine kesinlikle karıştırma.
5. Event ID 4625 varsa bunu başarısız Windows oturum açma olayı
   olarak değerlendir.
6. Source IP varsa öneride bu IP'nin incelenmesini kullanabilirsin.
7. Workstation varsa öneride bu bilgisayarın incelenmesini kullanabilirsin.
8. Kullanıcı varsa kullanıcı hesabını değerlendirmeye dahil et.
9. Correlation Count yüksekse tekrar eden olayları özellikle belirt.
10. Tek bir 4625 olayını otomatik olarak saldırı, malware, exploit,
    persistence veya yetkisiz erişim olarak kesin şekilde tanımlama.
11. Kanıt yoksa bilgi uydurma.
12. MITRE tekniği alarmda açıkça yoksa MITRE tekniği üretme.
13. CVE yoksa CVE üretme.
14. IP, kullanıcı, bilgisayar, port veya hata kodu uydurma.
15. Risk değerlendirmesinde Rule Level, Rule Description,
    teknik kanıtlar ve correlation birlikte değerlendirilmelidir.

================ RİSK =================

Yalnızca:

DÜŞÜK
ORTA
YÜKSEK
KRİTİK

değerlerinden birini seç.

Rule Level 10 tek başına KRİTİK anlamına gelmez.

================ ÇIKTI =================

Cevap TAM OLARAK 3 satır olmalıdır.

RİSK: [tek değer]
SEBEP: [tek kısa ve kanıta dayalı cümle]
ÖNERİ: [tek kısa ve uygulanabilir cümle]

SEBEP içinde mümkün olduğunda olayın ilişkisini açıkça belirt:

Etkileyen PC → Etkileyen IP → Kullanıcı → Etkilenen PC

Örneğin mevcut kanıtlar varsa:

ÖRNEK-PC → 192.0.2.10 → kullanıcı → ÖRNEK-SUNUCU

Ancak eksik alanları kesinlikle uydurma.

ÖNERİ somut olmalıdır.
Örneğin Source IP ve Workstation mevcutsa,
bu kaynaktan gelen tekrar eden başarısız oturum açma olaylarının
ve ilgili hesabın incelenmesini önerebilirsin.

Kesinlikle:

- Alıntı işareti kullanma
- Markdown kullanma
- Dördüncü satır yazma
- Açıklama ekleme
- MITRE uydurma
- Saldırgan uydurma
- Saldırı gerçekleştiğini kanıtsız şekilde kesinleştirme

Yalnızca şu üç satırı döndür:

RİSK:
SEBEP:
ÖNERİ:
""".strip()

        raw_result = self.generate(
            prompt
        )

        cleaned_result = self._clean_ai_result(
            raw_result
        )

        self.logger.info(
            "Wazuh AI sonucu normalize edildi."
        )

        return cleaned_result
