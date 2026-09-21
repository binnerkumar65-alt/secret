import os
import time
import json as jsonlib
import asyncio
from urllib import request as urlrequest
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
    try:
        payload = jsonlib.dumps(data).encode("utf-8")
        req = urlrequest.Request(
            f"{FIREBASE_DB_URL}/photos.json",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urlrequest.urlopen(req, timeout=10) as response:
            return response.status == 200
    except Exception as e:
        print(f"Firebase push failed: {e}")
        return False

# ---------- Telegram Client (Global Setup) ----------
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
loop = asyncio.get_event_loop()

async def init_telegram():
    if not client.is_connected():
        await client.connect()
    if not await client.is_user_authorized():
        raise RuntimeError("Session string invalid ya expired hai!")

# Startup par hi client connect kar lo
try:
    loop.run_until_complete(init_telegram())
except Exception as e:
    print(f"Telegram initialization error: {e}")

def send_photo_to_channel(photo_path, caption=""):
    async def send_async():
        if not client.is_connected():
            await client.connect()
        message = await client.send_file(CHANNEL_USERNAME, photo_path, caption=caption)
        return message

    # Existing event loop ka use karein, naya loop baar-baar na banayein
    future = asyncio.run_coroutine_threadsafe(send_async(), loop)
    return future.result(timeout=30)

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
    return "✅ Server ekdum mast chal raha hai!"

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

        # 3. Success response ke sath embed_code bhi bhejo
        return jsonify({
            "success": True,
            "embed_code": embed_code,
            "photo_link": photo_link,
            "message": "✅ Photo channel par successfully chali gayi!"
        })

    except Exception as e:
        return jsonify({"success": False, "message": f"❌ Error: {e}"}), 500
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
