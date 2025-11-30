from flask import Flask, request, jsonify
from flask_cors import CORS
from pyfcm import FCMNotification
import os
from dotenv import load_dotenv
import json

load_dotenv()

app = Flask(__name__)
CORS(app)


FCM_SERVER_KEY = os.getenv('FCM_SERVER_KEY')


push_service = FCMNotification(api_key=FCM_SERVER_KEY)

@app.route('/')
def home():
    return jsonify({"status": "OK", "message": "TripMate Notification Service"})

@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

@app.route('/send-notification', methods=['POST', 'OPTIONS'])
def send_notification():
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        
        required_fields = ['tokens', 'title', 'body']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    "success": False,
                    "error": f"Missing required field: {field}"
                }), 400
        
        tokens = data['tokens']
        title = data['title']
        body = data['body']
        custom_data = data.get('data', {})
        
        if not isinstance(tokens, list) or len(tokens) == 0:
            return jsonify({
                "success": False,
                "error": "Tokens must be a non-empty array"
            }), 400
        
        print(f"Sending notification to {len(tokens)} tokens")
        print(f"Title: {title}, Body: {body}")
        print(f"Data: {custom_data}")
        

        results = []
        for token in tokens:
            try:
        
                result = push_service.notify_single_device(
                    registration_id=token,
                    message_title=title,
                    message_body=body,
                    data_message=custom_data,
                    sound="default",
                    badge=1,
                    content_available=True
                )
                
                results.append({
                    "token": token[:10] + "...",  
                    "success": result.get('success', 0) == 1,
                    "message_id": result.get('results', [{}])[0].get('message_id'),
                    "error": result.get('results', [{}])[0].get('error')
                })
                
            except Exception as e:
                results.append({
                    "token": token[:10] + "...",
                    "success": False,
                    "error": str(e)
                })
        
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
        print(f"Error in send-notification: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/send-batch-notification', methods=['POST'])
def send_batch_notification():
    try:
        data = request.get_json()
        
        tokens = data['tokens']
        title = data['title']
        body = data['body']
        custom_data = data.get('data', {})
        
      
        result = push_service.notify_multiple_devices(
            registration_ids=tokens,
            message_title=title,
            message_body=body,
            data_message=custom_data,
            sound="default"
        )
        
        return jsonify({
            "success": True,
            "result": result
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)