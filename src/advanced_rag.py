#!/usr/bin/env python3
"""
Advanced RAG System with Hybrid Search, Re-ranking, Memory, Agents, and Analytics
==================================================================================
Enhanced RAG implementation with:
- Hybrid Search (Semantic + Keyword BM25)
- Re-ranking with Cross-Encoders
- Advanced Memory Management
- Agentic Framework
- Feedback Loop
- Multi-modal Support
- Analytics Dashboard
"""

import os
import sys
import json
import hashlib
import time
import re
import string
import warnings
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Any
from collections import defaultdict
from pathlib import Path

# Suppress warnings
warnings.filterwarnings("ignore", category=FutureWarning, module="huggingface_hub")
warnings.filterwarnings("ignore", category=UserWarning, module="transformers")
warnings.filterwarnings("ignore", message=".*use_fast.*")
warnings.filterwarnings("ignore", message=".*slow processor.*")

# Suppress ONNX runtime GPU discovery warnings (harmless, just checking for GPU)
import os
os.environ['ORT_DEVICE_DISCOVERY_LOG_LEVEL'] = 'ERROR'

import pandas as pd
import numpy as np
import requests

# Suppress ChromaDB telemetry errors - patch before import
import logging
logging.getLogger("chromadb.telemetry").setLevel(logging.CRITICAL)
logging.getLogger("chromadb").setLevel(logging.WARNING)

# Monkey-patch ChromaDB telemetry to prevent errors
try:
    import chromadb.telemetry.events as telemetry_events
    if hasattr(telemetry_events, 'capture'):
        original_capture = telemetry_events.capture
        def patched_capture(*args, **kwargs):
            try:
                return original_capture(*args, **kwargs)
            except:
                pass  # Silently ignore telemetry errors
        telemetry_events.capture = patched_capture
except:
    pass  # If patching fails, continue anyway

from chromadb import PersistentClient
from chromadb.config import Settings

# Import pandas for NaN checking
pd_isna = pd.isna

# Advanced search and ranking
CROSS_ENCODER_AVAILABLE = False
CrossEncoder = None

try:
    # Try importing with verbose error reporting
    import sentence_transformers
    from sentence_transformers import CrossEncoder
    CROSS_ENCODER_AVAILABLE = True
    print("✓ sentence-transformers loaded successfully. Re-ranking enabled.")
except ImportError as e:
    CROSS_ENCODER_AVAILABLE = False
    CrossEncoder = None
    print(f"⚠️ sentence-transformers import failed. Re-ranking will be disabled.")
    print(f"   Import error: {str(e)[:200]}")
except Exception as e:
    CROSS_ENCODER_AVAILABLE = False
    CrossEncoder = None
    print(f"⚠️ sentence-transformers failed to load. Re-ranking will be disabled.")
    print(f"   Error: {str(e)[:200]}")

try:
    from rank_bm25 import BM25Okapi
    BM25_AVAILABLE = True
except ImportError:
    BM25_AVAILABLE = False
    BM25Okapi = None
    print("⚠️ rank-bm25 not available. BM25 keyword search will be disabled.")

# Multi-modal support
try:
    from transformers import CLIPProcessor, CLIPModel
    from PIL import Image
    MULTIMODAL_AVAILABLE = True
except ImportError:
    MULTIMODAL_AVAILABLE = False
    print("⚠️ CLIP not available. Multi-modal search will be disabled.")

from config import Config
from geminiLLM import generate_human_readable_response

# Image enhancement removed - using local image paths from metadata only
IMAGE_UTILS_AVAILABLE = False

# Read settings
config = Config()
CLU_ENDPOINT = config.get("CLU_ENDPOINT")
CLU_KEY = config.get("CLU_KEY")
CLU_PROJECT_NAME = config.get("CLU_PROJECT_NAME")
CLU_DEPLOYMENT_NAME = config.get("CLU_DEPLOYMENT_NAME")
CHROMA_DB_PATH = config.get("CHROMA_DB_PATH", "chroma_db")
COLLECTION_NAME = config.get("COLLECTION_NAME", "shop_assist_retail_data_clu")


class ConversationMemory:
    """Advanced conversation memory with summarization."""
    
    def __init__(self, max_messages=20, summary_threshold=15):
        self.messages = []
        self.summary = ""
        self.max_messages = max_messages
        self.summary_threshold = summary_threshold
        self.conversation_id = None
    
    def add_message(self, role: str, content: str):
        """Add a message to conversation history."""
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        
        # Summarize if too long
        if len(self.messages) > self.max_messages:
            self._summarize_conversation()
    
    def _summarize_conversation(self):
        """Summarize old messages to maintain context."""
        if len(self.messages) <= self.summary_threshold:
            return
        
        # Keep last N messages, summarize the rest
        keep_count = self.summary_threshold
        old_messages = self.messages[:-keep_count]
        recent_messages = self.messages[-keep_count:]
        
        # Create summary of old messages
        old_text = "\n".join([f"{m['role']}: {m['content'][:100]}" for m in old_messages])
        self.summary = f"Previous conversation summary: {old_text[:500]}..."
        
        # Keep only recent messages
        self.messages = recent_messages
    
    def get_context(self, max_exchanges=3) -> str:
        """Get formatted conversation context."""
        context_parts = []
        
        if self.summary:
            context_parts.append(self.summary)
        
        # Get recent messages
        recent = self.messages[-max_exchanges*2:] if len(self.messages) > max_exchanges*2 else self.messages
        
        for msg in recent:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if len(content) > 200:
                content = content[:200] + "..."
            context_parts.append(f"{role.capitalize()}: {content}")
        
        return "\n".join(context_parts) if context_parts else None


class AnalyticsTracker:
    """Track queries, performance, and patterns."""
    
    def __init__(self, log_file="analytics.json"):
        self.log_file = log_file
        self.metrics = {
            'total_queries': 0,
            'successful_queries': 0,
            'failed_queries': 0,
            'avg_response_time': 0,
            'query_patterns': defaultdict(int),
            'intent_distribution': defaultdict(int),
            'response_times': [],
            'cache_hits': 0,
            'cache_misses': 0,
        }
        self.query_log = []
        self.load_analytics()
    
    def log_query(self, query: str, intent: str, response_time: float, success: bool, 
                  num_results: int = 0, cache_hit: bool = False):
        """Log a query for analytics."""
        self.metrics['total_queries'] += 1
        
        if cache_hit:
            self.metrics['cache_hits'] += 1
        else:
            self.metrics['cache_misses'] += 1
        
        if success:
            self.metrics['successful_queries'] += 1
        else:
            self.metrics['failed_queries'] += 1
        
        self.metrics['intent_distribution'][intent] += 1
        self.metrics['response_times'].append(response_time)
        
        # Update average response time
        if self.metrics['response_times']:
            self.metrics['avg_response_time'] = np.mean(self.metrics['response_times'][-100:])
        
        # Track query pattern
        query_type = self._classify_query(query)
        self.metrics['query_patterns'][query_type] += 1
        
        # Log detailed entry
        self.query_log.append({
            'timestamp': datetime.now().isoformat(),
            'query': query,
            'intent': intent,
            'response_time': response_time,
            'success': success,
            'num_results': num_results,
            'cache_hit': cache_hit
        })
        
        # Save periodically
        if len(self.query_log) % 10 == 0:
            self.save_analytics()
    
    def _classify_query(self, query: str) -> str:
        """Classify query type."""
        query_lower = query.lower()
        if any(word in query_lower for word in ['price', 'cost', 'discount', 'cheap', 'expensive']):
            return 'pricing'
        elif any(word in query_lower for word in ['available', 'stock', 'in stock', 'out of stock']):
            return 'availability'
        elif any(word in query_lower for word in ['store', 'location', 'where', 'near']):
            return 'location'
        elif any(word in query_lower for word in ['color', 'colour', 'red', 'blue', 'green']):
            return 'color_search'
        elif any(word in query_lower for word in ['size', 'small', 'medium', 'large']):
            return 'size_search'
        else:
            return 'general'
    
    def get_stats(self) -> Dict:
        """Get analytics statistics."""
        success_rate = (self.metrics['successful_queries'] / self.metrics['total_queries'] * 100) \
            if self.metrics['total_queries'] > 0 else 0
        
        cache_hit_rate = (self.metrics['cache_hits'] / 
                         (self.metrics['cache_hits'] + self.metrics['cache_misses']) * 100) \
            if (self.metrics['cache_hits'] + self.metrics['cache_misses']) > 0 else 0
        
        return {
            'total_queries': self.metrics['total_queries'],
            'success_rate': f"{success_rate:.1f}%",
            'avg_response_time': f"{self.metrics['avg_response_time']:.2f}s",
            'cache_hit_rate': f"{cache_hit_rate:.1f}%",
            'intent_distribution': dict(self.metrics['intent_distribution']),
            'query_patterns': dict(self.metrics['query_patterns']),
        }
    
    def save_analytics(self):
        """Save analytics to file."""
        try:
            with open(self.log_file, 'w') as f:
                json.dump({
                    'metrics': self.metrics,
                    'recent_queries': self.query_log[-100:]  # Keep last 100
                }, f, indent=2)
        except Exception as e:
            print(f"⚠️ Failed to save analytics: {e}")
    
    def load_analytics(self):
        """Load analytics from file."""
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, 'r') as f:
                    data = json.load(f)
                    loaded_metrics = data.get('metrics', {})
                    # Merge loaded data while keeping defaultdict behavior
                    for key, value in loaded_metrics.items():
                        if key in ['query_patterns', 'intent_distribution']:
                            # Convert back to defaultdict
                            self.metrics[key] = defaultdict(int, value) if isinstance(value, dict) else value
                        else:
                            self.metrics[key] = value
                    self.query_log = data.get('recent_queries', [])
            except Exception as e:
                print(f"⚠️ Failed to load analytics: {e}")


