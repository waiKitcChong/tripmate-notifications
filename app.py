from flask import Flask, request, jsonify
from flask_cors import CORS
from firebase_admin import credentials, messaging, initialize_app
import os
from dotenv import load_dotenv
import json

# 加載環境變數
load_dotenv()

app = Flask(__name__)
CORS(app)

# 初始化 Firebase Admin
def init_firebase():
    try:
        # 從環境變數讀取 service account
        service_account_json = os.getenv('FIREBASE_SERVICE_ACCOUNT')
        
        if not service_account_json:
            print("❌ FIREBASE_SERVICE_ACCOUNT environment variable is missing")
            raise ValueError("FIREBASE_SERVICE_ACCOUNT environment variable is required")
        
        print("✅ Environment variable found")
        service_account_dict = json.loads(service_account_json)
        print(f"✅ Project ID: {service_account_dict.get('project_id')}")
        
        cred = credentials.Certificate(service_account_dict)
        
        # 初始化 Firebase
        firebase_app = initialize_app(cred)
        print("✅ Firebase Admin initialized successfully")
        return firebase_app
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing error: {e}")
        return None
    except Exception as e:
        print(f"❌ Error initializing Firebase: {e}")
        return None

firebase_app = init_firebase()

@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "message": "FCM Notification Server is running",
        "firebase_initialized": firebase_app is not None,
        "version": "1.0.0"
    })

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy" if firebase_app else "unhealthy",
        "firebase": "connected" if firebase_app else "disconnected"
    })

@app.route('/debug')
def debug():
    service_account_json = os.getenv('FIREBASE_SERVICE_ACCOUNT')
    return jsonify({
        "firebase_initialized": firebase_app is not None,
        "env_var_exists": bool(service_account_json),
        "env_var_length": len(service_account_json) if service_account_json else 0,
        "project_id": json.loads(service_account_json).get('project_id') if service_account_json else None
    })

@app.route('/send-notification', methods=['POST'])
def send_notification():
    try:
        # 檢查 Firebase 是否初始化
        if not firebase_app:
            return jsonify({
                "success": False,
                "error": "Firebase not initialized. Check server logs."
            }), 500
            
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
            
        tokens = data.get('tokens', [])
        title = data.get('title', '')
        body = data.get('body', '')
        custom_data = data.get('data', {})
        
        if not tokens or not isinstance(tokens, list):
            return jsonify({"error": "Tokens array is required"}), 400
            
        if not title or not body:
            return jsonify({"error": "Title and body are required"}), 400

        print(f"📨 Sending notification to {len(tokens)} tokens")
        print(f"📝 Title: {title}, Body: {body}")

        # 使用 Firebase Admin 發送通知
        results = []
        for token in tokens:
            try:
                # 創建 FCM v1 格式的消息
                message = messaging.Message(
                    notification=messaging.Notification(
                        title=title,
                        body=body,
                    ),
                    token=token,
                    data=custom_data,
                    android=messaging.AndroidConfig(
                        priority='high'
                    ),
                    apns=messaging.APNSConfig(
                        payload=messaging.APNSPayload(
                            aps=messaging.Aps(
                                sound='default'
                            )
                        )
                    )
                )
                
                # 發送消息（使用 FCM HTTP v1 API）
                response = messaging.send(message)
                
                results.append({
                    "token": token[:10] + "...",
                    "success": True,
                    "message_id": response,
                    "error": None
                })
                print(f"✅ Successfully sent to {token[:10]}...")
                
            except Exception as token_error:
                error_msg = str(token_error)
                results.append({
                    "token": token[:10] + "...",
                    "success": False,
                    "message_id": None,
                    "error": error_msg
                })
                print(f"❌ Failed to send to {token[:10]}...: {error_msg}")

        successful = len([r for r in results if r['success']])
        failed = len([r for r in results if not r['success']])
        
        print(f"📊 Notification results: {successful} successful, {failed} failed")
        
        return jsonify({
            "success": True,
            "results": {
                "successful": successful,
                "failed": failed,
                "details": results
            }
        })
        
    except Exception as e:
        print(f"💥 Error in send-notification: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Starting server on port {port}")
    print(f"🔧 Firebase initialized: {firebase_app is not None}")
    app.run(host='0.0.0.0', port=port, debug=False)