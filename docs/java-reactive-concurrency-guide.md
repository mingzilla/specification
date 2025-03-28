# Java Concurrency & Project Reactor: A Comprehensive Guide

## Java Concurrent Framework vs Project Reactor Overview

```
+--------------------------------------+    +------------------------------------+
|        java.util.concurrent          |    |         Project Reactor            |
+--------------------------------------+    +------------------------------------+
|                                      |    |                                    |
|  +-------------+  +---------------+  |    |  +-------------+  +-------------+  |
|  |  Executors  |  |ExecutorService|  |    |  | Schedulers  |  | Scheduler   |  |
|  |-------------|  |---------------|  |    |  |-------------|  |-------------|  |
|  | Factory     |  | Interface     |  |    |  | Factory     |  | Interface   |  |
|  | methods to  |  | for thread    |  |    |  | methods for |  | for async   |  |
|  | create      |  | pool mgmt     |  |    |  | scheduler   |  | execution   |  |
|  | thread pools|  |               |  |    |  | instances   |  | in streams  |  |
|  +-------------+  +---------------+  |    |  +-------------+  +-------------+  |
|                                      |    |                                    |
+--------------------------------------+    +------------------------------------+
                  |                                          ^
                  |                                          |
                  +------------------------------------------+
                            Built on top of / Extends
```

## Java Concurrency vs Project Reactor: Method Comparison

| Category                | Java Executors Method           | Project Reactor Schedulers Method | Purpose                    | Thread Lifecycle                                                                               | Best For                                 |
| ----------------------- | ------------------------------- | --------------------------------- | -------------------------- | ---------------------------------------------------------------------------------------------- | ---------------------------------------- |
| **Fixed-size Pool**     | `newFixedThreadPool(n)`         | `parallel()`                      | Limited thread pool        | Java: Permanent until shutdown<br>Reactor: Permanent                                           | CPU-bound tasks, parallel processing     |
| **Elastic Pool**        | `newCachedThreadPool()`         | `boundedElastic()`                | Scalable thread pool       | Java: Unlimited growth, 60s idle timeout<br>Reactor: Bounded growth (CPU×10), 60s idle timeout | I/O operations, blocking calls           |
| **Single Thread**       | `newSingleThreadExecutor()`     | `single()`                        | One worker thread          | Java: Permanent until shutdown<br>Reactor: Permanent                                           | Sequential execution, ordered operations |
| **Immediate Execution** | N/A (would be direct execution) | `immediate()`                     | No thread switch           | N/A (current thread)                                                                           | Testing, avoiding context switches       |
| **Timer**               | `newScheduledThreadPool(n)`     | `newParallel("timer", n)`         | Delayed/periodic execution | Java: Permanent until shutdown<br>Reactor: Permanent                                           | Scheduling tasks, timeouts               |
| **Custom**              | `new ThreadPoolExecutor(...)`   | `fromExecutorService(exec)`       | Custom configuration       | Depends on configuration                                                                       | Special threading requirements           |

## Usage Examples

### Java Executors
```java
// Fixed thread pool
ExecutorService fixedPool = Executors.newFixedThreadPool(4);
fixedPool.submit(() -> processCpuIntensiveTask());

// Cached thread pool
ExecutorService cachedPool = Executors.newCachedThreadPool();
cachedPool.submit(() -> handleRequest());

// Single thread executor
ExecutorService singleThread = Executors.newSingleThreadExecutor();
singleThread.submit(() -> processInOrder());

// Always close executors when done
fixedPool.shutdown();
```

### Project Reactor Schedulers
```java
// Parallel scheduler
Flux.range(1, 1000)
    .publishOn(Schedulers.parallel())
    .map(i -> performCalculation(i))
    .subscribe();

// BoundedElastic scheduler
Mono.fromCallable(() -> blockingDatabaseCall())
    .subscribeOn(Schedulers.boundedElastic())
    .subscribe(data -> process(data));

// Single scheduler
Flux.range(1, 100)
    .publishOn(Schedulers.single())
    .map(i -> processSequentially(i))
    .subscribe();
```

