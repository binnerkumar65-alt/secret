import os
import asyncio
from flask import Flask, request, jsonify
from telethon import TelegramClient
from telethon.sessions import StringSession

# ---------- Config ----------
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION_STRING = os.environ["SESSION_STRING"]
CHANNEL_USERNAME = "@Cartoon_crazy_toons"   # ✅ Aapka channel

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
        loop.run_until_complete(
            client.send_file(CHANNEL_USERNAME, photo_path, caption=caption)
        )
    finally:
        loop.close()

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
        send_photo_to_channel(temp_path, caption)
        return jsonify({"success": True, "message": "✅ Photo channel par send ho gayi!"})
    except Exception as e:
        return jsonify({"success": False, "message": f"❌ Error: {e}"}), 500
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
