"""
Zamanlayıcı: agent.py'yi 09:00, 15:00 ve 22:00'de otomatik çalıştırır.
Çalıştır: python scheduler.py
"""

import schedule
import time
from agent import run_agent

def job_morning():
    run_agent(slot="Sabah 09:00")

def job_afternoon():
    run_agent(slot="Öğleden Sonra 15:00")

def job_evening():
    run_agent(slot="Akşam 22:00")

# Görev zamanlarını ayarla (sunucu saatine göre)
schedule.every().day.at("09:00").do(job_morning)
schedule.every().day.at("15:00").do(job_afternoon)
schedule.every().day.at("22:00").do(job_evening)

print("⏰ Zamanlayıcı başlatıldı. Bekleniyor...")
print("   → 09:00 Sabah raporu")
print("   → 15:00 Öğleden sonra raporu")
print("   → 22:00 Akşam raporu")
print("   (Durdurmak için Ctrl+C)\n")

while True:
    schedule.run_pending()
    time.sleep(30)   # her 30 saniyede bir kontrol et
