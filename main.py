import os
import requests
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from flask import Flask, request, jsonify
from flask_cors import CORS
import asyncio
import concurrent.futures
import threading

API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
SESSION_STRING = os.environ.get("SESSION_STRING", "")
CHANNEL_USERNAME = "Cartoon_crazy_toons"
FIREBASE_DB_URL = "https://neetjee-ca8f5-default-rtdb.firebaseio.com/images.json"

app = Flask(__name__)
CORS(app)

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

@app.route('/')
def home():
    return "Bridge Server is running!"

@app.route('/upload', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        return jsonify({"error": "Image file nahi mili"}), 400
    
    file = request.files['image']
    temp_path = os.path.join('/tmp', file.filename)
    file.save(temp_path)

    try:
        # Thread-safe tarike se Telegram par file bhejna with timeout
        future = asyncio.run_coroutine_threadsafe(
            client.send_file(CHANNEL_USERNAME, temp_path), 
            client.loop
        )
        message = future.result(timeout=45) # 45 seconds timeout taaki atke nahi
        post_id = message.id
        
        if os.path.exists(temp_path):
            os.remove(temp_path)

        embed_script = f'<script async src="https://telegram.org/js/telegram-widget.js?24" data-telegram-post="{CHANNEL_USERNAME}/{post_id}" data-width="100%"></script>'
        
        firebase_payload = {
            "post_id": post_id,
            "embed_code": embed_script,
            "date": str(post_id)
        }
        
        requests.post(FIREBASE_DB_URL, json=firebase_payload)

        return jsonify({"success": True, "post_id": post_id}), 200

    except concurrent.futures.TimeoutError:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return jsonify({"error": "Telegram par upload karne me time limit exceed ho gayi."}), 500
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return jsonify({"error": str(e)}), 500

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

if __name__ == '__main__':
    t = threading.Thread(target=run_flask)
    t.start()
    
    with client:
        print("Telegram Bridge Client connected...")
        client.run_until_disconnected()
