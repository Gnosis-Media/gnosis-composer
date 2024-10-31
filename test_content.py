import unittest
import requests
import time
import os

class TestContentProcessor(unittest.TestCase):
    def setUp(self):
        self.composer_url = 'http://54.157.239.255:5001'
        self.user_id = 2122  # Test user ID
        self.test_file_path = 'test_files/test.txt'
        
        # Create test file if it doesn't exist
        os.makedirs('test_files', exist_ok=True)
        if not os.path.exists(self.test_file_path):
            with open(self.test_file_path, 'w') as f:
                for _ in range(100):
                    f.write("Lorem ipsum dolor sit amet, consectetur adipiscing elit.\n")

    def test_upload_flow(self):
        """Test the complete upload flow including status checks"""
        
        # 1. Test file upload
        with open(self.test_file_path, 'rb') as f:
            files = {'file': ('test.txt', f, 'text/plain')}
            data = {'user_id': self.user_id}
            
            response = requests.post(
                f'{self.composer_url}/api/upload',
                files=files,
                data=data
            )
            
            self.assertEqual(response.status_code, 202)
            self.assertIn('upload_id', response.json())
            upload_id = response.json()['upload_id']

        # 2. Test status checking
        max_attempts = 10
        attempts = 0
        status = None
        
        while attempts < max_attempts:
            status_response = requests.get(
                f'{self.composer_url}/api/upload_status/{upload_id}'
            )
            self.assertEqual(status_response.status_code, 200)
            
            status = status_response.json()['status']
            if status in ['COMPLETED', 'FAILED']:
                break
                
            attempts += 1
            time.sleep(20)  # Wait before next check
            
        self.assertEqual(status, 'COMPLETED')
        
        # 3. Test file listing
        files_response = requests.get(
            f'{self.composer_url}/api/files',
            params={'user_id': self.user_id}
        )
        
        self.assertEqual(files_response.status_code, 200)
        files_data = files_response.json()
        
        self.assertIn('files', files_data)
        self.assertIn('count', files_data)
        self.assertGreater(files_data['count'], 0)
        
        # Verify the uploaded file is in the list
        found_file = False
        for file in files_data['files']:
            if file['file_name'] == 'test.txt':
                found_file = True
                self.assertIn('id', file)
                self.assertIn('chunk_count', file)
                self.assertGreater(file['chunk_count'], 0)
                break
                
        self.assertTrue(found_file, "Uploaded file not found in files list")

    def test_invalid_upload(self):
        """Test upload validation"""
        
        # Test missing file
        response = requests.post(
            f'{self.composer_url}/api/upload',
            data={'user_id': self.user_id}
        )
        self.assertEqual(response.status_code, 400)
        
        # Test missing user_id
        with open(self.test_file_path, 'rb') as f:
            response = requests.post(
                f'{self.composer_url}/api/upload',
                files={'file': ('test.txt', f, 'text/plain')}
            )
        self.assertEqual(response.status_code, 400)
        
        # Test invalid file type
        invalid_file_path = 'test_files/test.invalid'
        with open(invalid_file_path, 'w') as f:
            f.write("Invalid file")
            
        with open(invalid_file_path, 'rb') as f:
            response = requests.post(
                f'{self.composer_url}/api/upload',
                files={'file': ('test.invalid', f, 'text/plain')},
                data={'user_id': self.user_id}
            )
        self.assertEqual(response.status_code, 400)
        
        os.remove(invalid_file_path)

    def test_file_listing(self):
        """Test file listing endpoint"""
        
        # Test without user_id
        response = requests.get(f'{self.composer_url}/api/files')
        self.assertEqual(response.status_code, 400)
        
        # Test with invalid user_id
        response = requests.get(
            f'{self.composer_url}/api/files',
            params={'user_id': 'invalid'}
        )
        self.assertEqual(response.status_code, 400)
        
        # Test with valid user_id
        response = requests.get(
            f'{self.composer_url}/api/files',
            params={'user_id': self.user_id}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('files', response.json())
        self.assertIn('count', response.json())

    def test_invalid_status_check(self):
        """Test status check with invalid upload_id"""
        
        response = requests.get(
            f'{self.composer_url}/api/upload_status/invalid-id'
        )
        self.assertEqual(response.status_code, 404)

    def tearDown(self):
        # Cleanup test files
        if os.path.exists(self.test_file_path):
            os.remove(self.test_file_path)
        if os.path.exists('test_files'):
            os.rmdir('test_files')

if __name__ == '__main__':
    unittest.main()