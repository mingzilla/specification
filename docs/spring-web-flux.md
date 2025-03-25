# RxJS and Spring WebFlux/Reactor Comparison
This document shows how Spring WebFlux works.

## Operator and Concept Comparison

| RxJS (Angular)                     | Spring WebFlux/Reactor | Description                                             |
| ---------------------------------- | ---------------------- | ------------------------------------------------------- |
| Observable<T>                      | Flux<T>                | Stream that can emit 0-N elements                       |
| Observable<T> with single emission | Mono<T>                | Stream that emits exactly 0-1 elements                  |
| Subscriber                         | Subscriber             | Entity that receives and processes stream events        |
| subscribe()                        | subscribe()            | Method to begin receiving events from a stream          |
| map()                              | map()                  | Transform each element in the stream                    |
| filter()                           | filter()               | Keep only elements matching a predicate                 |
| mergeMap()                         | flatMap()              | Transform each element into a new stream and flatten    |
| switchMap()                        | switchMap()            | Cancel previous inner streams when a new one arrives    |
| combineLatest()                    | combineLatest()        | Combine latest values whenever any source emits         |
| zip()                              | zip()                  | Combine emissions by matching index/arrival time        |
| concat()                           | concat()               | Append one stream after another sequentially            |
| merge()                            | merge()                | Combine streams as elements arrive (interleaved)        |
| debounceTime()                     | debounce()             | Wait for quiet period before emitting most recent value |
| delay()                            | delayElements()        | Delay emissions by a specified amount of time           |
| catchError()                       | onErrorResume()        | Catch errors and provide fallback logic                 |
| tap()                              | doOnNext()             | Perform side effects without modifying the stream       |
| of(), from()                       | just(), fromIterable() | Create streams from values or collections               |
| takeUntil()                        | takeUntil()            | Take elements until another stream emits                |
| throttleTime()                     | limitRate()            | Limit the rate of emissions                             |
| distinctUntilChanged()             | distinctUntilChanged() | Emit only when value changes from previous              |

## Source/Subject Comparison

| RxJS (Angular)         | Spring WebFlux/Reactor         | Description                                              |
| ---------------------- | ------------------------------ | -------------------------------------------------------- |
| Subject                | Sinks.many()                   | Basic subject without initial value                      |
| BehaviorSubject        | Sinks.many().replay(1)         | Subject that replays the latest value to new subscribers |
| ReplaySubject          | Sinks.many().replay(n)         | Subject that replays n values to new subscribers         |
| AsyncSubject           | Sinks.one()                    | Subject that emits only the last value upon completion   |
| subject.next(value)    | sink.tryEmitNext(value)        | Push a new value into the stream                         |
| subject.error(err)     | sink.tryEmitError(err)         | Push an error into the stream                            |
| subject.complete()     | sink.tryEmitComplete()         | Signal stream completion                                 |
| subject.asObservable() | sink.asFlux() or sink.asMono() | Get a "read-only" stream from the subject                |

## Code Examples

### RxJS (Angular)

```typescript
// Create a source of events
const subject = new BehaviorSubject<string>('initial value');

// Get a read-only stream to subscribe to
const observable = subject.asObservable();

// Subscribe to the stream
observable.subscribe(
  data => console.log('Received:', data),
  error => console.error('Error:', error),
  () => console.log('Completed')
);

// Later, push values into the stream
subject.next('new value');
subject.next('another value');
subject.complete();
```

### Spring WebFlux/Reactor - Flux Example

```java
// Create a source of events
Sinks.Many<String> sink = Sinks.many().multicast().onBackpressureBuffer();

// Get a read-only stream to subscribe to
Flux<String> flux = sink.asFlux();

// Subscribe to the stream
flux.subscribe(
  data -> System.out.println("Received: " + data),
  error -> System.err.println("Error: " + error),
  () -> System.out.println("Completed")
);

// Later, push values into the stream
sink.tryEmitNext("new value");
sink.tryEmitNext("another value");
sink.tryEmitComplete();
```

### Spring WebFlux/Reactor - Mono Example

```java
// Create a one-time emitter sink
Sinks.One<String> sink = Sinks.one();

// Get a read-only Mono to subscribe to
Mono<String> mono = sink.asMono();

// Subscribe to the Mono
mono.subscribe(
  data -> System.out.println("Received: " + data),
  error -> System.err.println("Error: " + error),
  () -> System.out.println("Completed")
);

// Emit a single value (can only be done successfully once)
sink.tryEmitValue("single value");

// Alternative ways to complete the Mono:
// sink.tryEmitEmpty(); // Complete without a value
// sink.tryEmitError(new RuntimeException("Something went wrong")); // Emit an error
```

If you already have a value, and you want it to be merged into the reactive flow:

```java
// Create a Mono with an immediately available value
Mono<String> mono = Mono.just("static value");

// Subscribe to it
mono.subscribe(
    data -> System.out.println("Received: " + data),
    error -> System.err.println("Error: " + error),
    () -> System.out.println("Completed")
);
```

The core concepts are the same in both frameworks - you create streams (Observables/Flux/Mono), transform them with operators, and subscribe to receive the results. Both frameworks handle the asynchronous processing and event propagation behind the scenes.

----

## Comparison of Mono Creation Methods

