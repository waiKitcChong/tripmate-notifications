from flask import Flask, request, jsonify
from flask_cors import CORS
from firebase_admin import credentials, messaging, initialize_app
import os
from dotenv import load_dotenv
import json


load_dotenv()

app = Flask(__name__)
CORS(app)


@app.route('/send-call-notification', methods=['POST'])
def send_call_notification():
    try:
        if not firebase_app:
            return jsonify({
                "success": False,
                "error": "Firebase not initialized"
            }), 500
            
        data = request.get_json()
        
        required_fields = ['target_token', 'caller_id', 'caller_name', 'call_type', 'channel_name']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        target_token = data['target_token']
        caller_id = data['caller_id']
        caller_name = data['caller_name']
        call_type = data['call_type']  # 'video' or 'voice'
        channel_name = data['channel_name']
        call_id = data.get('call_id', channel_name)
        
        print(f"📞 Sending call notification from {caller_name} ({caller_id})")
        
        # Prepare notification data
        notification_data = {
            'type': 'incoming_call',
            'caller_id': caller_id,
            'caller_name': caller_name,
            'call_type': call_type,
            'channel_name': channel_name,
            'call_id': call_id,
            'timestamp': str(datetime.utcnow())
        }
        
        message = messaging.Message(
            data=notification_data,
            token=target_token,
            android=messaging.AndroidConfig(
                priority='high',
                notification=messaging.AndroidNotification(
                    title=f"Incoming {call_type} call",
                    body=f"{caller_name} is calling you",
                    icon='@mipmap/ic_launcher',
                    color='#FF4081',
                    sound='default',
                    channel_id='calls_channel',
                    importance='high'
                ),
                direct_boot_ok=True
            ),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        alert=messaging.ApsAlert(
                            title=f"Incoming {call_type} call",
                            body=f"{caller_name} is calling you"
                        ),
                        sound='default',
                        category='INCOMING_CALL',
                        content_available=True,
                        mutable_content=True
                    )
                )
            ),
            notification=messaging.Notification(
                title=f"Incoming {call_type} call",
                body=f"{caller_name} is calling you"
            )
        )
        
        response = messaging.send(message)
        
        return jsonify({
            "success": True,
            "message_id": response,
            "data": notification_data
        })
        
    except Exception as e:
        print(f"💥 Error in send-call-notification: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/cancel-call-notification', methods=['POST'])
def cancel_call_notification():
    try:
        data = request.get_json()
        
        if not data or 'target_token' not in data:
            return jsonify({"error": "target_token is required"}), 400
        
        target_token = data['target_token']
        call_id = data.get('call_id', '')
        
        print(f"📞 Cancelling call notification for token: {target_token[:10]}...")
        
        message = messaging.Message(
            data={
                'type': 'call_cancelled',
                'call_id': call_id,
                'timestamp': str(datetime.utcnow())
            },
            token=target_token,
            android=messaging.AndroidConfig(
                priority='high'
            )
        )
        
        response = messaging.send(message)
        
        return jsonify({
            "success": True,
            "message": "Call cancelled notification sent"
        })
        
    except Exception as e:
        print(f"💥 Error in cancel-call-notification: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


def init_firebase():
    try:
        
        service_account_json = os.getenv('FIREBASE_SERVICE_ACCOUNT')
        
        if not service_account_json:
            print("❌ FIREBASE_SERVICE_ACCOUNT environment variable is missing")
            raise ValueError("FIREBASE_SERVICE_ACCOUNT environment variable is required")
        
        print("✅ Environment variable found")
        service_account_dict = json.loads(service_account_json)
        print(f"✅ Project ID: {service_account_dict.get('project_id')}")
        
        cred = credentials.Certificate(service_account_dict)
        
     
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


        results = []
        for token in tokens:
            try:
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