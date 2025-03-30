# LLM Client Implementation Specification (Reactive Pattern)

## Project Overview

- **Project Name:** llm-client
- **Language:** Java 17
- **Framework:** Spring WebFlux
- **Build System:** Gradle
- **Primary Use Case:** Non-blocking LLM API interaction following the streaming-api-spec.md

## Core Principles

1. **100% Non-blocking:** The entire library must be fully non-blocking from end to end, using Spring WebFlux reactive types (Mono/Flux) throughout.
2. **Minimalist Design:** Focus only on LLM chat completions API interactions, avoiding feature bloat.
3. **Immutable Data Structures:** Use Java records for all data structures to ensure immutability.
4. **Reactive Streaming:** Support both traditional request/response and streaming (JSON and SSE).
5. **Full Specification Compliance:** Adhere strictly to the streaming-api-spec.md format.
6. **Clear Error Handling:** Consistent approach to error handling throughout the library.
7. **Pure Reactive Patterns:** Use standard reactive patterns without callbacks to ensure compatibility with Spring WebFlux controllers.
8. **Separate Endpoints:** Distinct endpoints for each response type: json, stream, and sse.
9. **Safe Integration with Blocking Code:** Provide appropriate patterns for safely integrating with blocking database operations.

## Domain Model Specification

### LlmClientMessage

```java
/**
 * Message record for chat completions API
 * Represents a single message in a conversation with the LLM
 */
public record LlmClientMessage(String role, String content) {
    /**
     * Creates a system message
     * @param content The system instruction
     * @return A new LlmClientMessage with role "system"
     */
    public static LlmClientMessage system(String content) { /* ... */ }

    /**
     * Creates a user message
     * @param content The user's input
     * @return A new LlmClientMessage with role "user"
     */
    public static LlmClientMessage user(String content) { /* ... */ }

    /**
     * Creates an assistant message
     * @param content The assistant's response
     * @return A new LlmClientMessage with role "assistant"
     */
    public static LlmClientMessage assistant(String content) { /* ... */ }
}
```

### LlmClientError

```java
/**
 * Error representation for LLM API errors
 * Follows the error structure defined in the API specification
 */
public record LlmClientError(String message, String type,
        /**
         * Provider-specific error code from LLM response.
         * Examples:
         * - OpenAI: "context_length_exceeded", "rate_limit_exceeded"
         * - Anthropic: "overloaded_error", "invalid_request_error"
         * For internal errors: "INTERNAL_ERROR"
         * For HTTP transport errors without LLM error code: "HTTP_" + statusCode
         */
        String code) {
    /**
     * Creates an error from an exception
     * @param throwable The exception to convert
     * @return A new LlmClientError with appropriate message, type and code
     */
    public static LlmClientError fromException(Throwable throwable) { /* ... */ }

    /**
     * Creates an error from a response status, message, and provider-specific error code
     * @param statusCode The HTTP status code
     * @param message The error message
     * @param providerCode Provider-specific error code from response (can be null)
     * @return A new LlmClientError with appropriate type and code
     */
    public static LlmClientError fromResponse(int statusCode, String message, String providerCode) { /* ... */ }

    /**
     * Creates a standard 401 Unauthorized error
     * @return A new LlmClientError for unauthorized access
     */
    public static LlmClientError create401() { /* ... */ }
}
```

### LlmClientOutputChunk

```java
/**
 * Represents a chunk of response from the streaming API
 * Corresponds to a single piece of a streamed response
 */
public record LlmClientOutputChunk(LlmClientMessage message, boolean done, int index) {
    /**
     * Parses a JSON string into an LlmClientOutputChunk
     * @param json The JSON string to parse
     * @return A new LlmClientOutputChunk
     */
    public static LlmClientOutputChunk fromJson(String json) { /* ... */ }

    /**
     * Creates an error chunk with the given message
     * @param message The error message
     * @return A new LlmClientOutputChunk representing an error
     */
    public static LlmClientOutputChunk forError(String message) { /* ... */ }
}
```

### LlmClientOutput

