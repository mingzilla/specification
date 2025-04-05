# Apache Lucene 9.8 Cheat Sheet

## Overview

Apache Lucene 9.8 is a high-performance, full-featured search engine library written in Java. It provides powerful indexing and search capabilities for applications requiring structured search, full-text search, faceting, nearest-neighbor vector search, spell correction, and query suggestions.

## Required Dependencies

```xml
<dependency>
    <groupId>org.apache.lucene</groupId>
    <artifactId>lucene-core</artifactId>
    <version>9.8.0</version>
</dependency>
<dependency>
    <groupId>org.apache.lucene</groupId>
    <artifactId>lucene-analysis-common</artifactId>
    <version>9.8.0</version>
</dependency>
<!-- For query parsing (optional) -->
<dependency>
    <groupId>org.apache.lucene</groupId>
    <artifactId>lucene-queryparser</artifactId>
    <version>9.8.0</version>
</dependency>
```

## Directory Implementation Selection Guide

| Directory Type | Best For | Avoid When | Key Advantages | Key Limitations |
|----------------|----------|------------|----------------|-----------------|
| `ByteBuffersDirectory` | • Short-lived, transient indices<br>• Testing and demos<br>• In-memory operations without persistence<br>• Small indices (less than a few hundred MB) | • Large indices<br>• Production systems requiring persistence<br>• Limited heap memory environments | • Fast in-memory operation<br>• No disk I/O<br>• Better multi-threading than old RAMDirectory<br>• No file system dependency | • Uses Java heap memory<br>• Limited by available RAM<br>• Higher GC pressure<br>• Data is lost when JVM restarts |
| `MMapDirectory` | • Production environments<br>• Larger indices<br>• Performance-critical applications<br>• Systems with sufficient virtual memory | • Very memory-constrained 32-bit systems | • Uses OS memory-mapping for optimal performance<br>• Takes advantage of OS page cache<br>• Persists data to disk<br>• Lower heap usage | • Requires file system access<br>• Initial I/O overhead when data not in OS cache<br>• Can trigger SIGSEGV errors if misused with concurrent access |
| `FSDirectory` | • Basic filesystem storage<br>• When Lucene should auto-select best implementation | • When you specifically need memory-mapping features | • Automatically selects best implementation<br>• Works across all platforms | • May not be optimized for specific use cases |
| `NIOFSDirectory` | • Fallback when MMapDirectory is not available | • When better alternatives are available | • Uses java.nio for file access<br>• Better than SimpleFSDirectory | • Not as performant as MMapDirectory |

## Field Type Selection Guide

| Field Type | Best For | Index Behavior | Store Behavior | When To Choose |
|------------|----------|----------------|----------------|----------------|
| `TextField` | • Long text content<br>• Fields requiring full-text search<br>• Description fields<br>• Document bodies | Analyzed, tokenized, and indexed | Optional (use `Field.Store.YES` to store) | When you need full-text search with word analysis, stemming, stop words, etc. |
| `StringField` | • IDs<br>• Codes<br>• URLs<br>• Exact match fields<br>• Enum values | Indexed as a single token without analysis | Optional (use `Field.Store.YES` to store) | When you need exact matching without text analysis |
| `StoredField` | • Large fields only needed for retrieval<br>• Data not used for searching<br>• Binary content | Not indexed | Always stored | When you only need to retrieve the value but never search on it |
| `IntPoint`, `LongPoint`, etc. | • Numeric values for range queries<br>• Dates<br>• Prices<br>• Coordinates | Indexed for range queries | Not stored by default | When you need efficient numeric range queries - add separate `StoredField` if you need to retrieve values |
| `SortedDocValuesField` | • Fields used for sorting<br>• Faceting fields | Not directly searchable | Stored in column-oriented format | When you need efficient sorting or faceting on a field |
| `NumericDocValuesField` | • Numeric values for efficient sorting<br>• Fields for function queries | Not directly searchable | Stored in column-oriented format | When you need to sort on numeric values or use them in function queries |
| `KnnFloatVectorField` | • Vector embeddings<br>• Semantic search vectors<br>• ML feature vectors | Indexed for vector similarity search | Not stored | When you need to perform nearest-neighbor (similarity) searches with 32-bit floating point precision |
| `KnnByteVectorField` | • Quantized vector embeddings<br>• Memory-efficient vector storage | Indexed for vector similarity search | Not stored | When you need vector search with reduced memory footprint and can accept slight precision loss |

## Query Type Selection Guide