## Terminologies Comparison

Here's a side-by-side comparison of Java Reactor and JavaScript RxJS equivalents:

| Java (Project Reactor)                     | JavaScript (RxJS)                  | Purpose                                     |
| ------------------------------------------ | ---------------------------------- | ------------------------------------------- |
| `Mono`                                     | `Observable` (single value)        | Container for 0-1 async values              |
| `Flux`                                     | `Observable` (multiple values)     | Container for 0-n async values              |
| `Mono.fromCallable()`                      | `from(new Promise())` or `defer()` | Create observable from function call        |
| `subscribeOn(Schedulers.boundedElastic())` | `observeOn(asyncScheduler)`        | Control which thread pool executes the work |
| `subscribe(data -> process(data))`         | `subscribe(data => process(data))` | Terminal operation to start the chain       |
| `Schedulers.boundedElastic()`              | `asyncScheduler`                   | Thread pool for I/O operations              |
| `Schedulers.parallel()`                    | `queueScheduler`                   | Thread pool for CPU-bound work              |

Complete example conversion:

```java
// Java - Project Reactor
Mono.fromCallable(() -> blockingDatabaseCall())
    .subscribeOn(Schedulers.boundedElastic())
    .subscribe(data -> process(data));
```

```javascript
// JavaScript (RxJS)
import { defer, from, observeOn, asyncScheduler } from 'rxjs';
defer(() => from(blockingDatabaseCall())) // from: Similar to `Observable.from()`
    .pipe(observeOn(asyncScheduler))
    .subscribe(data => process(data));
```

Here's the RxJS comparison with the WHAT values filled in:

| Component         | RxJS Code                                                       | What it is                                                                           |
| ----------------- | --------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| Source creator    | `defer(() => from(blockingDatabaseCall()))`                     | Creates a lazy observable that runs `blockingDatabaseCall()` only when subscribed to |
| Operator          | `from(fetch('/api/data')).subscribe(resp => console.log(resp))` | from - async - converts promises into observables                                    |
| Operator          | `from([1, 2, 3]).subscribe(num => console.log(num))`            | from - sync - converts arrays into Observables that emit each array element          |
| Operator          | `Observable.pipe(observeOn(asyncScheduler))`                    | Pipe method to apply operators to the observable                                     |
| Thread management | `observeOn(asyncScheduler)`                                     | Controls which scheduler/thread processes emissions                                  |
| Thread pool       | `asyncScheduler`                                                | RxJS's asynchronous scheduler, an optimised `setTimeout()`                           |
| Consumer          | `subscribe(data => process(data))`                              | Terminal operation that starts the observable chain                                  |


## Key Differences

1. **Resource Management**: 
   - Executors require explicit shutdown
   - Schedulers handle cleanup automatically when unused

2. **Bounded Resources**:
   - CachedThreadPool can grow unbounded (risk of resource exhaustion)
   - boundedElastic has strict upper limits on thread count

3. **Reactive Integration**:
   - Schedulers preserve reactive context and backpressure
   - Executors have no built-in backpressure handling

4. **Execution Model**:
   - Executors focus on executing discrete tasks
   - Schedulers focus on when/where to process reactive streams

## Project Reactor Operators: `subscribeOn`, `publishOn`, and `subscribe`

| Operator                   | Primary Purpose                                  | Thread Execution                       | Multiple Calls                          | Scheduler Integration                                                              |
| -------------------------- | ------------------------------------------------ | -------------------------------------- | --------------------------------------- | ---------------------------------------------------------------------------------- |
| **subscribeOn(Scheduler)** | Controls subscription and source emission thread | Affects upstream operators and source  | Only first call has effect              | `Mono.fromCallable(() -> blockingCall()).subscribeOn(Schedulers.boundedElastic())` |
| **publishOn(Scheduler)**   | Controls downstream operator execution thread    | Affects only operators after publishOn | Each call changes thread for downstream | `Flux.range(1, 10).publishOn(Schedulers.parallel()).map(...)`                      |
| **subscribe()**            | Initiates reactive chain execution               | Executes on calling thread by default  | Terminal operation - starts chain       | `flux.subscribe(data -> {}, error -> {}, () -> {})`                                |

