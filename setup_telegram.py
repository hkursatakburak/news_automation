"""
Telegram kurulumunu test eder ve Chat ID'nizi bulmanıza yardımcı olur.
Çalıştır: python setup_telegram.py
"""

import os
import requests

TOKEN = input("Telegram Bot Token'ınızı girin: ").strip()

print("\n1. Telegram'da botunuzu açın ve /start yazın.")
input("   Gönderdikten sonra Enter'a basın...")

resp = requests.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates").json()
updates = resp.get("result", [])

if not updates:
    print("\n⚠️  Güncelleme bulunamadı. Botunuza bir mesaj gönderdiniz mi?")
else:
    chat = updates[-1]["message"]["chat"]
    chat_id = chat["id"]
    name    = chat.get("first_name", "") + " " + chat.get("last_name", "")
    print(f"\n✅ Chat ID bulundu: {chat_id}")
    print(f"   İsim: {name.strip()}")
    print(f"\n.env dosyanıza şunu ekleyin:")
    print(f"   TELEGRAM_CHAT_ID={chat_id}")

    # Test mesajı gönder
    send = input("\nTest mesajı gönderilsin mi? (e/h): ").strip().lower()
    if send == "e":
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": "✅ <b>Savunma & YZ Haber Ajanı</b> başarıyla bağlandı!\n\n"
                        "Artık 09:00, 15:00 ve 22:00'de haberlerinizi alacaksınız. 🛡️",
                "parse_mode": "HTML",
            },
        )
        print("   Test mesajı gönderildi!")
