from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db.session import SessionLocal
from app.models.models import Restaurant, User, UserRole
from app.schemas.schemas import RestaurantCreate, RestaurantRead
from app.services.auth import get_password_hash, get_current_admin_user, get_current_user

router = APIRouter(prefix="/restaurants", tags=["restaurants"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/", response_model=RestaurantRead)
def create_restaurant(payload: RestaurantCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_admin_user)):
    # Kullanıcı adı ve email kontrolü (restaurants tablosunda)
    if payload.username:
        existing_restaurant = db.query(Restaurant).filter(Restaurant.username == payload.username).first()
        if existing_restaurant:
            raise HTTPException(status_code=400, detail="Bu kullanıcı adı zaten kullanılıyor")
    
    if payload.email:
        existing_email = db.query(Restaurant).filter(Restaurant.email == payload.email).first()
        if existing_email:
            raise HTTPException(status_code=400, detail="Bu email zaten kullanılıyor")
    
    # Restoran kullanıcısı oluştur
    restaurant_username = payload.username or f"rest_{payload.name.lower().replace(' ', '_')}"
    restaurant_email = payload.email or f"{restaurant_username}@restaurant.com"
    restaurant_password = payload.password or "12345"
    
    # Kullanıcı adı benzersiz mi kontrol et (eğer otomatik oluşturuluyorsa)
    if not payload.username:
        counter = 1
        original_username = restaurant_username
        while db.query(Restaurant).filter(Restaurant.username == restaurant_username).first():
            restaurant_username = f"{original_username}_{counter}"
            counter += 1
    
    # Restoran oluştur (restaurants tablosunda)
    restaurant = Restaurant(
        name=payload.name, 
        address=payload.address, 
        phone=payload.phone,
        email=restaurant_email,
        username=restaurant_username,
        password_hash=get_password_hash(restaurant_password),
        is_active=True
    )
    db.add(restaurant)
    db.commit()
    db.refresh(restaurant)
    
    # Kullanıcı bilgilerini logla (güvenlik için)
    print(f"Restoran oluşturuldu: {restaurant.name}")
    print(f"Kullanıcı adı: {restaurant_username}")
    print(f"Şifre: {restaurant_password}")
    
    return restaurant

@router.get("/", response_model=List[RestaurantRead])
def list_restaurants(db: Session = Depends(get_db)):
    return db.query(Restaurant).all()

@router.get("/my-restaurant", response_model=RestaurantRead)
def get_my_restaurant(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Restoran sahibinin kendi restoranını getirir"""
    if current_user.role != UserRole.restaurant:
        raise HTTPException(status_code=403, detail="Sadece restoran sahipleri bu endpoint'i kullanabilir")
    
    # Restaurant kullanıcıları artık restaurants tablosunda
    # current_user.id'den restaurant ID'sini hesapla (10000 çıkar)
    restaurant_id = current_user.id - 10000
    restaurant = db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restoranınız bulunamadı")
    
    return restaurant

@router.get("/{restaurant_id}", response_model=RestaurantRead)
def get_restaurant(restaurant_id: int, db: Session = Depends(get_db)):
    restaurant = db.query(Restaurant).get(restaurant_id)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    
    return restaurant

@router.put("/my-restaurant", response_model=RestaurantRead)
def update_my_restaurant(payload: RestaurantCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Restoran sahibinin kendi restoranını günceller"""
    if current_user.role != UserRole.restaurant:
        raise HTTPException(status_code=403, detail="Sadece restoran sahipleri bu endpoint'i kullanabilir")
    
    # Restaurant kullanıcıları artık restaurants tablosunda
    # current_user.id'den restaurant ID'sini hesapla (10000 çıkar)
    restaurant_id = current_user.id - 10000
    restaurant = db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restoranınız bulunamadı")
    
    # Restoran bilgilerini güncelle
    restaurant.name = payload.name
    restaurant.address = payload.address
    restaurant.phone = payload.phone
    
    # Restaurant kullanıcı bilgilerini güncelle (restaurants tablosunda)
    # Username güncelleme
    if hasattr(payload, 'username') and payload.username:
        if restaurant.username != payload.username:
            existing_restaurant = db.query(Restaurant).filter(Restaurant.username == payload.username).first()
            if existing_restaurant and existing_restaurant.id != restaurant.id:
                raise HTTPException(status_code=400, detail="Bu kullanıcı adı zaten kullanılıyor")
            restaurant.username = payload.username
    
    # Email güncelleme
    if hasattr(payload, 'email') and payload.email and restaurant.email != payload.email:
        existing_email = db.query(Restaurant).filter(Restaurant.email == payload.email).first()
        if existing_email and existing_email.id != restaurant.id:
            raise HTTPException(status_code=400, detail="Bu email zaten kullanılıyor")
        restaurant.email = payload.email
    
    # Şifre güncelleme
    if hasattr(payload, 'password') and payload.password:
        restaurant.password_hash = get_password_hash(payload.password)
    
    db.commit()
    db.refresh(restaurant)
    
    return restaurant

@router.put("/{restaurant_id}", response_model=RestaurantRead)
def update_restaurant(restaurant_id: int, payload: RestaurantCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_admin_user)):
    restaurant = db.query(Restaurant).get(restaurant_id)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    
    # Restoran bilgilerini güncelle
    restaurant.name = payload.name
    restaurant.address = payload.address
    restaurant.phone = payload.phone
    
    # Restaurant kullanıcı bilgilerini güncelle (restaurants tablosunda)
    # Username güncelleme
    if hasattr(payload, 'username') and payload.username:
        if restaurant.username != payload.username:
            existing_restaurant = db.query(Restaurant).filter(Restaurant.username == payload.username).first()
            if existing_restaurant and existing_restaurant.id != restaurant.id:
                raise HTTPException(status_code=400, detail="Bu kullanıcı adı zaten kullanılıyor")
            restaurant.username = payload.username
    
    # Email güncelleme
    if hasattr(payload, 'email') and payload.email and restaurant.email != payload.email:
        existing_email = db.query(Restaurant).filter(Restaurant.email == payload.email).first()
        if existing_email and existing_email.id != restaurant.id:
            raise HTTPException(status_code=400, detail="Bu email zaten kullanılıyor")
        restaurant.email = payload.email
    
    # Şifre güncelleme
    if hasattr(payload, 'password') and payload.password:
        restaurant.password_hash = get_password_hash(payload.password)
    
    db.commit()
    db.refresh(restaurant)
    return restaurant

@router.delete("/{restaurant_id}")
def delete_restaurant(restaurant_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_admin_user)):
    restaurant = db.query(Restaurant).get(restaurant_id)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    db.delete(restaurant)
    db.commit()
    return {"ok": True}
