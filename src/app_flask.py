#!/usr/bin/env python3
"""
Shop Assist Smart Apparel Finder - Custom Flask Web App
-------------------------------------------------------
Custom HTML/CSS interface with responsive design and real-time chat.
"""

from flask import Flask, render_template, request, jsonify, session
from flask_socketio import SocketIO, emit
import sys, os, requests
import warnings
import pandas as pd
from pathlib import Path
from config import Config
from advanced_rag import AdvancedRAG, ShoppingAgent, FeedbackSystem
from user_management import UserManager, StockManager
import uuid
import json
from datetime import datetime

# Suppress FutureWarnings and other warnings at the very start
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", module="huggingface_hub")
warnings.filterwarnings("ignore", module="transformers")
warnings.filterwarnings("ignore", message=".*use_fast.*")
warnings.filterwarnings("ignore", message=".*slow processor.*")

# Suppress ONNX runtime GPU discovery warnings (harmless, just checking for GPU)
import os
os.environ['ORT_DEVICE_DISCOVERY_LOG_LEVEL'] = 'ERROR'

# Suppress ChromaDB telemetry errors
import logging
logging.getLogger("chromadb.telemetry").setLevel(logging.CRITICAL)
logging.getLogger("chromadb").setLevel(logging.WARNING)

# Monkey-patch Werkzeug to suppress "write() before start_response" errors
# This error occurs during WebSocket handshake failures (harmless on rapid reconnects)
try:
    from werkzeug.serving import WSGIRequestHandler
    original_handle = WSGIRequestHandler.handle
    
    def patched_handle(self):
        """Patched handle method that catches AssertionError during WebSocket handshakes."""
        try:
            return original_handle(self)
        except AssertionError as e:
            if 'start_response' in str(e):
                # This is a harmless error during WebSocket handshake failures
                # Log it as a warning instead of crashing
                print(f"⚠️ WebSocket handshake error (harmless on reconnect): {e}")
                # Try to send a minimal error response
                try:
                    self.send_error(500, "WebSocket handshake error")
                except:
                    pass
                return
            raise
        except Exception as e:
            # Log other errors but don't suppress them
            error_str = str(e)
            if 'start_response' in error_str or 'write() before' in error_str:
                print(f"⚠️ WebSocket handshake error (harmless on reconnect): {e}")
                try:
                    self.send_error(500, "WebSocket handshake error")
                except:
                    pass
                return
            raise
    
    WSGIRequestHandler.handle = patched_handle
    
    # Replace run_wsgi method with a version that has a patched write function
    original_run_wsgi = WSGIRequestHandler.run_wsgi
    
    def patched_run_wsgi(self):
        """Patched run_wsgi with a write function that handles WebSocket handshake errors gracefully."""
        # Import necessary modules
        from werkzeug.exceptions import InternalServerError
        from werkzeug.serving import connection_dropped_errors
        import selectors
        
        if self.headers.get("Expect", "").lower().strip() == "100-continue":
            self.wfile.write(b"HTTP/1.1 100 Continue\r\n\r\n")

        self.environ = environ = self.make_environ()
        status_set: str | None = None
        headers_set: list[tuple[str, str]] | None = None
        status_sent: str | None = None
        headers_sent: list[tuple[str, str]] | None = None
        chunk_response: bool = False

        def write(data: bytes) -> None:
            nonlocal status_sent, headers_sent, chunk_response
            # Patched: Don't raise AssertionError, just return silently if start_response wasn't called
            # This handles WebSocket handshake failures gracefully
            if status_set is None or headers_set is None:
                # This is a WebSocket handshake error - silently ignore it
                # (This happens during rapid reconnects/disconnects and is completely harmless)
                # The client will automatically retry the connection
                return
            
            if status_sent is None:
                status_sent = status_set
                headers_sent = headers_set
                try:
                    code_str, msg = status_sent.split(None, 1)
                except ValueError:
                    code_str, msg = status_sent, ""
                code = int(code_str)
                self.send_response(code, msg)
                header_keys = set()
                for key, value in headers_sent:
                    self.send_header(key, value)
                    header_keys.add(key.lower())

                if (
                    not (
                        "content-length" in header_keys
                        or environ["REQUEST_METHOD"] == "HEAD"
                        or (100 <= code < 200)
                        or code in {204, 304}
                    )
                    and self.protocol_version >= "HTTP/1.1"
                ):
                    chunk_response = True
                    self.send_header("Transfer-Encoding", "chunked")

                self.send_header("Connection", "close")
                self.end_headers()

            assert isinstance(data, bytes), "applications must write bytes"

            if data:
                if chunk_response:
                    self.wfile.write(hex(len(data))[2:].encode())
                    self.wfile.write(b"\r\n")

                self.wfile.write(data)

                if chunk_response:
                    self.wfile.write(b"\r\n")

            self.wfile.flush()

        def start_response(status, headers, exc_info=None):
            nonlocal status_set, headers_set
            if exc_info:
                try:
                    if headers_sent:
                        raise exc_info[1].with_traceback(exc_info[2])
                finally:
                    exc_info = None
            elif headers_set:
                raise AssertionError("Headers already set")
            status_set = status
            headers_set = headers
            return write

        def execute(app):
            application_iter = app(environ, start_response)
            try:
                for data in application_iter:
                    write(data)
                if not headers_sent:
                    write(b"")
                if chunk_response:
                    self.wfile.write(b"0\r\n\r\n")
            finally:
                selector = selectors.DefaultSelector()
                selector.register(self.connection, selectors.EVENT_READ)
                total_size = 0
                total_reads = 0

                while selector.select(timeout=0.01):
                    data = self.rfile.read(10_000_000)
                    total_size += len(data)
                    total_reads += 1

                    if not data or total_size >= 10_000_000_000 or total_reads > 1000:
                        break

                selector.close()

                if hasattr(application_iter, "close"):
                    application_iter.close()

        try:
            execute(self.server.app)
        except connection_dropped_errors as e:
            self.connection_dropped(e, environ)
        except AssertionError as e:
            # Catch AssertionError specifically for WebSocket handshake errors
            error_str = str(e)
            if 'start_response' in error_str or 'write() before' in error_str:
                # Silently ignore - this is a harmless WebSocket handshake error
                # that occurs during rapid reconnects. The client will retry automatically.
                return
            raise
        except Exception as e:
            if self.server.passthrough_errors:
                raise

            if status_sent is not None and chunk_response:
                self.close_connection = True

            try:
                if status_sent is None:
                    status_set = None
                    headers_set = None
                execute(InternalServerError())
            except Exception:
                pass

            from werkzeug.debug.tbtools import DebugTraceback

            msg = DebugTraceback(e).render_traceback_text()
            self.server.log("error", f"Error on request:\n{msg}")
    
    WSGIRequestHandler.run_wsgi = patched_run_wsgi
    
    print("✓ Werkzeug patched to handle WebSocket handshake errors (handle + run_wsgi)")
except Exception as e:
    print(f"⚠️ Could not patch Werkzeug: {e}")
    import traceback
    traceback.print_exc()

# Monkey-patch ChromaDB telemetry
try:
    import chromadb.telemetry.events as telemetry_events
    if hasattr(telemetry_events, 'capture'):
        original_capture = telemetry_events.capture
        def patched_capture(*args, **kwargs):
            try:
                return original_capture(*args, **kwargs)
            except:
                pass
        telemetry_events.capture = patched_capture
except:
    pass

# Read settings
config = Config()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 hours in seconds

