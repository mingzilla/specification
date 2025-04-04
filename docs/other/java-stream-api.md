# Java Stream API Cheat Sheet

## Introduction
The Java Stream API was introduced in Java 8 as part of the java.util.stream package. It enables functional-style operations on streams of elements, such as map-reduce transformations on collections.

## Creating Streams

```java
// From a Collection
List<String> list = Arrays.asList("a", "b", "c");
Stream<String> stream = list.stream();

// From an array
String[] array = {"a", "b", "c"};
Stream<String> stream = Arrays.stream(array);

// Stream.of
Stream<String> stream = Stream.of("a", "b", "c");

// Empty stream
Stream<String> emptyStream = Stream.empty();

// Infinite streams
Stream<Integer> infiniteStream = Stream.iterate(0, n -> n + 1);
Stream<Double> randomStream = Stream.generate(Math::random);

// IntStream, LongStream, DoubleStream for primitives
IntStream intStream = IntStream.range(1, 5); // 1, 2, 3, 4
IntStream intStream = IntStream.rangeClosed(1, 5); // 1, 2, 3, 4, 5
```

## Intermediate Operations
These operations transform a stream into another stream and are lazy (not executed until a terminal operation is invoked).

### Filtering
```java
// Filter elements that match the predicate
Stream<T> filtered = stream.filter(element -> element.startsWith("a"));

// Get first n elements
Stream<T> limited = stream.limit(10);

// Skip first n elements
Stream<T> skipped = stream.skip(5);

// Remove duplicates (based on .equals())
Stream<T> distinct = stream.distinct();
```

### Mapping
```java
// Apply function to each element
Stream<R> mapped = stream.map(element -> element.toUpperCase());

// Flatten nested streams
Stream<R> flatMapped = stream.flatMap(element -> element.getChildren().stream());

// For primitive streams
IntStream intStream = stream.mapToInt(element -> element.length());
LongStream longStream = stream.mapToLong(element -> element.getValue());
DoubleStream doubleStream = stream.mapToDouble(element -> element.getPrice());
```

### Sorting
```java
// Natural order (elements must implement Comparable)
Stream<T> sorted = stream.sorted();

// Custom comparator
Stream<T> sorted = stream.sorted((e1, e2) -> e1.length() - e2.length());
Stream<T> sorted = stream.sorted(Comparator.comparing(User::getName));

// Reversed order
Stream<T> sorted = stream.sorted(Comparator.comparing(User::getAge).reversed());
```

### Peeking (for debugging)
```java
// Execute action on each element without modifying stream
Stream<T> peeked = stream.peek(element -> System.out.println(element));
```

## Terminal Operations
These operations produce a result or a side-effect and cause the stream pipeline to be executed.

### Matching
```java
boolean allMatch = stream.allMatch(element -> element.length() > 0);
boolean anyMatch = stream.anyMatch(element -> element.length() > 5);
boolean noneMatch = stream.noneMatch(element -> element.length() > 10);
```

### Finding
```java
Optional<T> first = stream.findFirst();
Optional<T> any = stream.findAny(); // Useful for parallel streams
```

