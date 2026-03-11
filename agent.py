"""
Defense AI News Agent
Savunma sanayii ve yapay zeka haberlerini tarayıp Telegram'a gönderir.
"""

import os
import time
import json
import hashlib
import requests
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted
from datetime import datetime, timedelta, timezone
from pathlib import Path
from dotenv import load_dotenv

# Çevre değişkenlerini .env dosyasından yükle
load_dotenv()

# ── Yapılandırma ──────────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID   = os.environ["TELEGRAM_CHAT_ID"]
GEMINI_API_KEY     = os.environ["GEMINI_API_KEY"]
TAVILY_API_KEY     = os.environ.get("TAVILY_API_KEY", "")   # isteğe bağlı
NEWSAPI_KEY        = os.environ.get("NEWSAPI_KEY", "")       # isteğe bağlı

SENT_CACHE_FILE = Path("sent_hashes.json")   # daha önce gönderilenler

# Arama sorguları — dilden bağımsız
QUERIES = [
    "artificial intelligence defense industry integration",
    "AI military trials experiments",
    "yapay zeka savunma sanayii entegrasyon",
    "yapay zeka askeri denemeler",
    "defense AI autonomous systems",
    "AI weapons systems development",
    "savunma yapay zeka otonom sistemler",
    "NATO AI defense technology",
]

# ── Yardımcı: gönderilmiş haber önbelleği ────────────────────────────────────
def load_sent_cache() -> set:
    if SENT_CACHE_FILE.exists():
        data = json.loads(SENT_CACHE_FILE.read_text())
        return set(data.get("hashes", []))
    return set()

def save_sent_cache(hashes: set):
    # 30 günden eski hash'leri tutmaya gerek yok — sadece son 500'ü sakla
    recent = list(hashes)[-500:]
    SENT_CACHE_FILE.write_text(json.dumps({"hashes": recent}))

def url_hash(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()

# ── Haber Kaynağı 1: Tavily AI Search ────────────────────────────────────────
def search_tavily(query: str) -> list[dict]:
    if not TAVILY_API_KEY:
        return []
    try:
        resp = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": TAVILY_API_KEY,
                "query": query,
                "search_depth": "basic",
                "max_results": 5,
                "include_answer": False,
            },
            timeout=15,
        )
        results = resp.json().get("results", [])
        return [
            {"title": r.get("title", ""), "url": r.get("url", ""), "snippet": r.get("content", "")}
            for r in results
        ]
    except Exception as e:
        print(f"[Tavily] Hata: {e}")
        return []

# ── Haber Kaynağı 2: NewsAPI ──────────────────────────────────────────────────
def search_newsapi(query: str) -> list[dict]:
    if not NEWSAPI_KEY:
        return []
    try:
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
        resp = requests.get(
            "https://newsapi.org/v2/everything",
            params={
                "q": query,
                "from": yesterday,
                "sortBy": "publishedAt",
                "pageSize": 5,
                "apiKey": NEWSAPI_KEY,
            },
            timeout=15,
        )
        articles = resp.json().get("articles", [])
        return [
            {
                "title": a.get("title", ""),
                "url": a.get("url", ""),
                "snippet": a.get("description", "") or "",
            }
            for a in articles
            if a.get("url")
        ]
    except Exception as e:
        print(f"[NewsAPI] Hata: {e}")
        return []

# ── Haber Kaynağı 3: Google News RSS (API anahtarı gerektirmez) ───────────────
def search_google_rss(query: str) -> list[dict]:
    import xml.etree.ElementTree as ET
    try:
        encoded = requests.utils.quote(query)
        url = f"https://news.google.com/rss/search?q={encoded}&hl=tr&gl=TR&ceid=TR:tr"
        resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        root = ET.fromstring(resp.content)
        items = root.findall(".//item")[:5]
        results = []
        for item in items:
            title = item.findtext("title", "")
            link  = item.findtext("link", "")
            desc  = item.findtext("description", "")
            if link:
                results.append({"title": title, "url": link, "snippet": desc})
        return results
    except Exception as e:
        print(f"[GoogleRSS] Hata: {e}")
        return []

# ── Tüm kaynaklardan haber topla ──────────────────────────────────────────────
def collect_articles() -> list[dict]:
    all_articles = []
    seen_urls = set()

    for query in QUERIES:
        for fetcher in [search_tavily, search_newsapi, search_google_rss]:
            for article in fetcher(query):
                url = article.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    all_articles.append(article)

    print(f"[Agent] Toplam {len(all_articles)} benzersiz makale bulundu.")
    return all_articles