# Configure SocketIO with increased timeout settings to match client
# Explicitly set async_mode to threading to avoid reloader issues
socketio = SocketIO(
    app, 
    cors_allowed_origins="*",
    ping_timeout=60,  # Increase ping timeout to 60 seconds (default is 5s)
    ping_interval=25,  # Keep ping interval at 25 seconds
    max_http_buffer_size=1000000,  # 1MB max message size
    async_mode='threading',  # Explicitly use threading mode for Werkzeug compatibility
    logger=False,  # Disable Socket.IO logging to reduce noise
    engineio_logger=False  # Disable Engine.IO logging
)

# Wrap the Socket.IO wrapped app with error handler
# Socket.IO wraps Flask's wsgi_app, so we need to wrap that
original_wsgi_app = app.wsgi_app
def wrapped_wsgi_app(environ, start_response):
    try:
        return original_wsgi_app(environ, start_response)
    except AssertionError as e:
        # Catch "write() before start_response" errors during WebSocket handshake
        if 'start_response' in str(e):
            print(f"⚠️ WebSocket handshake error (usually harmless on reconnect): {e}")
            # Try to return a minimal error response
            try:
                status = '500 Internal Server Error'
                headers = [('Content-Type', 'text/plain')]
                write = start_response(status, headers)
                if write:
                    write(b'WebSocket handshake error')
                return [b'WebSocket handshake error']
            except:
                # If we can't call start_response, return empty
                return []
        raise
    except Exception as e:
        # Log other errors but don't suppress them
        print(f"⚠️ WSGI Error: {e}")
        raise

# Apply the wrapper after Socket.IO has wrapped the app
app.wsgi_app = wrapped_wsgi_app

# Initialize Advanced RAG System
try:
    rag = AdvancedRAG()
    agent = ShoppingAgent(rag)
    feedback_system = FeedbackSystem(rag)
    rag.feedback_system = feedback_system  # Attach feedback system
    user_manager = UserManager()  # Initialize user management
    stock_manager = StockManager()  # Initialize stock management
    print("✓ Advanced RAG system initialized with all features")
    print("✓ User management system initialized")
    print("✓ Stock management system initialized")
except Exception as e:
    print(f"❌ Failed to initialize Advanced RAG: {e}")
    rag = None
    agent = None
    feedback_system = None
    user_manager = None
    stock_manager = None

# Store pending queries for continuation (session-based)
# Format: {session_id: {'query': str, 'offset': int, 'total': int, 'enriched_query': str, 'where': dict, 'required_category': str, 'required_subcategory': str}}
pending_queries = {}

# Store per-session conversation memory to prevent cross-user data leakage
# Format: {session_id: ConversationMemory instance}
# Each user gets their own isolated conversation context
from advanced_rag import ConversationMemory
session_memories = {}

def get_session_memory(session_id: str) -> ConversationMemory:
    """Get or create conversation memory for a session."""
    if session_id not in session_memories:
        session_memories[session_id] = ConversationMemory()
    return session_memories[session_id]

def cleanup_old_sessions(max_age_hours=24):
    """Clean up old session memories to prevent memory leaks."""
    from datetime import datetime, timedelta
    cutoff = datetime.now() - timedelta(hours=max_age_hours)
    # Note: We'd need to track session creation time to implement this properly
    # For now, we'll rely on Socket.IO disconnect events
    pass

def is_continuation_query(query: str) -> bool:
    """Detect if query is a continuation request (yes, show more, etc.)"""
    query_lower = query.lower().strip()
    continuation_keywords = ['yes', 'yeah', 'yep', 'sure', 'ok', 'okay', 'show more', 'more', 'continue', 
                           'next', 'more results', 'see more', 'i want more', 'show me more']
    return any(keyword in query_lower for keyword in continuation_keywords)

def clean_product_description(description: str) -> str:
    """
    Clean product description to remove redundant data and keep only meaningful text.
    
    Args:
        description: Raw product description text
        
    Returns:
        Cleaned, concise product description
    """
    if not description or not isinstance(description, str):
        return ""
    
    import re
    
    # Remove common redundant patterns
    # Remove product name if it appears at the start
    desc = description.strip()
    
    # Remove price patterns
    desc = re.sub(r'₹[\d,]+\.?\d*', '', desc)
    desc = re.sub(r'Mrp\s*₹[\d,]+\.?\d*', '', desc, flags=re.I)
    desc = re.sub(r'\d+%\s*OFF', '', desc, flags=re.I)
    desc = re.sub(r'Inclusive of all taxes', '', desc, flags=re.I)
    
    # Remove button/action text
    desc = re.sub(r'Buy now', '', desc, flags=re.I)
    desc = re.sub(r'Add to Bag', '', desc, flags=re.I)
    desc = re.sub(r'ADD TO WISHLIST', '', desc, flags=re.I)
    
    # Remove delivery/return info
    desc = re.sub(r'Delivery Options.*?availability', '', desc, flags=re.I | re.DOTALL)
    desc = re.sub(r'Express Delivery.*?available', '', desc, flags=re.I | re.DOTALL)
    desc = re.sub(r'Free shipping.*', '', desc, flags=re.I)
    desc = re.sub(r'\d+\s*days?\s*Free Return.*', '', desc, flags=re.I)
    desc = re.sub(r'Not the right size.*', '', desc, flags=re.I | re.DOTALL)
    desc = re.sub(r'Need it fast.*', '', desc, flags=re.I | re.DOTALL)
    desc = re.sub(r'Select location.*', '', desc, flags=re.I | re.DOTALL)
    desc = re.sub(r'to see availability.*', '', desc, flags=re.I)
    desc = re.sub(r'Login.*?location', '', desc, flags=re.I | re.DOTALL)
    
    # Remove product details section
    desc = re.sub(r'product details.*?View More', '', desc, flags=re.I | re.DOTALL)
    desc = re.sub(r'Material:.*?Collection:.*?View More', '', desc, flags=re.I | re.DOTALL)
    
    # Remove product declaration
    desc = re.sub(r'product declaration.*', '', desc, flags=re.I | re.DOTALL)
    desc = re.sub(r'Product:.*?Number', '', desc, flags=re.I | re.DOTALL)
    desc = re.sub(r'Net Quantity:.*', '', desc, flags=re.I)
    desc = re.sub(r'Marketed by.*', '', desc, flags=re.I | re.DOTALL)
    desc = re.sub(r'For Customer.*', '', desc, flags=re.I | re.DOTALL)
    desc = re.sub(r'Toll Free.*', '', desc, flags=re.I)
    desc = re.sub(r'Customer Complaints.*', '', desc, flags=re.I | re.DOTALL)
    
    # Remove delivery/returns/exchange section
    desc = re.sub(r'Delivery, Returns And Exchange.*', '', desc, flags=re.I | re.DOTALL)
    desc = re.sub(r'Delivery.*?shipping', '', desc, flags=re.I | re.DOTALL)
    desc = re.sub(r'Return.*?policy', '', desc, flags=re.I | re.DOTALL)
    desc = re.sub(r'Exchange.*?policy', '', desc, flags=re.I | re.DOTALL)
    
    # Remove size/color labels that appear in description
    desc = re.sub(r'Size:\s*Color:.*', '', desc, flags=re.I)
    desc = re.sub(r'Size:.*?Color:.*', '', desc, flags=re.I)
    
    # Remove repeated product name patterns (e.g., "Shop AssistmencasualsshirtsMen")
    desc = re.sub(r'^[A-Z][a-z]+\s*[A-Z][a-z]+\s*[a-z]+\s*[a-z]+\s*[A-Z]', '', desc)
    
    # Split into lines and filter
    lines = desc.split('\n')
    clean_lines = []
    
    # Keywords that indicate meaningful description
    description_keywords = [
        'elevate', 'crafted', 'designed', 'perfect', 'features', 'ensures', 
        'embrace', 'step into', 'ideal for', 'makes it', 'comfortable', 
        'breathable', 'versatile', 'sophisticated', 'elegant', 'stylish',
        'premium', 'quality', 'collection', 'wardrobe', 'outfit'
    ]
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Skip if it's too short (likely a label)
        if len(line) < 20:
            continue
        
        # Skip if it's all caps (likely a header)
        if line.isupper() and len(line) > 10:
            continue
        
        # Skip if it contains technical fields
        if re.match(r'^(Material|Fit|Style|Code|Brand|Collar|Color|Cuffs|Occasion|Pattern|Sleeves|Subbrand|ProductType|Collection):', line, re.I):
            continue
        
        # Keep if it looks like a meaningful description
        if any(keyword in line.lower() for keyword in description_keywords):
            clean_lines.append(line)
        elif len(line) > 50:  # Long lines are likely descriptions
            clean_lines.append(line)
    
    # Join and clean up
    if clean_lines:
        cleaned = ' '.join(clean_lines)
        # Remove extra whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned)
        # Remove leading/trailing whitespace
        cleaned = cleaned.strip()
        # Limit length to reasonable size (2-3 sentences)
        if len(cleaned) > 300:
            # Take first 300 characters and cut at last sentence
            cleaned = cleaned[:300]
            last_period = cleaned.rfind('.')
            if last_period > 200:
                cleaned = cleaned[:last_period + 1]
        return cleaned
    
    return ""

