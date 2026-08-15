from app.clients.gmail_client import GmailClient
from app.parsers.wazuh_parser import WazuhParser


def main() -> None:
    print()
    print("=" * 70)
    print("YERİNDE SOC AI - WAZUH PARSER TEST")
    print("=" * 70)
    print()

    parser = WazuhParser()

    with GmailClient() as gmail:

        messages = gmail.fetch_unread_messages()

        print(f"Toplam okunmamış mail : {len(messages)}")
        print()

        accepted = 0
        ignored = 0

        for message in messages:

            alert = parser.parse(message)

            decision = (
                "ACCEPT"
                if parser.is_accepted(alert)
                else "IGNORE"
            )

            if alert.accepted:
                accepted += 1
            else:
                ignored += 1

            print("-" * 70)
            print(f"Mail ID     : {alert.mail_id}")
            print(f"Message-ID  : {alert.message_id}")
            print(f"Subject     : {alert.subject}")
            print(f"Rule Level  : {alert.rule_level}")
            print(f"Decision    : {decision}")

        print()
        print("=" * 70)
        print("FILTER SUMMARY")
        print("=" * 70)
        print()
        print(f"Total       : {len(messages)}")
        print(f"Accepted    : {accepted}")
        print(f"Ignored     : {ignored}")
        print()
        print("Filter Rule : Level >= 10")
        print()
        print("=" * 70)
        print("TEST TAMAMLANDI")
        print("=" * 70)


if __name__ == "__main__":
    main()