# ── Gemini ile özetle ve filtrele ─────────────────────────────────────────────
def summarize_with_gemini(articles: list[dict]) -> list[dict]:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.0-flash")

    all_summarized = []
    
    # Haberleri tek tek işleyerek RPM (dakikada 15 istek) limitini aşmayı önleyelim
    for i, article in enumerate(articles):
        # Yalnızca 1 makale gönder
        articles_text = (
            f"[1] Başlık: {article.get('title', '')}\n"
            f"URL: {article.get('url', '')}\n"
            f"İçerik: {str(article.get('snippet', ''))[:300]}"
        )

        prompt = f"""Aşağıdaki haberi incele. Görevin:
1. Yalnızca savunma sanayii, askeri teknoloji veya yapay zeka entegrasyonuyla DOĞRUDAN ilgiliyse seç. İlgisizse boş bir JSON dizisi ([]) döndür.
2. Eğer ilgiliyse, 2-3 cümlelik Türkçe bir özet yaz.
3. Önemine göre YÜKSEK / ORTA / DÜŞÜK etiketle.
4. Sonucu JSON dizisi olarak döndür — başka hiçbir şey yazma.

Format:
[
  {{
    "index": 1,
    "title": "<başlık>",
    "url": "<url>",
    "summary": "<2-3 cümle Türkçe özet>",
    "priority": "YÜKSEK|ORTA|DÜŞÜK"
  }}
]

Eğer haber ilgisizse SADECE bunu döndür:
[]

Haber:
{articles_text}
"""

        try:
            print(f"[Gemini] İşleniyor ({i+1}/{len(articles)}): {article.get('title', '')[:40]}...")
            response = model.generate_content(prompt)
        
            raw = response.text.strip()
            # JSON bloğunu temizle
            if "```" in raw:
                # Kod bloğunu (```json ... ```) bul ve içindekini al
                parts = raw.split("```")
                if len(parts) >= 3:
                    raw = parts[1]
                if raw.lower().startswith("json"):
                    raw = raw[4:]
            raw = raw.strip()
            
            try:
                parsed = json.loads(raw)
                
                # Sadece doğru JSON listesi döndürüldüyse ve içeriği varsa ekle
                if isinstance(parsed, list) and len(parsed) > 0 and "summary" in parsed[0]:
                    # Orijinal başlık ve URL'yi koruyalım (Gemini bazen kaybedebiliyor)
                    summary_obj = parsed[0]
                    summary_obj["title"] = article.get('title', '')
                    summary_obj["url"] = article.get('url', '')
                    all_summarized.append(summary_obj)
                    
            except json.JSONDecodeError:
                print("[Gemini] JSON parse hatası, ham yanıt:", raw[:200])
                
        except ResourceExhausted:
            print("[Gemini] Kota aşıldı (429). Bu haber atlanıyor...")
        except Exception as e:
            print(f"[Gemini] Beklenmeyen API hatası: {e}")
            
        # 15 RPM limitine takılmamak için her istekten sonra 5 saniye bekle
        # (Dakikada en fazla 12 istek gönderilmiş olur)
        if i < len(articles) - 1:
            time.sleep(5)

    return all_summarized

# ── Telegram gönder ───────────────────────────────────────────────────────────
def send_telegram(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, json={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }, timeout=10)

def build_telegram_message(articles: list[dict], slot: str) -> str:
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    header = f"🛡️ <b>SAVUNMA & YZ HABER ÖZETİ</b>\n📅 {now} ({slot} raporu)\n{'─'*30}\n\n"

    if not articles:
        return header + "⚠️ Bu periyotta ilgili haber bulunamadı."

    blocks = []
    for a in articles:
        priority = str(a.get("priority", "DÜŞÜK")).upper()
        emoji = {"YÜKSEK": "🔴", "ORTA": "🟡", "DÜŞÜK": "🟢"}.get(priority, "⚪")
        
        title = a.get("title", "Başlıksız")
        summary = a.get("summary", "Özet yok.")
        url = a.get("url", "#")
        
        block = (
            f"{emoji} <b>{title}</b>\n"
            f"📝 {summary}\n"
            f"🔗 <a href='{url}'>Habere git</a>\n"
        )
        blocks.append(block)

    # Telegram mesaj limiti 4096 karakter — gerekirse böl
    body = "\n".join(blocks)
    return header + body

# ── Ana çalıştırma fonksiyonu ─────────────────────────────────────────────────
def run_agent(slot: str = "Manuel"):
    print(f"\n[{datetime.now()}] Agent başlatıldı — slot: {slot}")

    sent_cache = load_sent_cache()

    # 1. Haberleri topla
    articles = collect_articles()

    # 2. Daha önce gönderilenlerı filtrele
    new_articles = [a for a in articles if url_hash(a["url"]) not in sent_cache]
    print(f"[Agent] {len(new_articles)} yeni makale (önceden gönderilmemiş)")

    if not new_articles:
        send_telegram(
            f"🛡️ <b>SAVUNMA & YZ HABER ÖZETİ</b>\n"
            f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')} ({slot})\n\n"
            f"✅ Yeni haber bulunamadı, tüm içerikler daha önce iletildi."
        )
        return

    # 3. Gemini ile özetle & filtrele
    # Modelin çok fazla yüklenmesini önlemek için maksimum 30 haber işleyelim
    process_articles = new_articles[:30]
    
    summarized = summarize_with_gemini(process_articles)
    print(f"[Agent] Gemini {len(summarized)} ilgili haber seçti.")

    if not summarized:
        # Uygun haber bulunamasa bile incelenenleri cache'e ekle ki bir daha aynı haberleri analiz etmesin
        for a in process_articles:
            sent_cache.add(url_hash(a["url"]))
        save_sent_cache(sent_cache)
        return

    # 4. Telegram mesajı oluştur ve gönder
    # Haberleri önceliğe göre sırala
    priority_order = {"YÜKSEK": 0, "ORTA": 1, "DÜŞÜK": 2}
    summarized.sort(key=lambda x: priority_order.get(str(x.get("priority", "DÜŞÜK")).upper(), 2))

    # Uzun listeler için 5'er 5'er böl
    chunk_size = 5
    for i in range(0, len(summarized), chunk_size):
        chunk = summarized[i:i+chunk_size]
        msg = build_telegram_message(chunk, slot)
        send_telegram(msg)

    # 5. Gönderilenleri önbelleğe ekle (sadece işlediklerimizi cache'e ekliyoruz)
    for a in process_articles:
        sent_cache.add(url_hash(a["url"]))
    save_sent_cache(sent_cache)

    print(f"[Agent] Tamamlandı. {len(summarized)} haber iletildi.")


if __name__ == "__main__":
    run_agent(slot="Manuel Test")
