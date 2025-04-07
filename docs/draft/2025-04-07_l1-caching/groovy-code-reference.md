## FILE: src/ExpirableLongLifeCache.groovy
~~~
package com.panintelligence.cache.util.ttl

import groovy.transform.CompileStatic
import groovy.transform.stc.ClosureParams
import groovy.transform.stc.SimpleType

import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.locks.ReentrantLock

/**
 * This allows reactively decide if there is a need to call fetchNonNullDataFn().
 * <pre>
 * This approach removes the need to proactively delete expired cache data (e.g. when saving a chart), which is not possible if load balancing nodes having sticky sessions turned off.
 * (This node cannot proactively delete data cached in another node)
 * When a request is made, this runs a quick query, which returns a object, used to decide if we delete the related cache.
 * - it Caches checkerCache for checkerShortLifeTime - (this means even the quick query is only allowed to be run e.g. once per second)
 * - it Caches actualDataCache for cacheLongLifeTime
 * - if expiryCondition.canUseCache() == false, cache for the related key is deleted, which forces fetchNonNullDataFn() to be executed
 * Cache for different `key`s do not interfere with each other. - (this is handled by {@link ExpirableObjectMap})
 * </pre>
 *
 * <pre>
 * Scenario:
 * - within e.g. 1s, many requests are made to get a chart using chartId 10
 *   - only 1 checker request is made to get a db chart
 * - it runs expiryCondition.canUseCache() to see if cache is expired
 *   - if true, the checker step does nothing
 *   - if false, the checker step it deletes the cache related to chartId 10,
 * </pre>
 *
 * (C) Copyright panintelligence Ltd
 *
 * @since 02/11/2024
 * @author ming.huang
 */
@CompileStatic
class ExpirableLongLifeCache<CheckerT, CacheT> {

    private ExpirableObjectMap<CheckerT> checkerCache // used internally to decide if the related cache needs to be deleted, which forces fetchNonNullDataFn() to run to create the cache
    private ExpirableObjectMap<CacheT> actualDataCache
    private ConcurrentHashMap<String, ReentrantLock> locks = new ConcurrentHashMap<>() // to allow only one thread if the key is the same

    static <CheckerT, CacheT> ExpirableLongLifeCache<CheckerT, CacheT> create(int checkerShortLifeTime, int cacheLongLifeTime) {
        ExpirableObjectMap<CheckerT> checkerCache = ExpirableObjectMap.create(checkerShortLifeTime, false)
        ExpirableObjectMap<CacheT> actualDataCache = ExpirableObjectMap.create(cacheLongLifeTime, false)
        return new ExpirableLongLifeCache<CheckerT, CacheT>(checkerCache: checkerCache, actualDataCache: actualDataCache)
    }

    /**
     * This uses {@link CacheExpiryCondition} to decide if {@link CacheExpiryCondition#canStillUseCacheWhenCheckerExpires}, which runs only ONCE within checkerShortLifeTime period.
     * Check how this {@link ExpirableLongLifeCache} object is created to see how {@link CacheExpiryCondition#canStillUseCacheWhenCheckerExpires} is implemented.
     *
     * @param key - unique key for the cache, which is used to lock a request. Threads with the SAME KEY would queue. Threads with different keys do NOT queue
     * @param fetchCheckerObjectFn - A quick request to decide if the cache can be used. Note: if NULL is returned, it deletes the cache for this key
     * @param fetchNonNullDataFn - A slow request - this does NOT cache NULL, so if null is returned, it ALWAYS runs the query again next time
     * @return the data cached for the given key
     */
    CacheT getOrFetch(String key,
                      @ClosureParams(value = SimpleType, options = ["java.lang.Object"]) Closure<CheckerT> fetchCheckerObjectFn,
                      @ClosureParams(value = SimpleType, options = ["java.lang.Object"]) Closure<CacheExpiryCondition<CheckerT, CacheT>> createExpiryConditionFn,
                      @ClosureParams(value = SimpleType, options = ["java.lang.Object"]) Closure<CacheT> fetchNonNullDataFn) {
        return getObject(key, new Date(), fetchCheckerObjectFn, createExpiryConditionFn, fetchNonNullDataFn)
    }

    protected CacheT getObject(String key, Date now,
                               @ClosureParams(value = SimpleType, options = ["java.lang.Object"]) Closure<CheckerT> fetchCheckerObjectFn,
                               @ClosureParams(value = SimpleType, options = ["java.lang.Object"]) Closure<CacheExpiryCondition<CheckerT, CacheT>> createExpiryConditionFn,
                               @ClosureParams(value = SimpleType, options = ["java.lang.Object"]) Closure<CacheT> fetchNonNullDataFn) {
        CacheT data = null
        ConcurrentLockUtil.runWithLock(locks, key, {
            CheckerT checkerData = ExpirableObjectMap.getObject(checkerCache, key, now, {
                CheckerT dbCheckerItem = fetchCheckerObjectFn(key)
                if (dbCheckerItem == null) return dbCheckerItem // not found in db, no need to cache

                ExpirableObject<CheckerT> cachedCheckerItem = checkerCache.getExistingExpirableObject(key, now)
                ExpirableObject<CacheT> cachedDataItem = actualDataCache.getExistingExpirableObject(key, now)
                boolean cacheExistsButExpired = (cachedDataItem?.object != null) && !createExpiryConditionFn().canStillUseCacheWhenCheckerExpires(cachedCheckerItem, dbCheckerItem, cachedDataItem)
                if (cacheExistsButExpired) actualDataCache.removeCache(key)

                return dbCheckerItem
            })

            if (checkerData == null) {
                checkerCache.removeCache(key) // remove [(key): null] to keep checkerCache clean
                actualDataCache.removeCache(key) // if checker is null, actual data is no longer valid
            } else {
                data = ExpirableObjectMap.getObject(actualDataCache, key, now, fetchNonNullDataFn)
            }
        })
        return data
    }

    synchronized static <CheckerT, CacheT> ExpirableLongLifeCache<CheckerT, CacheT> updateCheckerAndCacheData(ExpirableLongLifeCache<CheckerT, CacheT> longLifeCache, Map<String, CacheT> keyAndDataToCache,
                                                                                                              @ClosureParams(value = SimpleType, options = ["java.lang.Object"]) Closure<CheckerT> getCheckerDataFn) {
        keyAndDataToCache.each {
            String key = "$it.key"
            CacheT cacheData = it.value
            CheckerT checkerData = getCheckerDataFn(cacheData)
            if (!checkerData) return
            longLifeCache.getOrFetch(key, { checkerData }, {
                return new CacheExpiryCondition<CheckerT, CacheT>() {
                    @Override
                    boolean canStillUseCacheWhenCheckerExpires(ExpirableObject<CheckerT> cachedCheckerItem, CheckerT dbCheckerItem, ExpirableObject<CacheT> cachedDataItem) {
                        return false
                    }
                } as CacheExpiryCondition<CheckerT, CacheT>
            }, { cacheData })
        }
        return longLifeCache
    }

    void emptyCache() {
        checkerCache.emptyCache()
        actualDataCache.emptyCache()
    }

    boolean isEmpty() {
        return actualDataCache.isEmpty()
    }
}
~~~

----

## FILE: src/CacheExpiryCondition.groovy
~~~
package com.panintelligence.cache.util.ttl

import groovy.transform.CompileStatic

/**
 * The only reason this class exists is to make sure @CompileStatic can be applied.
 * If canUseCache is implemented as a closure, in Groovy, you cannot define the parameters (<CheckerT, CacheT>) using generics type.
 * @ClosureParams() does not allow generics.
 *
 * (C) Copyright panintelligence Ltd
 *
 * @since 02/11/2024
 * @author ming.huang
 */
@CompileStatic
abstract class CacheExpiryCondition<CheckerT, CacheT> {

    /**
     * Used by Long Life Cache to determine if it needs to delete the cache for the related key.
     *
     * @param cachedCheckerItem - previously cached checker item
     * @param dbCheckerItem - new checker item derived from the database
     * @param cachedDataItem - non-null existing cache data
     * @return true if cache can be used; false if cache is expired, which forces the cache to be deleted
     */
    abstract boolean canStillUseCacheWhenCheckerExpires(ExpirableObject<CheckerT> cachedCheckerItem, CheckerT dbCheckerItem, ExpirableObject<CacheT> cachedDataItem)
}
~~~

