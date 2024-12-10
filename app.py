from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_restx import Api, Resource, fields, reqparse
import requests
import os
import uuid
import logging
from functools import wraps
from secrets_manager import get_service_secrets
import jwt

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True, expose_headers=["Authorization"])
app.debug = True

# Initialize Flask-RestX
api = Api(app,
    version='1.0',
    title='Gnosis Composer API',
    description='API for managing conversations and content',
    doc='/docs'
)

ns = api.namespace('api', description='Gnosis Composer operations')

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

secrets = get_service_secrets('gnosis-composer')

C_PORT = int(secrets.get('PORT', 5000))
API_KEY = secrets.get('API_KEY')

# URLs for different services
AUTH_SERVICE_URL = secrets.get('AUTH_SERVICE_URL', 'http://localhost:5007')
CONVERSATION_SERVICE_URL = secrets.get('CONVERSATION_SERVICE_URL', 'http://localhost:5000')
UPLOAD_SERVICE_URL = secrets.get('UPLOAD_SERVICE_URL', 'http://localhost:5002')

EXEMPT_ROUTES = ['/api/login', '/api/register', '/api/auth/google']

# In-memory storage for upload status (in a real-world scenario, use a database)
upload_status = {}

def generate_correlation_id():
    return str(uuid.uuid4())

# Model definitions
register_model = api.model('Register', {
    'username': fields.String(required=True, description='Username'),
    'email': fields.String(required=True, description='Email'),
    'password': fields.String(required=True, description='Password')
})

login_model = api.model('Login', {
    'username': fields.String(required=True, description='Username'),
    'password': fields.String(required=True, description='Password')
})

google_auth_model = api.model('GoogleAuth', {
    'token': fields.String(required=True, description='Google OAuth token')
})

conversation_model = api.model('Conversation', {
    'user_id': fields.Integer(required=True, description='User ID'),
    'content_id': fields.Integer(required=True, description='Content ID'),
    'content_chunk_id': fields.Integer(required=False, description='Content Chunk ID')
})

reply_model = api.model('Reply', {
    'message': fields.String(required=True, description='Reply message')
})

shuffle_model = api.model('Shuffle', {
    'user_id': fields.Integer(required=True, description='User ID'),
    'volatility': fields.Float(required=False, default=0.5, description='Shuffle volatility')
})

batch_model = api.model('BatchConversations', {
    'user_id': fields.Integer(required=True, description='User ID'),
    'num_convos': fields.Integer(required=False, default=10, description='Number of conversations to create')
})

upload_model = api.model('Upload', {
    'user_id': fields.String(required=True, description='User ID'),
    'file': fields.Raw(required=True, description='File to upload')
})

# Response models
user_response = api.model('UserResponse', {
    'username': fields.String(description='Username'),
    'email': fields.String(description='Email'),
    'id': fields.Integer(description='User ID')
})

login_response = api.model('LoginResponse', {
    'message': fields.String(description='Status message'),
    'user': fields.Nested(user_response),
    'token': fields.String(description='JWT token')
})

conversation_response = api.model('ConversationResponse', {
    'id': fields.Integer(description='Conversation ID'),
    'user_id': fields.Integer(description='User ID'),
    'messages': fields.List(fields.Nested(api.model('Message', {
        'content': fields.String(description='Message content'),
        'role': fields.String(description='Message role (user/assistant)'),
        'timestamp': fields.DateTime(description='Message timestamp')
    })))
})

# Model for checking upload status
upload_status_model = api.model('UploadStatus', {
    'upload_id': fields.String(required=True, description='Upload ID to check status for')
})


# Update the response models to be more detailed
upload_status_response = api.model('UploadStatusResponse', {
    'upload_id': fields.String(description='Upload ID'),
    'status': fields.String(description='Upload status', enum=['pending', 'processing', 'completed', 'failed']),
    'progress': fields.Integer(description='Upload progress percentage'),
    'message': fields.String(description='Status message'),
    'created_at': fields.DateTime(description='Upload start time'),
    'updated_at': fields.DateTime(description='Last status update time'),
    'file_name': fields.String(description='Original file name'),
    'file_size': fields.Integer(description='File size in bytes')
})