```java
/**
 * Complete response from the LLM API
 * Represents either a successful response or an error
 */
public record LlmClientOutput(int statusCode, Map<String, String> headers, 
                             String body, LlmClientError error, LlmClientMessage message) {
    /**
     * Determines if the request was successful
     * @return true if successful, false otherwise
     */
    public boolean isSuccessful() { /* ... */ }

    /**
     * Gets the failure reason if the request failed
     * @return The error message or null if successful
     */
    public String getFailureReason() { /* ... */ }

    /**
     * Gets a specific header value
     * @param name The header name
     * @return The header value or null if not found
     */
    public String getHeader(String name) { /* ... */ }

    /**
     * Parses the response body as JSON
     * @param type The class to parse the JSON into
     * @return The parsed object
     */
    public <T> T parseJsonBody(Class<T> type) { /* ... */ }

    /**
     * Returns the response as a structured map
     * @return A map containing all response data
     */
    public Map<String, Object> asMap() { /* ... */ }

    /**
     * Creates an output object representing successful verification
     * @return A new LlmClientOutput indicating verification success
     */
    public static LlmClientOutput verificationSuccess() { /* ... */ }

    /**
     * Creates an output object for an error
     * @param error The LlmClientError, must not be null
     * @return A new LlmClientOutput with the error set
     * @throws IllegalArgumentException if error is null
     */
    public static LlmClientOutput forError(LlmClientError error) { /* ... */ }

    /**
     * Creates an output object for a successful response
     * @param response The WebFlux ClientResponse
     * @param body The response body
     * @return A new LlmClientOutput with success data
     */
    public static LlmClientOutput forSuccess(ClientResponse response, String body) { /* ... */ }

    /**
     * Creates a response from a WebClient response
     * @param response The WebClient response
     * @param body The response body as string
     * @return A new LlmClientOutput instance
     */
    public static LlmClientOutput fromResponse(ClientResponse response, String body) { /* ... */ }

    /**
     * Creates an output object for a 401 Unauthorized error
     * @return A new LlmClientOutput with 401 error
     */
    public static LlmClientOutput forError401() { /* ... */ }
}
```

### LlmClientInputBody

```java
/**
 * Input body structure for chat completions API
 * Contains the parameters for a chat completions request
 */
public record LlmClientInputBody(String model, List<LlmClientMessage> messages, 
                                boolean stream, Double temperature, boolean isSse) {
    /**
     * Creates a chat completion request body
     * @param model Model identifier or null to use default
     * @param messages Array of message objects with role and content
     * @param stream Whether to stream the response
     * @param temperature Temperature value (0-1) or null for default
     * @return The created input body
     */
    public static LlmClientInputBody chat(String model, List<LlmClientMessage> messages, 
                                        boolean stream, Double temperature) { /* ... */ }

    /**
     * Creates an SSE completion request body (always streaming)
     * @param model Model identifier or null to use default
     * @param messages Array of message objects with role and content
     * @param temperature Temperature value (0-1) or null for default
     * @return The created input body configured for SSE
     */
    public static LlmClientInputBody sse(String model, List<LlmClientMessage> messages, 
                                       Double temperature) { /* ... */ }

    /**
     * Creates a simple completion request with a single user message
     * @param content The user message content
     * @param stream Whether to stream the response
     * @return The created input body
     */
    public static LlmClientInputBody chatMessage(String content, boolean stream) { /* ... */ }

    /**
     * Converts the input body to a JSON-serializable map
     * @return A map of values ready for JSON serialization
     */
    public Map<String, Object> toJsonObject() { /* ... */ }
}
```

### LlmClientInput

```java
/**
 * Input contract for HTTP requests to LLM API
 * Represents a complete request to the LLM API
 */
public record LlmClientInput(String url, String body, 
                            Map<String, String> headers, LlmClientInputBody inputBody) {
    /**
     * Creates an input for an LLM chat request
     * @param url The complete URL to send the request to
     * @param inputBody The LlmClientInputBody containing the request parameters
     * @param headers Headers for the request
     * @return A new LlmClientInput configured for chat completions
     */
    public static LlmClientInput chat(String url, LlmClientInputBody inputBody, 
                                    Map<String, String> headers) { /* ... */ }

    /**
     * Sets HTTP headers for the request
     * Adds all headers from this input's headers map to the provided HttpHeaders object
     * @param headers The HttpHeaders object to update with this input's headers
     */
    public void setHeaders(HttpHeaders headers) { /* ... */ }
}
```

### LlmClientVerifier

```java
/**
 * Verification helper for LLM client operations
 */
public final class LlmClientVerifier {
    private LlmClientVerifier() {
        // Prevent instantiation
    }

    /**
     * Verifies that a required component is not null
     * @param component The component to verify
     * @param name The name of the component for the error message
     * @throws IllegalArgumentException if the component is null
     */
    public static void require(Object component, String name) { /* ... */ }
}
```