----

## FILE: src/ExpirableObjectMap.groovy
~~~
package com.panintelligence.cache.util.ttl


import groovy.transform.CompileStatic

import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.locks.ReentrantLock

/**
 * (C) Copyright panintelligence Ltd
 *
 * @since 29/11/2023
 * @author ming.huang
 */
@CompileStatic
class ExpirableObjectMap<T> {

    int cachePeriod = 5
    boolean canExtendLifeTime // true - extends life time if the object is requested

    private ConcurrentHashMap<String, ReentrantLock> locks = new ConcurrentHashMap<>() // to allow only one thread if the key is the same
    private ConcurrentHashMap<String, ExpirableObject<T>> map = new ConcurrentHashMap<>() // 1) locks and map have the same key, 2) use ConcurrentHashMap because it avoids corrupting the map data structure when multiple threads write to different entries with different keys

    static final <O> ExpirableObjectMap create(int cachePeriod, boolean canExtendLifeTime) {
        return new ExpirableObjectMap<O>(cachePeriod: cachePeriod, canExtendLifeTime: canExtendLifeTime).emptyCache()
    }

    /**
     * @return cached data, if not present it would not try to fetch data. It would just return null
     */
    final T getExistingCache(String key) {
        return getExistingExpirableObject(key, new Date())?.object
    }

    /**
     * @return a nullable {@link ExpirableObject}. This object has the last requested time, useful for handling cache expiry condition.
     */
    protected final ExpirableObject<T> getExistingExpirableObject(String key, Date now) {
        return getExpirableObject(this, key, now, { null }) as ExpirableObject<T>
    }

    final T getOrFetch(String key, Closure<T> fetchFn) {
        return getObject(this, key, new Date(), fetchFn)
    }

    final T getOrFetchAllowForcing(String key, boolean forceLoading, Closure<T> fetchFn) {
        if (forceLoading) removeCache(key)
        return getObject(this, key, new Date(), fetchFn)
    }

    protected static final <O> O getObject(ExpirableObjectMap<O> expirableObjectMap, String key, Date now, Closure<O> fetchFn) {
        if (key == null) return null // concurrent map does not like using null, so just avoid null as key
        return getExpirableObject(expirableObjectMap, key, now, fetchFn).object
    }

    /**
     * If the same key is supplied, it only allows one thread to execute the `try` block.
     * If different keys are supplied, it allows concurrent execution per key regardless how slow (within cachePeriod) the processing is.
     */
    protected static final <O> ExpirableObject<O> getExpirableObject(ExpirableObjectMap<O> expirableObjectMap, String key, Date now, Closure<O> fetchFn) {
        if (key == null) return null // concurrent map does not like using null, so just avoid null as key
        ReentrantLock lock = getLock(expirableObjectMap, key)
        lock.lock()
        ExpirableObject<O> newCache = null
        try {
            ExpirableObject<O> cache = expirableObjectMap.getCache(key)
            newCache = ExpirableObject.<O> getActiveExpirableObjectOrFetchNew(cache, now, fetchFn)
            expirableObjectMap.map[(key)] = newCache
        } finally {
            lock.unlock()
        }
        return newCache
    }

    static final <O> ReentrantLock getLock(ExpirableObjectMap<O> expirableObjectMap, String key) {
        return ConcurrentLockUtil.getLock(expirableObjectMap.locks, key)
    }

    private ExpirableObject<T> getCache(String key) {
        ExpirableObject<T> cache = map[(key)]
        if (cache != null) {
            return cache
        } else {
            cache = ExpirableObject.<T> create(cachePeriod, canExtendLifeTime)
            map[(key)] = cache
            return cache
        }
    }

    synchronized void removeCache(String key) {
        if (key == null) return
        map.remove(key)
        locks.remove(key)
    }

    ExpirableObjectMap<T> emptyCache() {
        locks = new ConcurrentHashMap<>()
        map = new ConcurrentHashMap<>()
        return this
    }

    boolean isEmpty() {
        return this.map.isEmpty()
    }
}
~~~

----

## FILE: src/ExpirableObjectNestedMap.groovy
~~~
package com.panintelligence.cache.util.ttl

import com.panintelligence.util.PiDateUtil
import groovy.transform.CompileStatic

import java.util.concurrent.ConcurrentHashMap

/**
 * This builds the cache with `key` and `nestedKey`.
 * It provides the ability to remove the whole stack of items for the same key.
 * <pre>
 * e.g. if remove key 'x', only the last item is left
 *  - key: 'x', nestedKey: 'a'
 *  - key: 'x', nestedKey: 'b'
 *  - key: 'y', nestedKey: 'c'
 * </pre>
 *
 * (C) Copyright panintelligence Ltd
 *
 * @since 29/11/2023
 * @author ming.huang
 */
@CompileStatic
class ExpirableObjectNestedMap<T> {

    int cachePeriod = 5
    boolean canExtendLifeTime // true - extends life time if the object is requested
    private Map<String, ExpirableObjectMap<T>> map = new ConcurrentHashMap<>()

    static final <O> ExpirableObjectNestedMap create(int cachePeriod, boolean canExtendLifeTime) {
        return new ExpirableObjectNestedMap<O>(cachePeriod: cachePeriod, canExtendLifeTime: canExtendLifeTime).emptyCache()
    }

    final T getOrFetch(String key, String nestedKey, Closure<T> fetchFn) {
        return getObject(this, key, nestedKey, PiDateUtil.now(), fetchFn)
    }

    protected static final <O> O getObject(ExpirableObjectNestedMap<O> expirableObjectNestedMap, String key, String nestedKey, Date now, Closure<O> fetchFn) {
        if (key == null) return null // concurrent map does not like using null, so just avoid null as key
        ExpirableObjectMap<O> nestedMap = expirableObjectNestedMap.getCache(key)
        O obj = ExpirableObjectMap.getObject(nestedMap, nestedKey, now, fetchFn)
        expirableObjectNestedMap.map[(key)] = nestedMap
        return obj
    }

    private ExpirableObjectMap<T> getCache(String key) {
        if (key == null) return null
        ExpirableObjectMap<T> cache = map[(key)]
        if (cache != null) {
            return cache
        } else {
            cache = ExpirableObjectMap.create(cachePeriod, canExtendLifeTime)
            map[(key)] = cache
            return cache
        }
    }

    void removeCache(String key) {
        map.remove(key) // deletes the whole stack of items related to the nestedKey
    }

    ExpirableObjectNestedMap<T> emptyCache() {
        map = new ConcurrentHashMap<>()
        return this
    }
}
~~~

----

## FILE: src/ExpirableObject.groovy
~~~
package com.panintelligence.cache.util.ttl

import groovy.transform.CompileStatic

/**
 * It caches an object, which can be returned if it's within the alive period.
 * After the period it uses the fetchFn to fetch and cache an object to keep a new copy alive for the period.
 * canExtendLifeTime decides if last requested time is refreshed when the object is requested, which extends the life time.
 *
 * (C) Copyright panintelligence Ltd
 *
 * @since 06/03/2023
 * @author ming.huang
 */
@CompileStatic
class ExpirableObject<T> {

    T object
    Date lastRequestedTime
    int alivePeriodInSeconds
    boolean canExtendLifeTime // true - Last requested time is refreshed if the object is requested, which extends the life time

    static <T> ExpirableObject<T> create(int alivePeriodInSeconds, boolean canExtendLifeTime) {
        return new ExpirableObject<T>(alivePeriodInSeconds: alivePeriodInSeconds, canExtendLifeTime: canExtendLifeTime)
    }

    static <T> T getActiveObjectOrFetchNew(ExpirableObject<T> expirableObject, Date now, Closure<T> fetchFn) {
        return getActiveExpirableObjectOrFetchNew(expirableObject, now, fetchFn).object
    }

    static <T> ExpirableObject<T> getActiveExpirableObjectOrFetchNew(ExpirableObject<T> expirableObject, Date now, Closure<T> fetchFn) {
        T activeObject = expirableObject.updateStatusAndReturnObject(now) // return null if it has expired
        if (activeObject != null) return expirableObject // explicitly using null check, because [], false, 0 etc. are false

        long t1 = System.currentTimeMillis()
        T newObject = fetchFn()
        long t2 = System.currentTimeMillis()
        long processingTime = t2 - t1
        Date lastRequestedTime = new Date(now.time + processingTime)

        expirableObject.cacheObject(newObject, lastRequestedTime)
        return expirableObject
    }