| Query Type | Best For | Performance | Limitations | When To Choose |
|------------|----------|-------------|------------|----------------|
| `TermQuery` | • Exact matches<br>• ID lookups<br>• Code lookups | Very fast | • No text analysis<br>• Case sensitive | When you need exact, verbatim matches on a specific term |
| `BooleanQuery` | • Combining multiple criteria<br>• Complex logical conditions | Depends on clauses | • Default limit of 1024 clauses | When you need to combine multiple query conditions with AND, OR, NOT logic |
| `PhraseQuery` | • Exact phrase matching<br>• Multi-word expressions | Moderate | • Performance degrades with high slop values | When word order and proximity matter (e.g., "big apple" exactly) |
| `FuzzyQuery` | • Typo-tolerant search<br>• Spelling variations | Slow (high CPU) | • Can be very expensive<br>• Can match too broadly | When you need to handle typos and minor spelling variations |
| `WildcardQuery` | • Pattern matching<br>• Prefix/suffix matching | Very slow on large indices | • Can be extremely expensive<br>• Prefix wildcards particularly slow | When you need pattern matching and the field is selective |
| `PrefixQuery` | • Autocomplete<br>• Begins-with queries | Moderate | • Less flexible than wildcards | When you need prefix matching without full wildcard capabilities |
| `RangeQuery` | • Date ranges<br>• Numeric ranges<br>• Alphabetical ranges | Fast for `*Point` fields | • Performance varies by field type | When you need to find values within a specific range |
| `RegexpQuery` | • Complex pattern matching | Very slow | • Can be extremely expensive | When you need sophisticated pattern matching and performance is not critical |
| `KnnFloatVectorQuery` | • Semantic search<br>• Similarity search | Fast with proper indexing | • Requires vector fields<br>• Approximate results | When you need to find documents with vectors similar to a query vector |

## Vector Similarity Function Selection Guide

| Function | Best For | Normalization | Considerations | When To Choose |
|----------|----------|---------------|---------------|----------------|
| `EUCLIDEAN` | • General distance measurement<br>• When magnitude matters | Not required | • Sensitive to magnitude differences | When the absolute distance between vectors matters and vector magnitudes have meaning |
| `EUCLIDEAN_HNSW` | • Most vector search applications<br>• Default option | Not required | • Optimized implementation for HNSW graph | When you want a good general-purpose similarity function with no special requirements |
| `DOT_PRODUCT` | • Optimized cosine similarity<br>• Recommendation systems | Required (unit vectors) | • All vectors must be normalized to unit length | When vectors are normalized and you want maximum performance for cosine similarity |
| `COSINE` | • Semantic similarity<br>• When vectors cannot be normalized in advance | Not required | • Less efficient than DOT_PRODUCT | When you need cosine similarity but cannot pre-normalize your vectors |
| `MAXIMUM_INNER_PRODUCT` | • Recommendation systems<br>• When higher values in dimensions correlate to preference | Not required | • Not normalized to [0,1] range<br>• Can return negative scores | When inner product aligns with your use case (e.g., user preferences represented as dimensional values) |

## Boolean Clause Selection Guide

| Operator | Effect on Results | Effect on Score | Use Case |
|----------|------------------|----------------|----------|
| `MUST` (AND) | Document must match this clause | Score contributes positively | Required criteria that must be present |
| `SHOULD` (OR) | Document can match this clause | Score contributes positively if matched | Optional criteria that improves relevance |
| `MUST_NOT` (NOT) | Document must not match this clause | No effect on score | Exclusionary criteria |
| `FILTER` | Document must match this clause | No effect on score | Required criteria where relevance scoring doesn't matter |

## When to Use in-memory vs. on-disk indices:

**Use in-memory indices (ByteBuffersDirectory) when:**
- Working with small, temporary indices
- Running tests or demos
- Creating ephemeral search functionality
- Performing operations where persistence isn't required
- The entire index can comfortably fit in available memory

**Use on-disk indices (MMapDirectory) when:**
- Working with production applications
- Dealing with indices that need to persist after application restarts
- The index is too large to fit in available memory 
- You need maximum performance for large indices
- You want to leverage the operating system's page cache

**Specific recommendations for vector search:**
- For development/testing of vector search with small datasets (<100K vectors): Use ByteBuffersDirectory
- For production vector search applications: Use MMapDirectory
- For large-scale vector search in production: Consider specialized vector databases or Lucene with MMapDirectory and appropriate hardware

### Performance Improvements

