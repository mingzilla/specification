# Chat Completions API Specification

This document outlines the specifications for a chat completions API that supports both regular invocations and streaming responses (JSON and SSE).

## Requirements and Key Criteria

- Follows Ollama's response format structure
- Supports both traditional request/response and streaming modes
- Separate endpoints for different response types
- Clean, consistent, and easy-to-implement interfaces
- Minimalist JSON structure for efficient parsing
- Proper termination signals for streams

## Endpoints

| Endpoint       | Method | Description                            | WebFlux Return Type                           |
| -------------- | ------ | -------------------------------------- | --------------------------------------------- |
| `/chat/json`   | POST   | For regular non-streaming responses    | `Mono<LlmClientOutput>`                       |
| `/chat/stream` | POST   | For JSON streaming responses           | `Flux<LlmClientOutputChunk>`                  |
| `/chat/sse`    | POST   | For SSE streaming (Server-Sent Events) | `Flux<ServerSentEvent<LlmClientOutputChunk>>` |

## Why Separate Endpoints?

While many LLM providers use a single endpoint with a `stream` parameter to handle both streaming and non-streaming requests, this approach creates significant implementation challenges. Separate endpoints offer several advantages:

1. **Different Response Handling Logic**: The code required to process streaming vs. non-streaming responses differs substantially.
2. **Different Response Formats**: Non-streaming responses return a complete JSON object, while streaming responses deliver sequences of chunks with different formats. Spring WebFlux and other non-blocking frameworks enforce different return types for these patterns (e.g., `Mono` for single responses, `Flux` for streams).
3. **Reduced Complexity**: Separate endpoints allow for cleaner, more focused implementation of each response type.
4. **Clear API Contract**: Makes it explicit to API consumers which endpoint to use for each use case.
5. **Simplified Error Handling**: Specialized error handling can be implemented for each response type.
6. **Focused Implementation**: Each endpoint can be implemented with code specifically tailored for its response type.
7. **Performance Optimization**: Each endpoint can be optimized for its specific response pattern.
8. **Independent Testing**: Easier to test and validate each response type separately.
9. **Framework Compatibility**: Directly aligns with reactive framework patterns, such as Spring WebFlux's return type requirements:
   - `/chat/json` can return a `Mono<LlmClientOutput>` for a single complete response
   - `/chat/stream` can return a `Flux<LlmClientOutputChunk>` for a stream of JSON chunks
   - `/chat/sse` can return a `Flux<ServerSentEvent<LlmClientOutputChunk>>` for SSE streaming

## Request Format

### Headers

~~~
Content-Type: application/json
Authorization: Bearer <your_api_key>
~~~

### Request Body for `/chat/json`

~~~json
{
  "model": "model-name",          // Optional: Model identifier (server side to provide default)
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
  "temperature": 0.7              // Optional: Controls randomness
}
~~~

### Request Body for `/chat/stream`

~~~json
{
  "model": "model-name",          // Optional: Model identifier (server side to provide default)
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
  "temperature": 0.7              // Optional: Controls randomness
}
~~~

### Request Body for `/chat/sse`

~~~json
{
  // Same parameters as other endpoints
  "model": "model-name",
  "messages": [
    // conversation history
  ],
  "temperature": 0.7
}
~~~

## Response Formats

### 1. Regular (Non-Streaming) Response from `/chat/json`

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

### 2. JSON Streaming Response from `/chat/stream`

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

### 3. SSE Streaming Response from `/chat/sse`

#### SSE Streaming Response Format (Formatted for readability)

Each chunk is formatted as an SSE message. The example below shows the logical structure:

~~~
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

### Regular Response Headers (`/chat/json`)

~~~
Content-Type: application/json
~~~

### JSON Streaming Response Headers (`/chat/stream`)

~~~
Content-Type: application/json
Transfer-Encoding: chunked
Cache-Control: no-cache
Connection: keep-alive
~~~

### SSE Streaming Response Headers (`/chat/sse`)

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
curl -X POST http://your-api.example/chat/json \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_api_key" \
  -d '{
    "model": "model-name",
    "messages": [{"role": "user", "content": "Hello, world!"}]
  }'
~~~

### Example: JSON Streaming

~~~bash
curl -X POST http://your-api.example/chat/stream \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_api_key" \
  -d '{
    "model": "model-name",
    "messages": [{"role": "user", "content": "Hello, world!"}]
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