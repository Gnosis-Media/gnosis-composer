import boto3
import json
from botocore.exceptions import ClientError

def get_secrets(secret_name, region_name="us-east-1"):
    """
    Retrieve secrets from AWS Secrets Manager
    
    Args:
        secret_name (str): Name of the secret in AWS Secrets Manager
        region_name (str): AWS region where the secret is stored
        
    Returns:
        dict: Dictionary containing the secret values
    """
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        raise e
    else:
        if 'SecretString' in get_secret_value_response:
            secret = json.loads(get_secret_value_response['SecretString'])
            return secret

# Usage example for gnosis-composer
def get_service_secrets(service_name):
    """
    Get secrets for a specific service
    
    Args:
        service_name (str): Name of the service (e.g., 'gnosis-composer')
        
    Returns:
        dict: Dictionary containing service-specific secrets
    """
    secrets = get_secrets('gnosis-secrets')  # Replace with your actual secret name
    # print(secrets)
    return secrets.get(service_name, {})

def main():
    secrets = get_service_secrets('gnosis-composer')
    print(secrets)
    print(secrets.get('UPLOAD_SERVICE_URL'))

if __name__ == '__main__':
    main()