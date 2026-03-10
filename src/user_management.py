"""
User Management System for Shop Assist E-commerce
Stores user records, purchase history, and prebooked items in ChromaDB
"""

import os
import json
import hashlib
import logging
from datetime import datetime
from typing import Dict, List, Optional
from chromadb import PersistentClient
from chromadb.config import Settings
from config import Config

# Suppress ChromaDB telemetry errors
logging.getLogger("chromadb.telemetry").setLevel(logging.CRITICAL)
logging.getLogger("chromadb").setLevel(logging.WARNING)

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

config = Config()
CHROMA_DB_PATH = config.get("CHROMA_DB_PATH", "chroma_db")
USER_COLLECTION_NAME = "shop_assist_users"

class UserManager:
    """Manages user records, purchases, and prebooks in ChromaDB"""
    
    def __init__(self):
        self.client = PersistentClient(path=CHROMA_DB_PATH, settings=Settings(anonymized_telemetry=False))
        
        # Get or create user collection
        try:
            self.collection = self.client.get_collection(USER_COLLECTION_NAME)
        except:
            self.collection = self.client.create_collection(USER_COLLECTION_NAME)
    
    def _generate_user_id(self, email: str) -> str:
        """Generate unique user ID from email"""
        return hashlib.md5(email.lower().encode()).hexdigest()
    
    def create_or_update_user(self, email: str, name: str, phone: str, address: Dict = None, gender: str = None) -> Dict:
        """Create or update user record"""
        user_id = self._generate_user_id(email)
        
        # Check if user exists
        existing = self.collection.get(ids=[user_id])
        
        # Convert address dict to string for ChromaDB compatibility
        address_str = ""
        if address:
            if isinstance(address, dict):
                address_str = json.dumps(address)
            else:
                address_str = str(address)
        
        # Normalize gender
        gender = (gender or "").lower().strip()
        if gender not in ['male', 'female', 'kid']:
            gender = ""
        
        user_data = {
            "email": email.lower(),
            "name": name,
            "phone": phone,
            "gender": gender,  # Store gender for personalized recommendations
            "address": address_str,  # Store as JSON string
            "created_at": datetime.now().isoformat(),
            "purchases": json.dumps([]),  # Store as JSON string
            "prebooks": json.dumps([]),  # Store as JSON string
            "cart": json.dumps([])  # Store as JSON string
        }
        
        if existing.get("ids"):
            # Update existing user
            existing_meta = existing["metadatas"][0]
            user_data["created_at"] = existing_meta.get("created_at", user_data["created_at"])
            
            # Parse existing JSON strings
            try:
                user_data["purchases"] = existing_meta.get("purchases", "[]")
                if isinstance(user_data["purchases"], str):
                    purchases_list = json.loads(user_data["purchases"])
                else:
                    purchases_list = user_data["purchases"]
            except:
                purchases_list = []
            
            try:
                user_data["prebooks"] = existing_meta.get("prebooks", "[]")
                if isinstance(user_data["prebooks"], str):
                    prebooks_list = json.loads(user_data["prebooks"])
                else:
                    prebooks_list = user_data["prebooks"]
            except:
                prebooks_list = []
            
            try:
                user_data["cart"] = existing_meta.get("cart", "[]")
                if isinstance(user_data["cart"], str):
                    cart_list = json.loads(user_data["cart"])
                else:
                    cart_list = user_data["cart"]
            except:
                cart_list = []
            
            # Update address if provided
            if address_str:
                user_data["address"] = address_str
            
            # Update gender if provided, otherwise keep existing
            if gender:
                user_data["gender"] = gender
            else:
                user_data["gender"] = existing_meta.get("gender", "")
            
            # Convert back to JSON strings for storage
            user_data["purchases"] = json.dumps(purchases_list)
            user_data["prebooks"] = json.dumps(prebooks_list)
            user_data["cart"] = json.dumps(cart_list)
        
        # Store user
        self.collection.upsert(
            ids=[user_id],
            documents=[f"User: {name} ({email})"],
            metadatas=[user_data]
        )
        
        # Return with parsed data
        return_data = user_data.copy()
        return_data["purchases"] = json.loads(user_data["purchases"])
        return_data["prebooks"] = json.loads(user_data["prebooks"])
        return_data["cart"] = json.loads(user_data["cart"])
        if user_data["address"]:
            try:
                return_data["address"] = json.loads(user_data["address"])
            except:
                return_data["address"] = user_data["address"]
        
        return {"user_id": user_id, **return_data}
    
    def get_user(self, email: str) -> Optional[Dict]:
        """Get user by email"""
        user_id = self._generate_user_id(email)
        result = self.collection.get(ids=[user_id])
        
        if result.get("ids"):
            user_data = result["metadatas"][0].copy()
            # Parse JSON strings back to lists/dicts
            try:
                if isinstance(user_data.get("purchases"), str):
                    user_data["purchases"] = json.loads(user_data["purchases"])
            except:
                user_data["purchases"] = []
            
            try:
                if isinstance(user_data.get("prebooks"), str):
                    user_data["prebooks"] = json.loads(user_data["prebooks"])
            except:
                user_data["prebooks"] = []
            
            try:
                if isinstance(user_data.get("cart"), str):
                    user_data["cart"] = json.loads(user_data["cart"])
            except:
                user_data["cart"] = []
            
            try:
                if isinstance(user_data.get("wishlist"), str):
                    user_data["wishlist"] = json.loads(user_data["wishlist"])
            except:
                user_data["wishlist"] = []
            
            try:
                if isinstance(user_data.get("address"), str) and user_data.get("address"):
                    user_data["address"] = json.loads(user_data["address"])
            except:
                pass
            
            return {"user_id": user_id, **user_data}
        return None
    
    def get_user_by_phone(self, phone: str) -> Optional[Dict]:
        """Get user by phone number"""
        # Clean phone number (remove spaces, dashes, country code)
        phone = phone.strip().replace(" ", "").replace("-", "")
        if phone.startswith("+91"):
            phone = phone[3:]
        elif phone.startswith("91") and len(phone) > 10:
            phone = phone[2:]
        
        # Search all users for matching phone
        try:
            all_users = self.collection.get()
            if all_users.get("metadatas"):
                for i, metadata in enumerate(all_users["metadatas"]):
                    user_phone = metadata.get("phone", "").strip()
                    if user_phone == phone:
                        # Found matching user, return full user data
                        email = metadata.get("email", "")
                        return self.get_user(email)
        except Exception as e:
            print(f"Error searching user by phone: {e}")
        
        return None
    
    def get_user_by_email_or_phone(self, identifier: str) -> Optional[Dict]:
        """Get user by either email or phone number"""
        identifier = identifier.strip()
        
        # Check if it looks like an email
        if "@" in identifier:
            return self.get_user(identifier)
        
        # Otherwise try phone lookup
        return self.get_user_by_phone(identifier)
    
    def add_purchase(self, email: str, purchase_data: Dict) -> bool:
        """Add purchase record to user"""
        user = self.get_user(email)
        if not user:
            return False
        
        purchase_data["purchase_date"] = datetime.now().isoformat()
        purchase_data["purchase_id"] = hashlib.md5(
            f"{email}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]
        
        # Ensure all dict values in purchase_data are converted to strings
        sanitized_purchase = {}
        for key, value in purchase_data.items():
            if isinstance(value, dict):
                sanitized_purchase[key] = json.dumps(value)
            elif isinstance(value, list):
                sanitized_purchase[key] = json.dumps(value)
            else:
                sanitized_purchase[key] = value
        
        purchases = user.get("purchases", [])
        if not isinstance(purchases, list):
            purchases = []
        purchases.append(sanitized_purchase)
        
        user_id = self._generate_user_id(email)
        
        # Convert to JSON strings for ChromaDB - ensure all values are primitives
        user_address = user.get("address", {})
        if isinstance(user_address, dict):
            address_str = json.dumps(user_address)
        elif isinstance(user_address, str):
            address_str = user_address
        else:
            address_str = ""
        
        user_meta = {
            "email": str(user.get("email", "")),
            "name": str(user.get("name", "")),
            "phone": str(user.get("phone", "")),
            "address": address_str,
            "created_at": str(user.get("created_at", datetime.now().isoformat())),
            "purchases": json.dumps(purchases),
            "prebooks": json.dumps(user.get("prebooks", [])),
            "cart": json.dumps(user.get("cart", []))
        }
        
        self.collection.update(
            ids=[user_id],
            metadatas=[user_meta]
        )
        
        return True
    
    def add_prebook(self, email: str, prebook_data: Dict) -> bool:
        """Add prebook record to user"""
        user = self.get_user(email)
        if not user:
            return False
        
        prebook_data["prebook_date"] = datetime.now().isoformat()
        prebook_data["prebook_id"] = hashlib.md5(
            f"{email}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]
        prebook_data["status"] = "pending"
        
        # Ensure all dict values in prebook_data are converted to strings
        sanitized_prebook = {}
        for key, value in prebook_data.items():
            if isinstance(value, dict):
                sanitized_prebook[key] = json.dumps(value)
            elif isinstance(value, list):
                sanitized_prebook[key] = json.dumps(value)
            else:
                sanitized_prebook[key] = value
        
        prebooks = user.get("prebooks", [])
        if not isinstance(prebooks, list):
            prebooks = []
        prebooks.append(sanitized_prebook)
        
        user_id = self._generate_user_id(email)
        
        # Convert to JSON strings for ChromaDB - ensure all values are primitives
        user_address = user.get("address", {})
        if isinstance(user_address, dict):
            address_str = json.dumps(user_address)
        elif isinstance(user_address, str):
            address_str = user_address
        else:
            address_str = ""
        
        user_meta = {
            "email": str(user.get("email", "")),
            "name": str(user.get("name", "")),
            "phone": str(user.get("phone", "")),
            "address": address_str,
            "created_at": str(user.get("created_at", datetime.now().isoformat())),
            "purchases": json.dumps(user.get("purchases", [])),
            "prebooks": json.dumps(prebooks),
            "cart": json.dumps(user.get("cart", []))
        }
        
        self.collection.update(
            ids=[user_id],
            metadatas=[user_meta]
        )
        
        return True
    
    def update_cart(self, email: str, cart_items: List[Dict]) -> bool:
        """Update user cart"""
        user = self.get_user(email)
        if not user:
            return False
        
        user["cart"] = cart_items
        
        user_id = self._generate_user_id(email)
        self.collection.update(
            ids=[user_id],
            metadatas=[user]
        )
        
        return True
    
    def get_cart(self, email: str) -> List[Dict]:
        """Get user cart"""
        user = self.get_user(email)
        if user:
            return user.get("cart", [])
        return []
    
    def verify_email(self, email: str, verification_code: str) -> bool:
        """Verify email (simplified - in production, use proper email verification)"""
        # For demo: accept any 6-digit code
        # In production, store verification codes and validate
        return len(verification_code) == 6 and verification_code.isdigit()
    
    # ============== WISHLIST MANAGEMENT ==============
    
    def add_to_wishlist(self, email: str, product: Dict) -> bool:
        """Add product to user's wishlist"""
        user = self.get_user(email)
        if not user:
            return False
        
        # Get existing wishlist or create new
        wishlist = user.get("wishlist", [])
        if not isinstance(wishlist, list):
            wishlist = []
        
        # Check if product already in wishlist (by product_url or product_name)
        product_identifier = product.get('product_url') or product.get('product_name', '')
        for item in wishlist:
            item_identifier = item.get('product_url') or item.get('product_name', '')
            if item_identifier == product_identifier:
                return True  # Already in wishlist
        
        # Add timestamp
        product['added_to_wishlist'] = datetime.now().isoformat()
        wishlist.append(product)
        
        # Update user record
        user_id = self._generate_user_id(email)
        user_address = user.get("address", {})
        if isinstance(user_address, dict):
            address_str = json.dumps(user_address)
        elif isinstance(user_address, str):
            address_str = user_address
        else:
            address_str = ""
        
        user_meta = {
            "email": str(user.get("email", "")),
            "name": str(user.get("name", "")),
            "phone": str(user.get("phone", "")),
            "gender": str(user.get("gender", "")),
            "address": address_str,
            "created_at": str(user.get("created_at", datetime.now().isoformat())),
            "purchases": json.dumps(user.get("purchases", [])),
            "prebooks": json.dumps(user.get("prebooks", [])),
            "cart": json.dumps(user.get("cart", [])),
            "wishlist": json.dumps(wishlist)
        }
        
        self.collection.update(
            ids=[user_id],
            metadatas=[user_meta]
        )
        
        return True
    
    def remove_from_wishlist(self, email: str, product_identifier: str) -> bool:
        """Remove product from user's wishlist"""
        user = self.get_user(email)
        if not user:
            return False
        
        wishlist = user.get("wishlist", [])
        if not isinstance(wishlist, list):
            return False
        
        # Find and remove product
        new_wishlist = []
        for item in wishlist:
            item_id = item.get('product_url') or item.get('product_name', '')
            if item_id != product_identifier:
                new_wishlist.append(item)
        
        # Update user record
        user_id = self._generate_user_id(email)
        user_address = user.get("address", {})
        if isinstance(user_address, dict):
            address_str = json.dumps(user_address)
        elif isinstance(user_address, str):
            address_str = user_address
        else:
            address_str = ""
        
        user_meta = {
            "email": str(user.get("email", "")),
            "name": str(user.get("name", "")),
            "phone": str(user.get("phone", "")),
            "gender": str(user.get("gender", "")),
            "address": address_str,
            "created_at": str(user.get("created_at", datetime.now().isoformat())),
            "purchases": json.dumps(user.get("purchases", [])),
            "prebooks": json.dumps(user.get("prebooks", [])),
            "cart": json.dumps(user.get("cart", [])),
            "wishlist": json.dumps(new_wishlist)
        }
        
        self.collection.update(
            ids=[user_id],
            metadatas=[user_meta]
        )
        
        return True
    
    def get_wishlist(self, email: str) -> List[Dict]:
        """Get user's wishlist"""
        user = self.get_user(email)
        if user:
            wishlist = user.get("wishlist", [])
            if isinstance(wishlist, str):
                try:
                    wishlist = json.loads(wishlist)
                except:
                    wishlist = []
            return wishlist if isinstance(wishlist, list) else []
        return []


class StockManager:
    """Manages product stock in ChromaDB"""
    
    def __init__(self, collection_name: str = None):
        from config import Config
        config = Config()
        self.client = PersistentClient(path=CHROMA_DB_PATH, settings=Settings(anonymized_telemetry=False))
        self.collection_name = collection_name or config.get("COLLECTION_NAME", "shop_assist_retail_data_clu")
        
        try:
            self.collection = self.client.get_collection(self.collection_name)
        except:
            print(f"⚠️ Product collection '{self.collection_name}' not found")
            self.collection = None
    
    def get_product_by_id(self, product_id: str) -> Optional[Dict]:
        """Get product by its ChromaDB ID (product_url or chroma_id)"""
        if not self.collection:
            return None
        
        try:
            # Try direct ID lookup first
            result = self.collection.get(ids=[product_id])
            if result.get("ids"):
                return {
                    "id": result["ids"][0],
                    "metadata": result["metadatas"][0],
                    "document": result["documents"][0] if result.get("documents") else None
                }
            
            # If not found, search by product_url in metadata
            all_products = self.collection.get(include=['metadatas', 'documents'])
            for i, meta in enumerate(all_products.get('metadatas', [])):
                if meta.get('product_url') == product_id or meta.get('chroma_id') == product_id:
                    return {
                        "id": all_products["ids"][i],
                        "metadata": meta,
                        "document": all_products["documents"][i] if all_products.get("documents") else None
                    }
        except Exception as e:
            print(f"❌ Error getting product by ID: {e}")
        
        return None
    
    def get_stock_quantity(self, product_id: str) -> int:
        """Get current stock quantity for a product"""
        product = self.get_product_by_id(product_id)
        if not product:
            return 0
        
        meta = product.get("metadata", {})
        try:
            stock = int(meta.get("stock_quantity") or meta.get("Stock_Quantity") or 0)
            return max(0, stock)
        except (ValueError, TypeError):
            return 0
    
    def get_availability(self, product_id: str) -> str:
        """Get availability status for a product"""
        product = self.get_product_by_id(product_id)
        if not product:
            return "Out of Stock"
        
        meta = product.get("metadata", {})
        stock = self.get_stock_quantity(product_id)
        
        if stock <= 0:
            return "Out of Stock"
        elif stock <= 5:
            return "Limited Stock"
        else:
            return meta.get("availability") or meta.get("Availability") or "In Stock"
    
    def deduct_stock(self, product_id: str, quantity: int = 1) -> Dict:
        """
        Deduct stock from a product after purchase/prebook.
        Returns: {'success': bool, 'new_stock': int, 'availability': str, 'error': str}
        """
        if not self.collection:
            return {'success': False, 'error': 'Product collection not initialized'}
        
        product = self.get_product_by_id(product_id)
        if not product:
            return {'success': False, 'error': f'Product not found: {product_id}'}
        
        meta = product.get("metadata", {})
        current_stock = self.get_stock_quantity(product_id)
        
        if current_stock < quantity:
            return {
                'success': False, 
                'error': f'Insufficient stock. Available: {current_stock}, Requested: {quantity}',
                'current_stock': current_stock
            }
        
        # Calculate new stock
        new_stock = current_stock - quantity
        
        # Determine new availability status
        if new_stock <= 0:
            new_availability = "Out of Stock"
        elif new_stock <= 5:
            new_availability = "Limited Stock"
        else:
            new_availability = "In Stock"
        
        # Update metadata
        meta["stock_quantity"] = new_stock
        meta["Stock_Quantity"] = new_stock
        meta["availability"] = new_availability
        meta["Availability"] = new_availability
        meta["stock_status"] = new_availability
        meta["Stock_Status"] = new_availability
        meta["last_stock_update"] = datetime.now().isoformat()
        
        try:
            self.collection.update(
                ids=[product["id"]],
                metadatas=[meta]
            )
            print(f"📦 Stock updated for {product_id}: {current_stock} -> {new_stock} ({new_availability})")
            return {
                'success': True,
                'previous_stock': current_stock,
                'new_stock': new_stock,
                'availability': new_availability,
                'product_name': meta.get('product_name') or meta.get('Product_Name', 'Unknown')
            }
        except Exception as e:
            print(f"❌ Failed to update stock: {e}")
            return {'success': False, 'error': str(e)}
    
    def check_cart_availability(self, cart_items: List[Dict]) -> Dict:
        """
        Validate cart items against current stock availability.
        Returns: {
            'all_available': bool,
            'available_items': [...],
            'out_of_stock_items': [...],
            'limited_stock_items': [...]
        }
        """
        result = {
            'all_available': True,
            'available_items': [],
            'out_of_stock_items': [],
            'limited_stock_items': []
        }
        
        for item in cart_items:
            product_id = item.get('product_url') or item.get('product_id') or item.get('chroma_id', '')
            quantity = int(item.get('quantity', 1))
            
            if not product_id:
                # Try to find by product name
                product_name = item.get('product_name', '')
                if product_name and self.collection:
                    # Search by product name
                    all_products = self.collection.get(include=['metadatas'])
                    for i, meta in enumerate(all_products.get('metadatas', [])):
                        if meta.get('product_name') == product_name or meta.get('Product_Name') == product_name:
                            product_id = all_products["ids"][i]
                            break
            
            current_stock = self.get_stock_quantity(product_id)
            availability = self.get_availability(product_id)
            
            item_with_stock = {
                **item,
                'current_stock': current_stock,
                'availability': availability,
                'requested_quantity': quantity
            }
            
            if current_stock <= 0 or availability == "Out of Stock":
                result['out_of_stock_items'].append(item_with_stock)
                result['all_available'] = False
            elif current_stock < quantity:
                item_with_stock['available_quantity'] = current_stock
                result['limited_stock_items'].append(item_with_stock)
                result['all_available'] = False
            elif availability == "Limited Stock":
                result['limited_stock_items'].append(item_with_stock)
                result['available_items'].append(item_with_stock)
            else:
                result['available_items'].append(item_with_stock)
        
        return result
    
    def is_product_available(self, product_id: str, quantity: int = 1) -> bool:
        """Check if a product is available in the requested quantity"""
        stock = self.get_stock_quantity(product_id)
        return stock >= quantity
