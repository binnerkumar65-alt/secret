import os
import requests
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from flask import Flask
import threading

# Environment variables se credentials aur session lena
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
SESSION_STRING = os.environ.get("SESSION_STRING", "")
CHANNEL_USERNAME = "Cartoon_crazy_toons"
FIREBASE_DB_URL = "https://neetjee-ca8f5-default-rtdb.firebaseio.com/images.json"

# Flask app taaki Render web service active rahe
app = Flask(__name__)

@app.route('/')
def home():
    return "Telegram Embed Script Bot is running!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# StringSession ke sath TelegramClient setup
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

@client.on(events.NewMessage(chats=CHANNEL_USERNAME))
async def handle_new_message(event):
    # Check karein ki message me photo/image hai ya nahi
    if event.photo:
        print("Nayi image post detect hui hai...")
        try:
            post_id = event.id
            
            # Aapke mange gaye format ke mutabiq HTML Embed Script banana
            embed_script = f'<script async src="https://telegram.org/js/telegram-widget.js?24" data-telegram-post="{CHANNEL_USERNAME}/{post_id}" data-width="100%"></script>'
            print(f"Embed Script ban gaya: {embed_script}")

            # Firebase payload me embed script bhejna
            firebase_payload = {
                "post_id": post_id,
                "embed_code": embed_script,
                "date": str(event.date)
            }
            
            # Firebase par push karna
            fb_response = requests.post(FIREBASE_DB_URL, json=firebase_payload)
            if fb_response.status_code == 200:
                print("Embed Script successfully Firebase me push ho gaya!")
            else:
                print(f"Firebase error: {fb_response.text}")

        except Exception as e:
            print(f"Error aaya: {e}")

def start_telegram_bot():
    with client:
        print("Telethon bot start ho gaya hai aur channel sun raha hai...")
        client.run_until_disconnected()

if __name__ == '__main__':
    # Flask server ko alag thread me chalayein
    t = threading.Thread(target=run_flask)
    t.start()
    
    # Telegram bot ko start karein
    start_telegram_bot()