```
// subscribeOn affects entire chain upstream
+-----------------------------------------------------+
|                                                     |
| [subscribeOn(boundedElastic)] --> [map] --> [filter]|
|       ^                                             |
|       |                                             |
| Everything upstream runs on boundedElastic thread   |
+-----------------------------------------------------+

// publishOn affects only operators downstream
+-----------------------------------------------------+
|                                                     |
| [map] --> [publishOn(parallel)] --> [filter]        |
|                   |                    |            |
|                   v                    v            |
|           Only downstream ops run on parallel thread|
+-----------------------------------------------------+
```

## Common Scheduler Integration Patterns

| Pattern                   | Code Example                                                                                                                                                                        | Description                                                    | Best For                                     |
| ------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------- | -------------------------------------------- |
| **Blocking Operations**   | `Mono.fromCallable(() -> blockingDbCall())`<br>`.subscribeOn(Schedulers.boundedElastic())`                                                                                          | Moves blocking operation to boundedElastic thread              | Database calls, file I/O, external API calls |
| **Parallel Processing**   | `Flux.range(1, 1000)`<br>`.parallel()`<br>`.runOn(Schedulers.parallel())`<br>`.map(i -> compute(i))`<br>`.sequential()`                                                             | Splits work across parallel threads                            | CPU-intensive calculations                   |
| **UI Thread Management**  | `uiEventFlux`<br>`.publishOn(Schedulers.single())`<br>`.map(this::processEvent)`<br>`.publishOn(Schedulers.fromExecutor(uiExecutor))`                                               | Processes on background thread, publishes results on UI thread | Desktop/mobile applications                  |
| **Mixed Threading Model** | `Flux.range(1, 100)`<br>`.publishOn(Schedulers.parallel())`<br>`.map(this::heavyComputation)`<br>`.publishOn(Schedulers.boundedElastic())`<br>`.flatMap(id -> externalApiCall(id))` | Uses appropriate scheduler for each operation type             | Complex processing pipelines                 |

## Thread Scheduling in LlmClient.java

```java
// From llm-client-java.md
public Flux<LlmClientOutputChunk> handleStream(Supplier<LlmClientInput> inputSupplier) {
    return Mono.fromCallable(inputSupplier::get)
            .subscribeOn(Schedulers.boundedElastic())
            .flatMapMany(this::stream);
}
```

This code demonstrates proper reactive handling of potentially blocking operations:

1. `Mono.fromCallable(inputSupplier::get)` - Creates a Mono that executes the supplier function when subscribed to
2. `.subscribeOn(Schedulers.boundedElastic())` - Moves execution to boundedElastic thread pool to handle potentially blocking operations
3. `.flatMapMany(this::stream)` - Once input is obtained, transforms to a stream of chunks

The `.subscribeOn(Schedulers.boundedElastic())` specifically:
- Ensures that any blocking code in the inputSupplier won't block reactive threads
- Uses boundedElastic which is designed for I/O operations
- Demonstrates the pattern of isolating blocking code in reactive applications

## Key Concepts

1. **subscribeOn** - Controls where the **subscription** happens and affects the entire upstream chain:
   - Only the first `subscribeOn()` in the chain has an effect
   - Used to move blocking operations off reactive threads

2. **publishOn** - Controls where **operators after it** execute:
   - Each `publishOn()` affects only downstream operators
   - Can be used multiple times to switch execution contexts

3. **subscribe** - The terminal operation that:
   - Starts the actual data flow (lazy execution model)
   - Takes three optional callbacks: `onNext`, `onError`, `onComplete`
   - Returns a `Disposable` that can be used to cancel the subscription

4. **Thread Switching Cost** - Changing threads has overhead:
   - Only use `subscribeOn`/`publishOn` when necessary
   - Group operations that can run on the same thread
