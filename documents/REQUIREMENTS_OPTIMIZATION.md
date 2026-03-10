# Requirements.txt Optimization for CPU Instances

## Summary

After removing image generation/enhancement logic, several dependencies are no longer needed for the main application runtime.

## Removed/Commented Dependencies

### 1. **Pillow (PIL)** - OPTIONAL
- **Status**: Commented out
- **Reason**: Only used in `search_by_image()` function which is not used in main app
- **Usage**: `advanced_rag.py` line 98, 1370
- **Action**: Keep commented unless you need image search feature

### 2. **eventlet** - OPTIONAL
- **Status**: Commented out
- **Reason**: Flask-SocketIO can auto-detect async mode or use threading (default)
- **Usage**: Not explicitly required
- **Action**: Only install if you specifically want async mode

### 3. **aiohttp** - OPTIONAL
- **Status**: Commented out
- **Reason**: Only used in `ingest_clu.py` for async ingestion (not needed at runtime)
- **Usage**: `ingest_clu.py` line 19, 640; `clu_client.py` line 2, 20
- **Action**: Only needed for ingestion scripts, not for running the app

## Performance Dependencies - OPTIONAL

All performance dependencies are now marked as optional:
- `sentence-transformers` - For re-ranking (20-30% improvement)
- `torch`, `torchvision`, `torchaudio` - CPU-only versions
- `transformers`, `scipy`, `huggingface-hub`, `safetensors` - Required for sentence-transformers

**Install separately**: `pip install -r requirements.performance.txt` (if you want re-ranking)

## Core Dependencies (Required)

These are the **minimum required** dependencies for running the app:

```txt
Flask==3.0.0
Flask-SocketIO==5.3.6
python-socketio==5.10.0
requests==2.31.0
chromadb==0.4.22
pandas==2.1.4
numpy==1.26.2
scikit-learn==1.3.2
rank-bm25==0.2.2
google-generativeai==0.3.2
PyYAML==6.0.1
python-dotenv==1.0.0
```

## Size Comparison

### Minimal Installation (Core Only)
- **Size**: ~500-800 MB
- **Features**: Full RAG functionality without re-ranking

### With Performance Dependencies
- **Size**: ~2.5-3 GB
- **Features**: +20-30% better search quality with re-ranking

## Installation Recommendations

### For CPU Production Server (Minimal)
```bash
pip install -r requirements.txt
# Skip performance dependencies unless you need re-ranking
```

### For CPU Production Server (With Re-ranking)
```bash
pip install -r requirements.txt
pip install -r requirements.performance.txt
```

### For Development/Ingestion
```bash
pip install -r requirements.txt
pip install aiohttp  # For async ingestion scripts
pip install Pillow   # If you need image search
```

## Unused Libraries Check

✅ **All unused libraries have been commented out or marked as optional**

- `image_utils` - No longer imported anywhere (removed)
- `Pillow` - Only used in unused `search_by_image()` function
- `eventlet` - Optional for SocketIO
- `aiohttp` - Only for ingestion scripts

## Notes

1. **Flask-SocketIO** works fine without `eventlet` - it will use threading mode
2. **Pillow** is only needed if you plan to use the `search_by_image()` function
3. **aiohttp** is only needed for running ingestion scripts, not the main app
4. **Performance dependencies** are optional but recommended for better search quality

