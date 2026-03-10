#!/usr/bin/env python3
"""
Check if performance dependencies are installed.
Run this to verify your installation status.
"""

import sys

def check_sentence_transformers():
    """Check if sentence-transformers is available."""
    try:
        import sentence_transformers
        from sentence_transformers import CrossEncoder
        print("✅ sentence-transformers: INSTALLED")
        print(f"   Version: {sentence_transformers.__version__ if hasattr(sentence_transformers, '__version__') else 'unknown'}")
        
        # Try to load the re-ranker model
        try:
            reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
            print("✅ Re-ranker model: LOADED")
            print("   → Re-ranking is ENABLED (20-30% better search quality)")
            return True
        except Exception as e:
            print(f"⚠️  Re-ranker model: FAILED TO LOAD")
            print(f"   Error: {str(e)[:200]}")
            return False
    except ImportError as e:
        print("❌ sentence-transformers: NOT INSTALLED")
        print("   → Re-ranking is DISABLED")
        print("\n   To install:")
        print("   pip install -r requirements.performance.txt")
        return False

def check_torch():
    """Check if torch is available."""
    try:
        import torch
        print(f"✅ torch: INSTALLED (version {torch.__version__})")
        if torch.cuda.is_available():
            print(f"   → CUDA available: {torch.cuda.get_device_name(0)}")
        else:
            print("   → Using CPU (no GPU detected)")
        return True
    except ImportError:
        print("⚠️  torch: NOT INSTALLED (will be installed with sentence-transformers)")
        return False

def check_transformers():
    """Check if transformers is available."""
    try:
        import transformers
        print(f"✅ transformers: INSTALLED (version {transformers.__version__})")
        return True
    except ImportError:
        print("⚠️  transformers: NOT INSTALLED (optional, for CLIP)")
        return False

def main():
    print("=" * 60)
    print("Performance Dependencies Check")
    print("=" * 60)
    print()
    
    has_reranking = check_sentence_transformers()
    print()
    check_torch()
    print()
    check_transformers()
    print()
    
    print("=" * 60)
    if has_reranking:
        print("✅ Performance mode: ENABLED")
        print("   Your search will have 20-30% better quality!")
    else:
        print("⚠️  Performance mode: DISABLED")
        print("   Install performance dependencies for better search quality:")
        print("   pip install -r requirements.performance.txt")
    print("=" * 60)

if __name__ == "__main__":
    main()

