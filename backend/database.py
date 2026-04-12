import csv
import sqlite3
from contextlib import contextmanager
import os
import re
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
import time
import random

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'database', 'inventory.db')
HISTORY_DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'database', 'history.db')

# ==================== UTILITY FUNCTIONS ====================

def clean_item_name(name: str) -> str:
    """Clean item name - removes punctuation, numbers, and number words"""
    name = name.lower().strip()
    name = re.sub(r'[^\w\s]', '', name)
    name = re.sub(r'\d+', '', name)
    
    number_words = ['one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten',
                   'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen', 'seventeen',
                   'eighteen', 'nineteen', 'twenty', 'thirty', 'forty', 'fifty', 'sixty', 'seventy', 
                   'eighty', 'ninety', 'hundred', 'thousand']
    for word in number_words:
        name = name.replace(word, '')
    
    name = re.sub(r'\s+', ' ', name).strip()
    return name if name else 'item'

def standardize_name(name: str) -> str:
    """Convert to singular form - works for ANY word dynamically"""
    name = clean_item_name(name)
    
    if not name or name == '':
        return 'item'
    
    if name.endswith('s') and len(name) > 1 and not name.endswith('ss'):
        if name.endswith('ies'):
            return name[:-3] + 'y'
        elif name.endswith('ves'):
            return name[:-3] + 'f'
        elif name.endswith('oes'):
            return name[:-2]
        else:
            return name[:-1]
    
    return name

def generate_unique_id() -> str:
    """Generate unique item ID"""
    return f"item_{int(time.time() * 1000000)}_{random.randint(1000, 9999)}"

def get_random_price(item_name: str) -> float:
    """Generate realistic price based on item name"""
    price_map = {
        'apple': 0.50, 'banana': 0.30, 'orange': 0.40, 'mango': 1.00, 'grape': 0.20,
        'biscuit': 10.0, 'namkeen': 15.0, 'chips': 20.0, 'cookie': 5.0, 'chocolate': 25.0,
        'pencil': 5.0, 'pen': 10.0, 'notebook': 30.0, 'eraser': 3.0, 'sharpener': 4.0,
        'cake': 50.0, 'bread': 25.0, 'milk': 30.0, 'egg': 6.0, 'butter': 45.0,
        'rice': 60.0, 'wheat': 45.0, 'sugar': 40.0, 'salt': 20.0, 'oil': 110.0,
        'tea': 250.0, 'coffee': 300.0, 'soap': 35.0, 'shampoo': 150.0, 'toothpaste': 80.0
    }
    
    if item_name in price_map:
        return price_map[item_name]
    return round(random.uniform(10, 500), 2)