class AdvancedRAG:
    """Advanced RAG system with hybrid search, re-ranking, and more."""
    
    def __init__(self):
        try:
            # Initialize CLU
            self.clu_endpoint = CLU_ENDPOINT
            self.clu_key = CLU_KEY
            self.clu_project = CLU_PROJECT_NAME
            self.clu_deployment = CLU_DEPLOYMENT_NAME
            if not self.clu_endpoint or not self.clu_key:
                raise ValueError("❌ CLU credentials missing.")
            
            # Initialize ChromaDB
            self.client = PersistentClient(path=CHROMA_DB_PATH, settings=Settings(anonymized_telemetry=False))
            
            # Get or create collection (create if doesn't exist for first-time setup)
            try:
                self.collection = self.client.get_collection(COLLECTION_NAME)
                self.total_docs = self.collection.count()
                if self.total_docs == 0:
                    print(f"⚠️ Collection '{COLLECTION_NAME}' exists but is empty. Please run ingestion to populate data.")
            except ValueError:
                # Collection doesn't exist - create empty one
                print(f"⚠️ Collection '{COLLECTION_NAME}' does not exist. Creating empty collection.")
                print(f"   Please ensure chroma_db is mounted as volume or run ingestion script to populate data.")
                self.collection = self.client.create_collection(COLLECTION_NAME)
                self.total_docs = 0
                print(f"   Created empty collection. Run 'python ingest_clu.py' to populate data.")
            
            # Initialize BM25 for keyword search
            self._init_bm25()
            
            # Initialize re-ranker
            if CROSS_ENCODER_AVAILABLE:
                try:
                    self.reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
                    print("✓ Cross-encoder re-ranker loaded")
                    print("  → Re-ranking enabled: 20-30% improvement in search quality")
                except Exception as e:
                    print(f"⚠️ Failed to load re-ranker: {e}")
                    self.reranker = None
            else:
                self.reranker = None
                print("⚠️ Re-ranking disabled. Install 'sentence-transformers' for 20-30% better search quality.")
                print("  → Run: pip install -r requirements.performance.txt")
            
            # Initialize multi-modal (CLIP) - Optional, not actively used
            if MULTIMODAL_AVAILABLE:
                try:
                    # Suppress warnings during CLIP loading
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        self.clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32", 
                                                                     local_files_only=False)
                        self.clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32",
                                                                          local_files_only=False)
                    print("✓ CLIP model loaded for multi-modal search")
                except Exception as e:
                    # CLIP is optional, so we silently disable it on failure
                    error_msg = str(e)
                    if "Consistency check failed" in error_msg or "size" in error_msg.lower():
                        # Corrupted download - can be fixed by clearing cache, but not critical
                        print("⚠️ CLIP model download corrupted (optional feature, continuing without it)")
                    else:
                        print(f"⚠️ CLIP model unavailable (optional feature, continuing without it)")
                    self.clip_model = None
            else:
                self.clip_model = None
            
            # Initialize memory and analytics
            self.memory = ConversationMemory()
            self.analytics = AnalyticsTracker()
            
            # Query cache
            self.cache = {}
            self.cache_size_limit = 1000
            
            print(f"✓ Advanced RAG initialized ({self.total_docs} docs indexed)")
            
        except Exception as e:
            print(f"❌ Initialization failed: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    def _init_bm25(self):
        """Initialize BM25 for keyword search."""
        if not BM25_AVAILABLE or BM25Okapi is None:
            self.bm25 = None
            self.bm25_doc_ids = []
            self.bm25_docs = []
            return
        
        try:
            # Get all documents for BM25
            all_data = self.collection.get()
            all_docs = all_data.get('documents', [])
            all_ids = all_data.get('ids', [])
            
            if not all_docs:
                self.bm25 = None
                self.bm25_doc_ids = []
                self.bm25_docs = []
                return
            
            # Tokenize documents
            tokenized_docs = [doc.lower().split() for doc in all_docs]
            self.bm25 = BM25Okapi(tokenized_docs)
            self.bm25_docs = all_docs
            self.bm25_doc_ids = all_ids
            print(f"✓ BM25 initialized with {len(all_docs)} documents")
        except Exception as e:
            print(f"⚠️ Failed to initialize BM25: {e}")
            self.bm25 = None
            self.bm25_doc_ids = []
            self.bm25_docs = []
    
    def call_clu(self, query: str) -> Dict:
        """Call CLU API for intent/entity extraction."""
        url = self.clu_endpoint
        headers = {"Ocp-Apim-Subscription-Key": self.clu_key, "Content-Type": "application/json"}
        payload = {
            "kind": "Conversation",
            "analysisInput": {
                "conversationItem": {
                    "id": "user",
                    "participantId": "user",
                    "text": query,
                    "modality": "text",
                    "language": "en"
                }
            },
            "parameters": {
                "projectName": self.clu_project,
                "deploymentName": self.clu_deployment,
                "verbose": True,
                "stringIndexType": "TextElement_V8"
            }
        }
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"❌ CLU API call failed: {e}")
            return {}
    
    def semantic_search(self, query: str, n_results: int = 10, where: Optional[Dict] = None) -> List[Dict]:
        """Semantic search using ChromaDB."""
        try:
            # ChromaDB requires where clause to have exactly one operator
            # If multiple conditions, wrap in $and operator
            # Preserve operator structures like $contains
            if where and len(where) > 1:
                where_clause = {"$and": [{k: v} for k, v in where.items()]}
            elif where and len(where) == 1:
                where_clause = where
            else:
                where_clause = None
            
            if where_clause:
                print(f"🔎 ChromaDB query with filter: {where_clause}")
                results = self.collection.query(query_texts=[query], n_results=n_results, where=where_clause)
                result_count = len(results['documents'][0]) if results['documents'] and results['documents'][0] else 0
                print(f"🔎 ChromaDB returned {result_count} results with filter")
                
                # If no results with filter, try without filter to see if data exists
                if result_count == 0:
                    print(f"⚠️ No results with filter, checking without filter...")
                    unfiltered = self.collection.query(query_texts=[query], n_results=5)
                    if unfiltered['documents'] and unfiltered['documents'][0]:
                        print(f"⚠️ Found {len(unfiltered['documents'][0])} results WITHOUT filter")
                        # Show what categories exist
                        for i, meta in enumerate(unfiltered['metadatas'][0][:3]):
                            cat = meta.get('Product_Category', meta.get('product_category', 'N/A'))
                            name = meta.get('Product_Name', meta.get('product_name', 'Unknown'))[:40]
                            print(f"   Sample {i+1}: '{name}' - Category: '{cat}'")
            else:
                results = self.collection.query(query_texts=[query], n_results=n_results)
            
            formatted_results = []
            for i in range(len(results['documents'][0])):
                meta = results['metadatas'][0][i]
                formatted_results.append({
                    "rank": i + 1,
                    "content": results["documents"][0][i],
                    "metadata": meta,
                    "similarity": 1 - results["distances"][0][i],
                    "source": "semantic"
                })
            return formatted_results
        except Exception as e:
            print(f"❌ Semantic search failed: {e}")
            return []
    
    def keyword_search(self, query: str, n_results: int = 10) -> List[Dict]:
        """Keyword search using BM25."""
        if not self.bm25 or not hasattr(self, 'bm25_docs') or not self.bm25_docs:
            return []
        
        try:
            # Tokenize query
            query_tokens = query.lower().split()
            
            # Get BM25 scores
            scores = self.bm25.get_scores(query_tokens)
            
            # Get top results
            top_indices = np.argsort(scores)[::-1][:n_results]
            
            # Format results
            formatted_results = []
            for idx in top_indices:
                if scores[idx] > 0:  # Only include results with positive scores
                    doc = self.bm25_docs[idx]
                    doc_id = self.bm25_doc_ids[idx] if idx < len(self.bm25_doc_ids) else None
                    
                    # Get metadata from ChromaDB using document ID
                    meta = {}
                    try:
                        if doc_id:
                            db_results = self.collection.get(ids=[doc_id])
                            if db_results.get('metadatas'):
                                meta = db_results['metadatas'][0]
                    except:
                        pass
                    
                    # Normalize score
                    max_score = max(scores) if len(scores) > 0 and max(scores) > 0 else 1
                    normalized_score = float(scores[idx]) / max_score
                    
                    formatted_results.append({
                        "rank": len(formatted_results) + 1,
                        "content": doc,
                        "metadata": meta,
                        "similarity": normalized_score,
                        "source": "keyword"
                    })
            
            return formatted_results
        except Exception as e:
            print(f"❌ Keyword search failed: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def hybrid_search(self, query: str, n_results: int = 10, where: Optional[Dict] = None,
                     semantic_weight: float = 0.7, keyword_weight: float = 0.3) -> List[Dict]:
        """Hybrid search combining semantic and keyword search."""
        # Get results from both methods
        semantic_results = self.semantic_search(query, n_results=n_results*2, where=where)
        keyword_results = self.keyword_search(query, n_results=n_results*2)
        
        # Post-filter keyword results to match the where clause (BM25 doesn't support filtering)
        if where and keyword_results:
            filtered_keyword_results = []
            for result in keyword_results:
                meta = result.get('metadata', {})
                matches = True
                for key, value in where.items():
                    meta_value = meta.get(key) or meta.get(key.title()) or meta.get(key.lower())
                    if meta_value is None:
                        # Try alternate key formats (e.g., product_category vs Product_Category)
                        alt_key = key.replace('_', ' ').title().replace(' ', '_')
                        meta_value = meta.get(alt_key)
                    
                    if isinstance(value, dict):
                        # Handle operators like $in
                        if '$in' in value:
                            if meta_value not in value['$in']:
                                matches = False
                                break
                    elif meta_value != value:
                        matches = False
                        break
                
                if matches:
                    filtered_keyword_results.append(result)
            
            if len(keyword_results) != len(filtered_keyword_results):
                print(f"🔍 Filtered keyword results: {len(keyword_results)} -> {len(filtered_keyword_results)} (applied where clause)")
            keyword_results = filtered_keyword_results
        
        # Combine results
        combined = {}
        
        # Add semantic results
        for result in semantic_results:
            content = result['content']
            if content not in combined:
                combined[content] = {
                    **result,
                    'hybrid_score': result['similarity'] * semantic_weight
                }
            else:
                # Boost score if found in both
                combined[content]['hybrid_score'] += result['similarity'] * semantic_weight
        
        # Add keyword results
        for result in keyword_results:
            content = result['content']
            if content not in combined:
                combined[content] = {
                    **result,
                    'hybrid_score': result['similarity'] * keyword_weight
                }
            else:
                # Boost score if found in both
                combined[content]['hybrid_score'] += result['similarity'] * keyword_weight
        
        # Sort by hybrid score
        sorted_results = sorted(combined.values(), key=lambda x: x['hybrid_score'], reverse=True)
        
        return sorted_results[:n_results]
    
    def rerank_results(self, query: str, results: List[Dict]) -> List[Dict]:
        """Re-rank results using cross-encoder."""
        if not self.reranker or not results:
            return results
        
        try:
            # Limit re-ranking to top 20 results for speed (re-ranking is expensive)
            max_rerank = min(len(results), 20)
            results_to_rerank = results[:max_rerank]
            results_after_rerank = results[max_rerank:]
            
            # Prepare pairs for re-ranking
            pairs = [[query, r['content']] for r in results_to_rerank]
            
            rerank_start = time.time()
            # Get re-ranking scores
            scores = self.reranker.predict(pairs)
            rerank_time = time.time() - rerank_start
            if rerank_time > 2.0:
                print(f"⚠️ Re-ranking took {rerank_time:.2f}s (slow)")
            
            # Update results with new scores
            for i, result in enumerate(results_to_rerank):
                result['rerank_score'] = float(scores[i])
                result['similarity'] = float(scores[i])  # Update similarity with rerank score
            
            # Sort by rerank score
            reranked = sorted(results_to_rerank, key=lambda x: x['rerank_score'], reverse=True)
            
            # Combine reranked results with non-reranked (maintain order)
            final_results = reranked + results_after_rerank
            
            # Update ranks
            for i, result in enumerate(final_results):
                result['rank'] = i + 1
            
            return final_results
        except Exception as e:
            print(f"⚠️ Re-ranking failed: {e}")
            return results
    
    def search(self, query: str, n_results: int = 5, where: Optional[Dict] = None,
              use_hybrid: bool = True, use_rerank: bool = True, 
              include_out_of_stock: bool = False) -> List[Dict]:
        """Main search method with hybrid search and re-ranking.
        
        Args:
            query: Search query
            n_results: Number of results to return
            where: Filter conditions
            use_hybrid: Use hybrid search (semantic + keyword)
            use_rerank: Use cross-encoder re-ranking
            include_out_of_stock: If False, filter out out-of-stock products
        """
        start_time = time.time()
        
        # Perform search
        if use_hybrid:
            results = self.hybrid_search(query, n_results=n_results*2, where=where)
        else:
            results = self.semantic_search(query, n_results=n_results*2, where=where)
        
        # Re-rank if enabled
        if use_rerank and results:
            results = self.rerank_results(query, results)
        
        # Filter by similarity threshold
        filtered = [r for r in results if r.get('similarity', 0) > -0.05]
        
        # Filter out out-of-stock products (unless explicitly requested)
        if not include_out_of_stock:
            in_stock_results = []
            out_of_stock_count = 0
            for r in filtered:
                meta = r.get('metadata', {})
                # Check stock quantity
                try:
                    stock_qty = int(meta.get('stock_quantity') or meta.get('Stock_Quantity') or 100)
                except (ValueError, TypeError):
                    stock_qty = 100  # Default to in-stock if unknown
                
                # Check availability status
                availability = (meta.get('availability') or meta.get('Availability') or 'In Stock').lower()
                
                # Include if in stock
                if stock_qty > 0 and availability != 'out of stock':
                    in_stock_results.append(r)
                else:
                    out_of_stock_count += 1
            
            if out_of_stock_count > 0:
                print(f"📦 Filtered out {out_of_stock_count} out-of-stock products")
            
            filtered = in_stock_results
        
        # Return top N
        final_results = filtered[:n_results] if filtered else results[:n_results]
        
        search_time = time.time() - start_time
        print(f"🔍 Search completed in {search_time:.2f}s ({len(final_results)} results)")
        
        return final_results
    
    def _direct_product_search(self, product_types: list = None, max_price: float = None,
                               min_price: float = None, color: str = None, gender: str = None,
                               category: str = None, requires_discount: bool = False,
                               min_discount: float = None, style: str = None, limit: int = 50) -> List[Dict]:
        """
        GENERALIZED FALLBACK: Direct database scan when semantic search fails.
        This bypasses embeddings and searches products by exact criteria.
        Works for ANY product type (dress, shirt, jeans, etc.)
        """
        try:
            # Build where clause for category filter only (most reliable)
            where = {}
            if category:
                where["product_category"] = category
            
            # Get products from ChromaDB
            if where:
                results = self.collection.get(where=where, include=['metadatas', 'documents'])
            else:
                results = self.collection.get(include=['metadatas', 'documents'], limit=500)
            
            matching_products = []
            
            for i, meta in enumerate(results.get('metadatas', [])):
                product_name = (meta.get('product_name') or meta.get('Product_Name', '')).lower()
                product_color = (meta.get('color') or meta.get('Color', '')).lower()
                product_category = (meta.get('product_category') or meta.get('Product_Category', '')).lower()
                
                # Get price
                try:
                    price = float(meta.get('discounted_price') or meta.get('base_price') or 99999)
                except (ValueError, TypeError):
                    price = 99999
                
                # Get discount
                try:
                    discount = float(meta.get('discount_percent') or 0)
                except (ValueError, TypeError):
                    discount = 0
                
                # GENERALIZED FILTERS:
                
                # 1. Product type filter - check if ANY required type is in product name
                type_match = True
                if product_types:
                    type_match = any(ptype.lower() in product_name for ptype in product_types)
                
                # 2. Price filter
                price_match = True
                if max_price is not None and price > max_price:
                    price_match = False
                if min_price is not None and price < min_price:
                    price_match = False
                
                # 3. Color filter
                color_match = True
                if color:
                    color_match = color.lower() in product_color or color.lower() in product_name
                
                # 4. Gender filter - use word boundary matching
                gender_match = True
                if gender:
                    name_words = set(product_name.split())
                    is_kids = bool(name_words & {'boys', 'girls', 'kids', 'boy', 'girl', 'kid'})
                    
                    if gender == 'women':
                        is_womens = bool(name_words & {'women', 'woman', 'womens'}) or "women's" in product_category
                        gender_match = is_womens and not is_kids
                    elif gender == 'men':
                        # Check for "men" as a word, NOT as substring of "women"
                        is_mens = bool(name_words & {'men', 'man', 'mens'}) or product_name.startswith('men ')
                        is_womens = bool(name_words & {'women', 'woman', 'womens'})
                        gender_match = is_mens and not is_womens and not is_kids
                    elif gender == 'kids':
                        gender_match = is_kids or 'kids' in product_category
                
                # 5. Discount filter
                discount_match = True
                if requires_discount and min_discount:
                    discount_match = discount >= min_discount
                
                # 6. Stock filter - exclude out-of-stock products
                stock_match = True
                try:
                    stock_qty = int(meta.get('stock_quantity') or meta.get('Stock_Quantity') or 100)
                except (ValueError, TypeError):
                    stock_qty = 100  # Default to in-stock if unknown
                availability = (meta.get('availability') or meta.get('Availability') or 'In Stock').lower()
                if stock_qty <= 0 or availability == 'out of stock':
                    stock_match = False
                
                # 7. Style/Occasion filter (formal, casual, party, sports)
                # Logic: Include if product matches style OR is neutral (doesn't have opposite style)
                style_match = True
                if style:
                    product_subcategory = (meta.get('product_subcategory') or meta.get('Product_Subcategory', '')).lower()
                    style_keywords_map = {
                        'formal': ['formal', 'office', 'business', 'professional'],
                        'casual': ['casual', 'everyday', 'relaxed'],
                        'party': ['party', 'evening', 'festive', 'wedding'],
                        'sports': ['sports', 'gym', 'athletic', 'workout']
                    }
                    style_kws = style_keywords_map.get(style, [])
                    style_in_name = any(kw in product_name for kw in style_kws)
                    style_in_subcat = any(kw in product_subcategory for kw in style_kws)
                    
                    # Define opposite styles - exclude products with OPPOSITE style
                    opposite_styles = {
                        'formal': ['casual', 'sports', 'gym', 'athletic', 'workout', 'relaxed', 'everyday'],
                        'casual': ['formal', 'office', 'business', 'professional'],
                        'party': ['sports', 'gym', 'athletic', 'workout'],
                        'sports': ['formal', 'office', 'business', 'party', 'evening']
                    }
                    opposite_keywords = opposite_styles.get(style, [])
                    has_opposite_style = any(kw in product_name for kw in opposite_keywords)
                    
                    # Match if: has required style OR (is neutral AND doesn't have opposite)
                    style_match = style_in_name or style_in_subcat or (not has_opposite_style)
                
                # Include if ALL filters pass
                if type_match and price_match and color_match and gender_match and discount_match and stock_match and style_match:
                    matching_products.append({
                        'metadata': meta,
                        'document': results.get('documents', [None])[i] if results.get('documents') else None,
                        'similarity': 0.9  # Assign high similarity for direct matches
                    })
                
                if len(matching_products) >= limit:
                    break
            
            return matching_products
            
        except Exception as e:
            print(f"⚠️ Direct product search failed: {e}")
            return []
    
    def query_rag(self, query: str, num_results: int = 5, conversation_context: Optional[str] = None,
                  use_hybrid: bool = True, use_rerank: bool = True) -> str:
        """Main RAG query method with all advanced features."""
        start_time = time.time()
        
        # Check cache
        cache_key = hashlib.md5(f"{query}_{num_results}".encode()).hexdigest()
        if cache_key in self.cache:
            print("📦 Cache hit!")
            self.analytics.log_query(query, "cached", 0.01, True, num_results, cache_hit=True)
            return self.cache[cache_key]
        
        # Get conversation context from memory
        if not conversation_context:
            conversation_context = self.memory.get_context()
        
        # Call CLU
        clu_result = self.call_clu(query)
        prediction = clu_result.get("result", {}).get("prediction", {})
        intent = prediction.get("topIntent", "None")
        entities = prediction.get("entities", [])
        
        # Build search query
        enriched_query, where, required_category, required_subcategory, max_price, min_price, requires_discount, required_product_types = self._build_search_from_clu(prediction, query)
        
        # Perform search
        results = self.search(enriched_query, n_results=num_results*2, where=where,
                            use_hybrid=use_hybrid, use_rerank=use_rerank)
        
        # Post-filter results to ensure strict matching (category and subcategory)
        if (required_category or required_subcategory) and results:
            filtered_results = []
            for result in results:
                meta = result.get('metadata', {})
                product_category = meta.get('product_category') or meta.get('Product_Category', '')
                product_subcategory = (meta.get('product_subcategory') or meta.get('Product_Subcategory', '')).lower()
                product_name = (meta.get('product_name') or meta.get('Product_Name', '')).lower()
                
                # Check category match (if required) - also check product name for contradictions
                category_match = True
                if required_category:
                    if required_category == "Men's Clothing":
                        # Category must match AND product name must not contradict
                        category_match = ("Men" in product_category or "Men's" in product_category) and \
                                        "women" not in product_name and "woman" not in product_name and \
                                        "girls" not in product_name and "girl" not in product_name
                    elif required_category == "Women's Clothing":
                        # Category must match AND product name must not contradict
                        category_match = ("Women" in product_category or "Women's" in product_category) and \
                                        "men" not in product_name and "man" not in product_name and \
                                        "boys" not in product_name and "boy" not in product_name
                    elif required_category == "Kids & Teens":
                        category_match = ("Kids" in product_category or "Teens" in product_category or "Boys" in product_category or "Girls" in product_category) and \
                                        ("boys" in product_name or "girls" in product_name or "boy" in product_name or "girl" in product_name or "kids" in product_name)
                
                # Check subcategory/product type match (if required) - strict matching
                subcategory_match = True
                if required_subcategory:
                    # Map product type to variations for matching
                    type_variations = {
                        'trouser': ['trouser', 'trousers', 'pant', 'pants'],
                        'shoe': ['shoe', 'shoes', 'footwear', 'sneaker', 'sneakers', 'boot', 'boots'],
                        'shirt': ['shirt', 'shirts', 'top', 'tops'],
                        'dress': ['dress', 'dresses', 'gown', 'gowns'],
                    }
                    
                    # Get variations for the required type
                    variations = type_variations.get(required_subcategory.lower(), [required_subcategory.lower()])
                    
                    # Check if subcategory contains any variation
                    subcategory_match = any(var in product_subcategory for var in variations)
                    
                    # Also check product name if subcategory doesn't match
                    if not subcategory_match:
                        subcategory_match = any(var in product_name for var in variations)
                
                # Only include if both category and subcategory match
                if category_match and subcategory_match:
                    filtered_results.append(result)
            
            results = filtered_results[:num_results]  # Limit to requested number
        
        if not results:
            response_time = time.time() - start_time
            self.analytics.log_query(query, intent, response_time, False, 0)
            # Create a more specific "not found" message
            not_found_msg = f"No matching items found for: {query}"
            return generate_human_readable_response(query, not_found_msg, conversation_context)
        
        # Format results
        structured_data = self._format_results_for_gemini(results, conversation_context)
        
        # Generate response
        response = generate_human_readable_response(query, structured_data, conversation_context)
        
        # Update memory
        self.memory.add_message("user", query)
        self.memory.add_message("assistant", response)
        
        # Cache result
        if len(self.cache) < self.cache_size_limit:
            self.cache[cache_key] = response
        
        # Log analytics
        response_time = time.time() - start_time
        self.analytics.log_query(query, intent, response_time, True, len(results))
        
        return response
    
    def _build_search_from_clu(self, prediction: dict, fallback_query: str, user_gender: str = None) -> Tuple[str, Optional[Dict], Optional[str], Optional[str], Optional[float], Optional[float], bool, list]:
        """Build search query from CLU prediction. Returns (query, where_clause, required_category, required_subcategory, max_price, min_price, requires_discount, required_product_types).
        
        Args:
            prediction: CLU prediction dict
            fallback_query: Original query text
            user_gender: User's gender from profile ('male', 'female', 'kid') - used as default if no gender in query
        """
        if not isinstance(prediction, dict):
            return fallback_query, None, None, None, None, None, False, []
        
        entities = prediction.get("entities", []) or []
        keywords = []
        where = {}
        required_category = None
        required_subcategory = None
        
        def set_where(key, value):
            if value is None:
                return
            if isinstance(value, dict):
                # Handle operators like $contains
                where[key] = value
            elif isinstance(value, str):
                v = value.strip()
                if v:
                    where[key] = v
            elif isinstance(value, (int, float, bool)):
                where[key] = value
        
        CATEGORY_MAP = {
            "product_name": ["product_name", "Product_Name"],
            "category": ["product_category", "Product_Category"],
            "product_category": ["product_category", "Product_Category"],  # Alias for consistency
            "color": ["color", "Color"],
            "size": ["size", "Size"],
            "material": ["material", "Material"],
            "pattern": ["pattern", "Pattern"],
            "fit": ["fit", "Fit"],  # New from scraper
            "store": ["store_name", "Store_Name", "store_area", "Store_Area"],  # Also check store_area
            "store_name": ["store_name", "Store_Name", "store_area", "Store_Area"],  # Alias - also check area
            "location": ["store_location", "Store_Location", "store_area", "Store_Area"],  # Also check store_area
            "store_location": ["store_location", "Store_Location", "store_area", "Store_Area"],  # Alias - also check area
            "store_area": ["store_area", "Store_Area"],  # New from scraper - key field for location matching
            "store_type": ["store_type", "Store_Type"],  # New from scraper
            "discount": ["discount_percent", "Discount_Percent"],  # New from scraper
        }
        
        # Extract store name/location from query text (before CLU entities)
        # Handle patterns like "in Shop Assist - LB Nagar", "at LB Nagar", "store LB Nagar", etc.
        query_lower = fallback_query.lower()
        store_patterns = [
            r'in\s+(shop\s+assist\s*-\s*[^,\.]+)',  # "in Shop Assist - LB Nagar"
            r'at\s+(shop\s+assist\s*-\s*[^,\.]+)',   # "at Shop Assist - LB Nagar"
            r'store\s+(shop\s+assist\s*-\s*[^,\.]+)', # "store Shop Assist - LB Nagar"
            r'(shop\s+assist\s*-\s*[^,\.]+)',        # "Shop Assist - LB Nagar"
            r'in\s+([^,\.]+nagar)',                  # "in LB Nagar"
            r'at\s+([^,\.]+nagar)',                   # "at LB Nagar"
        ]
        
        extracted_store_name = None
        extracted_store_location = None
        
        # Extract price constraints from query
        # Patterns: "under 2000", "below 1500", "less than 3000", "within 1000", "up to 500"
        max_price = None
        min_price = None
        price_patterns = [
            (r'under\s*(?:rs\.?|₹|inr)?\s*(\d+)', 'max'),  # "under 2000", "under Rs 2000"
            (r'below\s*(?:rs\.?|₹|inr)?\s*(\d+)', 'max'),  # "below 2000"
            (r'less\s+than\s*(?:rs\.?|₹|inr)?\s*(\d+)', 'max'),  # "less than 2000"
            (r'within\s*(?:rs\.?|₹|inr)?\s*(\d+)', 'max'),  # "within 2000"
            (r'up\s*to\s*(?:rs\.?|₹|inr)?\s*(\d+)', 'max'),  # "up to 2000"
            (r'(?:rs\.?|₹|inr)\s*(\d+)\s*(?:or\s+)?(?:less|below|under)', 'max'),  # "Rs 2000 or less"
            (r'above\s*(?:rs\.?|₹|inr)?\s*(\d+)', 'min'),  # "above 2000"
            (r'over\s*(?:rs\.?|₹|inr)?\s*(\d+)', 'min'),  # "over 2000"
            (r'more\s+than\s*(?:rs\.?|₹|inr)?\s*(\d+)', 'min'),  # "more than 2000"
            (r'(?:rs\.?|₹|inr)\s*(\d+)\s*(?:or\s+)?(?:more|above|over)', 'min'),  # "Rs 2000 or more"
        ]
        
        for pattern, price_type in price_patterns:
            match = re.search(pattern, query_lower, re.I)
            if match:
                try:
                    price_value = float(match.group(1))
                    if price_type == 'max':
                        max_price = price_value
                    else:
                        min_price = price_value
                    print(f"💰 Extracted price filter: {price_type}_price = {price_value}")
                except ValueError:
                    pass
                break
        
        # Check if query requires discounted products
        requires_discount = False
        discount_keywords = ['discount', 'discounted', 'sale', 'offer', 'off', 'deals', 'deal', 'reduced', 'savings']
        print(f"🔍 Checking for discount keywords in: '{query_lower}'")
        for kw in discount_keywords:
            if kw in query_lower:
                requires_discount = True
                print(f"🏷️ DISCOUNT FILTER ENABLED! Found keyword '{kw}' - only showing discounted products")
                break
        if not requires_discount:
            print(f"⚪ No discount keywords found")
        
        # Check if query requires specific product types
        required_product_types = []
        
        # Check if "top" is used as adjective (meaning "best") not as clothing type
        # e.g., "top discounted", "top rated", "top selling" → "top" means "best"
        # vs "show me tops", "women's top" → "top" is clothing
        top_as_adjective_patterns = ['top discounted', 'top rated', 'top selling', 'top products', 
                                     'top items', 'top deals', 'top offers', 'top picks', 'top choices',
                                     'top 5', 'top 10', 'top results', 'top trending', 'top popular']
        is_top_adjective = any(pattern in query_lower for pattern in top_as_adjective_patterns)
        if is_top_adjective:
            print(f"ℹ️ 'top' used as adjective (meaning 'best'), not as product type")
        
        # Specific product type mappings - when user asks for specific item, only show that
        specific_product_types = {
            'jeans': ['jeans', 'jean', 'denim'],
            'shirt': ['shirt', 'shirts'],
            't-shirt': ['t-shirt', 't-shirts', 'tshirt', 'tshirts', 'tee', 'tees'],
            'dress': ['dress', 'dresses', 'frock', 'frocks', 'gown', 'gowns'],
            'pant': ['pant', 'pants', 'trouser', 'trousers'],
            'top': ['top', 'tops', 'blouse', 'blouses'],
            'jacket': ['jacket', 'jackets', 'blazer', 'blazers', 'coat', 'coats'],
            'kurta': ['kurta', 'kurtas', 'kurti', 'kurtis'],
            'skirt': ['skirt', 'skirts'],
            'shorts': ['shorts', 'short'],
            'sweater': ['sweater', 'sweaters', 'hoodie', 'hoodies', 'sweatshirt', 'sweatshirts'],
            'polo': ['polo', 'polos'],
            # Generic clothing - all items
            'clothing': ['clothing', 'cloths', 'clothes', 'shirt', 'shirts', 't-shirt', 't-shirts', 
                        'dress', 'dresses', 'pant', 'pants', 'jeans', 'jean', 'top', 'tops',
                        'jacket', 'jackets', 'skirt', 'skirts', 'shorts', 'sweater', 'kurta'],
            # Accessories
            'wallet': ['wallet', 'wallets'],
            'bag': ['bag', 'bags', 'handbag', 'handbags', 'purse', 'purses'],
            'belt': ['belt', 'belts'],
            'watch': ['watch', 'watches'],
            'accessory': ['wallet', 'wallets', 'bag', 'bags', 'handbag', 'handbags', 
                         'belt', 'belts', 'watch', 'watches', 'tie', 'ties', 'scarf', 'scarves'],
        }
        
        # Find the MOST SPECIFIC product type that matches the query
        for product_type, keywords in specific_product_types.items():
            for kw in keywords:
                # Skip "top/tops" if used as adjective (meaning "best")
                if kw in ['top', 'tops'] and is_top_adjective:
                    continue
                if kw in query_lower and product_type not in ['clothing', 'accessory']:
                    # Found a specific product type
                    required_product_types = keywords
                    print(f"👕 SPECIFIC PRODUCT FILTER: '{product_type}' - only showing {keywords}")
                    break
            if required_product_types:
                break
        
        # If no specific type found, check for generic clothing/accessory
        if not required_product_types:
            if any(kw in query_lower for kw in ['clothing', 'cloths', 'clothes']):
                required_product_types = specific_product_types['clothing']
                print(f"👕 GENERIC CLOTHING FILTER - showing all clothing items")
            elif any(kw in query_lower for kw in ['accessory', 'accessories']):
                required_product_types = specific_product_types['accessory']
                print(f"👜 GENERIC ACCESSORY FILTER - showing all accessories")
        
        for pattern in store_patterns:
            match = re.search(pattern, query_lower, re.I)
            if match:
                store_text = match.group(1).strip()
                print(f"📍 Extracted store from query: '{store_text}' (pattern: {pattern})")
                # Normalize: remove extra spaces, handle "Shop Assist -" prefix
                if 'shop assist' in store_text:
                    # Full store name like "Shop Assist - LB Nagar"
                    extracted_store_name = store_text
                    # Extract location part (after "-")
                    if '-' in store_text:
                        location_part = store_text.split('-', 1)[1].strip()
                        extracted_store_location = location_part
                else:
                    # Just location like "LB Nagar"
                    extracted_store_location = store_text
                break
        
        # Detect gender/category from query text
        # Use word boundary matching to avoid "men" matching in "women"
        # Clean punctuation from words for better matching (e.g., "boys?" -> "boys")
        query_words = set(word.strip(string.punctuation) for word in query_lower.split())
        
        # Check women FIRST (before men) to avoid "men" in "women" issue
        # NOTE: Don't use ChromaDB filter for category - apostrophe encoding causes issues
        # Instead, rely on post-filtering which works reliably
        gender_detected_from_query = False
        
        if any(word in query_words for word in ['women', 'woman', 'female', 'womens', "women's", 'ladies', 'lady', 'her', 'she']) or \
           re.search(r'\bwomen\b|\bwoman\b|\bfemale\b|\bwomens\b|\bladies\b|\blady\b', query_lower):
            required_category = "Women's Clothing"
            gender_detected_from_query = True
            print(f"👩 Detected WOMEN's category from query - will post-filter results")
        elif any(word in query_words for word in ['men', 'man', 'male', 'mens', "men's", 'gentleman', 'his', 'he']) or \
             re.search(r'\bmen\b|\bman\b|\bmale\b|\bmens\b|\bgentleman\b', query_lower):
            required_category = "Men's Clothing"
            gender_detected_from_query = True
            print(f"👨 Detected MEN's category from query - will post-filter results")
        elif any(word in query_words for word in ['boys', 'boy', "boys'", 'kids', 'kid', "kids'", "kid's", 'child', 'children', 'junior', 'juniors']):
            required_category = "Kids & Teens"
            gender_detected_from_query = True
            print(f"👦 Detected KIDS/BOYS category from query - will post-filter results")
        elif any(word in query_words for word in ['girls', 'girl', "girls'", "girl's"]):
            required_category = "Kids & Teens"
            gender_detected_from_query = True
            print(f"👧 Detected KIDS/GIRLS category from query - will post-filter results")
        
        # If no gender detected in query, use user's profile gender as default
        if not gender_detected_from_query and user_gender:
            # Map user gender profile to category
            # Gender synonyms: male -> men, female -> women, kid -> kids
            gender_to_category = {
                'male': "Men's Clothing",
                'female': "Women's Clothing",
                'kid': "Kids & Teens"
            }
            if user_gender.lower() in gender_to_category:
                required_category = gender_to_category[user_gender.lower()]
                print(f"👤 Using user's profile gender '{user_gender}' -> {required_category} (no gender in query)")
        
        # Detect product type/subcategory from query text (strict matching)
        # Map common product type keywords to subcategory patterns
        product_type_keywords = {
            'shoe': ['shoe', 'shoes', 'footwear', 'sneaker', 'sneakers', 'boot', 'boots', 'sandal', 'sandals', 'heel', 'heels'],
            'dress': ['dress', 'dresses', 'gown', 'gowns'],
            'shirt': ['shirt', 'shirts', 'top', 'tops', 'blouse', 'blouses'],
            't-shirt': ['t-shirt', 't-shirts', 'tshirt', 'tshirts', 'tee', 'tees'],
            'jeans': ['jean', 'jeans', 'denim'],
            'trouser': ['trouser', 'trousers', 'pant', 'pants'],
            'blazer': ['blazer', 'blazers', 'jacket', 'jackets'],
            'kurta': ['kurta', 'kurtas', 'kurti', 'kurtis'],
            'saree': ['saree', 'sarees', 'sari', 'saris'],
            'skirt': ['skirt', 'skirts'],
            'bag': ['bag', 'bags', 'handbag', 'handbags', 'purse', 'purses'],
            'belt': ['belt', 'belts'],
            'wallet': ['wallet', 'wallets'],
            'watch': ['watch', 'watches'],
        }
        
        # Check if query contains product type keywords
        for product_type, keywords in product_type_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                required_subcategory = product_type
                break
        
        # Note: We don't add subcategory to where clause because ChromaDB doesn't support partial matching
        # Instead, we'll filter in post-processing for strict matching
        
        for ent in entities:
            try:
                text = (ent.get("text") or "").strip()
                cat = (ent.get("category") or "").strip().lower()
            except Exception:
                continue
            
            if text:
                keywords.append(text)
            
            if cat == "color":
                continue  # Use semantic search for colors
            
            meta_keys = CATEGORY_MAP.get(cat, [])
            for meta_key in meta_keys:
                if meta_key:
                    # Normalize size values (e.g., "m size" -> "M", "M size" -> "M")
                    if meta_key in ["size", "Size"]:
                        # Valid sizes whitelist - only accept these patterns
                        valid_sizes = [
                            'XS', 'S', 'M', 'L', 'XL', 'XXL', 'XXXL', 'XXXXL',
                            '2XL', '3XL', '4XL', '5XL',
                            'FREE SIZE', 'FREE', 'ONE SIZE',
                            # Numeric sizes (waist, etc.)
                            '28', '30', '32', '34', '36', '38', '40', '42', '44', '46', '48'
                        ]
                        # Extract size letter/number (M, L, XL, etc.)
                        size_match = re.search(r'\b(X{0,4}[SML]|FREE\s*SIZE|FREE|ONE\s*SIZE|\d{2})\b', text, re.I)
                        if size_match:
                            normalized_size = size_match.group(1).upper().replace(' ', ' ')
                            if normalized_size in valid_sizes or normalized_size.isdigit():
                                set_where(meta_key, normalized_size)
                            else:
                                print(f"⚠️ Ignoring invalid size: '{normalized_size}'")
                        else:
                            upper_text = text.upper().strip()
                            if upper_text in valid_sizes:
                                set_where(meta_key, upper_text)
                            else:
                                print(f"⚠️ Ignoring invalid size from CLU: '{upper_text}'")
                    elif meta_key in ["store_name", "Store_Name", "store_location", "Store_Location", "store_area", "Store_Area"]:
                        # ChromaDB doesn't support $contains, so we use $in with possible variations
                        normalized = text.strip()
                        # Determine which field to use
                        if meta_key in ["store_name", "Store_Name"]:
                            # If extracted_store_name was found in query, use that
                            store_value = extracted_store_name if extracted_store_name else normalized
                            # Create list of possible store name variations
                            # e.g., "LB Nagar" -> ["Shop Assist - LB Nagar"]
                            store_variations = []
                            if store_value:
                                # If it already has "Shop Assist -", use as is
                                if "shop assist" in store_value.lower():
                                    store_variations.append(store_value)
                                else:
                                    # Add "Shop Assist -" prefix
                                    store_variations.append(f"Shop Assist - {store_value}")
                                    # Also try exact match in case it's already in database
                                    store_variations.append(store_value)
                            if store_variations:
                                where[meta_key] = {"$in": store_variations}
                        elif meta_key in ["store_area", "Store_Area"]:
                            # Store area is simpler - just match the area name (e.g., "LB Nagar")
                            # This is the most reliable way to match locations
                            if normalized:
                                where[meta_key] = normalized
                        else:  # store_location
                            # For location, try to match using store_area instead (more reliable)
                            # But also try location variations
                            location_value = extracted_store_location if extracted_store_location else normalized
                            # Use store_area for matching (simpler and more reliable)
                            if location_value:
                                # Match against Store_Area field which has simple values like "LB Nagar"
                                where["Store_Area"] = location_value
                                # Also try location variations as fallback
                                location_variations = [location_value]
                                if "nagar" in location_value.lower():
                                    location_variations.append(f"{location_value} Main Road")
                                    location_variations.append(f"{location_value} Main Road, {location_value}")
                                where[meta_key] = {"$in": location_variations}
                    else:
                        set_where(meta_key, text)
                    break
        
        # If we extracted store info from query text but CLU didn't find it, add it now
        # Use $in with variations for matching, or Store_Area for simpler matching
        if extracted_store_name:
            # Check if already set by CLU entity
            if "store_name" not in where and "Store_Name" not in where and "store_area" not in where and "Store_Area" not in where:
                store_variations = []
                if "shop assist" in extracted_store_name.lower():
                    store_variations.append(extracted_store_name)
                    # Extract area from store name (after "-")
                    if '-' in extracted_store_name:
                        area = extracted_store_name.split('-', 1)[1].strip()
                        where["Store_Area"] = area
                else:
                    store_variations.append(f"Shop Assist - {extracted_store_name}")
                    store_variations.append(extracted_store_name)
                    # Also match by Store_Area (more reliable)
                    where["Store_Area"] = extracted_store_name
                if store_variations:
                    where["Store_Name"] = {"$in": store_variations}
        if extracted_store_location:
            # Check if already set by CLU entity
            if "store_location" not in where and "Store_Location" not in where and "store_area" not in where and "Store_Area" not in where:
                # Use Store_Area for matching (most reliable - simple values like "LB Nagar")
                where["Store_Area"] = extracted_store_location
                # Also try location variations as fallback
                location_variations = [extracted_store_location]
                if "nagar" in extracted_store_location.lower():
                    location_variations.append(f"{extracted_store_location} Main Road")
                    location_variations.append(f"{extracted_store_location} Main Road, {extracted_store_location}")
                where["Store_Location"] = {"$in": location_variations}
        
        query_text = fallback_query
        if keywords:
            query_text = f"{fallback_query} {' '.join(keywords[:5])}"
        
        # Enhance query with product type keywords for better semantic matching
        # IMPORTANT: Don't add generic words like "formal casual" - they match wrong products!
        if required_product_types:
            type_synonyms = {
                'dress': 'dress dresses frock gown maxi midi',
                'shirt': 'shirt shirts button-down',
                'jeans': 'jeans denim',
                't-shirt': 't-shirt tshirt tee',
                'pant': 'pants trousers',
                'jacket': 'jacket coat outerwear',
                'top': 'top tops blouse',
                'skirt': 'skirt skirts',
            }
            for ptype in required_product_types:
                if ptype in type_synonyms:
                    query_text = f"{query_text} {type_synonyms[ptype]}"
                    print(f"🔧 Enhanced query with '{ptype}' synonyms: {type_synonyms[ptype]}")
        
        # Add category filter to WHERE clause for better search results
        # This forces ChromaDB to only return products from the right category
        if required_category:
            where["product_category"] = required_category
            print(f"📦 Added category filter to ChromaDB: {required_category}")
        
        # Add subcategory filter for specific product types
        # This prevents semantic search from returning bags when user asks for dresses!
        subcategory_map = {
            'dress': ["Frocks and Dresses", "All Dresses", "Dresses"],
            'shirt': ["Shirts", "All Topwear"],
            'jeans': ["Jeans", "All Bottomwear"],
            't-shirt': ["T-Shirts", "All Topwear"],
            'pant': ["Trousers", "All Bottomwear"],
            'skirt': ["Skirts", "All Bottomwear"],
            'blazer': ["Blazers", "Formal Blazers"],
            'bag': ["Handbags", "All Accessories", "Sling Bags"],
        }
        if required_product_types:
            for ptype in required_product_types:
                if ptype in subcategory_map:
                    where["product_subcategory"] = {"$in": subcategory_map[ptype]}
                    print(f"👗 Added subcategory filter to ChromaDB: {subcategory_map[ptype]}")
                    break
        
        return query_text, where if where else None, required_category, required_subcategory, max_price, min_price, requires_discount, required_product_types
    
    def _format_results_for_gemini(self, results: List[Dict], context: Optional[str] = None) -> str:
        """Format search results for Gemini with concise summary (details shown in cards)."""
        count = len(results)
        if count == 1:
            formatted = f"We have {count} item available:\n\n"
        else:
            formatted = f"We have {count} items available:\n\n"
        
        for i, result in enumerate(results, 1):
            meta = result.get("metadata", {})
            
            def get_val(key, alt_key=None, default=""):
                """Helper to safely get value with fallback."""
                val = meta.get(key) or meta.get(alt_key) if alt_key else None
                if val is None or val == "" or (isinstance(val, float) and pd_isna(val)):
                    return default
                return str(val)
            
            # Concise summary - cards will show full details
            product_name = get_val('product_name', 'Product_Name')
            category = get_val('product_category', 'Product_Category')
            subcategory = get_val('product_subcategory', 'Product_Subcategory')
            size = get_val('size', 'Size')
            color = get_val('color', 'Color')
            availability = get_val('stock_status', 'Stock_Status') or get_val('availability', 'Availability')
            store_location = get_val('store_location', 'Store_Location')
            
            # Price summary
            discounted = get_val('discounted_price', 'Discounted_Price')
            base = get_val('base_price', 'Base_Price')
            discount_pct = get_val('discount_percent', 'Discount_Percent')
            
            price_info = ""
            try:
                if discounted and base and float(discounted) < float(base) and discount_pct and float(discount_pct) > 0:
                    price_info = f"₹{float(discounted):.2f} (was ₹{float(base):.2f}, {float(discount_pct):.0f}% off)"
                elif base:
                    price_info = f"₹{float(base):.2f}"
            except (ValueError, TypeError):
                if base:
                    price_info = f"₹{base}"
            
            # Build concise summary
            summary_parts = []
            if product_name:
                summary_parts.append(product_name)
            if category or subcategory:
                cat_text = " • ".join(filter(None, [category, subcategory]))
                if cat_text:
                    summary_parts.append(f"({cat_text})")
            if size:
                summary_parts.append(f"Size: {size}")
            if color:
                summary_parts.append(f"Color: {color}")
            if price_info:
                summary_parts.append(price_info)
            if availability:
                summary_parts.append(f"Status: {availability}")
            if store_location:
                summary_parts.append(f"Location: {store_location}")
            
            formatted += f"{i}. {' | '.join(summary_parts)}\n"
        
        if context:
            formatted += f"\n--- Previous Conversation: ---\n{context}\n"
        
        formatted += "\n--- NOTE: All product details are displayed in cards below. Provide a brief, friendly summary (2-3 sentences) like a store assistant would. Use natural language - say 'we have', 'available', 'in stock', etc. NEVER use technical terms like 'database', 'matching products', or 'found in database'. ---"
        
        return formatted
    
    def get_analytics(self) -> Dict:
        """Get analytics statistics."""
        return self.analytics.get_stats()
    
    def _is_new_topic(self, query: str, conversation_context: Optional[str] = None) -> bool:
        """
        Detect if the query is a new topic vs. continuation of previous conversation.
        Returns True if query appears to be a new, unrelated topic.
        """
        if not conversation_context:
            return True  # No context = new topic
        
        query_lower = query.lower().strip()
        
        # Check for explicit continuation keywords - these indicate continuation
        continuation_keywords = ['yes', 'yeah', 'yep', 'sure', 'ok', 'okay', 'show more', 'more', 
                                'continue', 'next', 'more results', 'see more', 'i want more', 
                                'show me more', 'what else', 'any other', 'another']
        if any(keyword in query_lower for keyword in continuation_keywords):
            return False  # This is a continuation
        
        # Extract key attributes from current query
        query_words = set(query_lower.split())
        
        # Extract key attributes from conversation context
        context_lower = conversation_context.lower()
        context_words = set(context_lower.split())
        
        # Key product attributes to compare
        colors = {'red', 'blue', 'green', 'black', 'white', 'yellow', 'pink', 'purple', 'orange', 
                 'brown', 'gray', 'grey', 'navy', 'maroon', 'beige', 'cream'}
        categories = {'men', "men's", 'women', "women's", 'kids', 'kid', 'boys', 'boy', 'girls', 'girl'}
        product_types = {'shirt', 'shirts', 'dress', 'dresses', 'pant', 'pants', 'trouser', 'trousers',
                        'shoe', 'shoes', 'bag', 'bags', 'handbag', 'handbags', 'top', 'tops', 'jean', 'jeans'}
        
        # Check if query has different color than context
        query_colors = colors.intersection(query_words)
        context_colors = colors.intersection(context_words)
        if query_colors and context_colors and not query_colors.intersection(context_colors):
            return True  # Different color = new topic
        
        # Check if query has different category than context
        query_categories = categories.intersection(query_words)
        context_categories = categories.intersection(context_words)
        if query_categories and context_categories and not query_categories.intersection(context_categories):
            return True  # Different category = new topic
        
        # Check if query has different product type than context
        query_types = product_types.intersection(query_words)
        context_types = product_types.intersection(context_words)
        if query_types and context_types and not query_types.intersection(context_types):
            return True  # Different product type = new topic
        
        # If query has multiple key attributes and none match context, it's likely a new topic
        query_key_attrs = query_colors | query_categories | query_types
        context_key_attrs = context_colors | context_categories | context_types
        if len(query_key_attrs) >= 2 and not query_key_attrs.intersection(context_key_attrs):
            return True  # Multiple attributes and none match = new topic
        
        return False  # Default: assume continuation if unclear
    
    def query_rag_with_images(self, query: str, num_results: int = 5, conversation_context: Optional[str] = None,
                              use_hybrid: bool = True, use_rerank: bool = True, enhance_images: bool = False,
                              offset: int = 0, user_gender: str = None) -> Tuple[str, List[Dict], bool, int]:
        """
        Query RAG and return both text response and results with image URLs.
        Uses local image paths from metadata (no generation/enhancement).
        
        Args:
            query: User query
            num_results: Number of results to return (default: 5, but we'll show only 3)
            conversation_context: Optional conversation context (None to auto-detect, "" to force no context)
            use_hybrid: Use hybrid search
            use_rerank: Use re-ranking
            enhance_images: Deprecated - kept for compatibility, always ignored
            offset: Offset for pagination (default: 0)
            user_gender: User's gender from profile ('male', 'female', 'kid') - used as default filter if no gender in query
        
        Returns: (response_text, results_with_images, has_more, total_count)
        """
        start_time = time.time()
        
        # Check for non-product queries (policy, FAQ, appointments, etc.) FIRST
        # These should be handled by Gemini without product search
        query_lower = query.lower()
        
        # Check for gibberish/nonsensical input
        # A query is likely gibberish if:
        # 1. Very short with no real words
        # 2. Contains mostly random characters
        # 3. No recognizable English words
        import re
        
        # Common meaningful words in shopping context
        meaningful_words = {
            'shirt', 'shirts', 'pant', 'pants', 'dress', 'dresses', 'jeans', 'top', 'tops',
            'jacket', 'blazer', 'skirt', 'shorts', 'kurta', 'saree', 'shoe', 'shoes',
            'bag', 'wallet', 'belt', 'watch', 'tie', 'scarf', 'hat', 'cap',
            'men', 'women', 'kids', 'boys', 'girls', 'man', 'woman', 'child',
            'red', 'blue', 'green', 'black', 'white', 'pink', 'yellow', 'orange', 'purple',
            'brown', 'grey', 'gray', 'navy', 'beige', 'maroon', 'olive',
            'small', 'medium', 'large', 'xl', 'xxl', 'xs', 'size',
            'cotton', 'silk', 'linen', 'polyester', 'wool',
            'formal', 'casual', 'party', 'office', 'wedding', 'festive',
            'cheap', 'expensive', 'discount', 'sale', 'offer', 'price', 'under', 'below',
            'show', 'find', 'search', 'looking', 'want', 'need', 'get', 'buy',
            'store', 'shop', 'available', 'stock', 'have', 'any',
            'hello', 'hi', 'hey', 'thanks', 'thank', 'help', 'please',
            'what', 'where', 'how', 'which', 'when', 'why', 'can', 'do', 'does',
            'return', 'exchange', 'refund', 'policy', 'order', 'delivery',
            'the', 'a', 'an', 'in', 'on', 'at', 'for', 'to', 'of', 'with', 'and', 'or'
        }
        
        # Extract words (letters only, at least 2 chars)
        query_words = set(re.findall(r'[a-zA-Z]{2,}', query_lower))
        
        # Check if query has any meaningful words
        has_meaningful_words = bool(query_words & meaningful_words)
        
        # Check if query is mostly random characters
        alpha_chars = sum(1 for c in query if c.isalpha())
        total_chars = len(query.replace(' ', ''))
        alpha_ratio = alpha_chars / total_chars if total_chars > 0 else 0
        
        # Query is gibberish if:
        # - Less than 3 meaningful words AND no recognized shopping terms
        # - OR very short with no meaning
        is_gibberish = (
            len(query_words) > 0 and 
            not has_meaningful_words and 
            len(query) > 3  # Not just a greeting like "hi"
        )
        
        # Check for other brand requests (Nike, Adidas, etc.)
        # Shop Assist only sells Shop Assist products!
        other_brands = [
            'nike', 'adidas', 'puma', 'reebok', 'fila', 'new balance', 'skechers',
            'levis', "levi's", 'wrangler', 'pepe jeans', 'spykar', 'killer',
            'zara', 'h&m', 'uniqlo', 'forever 21', 'mango', 'benetton',
            'tommy hilfiger', 'calvin klein', 'armani', 'gucci', 'prada', 'versace',
            'louis vuitton', 'burberry', 'ralph lauren', 'lacoste', 'hugo boss',
            'peter england', 'van heusen', 'raymond', 'park avenue', 'louis philippe',
            'arrow', 'blackberrys', 'indian terrain', 'monte carlo', 'colorplus',
            'woodland', 'red tape', 'bata', 'liberty', 'metro', 'hush puppies',
            'crocs', 'clarks', 'converse', 'vans', 'jordan', 'under armour',
            'fabindia', 'biba', 'global desi', 'aurelia',
            'pantaloons', 'lifestyle', 'shoppers stop', 'westside',
            'myntra', 'ajio', 'flipkart', 'amazon'
        ]
        
        # Short brand names that need word boundary matching (to avoid false positives)
        # e.g., 'w' brand shouldn't match "show", 'gap' shouldn't match in random text
        short_brands_word_boundary = ['w brand', 'gap', 'lee', 'max', 'and brand']
        
        mentioned_brand = None
        # Check regular brands (longer names, substring match is fine)
        for brand in other_brands:
            if brand in query_lower:
                mentioned_brand = brand
                break
        
        # Check short brands with word boundary
        if not mentioned_brand:
            query_words = set(query_lower.split())
            for brand in short_brands_word_boundary:
                # For "w brand" pattern, check if both words present
                if ' ' in brand:
                    parts = brand.split()
                    if all(p in query_words for p in parts):
                        mentioned_brand = brand
                        break
                elif brand in query_words:
                    mentioned_brand = brand
                    break
        
        if mentioned_brand:
            print(f"🏷️ Detected OTHER BRAND query: '{query}' (brand: {mentioned_brand})")
            brand_context = f"""The user is asking for a different brand: "{query}"

They mentioned "{mentioned_brand}" but this is an Shop Assist store chatbot.

Please provide a friendly response that:
1. Explains that we are Shop Assist and only sell Shop Assist products
2. We don't carry {mentioned_brand} products
3. Offer to show similar Shop Assist products instead (e.g., if they asked for Nike shoes, offer Shop Assist footwear)
4. Highlight Shop Assist's quality and style

Be helpful and not dismissive. Turn this into an opportunity to showcase Shop Assist products."""
            
            response = generate_human_readable_response(query, brand_context, conversation_context)
            response_time = time.time() - start_time
            self.analytics.log_query(query, "other_brand_query", response_time, True, 0)
            
            # Return empty results - no products for other brand queries
            return response, [], False, 0
        
        if is_gibberish:
            print(f"🤔 Detected GIBBERISH/UNCLEAR query: '{query}'")
            gibberish_context = f"""The user entered something unclear or random: "{query}"

Please provide a friendly response that:
1. Politely indicates you didn't understand the query
2. Asks them to rephrase or be more specific about what they're looking for
3. Gives examples of what they can ask: "Try asking things like 'Show me blue shirts for men' or 'Dresses under 2000'"
4. Be warm and helpful, not condescending

Keep it brief and friendly."""
            
            response = generate_human_readable_response(query, gibberish_context, conversation_context)
            response_time = time.time() - start_time
            self.analytics.log_query(query, "gibberish_query", response_time, True, 0)
            
            # Return empty results - no products for gibberish
            return response, [], False, 0
        
        # Policy/FAQ queries - don't search for products
        policy_keywords = [
            'policy', 'policies',  # Standalone policy keyword
            'return policy', 'refund policy', 'exchange policy', 'shipping policy',
            'return', 'refund', 'exchange', 'warranty', 'guarantee',
            'delivery time', 'shipping time', 'how long', 'when will',
            'store hours', 'opening hours', 'closing time', 'timings',
            'contact', 'phone number', 'email', 'customer service', 'helpline',
            'book an appointment', 'schedule a visit', 'make an appointment', 'appointment',
            'book appointment', 'booking', 'visit store', 'store visit', 'styling consultation',
            'suit fitting', 'personal stylist', 'try on', 'fitting room', 'reserve',
            'payment methods', 'payment options', 'accept credit card', 'upi', 'cash on delivery',
            'size chart', 'size guide', 'how to measure',
            'track order', 'order status', 'where is my order',
            'cancel order', 'modify order', 'change order',
            'gift card', 'voucher', 'coupon', 'promo code',
            'loyalty program', 'rewards', 'membership',
            'terms and conditions', 'terms of service', 'faq', 'faqs',
            'privacy policy', 'privacy', 'cod policy', 'cash on delivery',
            'emi option', 'emi available', 'installment', 'payment plan'
        ]
        
        # Check if query matches policy keywords, but exclude if it also contains product-related words
        is_policy_query = any(kw in query_lower for kw in policy_keywords)
        
        # Product-related words that would indicate a product search, not a policy query
        product_indicators = [
            'shirt', 'pant', 'dress', 'jeans', 'top', 'jacket', 'blazer', 'kurta',
            'shoe', 'bag', 'wallet', 'belt', 'skirt', 'shorts', 'trouser', 'polo',
            'wear', 'clothing', 'clothes', 'outfit', 'find me', 'show me', 'looking for'
        ]
        has_product_indicators = any(pi in query_lower for pi in product_indicators)
        
        # It's a policy query only if it has policy keywords AND no product indicators
        is_policy_query = is_policy_query and not has_product_indicators
        
        if is_policy_query:
            print(f"📋 Detected POLICY/FAQ query: '{query}'")
            policy_context = """This is a policy/FAQ question about Shop Assist store.
            
Policies:
- Return Policy: Products can be returned within 30 days of purchase with original tags and receipt.
- Exchange Policy: Exchanges are accepted within 30 days for different size/color.
- Refund: Refunds are processed within 7-10 business days to the original payment method.
- Shipping: Standard delivery takes 5-7 business days. Express delivery available in select areas.
- Store Hours: Most stores are open 10 AM to 9 PM, Monday to Sunday.
- Payment: We accept Credit/Debit cards, UPI, Net Banking, and Cash on Delivery.
- Appointment Booking: You can book an appointment at any Shop Assist store for personalized styling consultation, suit fitting, or bulk orders. Simply visit the store or call ahead to schedule. Walk-ins are also welcome!
- Store Pickup: For online orders, you can choose store pickup option. Your order will be ready within 2-4 hours at your selected store.
- Contact: For support, call 1800-xxx-xxxx .

Please provide a helpful, friendly response based on the above policies."""
            
            response = generate_human_readable_response(query, policy_context, conversation_context)
            response_time = time.time() - start_time
            self.analytics.log_query(query, "policy_query", response_time, True, 0)
            
            # Return empty results - no products for policy queries
            return response, [], False, 0
        
        # Check for translation requests
        translation_indicators = [
            'translate', 'translation', 'in hindi', 'in telugu', 'in tamil', 'in kannada',
            'in marathi', 'in bengali', 'in gujarati', 'in punjabi', 'in malayalam',
            'in spanish', 'in french', 'in german', 'in chinese', 'in japanese',
            'हिंदी में', 'తెలుగులో', 'தமிழில்', 'ಕನ್ನಡದಲ್ಲಿ',
            'convert to', 'say in', 'how to say'
        ]
        
        is_translation_query = any(indicator in query_lower for indicator in translation_indicators)
        
        if is_translation_query:
            print(f"🌐 Detected TRANSLATION query: '{query}'")
            translation_context = f"""The user is asking for translation: "{query}"

Please provide a helpful response explaining that:
1. Currently, all our product information is available in English only
2. We don't have built-in translation for product details
3. They can use browser's built-in translation feature (right-click > Translate) or Google Translate
4. We're happy to help them find products - just ask in any language!

Be friendly and helpful. Don't apologize excessively."""
            
            response = generate_human_readable_response(query, translation_context, conversation_context)
            response_time = time.time() - start_time
            self.analytics.log_query(query, "translation_query", response_time, True, 0)
            
            # Return empty results - no products for translation queries
            return response, [], False, 0
        
        # Check for comparison queries
        comparison_keywords = [
            'compare', 'comparison', 'comparing', 'versus', ' vs ', ' vs.', 
            'difference between', 'which is better', 'better than',
            'compare this', 'compare with', 'compare to', 'compared to',
            'what is the difference', 'how does it compare', 'side by side'
        ]
        
        is_comparison_query = any(kw in query_lower for kw in comparison_keywords)
        
        if is_comparison_query:
            print(f"⚖️ Detected COMPARISON query: '{query}'")
            comparison_context = f"""The user is asking for product comparison: "{query}"

Please provide a friendly response explaining that:
1. Product comparison feature is not available right now
2. We're working on enhancing this feature and it will be available soon
3. In the meantime, they can search for individual products and check their details
4. Suggest they can ask about specific product features like "What material is the blue shirt?" or "Show me shirts under 2000"

Be friendly, helpful and apologetic. Keep it brief."""
            
            response = generate_human_readable_response(query, comparison_context, conversation_context)
            response_time = time.time() - start_time
            self.analytics.log_query(query, "comparison_query", response_time, True, 0)
            
            # Return empty results - no products for comparison queries
            return response, [], False, 0
        
        # Check for personal/account queries (order history, past purchases, etc.)
        # Note: 'my cart' is handled separately in app_flask.py to trigger cart UI
        personal_query_indicators = [
            'my order', 'my orders', 'order history', 'past order', 'previous order',
            'last order', 'what did i order', 'what i ordered', 'ordered last',
            'my purchase', 'my purchases', 'purchase history', 'bought before',
            'what did i buy', 'what i bought', 'my wishlist',
            'my account', 'my profile', 'my address', 'saved address',
            'order status', 'track my order', 'where is my order'
        ]
        
        is_personal_query = any(indicator in query_lower for indicator in personal_query_indicators)
        
        if is_personal_query:
            print(f"👤 Detected PERSONAL/ACCOUNT query: '{query}'")
            # This needs to be handled by the app layer which has access to session
            # Return a special marker that app_flask.py will handle
            personal_context = f"""The user is asking about their personal account/order history: "{query}"

This requires checking their account. Please provide a helpful response that:
1. If they want to see order history, tell them to click the User/Account button to log in and view their purchase history
2. Mention that once logged in, they can see all their past orders, saved items, and account details
3. Be helpful and guide them to the right place

Note: You cannot access their order history directly - they need to log in through the User button."""
            
            response = generate_human_readable_response(query, personal_context, conversation_context)
            response_time = time.time() - start_time
            self.analytics.log_query(query, "personal_query", response_time, True, 0)
            
            # Return empty results - no products for personal queries
            return response, [], False, 0
        
        # Check for celebrity/influencer style queries
        celebrity_indicators = [
            'like the one', 'like what', 'worn by', 'wears', 'wore', 'wearing',
            'celebrity', 'actor', 'actress', 'bollywood', 'hollywood', 
            'influencer', 'star wears', 'famous', 'seen on',
            'shah rukh', 'shahrukh', 'srk', 'salman khan', 'aamir khan', 'hrithik',
            'ranveer', 'ranbir', 'virat', 'dhoni', 'sachin',
            'deepika', 'priyanka', 'alia', 'kareena', 'katrina', 'anushka',
            'amitabh', 'akshay kumar', 'ajay devgn', 'varun dhawan',
            'rajinikanth', 'vijay', 'mahesh babu', 'prabhas', 'allu arjun',
            'movie style', 'film look', 'red carpet', 'award show'
        ]
        
        is_celebrity_query = any(indicator in query_lower for indicator in celebrity_indicators)
        
        if is_celebrity_query:
            print(f"🌟 Detected CELEBRITY/STYLE query: '{query}'")
            celebrity_context = f"""The user is asking about celebrity fashion: "{query}"

IMPORTANT: We don't have information about specific outfits worn by celebrities or influencers. 
Please provide a helpful, friendly response that:
1. Acknowledges we can't match exact celebrity outfits
2. Offers to help find similar styles based on general descriptions
3. Asks the user to describe the style they're looking for (e.g., formal shirts, casual shirts, specific color, etc.)
4. Suggests they describe features like: color, pattern, fit (slim/regular), occasion (formal/casual)

Be warm and helpful, not apologetic. Turn this into an opportunity to understand what they really want."""
            
            response = generate_human_readable_response(query, celebrity_context, conversation_context)
            response_time = time.time() - start_time
            self.analytics.log_query(query, "celebrity_query", response_time, True, 0)
            
            # Return empty results - no products for celebrity queries
            return response, [], False, 0
        
        # Get conversation context from memory if not provided
        if conversation_context is None:
            conversation_context = self.memory.get_context()
        
        # Check if this is a new topic - if so, ignore conversation context
        if conversation_context and self._is_new_topic(query, conversation_context):
            print(f"🔄 Detected new topic query: '{query}'")
            print(f"   Previous context was about different product/color/category")
            print(f"   Ignoring conversation context for this query")
            conversation_context = None
        elif conversation_context:
            print(f"📝 Using conversation context for query: '{query}'")
        
        # Call CLU with timeout
        clu_start = time.time()
        clu_result = self.call_clu(query)
        clu_time = time.time() - clu_start
        if clu_time > 1.0:
            print(f"⚠️ CLU call took {clu_time:.2f}s (slow)")
        
        prediction = clu_result.get("result", {}).get("prediction", {})
        intent = prediction.get("topIntent", "None")
        intent_confidence = 0.0
        intents_list = prediction.get("intents", [])
        if intents_list:
            intent_confidence = intents_list[0].get("confidenceScore", 0.0)
        entities = prediction.get("entities", [])
        
        # Log the CLU classification result
        print(f"🎯 CLU Intent: '{intent}' (confidence: {intent_confidence:.2f})")
        if entities:
            entity_summary = [(e.get("category", ""), e.get("text", "")) for e in entities[:5]]
            print(f"🏷️ CLU Entities: {entity_summary}")
        
        # ============================================================
        # INTENT-BASED ROUTING SYSTEM
        # Route queries based on CLU intent classification
        # ============================================================
        
        # Extract product-related entities from CLU
        product_entity_categories = ['product_type', 'product_name', 'category', 'subcategory', 'product']
        product_entities = [e for e in entities if e.get("category", "").lower() in product_entity_categories]
        has_product_entity = len(product_entities) > 0
        
        # Extract other entity types
        color_entities = [e for e in entities if e.get("category", "").lower() == 'color']
        size_entities = [e for e in entities if e.get("category", "").lower() == 'size']
        location_entities = [e for e in entities if e.get("category", "").lower() in ['location', 'store', 'store_name']]
        price_entities = [e for e in entities if e.get("category", "").lower() in ['price', 'price_range', 'budget']]
        
        # Helper to check if query needs product specification
        def needs_product_clarification(intent_name: str) -> bool:
            """Check if the intent requires product specification but none was provided."""
            intents_requiring_product = ['Search', 'CheckAvailability', 'PriceInquiry', 'CompareProducts']
            if intent_name not in intents_requiring_product:
                return False
            return not has_product_entity
        
        # ---- INTENT: StoreInfo ----
        # User asking about store hours, locations, contact info
        if intent == "StoreInfo":
            print(f"📍 Routing to StoreInfo handler")
            store_context = """The user is asking about Shop Assist store information.

Store Information:
- Store Hours: Most Shop Assist stores are open 10 AM to 9 PM, Monday to Sunday
- Locations: We have stores across major cities including Hyderabad (Kondapur, Ameerpet, Punjagutta, Secunderabad, LB Nagar), Bangalore, Chennai, Mumbai, Delhi, and more
- Services: In-store styling, alterations, gift wrapping available at select locations
- Contact: Visit shopassist.com or call 1800-xxx-xxxx for store-specific queries

Please provide helpful store information based on the query."""
            
            response = generate_human_readable_response(query, store_context, conversation_context)
            response_time = time.time() - start_time
            self.analytics.log_query(query, intent, response_time, True, 0)
            return response, [], False, 0
        
        # ---- INTENT: GeneralQuery ----
        # Generic questions, greetings, or unclear queries
        if intent == "GeneralQuery":
            print(f"❓ Routing to GeneralQuery handler")
            
            # Check for product keywords directly in query text (CLU may miss these)
            product_keywords = ['dress', 'dresses', 'shirt', 'shirts', 't-shirt', 'tshirt', 'jeans', 'jean',
                               'pant', 'pants', 'trouser', 'trousers', 'top', 'tops', 'blouse', 'kurta', 'kurti',
                               'jacket', 'blazer', 'coat', 'skirt', 'shorts', 'sweater', 'hoodie', 'sweatshirt',
                               'polo', 'frock', 'gown', 'wallet', 'bag', 'handbag', 'belt', 'watch']
            has_product_keyword = any(kw in query_lower for kw in product_keywords)
            
            # Check for price patterns (indicates product search intent)
            has_price_pattern = bool(re.search(r'under\s*\d+|below\s*\d+|less\s+than\s*\d+|above\s*\d+|over\s*\d+|\d+\s*(?:rs|rupees|inr|₹)', query_lower))
            
            # If there are product entities, keywords, or price patterns, treat as Search instead
            if has_product_entity or has_product_keyword or has_price_pattern:
                if has_product_keyword:
                    print(f"   → Has product keywords in query, redirecting to Search flow")
                elif has_price_pattern:
                    print(f"   → Has price pattern in query, redirecting to Search flow")
                else:
                    print(f"   → Has product entities, redirecting to Search flow")
            else:
                general_context = f"""The user asked: "{query}"

This is a general question. Respond helpfully:
- If greeting → greet back and ask how you can help them find products
- If asking about the store → provide brief store info
- If unclear → ask what product they're looking for (shirts, dresses, accessories, etc.)

Be friendly and guide them toward product discovery."""
                
                response = generate_human_readable_response(query, general_context, conversation_context)
                response_time = time.time() - start_time
                self.analytics.log_query(query, intent, response_time, True, 0)
                return response, [], False, 0
        
        # ---- INTENT: CheckAvailability ----
        # User wants to know if something is in stock
        if intent == "CheckAvailability" and not has_product_entity:
            print(f"📦 Routing to CheckAvailability handler (no product specified)")
            availability_context = f"""The user asked: "{query}"

They want to check availability but didn't specify a product.

Respond by:
1. Acknowledge their question about availability
2. Mention we have many products in stock
3. Ask what they're looking for: shirts, pants, dresses, accessories?
4. Offer to help find specific items

Keep it conversational and helpful."""
            
            response = generate_human_readable_response(query, availability_context, conversation_context)
            response_time = time.time() - start_time
            self.analytics.log_query(query, intent, response_time, True, 0)
            return response, [], False, 0
        
        # ---- INTENT: PriceInquiry ----
        # User asking about prices without specifying product
        if intent == "PriceInquiry" and not has_product_entity:
            print(f"💰 Routing to PriceInquiry handler (no product specified)")
            price_context = f"""The user asked: "{query}"

They're asking about prices but didn't specify a product.

Respond by:
1. Mention our price ranges: Shirts ₹999-2999, Pants ₹1499-3499, Dresses ₹1999-4999, Accessories ₹499-1999
2. Ask what product they want to see prices for
3. Mention we have items across different budgets

Be helpful and guide them to specify a product."""
            
            response = generate_human_readable_response(query, price_context, conversation_context)
            response_time = time.time() - start_time
            self.analytics.log_query(query, intent, response_time, True, 0)
            return response, [], False, 0
        
        # ---- INTENT: FindStoreStock ----
        # User wants products at a specific store
        if intent == "FindStoreStock" and not has_product_entity and not location_entities:
            print(f"🏪 Routing to FindStoreStock handler (missing details)")
            store_stock_context = f"""The user asked: "{query}"

They want to find products at a store but need more details.

Ask them:
1. Which store location they're interested in (Kondapur, Ameerpet, Secunderabad, etc.)
2. What product they're looking for

Keep it brief and helpful."""
            
            response = generate_human_readable_response(query, store_stock_context, conversation_context)
            response_time = time.time() - start_time
            self.analytics.log_query(query, intent, response_time, True, 0)
            return response, [], False, 0
        
        # ---- INTENT: CompareProducts ----
        # User wants to compare products
        if intent == "CompareProducts" and len(product_entities) < 2:
            print(f"⚖️ Routing to CompareProducts handler (need more products)")
            compare_context = f"""The user asked: "{query}"

They want to compare products but need to specify at least 2 items.

Ask them to tell you which products they want to compare.
Example: "Compare blue shirt vs white shirt" or "Compare formal pants and casual pants"."""
            
            response = generate_human_readable_response(query, compare_context, conversation_context)
            response_time = time.time() - start_time
            self.analytics.log_query(query, intent, response_time, True, 0)
            return response, [], False, 0
        
        # ---- INTENT: Search (vague/unspecific) ----
        # User says something like "show something nice", "show me items", "what do you have"
        if intent == "Search" and not has_product_entity:
            # Check if query has any meaningful product hints
            vague_search_indicators = ['something', 'anything', 'items', 'products', 'stuff', 'things', 'nice', 'good', 'best']
            is_vague_search = any(word in query_lower for word in vague_search_indicators)
            
            if is_vague_search or len(query_lower.split()) <= 4:
                print(f"🤔 Routing to vague Search handler (no product specified)")
                vague_search_context = f"""The user asked: "{query}"

They want to see products but haven't specified what type.

Respond by:
1. Acknowledge their interest in our products
2. Ask what category interests them:
   - Men's wear: shirts, pants, blazers, accessories
   - Women's wear: dresses, tops, kurtas, accessories  
   - Kids' wear: boys and girls clothing
3. Or ask about the occasion: formal, casual, party, office?
4. Mention you can also show trending items, new arrivals, or deals

Be friendly and help them discover what they're looking for."""
                
                response = generate_human_readable_response(query, vague_search_context, conversation_context)
                response_time = time.time() - start_time
                self.analytics.log_query(query, intent, response_time, True, 0)
                return response, [], False, 0
        
        # ---- INTENTS THAT PROCEED TO SEARCH ----
        # TrendingItems, NewArrivals, Bestsellers, FindDeal, FestiveFilter
        # These don't require specific products - they show category-based results
        if intent in ["TrendingItems", "NewArrivals", "Bestsellers"]:
            print(f"🔥 Routing to {intent} handler - will search for trending/new/best items")
            # Let these pass through to search with appropriate enrichment
        
        if intent == "FindDeal" and not has_product_entity:
            print(f"🏷️ Routing to FindDeal handler - will search for deals")
            # Let this pass through to search for discounted items
        
        # ---- DEFAULT: Proceed to Product Search ----
        # For Search intent with entities, or any intent that passed the checks above
        print(f"🔍 Proceeding to product search (Intent: {intent})")
        
        # Build search query (pass user_gender for default filtering when no gender in query)
        enriched_query, where, required_category, required_subcategory, max_price, min_price, requires_discount, required_product_types = self._build_search_from_clu(prediction, query, user_gender)
        
        # Debug: Print where clause for location filtering
        if where:
            print(f"🔍 Where clause for filtering: {where}")
            # Check if store location/area is being filtered
            store_filters = {k: v for k, v in where.items() if 'store' in k.lower() or 'Store' in k or 'location' in k.lower() or 'Location' in k or 'area' in k.lower() or 'Area' in k}
            if store_filters:
                print(f"📍 Store/Location filters: {store_filters}")
            else:
                print(f"⚠️ No store/location filters found in where clause!")
        else:
            print(f"⚠️ No where clause generated - location filtering may not work")
        
        # Perform search - optimize: get fewer results initially (reduce from num_results*3 to num_results*2)
        # Also limit re-ranking to fewer results for speed
        # But get more results if price filtering is applied (since many may be filtered out)
        search_start = time.time()
        # Limit initial search to reasonable number
        # Get more results when filters are applied (price, product type) since many may be filtered out
        has_price_constraint = max_price is not None or min_price is not None
        has_type_constraint = len(required_product_types) > 0
        has_any_constraint = has_price_constraint or has_type_constraint
        search_n = min(num_results * 6, 60) if has_any_constraint else min(num_results * 2, 20)
        all_results = self.search(enriched_query, n_results=search_n, where=where,
                            use_hybrid=use_hybrid, use_rerank=use_rerank)
        search_time = time.time() - search_start
        if search_time > 2.0:
            print(f"⚠️ Search took {search_time:.2f}s (slow)")
        print(f"🔍 Found {len(all_results)} results in {search_time:.2f}s")
        
        # Debug: Check if results are from different locations
        if all_results:
            locations = set()
            for result in all_results[:5]:  # Check first 5 results
                meta = result.get('metadata', {})
                store_area = meta.get('store_area') or meta.get('Store_Area', '')
                store_name = meta.get('store_name') or meta.get('Store_Name', '')
                if store_area:
                    locations.add(store_area)
                elif store_name:
                    locations.add(store_name)
            if len(locations) > 1:
                print(f"⚠️ Results from multiple locations: {locations}")
            elif where and ('Store_Area' in where or 'store_area' in where or 'Store_Name' in where or 'store_name' in where):
                print(f"✅ All results from same location: {locations}")
        
        # Extract store filters from where clause for post-filtering
        required_store_name = None
        required_store_location = None
        required_store_area = None
        if where:
            required_store_name = where.get('store_name') or where.get('Store_Name')
            required_store_location = where.get('store_location') or where.get('Store_Location')
            required_store_area = where.get('store_area') or where.get('Store_Area')
            # If $in operator is used, extract the values
            if isinstance(required_store_name, dict) and '$in' in required_store_name:
                # Use the first value as the primary match
                required_store_name = required_store_name['$in'][0] if required_store_name['$in'] else None
            if isinstance(required_store_location, dict) and '$in' in required_store_location:
                required_store_location = required_store_location['$in'][0] if required_store_location['$in'] else None
        
        # Post-filter results - filter by price, product type, color, gender, and size
        has_price_filter = max_price is not None or min_price is not None
        has_product_type_filter = len(required_product_types) > 0
        
        # Extract required size from where clause or query
        required_size = None
        if where:
            required_size = where.get('size') or where.get('Size')
        # Also detect size from query text if not in where clause
        if not required_size:
            size_pattern = re.search(r'\bsize\s*([XSML]{1,3}|\d{2})\b|\b(X{0,2}[SML])\b(?:\s|$)', query.upper())
            if size_pattern:
                required_size = size_pattern.group(1) or size_pattern.group(2)
        has_size_filter = required_size is not None
        if has_size_filter:
            print(f"📏 POST-FILTER: Detected size filter: {required_size}")
        
        # Extract color and gender from query
        query_lower = query.lower()
        colors = ['black', 'white', 'red', 'blue', 'green', 'yellow', 'pink', 'purple', 'orange', 'brown', 'grey', 'gray', 'beige', 'navy', 'maroon']
        required_color = None
        for c in colors:
            if c in query_lower:
                required_color = c
                break
        
        # Detect gender from query - use word-level matching to avoid "men" matching in "women"
        # Strip punctuation from words (e.g., "women?" -> "women")
        query_words = set(word.strip(string.punctuation) for word in query_lower.replace("'", "").replace("'", "").split())
        required_gender = None
        # Check women FIRST (before men, since "women" contains "men")
        if query_words & {'women', 'woman', 'womens', 'ladies', 'lady', 'female'}:
            required_gender = 'women'
            print(f"👩 POST-FILTER: Detected WOMEN's category")
        elif query_words & {'men', 'man', 'mens', 'male'}:
            required_gender = 'men'
            print(f"👨 POST-FILTER: Detected MEN's category")
        elif query_words & {'boy', 'boys', 'girl', 'girls', 'kid', 'kids', 'child', 'children'}:
            required_gender = 'kids'
            print(f"👶 POST-FILTER: Detected KIDS category")
        
        has_color_filter = required_color is not None
        has_gender_filter = required_gender is not None
        has_discount_filter = requires_discount
        
        # Detect STYLE/OCCASION from query (formal, casual, party, etc.)
        style_keywords = {
            'formal': ['formal', 'office', 'business', 'professional', 'work wear', 'workwear'],
            'casual': ['casual', 'everyday', 'relaxed', 'weekend'],
            'party': ['party', 'evening', 'festive', 'wedding', 'celebration'],
            'sports': ['sports', 'gym', 'athletic', 'workout', 'fitness', 'active']
        }
        required_style = None
        for style, keywords in style_keywords.items():
            if any(kw in query_lower for kw in keywords):
                required_style = style
                print(f"👔 Detected STYLE from query: {required_style}")
                break
        
        has_style_filter = required_style is not None
        
        # Minimum discount threshold for "sale" queries (30%+)
        MIN_SALE_DISCOUNT = 30
        
        if (has_price_filter or has_product_type_filter or has_color_filter or has_gender_filter or has_discount_filter or has_style_filter or has_size_filter) and all_results:
            print(f"🔍 POST-FILTER: color={required_color}, gender={required_gender}, size={required_size}, types={required_product_types}, style={required_style}, discount_required={has_discount_filter}")
            print(f"🔍 Products from semantic search:")
            for r in all_results[:5]:
                m = r.get('metadata', {})
                pn = m.get('product_name') or m.get('Product_Name', 'Unknown')
                pc = m.get('product_category') or m.get('Product_Category', '')
                print(f"   - {pn[:50]} | cat: {pc}")
            
            filtered_results = []
            for result in all_results:
                meta = result.get('metadata', {})
                product_name = (meta.get('product_name') or meta.get('Product_Name', '')).lower()
                product_subcategory = (meta.get('product_subcategory') or meta.get('Product_Subcategory', '')).lower()
                product_color = (meta.get('color') or meta.get('Color', '')).lower()
                product_category = (meta.get('product_category') or meta.get('Product_Category', '')).lower()
                
                # Check color
                color_match = True
                if required_color:
                    color_match = required_color in product_color or required_color in product_name
                
                # Check size
                size_match = True
                if required_size:
                    product_size = (meta.get('size') or meta.get('Size', '')).upper().strip()
                    size_match = product_size == required_size.upper().strip()
                
                # Check gender - use word boundary matching to avoid "men" matching "women"
                gender_match = True
                if required_gender:
                    # Split product name into words for accurate matching
                    name_words = set(product_name.split())
                    is_kids = bool(name_words & {'boys', 'girls', 'kids', 'boy', 'girl', 'kid'})
                    
                    if required_gender == 'men':
                        # Check for "men" as a word, NOT as substring of "women"
                        is_mens = bool(name_words & {'men', 'man', 'mens'}) or product_name.startswith('men ')
                        is_mens = is_mens or "men's" in product_category
                        # Explicitly exclude women's products
                        is_womens = bool(name_words & {'women', 'woman', 'womens'}) or 'women' in product_category
                        gender_match = is_mens and not is_womens and not is_kids
                    elif required_gender == 'women':
                        is_womens = bool(name_words & {'women', 'woman', 'womens'}) or "women's" in product_category
                        gender_match = is_womens and not is_kids
                    elif required_gender == 'kids':
                        gender_match = is_kids or 'kids' in product_category
                
                # Check product type (shirt, pants, dress, etc.)
                product_type_match = True
                if required_product_types:
                    product_type_match = False
                    # Check product NAME first (more reliable than subcategory which may be wrong)
                    for ptype in required_product_types:
                        if ptype.lower() in product_name:
                            product_type_match = True
                            break
                    
                    # Exclude mismatched items (e.g., bags when looking for dresses)
                    # This handles data quality issues where bags are labeled as "Dresses"
                    exclude_keywords = {
                        'dress': ['bag', 'handbag', 'laptop bag', 'sling bag', 'wallet', 'belt'],
                        'shirt': ['bag', 'handbag', 'wallet', 'pant', 'trouser'],
                        'pant': ['shirt', 'bag', 'wallet'],
                        'jeans': ['shirt', 'bag', 'wallet'],
                    }
                    for ptype in required_product_types:
                        if ptype in exclude_keywords:
                            for exclude in exclude_keywords[ptype]:
                                if exclude in product_name:
                                    product_type_match = False
                                    break
                
                # Check price
                price_match = True
                if max_price is not None or min_price is not None:
                    product_price = None
                    try:
                        discounted = meta.get('discounted_price') or meta.get('Discounted_Price')
                        base = meta.get('base_price') or meta.get('Base_Price')
                        if discounted:
                            product_price = float(discounted)
                        elif base:
                            product_price = float(base)
                    except (ValueError, TypeError):
                        pass
                    
                    if product_price is not None:
                        if max_price is not None and product_price > max_price:
                            price_match = False
                        if min_price is not None and product_price < min_price:
                            price_match = False
                
                # Check discount (for "sale" queries)
                discount_match = True
                if has_discount_filter:
                    try:
                        discount_pct = meta.get('discount_percent') or meta.get('Discount_Percent') or 0
                        if discount_pct:
                            discount_pct = float(discount_pct)
                        else:
                            discount_pct = 0
                        # Require minimum discount for sale queries
                        discount_match = discount_pct >= MIN_SALE_DISCOUNT
                    except (ValueError, TypeError):
                        discount_match = False
                
                # Check style/occasion (formal, casual, party, sports)
                # Logic: Include if product matches style OR is neutral (doesn't have opposite style)
                style_match = True
                if required_style:
                    # Check product name and subcategory for style keywords
                    style_keywords_to_match = style_keywords.get(required_style, [])
                    # Check if any style keyword is in product name or subcategory
                    style_in_name = any(kw in product_name for kw in style_keywords_to_match)
                    style_in_subcat = any(kw in product_subcategory for kw in style_keywords_to_match)
                    
                    # Define opposite styles - exclude products with OPPOSITE style
                    opposite_styles = {
                        'formal': ['casual', 'sports', 'gym', 'athletic', 'workout', 'relaxed', 'everyday'],
                        'casual': ['formal', 'office', 'business', 'professional'],
                        'party': ['sports', 'gym', 'athletic', 'workout'],
                        'sports': ['formal', 'office', 'business', 'party', 'evening']
                    }
                    opposite_keywords = opposite_styles.get(required_style, [])
                    has_opposite_style = any(kw in product_name for kw in opposite_keywords)
                    
                    # Match if: has required style OR (is neutral AND doesn't have opposite)
                    # Neutral = doesn't have any style keyword explicitly
                    style_match = style_in_name or style_in_subcat or (not has_opposite_style)
                
                if price_match and product_type_match and color_match and gender_match and size_match and discount_match and style_match:
                    filtered_results.append(result)
            
            filter_info = []
            if has_price_filter:
                filter_info.append(f"price")
            if has_product_type_filter:
                filter_info.append(f"type:{required_product_types}")
            if has_color_filter:
                filter_info.append(f"color:{required_color}")
            if has_size_filter:
                filter_info.append(f"size:{required_size}")
            if has_gender_filter:
                filter_info.append(f"gender:{required_gender}")
            if has_discount_filter:
                filter_info.append(f"discount>={MIN_SALE_DISCOUNT}%")
            if has_style_filter:
                filter_info.append(f"style:{required_style}")
            print(f"✅ Filtered: {len(all_results)} -> {len(filtered_results)} by {', '.join(filter_info)}")
            all_results = filtered_results
            
            # GENERALIZED FALLBACK: If semantic search failed to find matching products,
            # do a direct database scan with the filters
            if len(filtered_results) == 0 and (has_product_type_filter or has_price_filter):
                print(f"🔄 FALLBACK: Semantic search returned no matches, doing direct DB scan...")
                fallback_results = self._direct_product_search(
                    product_types=required_product_types,
                    max_price=max_price,
                    min_price=min_price,
                    color=required_color,
                    gender=required_gender,
                    category=required_category,
                    requires_discount=requires_discount,
                    min_discount=MIN_SALE_DISCOUNT if requires_discount else None,
                    style=required_style
                )
                if fallback_results:
                    print(f"✅ FALLBACK found {len(fallback_results)} matching products!")
                    all_results = fallback_results
        
        # Pagination: show only 3 results at a time
        RESULTS_PER_PAGE = 3
        total_count = len(all_results)
        start_idx = offset
        end_idx = offset + RESULTS_PER_PAGE
        results = all_results[start_idx:end_idx]
        has_more = end_idx < total_count
        
        if not results:
            response_time = time.time() - start_time
            self.analytics.log_query(query, intent, response_time, False, 0)
            # Create a more specific "not found" message
            not_found_msg = f"No matching items found for: {query}"
            return generate_human_readable_response(query, not_found_msg, conversation_context), [], False, 0
        
        # Image enhancement removed - using local image paths from metadata only
        # Images are already stored locally and referenced via Image_Path in metadata
        
        # Format results for Gemini
        format_start = time.time()
        structured_data = self._format_results_for_gemini(results, conversation_context)
        format_time = time.time() - format_start
        if format_time > 1.0:
            print(f"⚠️ Formatting took {format_time:.2f}s (slow)")
        
        # Generate response
        gemini_start = time.time()
        response = generate_human_readable_response(query, structured_data, conversation_context)
        gemini_time = time.time() - gemini_start
        if gemini_time > 5.0:
            print(f"⚠️ Gemini response took {gemini_time:.2f}s (slow)")
        
        # Add "show more" prompt if there are more results
        if has_more:
            remaining = total_count - end_idx
            response += f"\n\nWould you like to see more? There are {remaining} more items available."
        
        # Update memory
        self.memory.add_message("user", query)
        self.memory.add_message("assistant", response)
        
        # Log analytics
        response_time = time.time() - start_time
        self.analytics.log_query(query, intent, response_time, True, len(results))
        
        # Performance summary
        print(f"⏱️ Total query time: {response_time:.2f}s")
        if response_time > 10.0:
            print(f"⚠️ WARNING: Query took {response_time:.2f}s - consider optimizing")
            print(f"   - Check logs above for slow operations")
            print(f"   - Consider disabling re-ranking or reducing num_results")
        
        return response, results, has_more, total_count


