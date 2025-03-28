// JavaScript client integration for both streaming and non-streaming requests
// This code works with the AWS Bedrock Lambda Proxy

// 1. Non-streaming request example (returns complete response at once)
async function callBedrockNonStreaming(prompt) {
  const apiEndpoint = 'https://your-api-gateway-url/prod/bedrock';
  const authToken = 'your-customer-token-here';
  
  const response = await fetch(apiEndpoint, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${authToken}`
    },
    body: JSON.stringify({
      // Required: specify which model to use
      modelId: 'anthropic.claude-3-sonnet-20240229-v1:0',
      
      // Set stream to false for non-streaming (this is optional as false is default)
      stream: false,
      
      // Claude-specific parameters
      anthropic_version: 'bedrock-2023-05-31',
      max_tokens: 1000,
      messages: [
        {
          role: 'user',
          content: [
            {
              type: 'text',
              text: prompt
            }
          ]
        }
      ]
    })
  });
  
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }
  
  return await response.json();
}

// 2. Streaming request with SSE from Lambda Function URL
// Returns SSE format with "data: [DONE]" at completion
async function callBedrockSSEStreaming(prompt) {
  const apiEndpoint = 'https://your-lambda-function-url/bedrock';
  const authToken = 'your-customer-token-here';
  
  const response = await fetch(apiEndpoint, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${authToken}`
    },
    body: JSON.stringify({
      modelId: 'anthropic.claude-3-sonnet-20240229-v1:0',
      stream: true, // Enable streaming
      anthropic_version: 'bedrock-2023-05-31',
      max_tokens: 1000,
      messages: [
        {
          role: 'user',
          content: [
            {
              type: 'text',
              text: prompt
            }
          ]
        }
      ]
    })
  });
  
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }
  
  return response; // Return the streaming response
  // Your app should handle SSE format with "data: [DONE]" at completion
}

// 3. API Gateway streaming (chunked response)
// Returns an array of chunks with final object having {done: true}
async function callBedrockChunkedStreaming(prompt) {
  const apiEndpoint = 'https://your-api-gateway-url/prod/bedrock';
  const authToken = 'your-customer-token-here';
  
  const response = await fetch(apiEndpoint, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${authToken}`
    },
    body: JSON.stringify({
      modelId: 'anthropic.claude-3-sonnet-20240229-v1:0',
      stream: true, // Enable streaming
      anthropic_version: 'bedrock-2023-05-31',
      max_tokens: 1000,
      messages: [
        {
          role: 'user',
          content: [
            {
              type: 'text',
              text: prompt
            }
          ]
        }
      ]
    })
  });
  
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }
  
  return await response.json(); 
  // This returns an array with the final object having {done: true}
}