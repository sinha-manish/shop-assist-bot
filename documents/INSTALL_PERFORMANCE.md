# Installing Performance Dependencies

## Overview

The performance dependencies (`sentence-transformers`) significantly improve search quality by enabling **re-ranking**, which provides a **20-30% improvement** in result relevance.

## Installation

### Option 1: Install Performance Dependencies (Recommended for Production)

```bash
pip install -r requirements.performance.txt
```

This will install:
- `sentence-transformers` (includes `torch` automatically)
- Enables re-ranking for better search results

**Size Impact**: Adds ~2-3GB to your environment

### Option 2: CPU-Only Installation (Recommended for CPU Servers)

**Best for CPU servers** - Smaller size, optimized for CPU:

**Linux/Mac:**
```bash
bash install_performance_cpu.sh
```

**Windows (PowerShell):**
```powershell
.\install_performance_cpu.ps1
```

**Manual installation:**
```bash
pip install sentence-transformers --no-deps
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
pip install transformers>=4.30.0 numpy>=1.24.0 scipy>=1.10.0 scikit-learn>=1.3.0 huggingface-hub>=0.16.0 safetensors>=0.3.0
```

**Benefits:**
- Smaller installation size (~1.5-2GB vs ~3GB for GPU version)
- Optimized for CPU performance
- No CUDA dependencies
- Perfect for production CPU servers

### Option 3: GPU Installation (Faster, Larger)

If you have CUDA GPU available:

```bash
pip install sentence-transformers
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

## Verification

After installation, restart your Flask app. You should see:

```
✓ sentence-transformers loaded successfully. Re-ranking enabled.
✓ Cross-encoder re-ranker loaded
```

Instead of:

```
⚠️ sentence-transformers import failed. Re-ranking will be disabled.
```

## Performance Impact

**Without re-ranking:**
- Search works but results may be less relevant
- Faster initial response (no re-ranking step)
- Smaller memory footprint

**With re-ranking:**
- 20-30% improvement in result relevance
- Better top-k accuracy
- Slightly slower (adds ~100-200ms per query)
- Larger memory footprint (~2-3GB)

## Server Deployment

For production servers, we recommend installing performance dependencies for better user experience:

```bash
# In your deployment script or Dockerfile
RUN pip install -r requirements.txt
RUN pip install -r requirements.performance.txt
```

Or in a single command:

```bash
pip install -r requirements.txt -r requirements.performance.txt
```

## Troubleshooting

### Import Error: No module named 'sentence_transformers'

Make sure you've installed the performance requirements:
```bash
pip install -r requirements.performance.txt
```

### Out of Memory Errors

If you get memory errors, you can:
1. Use CPU-only torch (smaller)
2. Reduce batch size in re-ranking (modify `advanced_rag.py`)
3. Disable re-ranking by not installing sentence-transformers

### Slow Performance

Re-ranking adds ~100-200ms per query. If this is too slow:
- Consider using a GPU
- Reduce the number of results being re-ranked
- Disable re-ranking for simple queries

