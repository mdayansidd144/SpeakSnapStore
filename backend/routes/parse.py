from fastapi import APIRouter, HTTPException, BackgroundTasks, status
from fastapi.responses import JSONResponse
from models import ParseRequest, ParseResponse, MultipleItemsResponse, MultipleItem
from ai_models.llama_client import llama
from database import add_item, get_item_by_name
from typing import List, Dict, Any, Optional
import re
import logging
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)
router = APIRouter()

# Thread pool for CPU-intensive operations
executor = ThreadPoolExecutor(max_workers=2)

# ==================== HELPER FUNCTIONS ====================

# Common words to filter out from item names
STOP_WORDS = {
    'add', 'remove', 'delete', 'stock', 'buy', 'purchase', 'get', 'want',
    'please', 'kindly', 'help', 'need', 'order', 'place', 'put',
    'and', 'or', 'then', 'also', 'with', 'for', 'from', 'to'
}

# Quantity word mapping
QUANTITY_WORDS = {
    'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
    'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
    'eleven': 11, 'twelve': 12, 'thirteen': 13, 'fourteen': 14, 'fifteen': 15,
    'sixteen': 16, 'seventeen': 17, 'eighteen': 18, 'nineteen': 19, 'twenty': 20,
    'dozen': 12, 'half': 0.5, 'quarter': 0.25
}

def parse_quantity(text: str) -> int:
    """Extract quantity from text (digits or words)"""
    text_lower = text.lower()
    
    # Check for digits first
    digits = re.findall(r'\d+', text_lower)
    if digits:
        return sum(int(d) for d in digits)
    
    # Check for quantity words
    words = text_lower.split()
    total = 0
    for word in words:
        if word in QUANTITY_WORDS:
            total += QUANTITY_WORDS[word]
    
    return total if total > 0 else 1

def parse_multiple_items(text: str) -> List[Dict[str, Any]]:
    """Parse multiple items from text (comma or 'and' separated)"""
    text_lower = text.lower()
    
    # Remove common action words
    for word in STOP_WORDS:
        text_lower = text_lower.replace(word, '')
    
    # Split by commas or 'and'
    separators = r'[ ,&]+|\s+and\s+'
    parts = re.split(separators, text_lower)
    
    items = []
    current_quantity = 1
    current_item_parts = []
    
    for part in parts:
        part = part.strip()
        if not part:
            continue
        
        # Check if part contains a number
        if re.search(r'\d+', part):
            # This part has a number - it might be a quantity
            if current_item_parts:
                # Save previous item
                item_name = ' '.join(current_item_parts).strip()
                if item_name and len(item_name) > 1:
                    items.append({
                        'item': item_name,
                        'quantity': current_quantity,
                        'action': 'add'
                    })
                current_item_parts = []
            
            # Extract quantity from this part
            current_quantity = parse_quantity(part)
            
            # Extract item name from remaining text
            remaining = re.sub(r'\d+', '', part).strip()
            if remaining:
                current_item_parts.append(remaining)
        else:
            # This is part of an item name
            current_item_parts.append(part)
    
    # Save last item
    if current_item_parts:
        item_name = ' '.join(current_item_parts).strip()
        if item_name and len(item_name) > 1:
            items.append({
                'item': item_name,
                'quantity': current_quantity,
                'action': 'add'
            })
    
    return items

def clean_item_name(name: str) -> str:
    """Clean and standardize item name"""
    name = name.lower().strip()
    
    # Remove punctuation
    name = re.sub(r'[^\w\s]', '', name)
    
    # Remove extra spaces
    name = re.sub(r'\s+', ' ', name).strip()
    
    # Remove stop words from beginning/end
    words = name.split()
    while words and words[0] in STOP_WORDS:
        words.pop(0)
    while words and words[-1] in STOP_WORDS:
        words.pop()
    
    return ' '.join(words) if words else name

def is_multiple_items_command(text: str) -> bool:
    """Check if command contains multiple items"""
    text_lower = text.lower()
    
    # Check for commas
    if ',' in text_lower:
        return True
    
    # Check for multiple 'and's
    if text_lower.count(' and ') >= 1:
        # Check if there are multiple numbers
        numbers = re.findall(r'\d+', text_lower)
        if len(numbers) >= 2:
            return True
    
    return False

# ==================== ASYNC PROCESSING ====================

async def process_multiple_items_async(items: List[Dict[str, Any]]) -> List[MultipleItem]:
    """Process multiple items asynchronously"""
    results = []
    
    for item in items:
        try:
            item_name = clean_item_name(item['item'])
            if not item_name or len(item_name) < 2:
                results.append(MultipleItem(
                    item=item['item'],
                    quantity=item['quantity'],
                    success=False
                ))
                continue
            
            success = add_item(item_name, item['quantity'])
            results.append(MultipleItem(
                item=item_name,
                quantity=item['quantity'],
                success=success
            ))
            logger.info(f"Added {item['quantity']} × {item_name}")
        except Exception as e:
            logger.error(f"Failed to add {item['item']}: {e}")
            results.append(MultipleItem(
                item=item['item'],
                quantity=item['quantity'],
                success=False
            ))
    
    return results

# ==================== MAIN ENDPOINTS ====================

