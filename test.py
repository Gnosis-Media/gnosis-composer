import requests
import json

# Base URL of your composer service
BASE_URL = "http://localhost:5001"  # Adjust this if your service is running on a different port or host

def print_response(response):
    print(f"Status Code: {response.status_code}")
    print("Response:")
    print(json.dumps(response.json(), indent=2))
    print("\n" + "="*50 + "\n")

# Test register endpoint
# def test_register():
#     print("Testing /api/register")
#     data = {"username": "testuser", "password": "testpass"}
#     response = requests.post(f"{BASE_URL}/api/register", json=data)
#     print_response(response)

# # Test login endpoint
# def test_login():
#     print("Testing /api/login")
#     data = {"username": "testuser", "password": "testpass"}
#     response = requests.post(f"{BASE_URL}/api/login", json=data)
#     print_response(response)

# Test get random conversations endpoint
def test_get_random_convos():
    print("Testing /api/convos/random")
    response = requests.get(f"{BASE_URL}/api/convos/random")
    print_response(response)

# Test get conversations by user ID endpoint
def test_get_convos_by_user_id():
    print("Testing /api/convos (GET)")
    params = {"userId": 1, "page": 1, "per_page": 10}
    response = requests.get(f"{BASE_URL}/api/convos", params=params)
    print_response(response)

# Test get conversation messages by ID endpoint
def test_get_convo_messages():
    print("Testing /api/convos/<id>/messages")
    convo_id = 1  # Replace with a valid conversation ID
    response = requests.get(f"{BASE_URL}/api/convos/{convo_id}/messages")
    print_response(response)

# Test delete conversation endpoint
def test_delete_convo():
    print("Testing /api/convos/<id> (DELETE)")
    convo_id = 1  # Replace with a valid conversation ID
    response = requests.delete(f"{BASE_URL}/api/convos/{convo_id}")
    print_response(response)

# Test add reply to conversation endpoint
def test_add_reply_to_convo():
    print("Testing /api/convos/<id> (PUT)")
    convo_id = 1  # Replace with a valid conversation ID
    data = {"reply": "This is a test reply"}
    response = requests.put(f"{BASE_URL}/api/convos/{convo_id}", json=data)
    print_response(response)

# Test create conversation endpoint
def test_create_convo():
    print("Testing /api/convos (POST)")
    data = {"conversation": {"user_id": 1}}
    response = requests.post(f"{BASE_URL}/api/convos", json=data)
    print_response(response)

# Test upload file endpoint
def test_upload_file():
    print("Testing /api/upload")
    files = {'file': ('test.txt', b'This is a test file content')}
    data = {'user_id': '1'}
    response = requests.post(f"{BASE_URL}/api/upload", files=files, data=data)
    print_response(response)
    return response.json().get('upload_id')

# Test check upload status endpoint
def test_check_upload_status(upload_id):
    print("Testing /api/upload_status/<upload_id>")
    response = requests.get(f"{BASE_URL}/api/upload_status/{upload_id}")
    print_response(response)

if __name__ == "__main__":
    # test_register()
    # test_login()
    test_get_random_convos()
    test_get_convos_by_user_id()
    test_get_convo_messages()
    test_delete_convo()
    test_add_reply_to_convo()
    test_create_convo()
    upload_id = test_upload_file()
    test_check_upload_status(upload_id)