# Legacy class removed - using AdvancedRAG instead
# All functionality is now in advanced_rag.py

def extract_product_card_data(results):
    """Extract comprehensive product data for display in cards."""
    images = []
    for result in results:
        meta = result.get('metadata', {})
        # Check for local image path first, then fall back to URL
        image_path = meta.get('Image_Path') or meta.get('image_path')
        image_url = meta.get('image_url') or meta.get('Image_URL')
        
        # Use local path if available, otherwise use URL
        if image_path and image_path.strip():
            # Convert local path to Flask URL
            # Remove 'data/' prefix if present and serve via Flask static route
            if image_path.startswith('data/'):
                image_url = f"/static/{image_path.replace('data/', '')}"
            elif image_path.startswith('/'):
                image_url = f"/static{image_path}"
            else:
                image_url = f"/static/{image_path}"
        elif image_url and image_url.strip():
            # Keep original URL if no local path
            pass
        else:
            continue  # Skip if no image available
        
        if image_url and image_url.strip():
            # Get price with discount info
            discounted = meta.get('discounted_price') or meta.get('Discounted_Price')
            base = meta.get('base_price') or meta.get('Base_Price')
            discount_pct = meta.get('discount_percent') or meta.get('Discount_Percent')
            
            # Format price string
            price_str = ""
            try:
                if discounted and base and float(discounted) < float(base) and discount_pct and float(discount_pct) > 0:
                    price_str = f"₹{float(discounted):.2f} (Original: ₹{float(base):.2f}, {float(discount_pct):.0f}% off)"
                elif base:
                    price_str = f"₹{float(base):.2f}"
            except (ValueError, TypeError):
                if base:
                    price_str = f"₹{base}"
            
            # Clean description to remove redundant data
            raw_description = meta.get('product_description') or meta.get('Product_Description', '')
            cleaned_description = clean_product_description(raw_description)
            
            images.append({
                'url': image_url,
                'product_name': meta.get('product_name') or meta.get('Product_Name', ''),
                'description': cleaned_description,
                'category': meta.get('product_category') or meta.get('Product_Category', ''),
                'subcategory': meta.get('product_subcategory') or meta.get('Product_Subcategory', ''),
                'size': meta.get('size') or meta.get('Size', ''),
                'color': meta.get('color') or meta.get('Color', ''),
                'material': meta.get('material') or meta.get('Material', ''),
                'pattern': meta.get('pattern') or meta.get('Pattern', ''),
                'price': price_str,
                'base_price': base,
                'discounted_price': discounted,
                'discount_percent': discount_pct,
                'availability': meta.get('availability') or meta.get('Availability', ''),
                'stock_status': meta.get('stock_status') or meta.get('Stock_Status', ''),
                'store_name': meta.get('store_name') or meta.get('Store_Name', ''),
                'store_location': meta.get('store_location') or meta.get('Store_Location', ''),
                'product_url': meta.get('product_url') or meta.get('Product_URL', '')
            })
    return images

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/static/images/<path:filename>')
def serve_image(filename):
    """Serve images from data/images directory"""
    from flask import send_from_directory
    import os
    images_dir = os.path.join('data', 'images')
    return send_from_directory(images_dir, filename)

@app.route('/api/query', methods=['POST'])
def api_query():
    try:
        if not rag:
            return jsonify({'error': 'RAG system not initialized'}), 500
        
        data = request.get_json()
        query = data.get('query', '').strip()
        use_agent = data.get('use_agent', False)  # Option to use agentic framework
        
        if not query:
            return jsonify({'error': 'Please enter a query.'}), 400
        
        # Process query through RAG (with or without agent)
        if use_agent and agent:
            response = agent.process_query(query)
            # Extract images from agent results if available
            images = []
        else:
            # Use query_rag_with_images to get both response and image data
            # Get session ID for HTTP requests (if available)
            session_id = session.get('session_id', None) or request.remote_addr
            session_memory = get_session_memory(session_id) if session_id else None
            conversation_context = session_memory.get_context() if session_memory else None
            
            # Use local image paths from metadata (no enhancement)
            if hasattr(rag, 'query_rag_with_images'):
                response, results, has_more, total_count = rag.query_rag_with_images(
                    query, num_results=10, use_hybrid=True, use_rerank=True, 
                    enhance_images=False, offset=0, conversation_context=conversation_context
                )
                images = extract_product_card_data(results)
            else:
                response = rag.query_rag(query, num_results=5, use_hybrid=True, use_rerank=True, 
                                       conversation_context=conversation_context)
                images = []
            
            # Update session memory
            if session_memory:
                session_memory.add_message("user", query)
                session_memory.add_message("assistant", response)
        
        return jsonify({
            'success': True,
            'response': response,
            'query': query,
            'used_agent': use_agent,
            'images': images
        })
    except Exception as e:
        import traceback
        print(f"❌ API query error: {e}")
        traceback.print_exc()
        # Use friendly fallback response instead of error
        fallback_response = "I apologize, but I'm having trouble processing your request. Please try again or rephrase your question."
        return jsonify({
            'success': True,
            'response': fallback_response,
            'query': query if 'query' in dir() else '',
            'used_agent': False,
            'images': []
        })

