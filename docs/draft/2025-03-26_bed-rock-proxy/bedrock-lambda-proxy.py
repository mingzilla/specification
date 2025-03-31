import json
import boto3
import os
import secrets

# Initialize the Bedrock Runtime client
bedrock_runtime = boto3.client('bedrock-runtime', region_name=os.environ.get('AWS_REGION'))

def lambda_handler(event, context):
    # Set up CORS headers
    headers = {
        "Access-Control-Allow-Origin": "*",  # Modify for production
        "Access-Control-Allow-Headers": "Content-Type,Authorization",
        "Access-Control-Allow-Methods": "OPTIONS,POST",
        "Content-Type": "application/json"
    }
    
    # Handle preflight OPTIONS request
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({'message': 'CORS preflight response'})
        }
    
    # Verify Bearer token authentication
    request_headers = event.get('headers', {})
    authorization = request_headers.get('authorization')

    print(event)
    
    # Get expected token from environment variable
    expected_token = os.environ.get('AUTH_TOKEN')
    
    # Check if authentication is required (token exists in environment)
    if expected_token:
        if not authorization or not authorization.startswith('Bearer '):
            print(f'authoirzation: {authorization}')
            return {
                'statusCode': 401,
                'headers': headers,
                'body': json.dumps({'error': 'Authorization header missing or invalid format. Use Bearer token.'})
            }
        
        # Extract the token
        token = authorization.replace('Bearer ', '')
        
        if token != expected_token:
            return {
                'statusCode': 401,
                'headers': headers,
                'body': json.dumps({'error': 'Invalid token'})
            }
    
    try:
        # Parse the request body
        request_body = json.loads(event.get('body', '{}'))

        # Extract modelId from the request
        model_id = request_body.pop('model', None)
        stream = request_body.pop('stream', None)

        if not model_id:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'modelId is required'})
            }

        request_body_json_string = json.dumps(request_body)
        

        # Invoke the Bedrock model
        response = bedrock_runtime.invoke_model(
            modelId=model_id,
            contentType='application/json',
            accept='application/json',
            body=request_body_json_string
        )
        
        # Parse and return the response
        response_body = json.loads(response['body'].read().decode('utf-8'))
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(response_body)
        }
    
    except Exception as e:
        print(f"Error: {str(e)}")
        
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({
                'error': str(e)
            })
        }