from app.clients.gmail_client import GmailClient
from app.parsers.wazuh_parser import WazuhParser
from app.ai.ollama_client import OllamaClient


def main() -> None:
    print()
    print("=" * 70)
    print("YERİNDE SOC AI - OLLAMA + WAZUH TEST")
    print("=" * 70)
    print()

    parser = WazuhParser()
    ai = OllamaClient()

    print("===== OLLAMA =====")
    print(f"Host  : {ai.host}")
    print(f"Model : {ai.model}")
    print()

    print("Ollama bağlantısı kontrol ediliyor...")

    if not ai.health():
        print("OLLAMA : FAILED")
        return

    print("OLLAMA : READY")
    print()

    print("===== GMAIL =====")

    with GmailClient() as gmail:

        messages = gmail.fetch_unread_messages()

        print(
            f"Okunmamış mail sayısı : "
            f"{len(messages)}"
        )

        print()

        selected = None

        for message in messages:

            alert = parser.parse(message)

            if parser.is_accepted(alert):

                selected = alert
                break

        if selected is None:

            print(
                "Level >= 10 olan Wazuh alarmı bulunamadı."
            )
            return

        print("===== SEÇİLEN WAZUH ALARMI =====")
        print()

        print(f"Mail ID    : {selected.mail_id}")
        print(f"Message-ID : {selected.message_id}")
        print(f"Subject    : {selected.subject}")
        print(f"Rule Level : {selected.rule_level}")

        print()
        print("=" * 70)
        print("AI ANALİZİ BAŞLIYOR")
        print("=" * 70)
        print()

        result = ai.analyze_wazuh_alert(
            selected
        )

        print(result)

        print()
        print("=" * 70)
        print("AI ANALİZİ TAMAMLANDI")
        print("=" * 70)
        print()


if __name__ == "__main__":
    main()
