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
public record LlmClientError(String message, String type, String code) {
    /**
     * Creates an error from an exception
     * @param throwable The exception to convert
     * @return A new LlmClientError with appropriate message, type and code
     */
    public static LlmClientError fromException(Throwable throwable) { /* ... */ }

    /**
     * Creates an error from a response status and message
     * @param statusCode The HTTP status code
     * @param message The error message
     * @return A new LlmClientError with appropriate type and code
     */
    public static LlmClientError fromResponse(int statusCode, String message) { /* ... */ }
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
     * Creates an output object for an error
     * @param error The LlmClientError
     * @return A new LlmClientOutput with the error set
     */
    public static LlmClientOutput forError(LlmClientError error) { /* ... */ }

    /**
     * Creates an output object for a successful response
     * @param response The WebFlux ClientResponse
     * @param body The response body
     * @return A new LlmClientOutput with success data
     */
    public static LlmClientOutput forSuccess(ClientResponse response, String body) { /* ... */ }
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
     * IMPORTANT: Do not use this method directly. Use handleSend() instead
     * to ensure proper handling of potentially blocking preparation code.
     * 
     * Sends a request to the LLM API and returns a single non-streaming response
     * @param input The LlmClientInput containing the request details
     * @return A Mono that emits the LlmClientOutput when the request completes
     */
    private Mono<LlmClientOutput> send(LlmClientInput input) { 
        return webClient.post()
            .uri(input.url())
            .bodyValue(input.body())
            .headers(headers -> headers.putAll(input.headers()))
            .retrieve()
            .bodyToMono(String.class)
            .map(this::parseResponse)
            .onErrorResume(error -> Mono.just(
                LlmClientOutput.forError(LlmClientError.fromException(error))));
    }
    
    /**
     * IMPORTANT: Do not use this method directly. Use handleStream() instead
     * to ensure proper handling of potentially blocking preparation code.
     * 
     * Streams a request to the LLM API with JSON streaming format
     * @param input The LlmClientInput containing the request details
     * @return A Flux that emits each chunk from the streaming response
     */
    private Flux<LlmClientOutputChunk> stream(LlmClientInput input) {
        return webClient.post()
            .uri(input.url())
            .bodyValue(input.body())
            .headers(headers -> headers.putAll(input.headers()))
            .retrieve()
            .bodyToFlux(String.class)
            .filter(line -> !line.isEmpty())
            .map(this::parseChunk)
            .takeUntil(LlmClientOutputChunk::done);
    }
    
    /**
     * IMPORTANT: Do not use this method directly. Use handleStreamSse() instead
     * to ensure proper handling of potentially blocking preparation code.
     * 
     * Streams a request to the LLM API with SSE streaming format
     * @param input The LlmClientInput containing the request details
     * @return A Flux that emits each SSE event from the streaming response
     */
    private Flux<ServerSentEvent<LlmClientOutputChunk>> streamSse(LlmClientInput input) {
        return webClient.post()
            .uri(input.url())
            .bodyValue(input.body())
            .headers(headers -> headers.putAll(input.headers()))
            .retrieve()
            .bodyToFlux(String.class)
            .filter(line -> !line.isEmpty() && line.startsWith("data: "))
            .map(line -> {
                String data = line.substring(6);  // Remove "data: " prefix
                if ("[END]".equals(data)) {
                    return ServerSentEvent.<LlmClientOutputChunk>builder()
                        .data(null)
                        .event("end")
                        .build();
                } else {
                    return ServerSentEvent.<LlmClientOutputChunk>builder()
                        .data(parseChunk(data))
                        .build();
                }
            })
            .takeUntil(event -> "end".equals(event.event()));
    }
    
    /**
     * Safely handles sending a request with potentially blocking preparation logic
     * This method should be used instead of send() to ensure proper reactive patterns
     * 
     * @param inputSupplier A supplier function that provides the LlmClientInput, may contain blocking code
     * @return A Mono that emits the LlmClientOutput when the request completes
     */
    public Mono<LlmClientOutput> handleSend(Supplier<LlmClientInput> inputSupplier) {
        return Mono.fromCallable(inputSupplier::get)
            .subscribeOn(Schedulers.boundedElastic())
            .flatMap(this::send);
    }
    