@ns.route('/register')
class RegisterResource(Resource):
    @api.doc('register_user')
    @api.expect(register_model)
    @api.marshal_with(login_response)
    @api.response(201, 'User registered successfully')
    @api.response(400, 'Missing required fields')    
    @api.response(400, 'Username already exists')
    @api.response(400, 'Email already exists')
    @api.response(500, 'Registration failed')
    @api.response(503, 'Authentication service unavailable')
    def post(self):
        if not api.payload or not all(k in api.payload for k in ['username', 'email', 'password']):
            api.abort(400, 'Missing required fields')

        try:
            correlation_id = generate_correlation_id()
            logging.info("Registering user: %s, Correlation ID: %s", api.payload.get('username'), correlation_id)
            headers = {
                'X-API-KEY': API_KEY,
                'X-Correlation-ID': correlation_id
            }
            response = requests.post(f'{AUTH_SERVICE_URL}/api/register', json=api.payload, headers=headers)
            
            if response.status_code == 400:
                error_msg = response.json().get('error')
                logging.warning(f"Registration validation error: {error_msg}")
                api.abort(400, error_msg)
                
            elif response.status_code == 500:
                error_msg = response.json().get('error')
                logging.error(f"Registration failed: {error_msg}")
                api.abort(500, 'Registration failed')
                
            elif response.status_code == 201:
                logging.info(f"User registered successfully: {api.payload.get('username')}")
                return {
                    'message': 'User registered successfully',
                    'user': {
                        'username': api.payload.get('username'),
                        'email': api.payload.get('email')
                    }
                }, 201
                
            api.abort(response.status_code, response.json().get('error'))
                        
        except Exception as e:
            logging.error("Registration error: %s", str(e))
            api.abort(503, 'Authentication service unavailable')

@ns.route('/login')
class LoginResource(Resource):
    @api.doc('login_user')
    @api.expect(login_model)
    @api.marshal_with(login_response)
    @api.response(200, 'Login successful')
    @api.response(400, 'Missing username or password')
    @api.response(503, 'Authentication service unavailable')
    def post(self):
        if not api.payload or not all(k in api.payload for k in ['username', 'password']):
            api.abort(400, 'Missing username or password')

        try:
            correlation_id = generate_correlation_id()
            logging.info("Login attempt for user: %s, Correlation ID: %s", api.payload.get('username'), correlation_id)
            headers = {
                'X-API-KEY': API_KEY,
                'X-Correlation-ID': correlation_id
            }
            response = requests.post(f'{AUTH_SERVICE_URL}/api/login', json=api.payload, headers=headers)
            
            if response.status_code == 200:
                logging.info("User logged in successfully: %s", api.payload.get('username'))
                return {
                    'message': 'Login successful',
                    'user': {
                        'username': api.payload.get('username'),
                        'id': response.json().get('user').get('id')
                    },
                    'token': response.json().get('token')
                }, 200
            
            api.abort(response.status_code, response.json().get('error'))
                
        except Exception as e:
            logging.error("Login error: %s", str(e))
            api.abort(503, 'Authentication service unavailable')


@ns.route('/auth/google')
class GoogleAuthResource(Resource):
    @api.doc('google_auth')
    @api.expect(google_auth_model)
    @api.response(200, 'Authentication successful')
    @api.response(503, 'Authentication service unavailable')
    def post(self):
        try:
            correlation_id = generate_correlation_id()
            auth_url = f'{AUTH_SERVICE_URL}/api/auth/google'
            logging.info("=== Google Auth Debug ===")
            logging.info(f"Auth URL: {auth_url}")
            logging.info(f"Request Headers: {dict(request.headers)}")
            logging.info(f"Request Body: {request.json}")
            
            response = requests.post(
                auth_url,
                headers={
                    'Authorization': request.headers.get('Authorization'),
                    'Content-Type': 'application/json',
                    'X-API-KEY': API_KEY,
                    'X-Correlation-ID': correlation_id  # Add correlation ID to headers
                },
                json=request.json,
                timeout=10  # Add timeout to see if it's a connection issue
            )
            logging.info(f"Response Status: {response.status_code}")
            logging.info(f"Response Body: {response.json()}")
            return response.json(), response.status_code
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Request failed: {str(e)}")
            api.abort(503, f'Authentication service unavailable: {str(e)}')
        except Exception as e:
            logging.error(f"Unexpected error: {str(e)}")
            api.abort(503, f'Authentication service unavailable: {str(e)}')