## Core Client Implementation

### LlmClient

```java
/**
 * Main client class for LLM operations
 * Handles all communication with the LLM API
 */
public class LlmClient {
    private final WebClient webClient;
    
    /**
     * Creates a new LlmClient with the specified WebClient
     * @param webClient The WebClient to use for HTTP requests
     */
    public LlmClient(WebClient webClient) { /* ... */ }
    
    /**
     * Creates a new LlmClient with a custom WebClient
     * @param webClient The WebClient to use
     * @return A new LlmClient
     */
    public static LlmClient create(WebClient webClient) { /* ... */ }
    
    /**
     * Handles verification and sending a request with a simpler API
     * Executes verification check before proceeding with the request
     * 
     * @param verificationSupplier A supplier that returns LlmClientError if verification fails, null if successful
     * @param inputSupplier A supplier function that provides the LlmClientInput
     * @return A Mono that emits the LlmClientOutput when the request completes
     */
    public Mono<LlmClientOutput> verifyAndSend(
            Supplier<LlmClientOutput> verificationSupplier,
            Supplier<LlmClientInput> inputSupplier) { /* ... */ }
    
    /**
     * Safely handles sending a request with potentially blocking preparation logic
     * This method should be used instead of send() to ensure proper reactive patterns
     * 
     * @param inputSupplier A supplier function that provides the LlmClientInput, may contain blocking code
     * @return A Mono that emits the LlmClientOutput when the request completes
     */
    public Mono<LlmClientOutput> handleSend(Supplier<LlmClientInput> inputSupplier) { /* ... */ }
    
    /**
     * IMPORTANT: Do not use this method directly. Use handleSend() instead
     * to ensure proper handling of potentially blocking preparation code.
     * 
     * Sends a request to the LLM API and returns a single non-streaming response
     * 
     * @param input The LlmClientInput containing the request details
     * @return A Mono that emits the LlmClientOutput when the request completes
     */
    private Mono<LlmClientOutput> send(LlmClientInput input) { /* ... */ }
    
    /**
     * Handles verification and streaming a request with a simpler API
     * Executes verification check before proceeding with the request
     * 
     * @param verificationSupplier A supplier that returns LlmClientError if verification fails, null if successful
     * @param inputSupplier A supplier function that provides the LlmClientInput
     * @return A Flux that emits each chunk from the streaming response
     */
    public Flux<LlmClientOutputChunk> verifyAndStream(
            Supplier<LlmClientOutput> verificationSupplier,
            Supplier<LlmClientInput> inputSupplier) { /* ... */ }
    
    /**
     * Safely handles streaming a request with potentially blocking preparation logic
     * This method should be used instead of stream() to ensure proper reactive patterns
     * 
     * @param inputSupplier A supplier function that provides the LlmClientInput, may contain blocking code
     * @return A Flux that emits each chunk from the streaming response
     */
    public Flux<LlmClientOutputChunk> handleStream(Supplier<LlmClientInput> inputSupplier) { /* ... */ }
    
    /**
     * IMPORTANT: Do not use this method directly. Use handleStream() instead
     * to ensure proper handling of potentially blocking preparation code.
     * 
     * Streams a request to the LLM API with JSON streaming format
     * 
     * @param input The LlmClientInput containing the request details
     * @return A Flux that emits each chunk from the streaming response
     */
    private Flux<LlmClientOutputChunk> stream(LlmClientInput input) { /* ... */ }
    
    /**
     * Handles verification and SSE streaming a request with a simpler API
     * Executes verification check before proceeding with the request
     * 
     * @param verificationSupplier A supplier that returns LlmClientError if verification fails, null if successful
     * @param inputSupplier A supplier function that provides the LlmClientInput
     * @return A Flux that emits each SSE event from the streaming response
     */
    public Flux<ServerSentEvent<?>> verifyAndStreamSse(
            Supplier<LlmClientOutput> verificationSupplier,
            Supplier<LlmClientInput> inputSupplier) { /* ... */ }
    
    /**
     * Safely handles SSE streaming a request with potentially blocking preparation logic
     * This method should be used instead of streamSse() to ensure proper reactive patterns
     * 
     * @param inputSupplier A supplier function that provides the LlmClientInput, may contain blocking code
     * @return A Flux that emits each SSE event from the streaming response
     */
    public Flux<ServerSentEvent<?>> handleStreamSse(Supplier<LlmClientInput> inputSupplier) { /* ... */ }
    
    /**
     * IMPORTANT: Do not use this method directly. Use handleStreamSse() instead
     * to ensure proper handling of potentially blocking preparation code.
     * 
     * Streams a request to the LLM API with SSE streaming format
     * 
     * @param input The LlmClientInput containing the request details
     * @return A Flux that emits each SSE event from the streaming response
     */
    private Flux<ServerSentEvent<?>> streamSse(LlmClientInput input) { /* ... */ }
}
```