@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    try:
        # request.sid might not be available immediately during handshake
        # Use getattr to safely access it
        session_id = getattr(request, 'sid', None)
        if session_id:
            print(f"✅ Client connected: {session_id}")
            # Initialize session memory if needed
            get_session_memory(session_id)
        return True
    except Exception as e:
        print(f"❌ Error in connect handler: {e}")
        import traceback
        traceback.print_exc()
        # Return True to allow connection even if initialization fails
        return True

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection and clean up session data."""
    try:
        # request.sid might not be available if connection failed
        session_id = getattr(request, 'sid', None)
        if session_id:
            print(f"❌ Client disconnected: {session_id}")
            # Clean up session data
            if session_id in session_memories:
                del session_memories[session_id]
            if session_id in pending_queries:
                del pending_queries[session_id]
    except Exception as e:
        print(f"❌ Error in disconnect handler: {e}")
        import traceback
        traceback.print_exc()

@socketio.on('send_message')
def handle_message(data):
    try:
        if not rag:
            emit('bot_response', {'error': 'RAG system not initialized'})
            return
        
        query = data.get('message', '').strip()
        # Get session ID from Flask-SocketIO request context (request.sid is available in socket handlers)
        session_id = request.sid  # Flask-SocketIO provides request.sid in handler context
        use_agent = data.get('use_agent', False)
        
        if not query:
            emit('bot_response', {'error': 'Please enter a message.'})
            return
        
        # Send typing indicator
        emit('bot_typing', {'typing': True})
        
        # Check if this is a continuation query
        is_continuation = is_continuation_query(query)
        pending = pending_queries.get(session_id)
        
        if is_continuation and pending:
            # Continue with previous query - use STORED filters to get consistent results
            original_query = pending['query']
            enriched_query = pending.get('enriched_query', original_query)
            where = pending.get('where', {})
            required_category = pending.get('required_category')
            required_subcategory = pending.get('required_subcategory')
            max_price = pending.get('max_price')
            min_price = pending.get('min_price')
            requires_discount = pending.get('requires_discount', False)
            required_product_types = pending.get('required_product_types', [])
            required_color = pending.get('required_color')
            offset = pending['offset'] + 3  # Next 3 results
            
            print(f"🔄 Continuing query: {original_query}")
            print(f"🔄 Using stored filters - category: {required_category}, subcategory: {required_subcategory}, color: {required_color}, price: {max_price}/{min_price}")
            print(f"🔄 Offset: {offset}")
            
            # Use stored filters to continue search - don't re-run CLU
            if hasattr(rag, 'query_rag_with_images'):
                # Call internal search method with stored filters to get consistent results
                try:
                    # Perform search with stored filters
                    num_results = 15
                    all_results = rag.search(enriched_query, n_results=num_results*3, where=where,
                                            use_hybrid=True, use_rerank=True)
                    
                    # Post-filter results using ALL stored filters (category, subcategory, color, price, product type)
                    if all_results:
                        filtered_results = []
                        for result in all_results:
                            meta = result.get('metadata', {})
                            product_category = meta.get('product_category') or meta.get('Product_Category', '')
                            product_subcategory = (meta.get('product_subcategory') or meta.get('Product_Subcategory', '')).lower()
                            product_name = (meta.get('product_name') or meta.get('Product_Name', '')).lower()
                            product_color = (meta.get('color') or meta.get('Color', '')).lower()
                            
                            # Check category match (if required)
                            category_match = True
                            if required_category:
                                if required_category == "Men's Clothing":
                                    category_match = ("Men" in product_category or "Men's" in product_category) and \
                                                    "women" not in product_name and "woman" not in product_name and \
                                                    "girls" not in product_name and "girl" not in product_name
                                elif required_category == "Women's Clothing":
                                    category_match = ("Women" in product_category or "Women's" in product_category) and \
                                                    "men" not in product_name and "man" not in product_name and \
                                                    "boys" not in product_name and "boy" not in product_name
                                elif required_category == "Kids & Teens":
                                    category_match = ("Kids" in product_category or "Teens" in product_category or "Boys" in product_category or "Girls" in product_category) or \
                                                    ("boys" in product_name or "girls" in product_name or "boy" in product_name or "girl" in product_name or "kids" in product_name or "kid" in product_name)
                                    if "women" in product_name or "woman" in product_name or "men" in product_name or "man" in product_name:
                                        category_match = False
                            
                            # Check subcategory/product type match (if required)
                            subcategory_match = True
                            if required_subcategory:
                                type_variations = {
                                    'trouser': ['trouser', 'trousers', 'pant', 'pants'],
                                    'shoe': ['shoe', 'shoes', 'footwear', 'sneaker', 'sneakers', 'boot', 'boots'],
                                    'shirt': ['shirt', 'shirts', 'top', 'tops'],
                                    'dress': ['dress', 'dresses', 'gown', 'gowns'],
                                    'jeans': ['jeans', 'jean', 'denim'],
                                }
                                variations = type_variations.get(required_subcategory.lower(), [required_subcategory.lower()])
                                subcategory_match = any(var in product_subcategory for var in variations)
                                if not subcategory_match:
                                    subcategory_match = any(var in product_name for var in variations)
                            
                            # Check color match (if required)
                            color_match = True
                            if required_color:
                                color_match = required_color in product_color or required_color in product_name
                            
                            # Check price match (if required)
                            price_match = True
                            if max_price is not None or min_price is not None:
                                try:
                                    discounted = meta.get('discounted_price') or meta.get('Discounted_Price')
                                    base = meta.get('base_price') or meta.get('Base_Price')
                                    product_price = float(discounted) if discounted else (float(base) if base else None)
                                    if product_price is not None:
                                        if max_price is not None and product_price > max_price:
                                            price_match = False
                                        if min_price is not None and product_price < min_price:
                                            price_match = False
                                except (ValueError, TypeError):
                                    pass
                            
                            # Check product type match (if required)
                            product_type_match = True
                            if required_product_types:
                                product_type_match = any(ptype.lower() in product_name for ptype in required_product_types)
                            
                            if category_match and subcategory_match and color_match and price_match and product_type_match:
                                filtered_results.append(result)
                        
                        all_results = filtered_results
                    
                    # Pagination: show only 3 results at a time
                    RESULTS_PER_PAGE = 3
                    total_count = len(all_results)
                    start_idx = offset
                    end_idx = offset + RESULTS_PER_PAGE
                    results = all_results[start_idx:end_idx]
                    has_more = end_idx < total_count
                    
                    if not results:
                        from geminiLLM import generate_human_readable_response
                        # Use session-specific context
                        session_memory = get_session_memory(session_id)
                        conversation_context = session_memory.get_context() if session_memory else None
                        not_found_msg = f"No more matching items found for: {original_query}"
                        response = generate_human_readable_response(original_query, not_found_msg, conversation_context)
                        images = []
                        pending_queries.pop(session_id, None)
                        # Update session memory
                        if session_memory:
                            session_memory.add_message("user", query)
                            session_memory.add_message("assistant", response)
                    else:
                        # Image enhancement removed - using local image paths from metadata only
                        
                        # Format and generate response with session-specific context
                        session_memory = get_session_memory(session_id)
                        conversation_context = session_memory.get_context() if session_memory else None
                        structured_data = rag._format_results_for_gemini(results, conversation_context)
                        from geminiLLM import generate_human_readable_response
                        response = generate_human_readable_response(original_query, structured_data, conversation_context)
                        
                        # Update session memory
                        if session_memory:
                            session_memory.add_message("user", query)
                            session_memory.add_message("assistant", response)
                        
                        # Note: "Would you like to see more?" is already added by query_rag_with_images
                        
                        images = extract_product_card_data(results)
                        
                        # Update pending query with all filters for next continuation
                        if has_more:
                            pending_queries[session_id] = {
                                'query': original_query,
                                'offset': offset,
                                'total': total_count,
                                'enriched_query': enriched_query,
                                'where': where,
                                'required_category': required_category,
                                'required_subcategory': required_subcategory,
                                'max_price': max_price,
                                'min_price': min_price,
                                'requires_discount': requires_discount,
                                'required_product_types': required_product_types,
                                'required_color': required_color
                            }
                        else:
                            # No more results, remove from pending
                            pending_queries.pop(session_id, None)
                            
                except Exception as e:
                    print(f"❌ Error in continuation: {e}")
                    import traceback
                    traceback.print_exc()
                    # Fallback to regular query with session context
                    session_memory = get_session_memory(session_id)
                    conversation_context = session_memory.get_context() if session_memory else None
                    response, results, has_more, total_count = rag.query_rag_with_images(
                        original_query, num_results=15, use_hybrid=True, use_rerank=True, 
                        offset=offset, conversation_context=conversation_context
                    )
                    images = extract_product_card_data(results)
                    # Update session memory
                    if session_memory:
                        session_memory.add_message("user", query)
                        session_memory.add_message("assistant", response)
            else:
                response = "I'm sorry, continuation is not available."
                images = []
        else:
            # New query - process normally
            if use_agent and agent:
                response = agent.process_query(query)
                images = []
                has_more = False
                total_count = 0
            else:
                # Check for cart queries FIRST - these should trigger the cart UI
                query_lower = query.lower()
                cart_keywords = ['my cart', 'show cart', 'view cart', 'open cart', 'see cart', 
                                'what is in my cart', "what's in my cart", 'cart items', 'shopping cart']
                is_cart_query = any(kw in query_lower for kw in cart_keywords)
                
                if is_cart_query:
                    # Get cart from session and show products
                    cart = session.get('cart', [])
                    
                    if cart and len(cart) > 0:
                        # Format cart items for display
                        response = f"🛒 **Your Cart** ({len(cart)} item{'s' if len(cart) > 1 else ''}):\n\n"
                        total = 0
                        cart_images = []
                        
                        for i, item in enumerate(cart, 1):
                            name = item.get('product_name', 'Product')
                            price_str = item.get('price', '')
                            # Extract numeric price
                            try:
                                price = float(item.get('discounted_price') or item.get('base_price') or 0)
                                total += price
                            except:
                                price = 0
                            
                            response += f"{i}. **{name}**\n"
                            response += f"   Price: {price_str}\n"
                            if item.get('size'):
                                response += f"   Size: {item.get('size')}\n"
                            if item.get('color'):
                                response += f"   Color: {item.get('color')}\n"
                            response += "\n"
                            
                            # Add to images for product cards
                            cart_images.append(item)
                        
                        response += f"**Total: ₹{total:.2f}**\n\n"
                        response += "Click the 🛒 Cart button to checkout or modify your cart."
                        
                        emit('bot_response', {
                            'message': response,
                            'query': query,
                            'images': cart_images,
                            'action': 'open_cart'
                        })
                    else:
                        response = "Your cart is empty! Browse our products and add something you like. 🛍️"
                        emit('bot_response', {
                            'message': response,
                            'query': query,
                            'images': []
                        })
                    return
                
                # Check for personal/order history queries
                order_history_keywords = ['my order', 'order history', 'what did i order', 'what i ordered', 
                                         'last order', 'previous order', 'my purchase', 'purchase history',
                                         'what did i buy', 'what i bought']
                is_order_history_query = any(kw in query_lower for kw in order_history_keywords)
                
                if is_order_history_query:
                    # Check if user is logged in
                    verified_email = session.get('verified_email')
                    if verified_email and user_manager:
                        # Get user's order history (both purchases and prebooks)
                        user_data = user_manager.get_user(verified_email)
                        purchases = user_data.get('purchases', []) if user_data else []
                        prebooks = user_data.get('prebooks', []) if user_data else []
                        
                        # Parse if JSON strings
                        if isinstance(purchases, str):
                            try:
                                purchases = json.loads(purchases)
                            except:
                                purchases = []
                        if isinstance(prebooks, str):
                            try:
                                prebooks = json.loads(prebooks)
                            except:
                                prebooks = []
                        
                        if purchases or prebooks:
                            # Combine and build response
                            total_orders = len(purchases) + len(prebooks)
                            response = f"📦 **Your Order History** ({total_orders} total):\n\n"
                            if purchases:
                                response += f"🛒 {len(purchases)} purchase(s)"
                            if prebooks:
                                response += f"{' • ' if purchases else ''}📝 {len(prebooks)} prebook(s)"
                            response += "\n\nHere are your recent orders:"
                            
                            # Build product cards from both purchases and prebooks
                            order_images = []
                            
                            # Add purchases (last 5)
                            for purchase in purchases[-5:]:
                                product_data = purchase.get('product', {})
                                if isinstance(product_data, str):
                                    try:
                                        product_data = json.loads(product_data)
                                    except:
                                        product_data = {}
                                
                                card_data = {
                                    'product_name': product_data.get('product_name', '') or purchase.get('product_name', 'Product'),
                                    'url': product_data.get('url', '') or purchase.get('image_url', ''),
                                    'price': product_data.get('price', f"₹{purchase.get('amount', '')}"),
                                    'base_price': product_data.get('base_price', ''),
                                    'discounted_price': product_data.get('discounted_price', ''),
                                    'discount_percent': product_data.get('discount_percent', ''),
                                    'size': product_data.get('size', ''),
                                    'color': product_data.get('color', ''),
                                    'material': product_data.get('material', ''),
                                    'category': product_data.get('category', 'Purchased'),
                                    'subcategory': product_data.get('subcategory', ''),
                                    'store_name': product_data.get('store_name', ''),
                                    'store_location': product_data.get('store_location', ''),
                                    'is_purchase_history': True,
                                    'order_type': 'purchase',  # Tag as purchase
                                    'order_date': purchase.get('date', ''),
                                    'shipping_address': purchase.get('address', ''),
                                    'payment_method': purchase.get('payment_method', ''),
                                    'purchase_type': purchase.get('purchase_type', '')
                                }
                                order_images.append(card_data)
                            
                            # Add prebooks (last 5)
                            for prebook in prebooks[-5:]:
                                product_data = prebook.get('product', {})
                                if isinstance(product_data, str):
                                    try:
                                        product_data = json.loads(product_data)
                                    except:
                                        product_data = {}
                                
                                card_data = {
                                    'product_name': product_data.get('product_name', '') or prebook.get('product_name', 'Product'),
                                    'url': product_data.get('url', '') or prebook.get('image_url', ''),
                                    'price': prebook.get('price', product_data.get('price', '')),
                                    'base_price': product_data.get('base_price', ''),
                                    'discounted_price': product_data.get('discounted_price', ''),
                                    'discount_percent': product_data.get('discount_percent', ''),
                                    'size': product_data.get('size', ''),
                                    'color': product_data.get('color', ''),
                                    'material': product_data.get('material', ''),
                                    'category': product_data.get('category', 'Prebooked'),
                                    'subcategory': product_data.get('subcategory', ''),
                                    'store_name': prebook.get('store_name', ''),
                                    'store_location': prebook.get('store_location', ''),
                                    'is_purchase_history': True,
                                    'order_type': 'prebook',  # Tag as prebook
                                    'order_date': prebook.get('date', ''),
                                    'pickup_location': prebook.get('pickup_location', prebook.get('store_location', '')),
                                    'booking_type': prebook.get('booking_type', 'store_pickup')
                                }
                                order_images.append(card_data)
                            
                            emit('bot_response', {
                                'message': response,
                                'query': query,
                                'images': order_images
                            })
                            return
                        else:
                            response = "You haven't made any purchases or prebooks yet. Browse our collection and find something you love! 🛍️"
                            emit('bot_response', {'message': response, 'query': query, 'images': []})
                            return
                    else:
                        # Not logged in - prompt to log in
                        response = "To view your order history, please log in first by clicking the 👤 User button at the top. Once logged in, I can show you all your past orders and prebooks!"
                        emit('bot_response', {'message': response, 'query': query, 'images': []})
                        return
                
                # Use query_rag_with_images to get both response and image data
                if hasattr(rag, 'query_rag_with_images'):
                    # Get session-specific conversation context (prevents cross-user data leakage)
                    session_memory = get_session_memory(session_id)
                    conversation_context = session_memory.get_context() if session_memory else None
                    
                    # Get user's gender preference from session for personalized results
                    user_gender = session.get('user_gender', None)
                    
                    # Use local image paths from metadata (no enhancement)
                    response, results, has_more, total_count = rag.query_rag_with_images(
                        query, num_results=10, use_hybrid=True, use_rerank=True, 
                        enhance_images=False, offset=0, conversation_context=conversation_context,
                        user_gender=user_gender
                    )
                    images = extract_product_card_data(results)
                    
                    # Update session memory with this exchange (prevents cross-user context leakage)
                    if session_memory:
                        session_memory.add_message("user", query)
                        session_memory.add_message("assistant", response)
                    
                    # Store query context for continuation if there are more results
                    if has_more:
                        # Get query details for continuation
                        clu_result = rag.call_clu(query)
                        prediction = clu_result.get("result", {}).get("prediction", {})
                        enriched_query, where, required_category, required_subcategory, max_price, min_price, requires_discount, required_product_types = rag._build_search_from_clu(prediction, query)
                        
                        # Extract color from query for continuation filtering
                        query_lower = query.lower()
                        colors = ['red', 'blue', 'green', 'yellow', 'orange', 'purple', 'pink', 'black', 'white', 
                                  'grey', 'gray', 'brown', 'navy', 'beige', 'maroon', 'olive', 'cream', 'gold', 'silver']
                        required_color = None
                        for c in colors:
                            if c in query_lower:
                                required_color = c
                                break
                        
                        pending_queries[session_id] = {
                            'query': query,
                            'offset': 0,
                            'total': total_count,
                            'enriched_query': enriched_query,
                            'where': where,
                            'required_category': required_category,
                            'required_subcategory': required_subcategory,
                            'max_price': max_price,
                            'min_price': min_price,
                            'requires_discount': requires_discount,
                            'required_product_types': required_product_types,
                            'required_color': required_color
                        }
                else:
                    response = rag.query_rag(query, num_results=5, use_hybrid=True, use_rerank=True)
                    images = []
                    has_more = False
                    total_count = 0
        
        # Check if LLM response indicates no results
        # IMPORTANT: Trust Gemini's semantic understanding - it knows if products match the query
        response_lower = response.lower()
        no_results_indicators = [
            "don't currently have",
            "don't have",
            "no matching",
            "no items found",
            "couldn't find",
            "unable to find",
            "not available",
            "sorry, it looks like"
        ]
        has_no_results = any(indicator in response_lower for indicator in no_results_indicators)
        
        # Smart fallback logic:
        # Only override Gemini if products ACTUALLY match what user asked for
        # Gemini is smart - if it says "no formal wear" but we have T-shirts, it's CORRECT
        if has_no_results and images:
            query_lower = query.lower()
            
            # Check if products actually match the query (at least one product name contains query keywords)
            query_keywords = [w for w in query_lower.split() if len(w) > 2 and w not in 
                            ['show', 'find', 'get', 'for', 'the', 'and', 'with', 'men', 'women', 'kids', 'me', 'some', 'any']]
            
            # products_match_query = False
            # for img in images[:3]:  # Check first 3 products
            #     product_name = (img.get('product_name') or '').lower()
            #     # Check if any query keyword appears in product name
            #     if any(kw in product_name for kw in query_keywords):
            #         products_match_query = True
            #         break
            
            # if products_match_query:
            #     # Products match query - Gemini might be wrong, use fallback
            #     print(f"⚠️ LLM said no results but products match query keywords - using fallback response")
            #     response = f"Here are some products that match your search. You can see the details below."
            #     if has_more:
            #         remaining = total_count - len(images)
            #         response += f"\n\nWould you like to see more? There are {remaining} more items available."
            # else:
                # Products don't match query - Gemini is CORRECT
                # e.g., user asked "formal wear" but we found "T-shirts" - Gemini is right to say no formal wear
            print(f"ℹ️ LLM said no results and products don't match query '{query}' - hiding mismatched products")
                # Don't show mismatched products - just keep Gemini's "not found" response
            images = []  # Clear images - don't show irrelevant products
        
        # Send response
        print(f"📤 Full response length: {len(response)} chars")  # Debug log
        print(f"📤 FULL RESPONSE:\n{response}")  # Show complete response
        print(f"📤 --- END RESPONSE ---")
        print(f"📤 Images count: {len(images) if images else 0}")  # Debug log
        print(f"📤 Session ID: {session_id}")  # Debug log
        print(f"📤 Socket ID: {request.sid}")  # Debug log
        
        try:
            emit('bot_response', {
                'message': response,
                'query': query,
                'used_agent': use_agent,
                'images': images
            }, room=request.sid)  # Explicitly send to this session
            print(f"✅ Response emitted successfully to room {request.sid}")  # Debug log
        except Exception as emit_error:
            print(f"❌ Error emitting response: {emit_error}")  # Debug log
            raise
        
    except Exception as e:
        import traceback
        print(f"❌ Full error traceback:")
        traceback.print_exc()
        # Use friendly fallback response instead of error
        fallback_response = "I apologize, but I'm having trouble processing your request right now. Could you please try rephrasing your question or ask something else? I'm here to help you find products at Shop Assist!"
        emit('bot_response', {
            'message': fallback_response,
            'query': query if 'query' in dir() else '',
            'images': []
        })

@socketio.on('suggestion_click')
def handle_suggestion(data):
    try:
        if not rag:
            emit('bot_response', {'error': 'RAG system not initialized'})
            return
        
        suggestion = data.get('suggestion', '')
        if not suggestion:
            return
        
        # Send typing indicator
        emit('bot_typing', {'typing': True})
        
        # Process suggestion through RAG with session-specific context
        session_id = request.sid
        session_memory = get_session_memory(session_id)
        conversation_context = session_memory.get_context() if session_memory else None
        
        if hasattr(rag, 'query_rag_with_images'):
            response, results, _, _ = rag.query_rag_with_images(
                suggestion, num_results=5, use_hybrid=True, use_rerank=True, 
                conversation_context=conversation_context
            )
            images = extract_product_card_data(results)
        else:
            response = rag.query_rag(suggestion, num_results=5, use_hybrid=True, use_rerank=True, 
                                   conversation_context=conversation_context)
            images = []
        
        # Update session memory
        if session_memory:
            session_memory.add_message("user", suggestion)
            session_memory.add_message("assistant", response)
        
        # Send response
        emit('bot_response', {
            'message': response,
            'query': suggestion,
            'images': images
        })
        
    except Exception as e:
        import traceback
        print(f"❌ Suggestion error: {e}")
        traceback.print_exc()
        # Use friendly fallback response
        fallback_response = "I'm sorry, I couldn't process that suggestion. Please try asking in a different way!"
        emit('bot_response', {
            'message': fallback_response,
            'query': suggestion if 'suggestion' in dir() else '',
            'images': []
        })

@socketio.on('feedback')
def handle_feedback(data):
    """Handle user feedback for learning."""
    try:
        if not feedback_system:
            return
        
        query = data.get('query', '')
        response = data.get('response', '')
        user_feedback = data.get('feedback', '')
        helpful = data.get('helpful', True)
        rating = data.get('rating')
        
        feedback_system.record_feedback(query, response, user_feedback, helpful, rating)
        emit('feedback_received', {'status': 'success'})
    except Exception as e:
        emit('feedback_received', {'status': 'error', 'error': str(e)})

@app.route('/api/analytics')
def api_analytics():
    """Get analytics data."""
    try:
        if not rag:
            return jsonify({'error': 'RAG system not initialized'}), 500
        return jsonify(rag.get_analytics())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/prebook', methods=['POST'])
def api_prebook():
    """Handle product prebook request (store pickup - no shipping address needed)"""
    try:
        if not user_manager:
            return jsonify({'success': False, 'error': 'User manager not initialized'}), 500
            
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        name = data.get('name', '').strip()
        phone = data.get('phone', '').strip()
        product = data.get('product', {})
        store_location = data.get('store_location', '')
        store_name = data.get('store_name', '')
        pickup_location = data.get('pickup_location', store_location)  # Store pickup location
        quantity = int(data.get('quantity', 1))
        
        if not email or not name or not phone:
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        # Check stock availability before proceeding
        product_id = product.get('product_url') or product.get('product_id', '')
        if stock_manager and product_id:
            if not stock_manager.is_product_available(product_id, quantity):
                current_stock = stock_manager.get_stock_quantity(product_id)
                return jsonify({
                    'success': False, 
                    'error': f'Sorry, this product is out of stock or has insufficient quantity. Available: {current_stock}',
                    'out_of_stock': True,
                    'available_quantity': current_stock
                }), 400
        
        # Create or update user (no shipping address for prebook - customer picks up from store)
        user_manager.create_or_update_user(
            email=email,
            name=name,
            phone=phone
        )
        
        # Add prebook record with full product data for display
        prebook_data = {
            'product_name': product.get('product_name', ''),
            'product_id': product.get('product_url', ''),
            'price': product.get('discounted_price') or product.get('base_price', ''),
            'date': datetime.now().isoformat(),  # Store prebook date
            'image_url': product.get('url', ''),  # Store image URL directly for easy access
            'color': product.get('color', ''),
            'size': product.get('size', ''),
            'store_location': store_location,
            'store_name': store_name,
            'pickup_location': pickup_location,  # Where customer will pick up
            'booking_type': 'store_pickup',
            'quantity': quantity,
            # Store complete product data for card display
            'product': product  # Store the entire product object as-is
        }
        
        success = user_manager.add_prebook(email, prebook_data)
        
        if success:
            # Deduct stock from ChromaDB
            if stock_manager and product_id:
                stock_result = stock_manager.deduct_stock(product_id, quantity)
                if not stock_result.get('success'):
                    print(f"⚠️ Stock deduction warning: {stock_result.get('error')}")
            
            return jsonify({'success': True, 'message': 'Product prebooked successfully'})
        else:
            return jsonify({'success': False, 'error': 'Failed to prebook product'}), 500
            
    except Exception as e:
        print(f"❌ Prebook error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/purchase', methods=['POST'])
def api_purchase():
    """Handle product purchase request"""
    try:
        if not user_manager:
            return jsonify({'success': False, 'error': 'User manager not initialized'}), 500
            
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        name = data.get('name', '').strip()
        phone = data.get('phone', '').strip()
        address = data.get('address', '').strip()
        product = data.get('product', {})
        payment_method = data.get('payment_method', '')
        amount = data.get('amount', '0')
        quantity = int(data.get('quantity', 1))
        
        if not email or not name or not phone or not address:
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        # Check stock availability before proceeding
        product_id = product.get('product_url') or product.get('product_id', '')
        if stock_manager and product_id:
            if not stock_manager.is_product_available(product_id, quantity):
                current_stock = stock_manager.get_stock_quantity(product_id)
                return jsonify({
                    'success': False, 
                    'error': f'Sorry, this product is out of stock or has insufficient quantity. Available: {current_stock}',
                    'out_of_stock': True,
                    'available_quantity': current_stock
                }), 400
        
        # Create or update user
        user_manager.create_or_update_user(
            email=email,
            name=name,
            phone=phone,
            address={'shipping': address}
        )
        
        # Add purchase record with full product data for display
        # Store all product fields explicitly for easy access in purchase history
        purchase_data = {
            'product_name': product.get('product_name', ''),
            'product_id': product.get('product_url', ''),
            'date': datetime.now().isoformat(),  # Store purchase date
            'price': amount,  # Store as price for display
            'amount': amount,
            'payment_method': payment_method,
            'purchase_type': 'online',
            'address': address,
            'quantity': quantity,
            # Store image and other important product details
            'image_url': product.get('url', ''),
            'color': product.get('color', ''),
            'size': product.get('size', ''),
            'base_price': product.get('base_price', ''),
            'discounted_price': product.get('discounted_price', ''),
            'discount': product.get('discount', ''),
            # Store complete product data for card display (same format as search results)
            'product': product  # Store the entire product object as-is
        }
        
        success = user_manager.add_purchase(email, purchase_data)
        
        if success:
            # Deduct stock from ChromaDB
            if stock_manager and product_id:
                stock_result = stock_manager.deduct_stock(product_id, quantity)
                if not stock_result.get('success'):
                    print(f"⚠️ Stock deduction warning: {stock_result.get('error')}")
            
            return jsonify({'success': True, 'message': 'Order placed successfully'})
        else:
            return jsonify({'success': False, 'error': 'Failed to place order'}), 500
            
    except Exception as e:
        print(f"❌ Purchase error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/cart', methods=['GET', 'POST', 'DELETE'])
def api_cart():
    """Handle cart operations"""
    try:
        if request.method == 'GET':
            # Get cart from session
            cart = session.get('cart', [])
            return jsonify({'success': True, 'cart': cart})
        
        elif request.method == 'POST':
            # Add to cart (session-based)
            data = request.get_json()
            product = data.get('product', {})
            
            if 'cart' not in session:
                session['cart'] = []
            
            session['cart'].append(product)
            session.modified = True
            
            return jsonify({'success': True, 'message': 'Product added to cart', 'cart': session['cart']})
        
        elif request.method == 'DELETE':
            # Clear cart
            session['cart'] = []
            session.modified = True
            return jsonify({'success': True, 'message': 'Cart cleared'})
            
    except Exception as e:
        print(f"❌ Cart error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/validate-cart', methods=['POST'])
def api_validate_cart():
    """Validate cart items against current stock availability"""
    try:
        if not stock_manager:
            return jsonify({'success': False, 'error': 'Stock manager not initialized'}), 500
        
        data = request.get_json()
        cart_items = data.get('cart', [])
        
        # If no cart provided, use session cart
        if not cart_items:
            cart_items = session.get('cart', [])
        
        if not cart_items:
            return jsonify({
                'success': True,
                'all_available': True,
                'available_items': [],
                'out_of_stock_items': [],
                'limited_stock_items': [],
                'message': 'Cart is empty'
            })
        
        # Validate cart against stock
        validation_result = stock_manager.check_cart_availability(cart_items)
        
        # Add notification message
        if validation_result['out_of_stock_items']:
            out_of_stock_names = [item.get('product_name', 'Unknown') for item in validation_result['out_of_stock_items']]
            validation_result['message'] = f"Some items are out of stock: {', '.join(out_of_stock_names)}. Please move them to wishlist or remove from cart."
            validation_result['notification_type'] = 'out_of_stock'
        elif validation_result['limited_stock_items']:
            validation_result['message'] = 'Some items have limited stock. Please complete your purchase soon!'
            validation_result['notification_type'] = 'limited_stock'
        else:
            validation_result['message'] = 'All items are available!'
            validation_result['notification_type'] = 'success'
        
        validation_result['success'] = True
        return jsonify(validation_result)
        
    except Exception as e:
        print(f"❌ Cart validation error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/wishlist', methods=['GET', 'POST', 'DELETE'])
def api_wishlist():
    """Handle wishlist operations"""
    try:
        if not user_manager:
            return jsonify({'success': False, 'error': 'User manager not initialized'}), 500
        
        # Get user email from session
        email = session.get('verified_email')
        if not email:
            return jsonify({'success': False, 'error': 'Please login to access wishlist'}), 401
        
        if request.method == 'GET':
            # Get user's wishlist
            wishlist = user_manager.get_wishlist(email)
            return jsonify({'success': True, 'wishlist': wishlist})
        
        elif request.method == 'POST':
            # Add product to wishlist
            data = request.get_json()
            product = data.get('product', {})
            
            if not product:
                return jsonify({'success': False, 'error': 'No product provided'}), 400
            
            success = user_manager.add_to_wishlist(email, product)
            
            if success:
                wishlist = user_manager.get_wishlist(email)
                return jsonify({
                    'success': True, 
                    'message': 'Product added to wishlist',
                    'wishlist': wishlist
                })
            else:
                return jsonify({'success': False, 'error': 'Failed to add to wishlist'}), 500
        
        elif request.method == 'DELETE':
            # Remove product from wishlist
            data = request.get_json()
            product_identifier = data.get('product_id') or data.get('product_url', '')
            
            if not product_identifier:
                return jsonify({'success': False, 'error': 'No product identifier provided'}), 400
            
            success = user_manager.remove_from_wishlist(email, product_identifier)
            
            if success:
                wishlist = user_manager.get_wishlist(email)
                return jsonify({
                    'success': True, 
                    'message': 'Product removed from wishlist',
                    'wishlist': wishlist
                })
            else:
                return jsonify({'success': False, 'error': 'Failed to remove from wishlist'}), 500
            
    except Exception as e:
        print(f"❌ Wishlist error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/move-to-wishlist', methods=['POST'])
def api_move_to_wishlist():
    """Move an out-of-stock item from cart to wishlist"""
    try:
        if not user_manager:
            return jsonify({'success': False, 'error': 'User manager not initialized'}), 500
        
        # Get user email from session
        email = session.get('verified_email')
        if not email:
            return jsonify({'success': False, 'error': 'Please login to use wishlist'}), 401
        
        data = request.get_json()
        product = data.get('product', {})
        remove_from_cart = data.get('remove_from_cart', True)
        
        if not product:
            return jsonify({'success': False, 'error': 'No product provided'}), 400
        
        # Add to wishlist
        success = user_manager.add_to_wishlist(email, product)
        
        if success and remove_from_cart:
            # Remove from cart
            cart = session.get('cart', [])
            product_identifier = product.get('product_url') or product.get('product_name', '')
            
            new_cart = []
            for item in cart:
                item_identifier = item.get('product_url') or item.get('product_name', '')
                if item_identifier != product_identifier:
                    new_cart.append(item)
            
            session['cart'] = new_cart
            session.modified = True
        
        if success:
            wishlist = user_manager.get_wishlist(email)
            return jsonify({
                'success': True,
                'message': 'Product moved to wishlist',
                'wishlist': wishlist,
                'cart': session.get('cart', [])
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to move to wishlist'}), 500
            
    except Exception as e:
        print(f"❌ Move to wishlist error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/check-stock', methods=['POST'])
def api_check_stock():
    """Check stock availability for a specific product"""
    try:
        if not stock_manager:
            return jsonify({'success': False, 'error': 'Stock manager not initialized'}), 500
        
        data = request.get_json()
        product_id = data.get('product_id') or data.get('product_url', '')
        quantity = int(data.get('quantity', 1))
        
        if not product_id:
            return jsonify({'success': False, 'error': 'No product ID provided'}), 400
        
        stock_quantity = stock_manager.get_stock_quantity(product_id)
        availability = stock_manager.get_availability(product_id)
        is_available = stock_manager.is_product_available(product_id, quantity)
        
        return jsonify({
            'success': True,
            'product_id': product_id,
            'stock_quantity': stock_quantity,
            'availability': availability,
            'is_available': is_available,
            'requested_quantity': quantity
        })
        
    except Exception as e:
        print(f"❌ Stock check error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/login', methods=['POST'])
def api_login():
    """Login/Register user with email, phone, and gender"""
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        name = data.get('name', '').strip()
        phone = data.get('phone', '').strip()
        gender = data.get('gender', '').strip().lower()
        
        # Validate email
        import re
        email_regex = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
        if not email or not re.match(email_regex, email):
            return jsonify({'success': False, 'error': 'Invalid email address'}), 400
        
        # Validate phone (10 digits, starting with 6-9 for Indian numbers)
        phone_regex = r'^[6-9]\d{9}$'
        if not phone or not re.match(phone_regex, phone):
            return jsonify({'success': False, 'error': 'Invalid phone number. Must be 10 digits starting with 6-9'}), 400
        
        if not name:
            return jsonify({'success': False, 'error': 'Name is required'}), 400
        
        # Validate gender
        valid_genders = ['male', 'female', 'kid']
        if not gender or gender not in valid_genders:
            return jsonify({'success': False, 'error': 'Please select who you\'re shopping for (Men/Women/Kids)'}), 400
        
        if not user_manager:
            return jsonify({'success': False, 'error': 'User manager not initialized'}), 500
        
        # Create or update user with gender
        user = user_manager.create_or_update_user(email, name, phone, gender=gender)
        
        # Store in session
        session['verified_email'] = email
        session['verified_phone'] = phone
        session['user_name'] = name
        session['user_gender'] = gender
        session['verified_timestamp'] = datetime.now().isoformat()
        session.permanent = True
        session.modified = True
        
        print(f"✅ User logged in: {name} ({email}, +91{phone}, {gender})")
        
        return jsonify({
            'success': True, 
            'message': 'Login successful',
            'user': {
                'email': email,
                'phone': phone,
                'name': name,
                'gender': gender
            }
        })
        
    except Exception as e:
        print(f"❌ Login error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/verify', methods=['POST'])
def api_verify():
    """Store verification status in session"""
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        verified = data.get('verified', False)
        
        if email and verified:
            session['verified_email'] = email
            session['verified_timestamp'] = datetime.now().isoformat()
            session.permanent = True  # Make session persistent
            session.modified = True
            return jsonify({'success': True, 'message': 'Verification stored in session'})
        else:
            return jsonify({'success': False, 'error': 'Invalid verification data'}), 400
            
    except Exception as e:
        print(f"❌ Verification error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/purchase-history', methods=['GET'])
def api_purchase_history():
    """Get purchase history and prebooks for verified user"""
    try:
        email = request.args.get('email', '').strip().lower()
        
        # Check if user is verified in session
        verified_email = session.get('verified_email')
        if not verified_email or verified_email != email:
            return jsonify({'success': False, 'error': 'User not verified'}), 401
        
        if not user_manager:
            return jsonify({'success': False, 'error': 'User manager not initialized'}), 500
        
        # Get user data
        user = user_manager.get_user(email)
        if not user:
            return jsonify({'success': True, 'purchases': [], 'prebooks': []})
        
        purchases = user.get('purchases', [])
        if isinstance(purchases, str):
            purchases = json.loads(purchases)
        
        prebooks = user.get('prebooks', [])
        if isinstance(prebooks, str):
            prebooks = json.loads(prebooks)
        
        # Add order_type to each item
        for p in purchases:
            p['order_type'] = 'purchase'
        for p in prebooks:
            p['order_type'] = 'prebook'
        
        return jsonify({'success': True, 'purchases': purchases, 'prebooks': prebooks})
        
    except Exception as e:
        print(f"❌ Purchase history error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    try:
        print("🚀 Starting Shop Assist RAG Custom Web App...")
        port = int(os.environ.get("PORT", 5000))
        # Azure App Service uses PORT environment variable
        # Disable debug mode in production (Azure sets WEBSITE_SITE_NAME)
        debug_mode = os.environ.get("is_project") is None
        # Disable reloader to avoid WebSocket handshake issues with Werkzeug
        # The reloader can cause "write() before start_response" errors
        use_reloader = False
        # Allow Werkzeug in production (for Azure App Service and similar deployments)
        socketio.run(
            app, 
            host="0.0.0.0", 
            port=port, 
            debug=debug_mode, 
            use_reloader=use_reloader,
            allow_unsafe_werkzeug=True
        )
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
