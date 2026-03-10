# Continue Button Logic - Implementation Guide

## Overview

The chatbot now has two distinct modes of operation:

1. **Send Button** (✈️ Send): Always starts a **NEW** query (fresh search, no conversation context)
2. **Continue Button** (🔁 Continue): Continues the **PREVIOUS** conversation with context awareness

## How It Works

### Send Button Logic

**Purpose**: Treat each query as independent, starting fresh.

**Implementation**:
```python
def update_chat(user_msg, history):
    # Process as a fresh query (no conversation context)
    full_text = rag.query_rag(user_msg, num_results=5, conversation_context=None)
```

**Behavior**:
- Each query is processed independently
- No reference to previous messages
- Always starts a new search
- Best for: New topics, unrelated queries, starting fresh

### Continue Button Logic

**Purpose**: Continue conversation with context from previous messages.

**Implementation**:
```python
def continue_from_previous(user_msg, history):
    # Build conversation context from last 3 exchanges
    conversation_context = build_conversation_context(history)
    
    # Process with conversation context
    full_text = rag.query_rag(enhanced_query, num_results=5, conversation_context=conversation_context)
```

**Behavior**:
- Uses last 3 exchanges (6 messages) for context
- Can work with or without new user input
- Maintains conversational flow
- Best for: Follow-up questions, getting more details, continuing discussion

## Conversation Context Building

### Context Extraction
- Gets last 6 messages (3 user + 3 assistant exchanges)
- Truncates long assistant responses to 200 chars
- Formats as: "User: ..." and "Assistant: ..."

### Context Usage
1. **Passed to RAG**: Included in structured data sent to Gemini
2. **Gemini Prompt**: Added as "Previous Conversation Context"
3. **Response Generation**: Gemini uses context to maintain flow

## Example Scenarios

### Scenario 1: New Query (Send Button)
```
User: "Show me green shirts"
Bot: [Shows green shirts]

User: "What about blue dresses?"  ← Send Button
Bot: [Shows blue dresses - no reference to green shirts]
```

### Scenario 2: Continue Conversation (Continue Button)
```
User: "Show me green shirts"
Bot: [Shows green shirts]

User: [Clicks Continue Button]
Bot: [Shows more green shirts or related items, references previous query]

OR

User: "Do you have them in size M?"  ← Continue Button
Bot: [Shows green shirts in size M, references previous conversation]
```

## Technical Details

### Function Signatures

**`query_rag(query, num_results=5, conversation_context=None)`**
- `query`: User's query string
- `num_results`: Number of results to retrieve
- `conversation_context`: Optional formatted conversation history

**`build_conversation_context(history)`**
- Takes chat history array
- Returns formatted string with recent messages
- Returns `None` if no history

**`generate_human_readable_response(user_question, structured_data, conversation_context=None)`**
- Enhanced to accept conversation context
- Adds context-aware instructions to Gemini prompt

## Key Features

1. **Context Window**: Last 3 exchanges (6 messages) for optimal balance
2. **Smart Fallback**: If no history, Continue acts like Send
3. **Flexible Input**: Continue works with or without new user input
4. **Context Truncation**: Long responses truncated to prevent token overflow
5. **Context Logging**: Console logs show when context is used

## Benefits

1. **Better User Experience**: Natural conversation flow
2. **Context Awareness**: Follow-up questions work better
3. **Flexibility**: Users can choose fresh search or continue
4. **Efficiency**: Context window limits prevent token bloat

## Usage Tips

### When to Use Send:
- Starting a new topic
- Unrelated queries
- Want fresh search results
- First query in session

### When to Use Continue:
- Follow-up questions
- Want more details about previous results
- Continuing discussion about same topic
- Refining previous search

## Implementation Files

- `app.py`: Gradio UI with Send/Continue buttons
- `app_flask.py`: Flask/SocketIO version (same logic)
- `geminiLLM.py`: Enhanced to accept conversation context

## Future Enhancements

1. **Session Management**: Store conversation history per session
2. **Context Summarization**: Summarize long conversations
3. **Context Relevance**: Filter context by relevance
4. **Multi-turn Refinement**: Better handling of iterative queries

