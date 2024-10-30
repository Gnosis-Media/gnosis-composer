import requests
import json

# Base URL of your composer service
BASE_URL = "http://localhost:5001"

def print_response(response):
    print(f"Status Code: {response.status_code}")
    print("Response:")
    print(json.dumps(response.json(), indent=2))
    print("\n" + "="*50 + "\n")

# Create a new conversation
def test_create_conversation():
    print("Testing POST /api/convos - Create new conversation")
    data = {
        "user_id": 1,
        "message": "Hello! This is the initial AI message."
    }
    response = requests.post(f"{BASE_URL}/api/convos", json=data)
    print_response(response)
    return response.json()['conversation']['id'] if response.status_code == 201 else None

# Get conversations (ordered)
def test_get_conversations():
    print("Testing GET /api/convos - Get conversations (ordered)")
    params = {
        "user_id": 1,
        "limit": 5,
        "random": "false"
    }
    response = requests.get(f"{BASE_URL}/api/convos", params=params)
    print_response(response)

# Get conversations (random)
def test_get_random_conversations():
    print("Testing GET /api/convos - Get random conversations")
    params = {
        "user_id": 1,
        "limit": 5,
        "random": "true"
    }
    response = requests.get(f"{BASE_URL}/api/convos", params=params)
    print_response(response)

# Add a reply to a conversation
def test_add_reply(conversation_id):
    print(f"Testing PUT /api/convos/{conversation_id}/reply - Add user reply")
    data = {
        "message": "This is a test reply from the user"
    }
    response = requests.put(f"{BASE_URL}/api/convos/{conversation_id}/reply", json=data)
    print_response(response)

# Delete a conversation
def test_delete_conversation(conversation_id):
    print(f"Testing DELETE /api/convos/{conversation_id} - Delete conversation")
    response = requests.delete(f"{BASE_URL}/api/convos/{conversation_id}")
    print_response(response)

if __name__ == "__main__":
    # First create a conversation and get its ID
    conversation_id = test_create_conversation()
    
    if conversation_id:
        # Test other endpoints using the created conversation
        test_get_conversations()
        test_get_random_conversations()
        test_add_reply(conversation_id)
        test_delete_conversation(conversation_id)
    else:
        print("Failed to create conversation, skipping other tests")