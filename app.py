from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import uuid
import logging

app = Flask(__name__)
CORS(app)
# turn debug on
app.debug = True

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S', filename='app.log')

C_PORT = 5001

# URLs for different services
AUTH_SERVICE_URL = 'http://3.86.58.152:5000'
# CONVERSATION_SERVICE_URL = 'http://54.165.240.60:5000'  # Updated from FEED_SERVICE_URL
CONVERSATION_SERVICE_URL = 'http://localhost:5000'
UPLOAD_SERVICE_URL = 'http://localhost:5002'

# In-memory storage for upload status (in a real-world scenario, use a database)
upload_status = {}

# Implement middleware here
@app.route('/api/register', methods=['POST'])
def register():
    logging.info("Registering user with data: %s", request.json)
    response = requests.post(f'{AUTH_SERVICE_URL}/api/register', json=request.json)
    logging.info("Register response: %s", response.json())
    return jsonify(response.json()), response.status_code

@app.route('/api/login', methods=['POST'])
def login():
    logging.info("Logging in user with data: %s", request.json)
    response = requests.post(f'{AUTH_SERVICE_URL}/api/login', json=request.json)
    logging.info("Login response: %s", response.json())
    return jsonify(response.json()), response.status_code

# Conversation API
@app.route('/api/convos', methods=['GET'])
def get_convos():
    user_id = request.args.get('user_id')
    limit = request.args.get('limit', 10)
    random = request.args.get('random', 'false')
    
    params = {
        'user_id': user_id,
        'limit': limit,
        'random': random
    }
    
    logging.info("Fetching conversations with params: %s", params)
    response = requests.get(f'{CONVERSATION_SERVICE_URL}/api/convos', params=params)
    logging.info("Get conversations response: %s", response.json())
    return jsonify(response.json()), response.status_code

@app.route('/api/convos', methods=['POST'])
def create_convo():
    data = {
        'user_id': request.json.get('user_id'),
        'message': request.json.get('message')
    }
    logging.info("Creating conversation with data: %s", data)
    response = requests.post(f'{CONVERSATION_SERVICE_URL}/api/convos', json=data)
    logging.info("Create conversation response: %s", response.json())
    return jsonify(response.json()), response.status_code

@app.route('/api/convos/<int:conversation_id>/reply', methods=['PUT'])
def add_reply(conversation_id):
    data = {
        'message': request.json.get('message')
    }
    logging.info("Adding reply to conversation %d with data: %s", conversation_id, data)
    response = requests.put(
        f'{CONVERSATION_SERVICE_URL}/api/convos/{conversation_id}/reply', 
        json=data
    )
    logging.info("Add reply response: %s", response.json())
    return jsonify(response.json()), response.status_code

@app.route('/api/convos/<int:conversation_id>', methods=['DELETE'])
def delete_conversation(conversation_id):
    logging.info("Deleting conversation with ID: %d", conversation_id)
    response = requests.delete(f'{CONVERSATION_SERVICE_URL}/api/convos/{conversation_id}')
    logging.info("Delete conversation response: %s", response.json())
    return jsonify(response.json()), response.status_code

@app.route('/api/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400

    file = request.files['file']
    user_id = request.form.get('user_id')

    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400

    # Forward to content processor service
    files = {'file': (file.filename, file.read(), file.content_type)}
    data = {'user_id': user_id}

    try:
        response = requests.post(f'{UPLOAD_SERVICE_URL}/api/upload', 
                               files=files, 
                               data=data)
        
        if response.status_code == 202:
            upload_data = response.json()
            return jsonify({
                'message': 'Upload request accepted',
                'upload_id': upload_data['upload_id']
            }), 202
        else:
            return jsonify(response.json()), response.status_code

    except Exception as e:
        logging.error(f"Upload request failed: {str(e)}")
        return jsonify({'error': 'Upload service unavailable'}), 503

@app.route('/api/upload_status/<upload_id>', methods=['GET'])
def check_upload_status(upload_id):
    try:
        response = requests.get(f'{UPLOAD_SERVICE_URL}/api/upload_status/{upload_id}')
        return jsonify(response.json()), response.status_code
    except Exception as e:
        logging.error(f"Status check failed: {str(e)}")
        return jsonify({'error': 'Upload service unavailable'}), 503

@app.route('/api/files', methods=['GET'])
def get_files():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400

    try:
        response = requests.get(f'{UPLOAD_SERVICE_URL}/api/files', 
                              params={'user_id': user_id})
        return jsonify(response.json()), response.status_code
    except Exception as e:
        logging.error(f"File list request failed: {str(e)}")
        return jsonify({'error': 'Upload service unavailable'}), 503
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=C_PORT)