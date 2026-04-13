import sqlite3
import os
import re
import json
import asyncio
import threading
import random
from contextlib import contextmanager, asynccontextmanager
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor
import functools
import hashlib
from collections import OrderedDict
import time

#CONFIGURATION 
DB_PATH = os.getenv('SQLITE_PATH', os.path.join(os.path.dirname(__file__), 'database', 'inventory.db'))
CACHE_SIZE = 1000
CACHE_TTL = 30  # seconds

# Thread pool for async operations
executor = ThreadPoolExecutor(max_workers=4)

# Simple in-memory cache
class TimeoutCache:
    def __init__(self, maxsize=1000, ttl=30):
        self.cache = OrderedDict()
        self.maxsize = maxsize
        self.ttl = ttl
        self.lock = threading.Lock()
    
    def get(self, key):
        with self.lock:
            if key in self.cache:
                value, timestamp = self.cache[key]
                if time.time() - timestamp < self.ttl:
                    self.cache.move_to_end(key)
                    return value
                else:
                    del self.cache[key]
        return None
    
    def set(self, key, value):
        with self.lock:
            if key in self.cache:
                self.cache.move_to_end(key)
            self.cache[key] = (value, time.time())
            if len(self.cache) > self.maxsize:
                self.cache.popitem(last=False)
    
    def invalidate(self, pattern=None):
        with self.lock:
            if pattern is None:
                self.cache.clear()
            else:
                keys_to_remove = [k for k in self.cache if pattern in k]
                for k in keys_to_remove:
                    del self.cache[k]

# Global cache instance
cache = TimeoutCache(maxsize=CACHE_SIZE, ttl=CACHE_TTL)

# DYNAMIC PRICING

def get_realistic_price(item_name: str) -> float:
    """Generate realistic price based on item type"""
    item_name = item_name.lower()
    
    # Price mapping for common items (realistic market prices)
    price_map = {
        # Fruits (per piece)
        'apple': 5.0, 'banana': 3.0, 'orange': 2.5, 'mango': 3.0,
        'grape': 2.0, 'strawberry': 0.60, 'watermelon': 3.00, 'pineapple': 2.5,
        'pear': 5.0, 'peach': 8.0, 'kiwi': 20.0, 'lemon': 3.5,
        
        # Vegetables (per piece or kg)
        'tomato': 4.0, 'potato': 2.5, 'onion': 3.0, 'carrot': 3.5,
        'cucumber': 4.5, 'broccoli': 6.20, 'cauliflower': 4.00, 'cabbage': 6.0,
        'spinach': 5.0, 'bell pepper': 7.0, 'chili': 1.0, 'garlic': 2.5,
        
        # Snacks (per packet)
        'biscuit': 10.0, 'cookie': 15.0, 'chocolate': 25.0, 'chips': 20.0,
        'namkeen': 15.0, 'cake': 50.0, 'donut': 30.0, 'ice cream': 40.0,
        
        # Stationery (per piece)
        'pen': 10.0, 'pencil': 5.0, 'eraser': 3.0, 'sharpener': 4.0,
        'notebook': 30.0, 'ruler': 8.0, 'marker': 12.0, 'highlighter': 15.0,
        
        # Household
        'bottle': 25.0, 'cup': 15.0, 'plate': 20.0, 'bowl': 18.0,
        'spoon': 5.0, 'fork': 5.0, 'knife': 8.0, 'glass': 12.0,
        
        # Electronics
        'battery': 100.0, 'charger': 250.0, 'cable': 80.0, 'headphone': 300.0,
        
        # Dairy
        'milk': 30.0, 'butter': 45.0, 'cheese': 80.0, 'yogurt': 25.0,
        
        # Grains (per kg)
        'rice': 60.0, 'wheat': 45.0, 'flour': 40.0, 'sugar': 40.0,
        'salt': 20.0, 'oil': 110.0, 'spice': 50.0,
        
        # Beverages
        'tea': 250.0, 'coffee': 300.0, 'juice': 80.0, 'soda': 35.0,
        
        # Personal care
        'soap': 35.0, 'shampoo': 150.0, 'toothpaste': 80.0, 'brush': 25.0,
    }
    
    # Check for exact match
    for key, price in price_map.items():
        if key in item_name:
            return price
    
    # Generate random price based on item name length (10-500 range)
    base_price = random.uniform(10, 100)
    if len(item_name) > 10:
        base_price *= 1.5
    return round(base_price, 2)

