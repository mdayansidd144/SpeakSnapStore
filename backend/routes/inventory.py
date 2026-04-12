# from fastapi import APIRouter, HTTPException, Query, Response
# from models import InventoryItem
# from database import (
#     get_all_items, add_item, remove_item, get_summary_stats,
#     get_all_categories, search_items, get_transaction_history,
#     export_inventory_to_json, export_inventory_to_csv, export_inventory_to_txt,
#     update_item_price
# )
# from typing import Optional
# import json

# router = APIRouter()

# @router.get("/")
# async def get_inventory():
#     """Get all inventory items with values"""
#     try:
#         return get_all_items()
#     except Exception as e:
#         print(f"Error: {e}")
#         return []

# @router.get("/stats")
# async def get_stats():
#     """Get inventory statistics"""
#     try:
#         return get_summary_stats()
#     except Exception as e:
#         print(f"Error: {e}")
#         return {"total_items": 0, "total_quantity": 0, "total_value": 0}

# @router.get("/categories")
# async def get_categories():
#     """Get all categories"""
#     try:
#         return get_all_categories()
#     except Exception as e:
#         return []

# @router.get("/transactions")
# async def get_transactions(limit: int = 50):
#     """Get recent transaction history"""
#     try:
#         return get_transaction_history(limit)
#     except Exception as e:
#         return []

# @router.get("/search")
# async def search(query: str = Query(..., min_length=1)):
#     """Search items by name"""
#     try:
#         return search_items(query)
#     except Exception as e:
#         return []

# @router.post("/add")
# async def add_inventory_item(item: InventoryItem):
#     """Add item to inventory"""
#     if item.quantity <= 0:
#         raise HTTPException(status_code=400, detail="Quantity must be positive")
    
#     result = add_item(item.name.lower(), item.quantity, item.category, item.unit, item.price)
    
#     if result:
#         return {"success": True, "message": f"Added {item.quantity} {item.name}(s)"}
#     raise HTTPException(status_code=400, detail="Failed to add item")

# @router.post("/remove")
# async def remove_inventory_item(item: InventoryItem):
#     """Remove item from inventory"""
#     if item.quantity <= 0:
#         raise HTTPException(status_code=400, detail="Quantity must be positive")
    
#     result = remove_item(item.name.lower(), item.quantity)
    
#     if result:
#         return {"success": True, "message": f"Removed {item.quantity} {item.name}(s)"}
#     raise HTTPException(status_code=404, detail=f"Item '{item.name}' not found")

# @router.put("/price/{name}")
# async def update_price(name: str, price: float):
#     """Update item price"""
#     result = update_item_price(name, price)
#     if result:
#         return {"success": True, "message": f"Updated price for {name} to ₹{price}"}
#     raise HTTPException(status_code=404, detail="Item not found")

# # ==================== EXPORT ENDPOINTS ====================

# @router.get("/export/json")
# async def export_json():
#     """Export inventory to JSON file"""
#     try:
#         filepath = export_inventory_to_json()
#         return {"success": True, "filepath": filepath, "format": "json"}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

# @router.get("/export/csv")
# async def export_csv():
#     """Export inventory to CSV file"""
#     try:
#         filepath = export_inventory_to_csv()
#         return {"success": True, "filepath": filepath, "format": "csv"}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

# @router.get("/export/txt")
# async def export_txt():
#     """Export inventory to TXT file"""
#     try:
#         filepath = export_inventory_to_txt()
#         return {"success": True, "filepath": filepath, "format": "txt"}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

# @router.get("/export/all")
# async def export_all_formats():
#     """Export inventory in all formats"""
#     try:
#         json_path = export_inventory_to_json()
#         csv_path = export_inventory_to_csv()
#         txt_path = export_inventory_to_txt()
#         return {
#             "success": True,
#             "files": {
#                 "json": json_path,
#                 "csv": csv_path,
#                 "txt": txt_path
#             }
#         }
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")
from fastapi import APIRouter, HTTPException, Query, Response
from models import InventoryItem
from database import (
    get_all_items, add_item, remove_item, get_summary_stats,
    get_all_categories, search_items, get_transaction_history,
    update_item_price
)
from typing import Optional
import json
import csv
from io import StringIO
from datetime import datetime

router = APIRouter()

@router.get("/")
async def get_inventory():
    """Get all inventory items with values"""
    try:
        return get_all_items()
    except Exception as e:
        print(f"Error: {e}")
        return []

@router.get("/stats")
async def get_stats():
    """Get inventory statistics"""
    try:
        return get_summary_stats()
    except Exception as e:
        print(f"Error: {e}")
        return {"total_items": 0, "total_quantity": 0, "total_value": 0}

@router.get("/categories")
async def get_categories():
    """Get all categories"""
    try:
        return get_all_categories()
    except Exception as e:
        return []

@router.get("/transactions")
async def get_transactions(limit: int = 50):
    """Get recent transaction history"""
    try:
        return get_transaction_history(limit)
    except Exception as e:
        return []

@router.get("/search")
async def search(query: str = Query(..., min_length=1)):
    """Search items by name"""
    try:
        return search_items(query)
    except Exception as e:
        return []

