import unittest
import requests
import logging
import os
import random
import string

logging.basicConfig(level=logging.INFO)

class TestAuthAPI(unittest.TestCase):
    def setUp(self):
        """Setup test case"""
        self.composer_url = 'http://54.157.239.255:5001'
        # Generate random username and email for each test
        random_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        self.test_user = {
            'username': f'testuser_{random_string}',
            'email': f'test_{random_string}@example.com',
            'password': 'TestPassword123!'
        }

    def test_register_flow(self):
        """Test the complete registration flow"""
        
        # Test successful registration
        response = requests.post(
            f'{self.composer_url}/api/register',
            json=self.test_user
        )
        self.assertEqual(response.status_code, 201)
        self.assertIn('message', response.json())
        self.assertIn('user', response.json())
        self.assertEqual(response.json()['user']['username'], self.test_user['username'])
        self.assertEqual(response.json()['user']['email'], self.test_user['email'])

        # Test duplicate registration
        response = requests.post(
            f'{self.composer_url}/api/register',
            json=self.test_user
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())

    def test_register_validation(self):
        """Test registration input validation"""
        
        # Test missing username
        invalid_user = {
            'email': 'test@example.com',
            'password': 'password123'
        }
        response = requests.post(
            f'{self.composer_url}/api/register',
            json=invalid_user
        )
        self.assertEqual(response.status_code, 400)
        
        # Test missing email
        invalid_user = {
            'username': 'testuser',
            'password': 'password123'
        }
        response = requests.post(
            f'{self.composer_url}/api/register',
            json=invalid_user
        )
        self.assertEqual(response.status_code, 400)
        
        # Test missing password
        invalid_user = {
            'username': 'testuser',
            'email': 'test@example.com'
        }
        response = requests.post(
            f'{self.composer_url}/api/register',
            json=invalid_user
        )
        self.assertEqual(response.status_code, 400)

    def test_login_flow(self):
        """Test the complete login flow"""
        
        # First register a user
        requests.post(
            f'{self.composer_url}/api/register',
            json=self.test_user
        )
        
        # Test successful login
        login_data = {
            'username': self.test_user['username'],
            'password': self.test_user['password']
        }
        response = requests.post(
            f'{self.composer_url}/api/login',
            json=login_data
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('message', response.json())
        self.assertIn('user', response.json())
        self.assertEqual(response.json()['user']['username'], self.test_user['username'])

        # Test invalid password
        login_data['password'] = 'wrongpassword'
        response = requests.post(
            f'{self.composer_url}/api/login',
            json=login_data
        )
        self.assertEqual(response.status_code, 401)
        self.assertIn('error', response.json())

    def test_login_validation(self):
        """Test login input validation"""
        
        # Test missing username
        invalid_login = {
            'password': 'password123'
        }
        response = requests.post(
            f'{self.composer_url}/api/login',
            json=invalid_login
        )
        self.assertEqual(response.status_code, 400)
        
        # Test missing password
        invalid_login = {
            'username': 'testuser'
        }
        response = requests.post(
            f'{self.composer_url}/api/login',
            json=invalid_login
        )
        self.assertEqual(response.status_code, 400)

if __name__ == '__main__':
    unittest.main(verbosity=2)