| Method                | Emits      | Execution Timing | Threading         | Best For                               |
| --------------------- | ---------- | ---------------- | ----------------- | -------------------------------------- |
| `Mono.just(value)`    | Value      | Eager            | Subscriber thread | Simple, immediate values               |
| `Mono.fromCallable()` | Value      | Lazy             | Configurable      | Blocking operations that return values |
| `Mono.fromRunnable()` | Completion | Lazy             | Configurable      | Side effects without return values     |
| `Sinks.One`           | Value      | Deferred         | Any thread        | Programmatic emission control          |
| `Mono.empty()`        | Completion | Immediate        | Subscriber thread | Signaling completion without value     |
| `Mono.error()`        | Error      | Immediate        | Subscriber thread | Immediate error signaling              |
| `Mono.defer()`        | Varies     | Lazy per sub     | Configurable      | Fresh state per subscriber             |

### Key Differences:
- **Eager vs Lazy**: `just()`, `empty()`, `error()` execute immediately; others wait for subscription
- **Value Production**: Only `just()`, `fromCallable()`, and `Sinks.One` emit actual values
- **Thread Control**: `fromCallable()`/`fromRunnable()` + `subscribeOn()` vs `Sinks` direct control
- **Re-execution**: `defer()` creates new Mono per subscription vs others are shared

----

## Conversion Operators

| Situation   | Operator      | Result |
| ----------- | ------------- | ------ |
| Mono → Flux | flatMapMany   | Flux   |
| Flux → Mono | collectList() | Mono   |
| Flux → Mono | reduce()      | Mono   |

### Usage Example

```java
// Mono -> Flux
Mono.fromCallable(inputSupplier::get)
    .subscribeOn(Schedulers.boundedElastic())
    .flatMapMany(input -> {
        return webClient.post().uri(input.url()).retrieve()
            .bodyToFlux(String.class)
            // ... rest of Flux operators
    })

// Flux -> Mono: collectList()
Mono<List<Integer>> monoList = Flux.just(1, 2, 3, 4, 5).collectList();

// Flux -> Mono: reduce()
Mono<Integer> sumMono = Flux.just(1, 2, 3, 4, 5).reduce(0, (acc, next) -> acc + next);

```

----

## Spring WebFlux Internals: How Reactive Endpoints Actually Work

### 1. How Spring Calls Your Controller

```java
// Spring internally creates your controller
ChatController controller = new ChatController(llmClient);

// Controller returns a Flux which is just a description of what will happen
Flux<LlmClientOutputChunk> flux = controller.stream(request);

// Spring WebFlux subscribes to that Flux
flux.subscribe(chunk -> {
    // Spring's internal HTTP response writer writes each chunk to client
});
```

### 2. What Your Controller Returns

Controller.stream() immediately returns the below ...bodyToFlux(). Note: this doesn't execute the HTTP request. It only builds the behaviour.

```java
webClient.post()
    .uri(input.url())
    .bodyValue(input.body())
    .headers(headers -> headers.putAll(input.headers()))
    .retrieve()
    .bodyToFlux(String.class)
```

### 3. Inside WebClient's implementation (simplified)
- `Sinks.Many<String> responseSink = Sinks.many().multicast().onBackpressureBuffer()` - Subject subject
- Future: `responseSink.tryEmitNext(chunk)` - subject.next()
- `return responseSink.asFlux()` - subject.asObservable()

```java
private Flux<String> bodyToFlux(String.class) {
    // Create a sink for HTTP response data
    Sinks.Many<String> responseSink = Sinks.many().multicast().onBackpressureBuffer();
    
    // Set up HTTP connection with Netty - The below is oversimplified for understanding, the code can be from the class outside of this method
    // The point is, something runs HttpClient.send(), and responseSink.tryEmitNext(chunk) is in a callback to be run in the future
    HttpClient.create().post().uri(uri).send(...)
        .responseHandler(response -> {
            response.onData(buffer -> {
                String chunk = buffer.toString(StandardCharsets.UTF_8);
                responseSink.tryEmitNext(chunk);  // HERE'S THE EMIT!
            });
            
            response.onComplete(() -> responseSink.tryEmitComplete());
        })
        .connect();  // Actually initiate the connection when subscribed

    return responseSink.asFlux();  // This is what bodyToFlux() returns
}
```

The key insight: the network request isn't made until something subscribes to the Flux. When data arrives from the network, callbacks emit values to the sink, which then flow through your reactive pipeline back to the client.

## Technique to run blocking code as part of the reactive process

```java
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
     * Safely handles streaming a request with potentially blocking preparation logic
     * This method should be used instead of stream() to ensure proper reactive patterns
     * 
     * @param inputSupplier A supplier function that provides the LlmClientInput, may contain blocking code
     * @return A Flux that emits each chunk from the streaming response
     */
    public Flux<LlmClientOutputChunk> handleStream(Supplier<LlmClientInput> inputSupplier) {
        // Mono.fromCallable( /* blocking code */ ).subscribeOn(Schedulers.boundedElastic()) runs blocking code in a separate thread elegantly
        return Mono.fromCallable(inputSupplier::get)
            .subscribeOn(Schedulers.boundedElastic())
            .flatMapMany(this::stream);
    }

    private Flux<LlmClientOutputChunk> stream(LlmClientInput input) {
        return webClient.post()
            .uri(input.url())
            .bodyValue(input.body())
            .headers(headers -> headers.putAll(input.headers()))
            .retrieve()
            .bodyToFlux(String.class) // internally calls `HttpClient.create().post().uri(uri).send(...)` to start the request
            .filter(line -> !line.isEmpty())
            .map(this::parseChunk)
            .takeUntil(LlmClientOutputChunk::done);
    }
```