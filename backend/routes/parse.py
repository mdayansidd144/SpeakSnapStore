from fastapi import APIRouter, HTTPException
from models import ParseRequest, ParseResponse
from ai_models.llama_client import llama

router = APIRouter()

@router.post("/", response_model=ParseResponse)
async def parse_command(request: ParseRequest):
    """Parse natural language command to structured data"""
    if not request.text or not request.text.strip():
        raise HTTPException(status_code=400, detail="No text provided")
    
    print(f"[PARSE] Received: {request.text}")
    
    result = llama.extract_inventory(request.text)
    print(f"[PARSE] Result: {result}")
    
    # Handle multiple items
    if result.get('type') == 'multiple':
        # Return multiple items for frontend to process
        return {
            "type": "multiple",
            "items": result['items'],
            "item": "multiple",
            "quantity": 0,
            "action": "add"
        }
    
    # Single item
    return ParseResponse(
        item=result.get("item", "item"),
        quantity=result.get("quantity", 1),
        action=result.get("action", "add")
    )