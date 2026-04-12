from fastapi import APIRouter, HTTPException
from models import ParseRequest, ParseResponse
from ai_models.llama_client import llama
from database import add_item
router = APIRouter()
@router.post("/")
async def parse_command(request: ParseRequest):
    """Parse natural language command to structured data"""
    if not request.text or not request.text.strip():
        raise HTTPException(status_code=400, detail="No text provided")
    
    print(f"[PARSE] Received: {request.text}")
    
    result = llama.extract_inventory(request.text)
    print(f"[PARSE] Result: {result}")
    
    # Handle multiple items
    if result.get('type') == 'multiple':
        added_items = []
        for item in result['items']:
            try:
                # Clean item name
                item_name = item['item'].strip()
                # Convert to singular if needed
                if item_name.endswith('s') and len(item_name) > 1:
                    item_name = item_name[:-1]
                
                success = add_item(item_name, item['quantity'])
                added_items.append({
                    'item': item_name,
                    'quantity': item['quantity'],
                    'success': success
                })
                print(f"[PARSE] Added: {item['quantity']} x {item_name}")
            except Exception as e:
                print(f"[PARSE] Error adding {item['item']}: {e}")
                added_items.append({
                    'item': item['item'],
                    'quantity': item['quantity'],
                    'success': False
                })
        
        return {
            "type": "multiple",
            "items": added_items,
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