### LlmClientJsonUtil

```java
/**
 * JSON utilities for LLM client
 * Provides JSON parsing and serialization capabilities
 */
public class LlmClientJsonUtil {
    private static final ObjectMapper objectMapper = new ObjectMapper();

    /**
     * Parses a JSON string into a simple class type
     * @param <T> The type to parse the JSON into
     * @param json The JSON string to parse
     * @param clazz The class to parse into
     * @return The parsed object
     */
    public static <T> T fromJson(String json, Class<T> clazz) { /* ... */ }
    
    /**
     * Convert JSON string to object using TypeReference
     * e.g. {@code new TypeReference<Map<String, List>>() {}}
     * returns a {@code Map<String, List>}
     * 
     * @param <T> The type to parse the JSON into
     * @param json The JSON string to parse
     * @param typeReference The TypeReference describing the type
     * @return The parsed object
     */
    public static <T> T fromJsonToStructure(String json, TypeReference<T> typeReference) { /* ... */ }
    
    /**
     * Converts an object to a JSON string
     * @param obj The object to convert
     * @return The JSON string
     */
    public static String toJson(Object obj) { /* ... */ }
    
    /**
     * Parses a streaming chunk from a JSON string
     * @param chunk The JSON string to parse
     * @return The parsed LlmClientOutputChunk
     */
    public static LlmClientOutputChunk parseStreamChunk(String chunk) { /* ... */ }
    
    /**
     * Determines if a chunk represents the end of a stream
     * @param chunk The chunk to check
     * @return true if the chunk is an end marker, false otherwise
     */
    public static boolean isStreamEnd(String chunk) { /* ... */ }

    /**
     * Extracts error code from LLM provider error response
     * Handles different provider formats:
     * - OpenAI: {"error": {"code": "context_length_exceeded"}}
     * - Anthropic: {"error": {"type": "invalid_request_error"}}
     * - Generic: {"code": "error_code"}
     *
     * @param errorBody The error response body
     * @return The provider error code or null if not found
     */
    public static String extractErrorCode(String errorBody) { /* ... */ }
}
```

## Example Controller Implementation

