from fastapi import APIRouter, HTTPException, Query, BackgroundTasks, status
from fastapi.responses import JSONResponse, StreamingResponse
from models import (
    InventoryItem, InventoryItemUpdate, InventoryItemResponse,
    BulkAddRequest, BulkRemoveRequest, BulkOperationResult,
    PaginationParams, PaginatedResponse, ErrorResponse,
    InventoryStats, CategorySummary, TransactionResponse
)
from database import (
    get_all_items, add_item, remove_item, get_summary_stats,
    get_all_categories, search_items, get_transaction_history,
    get_low_stock_items, update_item_price, get_item_by_name,
    bulk_add_items, bulk_remove_items, get_top_items,
    get_recent_activity, get_db_health, export_inventory_to_json,
    export_inventory_to_csv, export_inventory_to_txt
)
from typing import Optional, List, Dict, Any
import logging
import asyncio
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)
router = APIRouter()

# ==================== HELPER FUNCTIONS ====================

def format_item_response(item: Dict[str, Any]) -> Dict[str, Any]:
    """Format item for consistent response"""
    return {
        "id": item.get("id"),
        "name": item.get("name"),
        "quantity": item.get("quantity", 0),
        "category": item.get("category", "general"),
        "unit": item.get("unit", "piece"),
        "price": round(item.get("price", 0), 2),
        "total_value": round(item.get("quantity", 0) * item.get("price", 0), 2),
        "created_at": item.get("created_at"),
        "updated_at": item.get("updated_at")
    }

# ==================== MAIN ENDPOINTS ====================

@router.get(
    "/",
    response_model=List[Dict[str, Any]],
    summary="Get all inventory items",
    description="Returns a list of all items in the inventory with their details"
)
async def get_inventory(
    limit: Optional[int] = Query(None, ge=1, le=500, description="Maximum number of items to return"),
    offset: Optional[int] = Query(0, ge=0, description="Number of items to skip")
):
    """Get all inventory items with optional pagination"""
    try:
        items = get_all_items()
        
        if limit:
            items = items[offset:offset + limit]
        elif offset:
            items = items[offset:]
        
        return [format_item_response(item) for item in items]
    except Exception as e:
        logger.error(f"Error in get_inventory: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch inventory"
        )

@router.get(
    "/stats",
    response_model=InventoryStats,
    summary="Get inventory statistics",
    description="Returns comprehensive statistics about the inventory"
)
async def get_stats():
    """Get inventory statistics"""
    try:
        stats = get_summary_stats()
        items = get_all_items()
        
        # Calculate additional stats
        if items:
            avg_price = sum(item.get('price', 0) for item in items) / len(items)
            most_expensive = max(items, key=lambda x: x.get('price', 0))
            most_plentiful = max(items, key=lambda x: x.get('quantity', 0))
            
            return InventoryStats(
                total_items=stats['total_items'],
                total_quantity=stats['total_quantity'],
                total_value=stats['total_value'],
                low_stock_items=stats['low_stock_items'],
                average_price=round(avg_price, 2),
                most_expensive_item=most_expensive.get('name'),
                most_plentiful_item=most_plentiful.get('name')
            )
        
        return InventoryStats(
            total_items=stats['total_items'],
            total_quantity=stats['total_quantity'],
            total_value=stats['total_value'],
            low_stock_items=stats['low_stock_items']
        )
    except Exception as e:
        logger.error(f"Error in get_stats: {e}")
        return InventoryStats()

@router.get(
    "/categories",
    response_model=List[str],
    summary="Get all categories",
    description="Returns a list of all unique categories"
)
async def get_categories():
    """Get all unique categories"""
    try:
        return get_all_categories()
    except Exception as e:
        logger.error(f"Error in get_categories: {e}")
        return []

@router.get(
    "/categories/summary",
    response_model=List[CategorySummary],
    summary="Get category summary",
    description="Returns summary statistics for each category"
)
async def get_category_summary():
    """Get category-wise summary"""
    try:
        items = get_all_items()
        categories = {}
        
        for item in items:
            cat = item.get('category', 'general')
            if cat not in categories:
                categories[cat] = {
                    'item_count': 0,
                    'total_quantity': 0,
                    'total_value': 0
                }
            categories[cat]['item_count'] += 1
            categories[cat]['total_quantity'] += item.get('quantity', 0)
            categories[cat]['total_value'] += item.get('quantity', 0) * item.get('price', 0)
        
        return [
            CategorySummary(
                category=cat,
                item_count=data['item_count'],
                total_quantity=data['total_quantity'],
                total_value=round(data['total_value'], 2)
            )
            for cat, data in categories.items()
        ]
    except Exception as e:
        logger.error(f"Error in get_category_summary: {e}")
        return []

