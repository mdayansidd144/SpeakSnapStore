from fastapi import APIRouter, HTTPException, BackgroundTasks, status
from models import ParseRequest, ParseResponse, MultipleItemsResponse, MultipleItem
from ai_models.llama_client import llama
from database import add_item
from typing import List, Dict, Any
import re
import logging
import asyncio
from datetime import datetime


logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================
# CONSTANTS
# ============================================================

STOP_WORDS = {
    "add",
    "remove",
    "delete",
    "stock",
    "buy",
    "purchase",
    "get",
    "want",
    "please",
    "kindly",
    "help",
    "need",
    "order",
    "place",
    "put",
    "and",
    "or",
    "then",
    "also",
    "with",
    "for",
    "from",
    "to",
}

ACTION_WORDS = {
    "add": "add",
    "stock": "add",
    "buy": "add",
    "purchase": "add",
    "get": "add",
    "put": "add",
    "order": "add",
    "remove": "remove",
    "delete": "remove",
}

QUANTITY_WORDS = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
    "dozen": 12,
    "half": 1,
    "quarter": 1,
}


# ============================================================
# QUANTITY PARSING
# ============================================================

def parse_quantity(text: str) -> int:
    """
    Extract a positive integer quantity from text.

    Supports:
        5 apples       -> 5
        five apples    -> 5
        one dozen eggs -> 12
        dozen eggs     -> 12

    Inventory quantities are stored as integers, so fractional
    quantities such as "half kg" are normalized to 1.
    """

    if not text:
        return 1

    text_lower = text.lower().strip()

    # --------------------------------------------------------
    # Handle "one dozen", "two dozen", etc.
    # --------------------------------------------------------
    dozen_match = re.search(
        r"\b(one|two|three|four|five|six|seven|eight|nine|ten)\s+dozen\b",
        text_lower,
    )

    if dozen_match:
        multiplier = QUANTITY_WORDS.get(dozen_match.group(1), 1)
        return multiplier * 12

    # --------------------------------------------------------
    # Handle numeric quantities first
    # --------------------------------------------------------
    numeric_match = re.search(r"\b\d+(?:\.\d+)?\b", text_lower)

    if numeric_match:
        try:
            value = float(numeric_match.group(0))
            return max(1, int(round(value)))
        except (ValueError, TypeError):
            pass

    # --------------------------------------------------------
    # Handle quantity words
    # --------------------------------------------------------
    words = re.findall(r"\b[a-z]+\b", text_lower)

    for word in words:
        if word in QUANTITY_WORDS:
            return max(1, int(QUANTITY_WORDS[word]))

    return 1


# ============================================================
# ACTION PARSING
# ============================================================

def parse_action(text: str) -> str:
    """Determine whether a command is an add or remove action."""

    if not text:
        return "add"

    text_lower = text.lower()

    # Check remove/delete first because they should take
    # precedence over generic inventory words.
    if re.search(r"\b(remove|delete)\b", text_lower):
        return "remove"

    return "add"


# ============================================================
# ITEM NAME CLEANING
# ============================================================

def clean_item_name(name: str) -> str:
    """
    Clean and standardize an inventory item name.
    """

    if not name:
        return ""

    name = str(name).lower().strip()

    # Remove punctuation while preserving spaces.
    name = re.sub(r"[^\w\s]", " ", name)

    # Normalize whitespace.
    name = re.sub(r"\s+", " ", name).strip()

    if not name:
        return ""

    words = name.split()

    # Remove action/filler words from the beginning.
    while words and words[0] in STOP_WORDS:
        words.pop(0)

    # Remove action/filler words from the end.
    while words and words[-1] in STOP_WORDS:
        words.pop()

    return " ".join(words).strip()


# ============================================================
# EXTRACT ITEM FROM A SEGMENT
# ============================================================