class ShoppingAgent:
    """Agentic framework for complex multi-step queries."""
    
    def __init__(self, rag_system: AdvancedRAG):
        self.rag = rag_system
        self.tools = {
            'search_products': self._search_products,
            'compare_prices': self._compare_prices,
            'check_availability': self._check_availability,
            'find_stores': self._find_stores,
            'filter_by_attribute': self._filter_by_attribute,
        }
    
    def process_query(self, query: str) -> str:
        """Process query using agentic reasoning."""
        # Analyze query to determine tools needed
        plan = self._plan_query(query)
        
        results = []
        for step in plan:
            tool_name = step['tool']
            if tool_name in self.tools:
                tool_result = self.tools[tool_name](**step.get('params', {}))
                results.append(tool_result)
        
        # Synthesize final response
        return self._synthesize_response(query, results)
    
    def _plan_query(self, query: str) -> List[Dict]:
        """Plan the steps needed to answer the query."""
        query_lower = query.lower()
        plan = []
        
        # Check if comparison needed
        if any(word in query_lower for word in ['compare', 'difference', 'better', 'cheaper']):
            plan.append({'tool': 'compare_prices', 'params': {'query': query}})
        
        # Check if store location needed
        if any(word in query_lower for word in ['where', 'store', 'location', 'near']):
            plan.append({'tool': 'find_stores', 'params': {'query': query}})
        
        # Check if availability check needed
        if any(word in query_lower for word in ['available', 'stock', 'in stock']):
            plan.append({'tool': 'check_availability', 'params': {'query': query}})
        
        # Default: search products
        if not plan:
            plan.append({'tool': 'search_products', 'params': {'query': query}})
        
        return plan
    
    def _search_products(self, query: str, **kwargs) -> Dict:
        """Search for products."""
        results = self.rag.search(query, n_results=5, use_hybrid=True, use_rerank=True)
        return {'type': 'products', 'data': results}
    
    def _compare_prices(self, query: str, **kwargs) -> Dict:
        """Compare prices of products."""
        results = self.rag.search(query, n_results=10, use_hybrid=True, use_rerank=True)
        # Extract prices and compare
        prices = []
        for r in results:
            meta = r.get('metadata', {})
            price = meta.get('discounted_price') or meta.get('Discounted_Price') or meta.get('base_price') or meta.get('Base_Price')
            if price:
                prices.append({'product': meta.get('product_name', 'Unknown'), 'price': price})
        
        return {'type': 'price_comparison', 'data': sorted(prices, key=lambda x: float(x['price']) if isinstance(x['price'], (int, float)) else 0)}
    
    def _check_availability(self, query: str, **kwargs) -> Dict:
        """Check product availability."""
        results = self.rag.search(query, n_results=5, use_hybrid=True, use_rerank=True)
        availability = []
        for r in results:
            meta = r.get('metadata', {})
            availability.append({
                'product': meta.get('product_name', 'Unknown'),
                'availability': meta.get('availability', 'Unknown'),
                'stock': meta.get('stock_quantity', 'Unknown'),
                'store': meta.get('store_name', 'Unknown')
            })
        return {'type': 'availability', 'data': availability}
    
    def _find_stores(self, query: str, **kwargs) -> Dict:
        """Find stores based on query."""
        results = self.rag.search(query, n_results=10, use_hybrid=True, use_rerank=True)
        stores = {}
        for r in results:
            meta = r.get('metadata', {})
            store_name = meta.get('store_name') or meta.get('Store_Name')
            location = meta.get('store_location') or meta.get('Store_Location')
            if store_name:
                if store_name not in stores:
                    stores[store_name] = {
                        'location': location,
                        'products': []
                    }
                stores[store_name]['products'].append(meta.get('product_name', 'Unknown'))
        return {'type': 'stores', 'data': stores}
    
    def _filter_by_attribute(self, attribute: str, value: str, **kwargs) -> Dict:
        """Filter products by attribute."""
        where = {attribute: value}
        results = self.rag.search("", n_results=10, where=where, use_hybrid=True, use_rerank=True)
        return {'type': 'filtered_products', 'data': results}
    
    def _synthesize_response(self, query: str, results: List[Dict]) -> str:
        """Synthesize agent results into final response."""
        if not results:
            return "I couldn't find any information to answer your query."
        
        # Format results for Gemini
        formatted = f"Query: {query}\n\n"
        for i, result in enumerate(results, 1):
            formatted += f"Result {i} ({result['type']}):\n"
            formatted += json.dumps(result['data'], indent=2)[:500] + "\n\n"
        
        # Use RAG to generate response
        return self.rag.query_rag(query, num_results=5, conversation_context=formatted)


