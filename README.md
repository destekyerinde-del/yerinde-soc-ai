# YERİNDE SOC AI

**YERİNDE SOC AI**, Wazuh güvenlik alarmlarını otomatik olarak okuyup analiz eden, tekrar eden alarmları filtreleyen, Ollama üzerinden yapay zekâ analizi gerçekleştiren ve sonuçları incident olarak yöneten SOC otomasyon sistemidir.

Bu dokümanın amacı, **projeyi daha önce hiç görmemiş bir sistem yöneticisinin** YERİNDE SOC AI sistemini sıfırdan kurabilmesini, yapılandırabilmesini, çalıştırabilmesini ve gerektiğinde yedekten geri yükleyebilmesini sağlamaktır.

---

# 1. Sistem Mimarisi

Temel çalışma akışı:

```text
Wazuh
   │
   ▼
Gmail
   │
   ▼
Gmail Client
   │
   ▼
Wazuh Parser
   │
   ▼
Level Filter
   │
   ▼
Duplicate Filter
   │
   ▼
Incident Manager
   │
   ▼
Ollama / LLM
   │
   ▼
AI Response Parser
   │
   ▼
Incident Database
   │
   ├── Web Dashboard
   │
   └── Telegram
```

Sistem temel olarak şu işlemleri gerçekleştirir:

- Gmail üzerinden Wazuh alarmlarını okur.
- Wazuh alarm seviyesini kontrol eder.
- Belirlenen seviyenin altındaki alarmları filtreler.
- Aynı alarmın tekrar işlenmesini engeller.
- Yeni güvenlik olaylarını incident olarak oluşturur.
- Ollama üzerinden yapay zekâ analizi gerçekleştirir.
- AI sonucunu yapılandırılmış biçimde işler.
- Incident bilgilerini SQLite veritabanına kaydeder.
- Web arayüzünde incident bilgilerini gösterir.
- Telegram üzerinden bildirim gönderebilir.

---

# 2. Gereksinimler

Önerilen işletim sistemi:

```text
Ubuntu 24.04 LTS
```

Minimum önerilen sistem:

```text
CPU     : 4 Core
RAM     : 8 GB
Disk    : 50 GB+
Network : İnternet erişimi
```

AI modeli kullanılacağı için daha güçlü sistem önerilir.

Örneğin:

```text
CPU     : 8 Core
RAM     : 16 GB+
Disk    : 100 GB+
GPU     : Opsiyonel
```

GPU bulunması zorunlu değildir.

---

# 3. Proje Dizin Yapısı

Ana proje dizini:

```text
/home/yerinde/yerinde-soc-ai
```

Önemli dosyalar:

```text
app/
├── ai/
│   ├── ollama_client.py
│   └── response_parser.py
│
├── clients/
│   ├── gmail_client.py
│   └── telegram_client.py
│
├── core/
│   └── config.py
│
├── filters/
│   └── duplicate_filter.py
│
├── parsers/
│   └── wazuh_parser.py
│
├── pipeline/
│   └── runner.py
│
├── services/
│   └── incident_manager.py
│
├── storage/
│   ├── alert_store.py
│   └── incident_store.py
│
├── templates/
│   ├── dashboard.html
│   └── incident_detail.html
│
└── web/
    ├── database.py
    └── main.py

main.py
requirements.txt
.env
```

`venv/` GitHub'a gönderilmez.

`.env` GitHub'a gönderilmez.

SQLite database dosyaları GitHub'a gönderilmez.

---

# 4. Ubuntu Hazırlığı

Sistemi güncelleyin:

```bash
sudo apt update
sudo apt upgrade -y
```

Gerekli temel paketleri kurun:

```bash
sudo apt install -y \
git \
python3 \
python3-venv \
python3-pip \
curl \
wget \
build-essential
```

Python sürümünü kontrol edin:

```bash
python3 --version
```

Python 3.12 veya uyumlu daha yeni bir sürüm kullanılmalıdır.