@ns.route('/convos')
class ConversationCreateResource(Resource):
    @api.doc('list_conversations')
    @api.response(200, 'Success')
    @api.response(400, 'Missing user_id')
    @api.response(503, 'Conversation service unavailable')
    def get(self):
        """Get list of conversations"""
        user_id = request.args.get('user_id')
        limit = request.args.get('limit', 20)
        cursor = request.args.get('cursor')
        refresh = request.args.get('refresh', 'false')

        if not user_id:
            api.abort(400, 'user_id is required')

        try:
            correlation_id = generate_correlation_id()
            headers = {
                'X-API-KEY': API_KEY,
                'X-Correlation-ID': correlation_id
            }
            
            # Forward the request to conversation service with all query params
            response = requests.get(
                f'{CONVERSATION_SERVICE_URL}/api/convos',
                params={
                    'user_id': user_id,
                    'limit': limit,
                    'cursor': cursor,
                    'refresh': refresh
                },
                headers=headers
            )
            
            return response.json(), response.status_code
            
        except Exception as e:
            logging.error(f"Error fetching conversations: {str(e)}")
            api.abort(503, 'Conversation service unavailable')
                      
    @api.doc('create_conversation')
    @api.expect(conversation_model)
    @api.response(201, 'Conversation created successfully')
    @api.response(400, 'Invalid request')
    @api.response(500, 'Server error')
    def post(self):
        # Get data from api.payload instead of request.json when using flask-restx
        data = {
            'user_id': api.payload.get('user_id'),
            'content_id': api.payload.get('content_id'),
            'content_chunk_id': api.payload.get('content_chunk_id')  # Optional field
        }

        # Validate required fields
        if not data['user_id'] or not data['content_id']:
            return {'error': 'user_id and content_id are required'}, 400

        correlation_id = generate_correlation_id()
        headers = {
            'X-API-KEY': API_KEY,
            'X-Correlation-ID': correlation_id
        }
        
        logging.info("Creating conversation with data: %s, Correlation ID: %s", data, correlation_id)
        
        try:
            response = requests.post(
                f'{CONVERSATION_SERVICE_URL}/api/convos',
                json=data,
                headers=headers
            )
            
            if response.status_code == 201 or response.status_code == 200:  # Success status from conversation service
                logging.info("Conversation created successfully: %s", response.json())
                return response.json(), response.status_code
            elif response.status_code == 400:  # Bad request
                logging.warning("Bad request to conversation service: %s", response.json())
                return response.json(), 400
            else:
                logging.error("Unexpected response from conversation service: %s", response.json())
                return {'error': 'Failed to create conversation'}, 500
                
        except Exception as e:
            logging.error("Error creating conversation: %s", str(e))
            return {'error': 'Failed to create conversation'}, 500

@ns.route('/convos/<int:conversation_id>')
class ConversationResource(Resource):
    @api.doc('get_conversation')
    @api.expect(conversation_model)
    def get(self, conversation_id):
        correlation_id = generate_correlation_id()
        headers = {
            'X-API-KEY': API_KEY,
            'X-Correlation-ID': correlation_id
        }
        response = requests.get(f'{CONVERSATION_SERVICE_URL}/api/convos/{conversation_id}', headers=headers)
        return response.json(), response.status_code

    @api.doc('delete_conversation')
    def delete(self, conversation_id):
        correlation_id = generate_correlation_id()
        headers = {
            'X-API-KEY': API_KEY,
            'X-Correlation-ID': correlation_id
        }
        logging.info("Deleting conversation with ID: %d, Correlation ID: %s", conversation_id, correlation_id)
        response = requests.delete(f'{CONVERSATION_SERVICE_URL}/api/convos/{conversation_id}', headers=headers)
        logging.info("Delete conversation response: %s", response.json())
        return response.json(), response.status_code

