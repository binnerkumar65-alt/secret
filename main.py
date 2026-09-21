import os
import time
import asyncio
import requests
from flask import Flask, request, jsonify
from telethon import TelegramClient
from telethon.sessions import StringSession

# ---------- Config ----------
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION_STRING = os.environ["SESSION_STRING"]
CHANNEL_USERNAME = "@Cartoon_crazy_toons"

# ---------- Firebase ----------
FIREBASE_DB_URL = "https://neetjee-ca8f5-default-rtdb.firebaseio.com/"

def push_to_firebase(data):
    """Firebase Realtime DB mein data push karo (REST API se)"""
    try:
        response = requests.post(
            f"{FIREBASE_DB_URL}/photos.json",
            json=data,
            timeout=10
        )
        return response.ok
    except Exception as e:
        print(f"Firebase push failed: {e}")
        return False

# ---------- Telegram Client ----------
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
client_started = False

async def ensure_client():
    global client_started
    if not client_started:
        await client.connect()
        if not await client.is_user_authorized():
            raise RuntimeError("Session string invalid ya expired hai!")
        client_started = True

def send_photo_to_channel(photo_path, caption=""):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(ensure_client())
        # Message object return hota hai — isse photo ka link banayenge
        message = loop.run_until_complete(
            client.send_file(CHANNEL_USERNAME, photo_path, caption=caption)
        )
        return message
    finally:
        loop.close()

# ---------- Flask App ----------
app = Flask(__name__)

# ---------- CORS Fix ----------
@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "POST, GET, OPTIONS"
    return response

@app.route("/")
def index():
    return "✅ Server chal raha hai! HTML file se upload karo."

@app.route("/upload", methods=["POST", "OPTIONS"])
def upload():
    if request.method == "OPTIONS":
        return "", 200

    photo = request.files.get("photo")
    caption = request.form.get("caption", "")

    if not photo:
        return jsonify({"success": False, "message": "Photo select karo!"}), 400

    temp_path = "/tmp/uploaded_photo.jpg"
    photo.save(temp_path)

    try:
        # 1. Telegram channel par bhejo
        message = send_photo_to_channel(temp_path, caption)

        # 2. Photo ka link aur embed code banao
        channel_name = CHANNEL_USERNAME.replace("@", "")
        photo_link = f"https://t.me/{channel_name}/{message.id}"
        embed_code = f'<script async src="https://telegram.org/js/telegram-widget.js?24" data-telegram-post="{channel_name}/{message.id}" data-width="100%"></script>'

        # 3. Firebase mein push karo
        firebase_data = {
            "photo_link": photo_link,
            "embed_code": embed_code,
            "post_id": f"{channel_name}/{message.id}",
            "caption": caption,
            "message_id": message.id,
            "timestamp": int(time.time())
        }
        firebase_ok = push_to_firebase(firebase_data)

        if firebase_ok:
            return jsonify({
                "success": True,
                "message": f"✅ Photo channel par gayi! Embed link Firebase mein push ho gaya!"
            })
        else:
            return jsonify({
                "success": True,
                "message": f"⚠️ Photo channel par gayi ({photo_link}), par Firebase push failed!"
            })
    except Exception as e:
        return jsonify({"success": False, "message": f"❌ Error: {e}"}), 500
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