### Collecting
```java
// To List
List<T> list = stream.collect(Collectors.toList());

// To Set
Set<T> set = stream.collect(Collectors.toSet());

// To Array
// Generic object array - IMPORTANT: This always returns Object[] regardless of stream source type
Object[] objectArray = stream.toArray();  // Even if stream comes from List<User>, this returns Object[], not User[]

// Typed array using generator function - needed for proper type preservation
String[] stringArray = stream.toArray(String[]::new);
User[] userArray = userStream.toArray(User[]::new);  // Correct way to get User[] from a List<User>

// Alternative collecting to array (less common)
String[] stringArray = stream.collect(Collectors.toArray(String[]::new));

// Converting primitive streams to arrays
int[] intArray = intStream.toArray();
long[] longArray = longStream.toArray();
double[] doubleArray = doubleStream.toArray();

// To Map
Map<K, V> map = stream.collect(Collectors.toMap(
    element -> element.getId(),      // Key mapper
    element -> element,              // Value mapper
    (existing, replacement) -> existing  // Merge function for duplicates
));

// Joining strings
String joined = stream.map(Object::toString)
    .collect(Collectors.joining(", ", "[", "]"));

// Grouping
Map<Department, List<Employee>> byDept = 
    employees.stream()
             .collect(Collectors.groupingBy(Employee::getDepartment));

// Partitioning (special case of grouping with boolean predicate)
Map<Boolean, List<Employee>> partitioned = 
    employees.stream()
             .collect(Collectors.partitioningBy(e -> e.getSalary() > 50000));

// Counting
long count = stream.collect(Collectors.counting());

// Summing
int total = stream.collect(Collectors.summingInt(Product::getPrice));

// Statistics (count, sum, min, max, average)
IntSummaryStatistics stats = 
    stream.collect(Collectors.summarizingInt(Product::getPrice));
```

### Reducing
```java
// With identity and accumulator
Optional<T> reduced = stream.reduce((a, b) -> a + b);

// With identity and accumulator
T reduced = stream.reduce(identity, (a, b) -> a + b);

// With identity, accumulator, and combiner (for parallel streams)
U reduced = stream.reduce(
    identity,
    (result, element) -> accumulator.apply(result, mapper.apply(element)),
    (result1, result2) -> combiner.apply(result1, result2)
);
```

### Other Terminal Operations
```java
// Count elements
long count = stream.count();

// Get min/max element
Optional<T> min = stream.min(Comparator.naturalOrder());
Optional<T> max = stream.max(Comparator.comparing(User::getAge));

// Convert to array
Object[] array = stream.toArray();
String[] array = stream.toArray(String[]::new);

// Execute action for each element (for side effects)
stream.forEach(element -> System.out.println(element));

// For parallel streams - no guaranteed order
stream.parallel().forEach(element -> System.out.println(element));

// Guaranteed order even for parallel streams
stream.parallel().forEachOrdered(element -> System.out.println(element));
```

## Specialized Stream Operations for Primitives

```java
// Sum
int sum = intStream.sum();

// Average
OptionalDouble avg = intStream.average();

// Statistics
IntSummaryStatistics stats = intStream.summaryStatistics();

// Boxing back to Stream<Integer>
Stream<Integer> boxed = intStream.boxed();
```

## Parallel Streams

```java
// Create parallel stream from collection
Stream<T> parallelStream = collection.parallelStream();

// Convert sequential stream to parallel
Stream<T> parallel = stream.parallel();

// Check if stream is parallel
boolean isParallel = stream.isParallel();

// Convert parallel stream to sequential
Stream<T> sequential = parallel.sequential();
```

## Best Practices

1. **Prefer method references over lambda expressions when possible**
   ```java
   stream.map(String::toUpperCase) // Better than stream.map(s -> s.toUpperCase())
   ```

2. **Use specialized streams for primitives**
   ```java
   IntStream.range(1, 100) // Better than Stream.iterate(1, i -> i + 1).limit(99)
   ```

3. **Be careful with infinite streams**
   ```java
   Stream.iterate(0, i -> i + 1) // Must use limit() or it will run forever
   ```

4. **Streams are not reusable**
   ```java
   // This will throw IllegalStateException
   Stream<String> stream = list.stream();
   stream.collect(Collectors.toList());
   stream.collect(Collectors.toSet()); // Error: stream has already been operated upon or closed
   ```

5. **Consider performance when choosing parallel streams**
   - Parallel streams use the common ForkJoinPool
   - Only use for computationally intensive operations
   - Beware of operations that rely on order or have side effects

6. **Avoid stateful lambda expressions in parallel streams**
   ```java
   // Bad: result depends on execution order
   List<Integer> bad = new ArrayList<>();
   stream.parallel().map(e -> { bad.add(e); return e; }); // Don't do this!
   ```
