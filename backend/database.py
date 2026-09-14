import sqlite3
import os
import re
import json
import asyncio
import threading
import random
import functools
import time

from contextlib import contextmanager
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor
from collections import OrderedDict


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DEFAULT_DB_PATH = os.path.join(
    BASE_DIR,
    "database",
    "inventory.db"
)

DB_PATH = os.getenv(
    "SQLITE_PATH",
    DEFAULT_DB_PATH
)

# Make sure the database directory exists.
DB_DIRECTORY = os.path.dirname(os.path.abspath(DB_PATH))

if DB_DIRECTORY:
    os.makedirs(DB_DIRECTORY, exist_ok=True)


CACHE_SIZE = 1000
CACHE_TTL = 30


# ============================================================
# THREAD POOL
# ============================================================

executor = ThreadPoolExecutor(
    max_workers=4,
    thread_name_prefix="database-worker"
)


# ============================================================
# CACHE
# ============================================================

class TimeoutCache:
    """
    Thread-safe in-memory cache with TTL.
    """

    def __init__(
        self,
        maxsize: int = 1000,
        ttl: int = 30
    ):
        self.cache = OrderedDict()
        self.maxsize = maxsize
        self.ttl = ttl
        self.lock = threading.Lock()

    def get(self, key):

        with self.lock:

            if key not in self.cache:
                return None

            value, timestamp = self.cache[key]

            if time.time() - timestamp < self.ttl:
                self.cache.move_to_end(key)
                return value

            # Expired item
            del self.cache[key]

            return None

    def set(self, key, value):

        with self.lock:

            if key in self.cache:
                self.cache.move_to_end(key)

            self.cache[key] = (
                value,
                time.time()
            )

            while len(self.cache) > self.maxsize:
                self.cache.popitem(last=False)

    def invalidate(self, pattern=None):

        with self.lock:

            if pattern is None:
                self.cache.clear()
                return

            keys_to_remove = [
                key
                for key in self.cache
                if pattern in str(key)
            ]

            for key in keys_to_remove:
                self.cache.pop(key, None)


cache = TimeoutCache(
    maxsize=CACHE_SIZE,
    ttl=CACHE_TTL
)


# ============================================================
# DYNAMIC PRICING
# ============================================================

def get_realistic_price(item_name: str) -> float:
    """
    Generate a realistic default price based on item type.
    """

    item_name = str(item_name).lower().strip()

    price_map = {

        # Fruits
        "apple": 5.0,
        "banana": 3.0,
        "orange": 2.5,
        "mango": 3.0,
        "grape": 2.0,
        "strawberry": 0.60,
        "watermelon": 3.00,
        "pineapple": 2.5,
        "pear": 5.0,
        "peach": 8.0,
        "kiwi": 20.0,
        "lemon": 3.5,

        # Vegetables
        "tomato": 4.0,
        "potato": 2.5,
        "onion": 3.0,
        "carrot": 3.5,
        "cucumber": 4.5,
        "broccoli": 6.20,
        "cauliflower": 4.00,
        "cabbage": 6.0,
        "spinach": 5.0,
        "bell pepper": 7.0,
        "chili": 1.0,
        "garlic": 2.5,

        # Snacks
        "biscuit": 10.0,
        "cookie": 15.0,
        "chocolate": 25.0,
        "chips": 20.0,
        "namkeen": 15.0,
        "cake": 50.0,
        "donut": 30.0,
        "ice cream": 40.0,

        # Stationery
        "pen": 10.0,
        "pencil": 5.0,
        "eraser": 3.0,
        "sharpener": 4.0,
        "notebook": 30.0,
        "ruler": 8.0,
        "marker": 12.0,
        "highlighter": 15.0,

        # Household
        "bottle": 25.0,
        "cup": 15.0,
        "plate": 20.0,
        "bowl": 18.0,
        "spoon": 5.0,
        "fork": 5.0,
        "knife": 8.0,
        "glass": 12.0,

        # Electronics
        "battery": 100.0,
        "charger": 250.0,
        "cable": 80.0,
        "headphone": 300.0,

        # Dairy
        "milk": 30.0,
        "butter": 45.0,
        "cheese": 80.0,
        "yogurt": 25.0,

        # Grains
        "rice": 60.0,
        "wheat": 45.0,
        "flour": 40.0,
        "sugar": 40.0,
        "salt": 20.0,
        "oil": 110.0,
        "spice": 50.0,

        # Beverages
        "tea": 250.0,
        "coffee": 300.0,
        "juice": 80.0,
        "soda": 35.0,

        # Personal care
        "soap": 35.0,
        "shampoo": 150.0,
        "toothpaste": 80.0,
        "brush": 25.0
    }

    for key, price in price_map.items():

        if key in item_name:
            return price

    # Default fallback
    base_price = random.uniform(10, 100)

    if len(item_name) > 10:
        base_price *= 1.5

    return round(base_price, 2)


