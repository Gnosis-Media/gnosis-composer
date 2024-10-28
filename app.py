from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import uuid

app = Flask(__name__)
CORS(app)

C_PORT = 5001

# URLs for different services
AUTH_SERVICE_URL = 'http://3.86.58.152:5000'
# CONVERSATION_SERVICE_URL = 'http://54.165.240.60:5000'  # Updated from FEED_SERVICE_URL
CONVERSATION_SERVICE_URL = 'http://localhost:5000'
UPLOAD_SERVICE_URL = 'http://44.211.210.50:5000'

# In-memory storage for upload status (in a real-world scenario, use a database)
upload_status = {}

# Implement middleware here
@app.route('/api/register', methods=['POST'])
def register():
    response = requests.post(f'{AUTH_SERVICE_URL}/api/register', json=request.json)
    return jsonify(response.json()), response.status_code

@app.route('/api/login', methods=['POST'])
def login():
    response = requests.post(f'{AUTH_SERVICE_URL}/api/login', json=request.json)
    return jsonify(response.json()), response.status_code

# Conversation API
@app.route('/api/convos/random', methods=['GET'])
def get_convos():
    response = requests.get(f'{CONVERSATION_SERVICE_URL}/api/convos/random')
    return jsonify(response.json()), response.status_code

@app.route('/api/convos', methods=['GET'])
def get_convos_by_user_id():
    user_id = request.args.get('userId')
    page = request.args.get('page', 1)
    per_page = request.args.get('per_page', 10)
    response = requests.get(f'{CONVERSATION_SERVICE_URL}/api/convos', params={'userId': user_id, 'page': page, 'per_page': per_page})
    return jsonify(response.json()), response.status_code

@app.route('/api/convos/<int:id>/messages', methods=['GET'])
def get_convos_by_id(id):
    response = requests.get(f'{CONVERSATION_SERVICE_URL}/api/convos/{id}/messages')
    return jsonify(response.json()), response.status_code

@app.route('/api/convos/<int:id>', methods=['DELETE'])
def delete_convos_by_msg_id(id):
    response = requests.delete(f'{CONVERSATION_SERVICE_URL}/api/convos/{id}')
    return jsonify(response.json()), response.status_code

@app.route('/api/convos/<int:id>', methods=['PUT'])
def add_reply_to_conversation(id):
    response = requests.put(f'{CONVERSATION_SERVICE_URL}/api/convos/{id}', json=request.json)
    return jsonify(response.json()), response.status_code

@app.route('/api/convos', methods=['POST'])
def create_convo():
    response = requests.post(f'{CONVERSATION_SERVICE_URL}/api/convos', json=request.json)
    return jsonify(response.json()), response.status_code

@app.route('/api/upload', methods=['POST'])
def upload():
    # Generate a unique ID for this upload
    upload_id = str(uuid.uuid4())
    
    # Update status to "Accepted"
    upload_status[upload_id] = "Accepted"
    
    # Forward the file to the upload service
    files = {'file': request.files['file']}
    data = {'user_id': request.form.get('user_id')}
    
    def upload_file():
        response = requests.post(f'{UPLOAD_SERVICE_URL}/api/upload', files=files, data=data)
        if response.status_code == 200:
            upload_status[upload_id] = "Completed"
        else:
            upload_status[upload_id] = "Failed"
    
    # Start the upload process in a separate thread
    import threading
    threading.Thread(target=upload_file).start()
    
    return jsonify({
        "message": "Upload request accepted",
        "upload_id": upload_id
    }), 202

@app.route('/api/upload_status/<upload_id>', methods=['GET'])
def check_upload_status(upload_id):
    status = upload_status.get(upload_id, "Not Found")
    return jsonify({"status": status})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=C_PORT)