from pathlib import Path

from app.filters.duplicate_filter import DuplicateFilter


def main() -> None:
    print()
    print("=" * 70)
    print("YERİNDE SOC AI - DUPLICATE FILTER TEST")
    print("=" * 70)
    print()

    test_file = Path("logs/test_processed_alerts.txt")

    # Önceki test verisini temizle
    if test_file.exists():
        test_file.unlink()

    duplicate = DuplicateFilter(
        storage_file=test_file
    )

    print(f"Başlangıç kayıt sayısı : {duplicate.count()}")
    print()

    alert_1 = "TEST-ALERT-001"
    alert_2 = "TEST-ALERT-002"

    print("1. alarm ilk kez geliyor...")
    result = duplicate.check_and_mark(alert_1)

    print(f"Sonuç                  : {'YENİ' if result else 'DUPLICATE'}")
    print(f"Kayıt sayısı           : {duplicate.count()}")
    print()

    print("1. alarm tekrar geliyor...")
    result = duplicate.check_and_mark(alert_1)

    print(f"Sonuç                  : {'YENİ' if result else 'DUPLICATE'}")
    print(f"Kayıt sayısı           : {duplicate.count()}")
    print()

    print("2. alarm ilk kez geliyor...")
    result = duplicate.check_and_mark(alert_2)

    print(f"Sonuç                  : {'YENİ' if result else 'DUPLICATE'}")
    print(f"Kayıt sayısı           : {duplicate.count()}")
    print()

    print("1. alarm tekrar kontrol ediliyor...")
    result = duplicate.is_duplicate(alert_1)

    print(f"Duplicate              : {'EVET' if result else 'HAYIR'}")
    print()

    print("2. alarm tekrar kontrol ediliyor...")
    result = duplicate.is_duplicate(alert_2)

    print(f"Duplicate              : {'EVET' if result else 'HAYIR'}")
    print()

    print("===== PERSISTENCE TEST =====")
    print()

    # Yeni instance oluşturuyoruz.
    # Kayıtların dosyadan tekrar yüklenmesi gerekiyor.
    duplicate_2 = DuplicateFilter(
        storage_file=test_file
    )

    print(
        f"Yeni instance kayıt sayısı : "
        f"{duplicate_2.count()}"
    )

    print(
        f"TEST-ALERT-001 duplicate  : "
        f"{'EVET' if duplicate_2.is_duplicate(alert_1) else 'HAYIR'}"
    )

    print(
        f"TEST-ALERT-002 duplicate  : "
        f"{'EVET' if duplicate_2.is_duplicate(alert_2) else 'HAYIR'}"
    )

    print()
    print("=" * 70)
    print("TEST TAMAMLANDI")
    print("=" * 70)
    print()

    # Test dosyasını temizle
    if test_file.exists():
        test_file.unlink()

    print("Test kayıt dosyası temizlendi.")


if __name__ == "__main__":
    main()
