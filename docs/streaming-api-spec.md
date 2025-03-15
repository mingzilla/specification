# Chat Completions API Specification

This document outlines the specifications for a chat completions API that supports both regular invocations and streaming responses (JSON and SSE).

## Requirements and Key Criteria

- Follows Ollama's response format structure
- Supports both traditional request/response and streaming modes
- Separate endpoint for SSE streaming
- Clean, consistent, and easy-to-implement interfaces
- Minimalist JSON structure for efficient parsing
- Proper termination signals for streams

## Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/chat/completions` | POST | For both regular invocations and JSON streaming |
| `/chat/sse` | POST | For SSE streaming (Server-Sent Events) |

## Request Format

### Headers

~~~
Content-Type: application/json
Authorization: Bearer <your_api_key>
~~~

### Request Body for `/chat/completions`

~~~json
{
  "model": "model-name",          // Required: Model identifier
  "messages": [                   // Required: Conversation history
    {
      "role": "system",           // "system", "user", or "assistant" 
      "content": "You are a helpful assistant."
    },
    {
      "role": "user",
      "content": "Hello, how are you?"
    }
  ],
  "stream": false,                // Optional: Enable streaming (default: false)
  "temperature": 0.7,             // Optional: Controls randomness
}
~~~

### Request Body for `/chat/sse`

~~~json
{
  // Same parameters as /chat/completions 
  // (except "stream" which is always true for SSE)
}
~~~

## Response Formats

### 1. Regular (Non-Streaming) Response

~~~json
{
  "id": "cmpl-123abc",
  "model": "model-name",
  "created": 1678048938,
  "message": {
    "role": "assistant",
    "content": "I'm doing well, thank you for asking! How can I help you today?"
  },
  "done": true
}
~~~

### 2. JSON Streaming Response Format

#### JSON Streaming Response Format (Formatted for readability)

Each chunk is a JSON object with the following structure. The examples below are formatted for clarity only:

~~~json
{
  "message": {
    "role": "assistant",
    "content": "I'm "
  },
  "done": false,
  "index": 0
}
~~~

Subsequent chunks:

~~~json
{
  "message": {
    "role": "assistant",
    "content": "doing well"
  },
  "done": false,
  "index": 1
}
~~~

The last chunk has `"done": true`:

~~~json
{
  "message": {
    "role": "assistant",
    "content": ", thank you!"
  },
  "done": true,
  "index": 2
}
~~~

#### Actual JSON Streaming Response Format (RPC compliant)

For RPC compliance, each JSON response is sent as a single line ending with a newline character `\n`:

~~~
{"message":{"role":"assistant","content":"I'm "},"done":false,"index":0}\n
{"message":{"role":"assistant","content":"doing well"},"done":false,"index":1}\n
{"message":{"role":"assistant","content":", thank you!"},"done":true,"index":2}\n
~~~

### 3. SSE Streaming Response Format

#### SSE Streaming Response Format (Formatted for readability)

Each chunk is formatted as an SSE message. The example below shows the logical structure:

~~~json
// First chunk
data: {
  "message": {
    "role": "assistant",
    "content": "I'm "
  },
  "done": false,
  "index": 0
}

// Second chunk
data: {
  "message": {
    "role": "assistant",
    "content": "doing well"
  },
  "done": false,
  "index": 1
}

// Third chunk
data: {
  "message": {
    "role": "assistant",
    "content": ", thank you!"
  },
  "done": false,
  "index": 2
}

// Final termination signal
data: [END]
~~~

#### Actual SSE Streaming Response Format (RPC compliant)

The actual SSE stream follows the SSE protocol with each message on a single line followed by double newlines:

~~~
data: {"message":{"role":"assistant","content":"I'm "},"done":false,"index":0}\n\n
data: {"message":{"role":"assistant","content":"doing well"},"done":false,"index":1}\n\n
data: {"message":{"role":"assistant","content":", thank you!"},"done":false,"index":2}\n\n
data: [END]\n\n
~~~

The last chunk is a special `data: [END]\n\n` message to signal the end of the stream.

## Response Headers

### Regular Response Headers

~~~
Content-Type: application/json
~~~

### JSON Streaming Response Headers

~~~
Content-Type: application/json
Transfer-Encoding: chunked
Cache-Control: no-cache
Connection: keep-alive
~~~

### SSE Streaming Response Headers

~~~
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
~~~

## Error Responses

### Regular (Non-Streaming) Error Responses

For non-streaming requests, error responses will follow this format:

~~~json
{
  "error": {
    "message": "Error message describing what went wrong",
    "type": "error_type",
    "code": "error_code"
  }
}
~~~

### JSON Streaming Error Responses

For JSON streaming, error responses follow the same newline-delimited format but with an error object:

~~~
{"error":{"message":"Error message describing what went wrong","type":"error_type","code":"error_code"},"done":true}\n
~~~

**Note:** This is the most widely adopted format across APIs, but it differs structurally from success responses. In success cases, the "message" field contains a JSON object, while in error cases, "message" is a string. Clients will need to implement specific error parsing logic to handle this inconsistency.

### SSE Streaming Error Responses

For SSE streaming, errors use the standard SSE protocol's event type feature:

~~~
event: error
data: {"message":"Error message describing what went wrong","type":"error_type","code":"error_code"}\n\n
data: [END]\n\n
~~~

This format is fully compliant with the SSE specification and will be automatically routed to error handlers in browser-based EventSource implementations.

## Example Usage

### Example: Regular Invocation

~~~bash
curl -X POST http://your-api.example/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_api_key" \
  -d '{
    "model": "model-name",
    "messages": [{"role": "user", "content": "Hello, world!"}],
    "stream": false
  }'
~~~

### Example: JSON Streaming

~~~bash
curl -X POST http://your-api.example/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_api_key" \
  -d '{
    "model": "model-name",
    "messages": [{"role": "user", "content": "Hello, world!"}],
    "stream": true
  }'
~~~

### Example: SSE Streaming

~~~bash
curl -X POST http://your-api.example/chat/sse \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_api_key" \
  -d '{
    "model": "model-name",
    "messages": [{"role": "user", "content": "Hello, world!"}]
  }'
~~~

## Client-Side Implementation for SSE

~~~javascript
const eventSource = new EventSource('/chat/sse');

eventSource.onmessage = (event) => {
  if (event.data === '[END]') {
    console.log('Stream ended');
    eventSource.close(); // Close the connection
  } else {
    const data = JSON.parse(event.data);
    console.log(data.message.content); // Process chunk
  }
};

eventSource.onerror = (error) => {
  console.error('SSE error:', error);
  eventSource.close(); // Close on error
};
~~~