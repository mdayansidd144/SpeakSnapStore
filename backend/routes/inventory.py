from fastapi import (
    APIRouter,
    HTTPException,
    Query,
    status
)

from models import (
    InventoryItem,
    InventoryItemUpdate,
    BulkAddRequest,
    BulkRemoveRequest,
    BulkOperationResult,
    PaginationParams,
    PaginatedResponse,
    ErrorResponse,
    InventoryStats,
    CategorySummary,
    TransactionResponse
)

from database import (
    get_all_items,
    add_item,
    remove_item,
    get_summary_stats,
    get_all_categories,
    search_items,
    get_transaction_history,
    get_low_stock_items,
    update_item_price,
    get_item_by_name,
    bulk_add_items,
    bulk_remove_items,
    get_top_items,
    get_recent_activity,
    get_db_health,
    export_inventory_to_json,
    export_inventory_to_csv,
    export_inventory_to_txt,
    standardize_name,
    get_db
)

from typing import Optional, List, Dict, Any
import logging
from datetime import datetime


# ============================================================
# ROUTER
# ============================================================

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def format_item_response(
    item: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Format an inventory item into a consistent API response.
    """

    quantity = item.get("quantity", 0) or 0
    price = item.get("price", 0) or 0

    return {
        "id": item.get("id"),
        "name": item.get("name"),
        "quantity": quantity,
        "category": item.get(
            "category",
            "general"
        ),
        "unit": item.get(
            "unit",
            "piece"
        ),
        "price": round(
            float(price),
            2
        ),
        "total_value": round(
            float(quantity) * float(price),
            2
        ),
        "created_at": item.get(
            "created_at"
        ),
        "updated_at": item.get(
            "updated_at"
        )
    }


# ============================================================
# GET ALL INVENTORY
# ============================================================

@router.get(
    "/",
    response_model=List[Dict[str, Any]],
    summary="Get all inventory items",
    description=(
        "Returns a list of all items in the inventory "
        "with their details"
    )
)
async def get_inventory(
    limit: Optional[int] = Query(
        None,
        ge=1,
        le=500,
        description="Maximum number of items to return"
    ),
    offset: int = Query(
        0,
        ge=0,
        description="Number of items to skip"
    )
):

    try:

        items = get_all_items()

        if limit is not None:
            items = items[
                offset:offset + limit
            ]

        elif offset:
            items = items[offset:]

        return [
            format_item_response(item)
            for item in items
        ]

    except Exception as exc:

        logger.exception(
            "Error fetching inventory: %s",
            exc
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch inventory"
        )


# ============================================================
# STATISTICS
# ============================================================

@router.get(
    "/stats",
    response_model=InventoryStats,
    summary="Get inventory statistics",
    description=(
        "Returns comprehensive statistics "
        "about the inventory"
    )
)
async def get_stats():

    try:

        stats = get_summary_stats()
        items = get_all_items()

        if not items:

            return InventoryStats(
                total_items=stats["total_items"],
                total_quantity=stats["total_quantity"],
                total_value=stats["total_value"],
                low_stock_items=stats["low_stock_items"]
            )

        avg_price = (
            sum(
                float(item.get("price", 0) or 0)
                for item in items
            )
            / len(items)
        )

        most_expensive = max(
            items,
            key=lambda item:
                float(
                    item.get("price", 0) or 0
                )
        )

        most_plentiful = max(
            items,
            key=lambda item:
                int(
                    item.get("quantity", 0) or 0
                )
        )

        return InventoryStats(
            total_items=stats["total_items"],
            total_quantity=stats["total_quantity"],
            total_value=stats["total_value"],
            low_stock_items=stats["low_stock_items"],
            average_price=round(
                avg_price,
                2
            ),
            most_expensive_item=most_expensive.get(
                "name"
            ),
            most_plentiful_item=most_plentiful.get(
                "name"
            )
        )

    except Exception as exc:

        logger.exception(
            "Error getting inventory statistics: %s",
            exc
        )

        raise HTTPException(
            status_code=500,
            detail="Failed to calculate inventory statistics"
        )


# ============================================================
# CATEGORIES
# ============================================================

@router.get(
    "/categories",
    response_model=List[str],
    summary="Get all categories",
    description="Returns a list of all unique categories"
)
async def get_categories():

    try:
        return get_all_categories()

    except Exception as exc:

        logger.exception(
            "Error getting categories: %s",
            exc
        )

        return []


# ============================================================
# CATEGORY SUMMARY
# ============================================================

@router.get(
    "/categories/summary",
    response_model=List[CategorySummary],
    summary="Get category summary",
    description=(
        "Returns summary statistics "
        "for each category"
    )
)
async def get_category_summary():

    try:

        items = get_all_items()

        categories = {}

        for item in items:

            category = item.get(
                "category",
                "general"
            )

            if category not in categories:

                categories[category] = {
                    "item_count": 0,
                    "total_quantity": 0,
                    "total_value": 0.0
                }

            quantity = int(
                item.get("quantity", 0) or 0
            )

            price = float(
                item.get("price", 0) or 0
            )

            categories[category][
                "item_count"
            ] += 1

            categories[category][
                "total_quantity"
            ] += quantity

            categories[category][
                "total_value"
            ] += quantity * price

        return [
            CategorySummary(
                category=category,
                item_count=data["item_count"],
                total_quantity=data[
                    "total_quantity"
                ],
                total_value=round(
                    data["total_value"],
                    2
                )
            )
            for category, data
            in sorted(categories.items())
        ]

    except Exception as exc:

        logger.exception(
            "Error getting category summary: %s",
            exc
        )

        return []


# ============================================================
# TRANSACTIONS
# ============================================================

@router.get(
    "/transactions",
    response_model=List[TransactionResponse],
    summary="Get transaction history",
    description="Returns recent transaction history"
)
async def get_transactions(
    limit: int = Query(
        20,
        ge=1,
        le=100,
        description="Number of transactions to return"
    ),
    item_name: Optional[str] = Query(
        None,
        max_length=100,
        description="Filter by item name"
    )
):

    try:

        transactions = get_transaction_history(
            limit * 2
        )

        if item_name:

            normalized_name = standardize_name(
                item_name
            )

            transactions = [
                transaction
                for transaction in transactions
                if standardize_name(
                    transaction.get(
                        "item_name",
                        ""
                    )
                ) == normalized_name
            ]

        formatted = []

        for transaction in transactions[:limit]:

            formatted.append(
                TransactionResponse(
                    id=transaction.get("id"),
                    action=transaction.get(
                        "action"
                    ),
                    item_name=transaction.get(
                        "item_name"
                    ),
                    quantity=transaction.get(
                        "quantity",
                        0
                    ),
                    price=float(
                        transaction.get(
                            "price",
                            0
                        ) or 0
                    ),
                    total_value=float(
                        transaction.get(
                            "total_value",
                            0
                        ) or 0
                    ),
                    timestamp=transaction.get(
                        "timestamp"
                    ),
                    formatted_action=""
                )
            )

        return formatted

    except Exception as exc:

        logger.exception(
            "Error getting transactions: %s",
            exc
        )

        return []


# ============================================================
# LOW STOCK
# ============================================================

@router.get(
    "/low-stock",
    response_model=List[Dict[str, Any]],
    summary="Get low stock items",
    description=(
        "Returns items with quantity "
        "at or below the threshold"
    )
)
async def get_low_stock(
    threshold: int = Query(
        5,
        ge=1,
        le=100000,
        description="Stock threshold"
    )
):

    try:

        # IMPORTANT:
        # Pass the requested threshold to the database.
        items = get_low_stock_items(
            threshold
        )

        return [
            format_item_response(item)
            for item in items
        ]

    except Exception as exc:

        logger.exception(
            "Error getting low stock items: %s",
            exc
        )

        return []


# ============================================================
# TOP ITEMS
# ============================================================

@router.get(
    "/top",
    response_model=List[Dict[str, Any]],
    summary="Get top items by value",
    description=(
        "Returns top N items "
        "by total inventory value"
    )
)
async def get_top(
    limit: int = Query(
        10,
        ge=1,
        le=100,
        description="Number of top items to return"
    )
):

    try:

        items = get_top_items(limit)

        return [
            format_item_response(item)
            for item in items
        ]

    except Exception as exc:

        logger.exception(
            "Error getting top items: %s",
            exc
        )

        return []


# ============================================================
# RECENT ACTIVITY
# ============================================================

@router.get(
    "/activity",
    summary="Get recent activity",
    description=(
        "Returns activity summary "
        "for the last N days"
    )
)
async def get_activity(
    days: int = Query(
        7,
        ge=1,
        le=365,
        description="Number of days to analyze"
    )
):

    try:
        return get_recent_activity(days)

    except Exception as exc:

        logger.exception(
            "Error getting recent activity: %s",
            exc
        )

        return []


# ============================================================
# SEARCH
# ============================================================

@router.get(
    "/search",
    response_model=List[Dict[str, Any]],
    summary="Search items",
    description="Search inventory items by name"
)
async def search(
    query: str = Query(
        ...,
        min_length=1,
        max_length=100,
        description="Search query"
    ),
    limit: int = Query(
        50,
        ge=1,
        le=200,
        description="Maximum results"
    )
):

    try:

        items = search_items(query)

        return [
            format_item_response(item)
            for item in items[:limit]
        ]

    except Exception as exc:

        logger.exception(
            "Error searching inventory: %s",
            exc
        )

        return []


# ============================================================
# ADD ITEM
# ============================================================

@router.post(
    "/add",
    status_code=status.HTTP_201_CREATED,
    summary="Add item to inventory",
    description=(
        "Add a new item or increase "
        "quantity of an existing item"
    )
)
async def add_inventory_item(
    item: InventoryItem
):

    if item.quantity <= 0:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quantity must be positive"
        )

    price = (
        item.price
        if item.price is not None
        else 0.0
    )

    if price < 0:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Price cannot be negative"
        )

    try:

        result = add_item(
            item.name,
            item.quantity,
            item.category or "general",
            item.unit or "piece",
            price
        )

        if not result:

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Failed to add item. "
                    "Please check the item name."
                )
            )

        updated_item = get_item_by_name(
            item.name
        )

        return {
            "success": True,
            "message": (
                f"Added {item.quantity} "
                f"{item.name}(s)"
            ),
            "item": (
                format_item_response(
                    updated_item
                )
                if updated_item
                else item.name
            )
        }

    except HTTPException:
        raise

    except Exception as exc:

        logger.exception(
            "Error adding item: %s",
            exc
        )

        raise HTTPException(
            status_code=500,
            detail="Failed to add item"
        )


# ============================================================
# REMOVE ITEM
# ============================================================

@router.post(
    "/remove",
    summary="Remove item from inventory",
    description=(
        "Remove quantity from "
        "an existing item"
    )
)
async def remove_inventory_item(
    item: InventoryItem
):

    if item.quantity <= 0:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quantity must be positive"
        )

    try:

        existing = get_item_by_name(
            item.name
        )

        if not existing:

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    f"Item '{item.name}' "
                    "not found in inventory"
                )
            )

        available_quantity = int(
            existing.get(
                "quantity",
                0
            )
        )

        if available_quantity < item.quantity:

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Cannot remove "
                    f"{item.quantity} "
                    f"{item.name}(s). "
                    f"Only "
                    f"{available_quantity} "
                    "available."
                )
            )

        result = remove_item(
            item.name,
            item.quantity
        )

        if not result:

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to remove item"
            )

        remaining_quantity = (
            available_quantity
            - item.quantity
        )

        return {
            "success": True,
            "message": (
                f"Removed {item.quantity} "
                f"{item.name}(s)"
            ),
            "remaining_quantity":
                remaining_quantity
        }

    except HTTPException:
        raise

    except Exception as exc:

        logger.exception(
            "Error removing item: %s",
            exc
        )

        raise HTTPException(
            status_code=500,
            detail="Failed to remove item"
        )


# ============================================================
# UPDATE ITEM
# ============================================================

@router.put(
    "/update/{name}",
    summary="Update item",
    description=(
        "Update item properties "
        "such as price, category, unit "
        "or quantity"
    )
)
async def update_item(
    name: str,
    updates: InventoryItemUpdate
):

    normalized_name = standardize_name(
        name
    )

    existing = get_item_by_name(
        normalized_name
    )

    if not existing:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Item '{name}' "
                "not found"
            )
        )

    updated_fields = []

    try:

        # ----------------------------------------------------
        # PRICE
        # ----------------------------------------------------

        if updates.price is not None:

            if updates.price < 0:

                raise HTTPException(
                    status_code=400,
                    detail="Price cannot be negative"
                )

            if update_item_price(
                normalized_name,
                updates.price
            ):

                updated_fields.append(
                    f"price to ₹{updates.price}"
                )

        # ----------------------------------------------------
        # OTHER FIELDS
        # ----------------------------------------------------

        if (
            updates.quantity is not None
            or updates.category is not None
            or updates.unit is not None
            or updates.name is not None
        ):

            fields = []
            values = []

            if updates.quantity is not None:

                fields.append(
                    "quantity = ?"
                )

                values.append(
                    updates.quantity
                )

                updated_fields.append(
                    f"quantity to {updates.quantity}"
                )

            if updates.category is not None:

                fields.append(
                    "category = ?"
                )

                values.append(
                    updates.category
                )

                updated_fields.append(
                    f"category to {updates.category}"
                )

            if updates.unit is not None:

                fields.append(
                    "unit = ?"
                )

                values.append(
                    updates.unit
                )

                updated_fields.append(
                    f"unit to {updates.unit}"
                )

            # Renaming an item needs special handling because
            # name is UNIQUE.
            if updates.name is not None:

                new_name = standardize_name(
                    updates.name
                )

                if new_name != normalized_name:

                    duplicate = get_item_by_name(
                        new_name
                    )

                    if duplicate:

                        raise HTTPException(
                            status_code=409,
                            detail=(
                                f"Item '{new_name}' "
                                "already exists"
                            )
                        )

                    fields.append(
                        "name = ?"
                    )

                    values.append(
                        new_name
                    )

                    updated_fields.append(
                        f"name to {new_name}"
                    )

            if fields:

                fields.append(
                    "updated_at = CURRENT_TIMESTAMP"
                )

                values.append(
                    normalized_name
                )

                with get_db() as conn:

                    conn.execute(
                        f"""
                        UPDATE items
                        SET {", ".join(fields)}
                        WHERE name = ?
                        """,
                        values
                    )

        # ----------------------------------------------------
        # RESULT
        # ----------------------------------------------------

        if not updated_fields:

            return {
                "success": True,
                "message": "No updates applied"
            }

        # Clear cache because we changed the database.
        from database import cache
        cache.invalidate()

        final_name = (
            standardize_name(
                updates.name
            )
            if updates.name
            else normalized_name
        )

        updated_item = get_item_by_name(
            final_name
        )

        return {
            "success": True,
            "message": (
                f"Updated {name}: "
                f"{', '.join(updated_fields)}"
            ),
            "item": (
                format_item_response(
                    updated_item
                )
                if updated_item
                else None
            )
        }

    except HTTPException:
        raise

    except Exception as exc:

        logger.exception(
            "Error updating item: %s",
            exc
        )

        raise HTTPException(
            status_code=500,
            detail="Failed to update item"
        )


# ============================================================
# DELETE ITEM
# ============================================================

@router.delete(
    "/delete/{name}",
    summary="Delete item",
    description=(
        "Completely delete an item "
        "from inventory"
    )
)
async def delete_item(
    name: str
):

    normalized_name = standardize_name(
        name
    )

    try:

        existing = get_item_by_name(
            normalized_name
        )

        if not existing:

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    f"Item '{name}' "
                    "not found"
                )
            )

        result = remove_item(
            normalized_name,
            existing["quantity"]
        )

        if not result:

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to delete item"
            )

        return {
            "success": True,
            "message": (
                f"Deleted item "
                f"'{name}' completely"
            )
        }

    except HTTPException:
        raise

    except Exception as exc:

        logger.exception(
            "Error deleting item: %s",
            exc
        )

        raise HTTPException(
            status_code=500,
            detail="Failed to delete item"
        )


# ============================================================
# BULK ADD
# ============================================================

@router.post(
    "/bulk/add",
    response_model=BulkOperationResult,
    summary="Bulk add items",
    description="Add multiple items at once"
)
async def bulk_add_items_endpoint(
    request: BulkAddRequest
):

    try:

        items = [
            (
                item.name,
                item.quantity,
                item.category or "general",
                item.unit or "piece",
                item.price or 0.0
            )
            for item in request.items
        ]

        success_count = bulk_add_items(
            items
        )

        failed_count = (
            len(request.items)
            - success_count
        )

        return BulkOperationResult(
            total=len(request.items),
            success_count=success_count,
            failed_count=failed_count,
            failed_items=[],
            message=(
                f"Successfully added "
                f"{success_count} of "
                f"{len(request.items)} items"
            )
        )

    except Exception as exc:

        logger.exception(
            "Error in bulk add: %s",
            exc
        )

        raise HTTPException(
            status_code=500,
            detail="Bulk add operation failed"
        )


# ============================================================
# BULK REMOVE
# ============================================================

@router.post(
    "/bulk/remove",
    response_model=BulkOperationResult,
    summary="Bulk remove items",
    description="Remove multiple items at once"
)
async def bulk_remove_items_endpoint(
    request: BulkRemoveRequest
):

    try:

        success_count = bulk_remove_items(
            request.items
        )

        total = len(request.items)

        failed_count = (
            total - success_count
        )

        return BulkOperationResult(
            total=total,
            success_count=success_count,
            failed_count=failed_count,
            failed_items=[],
            message=(
                f"Successfully removed "
                f"{success_count} of "
                f"{total} items"
            )
        )

    except Exception as exc:

        logger.exception(
            "Error in bulk remove: %s",
            exc
        )

        raise HTTPException(
            status_code=500,
            detail="Bulk remove operation failed"
        )


# ============================================================
# EXPORT - JSON
# ============================================================

@router.get(
    "/export/json",
    summary="Export inventory to JSON"
)
async def export_json():

    try:

        filepath = export_inventory_to_json()

        return {
            "success": True,
            "filepath": filepath,
            "format": "json"
        }

    except Exception as exc:

        logger.exception(
            "JSON export error: %s",
            exc
        )

        raise HTTPException(
            status_code=500,
            detail="Export failed"
        )


# ============================================================
# EXPORT - CSV
# ============================================================

@router.get(
    "/export/csv",
    summary="Export inventory to CSV"
)
async def export_csv():

    try:

        filepath = export_inventory_to_csv()

        return {
            "success": True,
            "filepath": filepath,
            "format": "csv"
        }

    except Exception as exc:

        logger.exception(
            "CSV export error: %s",
            exc
        )

        raise HTTPException(
            status_code=500,
            detail="Export failed"
        )


# ============================================================
# EXPORT - TXT
# ============================================================

@router.get(
    "/export/txt",
    summary="Export inventory to TXT"
)
async def export_txt():

    try:

        filepath = export_inventory_to_txt()

        return {
            "success": True,
            "filepath": filepath,
            "format": "txt"
        }

    except Exception as exc:

        logger.exception(
            "TXT export error: %s",
            exc
        )

        raise HTTPException(
            status_code=500,
            detail="Export failed"
        )


# ============================================================
# EXPORT - ALL
# ============================================================

@router.get(
    "/export/all",
    summary="Export inventory to all formats"
)
async def export_all():

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

    except Exception as exc:

        logger.exception(
            "Export all error: %s",
            exc
        )

        raise HTTPException(
            status_code=500,
            detail="Export failed"
        )


# ============================================================
# DATABASE HEALTH
# ============================================================

@router.get(
    "/health/db",
    summary="Database health check"
)
async def db_health():

    try:

        return get_db_health()

    except Exception as exc:

        logger.exception(
            "Database health check failed: %s",
            exc
        )

        return {
            "status": "unhealthy",
            "error": str(exc)
        }


# ============================================================
# TEST
# ============================================================

@router.get(
    "/test",
    summary="Test endpoint"
)
async def test():

    try:

        items = get_all_items()

        return {
            "status": "ok",
            "message": "Inventory API is working",
            "item_count": len(items),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as exc:

        logger.exception(
            "Inventory test failed: %s",
            exc
        )

        return {
            "status": "error",
            "message": str(exc),
            "timestamp": datetime.now().isoformat()
        }


# ============================================================
# PAGINATED INVENTORY
# ============================================================

@router.get(
    "/paginated",
    response_model=PaginatedResponse,
    summary="Get paginated inventory",
    description=(
        "Returns a paginated list "
        "of inventory items"
    )
)
async def get_paginated_inventory(
    page: int = Query(
        1,
        ge=1,
        description="Page number"
    ),
    per_page: int = Query(
        20,
        ge=1,
        le=100,
        description="Items per page"
    ),
    sort_by: Optional[str] = Query(
        None,
        description=(
            "Sort field "
            "(name, quantity, price)"
        )
    ),
    sort_order: str = Query(
        "asc",
        pattern="^(asc|desc)$",
        description="Sort order"
    )
):

    try:

        items = get_all_items()

        # Never modify the cached list directly.
        items = list(items)

        allowed_sort_fields = {
            "name",
            "quantity",
            "price"
        }

        if sort_by in allowed_sort_fields:

            reverse = (
                sort_order == "desc"
            )

            items.sort(
                key=lambda item:
                    item.get(
                        sort_by,
                        0
                    ),
                reverse=reverse
            )

        total = len(items)

        start = (
            (page - 1)
            * per_page
        )

        end = start + per_page

        paginated_items = items[
            start:end
        ]

        return PaginatedResponse(
            items=[
                format_item_response(item)
                for item in paginated_items
            ],
            total=total,
            page=page,
            per_page=per_page
        )

    except Exception as exc:

        logger.exception(
            "Error in paginated inventory: %s",
            exc
        )

        return PaginatedResponse(
            items=[],
            total=0,
            page=page,
            per_page=per_page
        )