@router.get(
    "/transactions",
    response_model=List[TransactionResponse],
    summary="Get transaction history",
    description="Returns recent transaction history"
)
async def get_transactions(
    limit: int = Query(20, ge=1, le=100, description="Number of transactions to return"),
    item_name: Optional[str] = Query(None, description="Filter by item name")
):
    """Get recent transaction history"""
    try:
        transactions = get_transaction_history(limit * 2)  # Get extra for filtering
        
        if item_name:
            transactions = [t for t in transactions if t.get('item_name', '').lower() == item_name.lower()]
        
        # Format transactions
        formatted = []
        for txn in transactions[:limit]:
            formatted.append(TransactionResponse(
                id=txn.get('id'),
                action=txn.get('action'),
                item_name=txn.get('item_name'),
                quantity=txn.get('quantity'),
                timestamp=txn.get('timestamp')
            ))
        
        return formatted
    except Exception as e:
        logger.error(f"Error in get_transactions: {e}")
        return []

@router.get(
    "/low-stock",
    response_model=List[Dict[str, Any]],
    summary="Get low stock items",
    description="Returns items with quantity below threshold"
)
async def get_low_stock(
    threshold: int = Query(5, ge=1, le=50, description="Stock threshold")
):
    """Get items that need restocking"""
    try:
        items = get_low_stock_items()
        # Filter by custom threshold
        items = [item for item in items if item.get('quantity', 0) <= threshold]
        return [format_item_response(item) for item in items]
    except Exception as e:
        logger.error(f"Error in get_low_stock: {e}")
        return []

@router.get(
    "/top",
    response_model=List[Dict[str, Any]],
    summary="Get top items by value",
    description="Returns top N items by total value"
)
async def get_top(
    limit: int = Query(10, ge=1, le=50, description="Number of top items to return")
):
    """Get top items by total value"""
    try:
        items = get_top_items(limit)
        return [format_item_response(item) for item in items]
    except Exception as e:
        logger.error(f"Error in get_top: {e}")
        return []

@router.get(
    "/activity",
    summary="Get recent activity",
    description="Returns activity summary for the last N days"
)
async def get_activity(
    days: int = Query(7, ge=1, le=30, description="Number of days to analyze")
):
    """Get recent activity summary"""
    try:
        return get_recent_activity(days)
    except Exception as e:
        logger.error(f"Error in get_activity: {e}")
        return []

@router.get(
    "/search",
    response_model=List[Dict[str, Any]],
    summary="Search items",
    description="Search inventory items by name"
)
async def search(
    query: str = Query(..., min_length=1, max_length=100, description="Search query"),
    limit: int = Query(50, ge=1, le=200, description="Maximum results")
):
    """Search items by name"""
    try:
        items = search_items(query)
        return [format_item_response(item) for item in items[:limit]]
    except Exception as e:
        logger.error(f"Error in search: {e}")
        return []

# ==================== CREATE, UPDATE, DELETE OPERATIONS ====================

@router.post(
    "/add",
    status_code=status.HTTP_201_CREATED,
    summary="Add item to inventory",
    description="Add a new item or increase quantity of existing item"
)
async def add_inventory_item(
    item: InventoryItem,
    background_tasks: BackgroundTasks
):
    """Add item to inventory"""
    if item.quantity <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quantity must be positive"
        )
    
    if item.price < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Price cannot be negative"
        )
    
    result = add_item(
        item.name.lower(),
        item.quantity,
        item.category,
        item.unit,
        item.price
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to add item. Please check the item name."
        )
    
    # Refresh cache in background
    background_tasks.add_task(lambda: None)  # Placeholder for cache refresh
    
    return {
        "success": True,
        "message": f"Added {item.quantity} {item.name}(s)",
        "item": item.name,
        "quantity": item.quantity
    }

@router.post(
    "/remove",
    summary="Remove item from inventory",
    description="Remove quantity from an existing item"
)
async def remove_inventory_item(item: InventoryItem):
    """Remove item from inventory"""
    if item.quantity <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quantity must be positive"
        )
    
    # Check if item exists
    existing = get_item_by_name(item.name)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item '{item.name}' not found in inventory"
        )
    
    if existing['quantity'] < item.quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot remove {item.quantity} {item.name}(s). Only {existing['quantity']} available."
        )
    
    result = remove_item(item.name.lower(), item.quantity)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to remove item"
        )
    
    return {
        "success": True,
        "message": f"Removed {item.quantity} {item.name}(s)",
        "remaining_quantity": existing['quantity'] - item.quantity
    }

@router.put(
    "/update/{name}",
    summary="Update item",
    description="Update item properties (price, category, unit)"
)
async def update_item(
    name: str,
    updates: InventoryItemUpdate
):
    """Update item properties"""
    existing = get_item_by_name(name)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item '{name}' not found"
        )
    
    updated_fields = []
    
    if updates.price is not None:
        update_item_price(name, updates.price)
        updated_fields.append(f"price to ₹{updates.price}")
    
    # Add more update fields as needed
    
    if not updated_fields:
        return {"success": True, "message": "No updates applied"}
    
    return {
        "success": True,
        "message": f"Updated {name}: {', '.join(updated_fields)}"
    }