- **Faster Boolean Query Processing**: 20-30% speedup for disjunctive queries and 11-13% speedup for conjunctive queries compared to Lucene 9.7. Queries with many high-frequency terms see even greater improvements.
- **Improved Field Sorting**: 7-33% speedup when sorting by field, depending on field type and cardinality.
- **Lazy Evaluation in Expressions**: All arguments in expressions are now evaluated in a fully lazy manner, providing significant speedups for heavy expression users.
- **Vector Search Optimizations**: Improved KNN vector search performance with filter reuse and better algorithm implementation.

### New Vector Search Features

- **Custom KNN Collectors**: Added "KnnCollector" to "LeafReader" and "KnnVectorReader" for custom collection of vector search results.
- **Parent-Child Vector Relationships**: New `ToParentBlockJoin[Float|Byte]KnnVectorQuery` for joining child vector documents with their parent documents.
- **Vector Field Types**: Support for byte-sized vectors with `KnnByteVectorField` and `ByteVectorQuery`, alongside the float vector equivalents.

### Index Optimization

- **Recursive Graph Bisection (BP)**: Added support for bipartite graph partitioning, an algorithm for reordering doc IDs that results in more compact postings and faster queries, especially for conjunctions.
- **HNSW Graph Improvements**: Fixed bugs and improved implementation of the Hierarchical Navigable Small World algorithm for nearest neighbor search.

### Bug Fixes

- **HNSW Graph Search**: Fixed bug that potentially leaked unapproved documents.
- **TermsEnum**: Fixed bug in `TermsEnum#seekCeil` on doc values terms enums that caused IndexOutOfBoundsException.

## Core Components

### Indexing

```java
// Create an index writer configuration
IndexWriterConfig config = new IndexWriterConfig(analyzer);
config.setOpenMode(OpenMode.CREATE); // or OpenMode.CREATE_OR_APPEND

// Create an index writer
IndexWriter writer = new IndexWriter(directory, config);

// Create a document
Document doc = new Document();
doc.add(new TextField("title", "Document Title", Field.Store.YES));
doc.add(new StringField("id", "doc1", Field.Store.YES));
doc.add(new IntPoint("year", 2025));

// Add the document to the index
writer.addDocument(doc);

// Commit changes
writer.commit();

// Close the writer when done
writer.close();
```

### Searching

```java
// Create an index reader
IndexReader reader = DirectoryReader.open(directory);

// Create an index searcher
IndexSearcher searcher = new IndexSearcher(reader);

// Create a query (term query example)
Query query = new TermQuery(new Term("title", "lucene"));

// Execute the search
TopDocs results = searcher.search(query, 10);

// Process results
for (ScoreDoc scoreDoc : results.scoreDocs) {
    Document doc = searcher.doc(scoreDoc.doc);
    System.out.println(doc.get("title") + " (Score: " + scoreDoc.score + ")");
}

// Close the reader when done
reader.close();
```

### Query Types

#### Term Query
```java
Query query = new TermQuery(new Term("field", "term"));
```

#### Boolean Query
```java
BooleanQuery.Builder builder = new BooleanQuery.Builder();
builder.add(new TermQuery(new Term("field", "term1")), BooleanClause.Occur.MUST);
builder.add(new TermQuery(new Term("field", "term2")), BooleanClause.Occur.SHOULD);
builder.add(new TermQuery(new Term("field", "term3")), BooleanClause.Occur.MUST_NOT);
Query query = builder.build();
```

#### Phrase Query
```java
PhraseQuery.Builder builder = new PhraseQuery.Builder();
builder.add(new Term("field", "term1"));
builder.add(new Term("field", "term2"));
builder.setSlop(1); // Allow terms to be 1 position apart
Query query = builder.build();
```

#### Wildcard Query
```java
Query query = new WildcardQuery(new Term("field", "te*m"));
```

#### Range Query (Numeric)
```java
Query query = IntPoint.newRangeQuery("year", 2020, 2025);
```

#### Fuzzy Query
```java
Query query = new FuzzyQuery(new Term("field", "term"), 2); // Edit distance of 2
```

#### Query Parser
```java
QueryParser parser = new QueryParser("defaultField", analyzer);
Query query = parser.parse("title:lucene OR content:search");
```

## In-Memory Vector Store Operations

### Creating an In-Memory Index

Lucene 9.8 uses `ByteBuffersDirectory` for in-memory operations, which replaced the deprecated `RAMDirectory`:

```java
// Create in-memory directory
Directory directory = new ByteBuffersDirectory();

// Configure analyzer and writer
Analyzer analyzer = new StandardAnalyzer();
IndexWriterConfig config = new IndexWriterConfig(analyzer);
config.setOpenMode(OpenMode.CREATE);  // For a new index
IndexWriter writer = new IndexWriter(directory, config);
```

### Creating Documents with Vector Fields

```java
// Create document with vector field
Document doc = new Document();

// Add metadata fields
doc.add(new StringField("id", "doc1", Field.Store.YES));
doc.add(new TextField("title", "Example Document", Field.Store.YES));

// Add vector fields - KnnFloatVectorField is recommended over deprecated KnnVectorField
float[] vector = new float[] {0.1f, 0.2f, 0.3f, 0.4f};

// Use COSINE similarity for semantic search applications
doc.add(new KnnFloatVectorField("embedding", vector, VectorSimilarityFunction.COSINE));

// Or default to Euclidean distance (L2)
doc.add(new KnnFloatVectorField("vector_l2", vector));

// Index the document
writer.addDocument(doc);
writer.commit();
```

### Updating Documents with Vectors

```java
// Update a document with a new vector
// First, find and delete the old document
Term idTerm = new Term("id", "doc1");
writer.deleteDocuments(idTerm);

// Create new document with same ID but updated vector
Document updatedDoc = new Document();
updatedDoc.add(new StringField("id", "doc1", Field.Store.YES));
updatedDoc.add(new TextField("title", "Updated Document", Field.Store.YES));

// Updated vector
float[] updatedVector = new float[] {0.15f, 0.25f, 0.35f, 0.45f};
updatedDoc.add(new KnnFloatVectorField("embedding", updatedVector, VectorSimilarityFunction.COSINE));

// Add the updated document
writer.addDocument(updatedDoc);
writer.commit();
```

### Reading Documents and Performing Vector Search

```java
// Create a reader and searcher
IndexReader reader = DirectoryReader.open(directory);
IndexSearcher searcher = new IndexSearcher(reader);

// Vector similarity search (KNN)
float[] queryVector = new float[] {0.12f, 0.22f, 0.32f, 0.42f};
Query knnQuery = new KnnFloatVectorQuery("embedding", queryVector, 10);
TopDocs results = searcher.search(knnQuery, 10);

// Process results
for (ScoreDoc scoreDoc : results.scoreDocs) {
    Document doc = searcher.doc(scoreDoc.doc);
    String id = doc.get("id");
    String title = doc.get("title");
    float score = scoreDoc.score;
    System.out.println("Document ID: " + id + ", Title: " + title + ", Score: " + score);
}
```

### Filtered Vector Search

```java
// Create a filter (e.g., category = "electronics")
Query filter = new TermQuery(new Term("category", "electronics"));

// Vector search with filter
Query filteredKnnQuery = new KnnFloatVectorQuery("embedding", queryVector, 10, filter);
TopDocs filteredResults = searcher.search(filteredKnnQuery, 10);
```

### Deleting Documents

```java
// Delete a document by ID
Term idTerm = new Term("id", "doc1");
writer.deleteDocuments(idTerm);
writer.commit();

// Or delete documents matching a query
Query deleteQuery = new TermQuery(new Term("category", "obsolete"));
writer.deleteDocuments(deleteQuery);
writer.commit();
```

### Complete In-Memory Vector Store Example

```java
import org.apache.lucene.analysis.standard.StandardAnalyzer;
import org.apache.lucene.document.*;
import org.apache.lucene.index.*;
import org.apache.lucene.search.*;
import org.apache.lucene.store.ByteBuffersDirectory;
import org.apache.lucene.store.Directory;

public class InMemoryVectorStore {
    private Directory directory;
    private StandardAnalyzer analyzer;
    private IndexWriter writer;
    
    public InMemoryVectorStore() throws Exception {
        // Initialize in-memory store
        directory = new ByteBuffersDirectory();
        analyzer = new StandardAnalyzer();
        IndexWriterConfig config = new IndexWriterConfig(analyzer);
        config.setOpenMode(OpenMode.CREATE_OR_APPEND);
        writer = new IndexWriter(directory, config);
    }
    
    public void addDocument(String id, String text, float[] vector) throws Exception {
        Document doc = new Document();
        doc.add(new StringField("id", id, Field.Store.YES));
        doc.add(new TextField("text", text, Field.Store.YES));
        doc.add(new KnnFloatVectorField("vector", vector, VectorSimilarityFunction.COSINE));
        writer.addDocument(doc);
        writer.commit();
    }
    
    public void updateDocument(String id, String text, float[] vector) throws Exception {
        // Delete existing document
        writer.deleteDocuments(new Term("id", id));
        
        // Add updated document
        Document doc = new Document();
        doc.add(new StringField("id", id, Field.Store.YES));
        doc.add(new TextField("text", text, Field.Store.YES));
        doc.add(new KnnFloatVectorField("vector", vector, VectorSimilarityFunction.COSINE));
        writer.addDocument(doc);
        writer.commit();
    }
    
    public List<Document> searchByVector(float[] queryVector, int k) throws Exception {
        List<Document> results = new ArrayList<>();
        IndexReader reader = DirectoryReader.open(directory);
        try {
            IndexSearcher searcher = new IndexSearcher(reader);
            Query query = new KnnFloatVectorQuery("vector", queryVector, k);
            TopDocs topDocs = searcher.search(query, k);
            
            for (ScoreDoc scoreDoc : topDocs.scoreDocs) {
                Document doc = searcher.doc(scoreDoc.doc);
                results.add(doc);
            }
        } finally {
            reader.close();
        }
        return results;
    }
    
    public void deleteDocument(String id) throws Exception {
        writer.deleteDocuments(new Term("id", id));
        writer.commit();
    }
    
    public void close() throws Exception {
        writer.close();
        directory.close();
    }
}
```