@router.post(
    "/",
    response_model=ParseResponse,
    summary="Parse natural language command",
    description="Convert natural language to structured inventory command"
)
async def parse_command(
    request: ParseRequest,
    background_tasks: BackgroundTasks = None
):
    """Parse natural language command to structured data"""
    
    if not request.text or not request.text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No text provided"
        )
    
    text = request.text.strip()
    logger.info(f"Parsing command: {text}")
    
    # Check if this is a multiple items command
    if is_multiple_items_command(text):
        items = parse_multiple_items(text)
        if len(items) > 1:
            # Process multiple items
            results = await process_multiple_items_async(items)
            
            # Log in background
            if background_tasks:
                background_tasks.add_task(
                    log_parse_result,
                    text,
                    len(results),
                    sum(1 for r in results if r.success)
                )
            
            # Return multiple items response
            return {
                "type": "multiple",
                "items": [r.dict() for r in results],
                "item": "multiple",
                "quantity": 0,
                "action": "add"
            }
    
    # Single item parsing using Llama
    try:
        result = llama.extract_inventory(text)
        
        # Clean and validate item name
        item_name = clean_item_name(result.get("item", "item"))
        if not item_name or len(item_name) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not identify item name"
            )
        
        quantity = result.get("quantity", 1)
        if quantity <= 0:
            quantity = 1
        
        action = result.get("action", "add")
        if action not in ['add', 'remove']:
            action = 'add'
        
        # Log in background
        if background_tasks:
            background_tasks.add_task(
                log_parse_result,
                text,
                1,
                1 if action == 'add' else 0
            )
        
        return ParseResponse(
            item=item_name,
            quantity=quantity,
            action=action
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Parse error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to parse command: {str(e)}"
        )

@router.post(
    "/batch",
    summary="Parse multiple commands",
    description="Parse multiple natural language commands in one request"
)
async def parse_batch(
    commands: List[str],
    background_tasks: BackgroundTasks = None
):
    """Parse multiple commands in batch"""
    
    if len(commands) > 20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 20 commands per batch"
        )
    
    results = []
    
    for cmd in commands:
        try:
            result = llama.extract_inventory(cmd)
            results.append({
                "original": cmd,
                "item": clean_item_name(result.get("item", "item")),
                "quantity": result.get("quantity", 1),
                "action": result.get("action", "add"),
                "success": True
            })
        except Exception as e:
            results.append({
                "original": cmd,
                "error": str(e),
                "success": False
            })
    
    # Log in background
    if background_tasks:
        background_tasks.add_task(
            log_batch_parse,
            len(commands),
            sum(1 for r in results if r.get('success', False))
        )
    
    return {
        "success": True,
        "total": len(commands),
        "results": results,
        "timestamp": datetime.now().isoformat()
    }

@router.post(
    "/multiple",
    response_model=MultipleItemsResponse,
    summary="Parse multiple items",
    description="Parse multiple items from a single command"
)
async def parse_multiple_items(
    request: ParseRequest,
    background_tasks: BackgroundTasks = None
):
    """Parse multiple items from a single command"""
    
    if not request.text or not request.text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No text provided"
        )
    
    items = parse_multiple_items(request.text)
    
    if not items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not parse any items from command"
        )
    
    results = await process_multiple_items_async(items)
    
    # Log in background
    if background_tasks:
        background_tasks.add_task(
            log_parse_result,
            request.text,
            len(results),
            sum(1 for r in results if r.success)
        )
    
    return MultipleItemsResponse(items=results)

@router.get(
    "/suggestions",
    summary="Get command suggestions",
    description="Get example command suggestions"
)
async def get_suggestions():
    """Get example command suggestions"""
    suggestions = [
        "add 5 apples",
        "remove 2 oranges",
        "stock 10 bananas",
        "add 3 mangoes",
        "10 biscuits, 5 namkeen, 3 chips",
        "add 5 apples and 3 bananas and 2 oranges",
        "remove 1 dozen eggs",
        "stock 20 pencils and 15 erasers",
        "add half kg rice",
        "buy 2 liters milk"
    ]
    
    return {
        "suggestions": suggestions,
        "count": len(suggestions),
        "tip": "Use commas or 'and' for multiple items"
    }

@router.get(
    "/test",
    summary="Test endpoint",
    description="Test if parse API is working"
)
async def test_parse():
    """Test if parse API is working"""
    return {
        "status": "ok",
        "message": "Parse API is working",
        "timestamp": datetime.now().isoformat()
    }

# ==================== HEALTH CHECK ====================

@router.get(
    "/health",
    summary="Health check",
    description="Check parse service health"
)
async def health_check():
    """Health check for parse service"""
    try:
        # Test with a simple command
        test_result = llama is not None
        
        return {
            "status": "healthy" if test_result else "degraded",
            "model_loaded": test_result,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# ==================== LOGGING FUNCTIONS ====================

async def log_parse_result(text: str, total_items: int, success_count: int):
    """Background task to log parse results"""
    logger.info(f"Parse: '{text[:50]}...' - Items: {total_items}, Success: {success_count}")

async def log_batch_parse(total: int, success: int):
    """Background task to log batch parse results"""
    logger.info(f"Batch parse: {success}/{total} successful")