# DATABASE CONNECTION POOL
class ConnectionPool:
    """Thread-safe connection pool for SQLite"""
    def __init__(self, max_connections=5):
        self.max_connections = max_connections
        self._pool = []
        self._lock = threading.Lock()
    
    def get_connection(self):
        with self._lock:
            if self._pool:
                return self._pool.pop()
            return self._create_connection()
    
    def return_connection(self, conn):
        with self._lock:
            if len(self._pool) < self.max_connections:
                self._pool.append(conn)
            else:
                conn.close()
    
    def _create_connection(self):
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        conn = sqlite3.connect(DB_PATH, timeout=10, isolation_level=None)
        conn.row_factory = sqlite3.Row
        # Aggressive performance optimizations
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=-20000")  # 20MB cache
        conn.execute("PRAGMA temp_store=MEMORY")
        conn.execute("PRAGMA mmap_size=268435456")  # 256MB mmap
        conn.execute("PRAGMA optimize")
        return conn

# Global connection pool
pool = ConnectionPool(max_connections=10)

@contextmanager
def get_db():
    """Fast database connection from pool"""
    conn = pool.get_connection()
    try:
        yield conn
    finally:
        pool.return_connection(conn)

# Async wrapper for database operations
def run_in_executor(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        return await asyncio.get_event_loop().run_in_executor(executor, lambda: func(*args, **kwargs))
    return wrapper

# ==================== DATABASE INITIALIZATION ====================
def init_db():
    """Initialize database with optimized schema and indexes"""
    with get_db() as conn:
        # Items table with optimized schema
        conn.execute('''
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE COLLATE NOCASE,
                quantity INTEGER DEFAULT 0,
                category TEXT DEFAULT 'general',
                unit TEXT DEFAULT 'piece',
                price REAL DEFAULT 0.0,
                total_value REAL GENERATED ALWAYS AS (quantity * price) STORED,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Transactions table with price tracking
        conn.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id TEXT UNIQUE,
                action TEXT NOT NULL,
                item_name TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                previous_quantity INTEGER DEFAULT 0,
                new_quantity INTEGER DEFAULT 0,
                price REAL DEFAULT 0.0,
                total_value REAL DEFAULT 0.0,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Comprehensive indexes for lightning-fast queries
        conn.execute("CREATE INDEX IF NOT EXISTS idx_items_name ON items(name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_items_category ON items(category)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_items_quantity ON items(quantity)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_items_updated ON items(updated_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_transactions_item ON transactions(item_name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_transactions_time ON transactions(timestamp DESC)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_transactions_action ON transactions(action)")
        
        # Composite indexes for complex queries
        conn.execute("CREATE INDEX IF NOT EXISTS idx_items_category_quantity ON items(category, quantity)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_transactions_item_time ON transactions(item_name, timestamp DESC)")
        
        # Insert sample data if empty
        cursor = conn.execute("SELECT COUNT(*) FROM items")
        if cursor.fetchone()[0] == 0:
            sample_items = [
                ('apple', 12, 'fruits', 'piece', 0.50),
                ('banana', 5, 'fruits', 'piece', 0.30),
                ('orange', 8, 'fruits', 'piece', 0.40),
                ('biscuit', 10, 'snacks', 'packet', 10.0),
                ('namkeen', 8, 'snacks', 'packet', 15.0),
            ]
            conn.executemany('''INSERT INTO items (name, quantity, category, unit, price) 
                               VALUES (?, ?, ?, ?, ?)''', sample_items)
    
    cache.invalidate()
    print("[DB] ⚡ Database initialized with ultra-fast optimizations")

# ==================== UTILITY FUNCTIONS ====================
def standardize_name(name: str) -> str:
    """Fast name standardization with caching"""
    name = name.lower().strip()
    name = re.sub(r'[^\w\s]', '', name)
    name = re.sub(r'\d+', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    
    if name.endswith('s') and len(name) > 1 and not name.endswith('ss'):
        if name.endswith('ies'):
            name = name[:-3] + 'y'
        elif name.endswith('ves'):
            name = name[:-3] + 'f'
        else:
            name = name[:-1]
    return name if name and len(name) > 1 else 'item'

def generate_transaction_id() -> str:
    """Generate unique transaction ID"""
    return f"txn_{int(time.time() * 1000000)}_{random.randint(1000, 9999)}"

# ==================== CORE CRUD OPERATIONS (OPTIMIZED) ====================

def get_all_items() -> List[Dict[str, Any]]:
    """Get all items with caching - ULTRA FAST"""
    cache_key = 'all_items'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    
    with get_db() as conn:
        items = []
        cursor = conn.execute("SELECT * FROM items ORDER BY name")
        for row in cursor:
            item = dict(row)
            items.append(item)
        
        cache.set(cache_key, items)
        return items

@run_in_executor
async def get_all_items_async():
    """Async version for non-blocking operations"""
    return get_all_items()

def get_item_by_name(name: str) -> Optional[Dict[str, Any]]:
    """Get single item with caching"""
    name = standardize_name(name)
    cache_key = f'item_{name}'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    
    with get_db() as conn:
        result = conn.execute("SELECT * FROM items WHERE name = ?", (name,)).fetchone()
        item = dict(result) if result else None
        if item:
            cache.set(cache_key, item)
        return item

def add_item(name: str, quantity: int, category: str = 'general', unit: str = 'piece', price: float = None) -> bool:
    """Add item - INSTANT with cache invalidation and dynamic pricing"""
    name = standardize_name(name)
    if not name or len(name) < 2 or quantity <= 0:
        return False
    
    # Auto-assign price if not provided
    if price is None or price == 0:
        price = get_realistic_price(name)
    
    with get_db() as conn:
        existing = conn.execute("SELECT id, quantity, price FROM items WHERE name = ?", (name,)).fetchone()
        
        if existing:
            old_qty = existing['quantity']
            new_qty = old_qty + quantity
            # Keep existing price if already set
            if existing['price'] == 0:
                conn.execute('''UPDATE items SET quantity = ?, price = ?, updated_at = CURRENT_TIMESTAMP 
                               WHERE name = ?''', (new_qty, price, name))
            else:
                conn.execute('''UPDATE items SET quantity = ?, updated_at = CURRENT_TIMESTAMP 
                               WHERE name = ?''', (new_qty, name))
                price = existing['price']
            
            total_value = price * quantity
            log_transaction('add', name, quantity, old_qty, new_qty, price, total_value)
        else:
            conn.execute('''INSERT INTO items (name, quantity, category, unit, price) 
                           VALUES (?, ?, ?, ?, ?)''', (name, quantity, category, unit, price))
            total_value = price * quantity
            log_transaction('add', name, quantity, 0, quantity, price, total_value)
    
    # Invalidate caches
    cache.invalidate()
    return True

def remove_item(name: str, quantity: int) -> bool:
    """Remove item - INSTANT with cache invalidation and transaction logging"""
    name = standardize_name(name)
    if not name or len(name) < 2 or quantity <= 0:
        return False
    
    with get_db() as conn:
        existing = conn.execute("SELECT id, name, quantity, price FROM items WHERE name = ?", (name,)).fetchone()
        if not existing:
            return False
        
        current_qty = existing['quantity']
        if quantity > current_qty:
            return False
        
        price = existing['price'] if existing['price'] else get_realistic_price(name)
        new_qty = current_qty - quantity
        total_value = price * quantity
        
        if new_qty <= 0:
            conn.execute("DELETE FROM items WHERE name = ?", (name,))
            log_transaction('delete', name, quantity, current_qty, 0, price, total_value)
        else:
            conn.execute('''UPDATE items SET quantity = ?, updated_at = CURRENT_TIMESTAMP 
                           WHERE name = ?''', (new_qty, name))
            log_transaction('remove', name, quantity, current_qty, new_qty, price, total_value)
    
    # Invalidate caches
    cache.invalidate()
    return True

def update_item_price(name: str, price: float) -> bool:
    """Update item price with cache invalidation"""
    name = standardize_name(name)
    if not name:
        return False
    
    with get_db() as conn:
        conn.execute('''UPDATE items SET price = ?, updated_at = CURRENT_TIMESTAMP 
                       WHERE name = ?''', (price, name))
    
    cache.invalidate()
    return True

def log_transaction(action: str, item_name: str, quantity: int, prev_qty: int = 0, 
                    new_qty: int = 0, price: float = 0, total_value: float = 0):
    """Log every transaction with price and value"""
    try:
        with get_db() as conn:
            transaction_id = generate_transaction_id()
            conn.execute('''
                INSERT INTO transactions (transaction_id, action, item_name, quantity, 
                                         previous_quantity, new_quantity, price, total_value, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (transaction_id, action, item_name, quantity, prev_qty, new_qty, price, total_value))
    except Exception as e:
        print(f"Error logging transaction: {e}")

# ==================== OPTIMIZED QUERIES ====================

def get_summary_stats() -> Dict[str, Any]:
    """Get stats - FAST with caching"""
    cache_key = 'summary_stats'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    
    with get_db() as conn:
        stats = conn.execute('''
            SELECT 
                COUNT(*) as total_items,
                COALESCE(SUM(quantity), 0) as total_quantity,
                COALESCE(SUM(quantity * price), 0) as total_value,
                COUNT(CASE WHEN quantity <= 5 THEN 1 END) as low_stock_items
            FROM items
        ''').fetchone()
        
        result = {
            'total_items': stats[0],
            'total_quantity': stats[1],
            'total_value': round(stats[2], 2),
            'low_stock_items': stats[3]
        }
        cache.set(cache_key, result)
        return result

def get_transaction_history(limit: int = 20) -> List[Dict[str, Any]]:
    """Get recent transactions with price and value - FAST"""
    cache_key = f'transactions_{limit}'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    
    with get_db() as conn:
        transactions = [dict(row) for row in conn.execute('''
            SELECT id, action, item_name, quantity, price, total_value, timestamp 
            FROM transactions ORDER BY timestamp DESC LIMIT ?
        ''', (limit,))]
        cache.set(cache_key, transactions)
        return transactions

def get_all_categories() -> List[str]:
    """Get all categories with caching"""
    cache_key = 'all_categories'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    
    with get_db() as conn:
        categories = [row[0] for row in conn.execute("SELECT DISTINCT category FROM items ORDER BY category")]
        cache.set(cache_key, categories)
        return categories

def search_items(query: str) -> List[Dict[str, Any]]:
    """Search items - OPTIMIZED with FTS-like pattern"""
    if not query or len(query) < 2:
        return get_all_items()
    
    with get_db() as conn:
        items = []
        for row in conn.execute('''SELECT * FROM items WHERE name LIKE ? ORDER BY 
                                  CASE WHEN name = ? THEN 1 
                                       WHEN name LIKE ? THEN 2 
                                       ELSE 3 END''', 
                               (f'%{query}%', query, f'{query}%')):
            items.append(dict(row))
        return items

def get_low_stock_items(threshold: int = 5) -> List[Dict[str, Any]]:
    """Get low stock items - OPTIMIZED"""
    cache_key = f'low_stock_{threshold}'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    
    with get_db() as conn:
        items = [dict(row) for row in conn.execute('''
            SELECT * FROM items WHERE quantity <= ? ORDER BY quantity ASC
        ''', (threshold,))]
        cache.set(cache_key, items)
        return items

def get_top_items(limit: int = 10) -> List[Dict[str, Any]]:
    """Get top items by value"""
    with get_db() as conn:
        return [dict(row) for row in conn.execute('''
            SELECT * FROM items ORDER BY (quantity * price) DESC LIMIT ?
        ''', (limit,))]

def get_recent_activity(days: int = 7) -> List[Dict[str, Any]]:
    """Get recent activity summary"""
    with get_db() as conn:
        return [dict(row) for row in conn.execute('''
            SELECT date(timestamp) as date, 
                   COUNT(*) as total_actions,
                   SUM(CASE WHEN action = 'add' THEN quantity ELSE 0 END) as items_added,
                   SUM(CASE WHEN action = 'remove' THEN quantity ELSE 0 END) as items_removed
            FROM transactions 
            WHERE timestamp >= date('now', ?)
            GROUP BY date(timestamp)
            ORDER BY date DESC
        ''', (f'-{days} days',))]

# ==================== BULK OPERATIONS ====================

def bulk_add_items(items: List[Tuple]) -> int:
    """Bulk add items - VERY FAST"""
    if not items:
        return 0
    
    with get_db() as conn:
        conn.executemany('''INSERT OR REPLACE INTO items (name, quantity, category, unit, price, updated_at) 
                           VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)''', items)
        cache.invalidate()
        return len(items)

def bulk_remove_items(names: List[str]) -> int:
    """Bulk remove items - VERY FAST"""
    if not names:
        return 0
    
    placeholders = ','.join(['?' for _ in names])
    with get_db() as conn:
        conn.execute(f"DELETE FROM items WHERE name IN ({placeholders})", names)
        cache.invalidate()
        return len(names)

# ==================== EXPORT FUNCTIONS ====================

def export_inventory_to_json(filepath: str = None) -> str:
    """Export inventory to JSON"""
    items = get_all_items()
    data = {
        'export_date': datetime.now().isoformat(),
        'total_items': len(items),
        'total_quantity': sum(i['quantity'] for i in items),
        'total_value': get_summary_stats()['total_value'],
        'inventory': items
    }
    
    if not filepath:
        filepath = os.path.join(os.path.dirname(DB_PATH), f'inventory_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, default=str, ensure_ascii=False)
    
    return filepath

def export_inventory_to_csv(filepath: str = None) -> str:
    """Export inventory to CSV"""
    import csv
    items = get_all_items()
    
    if not filepath:
        filepath = os.path.join(os.path.dirname(DB_PATH), f'inventory_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')
    
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['name', 'quantity', 'category', 'unit', 'price', 'total_value'])
        writer.writeheader()
        for item in items:
            writer.writerow({
                'name': item['name'],
                'quantity': item['quantity'],
                'category': item.get('category', 'general'),
                'unit': item.get('unit', 'piece'),
                'price': item.get('price', 0),
                'total_value': item['quantity'] * item.get('price', 0)
            })
    
    return filepath

def export_inventory_to_txt(filepath: str = None) -> str:
    """Export inventory to formatted text"""
    items = get_all_items()
    stats = get_summary_stats()
    
    if not filepath:
        filepath = os.path.join(os.path.dirname(DB_PATH), f'inventory_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt')
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("SPEAK SNAP STORE - INVENTORY REPORT\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 60 + "\n\n")
        
        f.write("SUMMARY STATISTICS\n")
        f.write("-" * 40 + "\n")
        f.write(f"Total Items: {stats['total_items']}\n")
        f.write(f"Total Units: {stats['total_quantity']}\n")
        f.write(f"Total Value: ₹{stats['total_value']:.2f}\n")
        f.write(f"Low Stock Items: {stats['low_stock_items']}\n\n")
        
        f.write("INVENTORY DETAILS\n")
        f.write("-" * 40 + "\n")
        for item in items:
            f.write(f"\n📦 {item['name'].upper()}\n")
            f.write(f"   Quantity: {item['quantity']} {item.get('unit', 'piece')}(s)\n")
            f.write(f"   Price: ₹{item.get('price', 0):.2f} per unit\n")
            f.write(f"   Total Value: ₹{item['quantity'] * item.get('price', 0):.2f}\n")
            f.write(f"   Category: {item.get('category', 'general')}\n")
        
        f.write("\n" + "=" * 60 + "\n")
        f.write("END OF REPORT\n")
        f.write("=" * 60 + "\n")
    
    return filepath

# ==================== HEALTH CHECK ====================

def get_db_health() -> Dict[str, Any]:
    """Get database health metrics"""
    with get_db() as conn:
        # Get database size
        db_size = os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0
        
        # Get table stats
        item_count = conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
        transaction_count = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        
        return {
            'status': 'healthy',
            'db_size_mb': round(db_size / (1024 * 1024), 2),
            'item_count': item_count,
            'transaction_count': transaction_count,
            'cache_size': len(cache.cache),
            'connection_pool_size': pool.max_connections
        }

# ==================== INITIALIZE ====================
init_db()

print("=" * 50)
print("⚡ ULTRA-FAST REAL-TIME DATABASE ACTIVE")
print("=" * 50)
print(f"📁 Database: {DB_PATH}")
print(f"💾 Cache Size: {CACHE_SIZE} items, TTL: {CACHE_TTL}s")
print(f"🔌 Connection Pool: {pool.max_connections} connections")
print("💰 Dynamic Pricing Active")
print("📜 Enhanced Transaction Logging with Price/Value")
print("✅ Instant add/remove ready")
print("✅ Async operations ready")
print("=" * 50)
