# RxJS and Spring WebFlux/Reactor Comparison
This document shows how Spring WebFlux works.

## Operator and Concept Comparison Simplified

| RxJS (Angular)      | Code                                        | Spring WebFlux/Reactor    | Code                                                                        |
| ------------------- | ------------------------------------------- | ------------------------- | --------------------------------------------------------------------------- |
| Subject             | `const subject = new Subject<string>('hi')` | Sinks.many() / Sink.one() | `Sinks.Many<String> sink = Sinks.many().multicast().onBackpressureBuffer()` |
| Observable<T>       | `const observable = subject.asObservable()` | Flux<T> / Mono<T>         | `Flux<String> flux = sink.asFlux()`                                         |
| subscribe()         | `observable.subscribe(goodFn, badFn)`       | subscribe()               | `flux.subscribe(goodFn, badFn)`                                             |
| subject.next(value) | `subject.next('hi')`                        | sink.tryEmitNext(value)   | `sink.tryEmitNext("hi")`                                                    |

## Code Examples

### RxJS (Angular)

```typescript
const subject = new BehaviorSubject<string>('initial value');
const observable = subject.asObservable();
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
Sinks.Many<String> sink = Sinks.many().multicast().onBackpressureBuffer();
Flux<String> flux = sink.asFlux();
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

#### Using Runnable/Callable
```java
Mono<String> mono = Mono.fromCallable(() -> {
    System.out.println("Hello");
    return "World";
});

// Pipeline setup (nothing executes yet)
Mono<String> mapped = mono.map(String::toUpperCase);  

// THIS triggers the actual execution
mono.subscribe(item -> System.out.println(item)); // Output: "Hello", \n "World"
// Or do this to trigger the execution:
mapped.subscribe(item -> System.out.println(item)); // Output: "Hello", \n "WORLD"
// Or do this to trigger the execution:
String txt1 = mono.block(); // Output: "Hello", returns "World" and assign to txt1
// or do this to trigger the execution:
String txt2 = mapped.block(); // Output: "Hello", returns "WORLD" and assign to txt2
```

### Spring WebFlux/Reactor - Mono Example

```java
Sinks.One<String> sink = Sinks.one();
Mono<String> mono = sink.asMono();
mono.subscribe(
  data -> System.out.println("Received: " + data),
  error -> System.err.println("Error: " + error),
  () -> System.out.println("Completed")
);

