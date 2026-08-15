"""
YERİNDE SOC AI
Wazuh Mail Parser

Gmail'den alınan Wazuh alarm maillerini parse eder.

Amaç:

- Rule bilgilerini çıkarmak
- Etkilenen Wazuh Agent bilgisini çıkarmak
- Alarm içindeki teknik kanıtları çıkarmak
- AI ve Telegram tarafına yalnızca gerçek alarm
  içeriğinde bulunan bilgileri aktarmak
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class WazuhAlert:
    """Parsed Wazuh alert."""

    mail_id: str
    message_id: str
    subject: str
    body: str

    rule_level: int
    rule_id: str
    rule_description: str
    source_host: str

    # -----------------------------------------------------
    # Technical evidence
    # -----------------------------------------------------

    cve: str | None = None
    event_id: str | None = None

    username: str | None = None
    account_domain: str | None = None

    source_ip: str | None = None
    source_port: str | None = None

    logon_type: str | None = None
    authentication_package: str | None = None
    logon_process: str | None = None

    workstation: str | None = None

    status: str | None = None
    sub_status: str | None = None

    failure_reason: str | None = None

    error_code: str | None = None

    service_name: str | None = None
    process_name: str | None = None
    file_name: str | None = None

    # -----------------------------------------------------
    # Accepted
    # -----------------------------------------------------

    @property
    def accepted(self) -> bool:
        """Return True when alert meets minimum level."""

        return self.rule_level >= WazuhParser.MIN_LEVEL


class WazuhParser:
    """Parse Wazuh notification emails."""

    MIN_LEVEL = 9

    # ---------------------------------------------------------
    # Public API
    # ---------------------------------------------------------

    @classmethod
    def parse(
        cls,
        message: dict[str, Any],
    ) -> WazuhAlert:
        """Parse a Gmail message into a WazuhAlert."""

        body = str(
            message.get("body", "")
        )

        subject = str(
            message.get("subject", "")
        )

        mail_id = str(
            message.get("id", "")
        )

        message_id = str(
            message.get("message_id", "")
        )

        level = cls.extract_level(
            body=body,
            subject=subject,
        )

        rule_id, rule_description = (
            cls.extract_rule_info(body)
        )

        # -------------------------------------------------
        # AFFECTED PC
        #
        # Buradaki source_host:
        #
        #   ETKİLENEN PC
        #
        # Yani alarmı üreten Wazuh Agent / Windows makinesi.
        #
        # Öncelik:
        #
        # 1. agent.name
        # 2. agent.hostname
        # 3. Agent Name
        # 4. Agent Hostname
        # 5. Received From
        #
        # ÖNEMLİ:
        #
        # workstationName burada kullanılmaz.
        #
        # workstationName ayrı olarak:
        #
        #   ETKİLEYEN PC
        #
        # alanına aktarılır.
        # -------------------------------------------------

        source_host = cls.extract_source_host(
            body
        )

        return WazuhAlert(
            mail_id=mail_id,
            message_id=message_id,
            subject=subject,
            body=body,

            rule_level=level,
            rule_id=rule_id,
            rule_description=rule_description,
            source_host=source_host,

            # -------------------------------------------------
            # Technical evidence
            # -------------------------------------------------

            cve=cls.extract_cve(body),

            event_id=cls.extract_field(
                body,
                [
                    r'"eventID"\s*:\s*"([^"]+)"',
                    r'"eventId"\s*:\s*"([^"]+)"',
                    r"Event\s+ID\s*:\s*(\S+)",
                    r"win\.system\.eventID\s*:\s*(\S+)",
                ],
            ),

            username=cls.extract_field(
                body,
                [
                    r'"targetUserName"\s*:\s*"([^"]+)"',
                    r'"TargetUserName"\s*:\s*"([^"]+)"',
                    r"Account\s+Name\s*:\s*([^\r\n]+)",
                    r"User\s+Name\s*:\s*([^\r\n]+)",
                    r"Username\s*:\s*([^\r\n]+)",
                ],
            ),

            account_domain=cls.extract_field(
                body,
                [
                    r'"targetDomainName"\s*:\s*"([^"]+)"',
                    r'"TargetDomainName"\s*:\s*"([^"]+)"',
                    r"Account\s+Domain\s*:\s*([^\r\n]+)",
                    r"Domain\s*:\s*([^\r\n]+)",
                ],
            ),

            # -------------------------------------------------
            # ETKİLEYEN IP
            # -------------------------------------------------

            source_ip=cls.extract_field(
                body,
                [
                    r'"ipAddress"\s*:\s*"([^"]+)"',
                    r'"sourceIp"\s*:\s*"([^"]+)"',
                    r'"srcip"\s*:\s*"([^"]+)"',
                    r"Source\s+Network\s+Address\s*:\s*([^\r\n]+)",
                    r"Source\s+IP\s*:\s*([^\r\n]+)",
                    r"srcip\s*:\s*([^\r\n]+)",
                ],
            ),

            source_port=cls.extract_field(
                body,
                [
                    r'"ipPort"\s*:\s*"([^"]+)"',
                    r'"sourcePort"\s*:\s*"([^"]+)"',
                    r"Source\s+Port\s*:\s*(\S+)",
                ],
            ),

            logon_type=cls.extract_field(
                body,
                [
                    r'"logonType"\s*:\s*"([^"]+)"',
                    r'"LogonType"\s*:\s*"([^"]+)"',
                    r"Logon\s+Type\s*:\s*([^\r\n]+)",
                ],
            ),

            authentication_package=cls.extract_field(
                body,
                [
                    r'"authenticationPackageName"\s*:\s*"([^"]+)"',
                    r'"AuthenticationPackageName"\s*:\s*"([^"]+)"',
                    r"Authentication\s+Package\s*:\s*([^\r\n]+)",
                ],
            ),

            logon_process=cls.extract_field(
                body,
                [
                    r'"logonProcessName"\s*:\s*"([^"]+)"',
                    r'"LogonProcessName"\s*:\s*"([^"]+)"',
                    r"Logon\s+Process\s*:\s*([^\r\n]+)",
                ],
            ),

            # -------------------------------------------------
            # ETKİLEYEN PC
            #
            # Windows failed-logon olayındaki
            # workstationName burada tutulur.
            # -------------------------------------------------

            workstation=cls.extract_field(
                body,
                [
                    r'"workstationName"\s*:\s*"([^"]+)"',
                    r'"WorkstationName"\s*:\s*"([^"]+)"',
                    r"Workstation\s+Name\s*:\s*([^\r\n]+)",
                    r"workstationName\s*[:=]\s*([^\r\n]+)",
                    r"WorkstationName\s*[:=]\s*([^\r\n]+)",
                ],
            ),

            status=cls.extract_field(
                body,
                [
                    r'"status"\s*:\s*"([^"]+)"',
                    r'"Status"\s*:\s*"([^"]+)"',
                    r"Status\s*:\s*(0x[0-9A-Fa-f]+)",
                ],
            ),

            sub_status=cls.extract_field(
                body,
                [
                    r'"subStatus"\s*:\s*"([^"]+)"',
                    r'"SubStatus"\s*:\s*"([^"]+)"',
                    r"Sub\s+Status\s*:\s*(0x[0-9A-Fa-f]+)",
                ],
            ),

            failure_reason=cls.extract_field(
                body,
                [
                    r'"failureReason"\s*:\s*"([^"]+)"',
                    r'"FailureReason"\s*:\s*"([^"]+)"',
                    r"Failure\s+Reason\s*:\s*([^\r\n]+)",
                ],
            ),

            error_code=cls.extract_error_code(
                body
            ),

            service_name=cls.extract_field(
                body,
                [
                    r'"serviceName"\s*:\s*"([^"]+)"',
                    r'"ServiceName"\s*:\s*"([^"]+)"',
                    r"Service\s+Name\s*:\s*([^\r\n]+)",
                    r"Service\s*:\s*([^\r\n]+)",
                ],
            ),

            process_name=cls.extract_field(
                body,
                [
                    r'"processName"\s*:\s*"([^"]+)"',
                    r'"ProcessName"\s*:\s*"([^"]+)"',
                    r"Process\s+Name\s*:\s*([^\r\n]+)",
                ],
            ),

            file_name=cls.extract_field(
                body,
                [
                    r'"fileName"\s*:\s*"([^"]+)"',
                    r'"FileName"\s*:\s*"([^"]+)"',
                    r"File\s+Name\s*:\s*([^\r\n]+)",
                ],
            ),
        )

    # ---------------------------------------------------------
    # Generic field extraction
    # ---------------------------------------------------------

    @classmethod
    def extract_field(
        cls,
        body: str,
        patterns: list[str],
    ) -> str | None:
        """Extract first matching technical field."""

        for pattern in patterns:

            match = re.search(
                pattern,
                body,
                re.IGNORECASE,
            )

            if match:
                value = (
                    match.group(1)
                    .strip()
                    .strip('"')
                    .strip("'")
                )

                if value:
                    return value

        return None

    # ---------------------------------------------------------
    # CVE
    # ---------------------------------------------------------

    @classmethod
    def extract_cve(
        cls,
        body: str,
    ) -> str | None:
        """Extract CVE identifier from alarm."""

        match = re.search(
            r"\bCVE-\d{4}-\d{4,7}\b",
            body,
            re.IGNORECASE,
        )

        if not match:
            return None

        return match.group(0).upper()

    # ---------------------------------------------------------
    # Error code
    # ---------------------------------------------------------

    @classmethod
    def extract_error_code(
        cls,
        body: str,
    ) -> str | None:
        """
        Extract common Windows/application error codes.

        Examples:
            0x80070002
            0xC000006D
            0xC000006A

        Only hexadecimal error codes are returned.
        """

        patterns = [
            r"(?:Error\s+Code|ErrorCode|Hata\s+Kodu)\s*[:=]\s*(0x[0-9A-Fa-f]+)",
            r"\b(0x800[0-9A-Fa-f]{4})\b",
            r"\b(0xC000[0-9A-Fa-f]{4})\b",
        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                body,
                re.IGNORECASE,
            )

            if match:
                return match.group(1).upper()

        return None

    # ---------------------------------------------------------
    # Level
    # ---------------------------------------------------------

    @classmethod
    def extract_level(
        cls,
        body: str,
        subject: str = "",
    ) -> int:
        """Extract the actual Wazuh alert level."""

        subject_pattern = (
            r"Alert\s+level\s*[:=]?\s*(\d+)"
        )

        match = re.search(
            subject_pattern,
            subject,
            re.IGNORECASE,
        )

        if match:
            return int(
                match.group(1)
            )

        body_patterns = [
            r"Rule\s+Level\s*[:=]\s*(\d+)",
            r"rule\.level\s*[:=]\s*(\d+)",
            r"level\s*=\s*(\d+)",
            r"\bRule:\s*\d+\s*fired\s*\(level\s+(\d+)\)",
        ]

        for pattern in body_patterns:

            match = re.search(
                pattern,
                body,
                re.IGNORECASE,
            )

            if match:
                return int(
                    match.group(1)
                )

        return 0

    # ---------------------------------------------------------
    # Rule information
    # ---------------------------------------------------------

    @classmethod
    def extract_rule_info(
        cls,
        body: str,
    ) -> tuple[str, str]:
        """
        Extract Wazuh Rule ID and description.

        Example:

            Rule: 60602 fired (level 10) ->
            "Windows application error event."
        """

        pattern = (
            r'Rule:\s*(\d+)\s+fired'
            r'\s*\(level\s+\d+\)'
            r'\s*->\s*["\']([^"\']+)["\']'
        )

        match = re.search(
            pattern,
            body,
            re.IGNORECASE,
        )

        if match:
            return (
                match.group(1).strip(),
                match.group(2).strip(),
            )

        pattern_id = (
            r'Rule:\s*(\d+)\s+fired'
            r'\s*\(level\s+\d+\)'
        )

        match = re.search(
            pattern_id,
            body,
            re.IGNORECASE,
        )

        if match:
            return (
                match.group(1).strip(),
                "UNKNOWN",
            )

        return "UNKNOWN", "UNKNOWN"

    # ---------------------------------------------------------
    # Affected host / Wazuh Agent
    # ---------------------------------------------------------

    @classmethod
    def extract_source_host(
        cls,
        body: str,
    ) -> str:
        """
        Extract the affected PC.

        SOURCE_HOST artık:

            ETKİLENEN PC

        anlamına gelir.

        Windows failed-logon olayındaki
        workstationName burada kullanılmaz.

        workstationName ayrı olarak:

            ETKİLEYEN PC

        alanında tutulur.

        Öncelik:

        1. Wazuh JSON agent.name
        2. Wazuh JSON agent.hostname
        3. agent.name
        4. agent.hostname
        5. Agent Name
        6. Agent Hostname
        7. Received From

        Örnek:

            Received From: (FABXL)

        sonuç:

            source_host = FABXL
        """

        patterns = [

            # -------------------------------------------------
            # Wazuh JSON - agent.name
            # -------------------------------------------------

            r'"agent"\s*:\s*\{[^}]*"name"\s*:\s*"([^"]+)"',

            # -------------------------------------------------
            # Wazuh JSON - agent.hostname
            # -------------------------------------------------

            r'"agent"\s*:\s*\{[^}]*"hostname"\s*:\s*"([^"]+)"',

            # -------------------------------------------------
            # Flat JSON
            # -------------------------------------------------

            r'"agent\.name"\s*:\s*"([^"]+)"',
            r'"agent\.hostname"\s*:\s*"([^"]+)"',

            # -------------------------------------------------
            # Text representation
            # -------------------------------------------------

            r"Agent\s+Name\s*:\s*([^\r\n]+)",
            r"Agent\s+Hostname\s*:\s*([^\r\n]+)",

            # -------------------------------------------------
            # Wazuh mail format
            #
            # Örneğin:
            #
            # Received From: (FABXL)
            #
            # Buradaki FABXL etkilenmiş PC'dir.
            # -------------------------------------------------

            r"Received\s+From:\s*\(([^)]+)\)",
            r"Received\s+From:\s*([^\s]+)",
        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                body,
                re.IGNORECASE,
            )

            if not match:
                continue

            source_host = (
                match.group(1)
                .strip()
                .strip('"')
                .strip("'")
            )

            if not source_host:
                continue

            # Bazı Wazuh / Windows kayıtlarında
            # boş veya anlamsız değerler gelebilir.

            if source_host.upper() in {
                "-",
                "N/A",
                "NA",
                "UNKNOWN",
                "NULL",
            }:
                continue

            return source_host

        return "UNKNOWN"

    # ---------------------------------------------------------
    # Filter
    # ---------------------------------------------------------

    @classmethod
    def is_accepted(
        cls,
        alert: WazuhAlert,
    ) -> bool:
        """Return True when alert level is >= MIN_LEVEL."""

        return (
            alert.rule_level
            >= cls.MIN_LEVEL
        )