@router.post("/add")
async def add_inventory_item(item: InventoryItem):
    """Add item to inventory"""
    if item.quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be positive")
    
    result = add_item(item.name.lower(), item.quantity, item.category, item.unit, item.price)
    
    if result:
        return {"success": True, "message": f"Added {item.quantity} {item.name}(s)"}
    raise HTTPException(status_code=400, detail="Failed to add item")

@router.post("/remove")
async def remove_inventory_item(item: InventoryItem):
    """Remove item from inventory"""
    if item.quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be positive")
    
    result = remove_item(item.name.lower(), item.quantity)
    
    if result:
        return {"success": True, "message": f"Removed {item.quantity} {item.name}(s)"}
    raise HTTPException(status_code=404, detail=f"Item '{item.name}' not found")

@router.put("/price/{name}")
async def update_price(name: str, price: float):
    """Update item price"""
    result = update_item_price(name, price)
    if result:
        return {"success": True, "message": f"Updated price for {name} to ₹{price}"}
    raise HTTPException(status_code=404, detail="Item not found")

# ==================== EXPORT ENDPOINTS (FIXED) ====================

@router.get("/export/json")
async def export_json():
    """Export inventory to JSON - FIXED: Returns data directly"""
    try:
        items = get_all_items()
        return Response(
            content=json.dumps(items, indent=2, default=str),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=inventory.json"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

@router.get("/export/csv")
async def export_csv():
    """Export inventory to CSV - FIXED: Returns data directly"""
    try:
        items = get_all_items()
        output = StringIO()
        writer = csv.writer(output)
        
        # Write headers
        writer.writerow(['Name', 'Quantity', 'Unit', 'Category', 'Price (₹)', 'Total Value (₹)'])
        
        # Write data
        for item in items:
            writer.writerow([
                item['name'], 
                item['quantity'], 
                item.get('unit', 'piece'),
                item.get('category', 'general'), 
                item.get('price', 0),
                item['quantity'] * item.get('price', 0)
            ])
        
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=inventory.csv"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

@router.get("/export/txt")
async def export_txt():
    """Export inventory to TXT - FIXED: Returns data directly"""
    try:
        items = get_all_items()
        output = []
        
        # Header
        output.append("=" * 60)
        output.append("SPEAK SNAP STORE - INVENTORY REPORT")
        output.append(f"Export Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        output.append("=" * 60)
        output.append("")
        
        # Items
        for item in items:
            output.append(f"📦 {item['name'].upper()}")
            output.append(f"   Quantity: {item['quantity']} {item.get('unit', 'piece')}(s)")
            output.append(f"   Price: ₹{item.get('price', 0):.2f} per {item.get('unit', 'piece')}")
            output.append(f"   Total Value: ₹{item['quantity'] * item.get('price', 0):.2f}")
            output.append(f"   Category: {item.get('category', 'general')}")
            output.append("-" * 40)
        
        # Summary
        output.append("")
        output.append("=" * 60)
        output.append("SUMMARY")
        output.append(f"Total Items: {len(items)}")
        output.append(f"Total Quantity: {sum(i['quantity'] for i in items)}")
        output.append(f"Total Inventory Value: ₹{sum(i['quantity'] * i.get('price', 0) for i in items):.2f}")
        output.append("=" * 60)
        
        return Response(
            content="\n".join(output),
            media_type="text/plain",
            headers={"Content-Disposition": "attachment; filename=inventory.txt"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

@router.get("/export/all")
async def export_all_formats():
    """Export inventory in all formats - FIXED: Returns all data"""
    try:
        items = get_all_items()
        
        # JSON
        json_data = json.dumps(items, indent=2, default=str)
        
        # CSV
        csv_output = StringIO()
        writer = csv.writer(csv_output)
        writer.writerow(['Name', 'Quantity', 'Unit', 'Category', 'Price (₹)', 'Total Value (₹)'])
        for item in items:
            writer.writerow([
                item['name'], item['quantity'], item.get('unit', 'piece'),
                item.get('category', 'general'), item.get('price', 0),
                item['quantity'] * item.get('price', 0)
            ])
        csv_data = csv_output.getvalue()
        
        # TXT
        txt_lines = []
        txt_lines.append("=" * 60)
        txt_lines.append("SPEAK SNAP STORE - INVENTORY REPORT")
        txt_lines.append(f"Export Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        txt_lines.append("=" * 60)
        txt_lines.append("")
        for item in items:
            txt_lines.append(f"📦 {item['name'].upper()}")
            txt_lines.append(f"   Quantity: {item['quantity']} {item.get('unit', 'piece')}(s)")
            txt_lines.append(f"   Price: ₹{item.get('price', 0):.2f}")
            txt_lines.append(f"   Total Value: ₹{item['quantity'] * item.get('price', 0):.2f}")
            txt_lines.append("-" * 40)
        txt_lines.append("")
        txt_lines.append("=" * 60)
        txt_lines.append(f"Total Items: {len(items)}")
        txt_lines.append(f"Total Quantity: {sum(i['quantity'] for i in items)}")
        txt_lines.append(f"Total Value: ₹{sum(i['quantity'] * i.get('price', 0) for i in items):.2f}")
        txt_lines.append("=" * 60)
        txt_data = "\n".join(txt_lines)
        
        return {
            "success": True,
            "data": {
                "json": json_data,
                "csv": csv_data,
                "txt": txt_data
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")