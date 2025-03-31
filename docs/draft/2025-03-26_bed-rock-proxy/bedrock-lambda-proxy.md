# AWS Bedrock Lambda Proxy

This document contains the Python code for a Lambda function that acts as a proxy to AWS Bedrock models, along with deployment instructions.

## Lambda Function Code

- [bedrock-lambda-proxy.py](bedrock-lambda-proxy.py)
- [bedrock-streaming-docs.md](bedrock-streaming-docs.md) - Detailed documentation on streaming implementation
  - [bedrock-lambda-proxy-streaming.py](bedrock-lambda-proxy-streaming.py)

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

### 2. Configure IAM Permissions and Authentication

#### A. IAM Permissions

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
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream"
            ],
            "Resource": "*"
        }
    ]
}
```

6. Click "Review policy"
7. Name the policy (e.g., `bedrock-invoke-policy`)
8. Click "Create policy"

#### B. Set Up Bearer Token Authentication

The Lambda function is configured to use Bearer token authentication if an `AUTH_TOKEN` environment variable is set:

1. Generate a Secure Token:
   - Option 1: Use a secure token generator website like [passwordsgenerator.net](https://passwordsgenerator.net/)
   - Option 2: Generate a token via command line:
     ```bash
     # On Linux/Mac
     openssl rand -base64 32
     
     # On Windows PowerShell
     [Convert]::ToBase64String([Security.Cryptography.RandomNumberGenerator]::GetBytes(24))
     ```

2. Add the Token to Lambda Environment Variables:
   - In the Lambda console, go to the "Configuration" tab
   - Click on "Environment variables"
   - Click "Edit"
   - Add a key `AUTH_TOKEN` with your generated token as the value
   - Click "Save"

3. Your clients will now need to include this token in the Authorization header as a Bearer token

### 3. Configure Function URL or API Gateway

#### Option A: Function URL (Recommended for Streaming)

1. In the Lambda console, go to the "Configuration" tab
2. Select "Function URL" from the left menu
3. Click "Create function URL"
4. Auth type: Select "NONE" for testing, or "AWS_IAM" for production
5. **For streaming support**: Enable "Response streaming" option
6. Configure CORS as needed
7. Click "Save"
8. Note the Function URL that is generated

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

## Streaming Support

The Lambda proxy supports both streaming and non-streaming requests. To use streaming:

1. Add `"stream": true` to your request JSON
2. Handle the response format appropriate to your deployment method:
   - Lambda Function URL: SSE format with `data: {"content": "chunk text"}\n\n` chunks and `data: [DONE]\n\n` as the end signal
   - API Gateway: Array of chunks with objects like `{"content": "chunk text"}` and a final `{"done": true}` object

For complete details on streaming implementation, see [bedrock-streaming-docs.md](bedrock-streaming-docs.md).

## Testing Your Lambda Proxy

### Example API Call with Bearer Token Authentication

#### JavaScript (using fetch)

```javascript
// Your AUTH_TOKEN from Lambda environment variables
const authToken = 'your-generated-token-here';

fetch('https://your-lambda-function-url-or-api-gateway-url', {
  method: 'POST',
  headers: { 
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${authToken}`
  },
  body: JSON.stringify({
    // Required: specify which model to use
    modelId: 'eu.anthropic.claude-3-5-sonnet-20240620-v1:0',
    
    // Optional: set to true for streaming response
    stream: false,
    
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

#### Python (using requests)

```python
import requests
import json

url = "https://your-lambda-function-url-or-api-gateway-url"
auth_token = "your-generated-token-here"  # Your AUTH_TOKEN from Lambda environment variables

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {auth_token}"
}

payload = {
    "modelId": "eu.anthropic.claude-3-5-sonnet-20240620-v1:0",
    "stream": false,  # Set to true for streaming
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

response = requests.post(url, headers=headers, json=payload)
print(response.json())
```

## Security Considerations

### Token Management Best Practices

1. **Secure Storage**: Never hardcode tokens in your application. Use environment variables, secure vaults, or configuration management solutions.

2. **Token Rotation**: Periodically update your tokens to reduce the risk of unauthorized access.

3. **Least Privilege**: Consider creating different tokens with different access levels if you have multiple applications or use cases.

4. **Monitoring**: Implement logging and monitoring to detect unusual patterns that might indicate token compromise.

5. **Transport Security**: Always use HTTPS to protect tokens in transit.

### Additional Security Options

If you need more robust security, consider:

1. **JWT Tokens**: Implement JWT (JSON Web Token) validation for more sophisticated authentication with expiration and claims.

2. **IP Restrictions**: Add IP-based restrictions in your Lambda function to only accept requests from trusted sources.

3. **AWS WAF**: Deploy AWS WAF (Web Application Firewall) in front of your API Gateway for additional protection.

## Notes

- The Lambda function is generic and works with any AWS Bedrock model - just specify the correct modelId
- For high-traffic applications, consider increasing the Lambda's memory and timeout settings
- For production, make sure to restrict the CORS settings
- You can add additional error handling and logging as needed
- Authentication is optional - the Lambda will work without a token if you don't set the AUTH_TOKEN environment variable

For invoking different models, you'll need to adjust the payload format according to the model's requirements. The Claude model format is shown in the examples above.