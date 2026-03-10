# Quick Start Guide - Advanced RAG System

## 🚀 Getting Started

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

**Note**: This will install large packages (PyTorch, transformers, etc.). May take 5-10 minutes.

### Step 2: Start the Chat Application

```bash
python app_flask.py
```

Visit: http://localhost:5000

### Step 3: Start Analytics Dashboard (Optional)

In a new terminal:

```bash
python analytics_dashboard.py
```

Visit: http://localhost:5001

---

## ✨ What's New?

### Automatic Features (No Configuration Needed)

1. **Hybrid Search** - Automatically combines semantic + keyword search
2. **Re-ranking** - Automatically re-ranks results for better quality
3. **Query Caching** - Automatically caches frequent queries
4. **Advanced Memory** - Automatically manages conversation context
5. **Analytics** - Automatically tracks all queries

### Optional Features

6. **Agentic Framework** - Use for complex queries
7. **Feedback System** - Record user feedback
8. **Multi-modal** - Image search (requires image embeddings)

---

## 📝 Usage Examples

### Basic Query (Automatic Hybrid + Re-ranking)

```python
# In app_flask.py - already configured
response = rag.query_rag("green shirts", use_hybrid=True, use_rerank=True)
```

### Using Agentic Framework

```python
# For complex queries like comparisons
response = agent.process_query("Compare prices of green and blue shirts")
```

### Recording Feedback

```python
feedback_system.record_feedback(
    query="green shirts",
    response="...",
    user_feedback="Not helpful",
    helpful=False,
    rating=2
)
```

---

## 📊 Monitoring

### View Analytics

1. **Web Dashboard**: http://localhost:5001
2. **API**: `GET /api/analytics`
3. **Log File**: `analytics.json`

### Metrics Tracked

- Total queries
- Success rate
- Average response time
- Cache hit rate
- Intent distribution
- Query patterns

---

## 🔧 Configuration

All features are enabled by default. To disable:

```python
# Disable re-ranking
response = rag.query_rag(query, use_rerank=False)

# Disable hybrid search
response = rag.query_rag(query, use_hybrid=False)
```

---

## ⚠️ Troubleshooting

### Models Downloading Slowly

**Normal**: First run downloads models (~500MB). Subsequent runs are fast.

### BM25 Not Working

**Check**: Ensure ChromaDB has documents indexed.

### CLIP Not Available

**Optional**: Multi-modal is optional. System works without it.

---

## 🎯 Next Steps

1. Test with various queries
2. Monitor analytics dashboard
3. Collect user feedback
4. Tune hybrid search weights if needed

---

## 📚 Documentation

- `IMPLEMENTATION_GUIDE.md` - Detailed feature documentation
- `ARCHITECTURE_ANALYSIS.md` - Architecture overview
- `advanced_rag.py` - Source code with comments

---

**Your system is now enterprise-grade! 🎉**