@router.delete(
    "/delete/{name}",
    summary="Delete item",
    description="Completely delete an item from inventory"
)
async def delete_item(name: str):
    """Delete an item completely"""
    existing = get_item_by_name(name)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item '{name}' not found"
        )
    
    result = remove_item(name, existing['quantity'])
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to delete item"
        )
    
    return {
        "success": True,
        "message": f"Deleted item '{name}' completely"
    }

# ==================== BULK OPERATIONS ====================

@router.post(
    "/bulk/add",
    response_model=BulkOperationResult,
    summary="Bulk add items",
    description="Add multiple items at once"
)
async def bulk_add_items_endpoint(request: BulkAddRequest):
    """Add multiple items in one request"""
    try:
        items = [(item.name, item.quantity, item.category, item.unit, item.price) for item in request.items]
        success_count = bulk_add_items(items)
        
        return BulkOperationResult(
            total=len(request.items),
            success_count=success_count,
            failed_count=len(request.items) - success_count,
            failed_items=[],
            message=f"Successfully added {success_count} of {len(request.items)} items"
        )
    except Exception as e:
        logger.error(f"Error in bulk add: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Bulk add operation failed"
        )

@router.post(
    "/bulk/remove",
    response_model=BulkOperationResult,
    summary="Bulk remove items",
    description="Remove multiple items at once"
)
async def bulk_remove_items_endpoint(request: BulkRemoveRequest):
    """Remove multiple items in one request"""
    try:
        success_count = bulk_remove_items(request.items)
        
        return BulkOperationResult(
            total=len(request.items),
            success_count=success_count,
            failed_count=len(request.items) - success_count,
            failed_items=[],
            message=f"Successfully removed {success_count} of {len(request.items)} items"
        )
    except Exception as e:
        logger.error(f"Error in bulk remove: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Bulk remove operation failed"
        )

# ==================== EXPORT ENDPOINTS ====================

@router.get("/export/json", summary="Export inventory to JSON")
async def export_json():
    """Export inventory as JSON file"""
    try:
        filepath = export_inventory_to_json()
        return {"success": True, "filepath": filepath, "format": "json"}
    except Exception as e:
        logger.error(f"Export error: {e}")
        raise HTTPException(status_code=500, detail="Export failed")

@router.get("/export/csv", summary="Export inventory to CSV")
async def export_csv():
    """Export inventory as CSV file"""
    try:
        filepath = export_inventory_to_csv()
        return {"success": True, "filepath": filepath, "format": "csv"}
    except Exception as e:
        logger.error(f"Export error: {e}")
        raise HTTPException(status_code=500, detail="Export failed")

@router.get("/export/txt", summary="Export inventory to TXT")
async def export_txt():
    """Export inventory as TXT file"""
    try:
        filepath = export_inventory_to_txt()
        return {"success": True, "filepath": filepath, "format": "txt"}
    except Exception as e:
        logger.error(f"Export error: {e}")
        raise HTTPException(status_code=500, detail="Export failed")

@router.get("/export/all", summary="Export inventory to all formats")
async def export_all():
    """Export inventory in all formats"""
    try:
        json_path = export_inventory_to_json()
        csv_path = export_inventory_to_csv()
        txt_path = export_inventory_to_txt()
        
        return {
            "success": True,
            "files": {
                "json": json_path,
                "csv": csv_path,
                "txt": txt_path
            }
        }
    except Exception as e:
        logger.error(f"Export error: {e}")
        raise HTTPException(status_code=500, detail="Export failed")

# ==================== HEALTH & TEST ENDPOINTS ====================

@router.get("/health/db", summary="Database health check")
async def db_health():
    """Check database health"""
    try:
        health = get_db_health()
        return health
    except Exception as e:
        logger.error(f"DB health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}

@router.get("/test", summary="Test endpoint")
async def test():
    """Test endpoint to verify API is working"""
    try:
        items = get_all_items()
        return {
            "status": "ok",
            "message": "Inventory API is working",
            "item_count": len(items),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Test endpoint error: {e}")
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }

# ==================== PAGINATED LIST ====================

@router.get(
    "/paginated",
    response_model=PaginatedResponse,
    summary="Get paginated inventory",
    description="Returns paginated list of inventory items"
)
async def get_paginated_inventory(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    sort_by: Optional[str] = Query(None, description="Sort field (name, quantity, price)"),
    sort_order: str = Query("asc", regex="^(asc|desc)$", description="Sort order")
):
    """Get paginated inventory items"""
    try:
        items = get_all_items()
        
        # Sort if requested
        if sort_by and sort_by in ['name', 'quantity', 'price']:
            reverse = sort_order == 'desc'
            items.sort(key=lambda x: x.get(sort_by, 0), reverse=reverse)
        
        total = len(items)
        start = (page - 1) * per_page
        end = start + per_page
        paginated_items = items[start:end]
        
        return PaginatedResponse(
            items=[format_item_response(item) for item in paginated_items],
            total=total,
            page=page,
            per_page=per_page
        )
    except Exception as e:
        logger.error(f"Error in paginated inventory: {e}")
        return PaginatedResponse(
            items=[],
            total=0,
            page=page,
            per_page=per_page
        )