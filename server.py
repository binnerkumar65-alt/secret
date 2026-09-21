import os
import time
from flask import Flask, request, jsonify
from flask_cors import CORS
import boto3
from botocore.config import Config
import firebase_admin
from firebase_admin import credentials, firestore
import json

app = Flask(__name__)
CORS(app)

# 1. Firebase Initialize karein
firebase_json_str = os.environ.get('FIREBASE_CONFIG_JSON')
if firebase_json_str:
    cred_dict = json.loads(firebase_json_str)
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
else:
    raise ValueError("FIREBASE_CONFIG_JSON environment variable set nahi hai!")

# 2. Internet Archive (S3-compatible) Configuration
s3 = boto3.client(
    's3',
    endpoint_url='https://s3.us.archive.org',
    aws_access_key_id=os.environ.get('IA_ACCESS_KEY'),
    aws_secret_access_key=os.environ.get('IA_SECRET_KEY'),
    config=Config(
        signature_version='s3',
        s3={'addressing_style': 'path'}
    )
)

@app.route('/upload', methods=['POST'])
def upload_photo():
    if 'photo' not in request.files:
        return jsonify({'error': 'Koi photo select nahi ki gayi hai.'}), 400
    
    file = request.files['photo']
    if file.filename == '':
        return jsonify({'error': 'File ka naam khali hai.'}), 400

    try:
        bucket_name = os.environ.get('IA_BUCKET_NAME', 'binner-unique-photos-item-2026')
        file_name = f"uploads/{int(time.time())}_{file.filename}"
        
        file_bytes = file.read()
        content_type = file.content_type or 'image/jpeg'

        # A. Pehle check karein / Bucket create karein agar nahi hai
        try:
            s3.head_bucket(Bucket=bucket_name)
        except Exception:
            try:
                s3.create_bucket(Bucket=bucket_name)
            except Exception as bucket_err:
                print("Bucket creation notice:", str(bucket_err))

        # B. Internet Archive par photo upload karein
        s3.put_object(
            Bucket=bucket_name,
            Key=file_name,
            Body=file_bytes,
            ContentType=content_type,
            ACL='public-read'
        )

        # Internet Archive ka public URL banana
        internet_archive_url = f"https://archive.org/download/{bucket_name}/{file_name}"

        # C. Firebase Firestore mein URL save karein
        doc_ref = db.collection('photos').document()
        doc_ref.set({
            'url': internet_archive_url,
            'createdAt': firestore.SERVER_TIMESTAMP
        })

        return jsonify({
            'success': True,
            'message': 'Photo successfully uploaded and saved!',
            'url': internet_archive_url,
            'firebaseId': doc_ref.id
        })

    except Exception as e:
        print("Upload Error:", str(e))
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=port)
