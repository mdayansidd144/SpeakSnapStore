from pydantic import BaseModel, Field, validator, field_validator, model_validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum
import re

# ==================== ENUMS FOR CONSTRAINED VALUES ====================
class ActionType(str, Enum):
    """Valid inventory actions"""
    ADD = "add"
    REMOVE = "remove"
    UPDATE = "update"
    
class CategoryType(str, Enum):
    """Predefined categories with validation"""
    FRUITS = "fruits"
    VEGETABLES = "vegetables"
    SNACKS = "snacks"
    BEVERAGES = "beverages"
    STATIONERY = "stationery"
    ELECTRONICS = "electronics"
    HOUSEHOLD = "household"
    GENERAL = "general"
    
    @classmethod
    def get_all(cls) -> List[str]:
        return [item.value for item in cls]

class UnitType(str, Enum):
    """Valid unit types"""
    PIECE = "piece"
    KG = "kg"
    GRAM = "gram"
    LITER = "liter"
    ML = "ml"
    PACKET = "packet"
    BOX = "box"
    DOZEN = "dozen"

# ==================== BASE MODELS ====================
class VoiceRequest(BaseModel):
    """Voice recognition request model"""
    audio_base64: Optional[str] = Field(
        None,
        description="Base64 encoded audio data",
        examples=["base64_encoded_audio_string..."]
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "audio_base64": "base64_encoded_audio_data_here"
            }
        }

# ==================== PARSE MODELS ====================
class ParseRequest(BaseModel):
    """Natural language parsing request"""
    text: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Natural language command to parse",
        examples=["add 5 apples", "remove 2 oranges", "10 biscuits, 5 namkeen, 3 chips"]
    )
    
    @field_validator('text')
    @classmethod
    def validate_text(cls, v: str) -> str:
        """Validate and clean input text"""
        if not v or not v.strip():
            raise ValueError('Text cannot be empty')
        if len(v) > 500:
            raise ValueError('Text too long (max 500 characters)')
        return v.strip()
    
    class Config:
        json_schema_extra = {
            "example": {
                "text": "add 5 apples"
            }
        }

class ParseResponse(BaseModel):
    """Parsed command response"""
    item: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Extracted item name",
        examples=["apple", "banana", "water bottle"]
    )
    quantity: int = Field(
        ...,
        ge=1,
        le=10000,
        description="Extracted quantity",
        examples=[1, 5, 10, 100]
    )
    action: ActionType = Field(
        ...,
        description="Action to perform",
        examples=["add", "remove"]
    )
    
    @field_validator('item')
    @classmethod
    def validate_item(cls, v: str) -> str:
        """Clean and validate item name"""
        v = v.lower().strip()
        v = re.sub(r'[^\w\s]', '', v)
        v = re.sub(r'\s+', ' ', v)
        if len(v) < 2:
            raise ValueError('Item name too short')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "item": "apple",
                "quantity": 5,
                "action": "add"
            }
        }

class MultipleItem(BaseModel):
    """Individual item in multiple items response"""
    item: str = Field(..., description="Item name")
    quantity: int = Field(..., ge=1, description="Quantity")
    success: bool = Field(True, description="Whether addition was successful")

class MultipleItemsResponse(BaseModel):
    """Response for multiple items parsing"""
    type: str = Field("multiple", description="Response type")
    items: List[MultipleItem] = Field(..., description="List of parsed items")
    total_success: int = Field(0, description="Number of successfully added items")
    total_failed: int = Field(0, description="Number of failed items")
    
    @model_validator(mode='after')
    def calculate_totals(self) -> 'MultipleItemsResponse':
        """Auto-calculate success/failure counts"""
        self.total_success = sum(1 for item in self.items if item.success)
        self.total_failed = len(self.items) - self.total_success
        return self

# ==================== INVENTORY MODELS ====================
class InventoryItem(BaseModel):
    """Inventory item model"""
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Item name",
        examples=["apple", "banana", "water bottle"]
    )
    quantity: int = Field(
        ...,
        ge=0,
        le=100000,
        description="Current quantity in stock",
        examples=[0, 1, 5, 10, 100]
    )
    category: Optional[str] = Field(
        'general',
        description="Item category",
        examples=["fruits", "snacks", "electronics"]
    )
    unit: Optional[str] = Field(
        'piece',
        description="Unit of measurement",
        examples=["piece", "kg", "liter", "packet"]
    )
    price: Optional[float] = Field(
        0.0,
        ge=0,
        le=1000000,
        description="Price per unit",
        examples=[0.50, 10.0, 99.99]
    )
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Clean and validate item name"""
        v = v.lower().strip()
        v = re.sub(r'[^\w\s]', '', v)
        v = re.sub(r'\s+', ' ', v)
        if len(v) < 2:
            raise ValueError('Item name must be at least 2 characters')
        return v
    
    @field_validator('category')
    @classmethod
    def validate_category(cls, v: str) -> str:
        """Validate category"""
        if v:
            v = v.lower().strip()
            if v not in CategoryType.get_all():
                # Allow custom categories but warn (optional)
                pass
        return v
    
    @field_validator('unit')
    @classmethod
    def validate_unit(cls, v: str) -> str:
        """Validate unit"""
        if v:
            v = v.lower().strip()
        return v
    
    @model_validator(mode='after')
    def validate_total_value(self) -> 'InventoryItem':
        """Ensure total value doesn't overflow"""
        if self.quantity * self.price > 1e9:
            raise ValueError('Total value exceeds maximum allowed')
        return self
    
    @property
    def total_value(self) -> float:
        """Calculate total value (quantity × price)"""
        return self.quantity * self.price
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "apple",
                "quantity": 12,
                "category": "fruits",
                "unit": "piece",
                "price": 0.50
            }
        }

