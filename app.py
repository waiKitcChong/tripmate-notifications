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
            raise ValueError("FIREBASE_SERVICE_ACCOUNT environment variable is required")
        
        service_account_dict = json.loads(service_account_json)
        cred = credentials.Certificate(service_account_dict)
        
        # 初始化 Firebase
        firebase_app = initialize_app(cred)
        print("Firebase Admin initialized successfully")
        return firebase_app
        
    except Exception as e:
        print(f"Error initializing Firebase: {e}")
        return None

firebase_app = init_firebase()

@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "message": "FCM Notification Server is running",
        "version": "1.0.0"
    })

@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

@app.route('/send-notification', methods=['POST'])
def send_notification():
    try:
        data = request.get_json()
        
        # 驗證必要參數
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

        print(f"Sending notification to {len(tokens)} tokens")
        print(f"Title: {title}, Body: {body}")
        print(f"Data: {custom_data}")

        # 發送通知
        results = []
        for token in tokens:
            try:
                # 創建消息
                message = messaging.Message(
                    notification=messaging.Notification(
                        title=title,
                        body=body,
                    ),
                    token=token,
                    data=custom_data,
                    android=messaging.AndroidConfig(
                        priority='high',
                        notification=messaging.AndroidNotification(
                            sound='default',
                            click_action='FLUTTER_NOTIFICATION_CLICK'
                        )
                    ),
                    apns=messaging.APNSConfig(
                        payload=messaging.APNSPayload(
                            aps=messaging.Aps(
                                content_available=True,
                                badge=1,
                                sound='default'
                            )
                        )
                    )
                )
                
                # 發送消息
                response = messaging.send(message)
                
                results.append({
                    "token": token[:10] + "...",
                    "success": True,
                    "message_id": response,
                    "error": None
                })
                print(f"Successfully sent to {token[:10]}...")
                
            except Exception as token_error:
                error_msg = str(token_error)
                results.append({
                    "token": token[:10] + "...",
                    "success": False,
                    "message_id": None,
                    "error": error_msg
                })
                print(f"Failed to send to {token[:10]}...: {error_msg}")

        # 統計結果
        successful = len([r for r in results if r['success']])
        failed = len([r for r in results if not r['success']])
        
        print(f"Notification results: {successful} successful, {failed} failed")
        
        return jsonify({
            "success": True,
            "results": {
                "successful": successful,
                "failed": failed,
                "details": results
            }
        })
        
    except Exception as e:
        print(f"Error in send-notification: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/send-batch-notification', methods=['POST'])
def send_batch_notification():
    """批量發送通知到多個設備"""
    try:
        data = request.get_json()
        
        tokens = data.get('tokens', [])
        title = data.get('title', '')
        body = data.get('body', '')
        custom_data = data.get('data', {})
        
        if not tokens or not isinstance(tokens, list):
            return jsonify({"error": "Tokens array is required"}), 400
            
        if not title or not body:
            return jsonify({"error": "Title and body are required"}), 400

        # 創建多播消息
        message = messaging.MulticastMessage(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            tokens=tokens,
            data=custom_data,
        )
        
        # 發送批量消息
        response = messaging.send_multicast(message)
        
        results = {
            "successful": response.success_count,
            "failed": response.failure_count,
            "responses": [
                {
                    "token": tokens[i][:10] + "...",
                    "success": response.responses[i].success,
                    "message_id": response.responses[i].message_id if response.responses[i].success else None,
                    "error": str(response.responses[i].exception) if response.responses[i].exception else None
                }
                for i in range(len(tokens))
            ]
        }
        
        return jsonify({
            "success": True,
            "results": results
        })
        
    except Exception as e:
        print(f"Error in batch notification: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)