- Refer to [llm-client](https://github.com/mingzilla/llm-client)

## Implementation Guidelines

### Non-blocking Requirements

1. **WebClient Usage:** All HTTP requests must use Spring WebFlux's WebClient with non-blocking methods.
2. **Reactive Types:** All API methods must return Mono or Flux and not block.
3. **No Blocking Calls:** Never use `.block()`, `.toFuture().get()`, or similar blocking methods.
4. **Reactive Operators:** Use appropriate reactive operators like `map`, `flatMap`, `doOnNext`, etc.
5. **Thread Verification:** Unit tests must verify that operations run on non-blocking threads.
6. **Blocking Code Handling:** All potentially blocking code (database queries, file I/O) must be wrapped in supplier functions and processed through the handle* methods.

### JSON Parsing and Serialization

1. **Jackson Integration:** Use Jackson for JSON handling, configured for Spring WebFlux.
2. **Error Handling:** Handle JSON parsing errors gracefully with proper error propagation.
3. **Streaming Parsing:** For streaming responses, parse chunks individually without blocking.

### Stream Processing

1. **Chunked Processing:** Properly handle line-delimited JSON in streams.
2. **End Detection:** Correctly identify stream termination markers (`"done": true` or `data: [DONE]`).
3. **SSE Handling:** For SSE streams, use the appropriate WebClient methods and SSE decoder.
4. **Backpressure:** Respect backpressure throughout stream processing.

### Error Handling

1. **Consistent Approach:** Convert all errors to LlmClientError.
2. **Non-blocking:** Error handling must not block.
3. **Propagation:** Error states should properly propagate through reactive chains.
4. **Status Codes:** Correctly handle different HTTP status codes.

## Testing Strategy

### Unit Testing

1. **Non-blocking Verification:**
   - Use `StepVerifier` to test reactive streams
   - Verify execution on non-blocking threads
   - Ensure no blocking operations are used

2. **Mock Integration:**
   - Use `MockWebServer` to simulate HTTP responses
   - Test various response scenarios including success, errors, and timeouts
   - Verify correct handling of different content types

3. **Stream Testing:**
   - Test with simulated chunked/SSE responses
   - Verify correct chunk processing
   - Validate end-of-stream detection

4. **Error Handling Tests:**
   - Verify proper error propagation
   - Test provider-specific error code extraction
   - Check HTTP status code handling

### Example Test Classes

```java
// Test basic error functionality
class LlmClientErrorTests {
    @Test void testFromException() { /* ... */ }
    @Test void testFromResponse() { /* ... */ }
    @Test void testFromResponseWithProviderCode() { /* ... */ }
}

// Test input body creation and serialization
class LlmClientInputBodyTests {
    @Test void testChat() { /* ... */ }
    @Test void testSse() { /* ... */ }
    @Test void testToJsonObject() { /* ... */ }
}

// Test JSON utility functions
class LlmClientJsonUtilTests {
    @Test void extractErrorCode_nullOrEmpty_returnsNull() { /* ... */ }
    @Test void extractErrorCode_invalidJson_returnsNull() { /* ... */ }
    @Test void extractErrorCode_directCode_returnsCode() { /* ... */ }
    @Test void extractErrorCode_openAiStyle_returnsCode() { /* ... */ }
    @Test void extractErrorCode_anthropicStyle_returnsType() { /* ... */ }
    @Test void extractErrorCode_noCodeOrType_returnsNull() { /* ... */ }
}

// Test message creation
class LlmClientMessageTests {
    @Test void testSystemMessage() { /* ... */ }
    @Test void testUserMessage() { /* ... */ }
    @Test void testAssistantMessage() { /* ... */ }
}

// Test output chunk parsing
class LlmClientOutputChunkTests {
    @Test void testFromJson() { /* ... */ }
    @Test void testFromInvalidJson() { /* ... */ }
}

// Integration tests for the main client
class LlmClientTests {
    @Test void testNonBlockingSend() { /* ... */ }
    @Test void testJsonStreaming() { /* ... */ }
    @Test void testSseStreaming() { /* ... */ }
    @Test void testErrorHandling() { /* ... */ }
}
```

## Gradle Setup

```groovy
plugins {
    id 'java-library'
    id 'maven-publish'
}

group = 'io.github.mingzilla'
version = '0.1.0'
sourceCompatibility = '17'

repositories {
    mavenCentral()
}

dependencies {
    implementation 'org.springframework:spring-webflux:5.3.27'
    implementation 'io.projectreactor.netty:reactor-netty-http:1.0.30'
    implementation 'com.fasterxml.jackson.core:jackson-databind:2.14.2'
    implementation 'io.projectreactor:reactor-core:3.5.6'
    
    testImplementation 'org.junit.jupiter:junit-jupiter:5.9.2'
    testImplementation 'io.projectreactor:reactor-test:3.5.6'
    testImplementation 'com.squareup.okhttp3:mockwebserver:4.10.0'
}

test {
    useJUnitPlatform()
}

publishing {
    publications {
        mavenJava(MavenPublication) {
            from components.java
        }
    }
}
```

## Best Practices for Blocking Code Integration

1. **Use verification methods** - `verifyAndSend`, `verifyAndStream`, and `verifyAndStreamSse` methods provide integrated verification before executing requests.

2. **Use handle* methods for blocking preparation** - Never directly call the private send/stream/streamSse methods. Always use `handleSend`, `handleStream`, or `handleStreamSse`.

3. **Keep blocking code minimal** - Only include necessary database calls and processing logic in the supplier function.

4. **Return prepared input** - The supplier should return a fully configured LlmClientInput object.

5. **Handle errors** - Include appropriate error handling within the supplier function.

6. **Avoid nested reactive code** - Don't include Mono/Flux operations inside the supplier function.

7. **Consider timeout handling** - For long-running database operations, consider adding timeouts.

8. **Perform validation** - Use LlmClientVerifier.require() to validate inputs and prevent NullPointerExceptions.

These guidelines ensure a clean separation between potentially blocking preparation code and the non-blocking reactive pipeline for API communication.