@ns.route('/convos')
class ConversationCreateResource(Resource):
    @api.doc('create_conversation')
    @api.expect(conversation_model)
    def post(self):
        data = {
            'user_id': request.json.get('user_id'),
            'content_id': request.json.get('content_id')
        }
        correlation_id = generate_correlation_id()
        headers = {
            'X-API-KEY': API_KEY,
            'X-Correlation-ID': correlation_id
        }
        logging.info("Creating conversation with data: %s, Correlation ID: %s", data, correlation_id)
        response = requests.post(f'{CONVERSATION_SERVICE_URL}/api/convos', json=data, headers=headers)
        logging.info("Create conversation response: %s", response.json())
        return response.json(), response.status_code

@ns.route('/convos/<int:conversation_id>/reply')
class ConversationReplyResource(Resource):
    @api.doc('add_reply')
    @api.expect(reply_model)
    def put(self, conversation_id):
        data = {
            'message': request.json.get('message')
        }
        correlation_id = generate_correlation_id()
        headers = {
            'X-API-KEY': API_KEY,
            'X-Correlation-ID': correlation_id
        }
        logging.info("Adding reply to conversation %d with data: %s, Correlation ID: %s", conversation_id, data, correlation_id)
        response = requests.put(
            f'{CONVERSATION_SERVICE_URL}/api/convos/{conversation_id}/reply',
            json=data,
            headers=headers
        )
        logging.info("Add reply response: %s", response.json())
        return response.json(), response.status_code

@ns.route('/composer/shuffle-convos')
class ShuffleConversationsResource(Resource):
    @api.doc('shuffle_conversations')
    @api.expect(shuffle_model)
    @api.response(200, 'Success')
    @api.response(400, 'Missing user_id')
    @api.response(500, 'Server error')
    def post(self):
        if not request.json or 'user_id' not in request.json:
            api.abort(400, 'user_id is required')

        user_id = request.json['user_id']
        volatility = request.json.get('volatility', 0.5)  # Optional parameter

        try:
            correlation_id = generate_correlation_id()
            headers = {
                'X-API-KEY': API_KEY,
                'X-Correlation-ID': correlation_id
            }
            # Forward request to conversation service
            response = requests.post(
                f'{CONVERSATION_SERVICE_URL}/api/convos/shuffle',
                json={
                    'user_id': user_id,
                    'volatility': volatility
                },
                headers=headers
            )
            return response.json(), response.status_code
        except Exception as e:
            logging.error(f"Error requesting conversation shuffle: {e}")
            api.abort(500, 'Failed to request conversation shuffle')

@ns.route('/composer/batch-convos')  # Match the URL used in the test
class BatchConversationsResource(Resource):
    @api.doc('create_batch_conversations')
    @api.expect(batch_model)
    @api.response(202, 'Batch conversation creation initiated')
    @api.response(400, 'Missing user_id')
    @api.response(500, 'Server error')
    def post(self):
        if not api.payload or 'user_id' not in api.payload:
            logging.warning("user_id is required")
            api.abort(400, 'user_id is required')

        user_id = api.payload['user_id']
        num_convos = api.payload.get('num_convos', 10)  # Default to 10 if not specified

        try:
            correlation_id = generate_correlation_id()
            headers = {
                'X-API-KEY': API_KEY,
                'X-Correlation-ID': correlation_id
            }
            
            logging.info(f"Initiating batch conversation creation for user_id: {user_id}, num_convos: {num_convos}")
            
            # Send request to conversation service to create batch conversations
            response = requests.post(
                f"{CONVERSATION_SERVICE_URL}/api/convos/batch",
                json={
                    'user_id': user_id,
                    'num_convos': num_convos
                },
                headers=headers
            )

            logging.info(f"Batch conversation response: {response.status_code} - {response.text}")

            if response.status_code == 200:
                return {
                    "message": "Batch conversation creation initiated",
                    "user_id": user_id,
                    "num_convos": num_convos
                }, 200
            else:
                error_message = response.json().get('error', 'Unknown error')
                logging.error(f"Failed to create batch conversations: {error_message}")
                return {"error": error_message}, response.status_code

        except requests.exceptions.RequestException as e:
            logging.error(f"Network error in batch conversation creation: {str(e)}")
            return {"error": "Failed to connect to conversation service"}, 503
        except Exception as e:
            logging.error(f"Error requesting batch conversation creation: {str(e)}")
            return {"error": "Internal server error"}, 500