    private void cacheObject(T object, Date now) {
        this.object = object
        lastRequestedTime = now // needs to be set, because the getter only updates this value when passing expiry check
    }

    private T updateStatusAndReturnObject(Date now) {
        if (isExpired(lastRequestedTime, now, alivePeriodInSeconds)) {
            object = null
            return null
        } else {
            if (canExtendLifeTime) lastRequestedTime = now // updated time to extend the life time of this object
            return object
        }
    }

    static boolean isExpired(Date lastRequestedTime, Date requestedTime, int alivePeriodInSeconds) {
        if (!lastRequestedTime || !requestedTime) return false
        long gap = requestedTime.time - lastRequestedTime.time
        return gap > (alivePeriodInSeconds * 1000)
    }

    void clear() {
        object = null
        lastRequestedTime = null
    }
}
~~~

----

## FILE: src/ConcurrentLockUtil.groovy
~~~
package com.panintelligence.cache.util.ttl

import groovy.transform.CompileStatic
import groovy.transform.Immutable
import groovy.transform.stc.ClosureParams
import groovy.transform.stc.SimpleType
import org.apache.commons.lang3.StringUtils

import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.locks.ReentrantLock

/**
 * (C) Copyright panintelligence Ltd
 *
 * @since 03/11/2024
 * @author ming.huang
 */
@CompileStatic
@Immutable(copyWith = true)
class ConcurrentLockUtil {

    static final ReentrantLock getLock(ConcurrentHashMap<String, ReentrantLock> locks, String key) {
        if (key == null) return null
        return locks.computeIfAbsent(key, { new ReentrantLock() })
    }

    static void runWithLock(ConcurrentHashMap<String, ReentrantLock> locks, String key, @ClosureParams(value = SimpleType, options = ["java.lang.Object"]) Closure runFn) {
        if (StringUtils.isBlank(key)) return
        ReentrantLock lock = getLock(locks, key)
        lock.lock()
        try {
            runFn()
        } finally {
            lock.unlock()
        }
    }
}
~~~

----

## FILE: test/ExpirableObjectMapConcurrentSpec.groovy
~~~
package com.panintelligence.cache.util.ttl


import spock.lang.Specification
import spock.lang.Timeout

import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.ConcurrentMap
import java.util.concurrent.TimeUnit
import java.util.concurrent.locks.ReentrantLock

/**
 * (C) Copyright panintelligence Ltd
 *
 * @since 29/11/2023
 * @author ming.huang
 */
class ExpirableObjectMapConcurrentSpec extends Specification {

    @Timeout(value = 5, unit = TimeUnit.SECONDS)
    def "Test getObject - concurrency"() {
        given:
        List<Thread> threads = []
        ExpirableObjectMap<String> map = ExpirableObjectMap.create(5, true)

        ConcurrentMap<String, String> processingCounter = new ConcurrentHashMap<>()
        Closure runIt = { String key ->
            return ExpirableObjectMap.<String> getObject(map, key, new Date(), {
                processingCounter.put(key, key)
                Thread.sleep(100) // simulates processing
                return key // note: if this returns null, it runs more than TWICE (see `then:`) because it assumes there isn't any cache, so it runs fetchFn
            })
        }

        when:
        (1..50).each {
            threads << Thread.start { runIt('hello') }
            threads << Thread.start { runIt('hello') }
            threads << Thread.start { runIt('hello1') }
            threads << Thread.start { runIt('hello') }
            threads << Thread.start { runIt('hello1') }
        }

        threads*.join()

        then:
        assert processingCounter.keySet().size() == 2 // TWICE because there are only 2 unique keys
    }

    @Timeout(value = 5, unit = TimeUnit.SECONDS)
    def "Test getLock - in concurrency mode - to verify if the same key returns the same lock"() {
        given:
        List<Thread> threads = []
        ExpirableObjectMap<String> map = ExpirableObjectMap.create(5, true)

        ConcurrentMap<String, String> lockIdentities = new ConcurrentHashMap<>()
        Closure runIt = { String key ->
            ReentrantLock lock = ExpirableObjectMap.getLock(map, key)
            String id = "${key} ${lock.hashCode()}".toString() // this somehow needs to be a variable, otherwise lockIdentities has an extra 'null' item
            lockIdentities.put(id, id)
        }

        when:
        (1..50).each {
            threads << Thread.start { runIt('hello') }
            threads << Thread.start { runIt('hello') }
            threads << Thread.start { runIt('hello1') }
            threads << Thread.start { runIt('hello') }
            threads << Thread.start { runIt('hello1') }
        }

        threads*.join()

        then:
        assert lockIdentities.keySet().size() == 2
    }

    @Timeout(value = 5, unit = TimeUnit.SECONDS)
    def "Test clearing while locking"() {
        List<Thread> threads = []
        List<String> threadExecutedOrder = []
        ExpirableObjectMap<String> map = ExpirableObjectMap.create(5, true)
        Closure runIt = { String identifier, String key, String value, Integer sleepTime ->
            return ExpirableObjectMap.<String> getObject(map, key, new Date(), {
                Thread.sleep(sleepTime) // simulates processing
                threadExecutedOrder.add(identifier)
                return value // note: if this returns null, it runs more than TWICE (see `then:`) because it assumes there isn't any cache, so it runs fetchFn
            })
        }

        given:
        runIt('Thread0', 'k1', 'v1', 0)
        assert map.locks.keySet().toList() == ['k1']
        assert map.map.keySet().toList() == ['k1']

        and: 'Thread1'
        String thread1PreLockKeys = null
        String thread1PreMapKeys = null
        String thread1Data = null
        String thread1PostLockKeys = null
        String thread1PostMapKeys = null
        String thread1PostMapValues = null
        threads << Thread.start {
            thread1PreLockKeys = map.locks.keySet().join(', ') // 'k1' - this happens before emptyCache()
            thread1PreMapKeys = map.map.keySet().join(', ')
            thread1Data = runIt('Thread1', 'k2', 'v2a', 400)
            println 'step 2'
            thread1PostLockKeys = map.locks.keySet().join(', ') // the lock for this request is no longer present in map.locks, so it is empty. the lock is to lock a key, not to lock map.map
            thread1PostMapKeys = map.map.keySet().join(', ') // after runIt(), which takes 200ms, the value is set to map.map,
            thread1PostMapValues = map.map.values()*.object.join(', ') // This overrides the value set by Thread2
        }

        and: 'emptyCache()'
        Thread.sleep(100) // To make sure Thread1 starts before emptyCache()
        map.emptyCache()
        assert map.locks.keySet().size() == 0 // this happens after Thread1 is started. The lock is created, it does not assign back to map.locks, so This makes Thread1 k1 lock detached from map.locks
        assert map.map.keySet().size() == 0 // this happens after Thread1 is started, before Thread1 sets 'v2a' to this map

        threads*.join()

        expect:
        assert map.locks.keySet().size() == 0 // emptyCache() removes the lock
        assert map.map.keySet().size() == 1 // a value is set to a new map created by emptyCache()

        and:
        assert thread1PreLockKeys == 'k1'
        assert thread1PreMapKeys == 'k1'
        assert thread1Data == 'v2a'
        assert thread1PostLockKeys == ''
        assert thread1PostMapKeys == 'k2'
        assert thread1PostMapValues == 'v2a'
        and:
        assert threadExecutedOrder == [
                'Thread0',
                'Thread1'
        ]
    }