class InventoryItemCreate(InventoryItem):
    """Model for creating new inventory items"""
    pass

class InventoryItemUpdate(BaseModel):
    """Model for updating existing inventory items"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    quantity: Optional[int] = Field(None, ge=0, le=100000)
    category: Optional[str] = None
    unit: Optional[str] = None
    price: Optional[float] = Field(None, ge=0, le=1000000)
    
    class Config:
        json_schema_extra = {
            "example": {
                "quantity": 15,
                "price": 0.75
            }
        }

class InventoryItemResponse(InventoryItem):
    """Inventory item response with additional fields"""
    id: int = Field(..., description="Database ID")
    total_value: float = Field(..., description="Total value (quantity × price)")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# ==================== TRANSACTION MODELS ====================
class Transaction(BaseModel):
    """Transaction record model"""
    id: int
    transaction_id: str
    action: ActionType
    item_name: str
    quantity: int
    previous_quantity: int = 0
    new_quantity: int = 0
    timestamp: datetime
    
    class Config:
        from_attributes = True

class TransactionResponse(BaseModel):
    """Transaction response with formatted data"""
    id: int
    action: str
    item_name: str
    quantity: int
    formatted_action: str = Field(..., description="Human readable action")
    timestamp: str
    
    @model_validator(mode='after')
    def format_data(self) -> 'TransactionResponse':
        """Format transaction data for display"""
        self.formatted_action = f"{self.action.upper()} {self.quantity} × {self.item_name}"
        if isinstance(self.timestamp, datetime):
            self.timestamp = self.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        return self

# ==================== STATISTICS MODELS ====================
class InventoryStats(BaseModel):
    """Inventory statistics model"""
    total_items: int = Field(0, description="Total number of unique items")
    total_quantity: int = Field(0, description="Total units in stock")
    total_value: float = Field(0.0, description="Total inventory value")
    low_stock_items: int = Field(0, description="Number of low stock items")
    average_price: float = Field(0.0, description="Average price per item")
    most_expensive_item: Optional[str] = None
    most_plentiful_item: Optional[str] = None

class CategorySummary(BaseModel):
    """Category-wise summary"""
    category: str
    item_count: int
    total_quantity: int
    total_value: float

# ==================== DETECTION MODELS ====================
class DetectionResponse(BaseModel):
    """Object detection response"""
    detected_item: str = Field(
        ...,
        description="Detected object name",
        examples=["apple", "banana", "laptop"]
    )
    confidence: float = Field(
        ...,
        ge=0,
        le=1,
        description="Detection confidence score (0-1)",
        examples=[0.85, 0.92, 0.67]
    )
    success: bool = Field(True, description="Whether detection was successful")
    
    @field_validator('confidence')
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        """Ensure confidence is within valid range"""
        if v < 0 or v > 1:
            raise ValueError('Confidence must be between 0 and 1')
        return round(v, 4)

class MultipleDetectionResponse(BaseModel):
    """Response for multiple object detection"""
    success: bool
    detections: List[DetectionResponse]
    total_objects: int = 0
    
    @model_validator(mode='after')
    def set_total(self) -> 'MultipleDetectionResponse':
        self.total_objects = len(self.detections)
        return self

# ==================== BULK OPERATION MODELS ====================
class BulkAddRequest(BaseModel):
    """Bulk add items request"""
    items: List[InventoryItem] = Field(..., min_length=1, max_length=100)
    
    class Config:
        json_schema_extra = {
            "example": {
                "items": [
                    {"name": "apple", "quantity": 10, "price": 0.50},
                    {"name": "banana", "quantity": 5, "price": 0.30}
                ]
            }
        }

class BulkRemoveRequest(BaseModel):
    """Bulk remove items request"""
    items: List[str] = Field(..., min_length=1, max_length=100, description="List of item names to remove")
    
    class Config:
        json_schema_extra = {
            "example": {
                "items": ["apple", "banana", "orange"]
            }
        }

class BulkOperationResult(BaseModel):
    """Result of bulk operation"""
    total: int
    success_count: int
    failed_count: int
    failed_items: List[str] = []
    message: str

# ==================== ERROR RESPONSE ====================
class ErrorResponse(BaseModel):
    """Standard error response model"""
    error: str
    detail: Optional[str] = None
    status_code: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "Not Found",
                "detail": "Item 'apple' not found in inventory",
                "status_code": 404
            }
        }

# ==================== PAGINATION ====================
class PaginationParams(BaseModel):
    """Pagination parameters"""
    page: int = Field(1, ge=1, description="Page number")
    per_page: int = Field(20, ge=1, le=100, description="Items per page")
    sort_by: Optional[str] = Field(None, description="Sort field")
    sort_order: str = Field("asc", pattern="^(asc|desc)$", description="Sort order")

class PaginatedResponse(BaseModel):
    """Paginated response wrapper"""
    items: List[Dict[str, Any]]
    total: int
    page: int
    per_page: int
    total_pages: int
    
    @model_validator(mode='after')
    def calculate_pages(self) -> 'PaginatedResponse':
        self.total_pages = (self.total + self.per_page - 1) // self.per_page
        return self

# ==================== HEALTH CHECK ====================
class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: datetime
    version: str = "3.0.0"
    database: Optional[Dict[str, Any]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2024-01-15T10:30:00",
                "version": "3.0.0"
            }
        }