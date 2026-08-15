from app.clients.gmail_client import GmailClient
from app.parsers.wazuh_parser import WazuhParser
from app.filters.duplicate_filter import DuplicateFilter


def main() -> None:
    print()
    print("=" * 70)
    print("YERİNDE SOC AI - PARSER + DUPLICATE FILTER TEST")
    print("=" * 70)
    print()

    parser = WazuhParser()

    duplicate = DuplicateFilter(
        storage_file="logs/test_pipeline_alerts.txt"
    )

    print(
        f"Başlangıç duplicate kayıtları : "
        f"{duplicate.count()}"
    )
    print()

    with GmailClient() as gmail:

        messages = gmail.fetch_unread_messages()

        print(
            f"Toplam okunmamış Gmail       : "
            f"{len(messages)}"
        )
        print()

        level_accepted = 0
        level_ignored = 0
        new_alerts = 0
        duplicate_alerts = 0

        for message in messages:

            alert = parser.parse(message)

            print("-" * 70)
            print(f"Mail ID     : {alert.mail_id}")
            print(f"Subject     : {alert.subject}")
            print(f"Rule Level  : {alert.rule_level}")

            # -------------------------------------------------
            # LEVEL FILTER
            # -------------------------------------------------

            if not parser.is_accepted(alert):

                level_ignored += 1

                print("Level Filter: IGNORE")
                continue

            level_accepted += 1

            print("Level Filter: ACCEPT")

            # -------------------------------------------------
            # DUPLICATE FILTER
            # -------------------------------------------------

            alert_key = (
                alert.message_id
                or alert.mail_id
            )

            if duplicate.is_duplicate(alert_key):

                duplicate_alerts += 1

                print("Duplicate   : YES")
                print("Pipeline    : IGNORE")
                continue

            new_alerts += 1

            print("Duplicate   : NO")
            print("Pipeline    : READY FOR AI")

            # -------------------------------------------------
            # TEST PURPOSE ONLY
            # -------------------------------------------------
            # Şimdilik AI yok.
            # Başarılı pipeline adayını kaydediyoruz.

            duplicate.mark_processed(alert_key)

        print()
        print("=" * 70)
        print("PIPELINE SUMMARY")
        print("=" * 70)
        print()

        print(
            f"Total Gmail              : "
            f"{len(messages)}"
        )

        print(
            f"Level >= 10              : "
            f"{level_accepted}"
        )

        print(
            f"Level < 10               : "
            f"{level_ignored}"
        )

        print(
            f"New alerts               : "
            f"{new_alerts}"
        )

        print(
            f"Duplicates               : "
            f"{duplicate_alerts}"
        )

        print(
            f"Duplicate kayıt sayısı   : "
            f"{duplicate.count()}"
        )

        print()
        print("=" * 70)
        print("TEST TAMAMLANDI")
        print("=" * 70)
        print()

    # Test dosyasını temizle
    import pathlib

    test_file = pathlib.Path(
        "logs/test_pipeline_alerts.txt"
    )

    if test_file.exists():
        test_file.unlink()

    print("Test kayıtları temizlendi.")


if __name__ == "__main__":
    main()