# ==================== DATABASE CONNECTION ====================

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def init_db():
    """Initialize database with fresh schema"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    with get_db() as conn:
        conn.execute("DROP TABLE IF EXISTS items")
        
        conn.execute('''
            CREATE TABLE items (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                quantity INTEGER DEFAULT 0,
                category TEXT DEFAULT 'general',
                unit TEXT DEFAULT 'piece',
                price REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.execute('CREATE INDEX IF NOT EXISTS idx_name ON items(name)')
        
        # Insert sample items with prices
        sample_items = [
            (generate_unique_id(), 'biscuit', 10, 'snacks', 'packet', 10.0),
            (generate_unique_id(), 'namkeen', 8, 'snacks', 'packet', 15.0),
            (generate_unique_id(), 'apple', 12, 'fruits', 'piece', 0.50),
            (generate_unique_id(), 'banana', 5, 'fruits', 'piece', 0.30),
            (generate_unique_id(), 'orange', 8, 'fruits', 'piece', 0.40),
        ]
        conn.executemany('''
            INSERT INTO items (id, name, quantity, category, unit, price)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', sample_items)
        
        print("[DB] Database initialized with sample data")

def init_history_db():
    os.makedirs(os.path.dirname(HISTORY_DB_PATH), exist_ok=True)
    
    conn = sqlite3.connect(HISTORY_DB_PATH)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id TEXT UNIQUE,
            action TEXT NOT NULL,
            item_name TEXT NOT NULL,
            quantity INTEGER DEFAULT 0,
            previous_quantity INTEGER DEFAULT 0,
            new_quantity INTEGER DEFAULT 0,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_item_name ON transactions(item_name)')
    conn.commit()
    conn.close()

# ==================== CORE OPERATIONS (REAL-TIME) ====================

def get_all_items() -> List[Dict[str, Any]]:
    """Get all inventory items with calculated total value"""
    with get_db() as conn:
        items = []
        for row in conn.execute("SELECT * FROM items ORDER BY name"):
            item = dict(row)
            item['total_value'] = item['quantity'] * item.get('price', 0)
            items.append(item)
        return items

def get_item_by_name(name: str) -> Optional[Dict[str, Any]]:
    name = standardize_name(name)
    with get_db() as conn:
        result = conn.execute("SELECT * FROM items WHERE name = ?", (name,)).fetchone()
        if result:
            item = dict(result)
            item['total_value'] = item['quantity'] * item.get('price', 0)
            return item
        return None

def add_item(name: str, quantity: int, category: str = 'general', unit: str = 'piece', price: float = None) -> bool:
    """Add item - REAL-TIME dynamic"""
    name = standardize_name(name)
    
    if not name or name == 'item' or len(name) < 2:
        return False
    
    if quantity <= 0:
        return False
    
    # Auto-assign price if not provided
    if price is None:
        price = get_random_price(name)
    
    with get_db() as conn:
        existing = conn.execute("SELECT id, quantity, price FROM items WHERE name = ?", (name,)).fetchone()
        
        if existing:
            old_qty = existing['quantity']
            new_qty = old_qty + quantity
            conn.execute('''
                UPDATE items 
                SET quantity = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE name = ?
            ''', (new_qty, name))
            log_transaction('add', name, quantity, old_qty, new_qty)
        else:
            item_id = generate_unique_id()
            conn.execute('''
                INSERT INTO items (id, name, quantity, category, unit, price, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ''', (item_id, name, quantity, category, unit, price))
            log_transaction('add', name, quantity, 0, quantity)
        
        return True

def remove_item(name: str, quantity: int) -> bool:
    """Remove item - REAL-TIME dynamic"""
    name = standardize_name(name)
    
    if not name or name == 'item':
        return False
    
    if quantity <= 0:
        return False
    
    with get_db() as conn:
        existing = conn.execute("SELECT id, name, quantity FROM items WHERE name = ?", (name,)).fetchone()
        
        if not existing:
            return False
        
        current_qty = existing['quantity']
        
        if quantity > current_qty:
            return False
        
        new_qty = current_qty - quantity
        
        if new_qty <= 0:
            conn.execute("DELETE FROM items WHERE name = ?", (name,))
            log_transaction('delete', name, quantity, current_qty, 0)
        else:
            conn.execute('''
                UPDATE items 
                SET quantity = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE name = ?
            ''', (new_qty, name))
            log_transaction('remove', name, quantity, current_qty, new_qty)
        
        return True

def update_item_price(name: str, price: float) -> bool:
    """Update item price - REAL-TIME"""
    name = standardize_name(name)
    with get_db() as conn:
        conn.execute("UPDATE items SET price = ?, updated_at = CURRENT_TIMESTAMP WHERE name = ?", (price, name))
        return True

# ==================== TRANSACTION HISTORY ====================

def log_transaction(action: str, item_name: str, quantity: int, prev_qty: int = 0, new_qty: int = 0):
    try:
        conn = sqlite3.connect(HISTORY_DB_PATH)
        transaction_id = f"txn_{int(time.time() * 1000000)}_{random.randint(1000, 9999)}"
        conn.execute('''
            INSERT INTO transactions (transaction_id, action, item_name, quantity, previous_quantity, new_quantity, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (transaction_id, action, item_name, quantity, prev_qty, new_qty))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error logging transaction: {e}")

def get_transaction_history(limit: int = 50) -> List[Dict[str, Any]]:
    try:
        conn = sqlite3.connect(HISTORY_DB_PATH)
        conn.row_factory = sqlite3.Row
        history = [dict(row) for row in conn.execute(
            "SELECT * FROM transactions ORDER BY timestamp DESC LIMIT ?", (limit,)
        )]
        conn.close()
        return history
    except Exception as e:
        return []

# ==================== STATISTICS (REAL-TIME) ====================

def get_summary_stats() -> Dict[str, Any]:
    items = get_all_items()
    total_items = len(items)
    total_quantity = sum(i['quantity'] for i in items)
    total_value = sum(i['total_value'] for i in items)
    
    return {
        'total_items': total_items,
        'total_quantity': total_quantity,
        'total_value': round(total_value, 2)
    }

def get_all_categories() -> List[str]:
    with get_db() as conn:
        return [row[0] for row in conn.execute("SELECT DISTINCT category FROM items ORDER BY category")]

def search_items(query: str) -> List[Dict[str, Any]]:
    with get_db() as conn:
        items = []
        for row in conn.execute("SELECT * FROM items WHERE name LIKE ? ORDER BY name", (f'%{query}%',)):
            item = dict(row)
            item['total_value'] = item['quantity'] * item.get('price', 0)
            items.append(item)
        return items

# ==================== EXPORT FUNCTIONS ====================

def export_inventory_to_json(filepath: str = None) -> str:
    """Export inventory to JSON"""
    items = get_all_items()
    data = {
        'export_date': datetime.now().isoformat(),
        'total_items': len(items),
        'total_quantity': sum(i['quantity'] for i in items),
        'total_value': sum(i['total_value'] for i in items),
        'inventory': items
    }
    
    if not filepath:
        filepath = os.path.join(os.path.dirname(DB_PATH), f'inventory_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, default=str, ensure_ascii=False)
    
    return filepath

def export_inventory_to_csv() -> str:
    """Export inventory to CSV"""
    items = get_all_items()
    filepath = os.path.join(os.path.dirname(DB_PATH), f'inventory_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')
    
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Name', 'Quantity', 'Unit', 'Category', 'Price (₹)', 'Total Value (₹)'])
        for item in items:
            writer.writerow([
                item['name'], item['quantity'], item.get('unit', 'piece'),
                item.get('category', 'general'), item.get('price', 0),
                item['total_value']
            ])
    
    return filepath

def export_inventory_to_txt() -> str:
    """Export inventory to TXT format"""
    items = get_all_items()
    filepath = os.path.join(os.path.dirname(DB_PATH), f'inventory_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt')
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("SPEAK SNAP STORE - INVENTORY REPORT\n")
        f.write(f"Export Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 60 + "\n\n")
        
        for item in items:
            f.write(f"📦 {item['name'].upper()}\n")
            f.write(f"   Quantity: {item['quantity']} {item.get('unit', 'piece')}(s)\n")
            f.write(f"   Price: ₹{item.get('price', 0):.2f} per {item.get('unit', 'piece')}\n")
            f.write(f"   Total Value: ₹{item['total_value']:.2f}\n")
            f.write(f"   Category: {item.get('category', 'general')}\n")
            f.write("-" * 40 + "\n")
        
        f.write("\n" + "=" * 60 + "\n")
        f.write(f"SUMMARY\n")
        f.write(f"Total Items: {len(items)}\n")
        f.write(f"Total Quantity: {sum(i['quantity'] for i in items)}\n")
        f.write(f"Total Inventory Value: ₹{sum(i['total_value'] for i in items):.2f}\n")
        f.write("=" * 60 + "\n")
    
    return filepath

# ==================== INITIALIZE ====================
init_db()
init_history_db()

print("=" * 50)
print("🗄️ REAL-TIME DATABASE ACTIVE")
print("=" * 50)
print("✅ Dynamic add/remove ready")
print("✅ Price/Value system active")
print("✅ Export ready (JSON/CSV/TXT)")
print("=" * 50)