---

# 5. GitHub'dan Projeyi İndirme

Projeyi home dizinine alın:

```bash
cd ~
```

GitHub repository:

```text
git@github.com:destekyerinde-del/yerinde-soc-ai.git
```

SSH anahtarı yapılandırılmışsa:

```bash
git clone git@github.com:destekyerinde-del/yerinde-soc-ai.git
```

Dizine girin:

```bash
cd ~/yerinde-soc-ai
```

Kontrol:

```bash
pwd
```

Beklenen:

```text
/home/yerinde/yerinde-soc-ai
```

---

# 6. Python Virtual Environment

Proje dizininde:

```bash
cd ~/yerinde-soc-ai
```

Virtual environment oluşturun:

```bash
python3 -m venv venv
```

Aktifleştirin:

```bash
source venv/bin/activate
```

Python kontrolü:

```bash
python --version
```

Alternatif olarak doğrudan:

```bash
./venv/bin/python --version
```

---

# 7. Python Paketlerinin Kurulması

Virtual environment aktifken:

```bash
pip install --upgrade pip
```

Ardından:

```bash
pip install -r requirements.txt
```

Kurulum sonrası:

```bash
./venv/bin/pip freeze
```

`requirements.txt` içerisindeki paketlerin kurulu olduğu görülmelidir.

---

# 8. Environment Dosyası

Proje içerisinde `.env` dosyası oluşturulmalıdır.

Örnek:

```bash
cp .env.example .env
```

Ardından:

```bash
nano .env
```

Örnek yapı:

```env
GMAIL_HOST=imap.gmail.com
GMAIL_USER=YOUR_GMAIL_ACCOUNT
GMAIL_PASS=YOUR_GMAIL_PASSWORD_OR_APP_PASSWORD

TELEGRAM_BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID=YOUR_TELEGRAM_CHAT_ID

OLLAMA_HOST=http://127.0.0.1:11434
OLLAMA_MODEL=qwen3:8b

AI_TIMEOUT=120
CHECK_INTERVAL=30
LOG_LEVEL=INFO
```

**Gerçek şifre, token veya API anahtarı GitHub'a gönderilmemelidir.**

Kontrol:

```bash
ls -lh .env
```

---

# 9. Ollama Kurulumu

Ollama kurulumunu resmi kurulum yöntemiyle gerçekleştirin.

Kurulum sonrası:

```bash
ollama --version
```

Ollama servisinin çalıştığını kontrol edin:

```bash
systemctl status ollama
```

API kontrolü:

```bash
curl http://127.0.0.1:11434/api/tags
```

---

# 10. AI Modeli

YERİNDE SOC AI Ollama üzerinden model kullanır.

Örnek model:

```text
qwen3:8b
```

Kurulum:

```bash
ollama pull qwen3:8b
```

Kontrol:

```bash
ollama list
```

Beklenen model:

```text
qwen3:8b
```

Projede kullanılan model `.env` içerisinden belirlenir:

```env
OLLAMA_MODEL=qwen3:8b
```

---

# 11. Ollama Testi

Projede:

```bash
./venv/bin/python test_ollama_wazuh.py
```

Başarılı durumda aşağıdakine benzer sonuç görülmelidir:

```text
OLLAMA : READY
```

Ayrıca Gmail kontrolü gerçekleştirilir.

Gmail'de okunmamış Wazuh alarmı yoksa:

```text
Okunmamış mail sayısı : 0
```

görülmesi normaldir.

---

# 12. Python Syntax Kontrolü

Projede bulunan tüm Python dosyalarını kontrol etmek için:

```bash
find . -type f -name "*.py" \
-not -path "./venv/*" \
-not -path "./.git/*" \
-print0 | xargs -0 -n1 ./venv/bin/python -m py_compile
```

**Herhangi bir çıktı gelmemesi normaldir.**

Hata varsa Python syntax hatası gösterilir.

---

# 13. Testler

Sırayla çalıştırılabilir:

```bash
./venv/bin/python test_wazuh_parser.py
```

```bash
./venv/bin/python test_parser_duplicate.py
```

```bash
./venv/bin/python test_duplicate_filter.py
```

```bash
./venv/bin/python test_ollama_wazuh.py
```

Duplicate filter testinde benzer şekilde:

```text
Sonuç : YENİ
```

ve tekrar gelen aynı kayıt için:

```text
Sonuç : DUPLICATE
```

görülmelidir.

---

# 14. Systemd Servisi

Servis dosyası:

```text
/etc/systemd/system/yerinde-soc-ai.service
```

Örnek:

```ini
[Unit]
Description=YERİNDE SOC AI
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=yerinde
Group=yerinde
WorkingDirectory=/home/yerinde/yerinde-soc-ai
Environment="PATH=/home/yerinde/yerinde-soc-ai/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/home/yerinde/yerinde-soc-ai/venv/bin/python /home/yerinde/yerinde-soc-ai/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Dosyayı oluşturun:

```bash
sudo nano /etc/systemd/system/yerinde-soc-ai.service
```

Sonra:

```bash
sudo systemctl daemon-reload
```

Servisi etkinleştirin:

```bash
sudo systemctl enable yerinde-soc-ai.service
```

Başlatın:

```bash
sudo systemctl start yerinde-soc-ai.service
```

---

# 15. Servis Kontrolü

Durum:

```bash
systemctl is-active yerinde-soc-ai.service
```

Beklenen:

```text
active
```

Ayrıntılı durum:

```bash
systemctl status yerinde-soc-ai.service
```

Log:

```bash
journalctl -u yerinde-soc-ai.service -f
```

Son 100 satır:

```bash
journalctl -u yerinde-soc-ai.service -n 100
```

---

# 16. Uygulama Logları

Proje logları:

```text
logs/
```

Kontrol:

```bash
ls -lh logs/
```

Canlı log:

```bash
tail -f logs/yerinde-soc.log
```

---

# 17. Database

Ana SQLite database:

```text
logs/yerinde-soc.db
```

Database kontrolü:

```bash
ls -lh logs/yerinde-soc.db
```

**Database GitHub'a gönderilmemelidir.**

Database SOC incident kayıtlarını içerdiği için güvenli şekilde yedeklenmelidir.

---

# 18. Web Arayüzü

Web uygulaması `main.py` üzerinden çalışır.

Servis çalışırken uygulamanın dinlediği portu kontrol edin:

```bash
ss -lntp
```

Uygulama loglarında belirtilen port üzerinden tarayıcıdan erişilebilir.

Örnek:

```text
http://SUNUCU_IP:PORT
```

---

# 19. Gmail Kontrolü

Gmail bağlantısını test etmek için:

```bash
./venv/bin/python test_wazuh_parser.py
```

Örneğin:

```text
Toplam okunmamış mail : 0
```

görülmesi bağlantının başarısız olduğu anlamına gelmez.

Asıl önemli olan test sırasında hata oluşmamasıdır.

---

# 20. Telegram

Telegram yapılandırması `.env` üzerinden yapılır:

```env
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
```

Token kesinlikle kaynak koduna yazılmamalıdır.

Telegram ayarlarını değiştirdikten sonra servis yeniden başlatılmalıdır:

```bash
sudo systemctl restart yerinde-soc-ai.service
```

---

# 21. Güncelleme

GitHub'daki yeni kodu almak için:

```bash
cd ~/yerinde-soc-ai
```

Önce durum:

```bash
git status
```

Sonra:

```bash
git pull --ff-only
```

Python bağımlılıkları değiştiyse:

```bash
./venv/bin/pip install -r requirements.txt
```

Test:

```bash
find . -type f -name "*.py" \
-not -path "./venv/*" \
-not -path "./.git/*" \
-print0 | xargs -0 -n1 ./venv/bin/python -m py_compile
```

Servisi yeniden başlatın:

```bash
sudo systemctl restart yerinde-soc-ai.service
```

Kontrol:

```bash
systemctl is-active yerinde-soc-ai.service
```

---

# 22. Yedekleme

GitHub sadece **kaynak kodun yedeğidir**.

Aşağıdaki dosyalar ayrıca yedeklenmelidir:

```text
.env
logs/yerinde-soc.db
logs/processed_alerts.txt
requirements.txt
/etc/systemd/system/yerinde-soc-ai.service
```

Mevcut sistemde bunların yedeği:

```text
~/yerinde-soc-ai-backups/
```

altında tutulmaktadır.

Ana restore arşivi:

```text
yerinde-soc-ai-backup-2026-08-15.tar.gz
```

Checksum:

```text
yerinde-soc-ai-backup-2026-08-15.sha256
```

Checksum kontrolü:

```bash
sha256sum -c yerinde-soc-ai-backup-2026-08-15.sha256
```

Beklenen:

```text
OK
```

**Backup aynı fiziksel diskte tutulmamalıdır.**

Harici disk veya başka güvenli bir depolama alanında saklanmalıdır.

---

# 23. FELAKET SENARYOSU — Ubuntu Tamamen Çökerse

Ubuntu yeniden kurulduğunda iki kaynağa ihtiyaç vardır:

```text
1. GitHub
2. Harici backup
```

### Aşama 1 — Ubuntu

Ubuntu kurulumu tamamlanır.

Kullanıcı oluşturulur:

```text
yerinde
```

### Aşama 2 — Temel paketler

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip curl wget build-essential
```

