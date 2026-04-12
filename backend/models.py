from pydantic import BaseModel
from typing import Optional, List

class VoiceRequest(BaseModel):
    audio_base64: Optional[str] = None

class ParseRequest(BaseModel):
    text: str

class ParseResponse(BaseModel):
    item: str
    quantity: int
    action: str

class InventoryItem(BaseModel):
    name: str
    quantity: int
    category: Optional[str] = 'general'
    unit: Optional[str] = 'piece'
    price: Optional[float] = 0.0

class DetectionResponse(BaseModel):
    detected_item: str
    confidence: float

class MultipleItem(BaseModel):
    item: str
    quantity: int
    success: bool

class MultipleItemsResponse(BaseModel):
    type: str = 'multiple'
    items: List[MultipleItem]