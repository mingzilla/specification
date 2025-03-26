import json
import boto3
import os
import time
import re

# Initialize clients
bedrock_runtime = boto3.client('bedrock-runtime', region_name=os.environ.get('AWS_REGION'))
dynamodb = boto3.resource('dynamodb')
token_table = dynamodb.Table('bedrock_tokens')

# Token estimation function (same as before)
def estimate_tokens(text, model_id):
    if not text:
        return 0
        
    words = re.findall(r'\w+', text)
    punctuation = re.findall(r'[^\w\s]', text)
    estimated_tokens = len(words) + len(punctuation)
    
    if 'claude' in model_id.lower():
        return int(estimated_tokens * 0.9)
    elif 'llama' in model_id.lower():
        return int(estimated_tokens * 1.1)
    else:
        return estimated_tokens

def lambda_handler(event, context):
    # CORS headers
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
    model_id = None
    token_count = 0
    request_id = context.aws_request_id
    
    try:
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
            
            customer_id = token_item.get('customer_id')
            
            if token_item.get('status') == 'deprecated':
                print(f"Warning: Customer {customer_id} is using a deprecated token")
            
        except Exception as e:
            print(f"Error looking up token: {str(e)}")
            return {
                'statusCode': 500,
                'headers': headers,
                'body': json.dumps({'error': 'Error authenticating request'})
            }
        
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
        
        # Check if streaming is requested
        use_streaming = request_body.pop('stream', False)
        
        # Extract input text for token estimation
        input_text = ""
        if 'messages' in request_body:
            for msg in request_body['messages']:
                if isinstance(msg.get('content'), list):
                    for content in msg['content']:
                        if content.get('type') == 'text':
                            input_text += content.get('text', '')
                elif isinstance(msg.get('content'), str):
                    input_text += msg.get('content', '')
        
        input_tokens = estimate_tokens(input_text, model_id)
        
        # Convert remaining payload to JSON string
        payload = json.dumps(request_body)
        
        print(f"Calling Bedrock model: {model_id} for customer: {customer_id} (Streaming: {use_streaming})")
        
        # NON-STREAMING RESPONSE
        if not use_streaming:
            # Invoke the Bedrock model
            response = bedrock_runtime.invoke_model(
                modelId=model_id,
                contentType='application/json',
                accept='application/json',
                body=payload
            )
            
            # Parse and return the response
            response_body = json.loads(response['body'].read().decode('utf-8'))
            
            # Extract output text for token estimation
            output_text = ""
            if 'content' in response_body:
                if isinstance(response_body['content'], list):
                    for content in response_body['content']:
                        if content.get('type') == 'text':
                            output_text += content.get('text', '')
                elif isinstance(response_body['content'], str):
                    output_text += response_body['content']
            
            output_tokens = estimate_tokens(output_text, model_id)
            token_count = input_tokens + output_tokens
            
            # Calculate duration in milliseconds
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Log usage information
            log_entry = {
                "event_type": "bedrock_invoke",
                "customer_id": customer_id,
                "request_id": request_id,
                "model_id": model_id,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "token_count": token_count,
                "duration_ms": duration_ms,
                "timestamp": int(time.time())
            }
            
            print(json.dumps(log_entry))
            
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps(response_body)
            }
        
        # STREAMING RESPONSE
        else:
            # For Lambda function URL - use direct streaming response
            if event.get('requestContext', {}).get('apiGateway') is None:
                # Update the headers for SSE
                sse_headers = headers.copy()
                sse_headers.update({
                    'Content-Type': 'text/event-stream',
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive',
                    'X-Accel-Buffering': 'no'  # For Nginx
                })
                
                # Stream response using Lambda response streaming
                def generate_streaming_response():
                    yield json.dumps({
                        'statusCode': 200, 
                        'headers': sse_headers
                    }) + '\n'
                    
                    output_text = ""
                    response_stream = bedrock_runtime.invoke_model_with_response_stream(
                        modelId=model_id,
                        contentType='application/json',
                        accept='application/json',
                        body=payload
                    )
                    
                    # Process each chunk in the stream
                    for event in response_stream['body']:
                        chunk = json.loads(event['chunk']['bytes'].decode())
                        
                        # Extract text content (model-specific)
                        text_content = ""
                        if 'completion' in chunk:  # Claude 2
                            text_content = chunk['completion']
                        elif 'content' in chunk:  # Claude 3
                            if isinstance(chunk['content'], list):
                                for item in chunk['content']:
                                    if item.get('type') == 'text':
                                        text_content += item.get('text', '')
                            else:
                                text_content = chunk.get('content', '')
                        
                        # Build SSE response
                        if text_content:
                            output_text += text_content
                            yield f"data: {json.dumps({'content': text_content})}\n\n"
                    
                    # Send end signal
                    yield "data: [END]\n\n"
                    
                    # Log usage metrics after completion
                    output_tokens = estimate_tokens(output_text, model_id)
                    token_count = input_tokens + output_tokens
                    duration_ms = int((time.time() - start_time) * 1000)
                    
                    log_entry = {
                        "event_type": "bedrock_stream",
                        "customer_id": customer_id,
                        "request_id": request_id,
                        "model_id": model_id,
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "token_count": token_count,
                        "duration_ms": duration_ms,
                        "timestamp": int(time.time())
                    }
                    
                    print(json.dumps(log_entry))
                
                return generate_streaming_response()
            
            # For API Gateway - collect chunks and return as complete response
            else:
                collected_chunks = []
                output_text = ""
                
                response_stream = bedrock_runtime.invoke_model_with_response_stream(
                    modelId=model_id,
                    contentType='application/json',
                    accept='application/json',
                    body=payload
                )
                
                # Process each chunk in the stream
                for event in response_stream['body']:
                    chunk = json.loads(event['chunk']['bytes'].decode())
                    
                    # Extract text content (model-specific)
                    text_content = ""
                    if 'completion' in chunk:  # Claude 2
                        text_content = chunk['completion']
                    elif 'content' in chunk:  # Claude 3
                        if isinstance(chunk['content'], list):
                            for item in chunk['content']:
                                if item.get('type') == 'text':
                                    text_content += item.get('text', '')
                        else:
                            text_content = chunk.get('content', '')
                    
                    # Add to collected chunks
                    if text_content:
                        output_text += text_content
                        collected_chunks.append({'content': text_content})
                
                # Add final done: true indicator
                collected_chunks.append({'done': True})
                
                # Log usage metrics
                output_tokens = estimate_tokens(output_text, model_id)
                token_count = input_tokens + output_tokens
                duration_ms = int((time.time() - start_time) * 1000)
                
                log_entry = {
                    "event_type": "bedrock_stream",
                    "customer_id": customer_id,
                    "request_id": request_id,
                    "model_id": model_id,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "token_count": token_count,
                    "duration_ms": duration_ms,
                    "timestamp": int(time.time())
                }
                
                print(json.dumps(log_entry))
                
                return {
                    'statusCode': 200,
                    'headers': headers,
                    'body': json.dumps(collected_chunks)
                }
    
    except Exception as e:
        error_message = str(e)
        print(f"Error: {error_message}")
        
        # Log error for analytics
        if customer_id:
            error_log = {
                "event_type": "bedrock_error",
                "customer_id": customer_id,
                "model_id": model_id,
                "request_id": request_id,
                "error": error_message,
                "duration_ms": int((time.time() - start_time) * 1000),
                "timestamp": int(time.time())
            }
            print(json.dumps(error_log))
        
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({
                'error': error_message
            })
        }