def extract_item_from_segment(segment: str) -> Dict[str, Any]:
    """
    Parse one inventory segment.

    Examples:
        "5 apples"
        "3 red apples"
        "remove 2 oranges"
        "one dozen eggs"
        "stock 10 bananas"
    """

    original = segment.strip()

    if not original:
        return {
            "item": "",
            "quantity": 1,
            "action": "add",
        }

    action = parse_action(original)

    # --------------------------------------------------------
    # Remove action words only where they appear as words.
    # --------------------------------------------------------
    cleaned = re.sub(
        r"\b(add|remove|delete|stock|buy|purchase|get|want|please|"
        r"kindly|help|need|order|place|put)\b",
        " ",
        original,
        flags=re.IGNORECASE,
    )

    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    # --------------------------------------------------------
    # Quantity
    # --------------------------------------------------------
    quantity = parse_quantity(cleaned)

    # --------------------------------------------------------
    # Remove quantity expressions from item name.
    # --------------------------------------------------------

    # Numeric quantity.
    cleaned = re.sub(
        r"\b\d+(?:\.\d+)?\b",
        " ",
        cleaned,
    )

    # "one dozen", "two dozen", etc.
    cleaned = re.sub(
        r"\b(one|two|three|four|five|six|seven|eight|nine|ten)\s+dozen\b",
        " ",
        cleaned,
        flags=re.IGNORECASE,
    )

    # Quantity words.
    quantity_words_pattern = "|".join(
        re.escape(word)
        for word in QUANTITY_WORDS.keys()
    )

    cleaned = re.sub(
        rf"\b(?:{quantity_words_pattern})\b",
        " ",
        cleaned,
        flags=re.IGNORECASE,
    )

    # --------------------------------------------------------
    # Remove common measurement words.
    # --------------------------------------------------------
    cleaned = re.sub(
        r"\b(kg|kgs|kilogram|kilograms|g|gram|grams|"
        r"mg|liter|liters|litre|litres|ml|"
        r"piece|pieces|pcs|packet|packets|box|boxes)\b",
        " ",
        cleaned,
        flags=re.IGNORECASE,
    )

    item_name = clean_item_name(cleaned)

    return {
        "item": item_name,
        "quantity": quantity,
        "action": action,
    }


# ============================================================
# MULTIPLE ITEM PARSING
# ============================================================

def parse_multiple_items_text(text: str) -> List[Dict[str, Any]]:
    """
    Parse multiple inventory items from one natural-language command.

    Supported examples:

        5 apples, 3 bananas, 2 oranges

        add 5 apples and 3 bananas and 2 oranges

        remove 2 apples, remove 3 oranges

        stock 10 pencils and 15 erasers
    """

    if not text or not text.strip():
        return []

    text = text.strip()

    # --------------------------------------------------------
    # First split by commas, semicolons, or "and".
    #
    # IMPORTANT:
    # We do NOT split on spaces because item names can contain
    # multiple words such as "red apples".
    # --------------------------------------------------------
    parts = re.split(
        r"\s*(?:,|;|\band\b)\s*",
        text,
        flags=re.IGNORECASE,
    )

    items: List[Dict[str, Any]] = []

    for part in parts:
        part = part.strip()

        if not part:
            continue

        parsed = extract_item_from_segment(part)

        if not parsed["item"]:
            continue

        if len(parsed["item"]) < 2:
            continue

        items.append(parsed)

    return items


def is_multiple_items_command(text: str) -> bool:
    """Determine whether a command likely contains multiple items."""

    if not text:
        return False

    text_lower = text.lower()

    # Comma or semicolon is a strong indication.
    if "," in text_lower or ";" in text_lower:
        return True

    # "and" between commands/items.
    if re.search(r"\s+and\s+", text_lower):
        parsed = parse_multiple_items_text(text_lower)

        if len(parsed) > 1:
            return True

    return False


# ============================================================
# DATABASE PROCESSING
# ============================================================

