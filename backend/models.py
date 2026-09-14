from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any

import re

from pydantic import BaseModel, Field, field_validator, model_validator


# ============================================================
# ENUMS
# ============================================================

class ActionType(str, Enum):
    """Valid inventory actions."""

    ADD = "add"
    REMOVE = "remove"
    UPDATE = "update"


class CategoryType(str, Enum):
    """Predefined inventory categories."""

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
    """Valid unit types."""

    PIECE = "piece"
    KG = "kg"
    GRAM = "gram"
    LITER = "liter"
    ML = "ml"
    PACKET = "packet"
    BOX = "box"
    DOZEN = "dozen"


# ============================================================
# VOICE MODELS
# ============================================================

class VoiceRequest(BaseModel):
    """Voice recognition request model."""

    audio_base64: Optional[str] = Field(
        default=None,
        description="Base64 encoded audio data",
        examples=[
            "base64_encoded_audio_string..."
        ]
    )

    class Config:
        json_schema_extra = {
            "example": {
                "audio_base64":
                    "base64_encoded_audio_data_here"
            }
        }


# ============================================================
# PARSE MODELS
# ============================================================

class ParseRequest(BaseModel):
    """Natural language parsing request."""

    text: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Natural language command to parse",
        examples=[
            "add 5 apples",
            "remove 2 oranges",
            "10 biscuits, 5 namkeen, 3 chips"
        ]
    )

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:

        if not value or not value.strip():
            raise ValueError(
                "Text cannot be empty"
            )

        value = value.strip()

        if len(value) > 500:
            raise ValueError(
                "Text too long (max 500 characters)"
            )

        return value

    class Config:
        json_schema_extra = {
            "example": {
                "text": "add 5 apples"
            }
        }


class ParseResponse(BaseModel):
    """Parsed command response."""

    item: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Extracted item name",
        examples=[
            "apple",
            "banana",
            "water bottle"
        ]
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
        examples=[
            "add",
            "remove"
        ]
    )

    @field_validator("item")
    @classmethod
    def validate_item(cls, value: str) -> str:

        value = value.lower().strip()

        value = re.sub(
            r"[^\w\s]",
            "",
            value
        )

        value = re.sub(
            r"\s+",
            " ",
            value
        )

        if len(value) < 2:
            raise ValueError(
                "Item name too short"
            )

        return value

    class Config:
        json_schema_extra = {
            "example": {
                "item": "apple",
                "quantity": 5,
                "action": "add"
            }
        }


class MultipleItem(BaseModel):
    """Individual item in multiple-item response."""

    item: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Item name"
    )

    quantity: int = Field(
        ...,
        ge=1,
        le=100000,
        description="Quantity"
    )

    success: bool = Field(
        default=True,
        description="Whether operation was successful"
    )

    @field_validator("item")
    @classmethod
    def validate_item(cls, value: str) -> str:

        value = value.lower().strip()

        value = re.sub(
            r"[^\w\s]",
            "",
            value
        )

        value = re.sub(
            r"\s+",
            " ",
            value
        )

        return value


class MultipleItemsResponse(BaseModel):
    """Response for multiple-item parsing."""

    type: str = Field(
        default="multiple",
        description="Response type"
    )

    items: List[MultipleItem] = Field(
        ...,
        min_length=1,
        description="List of parsed items"
    )

    total_success: int = Field(
        default=0,
        ge=0,
        description="Number of successful items"
    )

    total_failed: int = Field(
        default=0,
        ge=0,
        description="Number of failed items"
    )

    @model_validator(mode="after")
    def calculate_totals(self):

        self.total_success = sum(
            1
            for item in self.items
            if item.success
        )

        self.total_failed = (
            len(self.items)
            - self.total_success
        )

        return self


# ============================================================
# INVENTORY MODELS
# ============================================================