    @Timeout(value = 5, unit = TimeUnit.SECONDS)
    def "Test clearing while locking - having an extra thread"() {
        List<Thread> threads = []
        List<String> threadExecutedOrder = []
        ExpirableObjectMap<String> map = ExpirableObjectMap.create(5, true)
        Closure runIt = { String identifier, String key, String value, Integer sleepTime ->
            return ExpirableObjectMap.<String> getObject(map, key, new Date(), {
                Thread.sleep(sleepTime) // simulates processing
                threadExecutedOrder.add(identifier)
                return value // note: if this returns null, it runs more than TWICE (see `then:`) because it assumes there isn't any cache, so it runs fetchFn
            })
        }

        given:
        runIt('Thread0', 'k1', 'v1', 0)
        assert map.locks.keySet().toList() == ['k1']
        assert map.map.keySet().toList() == ['k1']

        and: 'Thread1'
        String thread1PreLockKeys = null
        String thread1PreMapKeys = null
        String thread1Data = null
        String thread1PostLockKeys = null
        String thread1PostMapKeys = null
        String thread1PostMapValues = null
        threads << Thread.start {
            thread1PreLockKeys = map.locks.keySet().join(', ') // 'k1' - this happens before emptyCache()
            thread1PreMapKeys = map.map.keySet().join(', ')
            thread1Data = runIt('Thread1', 'k2', 'v2a', 400)
            thread1PostLockKeys = map.locks.keySet().join(', ') // the lock for this request is no longer present in map.locks, so it is empty. the lock is to lock a key, not to lock map.map
            thread1PostMapKeys = map.map.keySet().join(', ') // after runIt(), which takes 200ms, the value is set to map.map,
            thread1PostMapValues = map.map.values()*.object.join(', ') // This overrides the value set by Thread2
        }

        and: 'emptyCache()'
        Thread.sleep(100) // To make sure Thread1 starts before emptyCache()
        map.emptyCache()
        assert map.locks.keySet().size() == 0 // this happens after Thread1 is started. The lock is created, it does not assign back to map.locks, so This makes Thread1 k1 lock detached from map.locks
        assert map.map.keySet().size() == 0 // this happens after Thread1 is started, before Thread1 sets 'v2a' to this map

        and: 'Thread2'
        String thread2Data = null
        String thread2PostLockKeys = null
        String thread2PostMapKeys = null
        String thread2PostMapValues = null
        threads << Thread.start {
            thread2Data = runIt('Thread2', 'k2', 'v2b', 200) // this creates a new lock for 'k2', this is different from `Thread1 'k2' lock`, so `Thread1 'k2' lock` does not block this
            thread2PostLockKeys = map.locks.keySet().join(', ') // This is `Thread2 'k2' lock`
            thread2PostMapKeys = map.map.keySet().join(', ')
            thread2PostMapValues = map.map.values()*.object.join(', ') // at this point, Thread1 is not finished
        }

        threads*.join()

        expect:
        assert map.locks.keySet().size() == 1
        assert map.map.keySet().size() == 1

        and:
        assert thread1PreLockKeys == 'k1'
        assert thread1PreMapKeys == 'k1'
        assert thread1Data == 'v2a'
        assert thread1PostLockKeys == 'k2' // NOTE: this is different from the previous test, Thread2 puts this key into locks
        assert thread1PostMapKeys == 'k2'
        assert thread1PostMapValues == 'v2a'
        and:
        assert thread2Data == 'v2b'
        assert thread2PostLockKeys == 'k2'
        assert thread2PostMapKeys == 'k2'
        assert thread2PostMapValues == 'v2b'
        and:
        assert threadExecutedOrder == [
                'Thread0',
                'Thread2', // since cache and lock are cleared, Thread1 does not block Thread2
                'Thread1'
        ]
    }
}
~~~

----

## FILE: test/ExpirableObjectMapSpec.groovy
~~~
package com.panintelligence.cache.util.ttl

import com.panintelligence.MisUser
import com.panintelligence.util.PiDateUtil
import spock.lang.Shared
import spock.lang.Specification
import spock.lang.Unroll

/**
 * (C) Copyright panintelligence Ltd
 *
 * @since 29/11/2023
 * @author ming.huang
 */
class ExpirableObjectMapSpec extends Specification {

    @Shared
    static final int processingTime = 10 // the processing time
    @Shared
    static final int validPeriod = 4999 // lower than the 5 seconds cache period
    @Shared
    static final int validPeriod2 = 5009 // lower than 5 seconds cache period + processing time
    @Shared
    static final int invalidPeriod = 6000 // higher than 5 seconds cache period + processing time, the actual test time can be longer, so we set it to +1s to allow the test to run slowly

    @Unroll
    def "Test getObject"() {
        given:
        Date requestTime1 = new Date(0)
        Date requestTime2 = PiDateUtil.createDate(requestTime1, toAdd)
        and:
        ExpirableObjectMap<MisUser> map = ExpirableObjectMap.create(5, true)
        ExpirableObjectMap.<MisUser> getObject(map, key1, requestTime1, {
            Thread.sleep(processingTime)
            return new MisUser()
        })

        and:
        boolean usesCache = true

        when:
        MisUser user = ExpirableObjectMap.<MisUser> getObject(map, key2, requestTime2, {
            usesCache = false
            Thread.sleep(processingTime)
            return new MisUser()
        })

        then:
        assert user
        assert usesCache == shouldUseCache
        assert map.map.size() == mapSize
        and:
        map.removeCache(key1)
        assert map.map.size() == mapSizeAfterRemovingKey1
        and:
        map.removeCache(key2)
        assert map.map.size() == mapSizeAfterRemovingKey2

        where:
        toAdd         | key1 | key2 | shouldUseCache | mapSize | mapSizeAfterRemovingKey1 | mapSizeAfterRemovingKey2
        validPeriod   | 'x'  | 'x'  | true           | 1       | 0                        | 0
        validPeriod2  | 'x'  | 'x'  | true           | 1       | 0                        | 0
        invalidPeriod | 'x'  | 'x'  | false          | 1       | 0                        | 0
        validPeriod   | 'x'  | 'y'  | false          | 2       | 1                        | 0
        validPeriod2  | 'x'  | 'y'  | false          | 2       | 1                        | 0
        invalidPeriod | 'x'  | 'y'  | false          | 2       | 1                        | 0
    }

    @Unroll
    def "Test getObject - false"() {
        given:
        Date requestTime1 = new Date(0)
        Date requestTime2 = PiDateUtil.createDate(requestTime1, validPeriod)
        and:
        ExpirableObjectMap<Boolean> map = ExpirableObjectMap.create(5, true)
        ExpirableObjectMap.<Boolean> getObject(map, 'x', requestTime1, {
            return false
        })

        and:
        boolean usesCache = true

        when:
        Boolean value = ExpirableObjectMap.<Boolean> getObject(map, 'x', requestTime2, {
            usesCache = false
            return false
        })

        then:
        assert !value
        assert String.valueOf(value) == 'false'
        assert usesCache
    }

    @Unroll
    def "Test getObject - avoid null errors"() {
        given:
        ExpirableObjectMap<MisUser> map = ExpirableObjectMap.create(5, true)

        when:
        Object item1 = ExpirableObjectMap.<MisUser> getObject(map, 'hello', new Date(), { null })
        map.removeCache('hello')
        Object item2 = ExpirableObjectMap.<MisUser> getObject(map, 'hello', new Date(), { null })
        Object item3 = ExpirableObjectMap.<MisUser> getObject(map, null, new Date(), { null })

        then:
        item1 == null
        item2 == null
        item3 == null
    }

    @Unroll
    def "Test removeCache - null key"() {
        given:
        ExpirableObjectMap<MisUser> map = ExpirableObjectMap.create(5, true)

        when:
        map.removeCache(null) // just to make sure it doesn't fail

        then:
        true // no errors should occur
    }

    @Unroll
    def "Test getOrFetchAllowForcing"() {
        given:
        ExpirableObjectMap<Integer> map = ExpirableObjectMap.create(5, true)
        ExpirableObjectMap.<Integer> getObject(map, '1', new Date(), { 1 })

        when:
        boolean fetchDataExecuted1 = false
        Integer item1 = map.getOrFetchAllowForcing('1', true, {
            fetchDataExecuted1 = true
            return 2
        })

        boolean fetchDataExecuted2 = false
        Integer item2 = map.getOrFetchAllowForcing('1', false, {
            fetchDataExecuted12 = true
            return 3
        })

        then:
        assert fetchDataExecuted1
        assert !fetchDataExecuted2
        assert item1 == 2
        assert item2 == 2
    }

}
~~~

----

## FILE: test/ExpirableLongLifeCacheSpec.groovy
~~~
package com.panintelligence.cache.util.ttl

import com.panintelligence.util.PiDateUtil
import spock.lang.Specification
import spock.lang.Unroll

