# AWS Bedrock Lambda Proxy

This document contains the Python code for a Lambda function that acts as a proxy to AWS Bedrock models, along with deployment instructions.

## Lambda Function Code

```python
import json
import boto3
import os

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
    
    try:
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
        
        print(f"Calling Bedrock model: {model_id}")
        
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
```

## Deployment Instructions

### 1. Create the Lambda Function

1. Open the AWS Lambda console: https://console.aws.amazon.com/lambda/
2. Click "Create function"
3. Select "Author from scratch"
4. Enter a name for your function (e.g., `bedrock-proxy`)
5. For Runtime, select "Python 3.9" or newer
6. Under Permissions, create a new role with basic Lambda permissions, or select an existing role
7. Click "Create function"
8. In the "Code" tab, paste the code above into the inline editor
9. Click "Deploy" to save your changes

### 2. Configure IAM Permissions

Your Lambda function needs permission to invoke Bedrock models. Add the following policy to your Lambda's execution role:

1. In the Lambda console, go to the "Configuration" tab
2. Click on "Permissions"
3. Click on the role name under "Execution role"
4. In the IAM console, click "Add permissions" and then "Create inline policy"
5. In the JSON tab, paste the following policy:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel"
            ],
            "Resource": "*"
        }
    ]
}
```

6. Click "Review policy"
7. Name the policy (e.g., `bedrock-invoke-policy`)
8. Click "Create policy"

### 3. Configure Function URL or API Gateway

#### Option A: Function URL (Simplest)

1. In the Lambda console, go to the "Configuration" tab
2. Select "Function URL" from the left menu
3. Click "Create function URL"
4. Auth type: Select "NONE" for testing, or "AWS_IAM" for production
5. Configure CORS as needed
6. Click "Save"
7. Note the Function URL that is generated

#### Option B: API Gateway

1. Open the API Gateway console: https://console.aws.amazon.com/apigateway/
2. Click "Create API"
3. Choose "REST API" and click "Build"
4. Name your API and click "Create API"
5. Click "Actions" > "Create Resource"
6. Resource name: "bedrock" (or any name you prefer)
7. Click "Create Resource"
8. Click "Actions" > "Create Method"
9. Select "POST" and click the checkmark
10. Integration type: "Lambda Function"
11. Lambda Function: Enter your function name
12. Click "Save"
13. Enable CORS: Click "Actions" > "Enable CORS"
14. Click "Enable CORS and replace existing CORS headers"
15. Deploy API: Click "Actions" > "Deploy API"
16. Create a new stage (e.g., "prod") and click "Deploy"
17. Note the Invoke URL that is displayed

## Testing Your Lambda Proxy

### Example API Call (using fetch in JavaScript)

```javascript
fetch('https://your-lambda-function-url-or-api-gateway-url', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    // Required: specify which model to use
    modelId: 'eu.anthropic.claude-3-5-sonnet-20240620-v1:0',
    
    // The rest is the model-specific payload
    anthropic_version: 'bedrock-2023-05-31',
    max_tokens: 1000,
    messages: [
      {
        role: 'user',
        content: [
          {
            type: 'text',
            text: 'What is the capital of France?'
          }
        ]
      }
    ]
  })
})
.then(response => response.json())
.then(data => console.log(data))
.catch(error => console.error('Error:', error));
```

### Example API Call (using Python requests)

```python
import requests
import json

url = "https://your-lambda-function-url-or-api-gateway-url"

payload = {
    "modelId": "eu.anthropic.claude-3-5-sonnet-20240620-v1:0",
    "anthropic_version": "bedrock-2023-05-31",
    "max_tokens": 1000,
    "messages": [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "What is the capital of France?"
                }
            ]
        }
    ]
}

response = requests.post(url, json=payload)
print(response.json())
```

## Notes

- The Lambda function is generic and works with any AWS Bedrock model - just specify the correct modelId
- For high-traffic applications, consider increasing the Lambda's memory and timeout settings
- For production, make sure to restrict the CORS settings and consider adding authentication
- You can add additional error handling and logging as needed

For invoking different models, you'll need to adjust the payload format according to the model's requirements. The Claude model format is shown in the examples above.
