# Session Management & Multi-User Support

## Overview

The system now supports **isolated per-session conversation memory** to prevent cross-user data leakage and enable proper multi-user support.

## Key Features

### ✅ Per-Session Conversation Memory

- **Each user gets their own isolated conversation context**
- **No cross-user data leakage** - User A's queries won't appear in User B's context
- **Session-based storage** using Socket.IO session IDs (`request.sid`)
- **Automatic cleanup** when users disconnect

### ✅ Session Isolation

1. **Socket.IO Session IDs**: Each WebSocket connection gets a unique session ID
2. **Per-Session Memory**: `session_memories[session_id] = ConversationMemory()`
3. **Isolated Context**: Each query uses only that session's conversation history
4. **Clean Disconnect**: Memory is cleaned up when user disconnects

## Implementation Details

### Session Memory Storage

```python
# Per-session conversation memory
session_memories = {
    'session_id_1': ConversationMemory(),
    'session_id_2': ConversationMemory(),
    # ... one per active user
}
```

### How It Works

1. **User Connects**: Socket.IO assigns unique `session_id` (e.g., `aX9HYtRgypX-50ENAAAB`)
2. **First Query**: System creates `ConversationMemory()` for that session
3. **Subsequent Queries**: Uses that session's memory for context
4. **User Disconnects**: Memory is automatically cleaned up

### Code Flow

```python
# Get session-specific memory
session_id = request.sid  # Socket.IO session ID
session_memory = get_session_memory(session_id)

# Get conversation context for this session only
conversation_context = session_memory.get_context()

# Use in RAG query
response, results, has_more, total_count = rag.query_rag_with_images(
    query, 
    conversation_context=conversation_context  # Session-specific!
)

# Update session memory
session_memory.add_message("user", query)
session_memory.add_message("assistant", response)
```

## Multi-User Support

### ✅ Supports 100+ Concurrent Users

**Current Architecture:**
- **Socket.IO**: Handles WebSocket connections (scales to 1000s of concurrent connections)
- **Per-Session Memory**: Lightweight in-memory storage (minimal overhead)
- **Shared RAG Instance**: Single instance shared across all users (efficient)
- **Session Cleanup**: Automatic cleanup prevents memory leaks

### Memory Usage

- **Per Session**: ~1-5 KB (20 messages max, ~200 chars each)
- **100 Users**: ~100-500 KB total (negligible)
- **1000 Users**: ~1-5 MB total (still very manageable)

### Scalability Considerations

**Current Setup (Good for 100-500 users):**
- In-memory session storage
- Single Flask-SocketIO server
- Shared RAG instance

**For 1000+ Users (Future Enhancements):**
- Consider Redis for session storage
- Load balancing with multiple Flask instances
- Session affinity/sticky sessions

## Data Isolation Guarantees

### ✅ Guaranteed Isolation

1. **Conversation Context**: Each user's conversation history is completely isolated
2. **Pending Queries**: Session-based (`pending_queries[session_id]`)
3. **Flask Sessions**: HTTP sessions are also isolated (for cart, user data)
4. **No Shared State**: No global conversation memory that could leak

### What's Shared (Safe)

- **RAG Instance**: Shared `rag` object (read-only, thread-safe)
- **ChromaDB**: Shared database (read-only queries)
- **CLU API**: Shared API client (stateless)
- **Gemini API**: Shared API client (stateless)

### What's Isolated (Per-Session)

- **Conversation Memory**: `session_memories[session_id]`
- **Pending Queries**: `pending_queries[session_id]`
- **Flask Sessions**: `session['cart']`, `session['verified_email']`, etc.

## Testing Multi-User Scenarios

### Test Case 1: Two Users, Same Query
```
User A: "Show me red shirts"
User B: "Show me red shirts"

Expected: Both get results, but User A's context doesn't affect User B
```

### Test Case 2: Context Continuity
```
User A: "Show me red shirts"
User A: "What about blue ones?"

Expected: User A's second query uses context from first query
User B: "Show me blue shirts"

Expected: User B gets fresh results (no context from User A)
```

### Test Case 3: Disconnect/Reconnect
```
User A: "Show me red shirts"
User A: Disconnects
User A: Reconnects (new session_id)
User A: "What about blue ones?"

Expected: No context (new session = fresh start)
```

## Performance Impact

### Minimal Overhead

- **Memory Lookup**: O(1) dictionary lookup (`session_memories[session_id]`)
- **Context Building**: O(n) where n = number of messages (max 20)
- **Total Overhead**: < 1ms per query

### Memory Management

- **Automatic Cleanup**: On disconnect
- **Message Limit**: Max 20 messages per session (then summarization)
- **No Memory Leaks**: Sessions are cleaned up on disconnect

## Troubleshooting

### Issue: Users seeing each other's context

**Check:**
1. Are you using `get_session_memory(session_id)`?
2. Is `conversation_context` being passed to RAG queries?
3. Are you updating `session_memory` after each exchange?

### Issue: Memory leaks

**Check:**
1. Is `handle_disconnect()` being called?
2. Are old sessions being cleaned up?
3. Check `len(session_memories)` - should match active connections

### Issue: Context not persisting

**Check:**
1. Is `session_memory.add_message()` being called?
2. Is `conversation_context` being retrieved before query?
3. Check if session_id is consistent across requests

## Future Enhancements

1. **Redis Backend**: For distributed session storage
2. **Session Persistence**: Save sessions to database for reconnection
3. **Session Analytics**: Track session duration, message counts
4. **Rate Limiting**: Per-session rate limiting
5. **Session Sharing**: Allow users to share session links