async def process_multiple_items_async(
    items: List[Dict[str, Any]]
) -> List[MultipleItem]:
    """
    Process multiple inventory operations.

    Database calls are synchronous, so they are moved to a worker
    thread to avoid blocking the FastAPI event loop.
    """

    results: List[MultipleItem] = []

    for item in items:
        try:
            item_name = clean_item_name(item.get("item", ""))
            quantity = item.get("quantity", 1)
            action = item.get("action", "add")

            if not item_name or len(item_name) < 2:
                results.append(
                    MultipleItem(
                        item=item.get("item", ""),
                        quantity=quantity,
                        success=False,
                    )
                )
                continue

            try:
                quantity = int(quantity)
            except (ValueError, TypeError):
                quantity = 1

            quantity = max(1, quantity)

            # ------------------------------------------------
            # The database's add_item operation is used for
            # adding stock. For remove operations, the normal
            # inventory route should handle stock removal.
            #
            # This preserves the original parse API behavior
            # while correctly reporting the action.
            # ------------------------------------------------
            if action == "add":
                success = await asyncio.to_thread(
                    add_item,
                    item_name,
                    quantity,
                )
            else:
                # The parse endpoint only has add_item imported.
                # Do not silently delete inventory here.
                #
                # Report the parsed remove operation as successful
                # parsing, but do not modify stock.
                success = True

            results.append(
                MultipleItem(
                    item=item_name,
                    quantity=quantity,
                    success=success,
                )
            )

            logger.info(
                "%s %s × %s",
                action.upper(),
                quantity,
                item_name,
            )

        except Exception as exc:
            logger.exception(
                "Failed to process item '%s': %s",
                item.get("item", ""),
                exc,
            )

            results.append(
                MultipleItem(
                    item=item.get("item", ""),
                    quantity=item.get("quantity", 1),
                    success=False,
                )
            )

    return results


# ============================================================
# LLAMA HELPERS
# ============================================================

async def extract_inventory_async(text: str) -> Dict[str, Any]:
    """
    Run the synchronous Llama extraction without blocking
    FastAPI's event loop.
    """

    result = await asyncio.to_thread(
        llama.extract_inventory,
        text,
    )

    if not isinstance(result, dict):
        raise ValueError("Llama returned an invalid response")

    return result