@ns.route('/upload')
class UploadResource(Resource):
    @api.doc('upload_file')
    @api.expect(upload_model)
    @api.response(202, 'Upload accepted')
    @api.response(400, 'Invalid request')
    @api.response(503, 'Upload service unavailable')
    def post(self):
        if 'file' not in request.files:
            api.abort(400, 'No file part in the request')

        file = request.files['file']
        user_id = request.form.get('user_id')

        if not user_id:
            api.abort(400, 'user_id is required')

        # Forward to content processor service
        files = {'file': (file.filename, file.read(), file.content_type)}
        data = {'user_id': user_id}
        correlation_id = generate_correlation_id()
        headers = {
            'X-API-KEY': API_KEY,
            'X-Correlation-ID': correlation_id
        }
        logging.info(f"Uploading file for user_id: {user_id}, Correlation ID: {correlation_id}")
        try:
            response = requests.post(f'{UPLOAD_SERVICE_URL}/api/upload',
                                   files=files,
                                   data=data,
                                   headers=headers)

            if response.status_code == 202:                
                return response.json(), response.status_code
            else:
                return response.json(), response.status_code

        except Exception as e:
            logging.error(f"Upload request failed: {str(e)}")
            api.abort(503, 'Upload service unavailable')

@ns.route('/upload_status/<string:upload_id>')
class UploadStatusResource(Resource):
    @api.doc('get_upload_status')
    @api.expect(upload_status_model)
    # @api.marshal_with(upload_status_response)
    @api.response(200, 'Success')
    @api.response(503, 'Upload service unavailable') 
    def get(self, upload_id):
        try:
            correlation_id = generate_correlation_id()
            headers = {
                'X-API-KEY': API_KEY,
                'X-Correlation-ID': correlation_id
            }
            response = requests.get(f'{UPLOAD_SERVICE_URL}/api/upload_status/{upload_id}', headers=headers)
            return response.json(), response.status_code
        except Exception as e:
            logging.error(f"Status check failed: {str(e)}")
            api.abort(503, 'Upload service unavailable')

# Authentication middleware
def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.path in EXEMPT_ROUTES:
            return f(*args, **kwargs)

        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            api.abort(401, 'Missing or invalid authorization header')
        
        token = auth_header.split(' ')[1]
        
        try:
            correlation_id = generate_correlation_id()
            headers = {
                'X-API-KEY': API_KEY,
                'X-Correlation-ID': correlation_id
            }
            response = requests.post(
                f'{AUTH_SERVICE_URL}/api/validate-token',
                json={'token': token},
                headers=headers
            )
            
            if response.status_code != 200:
                api.abort(401, 'Invalid token')
                
            request.user = response.json()['user']
            return f(*args, **kwargs)
            
        except Exception as e:
            logging.error(f"Token validation error: {str(e)}")
            api.abort(503, 'Authentication service unavailable')
            
    return decorated

@app.before_request
def before_request():
    # Exempt the /docs endpoint from logging and API key checks
    if request.path.startswith('/docs') or request.path.startswith('/swagger'):
        return

    logging.info("Received request: %s %s", request.method, request.url)
    logging.debug(f"Headers: {request.headers}")

    if request.method == 'OPTIONS':
        return {'status': 'ok'}, 200
    
    # Skip authentication for exempt routes
    if request.path in EXEMPT_ROUTES:
        return
        
    return requires_auth(lambda: None)()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=C_PORT)