    /**
     * Safely handles streaming a request with potentially blocking preparation logic
     * This method should be used instead of stream() to ensure proper reactive patterns
     * 
     * @param inputSupplier A supplier function that provides the LlmClientInput, may contain blocking code
     * @return A Flux that emits each chunk from the streaming response
     */
    public Flux<LlmClientOutputChunk> handleStream(Supplier<LlmClientInput> inputSupplier) {
        return Mono.fromCallable(inputSupplier::get)
            .subscribeOn(Schedulers.boundedElastic())
            .flatMapMany(this::stream);
    }
    
    /**
     * Safely handles SSE streaming a request with potentially blocking preparation logic
     * This method should be used instead of streamSse() to ensure proper reactive patterns
     * 
     * @param inputSupplier A supplier function that provides the LlmClientInput, may contain blocking code
     * @return A Flux that emits each SSE event from the streaming response
     */
    public Flux<ServerSentEvent<LlmClientOutputChunk>> handleStreamSse(Supplier<LlmClientInput> inputSupplier) {
        return Mono.fromCallable(inputSupplier::get)
            .subscribeOn(Schedulers.boundedElastic())
            .flatMapMany(this::streamSse);
    }
    
    // Private utility methods
    private LlmClientOutput parseResponse(String responseBody) { /* ... */ }
    private LlmClientOutputChunk parseChunk(String chunk) { /* ... */ }
    private boolean isDone(String chunk) { /* ... */ }
}
```

### LlmClientJsonUtil

```java
/**
 * JSON utilities for LLM client
 * Provides JSON parsing and serialization capabilities
 */
public class LlmClientJsonUtil {
    /**
     * Parses a JSON string into an object
     * @param json The JSON string to parse
     * @param clazz The class to parse into
     * @return The parsed object
     */
    public static <T> T fromJson(String json, Class<T> clazz) { /* ... */ }
    
    /**
     * Parses a JSON string into a complex type
     * @param json The JSON string to parse
     * @param typeReference The TypeReference describing the type
     * @return The parsed object
     */
    public static <T> T fromJson(String json, TypeReference<T> typeReference) { /* ... */ }
    
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
}
```

## Example Controller Implementation

```java
/**
 * Example controller that demonstrates how to use the LlmClient library
 * Shows implementations for all three endpoints: json, stream, and sse
 */
@RestController
@RequestMapping("/chat")
public class ChatController {
    private final LlmClient llmClient;
    private final String apiUrl;
    private final UserRepository userRepository;  // Example repository for DB access
    
    public ChatController(LlmClient llmClient, 
                         @Value("${llm.api.url}") String apiUrl,
                         UserRepository userRepository) {
        this.llmClient = llmClient;
        this.apiUrl = apiUrl;
        this.userRepository = userRepository;
    }
    
    /**
     * Non-streaming JSON response endpoint
     * Use for regular single response completions
     */
    @PostMapping("/json")
    public Mono<LlmClientOutput> json(@RequestBody ChatRequest request) {
        return llmClient.handleSend(() -> {
            // Any blocking database calls can safely go here
            User user = userRepository.findById(request.getUserId());
            List<Document> userDocs = documentRepository.findByUserId(user.getId());
            
            // Process data as needed
            List<LlmClientMessage> messages = createMessagesFromUserAndRequest(user, userDocs, request);
            
            // Return the input object for the LLM request
            return LlmClientInput.chat(
                apiUrl + "/chat/completions", 
                LlmClientInputBody.chat(
                    request.getModel(),
                    messages,
                    false,  // Not streaming
                    request.getTemperature()
                ), 
                createHeadersFromUser(user)
            );
        });
    }
    