# ============================================================
# DATABASE CONNECTION POOL
# ============================================================

class ConnectionPool:
    """
    Thread-safe SQLite connection pool.
    """

    def __init__(self, max_connections: int = 5):

        self.max_connections = max_connections
        self._pool = []
        self._lock = threading.Lock()

    def get_connection(self):

        with self._lock:

            # Reuse an existing connection if possible.
            while self._pool:

                conn = self._pool.pop()

                try:
                    # Test that connection is still usable.
                    conn.execute("SELECT 1")
                    return conn

                except sqlite3.Error:
                    try:
                        conn.close()
                    except Exception:
                        pass

            return self._create_connection()

    def return_connection(self, conn):

        if conn is None:
            return

        try:
            # Verify connection before returning it.
            conn.execute("SELECT 1")
        except sqlite3.Error:

            try:
                conn.close()
            except Exception:
                pass

            return

        with self._lock:

            if len(self._pool) < self.max_connections:
                self._pool.append(conn)
            else:

                try:
                    conn.close()
                except Exception:
                    pass

    def _create_connection(self):

        os.makedirs(
            os.path.dirname(os.path.abspath(DB_PATH)),
            exist_ok=True
        )

        conn = sqlite3.connect(
            DB_PATH,
            timeout=30,
            isolation_level=None,
            check_same_thread=False
        )

        conn.row_factory = sqlite3.Row

        # SQLite performance/reliability settings.
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA busy_timeout=30000")
            conn.execute("PRAGMA cache_size=-20000")
            conn.execute("PRAGMA temp_store=MEMORY")
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA optimize")
        except sqlite3.Error:
            pass

        return conn

    def close_all(self):

        with self._lock:

            for conn in self._pool:

                try:
                    conn.close()
                except Exception:
                    pass

            self._pool.clear()


pool = ConnectionPool(
    max_connections=10
)


# ============================================================
# DATABASE CONTEXT
# ============================================================

@contextmanager
def get_db():
    """
    Get a database connection from the pool.
    """

    conn = pool.get_connection()

    try:
        yield conn

    finally:
        pool.return_connection(conn)


# ============================================================
# ASYNC DATABASE WRAPPER
# ============================================================

