# AWS Bedrock Streaming Implementation Guide

This document explains the streaming capabilities in the AWS Bedrock Lambda Proxy (`bedrock-lambda-proxy.py`), including implementation details and deployment notes.

## Overview

The Lambda proxy supports both streaming and non-streaming requests to AWS Bedrock models. The implementation provides two streaming response formats:

1. **Server-Sent Events (SSE)** format with Lambda Function URLs
2. **Chunked Array** format with API Gateway

## How to Enable Streaming

To use streaming, simply add `"stream": true` to your request JSON:

```json
{
  "modelId": "anthropic.claude-3-sonnet-20240229-v1:0",
  "stream": true,
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": "Your prompt here"
        }
      ]
    }
  ],
  "anthropic_version": "bedrock-2023-05-31",
  "max_tokens": 1000
}
```

## Response Formats

### Non-Streaming Responses

For non-streaming requests (`"stream": false` or omitted), the Lambda returns the complete model response in a single JSON object, exactly as provided by AWS Bedrock.

### Streaming Responses

Depending on deployment method, streaming responses come in two formats:

#### 1. Lambda Function URL Streaming (SSE Format)

When using Lambda Function URLs with streaming enabled, the response:
- Has Content-Type: `text/event-stream`
- Delivers chunks in Server-Sent Events format: `data: {"content": "chunk text"}\n\n`
- Signals completion with: `data: [DONE]\n\n`

This format is ideal for real-time display of responses as they're generated.

#### 2. API Gateway Streaming (Chunked Array Format)

When using API Gateway with streaming enabled, the response:
- Returns a JSON array containing all content chunks
- Each chunk is an object: `{"content": "chunk text"}`
- The final object signals completion with: `{"done": true}`

This format is used because API Gateway doesn't natively support streaming responses.

## Deployment Requirements

### IAM Permissions

Add this permission to your Lambda's IAM role:

```json
{
  "Effect": "Allow",
  "Action": [
    "bedrock:InvokeModelWithResponseStream"
  ],
  "Resource": "*"
}
```

### Lambda Function URL Setup (Recommended for True Streaming)

1. In the Lambda console, go to the "Configuration" tab
2. Select "Function URL" from the left menu
3. Click "Create function URL"
4. Set Auth type as needed
5. **Important**: Enable "Response streaming" option
6. Configure CORS settings as needed
7. Click "Save"

## Usage Tracking

The Lambda proxy maintains compatibility with the existing usage tracking system:
- Logs streaming and non-streaming usage in the same format
- Compatible with the CloudWatch Logs export system defined in `reporting-setup.yml`
- Estimates token usage for both streaming and non-streaming requests

## Client Usage Examples

See the [client-integration.js](client-integration.js) file for examples of:
- Non-streaming requests
- SSE streaming with Lambda Function URLs
- Chunked streaming with API Gateway

## Recommended Deployment Method

For the best streaming experience:
- Use Lambda Function URL deployment for applications requiring real-time streaming
- API Gateway deployment works for all cases but buffers streaming responses

## Technical Implementation

The Lambda proxy:
1. Authenticates the request using the Bearer token
2. Checks customer rate limits from the customer database
3. Based on the `stream` parameter and deployment type:
   - For non-streaming: Uses `invoke_model`
   - For streaming with Function URL: Uses `invoke_model_with_response_stream` and returns SSE
   - For streaming with API Gateway: Uses `invoke_model_with_response_stream` but collects chunks
4. Logs detailed usage information for billing and analytics