/**
 * (C) Copyright panintelligence Ltd
 *
 * @since 02/11/2024
 * @author ming.huang
 */
class ExpirableLongLifeCacheSpec extends Specification {

    static Date time0 = new Date(0)
    static Date time1CheckerExpired = PiDateUtil.createDate(time0, 1100) // at this point checker lift time has expired

    def "Test getObject - null key"() {
        given:
        CacheExpiryCondition expiryCondition = new CacheExpiryCondition<String, String>() {
            @Override
            boolean canStillUseCacheWhenCheckerExpires(ExpirableObject<String> cachedCheckerItem, String dbCheckerItem, ExpirableObject<String> cachedDataItem) {
                return true
            }
        }
        ExpirableLongLifeCache<String, String> cache = ExpirableLongLifeCache.<String, String> create(1, 5)

        and:
        boolean checkerIsRun = false
        boolean fetchDataIsRun = false
        String data = cache.getOrFetch(null, { // null key
            checkerIsRun = true
            return '1'
        }, { expiryCondition }, {
            fetchDataIsRun = true
            return '2'
        })

        expect:
        assert data == null
        assert !checkerIsRun
        assert !fetchDataIsRun
        assert cache.checkerCache.map.values()*.object == []
        assert cache.actualDataCache.map.values()*.object == []
    }

    def "Test getObject - checker null value"() {
        given:
        CacheExpiryCondition expiryCondition = new CacheExpiryCondition<String, String>() {
            @Override
            boolean canStillUseCacheWhenCheckerExpires(ExpirableObject<String> cachedCheckerItem, String dbCheckerItem, ExpirableObject<String> cachedDataItem) {
                return true
            }
        }
        ExpirableLongLifeCache<String, String> cache = ExpirableLongLifeCache.<String, String> create(1, 5)

        and:
        boolean checker1IsRun = false
        boolean fetchData1IsRun = false
        String data1 = cache.getOrFetch('1', {
            checker1IsRun = true
            return null // checker returns null, which invalidates the cache, e.g. you cache chart1, but when checking if chart1 exists, you get null
        }, { expiryCondition }, {
            fetchData1IsRun = true
            return 'Data1'
        })
        List<String> checkerValues1 = cache.checkerCache.map.values()*.object
        List<String> cacheValues1 = cache.actualDataCache.map.values()*.object

        and:
        boolean checker2IsRun = false
        boolean fetchData2IsRun = false
        String data2 = cache.getOrFetch('1', { // same key, should run checker
            checker2IsRun = true
            return 'Checker2' // this time checker returns data, so the next call would use the checker cache
        }, { expiryCondition }, {
            fetchData2IsRun = true
            return 'Data2'
        })
        List<String> checkerValues2 = cache.checkerCache.map.values()*.object
        List<String> cacheValues2 = cache.actualDataCache.map.values()*.object

        and:
        boolean checker3IsRun = false
        boolean fetchData3IsRun = false
        String data3 = cache.getOrFetch('1', { // same key, should run checker
            checker3IsRun = true
            return 'Checker3' // checker cache is not expired, so this would not be run
        }, { expiryCondition }, {
            fetchData3IsRun = true
            return 'Data3' // canUseCache() decides that cache is used, so this is not run
        })
        List<String> checkerValues3 = cache.checkerCache.map.values()*.object
        List<String> cacheValues3 = cache.actualDataCache.map.values()*.object

        expect:
        assert checker1IsRun
        assert !fetchData1IsRun // checker returns null, so cache call is not run. if cache for this key is present it would also be removed
        assert data1 == null // checker returns null, which means there is no relevant data, so data also returns null
        assert checkerValues1 == []
        assert cacheValues1 == []
        and:
        assert checker2IsRun
        assert fetchData2IsRun
        assert data2 == 'Data2'
        assert checkerValues2 == ['Checker2']
        assert cacheValues2 == ['Data2']
        and:
        assert !checker3IsRun
        assert !fetchData3IsRun
        assert data3 == 'Data2'
        assert checkerValues3 == ['Checker2']
        assert cacheValues3 == ['Data2']
    }

    def "Test getObject - checker returns null - should remove cache of this key for checker and actual data"() {
        given:
        CacheExpiryCondition expiryCondition = new CacheExpiryCondition<String, String>() {
            @Override
            boolean canStillUseCacheWhenCheckerExpires(ExpirableObject<String> cachedCheckerItem, String dbCheckerItem, ExpirableObject<String> cachedDataItem) {
                return true
            }
        }
        ExpirableLongLifeCache<String, String> cache = ExpirableLongLifeCache.<String, String> create(1, 5)

        and: // valid call
        boolean checker1IsRun = false
        boolean fetchData1IsRun = false
        String data1 = cache.getObject('1', time0, {
            checker1IsRun = true
            return 'Checker1'
        }, { expiryCondition }, {
            fetchData1IsRun = true
            return 'Data1'
        })
        List<String> checkerValues1 = cache.checkerCache.map.values()*.object
        List<String> cacheValues1 = cache.actualDataCache.map.values()*.object

        and:
        boolean checker2IsRun = false
        boolean fetchData2IsRun = false
        String data2 = cache.getObject('1', time1CheckerExpired, { // same key, should run checker
            checker2IsRun = true
            return null // this is going to delete the cache for both the checker and the actual data
        }, { expiryCondition }, {
            fetchData2IsRun = true
            return 'Data2'
        })
        List<String> checkerValues2 = cache.checkerCache.map.values()*.object
        List<String> cacheValues2 = cache.actualDataCache.map.values()*.object

        and: // valid call
        boolean checker3IsRun = false
        boolean fetchData3IsRun = false
        String data3 = cache.getObject('1', time1CheckerExpired, { // same key, should run checker
            checker3IsRun = true
            return 'Checker3' // checker cache is not expired, so this would not be run
        }, { expiryCondition }, {
            fetchData3IsRun = true
            return 'Data3' // canUseCache() decides that cache is used, so this is not run
        })
        List<String> checkerValues3 = cache.checkerCache.map.values()*.object
        List<String> cacheValues3 = cache.actualDataCache.map.values()*.object

        expect:
        assert checker1IsRun
        assert fetchData1IsRun
        assert data1 == 'Data1'
        assert checkerValues1 == ['Checker1']
        assert cacheValues1 == ['Data1']
        and:
        assert checker2IsRun
        assert !fetchData2IsRun
        assert data2 == null
        assert checkerValues2 == []
        assert cacheValues2 == []
        and:
        assert checker3IsRun
        assert fetchData3IsRun
        assert data3 == 'Data3'
        assert checkerValues3 == ['Checker3']
        assert cacheValues3 == ['Data3']
    }

    def "Test getObject - cache expired - should fetch data"() {
        given:
        CacheExpiryCondition expiryCondition = new CacheExpiryCondition<String, String>() {
            @Override
            boolean canStillUseCacheWhenCheckerExpires(ExpirableObject<String> cachedCheckerItem, String dbCheckerItem, ExpirableObject<String> cachedDataItem) {
                return false // expires the cache
            }
        }
        ExpirableLongLifeCache<String, String> cache = ExpirableLongLifeCache.<String, String> create(1, 5)

        and: // valid call
        boolean checker1IsRun = false
        boolean fetchData1IsRun = false
        String data1 = cache.getObject('1', time0, {
            checker1IsRun = true
            return 'Checker1'
        }, { expiryCondition }, {
            fetchData1IsRun = true
            return 'Data1'
        })
        List<String> checkerValues1 = cache.checkerCache.map.values()*.object
        List<String> cacheValues1 = cache.actualDataCache.map.values()*.object

        and:
        boolean checker2IsRun = false
        boolean fetchData2IsRun = false
        String data2 = cache.getObject('1', time1CheckerExpired, { // same key, should run checker
            checker2IsRun = true
            return 'Checker2' // this time checker returns data, so the next call would use the checker cache
        }, { expiryCondition }, {
            fetchData2IsRun = true
            return 'Data2'
        })
        List<String> checkerValues2 = cache.checkerCache.map.values()*.object
        List<String> cacheValues2 = cache.actualDataCache.map.values()*.object

        expect:
        assert checker1IsRun
        assert fetchData1IsRun
        assert data1 == 'Data1'
        assert checkerValues1 == ['Checker1']
        assert cacheValues1 == ['Data1']
        and:
        assert checker2IsRun
        assert fetchData2IsRun
        assert data2 == 'Data2'
        assert checkerValues2 == ['Checker2']
        assert cacheValues2 == ['Data2']
    }