### Vector Search (KNN)

```java
// Index a float vector
Document doc = new Document();
float[] vector = new float[] {0.1f, 0.2f, 0.3f, 0.4f};
doc.add(new KnnFloatVectorField("vector_field", vector));
writer.addDocument(doc);

// Search for similar vectors
float[] queryVector = new float[] {0.15f, 0.25f, 0.35f, 0.45f};
Query knnQuery = new KnnFloatVectorQuery("vector_field", queryVector, 10);
TopDocs results = searcher.search(knnQuery, 10);
```

```java
// Using a filter with KNN search
Query filter = new TermQuery(new Term("category", "electronics"));
Query knnQuery = new KnnFloatVectorQuery("vector_field", queryVector, 10, filter);
```

## Analysis

### Creating an Analyzer

```java
// Standard analyzer
Analyzer analyzer = new StandardAnalyzer();

// Custom analyzer
Analyzer customAnalyzer = new Analyzer() {
    @Override
    protected TokenStreamComponents createComponents(String fieldName) {
        Tokenizer tokenizer = new StandardTokenizer();
        TokenStream filter = new LowerCaseFilter(tokenizer);
        filter = new StopFilter(filter, StandardAnalyzer.STOP_WORDS_SET);
        return new TokenStreamComponents(tokenizer, filter);
    }
};
```

### Common TokenFilters

- LowerCaseFilter
- StopFilter
- SynonymFilter
- PorterStemFilter
- KStemFilter
- SnowballFilter
- WordDelimiterGraphFilter

## Best Practices

1. **Choose the Right Directory Implementation**:
   - MMapDirectory for most applications (default in 9.8)
   - NIOFSDirectory as a fallback
   - RAMDirectory for testing

2. **Optimize Index Writing**:
   - Use appropriate RAM buffer size (IndexWriterConfig.setRAMBufferSizeMB)
   - Consider merge policy and merge scheduler settings
   - Batch document additions

3. **Query Performance**:
   - Use filters for initial narrowing of result sets
   - Consider caching frequently used filters
   - For complex queries, pre-process and use BooleanQuery with appropriate Occur values

4. **Vector Search**:
   - For KNN queries, choose the appropriate similarity function for your use case
   - Use appropriate vector dimensions (higher dimensions = more precise but slower)
   - Consider using filters to restrict the search space

5. **Concurrency**:
   - One IndexWriter per index
   - Multiple concurrent readers are safe
   - Consider using SearcherManager for thread-safe reader management

## System Requirements

- Java 11 or higher
- Standard JAR dependencies can be found in the Maven repository

## Additional Resources

- Official Documentation: https://lucene.apache.org/core/9_8_0/
- API Javadocs: https://lucene.apache.org/core/9_8_0/core/index.html
- Changes List: https://lucene.apache.org/core/9_8_0/changes/Changes.html
- Mailing Lists: https://lucene.apache.org/core/discussion.html

## Common Gotchas

1. Make sure to close resources (IndexReader, IndexWriter) in finally blocks or try-with-resources
2. Remember that Lucene is not thread-safe by default, especially for writing
3. Be careful with analyzers - the same analyzer should be used for indexing and querying
4. KNN vectors cannot have non-finite values such as NaN or ±Infinity
5. Document deletion is logical until segments are merged