    /**
     * Streaming JSON response endpoint
     * Use for JSON streaming responses (newline-delimited JSON)
     */
    @PostMapping(value = "/stream", produces = MediaType.APPLICATION_NDJSON_VALUE)
    public Flux<LlmClientOutputChunk> stream(@RequestBody ChatRequest request) {
        return llmClient.handleStream(() -> {
            // All blocking database access and processing can safely go here
            User user = userRepository.findById(request.getUserId());
            Preferences prefs = preferencesRepository.findByUserId(user.getId());
            
            // Process data as needed to build the request
            List<LlmClientMessage> messages = buildMessagesWithUserContext(user, prefs, request);
            
            // Return the input object for the LLM request
            return LlmClientInput.chat(
                apiUrl + "/chat/completions", 
                LlmClientInputBody.chat(
                    request.getModel(),
                    messages,
                    true,  // Streaming
                    request.getTemperature()
                ), 
                createHeadersWithAuth(user.getApiToken())
            );
        });
    }
    
    /**
     * SSE streaming response endpoint
     * Use for Server-Sent Events streaming
     */
    @PostMapping(value = "/sse", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public Flux<ServerSentEvent<LlmClientOutputChunk>> sse(@RequestBody ChatRequest request) {
        return llmClient.handleStreamSse(() -> {
            // All blocking code including database queries can safely go here
            ConversationHistory history = conversationRepository.findLatestByUserId(request.getUserId());
            List<Message> previousMessages = messageRepository.findByConversationId(history.getId());
            
            // Process the data as needed
            List<LlmClientMessage> messages = convertToLlmMessages(previousMessages, request.getContent());
            
            // Return the input object for the LLM request
            return LlmClientInput.chat(
                apiUrl + "/chat/sse", 
                LlmClientInputBody.sse(
                    request.getModel(),
                    messages,
                    request.getTemperature()
                ), 
                createAuthHeaders(request.getApiKey())
            );
        });
    }
}

/**
 * Example request body for chat completions
 */
public record ChatRequest(
    String userId,
    String model,
    List<LlmClientMessage> messages,
    String content,
    Double temperature,
    String apiKey
) {
    // Could include other parameters like max_tokens, top_p, etc.
}
```

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

2. **End Detection:** Correctly identify stream termination markers (`"done": true` or `data: [END]`).

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
   - Verify execution on non-blocking threads using `Thread.currentThread().getName()`
   - Ensure no blocking operations are used in implementations

2. **Mock Integration:**
   - Use `MockWebServer` or WebTestClient to simulate HTTP responses
   - Test various response scenarios including success, errors, and timeouts
   - Verify correct handling of different content types

3. **Stream Testing:**
   - Test with simulated chunked/SSE responses
   - Verify correct chunk accumulation
   - Validate end-of-stream detection

4. **Stress Testing:**
   - Test with high concurrency to ensure no blocking occurs under load
   - Verify backpressure handling with large responses
   - Test with intermittent delays to simulate network latency

5. **Blocking Code Integration:**
   - Test that blocking code in supplier functions is correctly executed on boundedElastic threads
   - Verify that the main event loop threads are not blocked by database operations

### Example Test Structure

```java
public class LlmClientTests {
    // Test non-blocking behavior
    @Test
    public void testNonBlockingSend() { /* ... */ }
    
    // Test JSON streaming
    @Test
    public void testJsonStreaming() { /* ... */ }
    
    // Test SSE streaming
    @Test
    public void testSseStreaming() { /* ... */ }
    
    // Test error handling
    @Test
    public void testErrorHandling() { /* ... */ }
    
    // Test backpressure
    @Test
    public void testBackpressure() { /* ... */ }
    
    // Test blocking code integration
    @Test
    public void testBlockingCodeIntegration() { /* ... */ }
}
```

## Gradle Setup

```groovy
plugins {
    id 'java-library'
    id 'maven-publish'
}

group = 'com.example'
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

1. **Use handleSend/handleStream/handleStreamSse methods** - Never directly call the private send/stream/streamSse methods.

2. **Keep blocking code minimal** - Only include necessary database calls and processing logic in the supplier function.

3. **Return prepared input** - The supplier should return a fully configured LlmClientInput object.

4. **Handle errors** - Include appropriate error handling within the supplier function.

5. **Avoid nested reactive code** - Don't include Mono/Flux operations inside the supplier function.

6. **Consider timeout handling** - For long-running database operations, consider adding timeouts.

7. **Clean DB connections** - Ensure any database resources are properly closed within the supplier function.

These guidelines ensure a clean separation between potentially blocking preparation code and the non-blocking reactive pipeline for API communication.