class FeedbackSystem:
    """Feedback loop for learning from user interactions."""
    
    def __init__(self, rag_system: AdvancedRAG):
        self.rag = rag_system
        self.feedback_log = []
        self.feedback_file = "feedback.json"
        self.load_feedback()
    
    def record_feedback(self, query: str, response: str, user_feedback: str, 
                       helpful: bool, rating: Optional[int] = None):
        """Record user feedback."""
        feedback_entry = {
            'timestamp': datetime.now().isoformat(),
            'query': query,
            'response': response[:200],  # Truncate
            'user_feedback': user_feedback,
            'helpful': helpful,
            'rating': rating
        }
        
        self.feedback_log.append(feedback_entry)
        
        # Analyze and learn
        self._analyze_feedback(feedback_entry)
        
        # Save periodically
        if len(self.feedback_log) % 5 == 0:
            self.save_feedback()
    
    def _analyze_feedback(self, feedback: Dict):
        """Analyze feedback to improve system."""
        if not feedback.get('helpful'):
            # Negative feedback - analyze why
            query = feedback.get('query', '')
            user_feedback = feedback.get('user_feedback', '')
            
            # Check for common issues
            if 'not found' in user_feedback.lower() or 'no results' in user_feedback.lower():
                # Query might need expansion
                print(f"📊 Learning: Query '{query}' had no results - may need query expansion")
            
            elif 'wrong' in user_feedback.lower() or 'incorrect' in user_feedback.lower():
                # Results might be incorrect
                print(f"📊 Learning: Query '{query}' returned incorrect results - may need better filtering")
    
    def get_feedback_stats(self) -> Dict:
        """Get feedback statistics."""
        if not self.feedback_log:
            return {'total_feedback': 0}
        
        helpful_count = sum(1 for f in self.feedback_log if f.get('helpful'))
        total = len(self.feedback_log)
        
        return {
            'total_feedback': total,
            'helpful_count': helpful_count,
            'helpful_rate': f"{(helpful_count/total*100):.1f}%",
            'avg_rating': np.mean([f.get('rating', 0) for f in self.feedback_log if f.get('rating')]) if any(f.get('rating') for f in self.feedback_log) else 0
        }
    
    def save_feedback(self):
        """Save feedback to file."""
        try:
            with open(self.feedback_file, 'w') as f:
                json.dump(self.feedback_log, f, indent=2)
        except Exception as e:
            print(f"⚠️ Failed to save feedback: {e}")
    
    def load_feedback(self):
        """Load feedback from file."""
        if os.path.exists(self.feedback_file):
            try:
                with open(self.feedback_file, 'r') as f:
                    self.feedback_log = json.load(f)
            except Exception as e:
                print(f"⚠️ Failed to load feedback: {e}")


# Multi-modal search functions
def search_by_image(rag_system: AdvancedRAG, image_path: str, n_results: int = 5) -> List[Dict]:
    """Search products by image using CLIP."""
    if not rag_system.clip_model:
        return []
    
    try:
        # Load and process image
        image = Image.open(image_path)
        inputs = rag_system.clip_processor(images=image, return_tensors="pt")
        
        # Get image embedding
        image_features = rag_system.clip_model.get_image_features(**inputs)
        image_embedding = image_features[0].detach().numpy()
        
        # Search in ChromaDB (would need to store image embeddings)
        # For now, return empty - requires image embeddings in database
        print("⚠️ Image search requires image embeddings in database")
        return []
    except Exception as e:
        print(f"⚠️ Image search failed: {e}")
        return []

