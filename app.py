from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import uuid
import logging
from functools import wraps

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True, expose_headers=["Authorization"])
# turn debug on
app.debug = True

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

C_PORT = 5001

# URLs for different services
# AUTH_SERVICE_URL = 'http://18.206.119.139:5007/'
# CONVERSATION_SERVICE_URL = 'http://54.165.240.60:5000'
# UPLOAD_SERVICE_URL = 'http://44.211.210.50:5000'

AUTH_SERVICE_URL = 'http://localhost:5007'
CONVERSATION_SERVICE_URL = 'http://localhost:5000'
UPLOAD_SERVICE_URL = 'http://localhost:5002'

EXEMPT_ROUTES = ['/api/login', '/api/register']  # Routes that don't need authentication

# In-memory storage for upload status (in a real-world scenario, use a database)
upload_status = {}

@app.route('/api/register', methods=['POST'])
def register():
    if not request.json or not all(k in request.json for k in ['username', 'email', 'password']):
        return jsonify({'error': 'Missing required fields'}), 400

    try:
        logging.info("Registering user: %s", request.json.get('username'))
        response = requests.post(f'{AUTH_SERVICE_URL}/api/register', json=request.json)
        
        if response.status_code == 201:
            logging.info("User registered successfully: %s", request.json.get('username'))
            return jsonify({
                'message': 'User registered successfully',
                'user': {
                    'username': request.json.get('username'),
                    'email': request.json.get('email')
                }
            }), 201
        else:
            logging.warning("Registration failed: %s", response.json().get('error'))
            return jsonify(response.json()), response.status_code
            
    except Exception as e:
        logging.error("Registration error: %s", str(e))
        return jsonify({'error': 'Authentication service unavailable'}), 503

@app.route('/api/login', methods=['POST'])
def login():
    if not request.json or not all(k in request.json for k in ['username', 'password']):
        return jsonify({'error': 'Missing username or password'}), 400

    try:
        logging.info("Login attempt for user: %s", request.json.get('username'))
        response = requests.post(f'{AUTH_SERVICE_URL}/api/login', json=request.json)
        
        if response.status_code == 200:
            logging.info("User logged in successfully: %s", request.json.get('username'))
            logging.debug(f"Token: {response.json().get('token')}")
            return jsonify({
                'message': 'Login successful',
                'user': {
                    'username': request.json.get('username'),
                    'id': response.json().get('user').get('id')
                },
                'token': response.json().get('token')
            }), 200
        else:
            logging.warning("Login failed for user: %s", request.json.get('username'))
            return jsonify(response.json()), response.status_code
            
    except Exception as e:
        logging.error("Login error: %s", str(e))
        return jsonify({'error': 'Authentication service unavailable'}), 503

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

@app.route('/api/convos/<int:conversation_id>', methods=['GET'])
def get_conversation(conversation_id):
    response = requests.get(f'{CONVERSATION_SERVICE_URL}/api/convos/{conversation_id}')
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


# Authentication middleware
def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.path in EXEMPT_ROUTES:
            return f(*args, **kwargs)

        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing or invalid authorization header'}), 401
        
        token = auth_header.split(' ')[1]
        
        try:
            # Validate token with auth service
            response = requests.post(
                f'{AUTH_SERVICE_URL}/api/validate-token',
                json={'token': token}
            )
            
            if response.status_code != 200:
                return jsonify({'error': 'Invalid token'}), 401
                
            # Add user info to request context
            request.user = response.json()['user']
            return f(*args, **kwargs)
            
        except Exception as e:
            logging.error(f"Token validation error: {str(e)}")
            return jsonify({'error': 'Authentication service unavailable'}), 503
            
    return decorated

@app.before_request
def before_request():
    logging.info("Received request: %s %s", request.method, request.url)
    logging.debug(f"Headers: {request.headers}")

    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200
    
    # Skip authentication for exempt routes
    if request.path in EXEMPT_ROUTES:
        return
        
    return requires_auth(lambda: None)()

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