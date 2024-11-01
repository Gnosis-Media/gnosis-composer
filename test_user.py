import unittest
import requests
import logging
import random
import string

logging.basicConfig(level=logging.INFO)

class TestAuthAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Setup test case once for the entire class"""
        cls.composer_url = 'http://localhost:5001'
        random_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        cls.test_user = {
            'username': f'testuser_{random_string}',
            'email': f'test_{random_string}@example.com',
            'password': 'TestPassword123!'
        }
        # Register the user once for all tests
        response = requests.post(
            f'{cls.composer_url}/api/register',
            json=cls.test_user
        )
        assert response.status_code == 201, "User registration failed during setup"

    def test_1_register_flow(self):
        """Test the complete registration flow"""
        # Since the user is already registered in setUpClass, this test can be skipped or modified
        pass

    def test_2_login_and_token(self):
        """Test login and token generation"""
        
        login_data = {
            'username': self.test_user['username'],
            'password': self.test_user['password']
        }
        response = requests.post(
            f'{self.composer_url}/api/login',
            json=login_data
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('token', response.json())
        self.auth_token = response.json()['token']

    def test_3_protected_endpoints(self):
        """Test accessing protected endpoints with and without token"""
        
        # First login to get token
        login_data = {
            'username': self.test_user['username'],
            'password': self.test_user['password']
        }
        response = requests.post(
            f'{self.composer_url}/api/login',
            json=login_data
        )
        token = response.json()['token']

        # Test accessing protected endpoint without token
        response = requests.get(f'{self.composer_url}/api/convos')
        self.assertEqual(response.status_code, 401)
        self.assertIn('error', response.json())

        # Test accessing protected endpoint with invalid token
        headers = {'Authorization': 'Bearer invalid_token'}
        response = requests.get(
            f'{self.composer_url}/api/convos',
            headers=headers,
            params={'user_id': 1, 'limit': 10, 'random': 'false'}
        )
        self.assertEqual(response.status_code, 401)

        # Test accessing protected endpoint with valid token
        headers = {'Authorization': f'Bearer {token}'}
        response = requests.get(
            f'{self.composer_url}/api/convos',
            headers=headers,
            params={'user_id': 1, 'limit': 10, 'random': 'false'}
        )
        self.assertEqual(response.status_code, 200)

    def test_4_token_validation(self):
        """Test token validation"""
        
        # First login to get token
        login_data = {
            'username': self.test_user['username'],
            'password': self.test_user['password']
        }
        response = requests.post(
            f'{self.composer_url}/api/login',
            json=login_data
        )
        token = response.json()['token']

        # Test various token scenarios
        test_cases = [
            ('', 401),  # Empty token
            ('invalid_token', 401),  # Invalid token
            (token, 200),  # Valid token
        ]

        for test_token, expected_status in test_cases:
            headers = {'Authorization': f'Bearer {test_token}'} if test_token else {}
            response = requests.get(
                f'{self.composer_url}/api/convos',
                headers=headers,
                params={'user_id': 1, 'limit': 10, 'random': 'false'}
            )
            self.assertEqual(
                response.status_code, 
                expected_status, 
                f"Failed for token: {test_token}"
            )

    def test_5_exempt_routes(self):
        """Test that exempt routes don't require authentication"""
        
        # Test register endpoint
        random_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        new_user = {
            'username': f'testuser_{random_string}',
            'email': f'test_{random_string}@example.com',
            'password': 'TestPassword123!'
        }
        response = requests.post(
            f'{self.composer_url}/api/register',
            json=new_user
        )
        self.assertEqual(response.status_code, 201)

        # Test login endpoint
        login_data = {
            'username': new_user['username'],
            'password': new_user['password']
        }
        response = requests.post(
            f'{self.composer_url}/api/login',
            json=login_data
        )
        self.assertEqual(response.status_code, 200)

if __name__ == '__main__':
    unittest.main(verbosity=2)