class InventoryItem(BaseModel):
    """Inventory item model."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Item name",
        examples=[
            "apple",
            "banana",
            "water bottle"
        ]
    )

    quantity: int = Field(
        ...,
        ge=0,
        le=100000,
        description="Current quantity in stock",
        examples=[
            0,
            1,
            5,
            10,
            100
        ]
    )

    category: Optional[str] = Field(
        default="general",
        max_length=50,
        description="Item category",
        examples=[
            "fruits",
            "snacks",
            "electronics"
        ]
    )

    unit: Optional[str] = Field(
        default="piece",
        max_length=30,
        description="Unit of measurement",
        examples=[
            "piece",
            "kg",
            "liter",
            "packet"
        ]
    )

    price: Optional[float] = Field(
        default=0.0,
        ge=0,
        le=1000000,
        description="Price per unit",
        examples=[
            0.50,
            10.0,
            99.99
        ]
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:

        value = value.lower().strip()

        value = re.sub(
            r"[^\w\s]",
            "",
            value
        )

        value = re.sub(
            r"\s+",
            " ",
            value
        )

        if len(value) < 2:
            raise ValueError(
                "Item name must be at least 2 characters"
            )

        return value

    @field_validator("category")
    @classmethod
    def validate_category(
        cls,
        value: Optional[str]
    ) -> str:

        if not value:
            return "general"

        return value.lower().strip()

    @field_validator("unit")
    @classmethod
    def validate_unit(
        cls,
        value: Optional[str]
    ) -> str:

        if not value:
            return "piece"

        return value.lower().strip()

    @model_validator(mode="after")
    def validate_total_value(self):

        total = self.quantity * (
            self.price or 0.0
        )

        if total > 1_000_000_000:
            raise ValueError(
                "Total value exceeds maximum allowed"
            )

        return self

    @property
    def total_value(self) -> float:

        return self.quantity * (
            self.price or 0.0
        )

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
    """Model for creating a new inventory item."""

    pass


class InventoryItemUpdate(BaseModel):
    """Model for updating an existing inventory item."""

    name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100
    )

    quantity: Optional[int] = Field(
        default=None,
        ge=0,
        le=100000
    )

    category: Optional[str] = Field(
        default=None,
        max_length=50
    )

    unit: Optional[str] = Field(
        default=None,
        max_length=30
    )

    price: Optional[float] = Field(
        default=None,
        ge=0,
        le=1000000
    )

    @field_validator("name")
    @classmethod
    def validate_name(
        cls,
        value: Optional[str]
    ) -> Optional[str]:

        if value is None:
            return None

        value = value.lower().strip()

        value = re.sub(
            r"[^\w\s]",
            "",
            value
        )

        value = re.sub(
            r"\s+",
            " ",
            value
        )

        if len(value) < 2:
            raise ValueError(
                "Item name must be at least 2 characters"
            )

        return value

    @field_validator("category")
    @classmethod
    def validate_category(
        cls,
        value: Optional[str]
    ) -> Optional[str]:

        if value is None:
            return None

        return value.lower().strip()

    @field_validator("unit")
    @classmethod
    def validate_unit(
        cls,
        value: Optional[str]
    ) -> Optional[str]:

        if value is None:
            return None

        return value.lower().strip()

    class Config:
        json_schema_extra = {
            "example": {
                "quantity": 15,
                "price": 0.75
            }
        }


class InventoryItemResponse(InventoryItem):
    """Inventory item response with database fields."""

    id: int = Field(
        ...,
        description="Database ID"
    )

    total_value: float = Field(
        ...,
        description="Total value (quantity × price)"
    )

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============================================================
# TRANSACTION MODELS
# ============================================================

class Transaction(BaseModel):
    """Transaction record model."""

    id: int

    transaction_id: str

    action: ActionType

    item_name: str

    quantity: int = Field(
        ...,
        ge=1
    )

    previous_quantity: int = Field(
        default=0,
        ge=0
    )

    new_quantity: int = Field(
        default=0,
        ge=0
    )

    price: float = Field(
        default=0.0,
        ge=0
    )

    total_value: float = Field(
        default=0.0,
        ge=0
    )

    timestamp: datetime

    class Config:
        from_attributes = True


class TransactionResponse(BaseModel):
    """Transaction response with formatted data."""

    id: int

    action: str

    item_name: str

    quantity: int

    price: float = 0.0

    total_value: float = 0.0

    formatted_action: str = Field(
        ...,
        description="Human readable action"
    )

    timestamp: str

    @model_validator(mode="after")
    def format_data(self):

        self.formatted_action = (
            f"{self.action.upper()} "
            f"{self.quantity} × "
            f"{self.item_name}"
        )

        if isinstance(
            self.timestamp,
            datetime
        ):
            self.timestamp = (
                self.timestamp.strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            )

        return self


# ============================================================
# STATISTICS
# ============================================================

class InventoryStats(BaseModel):
    """Inventory statistics model."""

    total_items: int = Field(
        default=0,
        ge=0,
        description="Total number of unique items"
    )

    total_quantity: int = Field(
        default=0,
        ge=0,
        description="Total units in stock"
    )

    total_value: float = Field(
        default=0.0,
        ge=0,
        description="Total inventory value"
    )

    low_stock_items: int = Field(
        default=0,
        ge=0,
        description="Number of low stock items"
    )

    average_price: float = Field(
        default=0.0,
        ge=0,
        description="Average price per item"
    )

    most_expensive_item: Optional[str] = None

    most_plentiful_item: Optional[str] = None


class CategorySummary(BaseModel):
    """Category-wise inventory summary."""

    category: str

    item_count: int = Field(
        ...,
        ge=0
    )

    total_quantity: int = Field(
        ...,
        ge=0
    )

    total_value: float = Field(
        ...,
        ge=0
    )


# ============================================================
# DETECTION MODELS
# ============================================================

class DetectionResponse(BaseModel):
    """Object detection response."""

    detected_item: str = Field(
        ...,
        min_length=1,
        description="Detected object name",
        examples=[
            "apple",
            "banana",
            "laptop"
        ]
    )

    confidence: float = Field(
        ...,
        ge=0,
        le=1,
        description="Detection confidence score (0-1)",
        examples=[
            0.85,
            0.92,
            0.67
        ]
    )

    success: bool = Field(
        default=True,
        description="Whether detection was successful"
    )

    @field_validator("confidence")
    @classmethod
    def validate_confidence(
        cls,
        value: float
    ) -> float:

        if not 0 <= value <= 1:
            raise ValueError(
                "Confidence must be between 0 and 1"
            )

        return round(value, 4)


class MultipleDetectionResponse(BaseModel):
    """Response for multiple object detection."""

    success: bool

    detections: List[DetectionResponse]

    total_objects: int = Field(
        default=0,
        ge=0
    )

    @model_validator(mode="after")
    def set_total(self):

        self.total_objects = len(
            self.detections
        )

        return self


# ============================================================
# BULK OPERATIONS
# ============================================================

class BulkAddRequest(BaseModel):
    """Bulk add items request."""

    items: List[InventoryItem] = Field(
        ...,
        min_length=1,
        max_length=100
    )

    class Config:
        json_schema_extra = {
            "example": {
                "items": [
                    {
                        "name": "apple",
                        "quantity": 10,
                        "price": 0.50
                    },
                    {
                        "name": "banana",
                        "quantity": 5,
                        "price": 0.30
                    }
                ]
            }
        }


class BulkRemoveRequest(BaseModel):
    """Bulk remove items request."""

    items: List[str] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="List of item names to remove"
    )

    @field_validator("items")
    @classmethod
    def validate_items(
        cls,
        values: List[str]
    ) -> List[str]:

        cleaned = []

        for value in values:

            if not value or not value.strip():
                continue

            value = value.lower().strip()

            value = re.sub(
                r"[^\w\s]",
                "",
                value
            )

            value = re.sub(
                r"\s+",
                " ",
                value
            )

            if value:
                cleaned.append(value)

        if not cleaned:
            raise ValueError(
                "At least one valid item name is required"
            )

        return cleaned

    class Config:
        json_schema_extra = {
            "example": {
                "items": [
                    "apple",
                    "banana",
                    "orange"
                ]
            }
        }


class BulkOperationResult(BaseModel):
    """Result of a bulk operation."""

    total: int = Field(
        ...,
        ge=0
    )

    success_count: int = Field(
        ...,
        ge=0
    )

    failed_count: int = Field(
        ...,
        ge=0
    )

    failed_items: List[str] = Field(
        default_factory=list
    )

    message: str


# ============================================================
# ERROR RESPONSE
# ============================================================

class ErrorResponse(BaseModel):
    """Standard API error response."""

    error: str

    detail: Optional[str] = None

    status_code: int

    class Config:
        json_schema_extra = {
            "example": {
                "error": "Not Found",
                "detail": (
                    "Item 'apple' not found "
                    "in inventory"
                ),
                "status_code": 404
            }
        }


# ============================================================
# PAGINATION
# ============================================================

class PaginationParams(BaseModel):
    """Pagination parameters."""

    page: int = Field(
        default=1,
        ge=1,
        description="Page number"
    )

    per_page: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Items per page"
    )

    sort_by: Optional[str] = Field(
        default=None,
        description="Sort field"
    )

    sort_order: str = Field(
        default="asc",
        pattern="^(asc|desc)$",
        description="Sort order"
    )


class PaginatedResponse(BaseModel):
    """Paginated response wrapper."""

    items: List[Dict[str, Any]]

    total: int = Field(
        ...,
        ge=0
    )

    page: int = Field(
        ...,
        ge=1
    )

    per_page: int = Field(
        ...,
        ge=1
    )

    total_pages: int = Field(
        default=0,
        ge=0
    )

    @model_validator(mode="after")
    def calculate_pages(self):

        self.total_pages = (
            self.total
            + self.per_page
            - 1
        ) // self.per_page

        return self


# ============================================================
# HEALTH
# ============================================================

class HealthResponse(BaseModel):
    """Health check response."""

    status: str

    timestamp: datetime

    version: str = "3.0.0"

    database: Optional[
        Dict[str, Any]
    ] = None

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp":
                    "2024-01-15T10:30:00",
                "version": "3.0.0"
            }
        }