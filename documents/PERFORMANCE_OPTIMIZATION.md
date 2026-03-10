# Performance Optimization Guide

## Issues Identified and Fixed

### 1. ⚠️ Image Enhancement (MAJOR BOTTLENECK)
**Problem**: Image enhancement was enabled by default and can take **minutes** per query
**Fix**: Disabled by default (`enhance_images=False`)
**Impact**: Saves 5-10+ minutes per query

### 2. ⚠️ Gemini API Timeout
**Problem**: No timeout, could hang indefinitely
**Fix**: Added 30-second timeout + faster generation config
**Impact**: Prevents infinite waits

### 3. ⚠️ Too Many Results
**Problem**: Fetching `num_results * 3` (45 results) then filtering
**Fix**: Reduced to `num_results * 2` (20 max) for initial search
**Impact**: Faster search operations

### 4. ⚠️ Re-ranking All Results
**Problem**: Re-ranking all results (expensive operation)
**Fix**: Limit re-ranking to top 20 results
**Impact**: Faster re-ranking (saves 1-5 seconds)

### 5. ⚠️ No Performance Monitoring
**Problem**: No visibility into slow operations
**Fix**: Added timing logs for each operation
**Impact**: Can identify bottlenecks

---

## Performance Optimizations Applied

### ✅ Image Enhancement Disabled
```python
# Before: enhance_images=True (default)
# After: enhance_images=False (default)
response, results, has_more, total_count = rag.query_rag_with_images(
    query, num_results=10, enhance_images=False  # Disabled for speed
)
```

### ✅ Reduced Search Results
```python
# Before: num_results * 3 = 45 results
# After: min(num_results * 2, 20) = 20 results max
all_results = self.search(enriched_query, n_results=20, ...)
```

### ✅ Limited Re-ranking
```python
# Before: Re-rank all results
# After: Re-rank only top 20
max_rerank = min(len(results), 20)
```

### ✅ Gemini API Timeout
```python
# Added 30-second timeout
response = model.generate_content(
    ...,
    request_options={"timeout": 30}
)

# Faster generation config
generation_config = {
    "max_output_tokens": 500,  # Limit length for speed
}
```

### ✅ Performance Logging
```python
# Now logs timing for each operation:
# - CLU call time
# - Search time
# - Re-ranking time
# - Gemini API time
# - Image enhancement time (if enabled)
```

---

## Expected Performance

### Before Optimizations:
- **Image enhancement**: 5-10+ minutes (if enabled)
- **Search**: 2-5 seconds
- **Re-ranking**: 2-5 seconds
- **Gemini API**: 3-10 seconds
- **Total**: 10+ minutes (with image enhancement)

### After Optimizations:
- **CLU call**: < 1 second
- **Search**: 1-3 seconds
- **Re-ranking**: 0.5-2 seconds (limited to 20 results)
- **Gemini API**: 2-5 seconds (with timeout)
- **Total**: **5-10 seconds** (without image enhancement)

---

## Further Optimizations (If Still Slow)

### 1. Disable Re-ranking (If Not Needed)
```python
response, results, has_more, total_count = rag.query_rag_with_images(
    query, num_results=10, use_rerank=False  # Disable re-ranking
)
```

### 2. Use Semantic Search Only (Skip Hybrid)
```python
response, results, has_more, total_count = rag.query_rag_with_images(
    query, num_results=10, use_hybrid=False  # Faster but less accurate
)
```

### 3. Reduce Number of Results
```python
response, results, has_more, total_count = rag.query_rag_with_images(
    query, num_results=5, ...  # Show fewer results
)
```

### 4. Enable Query Caching
Already implemented - repeated queries use cache (instant response)

### 5. Check CLU API Performance
If CLU is slow, the system falls back automatically, but you can:
- Check CLU quota/limits
- Monitor CLU response times
- Consider caching CLU results

---

## Monitoring Performance

Check logs for timing information:
```
🔍 Search completed in 0.99s (7 results)
⚠️ CLU call took 2.5s (slow)
⚠️ Search took 3.2s (slow)
⚠️ Re-ranking took 2.1s (slow)
⚠️ Gemini API call took 6.5s (slow)
```

If you see slow operations, you can:
1. Disable that feature (re-ranking, image enhancement)
2. Reduce number of results
3. Check network/API performance

---

## Quick Performance Checklist

- [x] Image enhancement disabled by default
- [x] Reduced search results (20 max)
- [x] Limited re-ranking (20 results)
- [x] Gemini API timeout (30s)
- [x] Performance logging enabled
- [x] Query caching enabled
- [ ] Consider disabling re-ranking if still slow
- [ ] Consider reducing num_results if still slow

---

## If Still Taking 10+ Minutes

Check these in order:

1. **Image Enhancement**: Make sure it's disabled (`enhance_images=False`)
2. **CLU API**: Check if quota exceeded or slow (logs will show)
3. **Gemini API**: Check if timing out (logs will show)
4. **Network**: Check server network connectivity
5. **Database**: Check ChromaDB performance
6. **Re-ranking**: Consider disabling if sentence-transformers is slow

The logs will tell you exactly which operation is slow!

