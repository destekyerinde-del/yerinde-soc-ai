🟢 1. 
Ubuntu kurdunuz tercih Server 24.04:
git clone git@github.com:destekyerinde-del/yerinde-soc-ai.git
ile projeyi yeniden alabiliriz.
Son commit'imiz:    942de6a   chore: initialize YERINDE SOC AI v2.2 Stable
🟡 2. Ama .env GitHub'da değil
Bu bilerek yaptığımız doğru bir şey.
.env içinde Gmail/Telegram gibi gizli bilgiler olabilir. Dolayısıyla:
.env
GitHub'a gönderilmedi.
Yeni Ubuntu kurarsak .env dosyasını yeniden oluşturmamız ve gerekli değerleri girmemiz gerekir.
🔴 Veritabanı da GitHub'da değil
Bizim:
logs/yerinde-soc.db
gibi çalışma verileri de GitHub'a gönderilmiyor.
Dolayısıyla kod kaybolmaz, ama eski alarm/incident geçmişini de korumak istiyorsak veritabanı için ayrıca yedekleme yapmamız gerekir.
Aynı şekilde:
~/yerinde-soc-ai-backups/
klasörünü de GitHub'a göndermedik.
________________________________________


En doğru sistemimiz şu olacak
                    GITHUB
                       │
                       │  Kod
                       ▼
              yerinde-soc-ai
                       │
              ┌────────┴────────┐
              │                 │
          Uygulama            .env
          kodları           (gizli)
              │
              └──────┐
                     │
                  logs/
                veritabanı



GitHub = projenin kod yedeği
Ayrı backup = .env + database + önemli çalışma verileri
________________________________________
Ubuntu yeniden kurulursa YERİNDE SOC AI'ı 0'dan ayağa kaldırabileceğimiz bir backup/restore sistemi hazırlayalım.
Böylece sadece:
git clone ...   deyip bırakmayız; Python ortamı, bağımlılıklar, .env, SQLite veritabanı, systemd servisi ve gerekli klasörleri de kontrollü şekilde geri kurarız.
O zaman gerçekten "sunucu çöktü → yeni Ubuntu → sistemi tekrar ayağa kaldır" seviyesinde sağlam bir yapımız olur.
NASIL YAPILACAK 
Şöyle yapacağız. Amacımız Ubuntu tamamen silinse bile YERİNDE SOC AI'ı yeniden kurup çalıştırabilmek.
1. GitHub kod yedeği zaten hazır ✅
Şu anda:
GitHub
└── yerinde-soc-ai
    ├── app/
    ├── main.py
    ├── test_*.py
    ├── .gitignore
    └── .env.example
Kod burada.
________________________________________
2. Ayrı bir "sunucu yedeği" oluşturacağız
GitHub'a şunları koymayacağız:
.env
logs/yerinde-soc.db
Bunun yerine sunucuda örneğin:
/home/yerinde/yerinde-soc-ai-backups/
altında tutacağız.
Ama daha iyisi, bunu harici disk / NAS / başka sunucuya da kopyalayacağız.
________________________________________
3. .env yedeği
.env bizim gizli ayarlarımız:
GMAIL_USER
GMAIL_PASS
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
OLLAMA_HOST
OLLAMA_MODEL
Bunu GitHub'a koymayacağız.
Örneğin şifreli bir backup dosyası oluşturabiliriz:
yerinde-soc-secrets.tar.gz
________________________________________
4. SQLite veritabanı yedeği
Bizim alarm ve incident geçmişimiz burada:
logs/yerinde-soc.db
Bunun düzenli yedeğini alacağız.
Örneğin:
yerinde-soc-db-2026-08-15.db
Böylece Ubuntu çökerse sadece kodu değil, eski alarm/incident kayıtlarını da geri getirebiliriz.
________________________________________
5. Ollama modelini de düşünmemiz gerekiyor
Şu anda testimiz:
OLLAMA MODEL : qwen3:8b
Ollama modelini GitHub'a koymayacağız.
Yeni Ubuntu'da tekrar:
ollama pull qwen3:8b
ile indiririz.
Bu nedenle model dosyasını ayrıca yedeklememiz şart değil.
________________________________________
6. Python ortamını tekrar oluşturacağız
venv de GitHub'a gitmiyor.
Yeni Ubuntu'da:
python3 -m venv ~/yerinde-soc-ai/venv
ve gerekli Python paketlerini kuracağız.
Bunun için projeye bir:
requirements.txt
ekleyeceğiz.
Örneğin:   fastapi ,uvicorn,requests,beautifulsoup4,python-dotenv    gibi kullandığımız paketler burada olacak.
________________________________________
7. Systemd servisini de yeniden kuracağız
Şu anda:
systemctl is-active yerinde-soc-ai.service
sonucumuz:
active
Yeni Ubuntu'da bunun otomatik kurulabilmesi için servis dosyasını da proje içine koyacağız.
Örneğin:
deploy/
└── yerinde-soc-ai.service
Yeni sistemde:
sudo cp deploy/yerinde-soc-ai.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now yerinde-soc-ai
yeterli olacak.
________________________________________
En sonunda tek bir restore senaryomuz olacak
Ubuntu tamamen çöktü diyelim.
Yeni Ubuntu kuruldu.
Sonra:
git clone git@github.com:destekyerinde-del/yerinde-soc-ai.git
cd yerinde-soc-ai
Ardından:
1. Python kurulumu
        ↓
2. venv oluştur
        ↓
3. requirements.txt
        ↓
4. Ollama kurulumu
        ↓
5. qwen3:8b indir
        ↓
6. .env geri yükle
        ↓
7. SQLite database geri yükle
        ↓
8. systemd servisini kur
        ↓
9. testleri çalıştır
        ↓
10. servis aktif
Ve sistem tekrar çalışır.
________________________________________
Projeye:
deploy/
├── install.sh
├── restore.sh
└── yerinde-soc-ai.service

backup/
└── backup.sh
ekleyebiliriz.
Böylece yeni Ubuntu'da neredeyse:
./deploy/install.sh
diyerek sistemi kurabiliriz.
Yedekten dönmek için de:
./deploy/restore.sh
kullanırız.


