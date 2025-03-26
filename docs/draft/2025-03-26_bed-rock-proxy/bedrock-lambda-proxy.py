import json
import boto3
import os
import secrets
import time

# Initialize the DynamoDB and Bedrock Runtime clients
bedrock_runtime = boto3.client('bedrock-runtime', region_name=os.environ.get('AWS_REGION'))
dynamodb = boto3.resource('dynamodb')
token_table = dynamodb.Table('bedrock_tokens')

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
    authorization = request_headers.get('Authorization')
    
    start_time = time.time()
    customer_id = None
    token_count = 0
    
    try:
        # Log the request (excluding sensitive data)
        print(f"Received request with method: {event.get('httpMethod')}")
        print(f"Path: {event.get('path')}")
        
        if not authorization or not authorization.startswith('Bearer '):
            return {
                'statusCode': 401,
                'headers': headers,
                'body': json.dumps({'error': 'Authorization header missing or invalid format. Use Bearer token.'})
            }
        
        # Extract the token
        token = authorization.replace('Bearer ', '')
        
        # Look up customer from token
        try:
            token_response = token_table.get_item(Key={'token': token})
            token_item = token_response.get('Item')
            
            if not token_item or token_item.get('status') not in ['active', 'deprecated']:
                return {
                    'statusCode': 401,
                    'headers': headers,
                    'body': json.dumps({'error': 'Invalid or expired token'})
                }
            
            # Get customer_id from token record
            customer_id = token_item.get('customer_id')
            
            # Additional check for token status
            if token_item.get('status') == 'deprecated':
                print(f"Warning: Customer {customer_id} is using a deprecated token")
            
        except Exception as e:
            print(f"Error looking up token: {str(e)}")
            return {
                'statusCode': 500,
                'headers': headers,
                'body': json.dumps({'error': 'Error authenticating request'})
            }
        
        # Rate limiting check could be implemented here
        # by checking the customer's usage against their limits
        
        # Parse the request body
        request_body = json.loads(event.get('body', '{}'))
        
        # Extract modelId from the request
        model_id = request_body.pop('modelId', None)
        
        if not model_id:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'modelId is required'})
            }
        
        print(f"Calling Bedrock model: {model_id} for customer: {customer_id}")
        
        # Convert remaining payload to JSON string
        payload = json.dumps(request_body)
        
        # Invoke the Bedrock model
        response = bedrock_runtime.invoke_model(
            modelId=model_id,
            contentType='application/json',
            accept='application/json',
            body=payload
        )
        
        # Parse and return the response
        response_body = json.loads(response['body'].read().decode('utf-8'))
        
        # Estimate token count (this is a very rough estimate)
        # For accurate token counting, you'd need to use a proper tokenizer
        # or extract token counts from model response if available
        input_text = ""
        if 'messages' in request_body:
            for msg in request_body['messages']:
                if isinstance(msg.get('content'), list):
                    for content in msg['content']:
                        if content.get('type') == 'text':
                            input_text += content.get('text', '')
                elif isinstance(msg.get('content'), str):
                    input_text += msg.get('content', '')
        
        output_text = ""
        if 'content' in response_body:
            if isinstance(response_body['content'], list):
                for content in response_body['content']:
                    if content.get('type') == 'text':
                        output_text += content.get('text', '')
            elif isinstance(response_body['content'], str):
                output_text += response_body['content']
        
        # Very rough token estimate (approximately 4 chars per token)
        input_tokens = len(input_text) // 4
        output_tokens = len(output_text) // 4
        token_count = input_tokens + output_tokens
        
        # Log usage information for analytics
        print(json.dumps({
            "event_type": "bedrock_invoke",
            "customer_id": customer_id,
            "model_id": model_id,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": token_count,
            "duration_ms": int((time.time() - start_time) * 1000)
        }))
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(response_body)
        }
    
    except Exception as e:
        error_message = str(e)
        print(f"Error: {error_message}")
        
        # Log error for analytics
        if customer_id:
            print(json.dumps({
                "event_type": "bedrock_error",
                "customer_id": customer_id,
                "error": error_message,
                "duration_ms": int((time.time() - start_time) * 1000)
            }))
        
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({
                'error': error_message
            })
        }