    @Unroll
    def "Test getObject - no cache found 1st time"() {
        given:
        CacheExpiryCondition expiryCondition = new CacheExpiryCondition<String, String>() {
            @Override
            boolean canStillUseCacheWhenCheckerExpires(ExpirableObject<String> cachedCheckerItem, String dbCheckerItem, ExpirableObject<String> cachedDataItem) {
                return true // e.g. in some cases, it uses cachedCheckerItem and dbCheckerItem to decide if we can use the cache
            }
        }
        ExpirableLongLifeCache<String, String> cache = ExpirableLongLifeCache.<String, String> create(1, 5)

        and: // valid call
        boolean checker1IsRun = false
        boolean fetchData1IsRun = false
        String data1 = cache.getObject('1', time0, {
            checker1IsRun = true
            return 'Checker1'
        }, { expiryCondition }, {
            fetchData1IsRun = true
            return null
        })
        List<String> checkerValues1 = cache.checkerCache.map.values()*.object
        List<String> cacheValues1 = cache.actualDataCache.map.values()*.object

        and:
        boolean checker2IsRun = false
        boolean fetchData2IsRun = false
        String data2 = cache.getObject('1', secondRequestTime, { // same key, should run checker
            checker2IsRun = true
            return 'Checker2' // this time checker returns data, so the next call would use the checker cache
        }, { expiryCondition }, {
            fetchData2IsRun = true
            return 'Data2'
        })
        List<String> checkerValues2 = cache.checkerCache.map.values()*.object
        List<String> cacheValues2 = cache.actualDataCache.map.values()*.object

        expect:
        assert checker1IsRun
        assert fetchData1IsRun
        assert data1 == null
        assert checkerValues1 == ['Checker1']
        assert cacheValues1 == [null]
        and:
        switch (resultScenario) {
            case 'scenario1':
                assert !checker2IsRun
                assert fetchData2IsRun
                assert data2 == 'Data2'
                assert checkerValues2 == ['Checker1']
                assert cacheValues2 == ['Data2']
                break
            case 'scenario2':
                assert checker2IsRun
                assert fetchData2IsRun
                assert data2 == 'Data2'
                assert checkerValues2 == ['Checker2']
                assert cacheValues2 == ['Data2']
        }

        where:
        secondRequestTime   | resultScenario
        time0               | 'scenario1'
        time1CheckerExpired | 'scenario2'
    }
}
~~~

----

## FILE: test/ExpirableLongLifeCacheConcurrentSpec.groovy
~~~
package com.panintelligence.cache.util.ttl

import com.panintelligence.util.PiDateUtil
import spock.lang.Specification
import spock.lang.Timeout

import java.util.concurrent.TimeUnit

/**
 * (C) Copyright panintelligence Ltd
 *
 * @since 02/11/2024
 * @author ming.huang
 */
class ExpirableLongLifeCacheConcurrentSpec extends Specification {

    @Timeout(value = 5, unit = TimeUnit.SECONDS)
    def "Test getObject - make sure only 1 thread can fetch data"() {
        // 1st thread, checker wait
        // other threads (same key), call checker
        // nothing should be allowed to run fetch data until 1st thread releases the lock
        given:
        List<Thread> threads = []
        List executedOrder = []
        List dataReturned = []
        and:
        Date requestTime1 = new Date(0)
        Date requestTime2 = PiDateUtil.createDate(requestTime1, 2000) // at this point checker lift time has expired
        and:
        CacheExpiryCondition expiryCondition = new CacheExpiryCondition<Object, Object>() {
            @Override
            boolean canStillUseCacheWhenCheckerExpires(ExpirableObject<Object> cachedCheckerItem, Object dbCheckerItem, ExpirableObject<Object> cachedDataItem) {
                return true
            }
        }
        ExpirableLongLifeCache cache = ExpirableLongLifeCache.create(1, 5)

        and:
        long initialCheckerCacheTime = 0
        threads << Thread.start {
            dataReturned << cache.getObject('1', requestTime1, {
                Thread.sleep(200)
                executedOrder.add('Key1 Step1')
                initialCheckerCacheTime = System.currentTimeMillis()
                return 1
            }, { expiryCondition }, {
                executedOrder.add('Key1 Step1 Data')
                return 2
            })
        }

        and:
        Thread.sleep(50) // make sure the rest runs after the thread above is started - in IDE when running the test 1st time, the next thread can start quicker than the line above
        (3..5).each { Integer num ->
            threads << Thread.start {
                dataReturned << cache.getObject('1', requestTime1, {
                    long checkerRunTime = System.currentTimeMillis()
                    long timeDiff = checkerRunTime - initialCheckerCacheTime // if timeDiff > 1s (checkerShortLifeTime), this test fail because it runs too slow
                    executedOrder.add("ERROR - Checker cache has not expired, should not fetch data - item ${num}, unless timeDiff ${timeDiff}ms > 1s")
                    return 1
                }, { expiryCondition }, {
                    executedOrder.add("ERROR - Should use cache, should not fetch data - item ${num}")
                    return 100
                })
            }
        }

        and:
        threads << Thread.start {
            dataReturned << cache.getObject('2', requestTime1, {
                executedOrder.add("Key2 Step1")
                return 1
            }, { expiryCondition }, {
                executedOrder.add('Key2 Step1 Data')
                return 1000
            })
        }

        threads*.join()

        // this uses requestTime2, so checker cache has expired
        threads << Thread.start {
            dataReturned << cache.getObject('1', requestTime2, {
                executedOrder.add("Key1 Step6")
                return 1
            }, { expiryCondition }, {
                executedOrder.add('ERROR - Should use cache, should not fetch data')
                return 200
            })
        }

        threads*.join()

        expect:
        assert executedOrder == [
                'Key2 Step1',
                'Key2 Step1 Data',
                'Key1 Step1',
                'Key1 Step1 Data',
                'Key1 Step6',
        ]
        assert dataReturned == [1000, 2, 2, 2, 2, 2]
    }
}
~~~

----

## FILE: test/ExpirableObjectNestedMapSpec.groovy
~~~
package com.panintelligence.cache.util.ttl

import com.panintelligence.MisUser
import com.panintelligence.util.PiDateUtil
import spock.lang.Shared
import spock.lang.Specification
import spock.lang.Unroll

/**
 * (C) Copyright panintelligence Ltd
 *
 * @since 29/11/2023
 * @author ming.huang
 */
class ExpirableObjectNestedMapSpec extends Specification {

    @Shared
    static final int processingTime = 10 // the processing time
    @Shared
    static final int validPeriod = 4999 // lower than the 5 seconds cache period
    @Shared
    static final int validPeriod2 = 5009 // lower than 5 seconds cache period + processing time
    @Shared
    static final int invalidPeriod = 6000 // higher than 5 seconds cache period + processing time, the actual test time can be longer, so we set it to +1s to allow the test to run slowly

    @Unroll
    def "Test getObject - same parent key"() {
        given:
        Date requestTime1 = new Date(0)
        Date requestTime2 = PiDateUtil.createDate(requestTime1, toAdd)
        and:
        ExpirableObjectNestedMap<MisUser> map = ExpirableObjectNestedMap.create(5, false)
        ExpirableObjectNestedMap.<MisUser> getObject(map, key1, nestedKey1, requestTime1, {
            Thread.sleep(processingTime)
            return new MisUser()
        })

        and:
        boolean usesCache = true

        when:
        MisUser user = ExpirableObjectNestedMap.<MisUser> getObject(map, key1, nestedKey2, requestTime2, {
            usesCache = false
            Thread.sleep(processingTime)
            return new MisUser()
        })

        then:
        assert user
        assert usesCache == shouldUseCache
        assert map.map.size() == mapSize
        assert map.map.values()*.map*.values().flatten().size() == mapTotalSize
        and:
        map.removeCache(key1)
        assert map.map.size() == mapSizeAfterRemovingKey1

        where:
        toAdd         | key1 | nestedKey1 | nestedKey2 | shouldUseCache | mapSize | mapTotalSize | mapSizeAfterRemovingKey1
        validPeriod   | 'x'  | '1'        | '1'        | true           | 1       | 1            | 0
        validPeriod2  | 'x'  | '1'        | '1'        | true           | 1       | 1            | 0
        invalidPeriod | 'x'  | '1'        | '1'        | false          | 1       | 1            | 0
        validPeriod   | 'x'  | '1'        | '2'        | false          | 1       | 2            | 0
        validPeriod2  | 'x'  | '1'        | '2'        | false          | 1       | 2            | 0
        invalidPeriod | 'x'  | '1'        | '2'        | false          | 1       | 2            | 0
    }

