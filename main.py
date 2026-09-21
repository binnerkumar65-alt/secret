import os
import asyncio
from flask import Flask, request, render_template_string
from telethon import TelegramClient
from telethon.sessions import StringSession

# ---------- Config (Render ke Environment Variables se) ----------
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION_STRING = os.environ["SESSION_STRING"]
CHANNEL_USERNAME = "@apka_channel_yahan"   # <-- apne public channel ka username likho

# ---------- Telegram Client (sirf ek baar banega) ----------
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
    # Telethon async hai, Flask sync hai — isliye event loop mein chalana padta hai
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

# ---------- Simple HTML Upload Form ----------
HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Photo Upload to Telegram</title>
    <style>
        body { font-family: Arial; max-width: 500px; margin: 50px auto; }
        input, button { width: 100%; padding: 10px; margin: 8px 0; }
        button { background: #0088cc; color: white; border: none; cursor: pointer; }
        .ok { color: green; } .err { color: red; }
    </style>
</head>
<body>
    <h2>Photo Upload karo → Telegram Channel</h2>
    <form action="/upload" method="POST" enctype="multipart/form-data">
        <input type="file" name="photo" accept="image/*" required>
        <input type="text" name="caption" placeholder="Caption (optional)">
        <button type="submit">Send to Channel</button>
    </form>
    {% if message %}<p class="{{ 'ok' if success else 'err' }}">{{ message }}</p>{% endif %}
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_PAGE)

@app.route("/upload", methods=["POST"])
def upload():
    photo = request.files.get("photo")
    caption = request.form.get("caption", "")

    if not photo:
        return render_template_string(HTML_PAGE, message="Photo select karo!", success=False)

    # Photo ko temporarily save karo
    temp_path = "/tmp/uploaded_photo.jpg"
    photo.save(temp_path)

    try:
        send_photo_to_channel(temp_path, caption)
        return render_template_string(HTML_PAGE, message="✅ Photo channel par send ho gayi!", success=True)
    except Exception as e:
        return render_template_string(HTML_PAGE, message=f"❌ Error: {e}", success=False)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
