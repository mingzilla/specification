## Desired Service Architecture

| Area             | Topic       | Grails | Stateful | GORM | L1Cache | DB | Domain | Reason                           |
|------------------|-------------|--------|----------|------|---------|----|--------|----------------------------------|
| Display Chart    | Charts      | X      | X        | X    | X       | X  | X      |                                  | 
|                  | Categories  |        | X        | X    | X       | X  | X      |                                  | 
|                  | Connections |        | X        | X    | X       | X  | X      |                                  | 
|                  | Variables   |        | X        | X    | X       | X  | X      |                                  | 
|                  | Auth        |        |          | X    | X       | X  | X      |                                  | 
|                  |             |        |          |      |         |    |        |                                  | 
| Edit Chart       | Charts      |        |          |      |         | X  | X      | Different from Display Chart     | 
|                  | Categories  |        | X        | X    | X       | X  | X      |                                  | 
|                  | Connections |        | X        | X    | X       | X  | X      |                                  | 
|                  | Variables   |        | X        | X    | X       | X  | X      |                                  | 
|                  | Auth        |        |          | X    | X       | X  | X      |                                  | 
|                  |             |        |          |      |         |    |        |                                  | 
| Display Category | Categories  | X      | X        | X    | X       | X  | X      |                                  | 
|                  | Connection  |        | X        | X    | X       | X  | X      |                                  | 
|                  | Variables   |        | X        | X    | X       | X  | X      |                                  | 
|                  | Auth        |        |          | X    | X       | X  | X      |                                  | 
|                  |             |        |          |      |         |    |        |                                  | 
| Can View         | Charts      |        |          |      | X       | X  | X      | Designed for concurrent requests | 
| Can View         | Categories  |        |          |      | _       | X  | X      | Designed for concurrent requests | 
| Can View         | Connections |        |          |      | _       | X  | X      | Designed for concurrent requests | 
|                  |             |        |          |      |         |    |        |                                  | 
| Edit Non Charts  | Any         |        |          |      |         | X  | X      | should use realtime data         | 
| Export Import    | Any         |        |          |      |         | X  | X      | should use realtime data         | 
| API CRUD         | Any         |        |          |      | _       | X  | X      | should use realtime data         | 

## Service Type and Reason

| Service Type | Content                                                       | Reason                                                                         |
|--------------|---------------------------------------------------------------|--------------------------------------------------------------------------------|
| Grails       | DB + External                                                 | Combines application and external services e.g. OAuth, File System             |
| Stateful     | Caches bundles - (Connections, Categories, Charts, Variables) | Legacy Cache Level                                                             |
| GORM         | Multiple L1Cache Topics + Legacy DbServices                   | Old - Same as DbServices, Now - to use many L1Caches and DbServices            |
| L1Cache      | Single L1Cache Topic (avoid using other L1Cache services)     | Lower than GORM, otherwise if this uses GORM, all controllers need refactoring |
| Db           | Many GORM Domains                                             | Move all the old GormService logic to this level                               |
| Domain       | Single GORM Domain                                            | Unchanged                                                                      |

## L1CacheService

### Should and Shouldn't

- Should - these services are used for the display side of the system, which would repeatedly fetch the same data from the database if these services are not used
    - especially for things that allow concurrent requests - e.g. F5 refresh causing multiple requests to occur
    - interceptors for UI display area of the system
- Shouldn't - these services should not be used for anything related to an editing area or the API e.g.
    - use `DbService` directly for `EditorsController`s - when making an edit, avoid getting caching data which may not be up to date
    - use `DbService` directly for API calls - the API needs real time data that reflects the database
    - interceptors for APIs should avoid `L1CacheService` for the same reason

### Caching and Transactions

Cache Services should not be used within a Transaction wrapper.

- it's fine for it to wrap a transaction,
- it can have problems if a transaction wraps a cache service

The intention to use a transaction is to write data to the database

- so generally it's not likely to implement transaction with caching
- there are people using transactions to maintain db and redis consistency, but with our solution it doesn't seem to be necessary
- If caching services are used for rate limiting purposes, then you may implement rate limiting to prevent too many hits to the database

### Caching lifetime

These services currently only have short life caching.

- The intention is not to cache the data for a long time because they can be invalid.
- The intention is to cache the data to prevent concurrent requests applying pressure to the database

## StatefulService

These are similar to `L1CacheService`. These are the legacy version of `L1CacheService`s.

### Areas of the system

They cache the following 4 areas of the system:

- data connections - has been converted to use long life cache
- charts - has been converted to use long life cache
- categories
- variables

### Caching lifetime

These services will be converted to handle long life caching with [ExpirableLongLifeCache.groovy](../../../../../src/main/groovy/com/panintelligence/cache/util/ttl/ExpirableLongLifeCache.groovy).

- a quick request (with 1s or 2s rate limit control) to verify if the cache is still valid
- a slow request to get the cache and store the cache with a long lifetime

### Caching maintenance

To avoid the need of sticky session, caching maintenance needs to happen reactively, not proactively.

- proactive - when updating e.g. a data connection, delete the cache
- reactive - when requesting a data connection, do a quick check to verify if the cache is still valid, and update the cache accordingly

Generally, the cache expiry condition is: checkerObject.updatedAt is newer than what's in the cache

- this is defined with [CacheExpiryCondition.groovy](../../../../../src/main/groovy/com/panintelligence/cache/util/ttl/CacheExpiryCondition.groovy)