    @Unroll
    def "Test getObject - different parent key"() {
        given:
        Date requestTime1 = new Date(0)
        Date requestTime2 = PiDateUtil.createDate(requestTime1, toAdd)
        and:
        ExpirableObjectNestedMap<MisUser> map = ExpirableObjectNestedMap.create(5, false)
        ExpirableObjectNestedMap.<MisUser> getObject(map, key1, nestedKey1, requestTime1, {
            Thread.sleep(processingTime)
            return new MisUser()
        })

        and:
        boolean usesCache = true

        when:
        MisUser user = ExpirableObjectNestedMap.<MisUser> getObject(map, key2, nestedKey1, requestTime2, {
            usesCache = false
            Thread.sleep(processingTime)
            return new MisUser()
        })

        then:
        assert user
        assert usesCache == shouldUseCache
        assert map.map.size() == mapSize
        assert map.map.values()*.map*.values().flatten().size() == mapTotalSize
        and:
        map.removeCache(key1)
        assert map.map.size() == mapSizeAfterRemovingKey1
        and:
        map.removeCache(key2)
        assert map.map.size() == mapSizeAfterRemovingKey2

        where:
        toAdd         | key1 | key2 | nestedKey1 | shouldUseCache | mapSize | mapTotalSize | mapSizeAfterRemovingKey1 | mapSizeAfterRemovingKey2
        validPeriod   | 'x'  | 'x'  | '1'        | true           | 1       | 1            | 0                        | 0
        validPeriod2  | 'x'  | 'x'  | '1'        | true           | 1       | 1            | 0                        | 0
        invalidPeriod | 'x'  | 'x'  | '1'        | false          | 1       | 1            | 0                        | 0
        validPeriod   | 'x'  | 'y'  | '1'        | false          | 2       | 2            | 1                        | 0
        validPeriod2  | 'x'  | 'y'  | '1'        | false          | 2       | 2            | 1                        | 0
        invalidPeriod | 'x'  | 'y'  | '1'        | false          | 2       | 2            | 1                        | 0
    }

    @Unroll
    def "Test getObject - avoid null errors"() {
        given:
        ExpirableObjectNestedMap<MisUser> map = ExpirableObjectNestedMap.create(5, false)

        when:
        Object item1 = ExpirableObjectNestedMap.<MisUser> getObject(map, 'hello', 'hello', new Date(), { null })
        map.removeCache('hello')
        Object item2 = ExpirableObjectNestedMap.<MisUser> getObject(map, 'hello', 'hello', new Date(), { null })
        Object item3 = ExpirableObjectNestedMap.<MisUser> getObject(map, null, null, new Date(), { null })

        then:
        item1 == null
        item2 == null
        item3 == null
    }
}
~~~

----

## FILE: test/ExpirableObjectSpec.groovy
~~~
package com.panintelligence.cache.util.ttl

import com.panintelligence.MisUser
import com.panintelligence.util.PiDateUtil
import spock.lang.Shared
import spock.lang.Specification
import spock.lang.Unroll

/**
 * (C) Copyright panintelligence Ltd
 *
 * @since 06/03/2023
 * @author ming.huang
 */
class ExpirableObjectSpec extends Specification {

    @Shared
    static final int processingTime = 10 // the processing time
    @Shared
    static final int validPeriod = 4999 // lower than the 5 seconds cache period
    @Shared
    static final int validPeriod2 = 5009 // lower than 5 seconds cache period + processing time
    @Shared
    static final int invalidPeriod = 6000 // higher than 5 seconds cache period + processing time, the actual test time can be longer, so we set it to +1s to allow the test to run slowly

    @Unroll
    def "Test isExpired"() {
        given:
        Date requestTime1 = new Date(0)
        Date requestTime2 = PiDateUtil.createDate(requestTime1, toAdd)

        expect:
        assert ExpirableObject.isExpired(requestTime1, requestTime2, 5) == isExpired

        where:
        toAdd         | isExpired
        validPeriod   | false
        invalidPeriod | true
    }

    @Unroll
    def "Test getActiveObjectOrFetchNew"() {
        given:
        Date requestTime1 = new Date(0)
        Date requestTime2 = PiDateUtil.createDate(requestTime1, toAdd)
        Date requestTime3 = PiDateUtil.createDate(requestTime1, 7000) // if not adding another 5s, this would definitely expire
        and:
        ExpirableObject<MisUser> expirableUser = ExpirableObject.create(5, canExtendLifeTime)
        ExpirableObject.<MisUser> getActiveObjectOrFetchNew(expirableUser, requestTime1, {
            Thread.sleep(processingTime)
            return new MisUser()
        })
        Date actualRequestTime1 = expirableUser.lastRequestedTime
        assert actualRequestTime1.time >= (requestTime1.time + processingTime)

        and:
        boolean usesCache1 = true
        boolean usesCache2 = true

        when: // if canExtendLifeTime == true: this request is going to add another 5s to extend the cache time
        MisUser user1 = ExpirableObject.<MisUser> getActiveObjectOrFetchNew(expirableUser, requestTime2, {
            usesCache1 = false
            Thread.sleep(processingTime)
            return new MisUser()
        })

        MisUser user2 = ExpirableObject.<MisUser> getActiveObjectOrFetchNew(expirableUser, requestTime3, {
            usesCache2 = false
            Thread.sleep(processingTime)
            return new MisUser()
        })

        then:
        assert user1
        assert usesCache1 == shouldUseCache1stTime
        and:
        assert user2
        assert usesCache2 == shouldUseCache2ndTime

        where:
        toAdd         | canExtendLifeTime | shouldUseCache1stTime | shouldUseCache2ndTime
        validPeriod   | true              | true                  | true
        validPeriod   | false             | true                  | false
        validPeriod2  | true              | true                  | true
        validPeriod2  | false             | true                  | false
        invalidPeriod | true              | false                 | true // uses cache because the previous request creates the cache, which has not expire
        invalidPeriod | false             | false                 | true // uses cache because the previous request creates the cache, which has not expire
    }

    @Unroll
    def "Test getActiveObjectOrFetchNew - false evaluation - empty list"() {
        given:
        Date requestTime1 = new Date(0)
        Date requestTime2 = PiDateUtil.createDate(requestTime1, toAdd)
        Date requestTime3 = PiDateUtil.createDate(requestTime1, 7000) // if not adding another 5s, this would definitely expire
        and:
        ExpirableObject<List<MisUser>> expirableUser = ExpirableObject.create(5, canExtendLifeTime)
        ExpirableObject.<List<MisUser>> getActiveObjectOrFetchNew(expirableUser, requestTime1, {
            Thread.sleep(processingTime)
            return []
        })
        Date actualRequestTime1 = expirableUser.lastRequestedTime
        assert actualRequestTime1.time >= (requestTime1.time + processingTime)

        and:
        boolean usesCache1 = true
        boolean usesCache2 = true

        when:
        List<MisUser> users1 = ExpirableObject.<List<MisUser>> getActiveObjectOrFetchNew(expirableUser, requestTime2, {
            usesCache1 = false
            Thread.sleep(processingTime)
            return []
        })

        and:
        List<MisUser> users2 = ExpirableObject.<List<MisUser>> getActiveObjectOrFetchNew(expirableUser, requestTime3, {
            usesCache2 = false
            Thread.sleep(processingTime)
            return []
        })

        then:
        assert users1 != null
        assert usesCache1 == shouldUseCache1stTime
        and:
        assert users2 != null
        assert usesCache2 == shouldUseCache2ndTime

        where:
        toAdd         | canExtendLifeTime | shouldUseCache1stTime | shouldUseCache2ndTime
        validPeriod   | true              | true                  | true
        validPeriod   | false             | true                  | false
        validPeriod2  | true              | true                  | true
        validPeriod2  | false             | true                  | false
        invalidPeriod | true              | false                 | true // uses cache because the previous request creates the cache, which has not expire
        invalidPeriod | false             | false                 | true // uses cache because the previous request creates the cache, which has not expire
    }