def run_in_executor(func):

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):

        loop = asyncio.get_running_loop()

        return await loop.run_in_executor(
            executor,
            lambda: func(*args, **kwargs)
        )

    return wrapper


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def init_db():
    """
    Create database tables and indexes if they do not exist.
    """

    with get_db() as conn:

        # ----------------------------------------------------
        # ITEMS
        # ----------------------------------------------------

        conn.execute("""
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE COLLATE NOCASE,
                quantity INTEGER DEFAULT 0,
                category TEXT DEFAULT 'general',
                unit TEXT DEFAULT 'piece',
                price REAL DEFAULT 0.0,
                total_value REAL
                    GENERATED ALWAYS AS (quantity * price) STORED,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ----------------------------------------------------
        # TRANSACTIONS
        # ----------------------------------------------------

        conn.execute("""
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
        """)

        # ----------------------------------------------------
        # SCHEMA MIGRATIONS
        # ----------------------------------------------------
        # The application may be opened with a database created by
        # an older version of the project. CREATE TABLE IF NOT EXISTS
        # does not add newly introduced columns to an existing table.
        # Add missing columns here so old databases continue to work.

        def ensure_column(table_name: str, column_name: str, column_definition: str):
            existing_columns = {
                row["name"]
                for row in conn.execute(
                    f"PRAGMA table_info({table_name})"
                ).fetchall()
            }

            if column_name not in existing_columns:
                conn.execute(
                    f"ALTER TABLE {table_name} "
                    f"ADD COLUMN {column_name} {column_definition}"
                )
                print(
                    f"[DB] Added missing column "
                    f"{table_name}.{column_name}"
                )

        # Existing versions of the database may not have these
        # transaction pricing columns.
        ensure_column(
            "transactions",
            "price",
            "REAL DEFAULT 0.0"
        )

        ensure_column(
            "transactions",
            "total_value",
            "REAL DEFAULT 0.0"
        )

        # Keep transaction price/value data consistent for old rows.
        conn.execute("""
            UPDATE transactions
            SET price = COALESCE(price, 0.0),
                total_value = COALESCE(
                    total_value,
                    quantity * COALESCE(price, 0.0)
                )
            WHERE price IS NULL
               OR total_value IS NULL
        """)

        # Older databases may also be missing price on items.
        # This is harmless for databases that already have it.
        ensure_column(
            "items",
            "price",
            "REAL DEFAULT 0.0"
        )

        conn.execute("""
            UPDATE items
            SET price = COALESCE(price, 0.0)
            WHERE price IS NULL
        """)

        # ----------------------------------------------------
        # INDEXES
        # ----------------------------------------------------

        indexes = [
            """
            CREATE INDEX IF NOT EXISTS idx_items_name
            ON items(name)
            """,

            """
            CREATE INDEX IF NOT EXISTS idx_items_category
            ON items(category)
            """,

            """
            CREATE INDEX IF NOT EXISTS idx_items_quantity
            ON items(quantity)
            """,

            """
            CREATE INDEX IF NOT EXISTS idx_items_updated
            ON items(updated_at)
            """,

            """
            CREATE INDEX IF NOT EXISTS idx_transactions_item
            ON transactions(item_name)
            """,

            """
            CREATE INDEX IF NOT EXISTS idx_transactions_time
            ON transactions(timestamp DESC)
            """,

            """
            CREATE INDEX IF NOT EXISTS idx_transactions_action
            ON transactions(action)
            """,

            """
            CREATE INDEX IF NOT EXISTS idx_items_category_quantity
            ON items(category, quantity)
            """,

            """
            CREATE INDEX IF NOT EXISTS idx_transactions_item_time
            ON transactions(item_name, timestamp DESC)
            """
        ]

        for index_sql in indexes:
            conn.execute(index_sql)

        # ----------------------------------------------------
        # SAMPLE DATA
        # ----------------------------------------------------

        cursor = conn.execute(
            "SELECT COUNT(*) FROM items"
        )

        item_count = cursor.fetchone()[0]

        if item_count == 0:

            sample_items = [
                (
                    "apple",
                    12,
                    "fruits",
                    "piece",
                    0.50
                ),
                (
                    "banana",
                    5,
                    "fruits",
                    "piece",
                    0.30
                ),
                (
                    "orange",
                    8,
                    "fruits",
                    "piece",
                    0.40
                ),
                (
                    "biscuit",
                    10,
                    "snacks",
                    "packet",
                    10.0
                ),
                (
                    "namkeen",
                    8,
                    "snacks",
                    "packet",
                    15.0
                )
            ]

            conn.executemany(
                """
                INSERT INTO items
                (
                    name,
                    quantity,
                    category,
                    unit,
                    price
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                sample_items
            )

    cache.invalidate()

    logger = print
    logger("[DB] Database initialized successfully")


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def standardize_name(name: str) -> str:

    if not name:
        return "item"

    name = str(name).lower().strip()

    name = re.sub(
        r"[^\w\s]",
        "",
        name
    )

    name = re.sub(
        r"\d+",
        "",
        name
    )

    name = re.sub(
        r"\s+",
        " ",
        name
    ).strip()

    # Basic plural normalization.
    if (
        name.endswith("s")
        and len(name) > 1
        and not name.endswith("ss")
    ):

        if name.endswith("ies"):
            name = name[:-3] + "y"

        elif name.endswith("ves"):
            name = name[:-3] + "f"

        else:
            name = name[:-1]

    return (
        name
        if name and len(name) > 1
        else "item"
    )


def generate_transaction_id() -> str:

    return (
        f"txn_"
        f"{int(time.time() * 1000000)}_"
        f"{random.randint(1000, 9999)}"
    )


# ============================================================
# CORE CRUD
# ============================================================

def get_all_items() -> List[Dict[str, Any]]:

    cache_key = "all_items"

    cached = cache.get(cache_key)

    if cached is not None:
        return cached

    with get_db() as conn:

        rows = conn.execute(
            """
            SELECT *
            FROM items
            ORDER BY name
            """
        ).fetchall()

        items = [
            dict(row)
            for row in rows
        ]

        cache.set(
            cache_key,
            items
        )

        return items


@run_in_executor
def get_all_items_async():

    return get_all_items()


def get_item_by_name(
    name: str
) -> Optional[Dict[str, Any]]:

    name = standardize_name(name)

    cache_key = f"item_{name}"

    cached = cache.get(cache_key)

    if cached is not None:
        return cached

    with get_db() as conn:

        result = conn.execute(
            """
            SELECT *
            FROM items
            WHERE name = ?
            """,
            (name,)
        ).fetchone()

        item = (
            dict(result)
            if result
            else None
        )

        if item:
            cache.set(
                cache_key,
                item
            )

        return item


def add_item(
    name: str,
    quantity: int,
    category: str = "general",
    unit: str = "piece",
    price: float = None
) -> bool:

    name = standardize_name(name)

    if (
        not name
        or len(name) < 2
        or quantity <= 0
    ):
        return False

    if price is None or price == 0:
        price = get_realistic_price(name)

    with get_db() as conn:

        existing = conn.execute(
            """
            SELECT id, quantity, price
            FROM items
            WHERE name = ?
            """,
            (name,)
        ).fetchone()

        if existing:

            old_qty = existing["quantity"]
            new_qty = old_qty + quantity

            existing_price = existing["price"]

            if not existing_price:

                conn.execute(
                    """
                    UPDATE items
                    SET quantity = ?,
                        price = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE name = ?
                    """,
                    (
                        new_qty,
                        price,
                        name
                    )
                )

            else:

                price = existing_price

                conn.execute(
                    """
                    UPDATE items
                    SET quantity = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE name = ?
                    """,
                    (
                        new_qty,
                        name
                    )
                )

            total_value = price * quantity

            log_transaction(
                "add",
                name,
                quantity,
                old_qty,
                new_qty,
                price,
                total_value
            )

        else:

            conn.execute(
                """
                INSERT INTO items
                (
                    name,
                    quantity,
                    category,
                    unit,
                    price
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    name,
                    quantity,
                    category,
                    unit,
                    price
                )
            )

            total_value = price * quantity

            log_transaction(
                "add",
                name,
                quantity,
                0,
                quantity,
                price,
                total_value
            )

    cache.invalidate()

    return True


def remove_item(
    name: str,
    quantity: int
) -> bool:

    name = standardize_name(name)

    if (
        not name
        or len(name) < 2
        or quantity <= 0
    ):
        return False

    with get_db() as conn:

        existing = conn.execute(
            """
            SELECT id, name, quantity, price
            FROM items
            WHERE name = ?
            """,
            (name,)
        ).fetchone()

        if not existing:
            return False

        current_qty = existing["quantity"]

        if quantity > current_qty:
            return False

        price = (
            existing["price"]
            if existing["price"]
            else get_realistic_price(name)
        )

        new_qty = current_qty - quantity

        total_value = price * quantity

        if new_qty <= 0:

            conn.execute(
                """
                DELETE FROM items
                WHERE name = ?
                """,
                (name,)
            )

            log_transaction(
                "delete",
                name,
                quantity,
                current_qty,
                0,
                price,
                total_value
            )

        else:

            conn.execute(
                """
                UPDATE items
                SET quantity = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE name = ?
                """,
                (
                    new_qty,
                    name
                )
            )

            log_transaction(
                "remove",
                name,
                quantity,
                current_qty,
                new_qty,
                price,
                total_value
            )

    cache.invalidate()

    return True


def update_item_price(
    name: str,
    price: float
) -> bool:

    name = standardize_name(name)

    if not name:
        return False

    if price < 0:
        return False

    with get_db() as conn:

        cursor = conn.execute(
            """
            UPDATE items
            SET price = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE name = ?
            """,
            (
                price,
                name
            )
        )

        if cursor.rowcount == 0:
            return False

    cache.invalidate()

    return True


# ============================================================
# TRANSACTION LOGGING
# ============================================================

def log_transaction(
    action: str,
    item_name: str,
    quantity: int,
    prev_qty: int = 0,
    new_qty: int = 0,
    price: float = 0,
    total_value: float = 0
):

    try:

        with get_db() as conn:

            transaction_id = generate_transaction_id()

            conn.execute(
                """
                INSERT INTO transactions
                (
                    transaction_id,
                    action,
                    item_name,
                    quantity,
                    previous_quantity,
                    new_quantity,
                    price,
                    total_value,
                    timestamp
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (
                    transaction_id,
                    action,
                    item_name,
                    quantity,
                    prev_qty,
                    new_qty,
                    price,
                    total_value
                )
            )

    except Exception as exc:

        print(
            f"[DB] Transaction logging error: {exc}"
        )


# ============================================================
# SUMMARY
# ============================================================

def get_summary_stats() -> Dict[str, Any]:

    cache_key = "summary_stats"

    cached = cache.get(cache_key)

    if cached is not None:
        return cached

    with get_db() as conn:

        stats = conn.execute(
            """
            SELECT
                COUNT(*) AS total_items,
                COALESCE(
                    SUM(quantity),
                    0
                ) AS total_quantity,
                COALESCE(
                    SUM(quantity * price),
                    0
                ) AS total_value,
                COUNT(
                    CASE
                        WHEN quantity <= 5
                        THEN 1
                    END
                ) AS low_stock_items
            FROM items
            """
        ).fetchone()

        result = {
            "total_items": stats["total_items"],
            "total_quantity": stats["total_quantity"],
            "total_value": round(
                stats["total_value"],
                2
            ),
            "low_stock_items": stats["low_stock_items"]
        }

        cache.set(
            cache_key,
            result
        )

        return result


# ============================================================
# TRANSACTION HISTORY
# ============================================================

def get_transaction_history(
    limit: int = 20
) -> List[Dict[str, Any]]:

    limit = max(
        1,
        min(int(limit), 500)
    )

    cache_key = f"transactions_{limit}"

    cached = cache.get(cache_key)

    if cached is not None:
        return cached

    with get_db() as conn:

        transactions = [
            dict(row)
            for row in conn.execute(
                """
                SELECT
                    id,
                    action,
                    item_name,
                    quantity,
                    price,
                    total_value,
                    timestamp
                FROM transactions
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (limit,)
            )
        ]

        cache.set(
            cache_key,
            transactions
        )

        return transactions


# ============================================================
# CATEGORIES
# ============================================================

def get_all_categories() -> List[str]:

    cache_key = "all_categories"

    cached = cache.get(cache_key)

    if cached is not None:
        return cached

    with get_db() as conn:

        categories = [
            row[0]
            for row in conn.execute(
                """
                SELECT DISTINCT category
                FROM items
                ORDER BY category
                """
            )
        ]

        cache.set(
            cache_key,
            categories
        )

        return categories


# ============================================================
# SEARCH
# ============================================================

def search_items(
    query: str
) -> List[Dict[str, Any]]:

    if not query or len(query.strip()) < 2:
        return get_all_items()

    query = query.strip()

    with get_db() as conn:

        rows = conn.execute(
            """
            SELECT *
            FROM items
            WHERE name LIKE ?
            ORDER BY
                CASE
                    WHEN name = ? THEN 1
                    WHEN name LIKE ? THEN 2
                    ELSE 3
                END,
                name
            """,
            (
                f"%{query}%",
                query,
                f"{query}%"
            )
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]


# ============================================================
# LOW STOCK
# ============================================================

def get_low_stock_items(
    threshold: int = 5
) -> List[Dict[str, Any]]:

    threshold = max(
        0,
        int(threshold)
    )

    cache_key = f"low_stock_{threshold}"

    cached = cache.get(cache_key)

    if cached is not None:
        return cached

    with get_db() as conn:

        items = [
            dict(row)
            for row in conn.execute(
                """
                SELECT *
                FROM items
                WHERE quantity <= ?
                ORDER BY quantity ASC
                """,
                (threshold,)
            )
        ]

        cache.set(
            cache_key,
            items
        )

        return items


# ============================================================
# TOP ITEMS
# ============================================================

def get_top_items(
    limit: int = 10
) -> List[Dict[str, Any]]:

    limit = max(
        1,
        min(int(limit), 500)
    )

    with get_db() as conn:

        return [
            dict(row)
            for row in conn.execute(
                """
                SELECT *
                FROM items
                ORDER BY
                    (quantity * price) DESC
                LIMIT ?
                """,
                (limit,)
            )
        ]


# ============================================================
# RECENT ACTIVITY
# ============================================================

def get_recent_activity(
    days: int = 7
) -> List[Dict[str, Any]]:

    days = max(
        1,
        int(days)
    )

    with get_db() as conn:

        return [
            dict(row)
            for row in conn.execute(
                """
                SELECT
                    date(timestamp) AS date,
                    COUNT(*) AS total_actions,
                    SUM(
                        CASE
                            WHEN action = 'add'
                            THEN quantity
                            ELSE 0
                        END
                    ) AS items_added,
                    SUM(
                        CASE
                            WHEN action = 'remove'
                            THEN quantity
                            ELSE 0
                        END
                    ) AS items_removed
                FROM transactions
                WHERE timestamp >= date(
                    'now',
                    ?
                )
                GROUP BY date(timestamp)
                ORDER BY date DESC
                """,
                (f"-{days} days",)
            )
        ]


# ============================================================
# BULK OPERATIONS
# ============================================================

def bulk_add_items(
    items: List[Tuple]
) -> int:

    if not items:
        return 0

    with get_db() as conn:

        conn.executemany(
            """
            INSERT OR REPLACE INTO items
            (
                name,
                quantity,
                category,
                unit,
                price,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            items
        )

    cache.invalidate()

    return len(items)


def bulk_remove_items(
    names: List[str]
) -> int:

    if not names:
        return 0

    standardized_names = [
        standardize_name(name)
        for name in names
    ]

    placeholders = ",".join(
        ["?" for _ in standardized_names]
    )

    with get_db() as conn:

        cursor = conn.execute(
            f"""
            DELETE FROM items
            WHERE name IN ({placeholders})
            """,
            standardized_names
        )

        deleted_count = cursor.rowcount

    cache.invalidate()

    return deleted_count


# ============================================================
# EXPORT - JSON
# ============================================================

def export_inventory_to_json(
    filepath: str = None
) -> str:

    items = get_all_items()

    data = {
        "export_date": datetime.now().isoformat(),
        "total_items": len(items),
        "total_quantity": sum(
            item["quantity"]
            for item in items
        ),
        "total_value": get_summary_stats()[
            "total_value"
        ],
        "inventory": items
    }

    if not filepath:

        filepath = os.path.join(
            DB_DIRECTORY,
            (
                "inventory_export_"
                f"{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                ".json"
            )
        )

    with open(
        filepath,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            indent=2,
            default=str,
            ensure_ascii=False
        )

    return filepath


# ============================================================
# EXPORT - CSV
# ============================================================

def export_inventory_to_csv(
    filepath: str = None
) -> str:

    import csv

    items = get_all_items()

    if not filepath:

        filepath = os.path.join(
            DB_DIRECTORY,
            (
                "inventory_export_"
                f"{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                ".csv"
            )
        )

    with open(
        filepath,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=[
                "name",
                "quantity",
                "category",
                "unit",
                "price",
                "total_value"
            ]
        )

        writer.writeheader()

        for item in items:

            writer.writerow({
                "name": item["name"],
                "quantity": item["quantity"],
                "category": item.get(
                    "category",
                    "general"
                ),
                "unit": item.get(
                    "unit",
                    "piece"
                ),
                "price": item.get(
                    "price",
                    0
                ),
                "total_value": (
                    item["quantity"]
                    * item.get("price", 0)
                )
            })

    return filepath


# ============================================================
# EXPORT - TXT
# ============================================================

def export_inventory_to_txt(
    filepath: str = None
) -> str:

    items = get_all_items()

    stats = get_summary_stats()

    if not filepath:

        filepath = os.path.join(
            DB_DIRECTORY,
            (
                "inventory_export_"
                f"{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                ".txt"
            )
        )

    with open(
        filepath,
        "w",
        encoding="utf-8"
    ) as file:

        file.write("=" * 60 + "\n")
        file.write(
            "SPEAK SNAP STORE - INVENTORY REPORT\n"
        )
        file.write(
            "Generated: "
            f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        )
        file.write("=" * 60 + "\n\n")

        file.write(
            "SUMMARY STATISTICS\n"
        )
        file.write("-" * 40 + "\n")

        file.write(
            f"Total Items: "
            f"{stats['total_items']}\n"
        )

        file.write(
            f"Total Units: "
            f"{stats['total_quantity']}\n"
        )

        file.write(
            f"Total Value: "
            f"₹{stats['total_value']:.2f}\n"
        )

        file.write(
            f"Low Stock Items: "
            f"{stats['low_stock_items']}\n\n"
        )

        file.write(
            "INVENTORY DETAILS\n"
        )
        file.write("-" * 40 + "\n")

        for item in items:

            file.write(
                f"\n📦 {item['name'].upper()}\n"
            )

            file.write(
                f"   Quantity: "
                f"{item['quantity']} "
                f"{item.get('unit', 'piece')}(s)\n"
            )

            file.write(
                f"   Price: "
                f"₹{item.get('price', 0):.2f} "
                "per unit\n"
            )

            file.write(
                f"   Total Value: "
                f"₹{item['quantity'] * item.get('price', 0):.2f}\n"
            )

            file.write(
                f"   Category: "
                f"{item.get('category', 'general')}\n"
            )

        file.write("\n" + "=" * 60 + "\n")
        file.write("END OF REPORT\n")
        file.write("=" * 60 + "\n")

    return filepath


# ============================================================
# HEALTH CHECK
# ============================================================

def get_db_health() -> Dict[str, Any]:
    """
    Return database health information.
    """

    with get_db() as conn:

        # Make sure the database is responsive.
        conn.execute("SELECT 1")

        db_size = (
            os.path.getsize(DB_PATH)
            if os.path.exists(DB_PATH)
            else 0
        )

        item_count = conn.execute(
            "SELECT COUNT(*) FROM items"
        ).fetchone()[0]

        transaction_count = conn.execute(
            "SELECT COUNT(*) FROM transactions"
        ).fetchone()[0]

        return {
            "status": "healthy",
            "db_size_mb": round(
                db_size / (1024 * 1024),
                2
            ),
            "item_count": item_count,
            "transaction_count": transaction_count,
            "cache_size": len(cache.cache),
            "connection_pool_size": pool.max_connections
        }


# ============================================================
# INITIALIZE DATABASE
# ============================================================

init_db()


print("=" * 50)
print("SPEAK SNAP STORE DATABASE ACTIVE")
print("=" * 50)
print(f"Database: {DB_PATH}")
print(
    f"Cache: {CACHE_SIZE} items, "
    f"TTL: {CACHE_TTL}s"
)
print(
    f"Connection Pool: "
    f"{pool.max_connections} connections"
)
print("Dynamic Pricing: Active")
print("Transaction Logging: Active")
print("Async Operations: Active")
print("=" * 50)