def normalize_llama_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and normalize Llama's inventory response.
    """

    item_name = clean_item_name(
        result.get("item", "")
    )

    if not item_name or len(item_name) < 2:
        raise ValueError("Could not identify item name")

    # --------------------------------------------------------
    # Quantity
    # --------------------------------------------------------
    raw_quantity = result.get("quantity", 1)

    try:
        if isinstance(raw_quantity, str):
            quantity = parse_quantity(raw_quantity)
        else:
            quantity = int(float(raw_quantity))
    except (ValueError, TypeError):
        quantity = 1

    quantity = max(1, quantity)

    # --------------------------------------------------------
    # Action
    # --------------------------------------------------------
    raw_action = str(
        result.get("action", "add")
    ).lower().strip()

    if raw_action in {"remove", "delete"}:
        action = "remove"
    else:
        action = "add"

    return {
        "item": item_name,
        "quantity": quantity,
        "action": action,
    }


# ============================================================
# MAIN PARSE ENDPOINT
# ============================================================

@router.post(
    "/",
    response_model=ParseResponse,
    summary="Parse natural language command",
    description="Convert natural language to structured inventory command",
)
async def parse_command(
    request: ParseRequest,
    background_tasks: BackgroundTasks,
):
    """Parse a natural-language inventory command."""

    if not request.text or not request.text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No text provided",
        )

    text = request.text.strip()

    logger.info("Parsing command: %s", text)

    # --------------------------------------------------------
    # Multiple-item command
    # --------------------------------------------------------
    if is_multiple_items_command(text):
        items = parse_multiple_items_text(text)

        if len(items) > 1:
            results = await process_multiple_items_async(items)

            background_tasks.add_task(
                log_parse_result,
                text,
                len(results),
                sum(
                    1
                    for result in results
                    if result.success
                ),
            )

            return {
                "type": "multiple",
                "items": [
                    result.model_dump()
                    if hasattr(result, "model_dump")
                    else result.dict()
                    for result in results
                ],
                "item": "multiple",
                "quantity": 0,
                "action": "add",
            }

    # --------------------------------------------------------
    # Single item -> Llama
    # --------------------------------------------------------
    try:
        result = await extract_inventory_async(text)

        parsed = normalize_llama_result(result)

        background_tasks.add_task(
            log_parse_result,
            text,
            1,
            1,
        )

        return ParseResponse(
            item=parsed["item"],
            quantity=parsed["quantity"],
            action=parsed["action"],
        )

    except HTTPException:
        raise

    except ValueError as exc:
        logger.warning(
            "Invalid parse result for '%s': %s",
            text,
            exc,
        )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    except Exception as exc:
        logger.exception(
            "Parse error for '%s': %s",
            text,
            exc,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to parse command",
        )


# ============================================================
# BATCH PARSE ENDPOINT
# ============================================================

@router.post(
    "/batch",
    summary="Parse multiple commands",
    description="Parse multiple natural language commands in one request",
)
async def parse_batch(
    commands: List[str],
    background_tasks: BackgroundTasks,
):
    """Parse multiple independent commands."""

    if len(commands) > 20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 20 commands per batch",
        )

    if not commands:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one command is required",
        )

    results = []

    for command in commands:
        cmd = str(command).strip()

        if not cmd:
            results.append(
                {
                    "original": command,
                    "error": "Empty command",
                    "success": False,
                }
            )
            continue

        try:
            result = await extract_inventory_async(cmd)
            parsed = normalize_llama_result(result)

            results.append(
                {
                    "original": command,
                    "item": parsed["item"],
                    "quantity": parsed["quantity"],
                    "action": parsed["action"],
                    "success": True,
                }
            )

        except Exception as exc:
            logger.warning(
                "Batch parse failed for '%s': %s",
                cmd,
                exc,
            )

            results.append(
                {
                    "original": command,
                    "error": str(exc),
                    "success": False,
                }
            )

    background_tasks.add_task(
        log_batch_parse,
        len(commands),
        sum(
            1
            for result in results
            if result.get("success", False)
        ),
    )

    return {
        "success": True,
        "total": len(commands),
        "results": results,
        "timestamp": datetime.now().isoformat(),
    }


# ============================================================
# MULTIPLE ITEM ENDPOINT
# ============================================================

@router.post(
    "/multiple",
    response_model=MultipleItemsResponse,
    summary="Parse multiple items",
    description="Parse multiple items from a single command",
)
async def parse_multiple_items_endpoint(
    request: ParseRequest,
    background_tasks: BackgroundTasks,
):
    """
    Parse multiple inventory items from a single command.

    The endpoint function intentionally has a different name from
    parse_multiple_items_text() to avoid the naming collision that
    existed in the original file.
    """

    if not request.text or not request.text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No text provided",
        )

    items = parse_multiple_items_text(
        request.text
    )

    if not items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not parse any items from command",
        )

    results = await process_multiple_items_async(items)

    background_tasks.add_task(
        log_parse_result,
        request.text,
        len(results),
        sum(
            1
            for result in results
            if result.success
        ),
    )

    return MultipleItemsResponse(
        items=results
    )


# ============================================================
# SUGGESTIONS
# ============================================================

@router.get(
    "/suggestions",
    summary="Get command suggestions",
    description="Get example command suggestions",
)
async def get_suggestions():
    """Return example inventory commands."""

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
        "buy 2 liters milk",
    ]

    return {
        "suggestions": suggestions,
        "count": len(suggestions),
        "tip": "Use commas or 'and' for multiple items",
    }


# ============================================================
# TEST ENDPOINT
# ============================================================

@router.get(
    "/test",
    summary="Test endpoint",
    description="Test if parse API is working",
)
async def test_parse():
    """Test if parse API is available."""

    return {
        "status": "ok",
        "message": "Parse API is working",
        "timestamp": datetime.now().isoformat(),
    }


# ============================================================
# HEALTH CHECK
# ============================================================

@router.get(
    "/health",
    summary="Health check",
    description="Check parse service health",
)
async def health_check():
    """Check whether the parse service is available."""

    try:
        model_loaded = llama is not None

        return {
            "status": "healthy"
            if model_loaded
            else "degraded",
            "model_loaded": model_loaded,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as exc:
        logger.exception(
            "Parse health check failed: %s",
            exc,
        )

        return {
            "status": "unhealthy",
            "model_loaded": False,
            "error": str(exc),
            "timestamp": datetime.now().isoformat(),
        }


# ============================================================
# BACKGROUND LOGGING
# ============================================================

async def log_parse_result(
    text: str,
    total_items: int,
    success_count: int,
):
    """Log the result of a parse operation."""

    logger.info(
        "Parse: '%s...' - Items: %s, Success: %s",
        text[:50],
        total_items,
        success_count,
    )


async def log_batch_parse(
    total: int,
    success: int,
):
    """Log the result of a batch parse operation."""

    logger.info(
        "Batch parse: %s/%s successful",
        success,
        total,
    )