    @Unroll
    def "Test getActiveObjectOrFetchNew - false evaluation - false"() {
        given:
        Date requestTime1 = new Date(0)
        Date requestTime2 = PiDateUtil.createDate(requestTime1, toAdd)
        Date requestTime3 = PiDateUtil.createDate(requestTime1, 7000) // if not adding another 5s, this would definitely expire
        and:
        ExpirableObject<Boolean> expirableUser = ExpirableObject.create(5, canExtendLifeTime)
        ExpirableObject.<Boolean> getActiveObjectOrFetchNew(expirableUser, requestTime1, {
            Thread.sleep(processingTime)
            return false
        })
        Date actualRequestTime1 = expirableUser.lastRequestedTime
        assert actualRequestTime1.time >= (requestTime1.time + processingTime)

        and:
        boolean usesCache1 = true
        boolean usesCache2 = true

        when:
        Boolean value1 = ExpirableObject.<Boolean> getActiveObjectOrFetchNew(expirableUser, requestTime2, {
            usesCache1 = false
            Thread.sleep(processingTime)
            return false
        })

        and:
        Boolean value2 = ExpirableObject.<Boolean> getActiveObjectOrFetchNew(expirableUser, requestTime3, {
            usesCache2 = false
            Thread.sleep(processingTime)
            return false
        })

        then:
        assert value1 != null
        assert String.valueOf(value1) == 'false'
        assert usesCache1 == shouldUseCache1stTime
        and:
        assert value2 != null
        assert String.valueOf(value2) == 'false'
        assert usesCache2 == shouldUseCache2ndTime

        where:
        toAdd         | canExtendLifeTime | shouldUseCache1stTime | shouldUseCache2ndTime
        validPeriod   | true              | true                  | true
        validPeriod   | false             | true                  | false
        validPeriod2  | true              | true                  | true
        validPeriod2  | false             | true                  | false
        invalidPeriod | true              | false                 | true // uses cache because the previous request creates the cache, which has not expire
        invalidPeriod | false             | false                 | true // uses cache because the previous request creates the cache, which has not expire
    }

    @Unroll
    def "Test clear"() {
        given:
        Date lastRequestedTime = new Date(0)
        Date requestedTime = PiDateUtil.createDate(lastRequestedTime, validPeriod)
        and:
        ExpirableObject<MisUser> expirableUser = ExpirableObject.create(5, true)
        ExpirableObject.<MisUser> getActiveObjectOrFetchNew(expirableUser, lastRequestedTime, { new MisUser() })
        and:
        boolean usesCache = true
        and:
        expirableUser.clear()

        when:
        ExpirableObject.<MisUser> getActiveObjectOrFetchNew(expirableUser, requestedTime, {
            usesCache = false
            return new MisUser()
        })

        then:
        assert !usesCache
    }
}
~~~

----

## FILE: LongLifeCacheCreator.groovy
~~~
package com.panintelligence.cache

import com.panintelligence.MisDataSourceItem
import com.panintelligence.api.column.ReadOnlyColumnsDomainBundle
import com.panintelligence.cache.util.ttl.CacheExpiryCondition
import com.panintelligence.cache.util.ttl.ExpirableLongLifeCache
import com.panintelligence.cache.util.ttl.ExpirableObject
import groovy.transform.CompileStatic
import groovy.transform.Immutable

/**
 * Creates {@link ExpirableLongLifeCache} and define the {@link CacheExpiryCondition} for each cache.
 *
 * (C) Copyright panintelligence Ltd
 *
 * @since 02/11/2024
 * @author ming.huang
 */
@CompileStatic
@Immutable()
class LongLifeCacheCreator {

    static CacheExpiryCondition createExpiryConditionForColumnBundle() {
        CacheExpiryCondition expiryCondition = new CacheExpiryCondition<List<MisDataSourceItem>, ReadOnlyColumnsDomainBundle>() {
            @Override
            boolean canStillUseCacheWhenCheckerExpires(ExpirableObject<List<MisDataSourceItem>> cachedCheckerItem, List<MisDataSourceItem> dbCheckerItem, ExpirableObject<ReadOnlyColumnsDomainBundle> cachedDataItem) {
                if (!cachedDataItem?.object?.dataSourceItem) return false
                if (dbCheckerItem == null || dbCheckerItem.empty) return false
                boolean childHasExpired = dbCheckerItem[0].updatedAtMs > cachedDataItem.object.dataSourceItem.updatedAtMs
                boolean parentHasExpired = (dbCheckerItem[1] && cachedDataItem.object.baseDataSourceItem) ? (dbCheckerItem[1].updatedAtMs > cachedDataItem.object.baseDataSourceItem.updatedAtMs) : false
                return !childHasExpired && !parentHasExpired
            }
        }
        return expiryCondition
    }
}
~~~

----

## FILE: StatefulDataSourceItemStoreService.groovy
~~~
package com.panintelligence.stateful


import com.panintelligence.MisDataSourceItem
import com.panintelligence.api.column.ReadOnlyColumnsDomainBundle
import com.panintelligence.cache.LongLifeCacheCreator
import com.panintelligence.cache.util.ttl.CacheExpiryCondition
import com.panintelligence.cache.util.ttl.ExpirableLongLifeCache
import com.panintelligence.gorm.GormDataSourceItemService
import groovy.transform.CompileStatic

/**
 * This class is stateful. It's needed so that:
 * 1) different requests - refreshing a category that makes 20 requests at the same time does not need to hit the db to get the same e.g. connection many times
 * 2) same request - the same request e.g. to get a chart only needs to hit the db once when getting a bundle
 *
 * Objects returned are discarded, so editors would never use this service.
 * If a user enters an editor, and try to edit something (not using the cache), by the time they exit the editor, the 5 seconds cache is long gone.
 *
 * (C) Copyright panintelligence Ltd
 *
 * @since 15/12/2018
 * @author ming.huang
 */
class StatefulDataSourceItemStoreService {

    static transactional = false
    private static final int ALIVE_IN_SECONDS = 5 // it definitely takes more than 5 second for a human to enter the edit connection screen, change it, then go to the dashboard to load charts
    private static final int ALIVE_IN_SECONDS__VERY_LONG = 50 * 60 // longer than cache clearing thread

    GormDataSourceItemService gormDataSourceItemService

    private ExpirableLongLifeCache<List<MisDataSourceItem>, ReadOnlyColumnsDomainBundle> columnBundleCache = ExpirableLongLifeCache.<List<MisDataSourceItem>, ReadOnlyColumnsDomainBundle> create(ALIVE_IN_SECONDS, ALIVE_IN_SECONDS__VERY_LONG)

    /**
     * @param dataSourceItemId can be null when this is called to get a columns bundle without the need of restricting to a particular connection
     */
    @CompileStatic
    ReadOnlyColumnsDomainBundle getBundle(Integer dataSourceItemId) {
        if (!dataSourceItemId) return ReadOnlyColumnsDomainBundle.createEmpty() // when doing GrailsSwapService.swap(), and #~Object~# is not supported, `dataSourceItemId` is set to null
        String key = "$dataSourceItemId"
        ReadOnlyColumnsDomainBundle data = columnBundleCache.getOrFetch(key, {
            return MisDataSourceItem.findCurrentAndParentConnections(dataSourceItemId) // 1st: current, 2nd: parent - the order matters here
        }, {
            CacheExpiryCondition expiryCondition = LongLifeCacheCreator.createExpiryConditionForColumnBundle()
            return expiryCondition
        }, {
            // the service call can return null, so fallback to an empty bundle to avoid null pointer errors
            return gormDataSourceItemService.fetchReadOnlyColumnsDomainBundle(dataSourceItemId) ?: ReadOnlyColumnsDomainBundle.createEmpty()
        })
        return data ?: ReadOnlyColumnsDomainBundle.createEmpty()
    }

    void clearLongLifeCache() {
        columnBundleCache.emptyCache()
    }
}
~~~

----

