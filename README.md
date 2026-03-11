# 🛡️ Savunma & Yapay Zeka Haber Ajanı

Savunma sanayii ve yapay zeka haberlerini otomatik tarayıp Telegram'a gönderen Python ajanı.

---

## 📁 Dosya Yapısı

```
defense_ai_agent/
├── agent.py            # Ana ajan — haberleri toplar, Claude ile özetler, Telegram'a gönderir
├── scheduler.py        # Zamanlayıcı — 09:00 / 15:00 / 22:00 görevleri
├── setup_telegram.py   # Telegram Chat ID bulma yardımcısı
├── requirements.txt    # Python bağımlılıkları
└── .env.example        # Ortam değişkenleri şablonu
```

---

## ⚡ Kurulum (Adım Adım)

### Adım 1 — Python Bağımlılıklarını Kur

```bash
pip install -r requirements.txt
```

### Adım 2 — Telegram Botu Oluştur

1. Telegram'da **@BotFather**'a gidin
2. `/newbot` yazın ve talimatları izleyin
3. Size verilen **Bot Token**'ı kopyalayın

### Adım 3 — Chat ID'nizi Bulun

```bash
python setup_telegram.py
```

Bu script Chat ID'nizi otomatik bulur ve test mesajı gönderir.

### Adım 4 — API Anahtarlarını Ayarlayın

`.env.example` dosyasını `.env` olarak kopyalayın:

```bash
cp .env.example .env
```

Sonra `.env` dosyasını düzenleyin:

```env
ANTHROPIC_API_KEY=sk-ant-...      # console.anthropic.com
TELEGRAM_BOT_TOKEN=7xxx:AAF...    # BotFather'dan
TELEGRAM_CHAT_ID=123456789        # setup_telegram.py'den

# İsteğe bağlı (daha iyi sonuçlar için):
TAVILY_API_KEY=tvly-...           # tavily.com — ücretsiz 1000/ay
NEWSAPI_KEY=...                   # newsapi.org — ücretsiz 100/gün
```

### Adım 5 — Test Çalıştırması

```bash
# Ortam değişkenlerini yükle
export $(cat .env | xargs)

# Manuel test
python agent.py
```

Telegram'a ilk rapor gelecek. ✅

### Adım 6 — Zamanlayıcıyı Başlat

```bash
python scheduler.py
```

---

## 🖥️ 7/24 Çalıştırma Seçenekleri

### Seçenek A — Kendi Bilgisayarınızda (pm2 ile)

```bash
npm install -g pm2
pm2 start scheduler.py --interpreter python3 --name haber-ajan
pm2 save
pm2 startup   # bilgisayar açılışında otomatik başlat
```

### Seçenek B — Ücretsiz Bulut (Railway.app)

1. [railway.app](https://railway.app) hesabı açın
2. "New Project" → "Deploy from GitHub"
3. Repo'nuzu bağlayın
4. Environment Variables sekmesinden `.env` değerlerini girin
5. `python scheduler.py` başlangıç komutu olarak ayarlayın
6. Deploy → 7/24 çalışır, aylık ~5$ veya ücretsiz plan

### Seçenek C — VPS (en stabil)

```bash
# Sunucuda screen ile arka planda çalıştır
screen -S haber-ajan
python scheduler.py
# Ctrl+A, D ile ayrıl — çalışmaya devam eder
```

---

## 🔧 Özelleştirme

### Farklı Konular Eklemek

`agent.py` içindeki `QUERIES` listesini düzenleyin:

```python
QUERIES = [
    "artificial intelligence defense industry",
    "autonomous weapons systems",
    "savunma sanayii yapay zeka",
    # Kendi sorgularınızı ekleyin:
    "hypersonic missiles AI guidance",
    "insansız hava araçları yapay zeka",
]
```

### Farklı Saatler

`scheduler.py` içinde:

```python
schedule.every().day.at("08:00").do(job_morning)    # saati değiştirin
schedule.every().day.at("14:00").do(job_afternoon)
schedule.every().day.at("21:00").do(job_evening)
```

---

## 🔍 Haber Kaynakları

| Kaynak | API Gerekli | Limit | Not |
|--------|------------|-------|-----|
| Google News RSS | ❌ Hayır | Sınırsız | Her zaman çalışır |
| Tavily AI | ✅ Evet | 1000/ay ücretsiz | En iyi AI-odaklı arama |
| NewsAPI | ✅ Evet | 100/gün ücretsiz | Büyük haber siteleri |

Google News RSS API anahtarı gerektirmez — sistemi yalnızca bu kaynak ile de çalıştırabilirsiniz.

---

## ❓ Sorun Giderme

**"Yeni haber bulunamadı" mesajı geliyor:**
→ `sent_hashes.json` dosyasını silin, önbellek sıfırlanır.

**Telegram mesajı gelmiyor:**
→ Bot Token ve Chat ID'yi kontrol edin. `setup_telegram.py` ile yeniden test edin.

**Claude hata veriyor:**
→ `ANTHROPIC_API_KEY` doğru mu? console.anthropic.com'dan kontrol edin.
