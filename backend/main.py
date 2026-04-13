from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "Speak Snap Store API", "status": "active"}

@app.get("/api/inventory/")
def get_inventory():
    return [
        {"id": 1, "name": "apple", "quantity": 12},
        {"id": 2, "name": "banana", "quantity": 5},
        {"id": 3, "name": "orange", "quantity": 8}
    ]

@app.post("/api/inventory/add")
def add_item(item: dict):
    return {"success": True, "message": f"Added {item.get('quantity', 0)} {item.get('name', 'item')}(s)"}

@app.post("/api/inventory/remove")
def remove_item(item: dict):
    return {"success": True, "message": f"Removed {item.get('quantity', 0)} {item.get('name', 'item')}(s)"}

@app.post("/api/parse/")
def parse_command(request: dict):
    text = request.get("text", "").lower()
    
    # Simple parsing
    action = "add" if "add" in text or "stock" in text else "remove"
    
    import re
    numbers = re.findall(r'\d+', text)
    quantity = int(numbers[0]) if numbers else 1
    
    # Extract item name
    words = text.split()
    skip_words = ["add", "remove", "stock", "delete", "and", "of", "the"]
    item_words = [w for w in words if w not in skip_words]
    item = " ".join(item_words) if item_words else "item"
    
    return {"item": item, "quantity": quantity, "action": action}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)