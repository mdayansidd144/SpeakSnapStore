import sqlite3
import os
import re

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'database', 'inventory.db')

print("=" * 50)
print("FIXING DATABASE - REMOVING BAD ENTRIES")
print("=" * 50)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Show current items
print("\nCurrent items in database:")
cursor.execute("SELECT id, name, quantity FROM items")
items = cursor.fetchall()
for id, name, qty in items:
    print(f"  ID: {id} | Name: '{name}' | Quantity: {qty}")

# Delete bad entries
cursor.execute("DELETE FROM items WHERE name LIKE '%five%' OR name LIKE '%pencils%' OR name LIKE '%seven%' OR name LIKE '%eight%' OR name LIKE '%nine%' OR name LIKE '%ten%'")
deleted_count = cursor.rowcount
conn.commit()

print(f"\n✅ Deleted {deleted_count} bad entry/entries")

# Show remaining items
print("\nRemaining items:")
cursor.execute("SELECT name, quantity FROM items ORDER BY name")
for name, qty in cursor.fetchall():
    print(f"  {name}: {qty} units")

conn.close()
print("\n" + "=" * 50)
print("DATABASE FIXED! Now restart your backend.")
print("=" * 50)