### Aşama 3 — GitHub

```bash
cd ~
git clone git@github.com:destekyerinde-del/yerinde-soc-ai.git
cd ~/yerinde-soc-ai
```

SSH anahtarı yeniden oluşturulmalı ve GitHub hesabına eklenmelidir.

### Aşama 4 — Python

```bash
python3 -m venv venv
```

```bash
./venv/bin/pip install -r requirements.txt
```

### Aşama 5 — Ollama

Ollama yeniden kurulmalıdır.

Model yeniden indirilebilir:

```bash
ollama pull qwen3:8b
```

### Aşama 6 — Backup

Harici diskten:

```text
yerinde-soc-ai-backup-2026-08-15.tar.gz
```

alınır.

Arşiv içerisindeki:

```text
.env
yerinde-soc.db
processed_alerts.txt
requirements.txt
yerinde-soc-ai.service
```

geri yüklenir.

### Aşama 7 — Systemd

Servis dosyası:

```text
/etc/systemd/system/yerinde-soc-ai.service
```

konumuna geri konur.

Sonra:

```bash
sudo systemctl daemon-reload
sudo systemctl enable yerinde-soc-ai.service
sudo systemctl start yerinde-soc-ai.service
```

### Aşama 8 — Kontrol

```bash
systemctl is-active yerinde-soc-ai.service
```

Beklenen:

```text
active
```

Ardından:

```bash
./venv/bin/python test_wazuh_parser.py
./venv/bin/python test_parser_duplicate.py
./venv/bin/python test_duplicate_filter.py
./venv/bin/python test_ollama_wazuh.py
```

Sistem tekrar çalışır hale gelmelidir.

---

# 24. Önemli Güvenlik Kuralları

Aşağıdaki dosyalar GitHub'a gönderilmemelidir:

```text
.env
*.db
*.sqlite
logs/
venv/
```

SSH private key kesinlikle paylaşılmamalıdır:

```text
~/.ssh/id_ed25519
```

Sadece public key paylaşılabilir:

```text
~/.ssh/id_ed25519.pub
```

Telegram bot token paylaşılmamalıdır.

Gmail parolası veya App Password paylaşılmamalıdır.

SOC database dosyaları üçüncü taraflara gönderilmemelidir.

---

# 25. Git Kontrolü

Değişikliklerden önce:

```bash
git status
```

Değişiklikleri kontrol edin:

```bash
git diff
```

Commit:

```bash
git add .
git commit -m "açıklama"
```

GitHub'a gönderme:

```bash
git push
```

Repository:

```text
git@github.com:destekyerinde-del/yerinde-soc-ai.git
```

---

# 26. Hızlı Sağlık Kontrolü

Sistemin genel durumunu hızlıca kontrol etmek için:

```bash
cd ~/yerinde-soc-ai

echo "===== PROJECT ====="
pwd

echo
echo "===== PYTHON ====="
./venv/bin/python --version

echo
echo "===== SERVICE ====="
systemctl is-active yerinde-soc-ai.service

echo
echo "===== OLLAMA ====="
ollama list

echo
echo "===== DATABASE ====="
ls -lh logs/yerinde-soc.db

echo
echo "===== GIT ====="
git status --short
```

Normal bir sistemde:

```text
Python       → çalışıyor
SERVICE      → active
OLLAMA       → model mevcut
DATABASE     → dosya mevcut
GIT          → temiz
```

olmalıdır.

---

# 27. Sorun Giderme

### Servis çalışmıyor

```bash
systemctl status yerinde-soc-ai.service
```

ve:

```bash
journalctl -u yerinde-soc-ai.service -n 100
```

### Ollama çalışmıyor

```bash
systemctl status ollama
```

ve:

```bash
curl http://127.0.0.1:11434/api/tags
```

### Model yok

```bash
ollama list
```

Gerekirse:

```bash
ollama pull qwen3:8b
```

### Python hatası

```bash
find . -type f -name "*.py" \
-not -path "./venv/*" \
-not -path "./.git/*" \
-print0 | xargs -0 -n1 ./venv/bin/python -m py_compile
```

### Gmail alarm gelmiyor

```bash
./venv/bin/python test_wazuh_parser.py
```

### Telegram bildirim gelmiyor

`.env` değerlerini kontrol edin ve:

```bash
sudo systemctl restart yerinde-soc-ai.service
```

### Database problemi

Önce database'i silmeyin.

Mevcut database'i yedekleyin:

```bash
cp logs/yerinde-soc.db logs/yerinde-soc.db.backup
```

Daha sonra sorunun nedeni araştırılmalıdır.

---

# 28. Kurulum Son Kontrol Listesi

```text
[ ] Ubuntu hazır
[ ] Git kuruldu
[ ] GitHub repository klonlandı
[ ] Python kuruldu
[ ] venv oluşturuldu
[ ] requirements.txt kuruldu
[ ] .env oluşturuldu
[ ] Gmail bilgileri girildi
[ ] Telegram bilgileri girildi
[ ] Ollama kuruldu
[ ] AI modeli indirildi
[ ] Python syntax kontrolü başarılı
[ ] Wazuh parser testi başarılı
[ ] Duplicate filter testi başarılı
[ ] Ollama testi başarılı
[ ] systemd servisi oluşturuldu
[ ] systemd servisi active
[ ] Web arayüzü kontrol edildi
[ ] Database oluşturuldu
[ ] Backup oluşturuldu
[ ] Backup checksum doğrulandı
[ ] Backup harici diske kopyalandı
```

---

# 29. Sonuç

YERİNDE SOC AI'nin kaynak kodu GitHub üzerinde tutulur.

Canlı sistem bilgileri ve hassas veriler ayrı backup mekanizmasıyla korunur.

Bu nedenle sistem tamamen kaybedilse bile:

```text
GitHub
   +
Harici Backup
   +
Yeni Ubuntu
   =
YERİNDE SOC AI
```

yeniden oluşturulabilir.

**Önemli:** Bu dokümandaki gerçek şifreleri, tokenları, private keyleri, gerçek IP adreslerini veya production database dosyalarını GitHub'a eklemeyin.

---

## YERİNDE SOC AI

**Security Operations Center Automation**

Wazuh + Gmail + Ollama + AI + Incident Management + Telegram