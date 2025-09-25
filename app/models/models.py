from sqlalchemy import Column, Integer, String, ForeignKey, Float, Enum, Boolean, Table, DateTime
from sqlalchemy.orm import relationship
from app.db.session import Base
from datetime import datetime
import enum

class ItemType(str, enum.Enum):
    food = "food"
    drink = "drink"
    dessert = "dessert"
    combo = "combo"

class UserRole(str, enum.Enum):
    admin = "admin"
    restaurant = "restaurant"
    customer = "customer"

# Bir menü birden fazla item içerebilir, kombo desteklemek için m2m tablo
menu_items_table = Table(
    "menu_items",
    Base.metadata,
    Column("menu_id", ForeignKey("menus.id"), primary_key=True),
    Column("item_id", ForeignKey("items.id"), primary_key=True),
)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.customer)
    is_active = Column(Boolean, default=True)
    address = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Restoran sahibi ise restoranı
    restaurant = relationship("Restaurant", back_populates="owner", uselist=False)
    # Cüzdan bilgisi
    wallet = relationship("Wallet", back_populates="user", uselist=False)

class Wallet(Base):
    __tablename__ = "wallets"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    balance = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="wallet")

class Restaurant(Base):
    __tablename__ = "restaurants"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    address = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    username = Column(String, unique=True, nullable=True)
    password_hash = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="restaurant")
    items = relationship("Item", back_populates="restaurant", cascade="all, delete-orphan")
    menus = relationship("Menu", back_populates="restaurant", cascade="all, delete-orphan")

class Item(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    price = Column(Float, nullable=False)
    type = Column(Enum(ItemType), nullable=False)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=False)

    restaurant = relationship("Restaurant", back_populates="items")

class Menu(Base):
    __tablename__ = "menus"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    price = Column(Float, nullable=True, default=0.0)
    item_ids = Column(String, nullable=True)  # JSON string olarak item ID'leri tut
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=False)

    restaurant = relationship("Restaurant", back_populates="menus")
    items = relationship("Item", secondary=menu_items_table, lazy="selectin")

class OrderStatus(str, enum.Enum):
    created = "created"
    paid = "paid"
    preparing = "preparing"
    delivering = "delivering"
    delivered = "delivered"
    cancelled = "cancelled"

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String, unique=True, nullable=False, index=True)
    customer_name = Column(String, nullable=False)
    customer_phone = Column(String, nullable=False)
    delivery_address = Column(String, nullable=False)
    status = Column(Enum(OrderStatus), default=OrderStatus.created, nullable=False)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    total_price = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=True)
    menu_id = Column(Integer, ForeignKey("menus.id"), nullable=True)
    quantity = Column(Integer, default=1)
    unit_price = Column(Float, default=0.0)