// Emit a single value (can only be done successfully once)
sink.tryEmitValue("single value");
// Alternative ways to complete the Mono:
sink.tryEmitEmpty(); // Complete without a value
sink.tryEmitError(new RuntimeException("Something went wrong")); // Emit an error
```

If you already have a value, and you want it to be merged into the reactive flow:

```java
Mono<String> mono = Mono.just("static value");
mono.subscribe(
    data -> System.out.println("Received: " + data),
    error -> System.err.println("Error: " + error),
    () -> System.out.println("Completed")
);
```

## Operator and Concept Comparison

### 1. Core Stream Components

| RxJS (Angular)                  | Spring WebFlux/Reactor         | Description                                                      |
| ------------------------------- | ------------------------------ | ---------------------------------------------------------------- |
| Observable<T>                   | Flux<T>                        | Stream that can emit 0-N elements                                |
| Observable<T> (single emission) | Mono<T>                        | Stream that emits exactly 0-1 elements                           |
| Subscriber                      | Subscriber                     | `flux.subscribe(new Subscriber(goodFn, badFn))`                  |
| subscribe()                     | subscribe()                    | `flux.subscribe(goodFn, badFn)` Subscriber is implicitly created |
|                                 |                                |                                                                  |
| Subject                         | Sinks.many()                   | Basic subject without initial value                              |
| BehaviorSubject                 | Sinks.many().replay(1)         | Subject that replays the latest value to new subscribers         |
| ReplaySubject                   | Sinks.many().replay(n)         | Subject that replays n values to new subscribers                 |
| AsyncSubject                    | Sinks.one()                    | Subject that emits only the last value upon completion           |
|                                 |                                |                                                                  |
| subject.next(value)             | sink.tryEmitNext(value)        | Push a new value into the stream                                 |
| subject.error(err)              | sink.tryEmitError(err)         | Push an error into the stream                                    |
| subject.complete()              | sink.tryEmitComplete()         | Signal stream completion                                         |
| subject.asObservable()          | sink.asFlux() or sink.asMono() | Get a "read-only" stream from the subject                        |

### 2. Basic Transformations

| RxJS (Angular) | Spring WebFlux/Reactor | Description                                             | Example                                                                                                                                                        |
| -------------- | ---------------------- | ------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| map()          | map()                  | Transform each element in the stream                    | RxJS: `of(1, 2, 3).pipe(map(x => x * 2))` // 2, 4, 6<br>Reactor: `Flux.just(1, 2, 3).map(x -> x * 2)`                                                          |
| filter()       | filter()               | Keep only elements matching a predicate                 | RxJS: `of(1, 2, 3, 4).pipe(filter(x => x % 2 === 0))` // 2, 4<br>Reactor: `Flux.just(1, 2, 3, 4).filter(x -> x % 2 == 0)`                                      |
| mergeMap()     | flatMap()              | Transform each element into a new stream and flatten    | RxJS: `of(1, 2).pipe(mergeMap(x => of(x, x+1)))` // 1, 2, 2, 3<br>Reactor: `Flux.just(1, 2).flatMap(x -> Flux.just(x, x+1))`                                   |
| zip()          | zip()                  | Combine emissions by matching index/arrival time        | RxJS: `zip(of('a', 'b'), of(1, 2))` // ['a',1], ['b',2]<br>Reactor: `Flux.zip(Flux.just("a", "b"), Flux.just(1, 2))`                                           |
| of()           | just()                 | Create streams from direct values                       | RxJS: `of(1, 2, 3)` // emits: 1, 2, 3<br>Reactor: `Flux.just(1, 2, 3)`                                                                                         |
| from()         | fromIterable()         | Create streams from collections or other reactive types | RxJS: `from([1, 2, 3])` // 1, 2, 3<br>Reactor: `Flux.fromIterable(Arrays.asList(1, 2, 3))`                                                                     |
| takeUntil()    | takeUntil()            | Take elements until another stream emits                | RxJS: `interval(100).pipe(takeUntil(timer(500)))` // 0,1,2,3<br>Reactor: `Flux.interval(Duration.ofMillis(100)).takeUntil(Flux.timer(Duration.ofMillis(500)))` |

### 3. Flow Control Operations

| RxJS (Angular)  | Spring WebFlux/Reactor         | Description                                                                               | Example                                                                                                                                                                                                                                             |
| --------------- | ------------------------------ | ----------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| switchMap()     | switchMap()                    | Cancel previous inner streams when a new one arrives                                      | RxJS: `clicks$.pipe(switchMap(() => interval(500)))` // Restarts interval on each click<br>Reactor: `clickFlux.switchMap(click -> Flux.interval(Duration.ofMillis(500)))`                                                                           |
| combineLatest() | combineLatest()                | Combine latest values whenever any source emits                                           | RxJS: `combineLatest([a$, b$], (a, b) => a + b)` // Sum of latest values<br>Reactor: `Flux.combineLatest(fluxA, fluxB, (a, b) -> a + b)`                                                                                                            |
| concat()        | concat()                       | Append one stream after another sequentially                                              | RxJS: `concat(of(1, 2), of(3, 4))` // 1,2,3,4<br>Reactor: `Flux.concat(Flux.just(1, 2), Flux.just(3, 4))`                                                                                                                                           |
| merge()         | merge()                        | Combine streams as elements arrive (interleaved)                                          | RxJS: `merge(interval(500).pipe(map(() => 'A')), interval(300).pipe(map(() => 'B')))` // Interleaved A's and B's<br>Reactor: `Flux.merge(Flux.interval(Duration.ofMillis(500)).map(i -> "A"), Flux.interval(Duration.ofMillis(300)).map(i -> "B"))` |
| N/A             | flatMap() on Flux<Mono<T>>     | Flattens each Mono emitted by the Flux into a single stream of T                          | Reactor: `Flux.just(Mono.just("a"), Mono.just("b")).flatMap(mono -> mono)` // "a", "b"                                                                                                                                                              |
| N/A             | flatMapMany() on Mono<Flux<T>> | Flattens the Flux inside the Mono, emitting each item in the flattened Flux               | Reactor: `Mono.just(Flux.just("a", "b")).flatMapMany(flux -> flux)` // "a", "b"                                                                                                                                                                     |
| N/A             | flatMapMany() on Mono<T>       | Transforms the value into a Flux                                                          | Reactor: `Mono.just("a").flatMapMany(a -> Flux.just(a, a + a))` // "a", "aa"                                                                                                                                                                        |
| N/A             | collectList() on Flux<T>       | Collects all items emitted by the Flux into a Mono<List<T>>                               | Reactor: `Flux.just(1, 2, 3).collectList()` // Mono<List<Integer>> containing [1, 2, 3]                                                                                                                                                             |
| reduce()        | reduce() on Flux<T>            | Reduces the items emitted by the Flux into a single Mono<T> using an accumulator function | RxJS: `of(1, 2, 3).pipe(reduce((acc, val) => acc + val, 0))` // 6<br>Reactor: `Flux.just(1, 2, 3).reduce(0, (acc, val) -> acc + val)` // Mono<Integer> containing 6                                                                                 |

### 4. Timing and Rate Management

| RxJS (Angular) | Spring WebFlux/Reactor | Description                                                | Example                                                                                                                                                         |
| -------------- | ---------------------- | ---------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| debounceTime() | debounce()             | Wait for quiet period before emitting most recent value    | RxJS: `searchInput$.pipe(debounceTime(300))` // Only emit after 300ms of inactivity<br>Reactor: `searchInputFlux.debounce(Duration.ofMillis(300))`              |
| delay()        | delayElements()        | Delay emissions by a specified amount of time              | RxJS: `of(1, 2, 3).pipe(delay(1000))` // Emit after 1s delay<br>Reactor: `Flux.just(1, 2, 3).delayElements(Duration.ofSeconds(1))`                              |
| throttleTime() | limitRate()            | Limit the rate of emissions                                | RxJS: `clicks$.pipe(throttleTime(1000))` // Max 1 click per second<br>Reactor: `clicksFlux.limitRate(10)` // Request max 10 at a time                           |
| interval()     | interval()             | Create a stream that emits sequential numbers periodically | RxJS: `interval(1000)` // Emit 0,1,2,... every 1s<br>Reactor: `Flux.interval(Duration.ofSeconds(1))`                                                            |
| timeout()      | timeout()              | Error if no emission within specified duration             | RxJS: `of(1).pipe(delay(2000), timeout(1000))` // Error after 1s<br>Reactor: `Flux.just(1).delayElements(Duration.ofSeconds(2)).timeout(Duration.ofSeconds(1))` |

### 5. Error Handling

| RxJS (Angular)      | Spring WebFlux/Reactor | Description                                              | Example                                                                                                                                                   |
| ------------------- | ---------------------- | -------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| catchError()        | onErrorResume()        | Catch errors and provide fallback logic                  | RxJS: `obs$.pipe(catchError(err => of('fallback')))` // Return fallback on error<br>Reactor: `flux.onErrorResume(e -> Flux.just("fallback"))`             |
| retry()             | retry()                | Resubscribe to the source after an error occurs          | RxJS: `http$.pipe(retry(3))` // Retry failed request 3 times<br>Reactor: `webClient.get().uri("/api").retrieve().bodyToMono(String.class).retry(3)`       |
| onErrorResumeNext() | onErrorComplete()      | Continue with next observable when error occurs          | RxJS: `onErrorResumeNext([a$, b$])` // If a$ fails, switch to b$<br>Reactor: `fluxA.onErrorComplete().concatWith(fluxB)`                                  |
| finalize()          | doFinally()            | Perform action when stream completes, errors, or cancels | RxJS: `obs$.pipe(finalize(() => console.log('Done')))` // Log when finished<br>Reactor: `flux.doFinally(signal -> System.out.println("Done: " + signal))` |

### 6. Utility Operations

| RxJS (Angular)         | Spring WebFlux/Reactor | Description                                            | Example                                                                                                                                                                                          |
| ---------------------- | ---------------------- | ------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| tap()                  | doOnNext()             | Perform side effects without modifying the stream      | RxJS: `of(1, 2, 3).pipe(tap(x => console.log(x)))` // Log values as they emit<br>Reactor: `Flux.just(1, 2, 3).doOnNext(x -> System.out.println(x))`                                              |
| distinctUntilChanged() | distinctUntilChanged() | Emit only when value changes from previous             | RxJS: `of(1, 1, 2, 2, 3).pipe(distinctUntilChanged())` // 1,2,3<br>Reactor: `Flux.just(1, 1, 2, 2, 3).distinctUntilChanged()`                                                                    |
| share()                | share()                | Share a single subscription among multiple subscribers | RxJS: `const shared$ = http$.pipe(share())` // Multiple subscribers share one HTTP call<br>Reactor: `Flux<Data> shared = webClient.get().uri("/data").retrieve().bodyToFlux(Data.class).share()` |
| startWith()            | startWith()            | Prepend values to the beginning of a stream            | RxJS: `of(3, 4).pipe(startWith(1, 2))` // 1,2,3,4<br>Reactor: `Flux.just(3, 4).startWith(1, 2)`                                                                                                  |
| scan()                 | scan()                 | Apply accumulator function to each value (like reduce) | RxJS: `of(1, 2, 3).pipe(scan((acc, val) => acc + val, 0))` // 1,3,6<br>Reactor: `Flux.just(1, 2, 3).scan(0, (acc, val) -> acc + val)` // 1,3,6                                                   |

### 7. Concurrency Management

| RxJS (Angular)          | Spring WebFlux/Reactor      | Description                                                |
| ----------------------- | --------------------------- | ---------------------------------------------------------- |
| observeOn()             | publishOn()                 | Specify scheduler for downstream operations                |
| subscribeOn()           | subscribeOn()               | Specify scheduler for subscription and upstream operations |
| asyncScheduler          | Schedulers.boundedElastic() | Schedule for I/O-bound work                                |
| queueScheduler          | Schedulers.parallel()       | Schedule for CPU-bound work                                |
| animationFrameScheduler | N/A                         | Schedule work with browser animation frame (RxJS specific) |

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

| **Operator**        | **Input Type**  |     | **Output Type** | **Description**                                                                                                    |
| ------------------- | --------------- | --- | --------------- | ------------------------------------------------------------------------------------------------------------------ |
| **`flatMap`**       | `Flux<Mono<T>>` | →   | `Flux<T>`       | Flattens each `Mono` emitted by the `Flux` into a single stream of `T`.                                            |
| **`flatMapMany`**   | `Mono<Flux<T>>` | →   | `Flux<T>`       | Flattens the `Flux` inside the `Mono`, emitting each item in the flattened `Flux`.                                 |
| **`flatMapMany`**   | `Mono<T>`       | →   | `Flux<T>`       | Flattens the `Flux` inside the `Mono`, emitting each item in the flattened `Flux`.                                 |
| **`collectList()`** | `Flux<T>`       | →   | `Mono<List<T>>` | Collects all items emitted by the `Flux` into a `List<T>` and emits it as a single `Mono<List<T>>`.                |
| **`reduce()`**      | `Flux<T>`       | →   | `Mono<T>`       | Reduces the items emitted by the `Flux` into a single value of type `T` by applying a binary accumulator function. |

---

### **Detailed Example of Each:**

1. **`flatMap` Example:**
   ```java
   Flux.just(1, 2, 3)
       .flatMap(x -> Mono.just(x * 2))  // `Mono<Integer>` for each item
       .subscribe(System.out::println);  // Outputs: 2, 4, 6
   ```
   - Transforms `Flux<Mono<Integer>>` into `Flux<Integer>` by flattening.

2. **`flatMapMany` Example:**
   ```java
   Mono.just(Flux.just(1, 2, 3))
       .flatMapMany(flux -> flux)  // Flattens `Flux` inside the `Mono`
       .subscribe(System.out::println);  // Outputs: 1, 2, 3
   ```
   - Transforms `Mono<Flux<T>>` into `Flux<T>` by extracting and flattening the `Flux`.

3. **`flatMapMany` Example:**
   ```java
   Mono.just(List.of(1, 2, 3, 4))
       .flatMapMany(List<Integer> list -> { // Or just `.flatMapMany(Flux::fromIterable)`
           return Flux.fromIterable(list);
       })  // Flattens the list into individual elements
       .subscribe(System.out::println);  // Output: 1, 2, 3, 4
   ```
   - Transforms `Mono<List<Object>>` to `Flux<Object>`.

4. **`collectList()` Example:**
   ```java
   Flux.just(1, 2, 3)
       .collectList()
       .subscribe(System.out::println);  // Outputs: [1, 2, 3]
   ```
   - Collects the items from `Flux<Integer>` and emits them as `Mono<List<Integer>>`.

5. **`reduce()` Example:**
   ```java
   Flux.just(1, 2, 3)
       .reduce((a, b) -> a + b)  // Reduces the sequence by summing
       .subscribe(System.out::println);  // Outputs: 6
   ```
   - Applies the reduction function (e.g., summing) and emits a single value as `Mono<T>`.

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