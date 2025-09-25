from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
from enum import Enum
from datetime import datetime

class ItemType(str, Enum):
    food = "food"
    drink = "drink"
    dessert = "dessert"
    combo = "combo"

class UserRole(str, Enum):
    admin = "admin"
    restaurant = "restaurant"
    customer = "customer"

# Authentication Schemas
class UserBase(BaseModel):
    username: str
    email: EmailStr
    role: UserRole = UserRole.customer

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserRead(UserBase):
    id: int
    is_active: bool
    address: Optional[str] = None
    phone: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
        use_enum_values = True

class UserUpdate(BaseModel):
    address: Optional[str] = None
    phone: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class RestaurantCreate(BaseModel):
    name: str
    address: Optional[str] = None
    phone: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    email: Optional[str] = None

class RestaurantRead(BaseModel):
    id: int
    name: str
    address: Optional[str] = None
    phone: Optional[str] = None
    username: Optional[str] = None
    email: Optional[str] = None
    is_active: bool
    class Config:
        from_attributes = True

class ItemCreate(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    type: ItemType

class ItemRead(ItemCreate):
    id: int
    restaurant_id: int
    class Config:
        from_attributes = True

class MenuCreate(BaseModel):
    name: str
    description: Optional[str] = None
    item_ids: List[int] = Field(default_factory=list)

class MenuRead(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    restaurant_id: int
    item_ids: List[int] = Field(default_factory=list)
    class Config:
        from_attributes = True

class OrderItemCreate(BaseModel):
    item_id: Optional[int] = None
    menu_id: Optional[int] = None
    quantity: int = 1

class OrderCreate(BaseModel):
    customer_name: str
    customer_phone: str
    delivery_address: str
    restaurant_id: int
    items: List[OrderItemCreate]

class OrderRead(BaseModel):
    id: int
    status: str
    total_price: float
    class Config:
        from_attributes = True
