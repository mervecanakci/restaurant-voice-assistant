from datetime import timedelta
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.models import User, UserRole, Restaurant, Wallet, Order, OrderItem
from app.schemas.schemas import UserCreate, UserRead, Token
from app.services.auth import (
    get_password_hash, 
    verify_password, 
    create_access_token, 
    get_current_user,
    get_current_admin_user,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

router = APIRouter(prefix="/auth", tags=["authentication"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/register", response_model=UserRead)
def register(user: UserCreate, db: Session = Depends(get_db)):
    """Kullanıcı kaydı"""
    # Kullanıcı adı kontrolü
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(
            status_code=400,
            detail="Username already registered"
        )
    
    # Email kontrolü
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    
    # Yeni kullanıcı oluştur
    hashed_password = get_password_hash(user.password)
    db_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
        role=user.role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Kullanıcı girişi - hem users hem restaurants tablosunda arar"""
    # Önce users tablosunda ara (admin ve customer kullanıcıları)
    user = db.query(User).filter(User.username == form_data.username).first()
    
    if user is not None:
        # Users tablosunda bulundu
        if not verify_password(form_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user"
            )
    else:
        # Sonra restaurants tablosunda ara (restaurant kullanıcıları)
        restaurant = db.query(Restaurant).filter(Restaurant.username == form_data.username).first()
        
        if restaurant is not None:
            # Restaurant kullanıcısı bulundu
            if not verify_password(form_data.password, restaurant.password_hash):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect username or password",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            if not restaurant.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Inactive user"
                )
            
            # Restaurant'ı User objesi gibi döndürmek için User objesi oluştur
            user = User(
                id=restaurant.id + 10000,  # Restaurant ID'lerini User ID'lerinden ayırmak için
                username=restaurant.username,
                email=restaurant.email,
                hashed_password=restaurant.password_hash,
                role=UserRole.restaurant,
                is_active=restaurant.is_active,
                address=restaurant.address,
                phone=restaurant.phone,
                created_at=restaurant.created_at,
                updated_at=restaurant.updated_at
            )
        else:
            # Hiçbir tabloda bulunamadı
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserRead)
def read_users_me(current_user: User = Depends(get_current_user)):
    """Mevcut kullanıcı bilgileri"""
    return current_user

@router.post("/create-admin")
def create_admin(db: Session = Depends(get_db)):
    """Admin kullanıcısı oluştur (sadece ilk kurulum için)"""
    # Admin zaten var mı kontrol et
    admin_user = db.query(User).filter(User.role == UserRole.admin).first()
    if admin_user:
        raise HTTPException(
            status_code=400,
            detail="Admin user already exists"
        )
    
    # Admin kullanıcısı oluştur
    admin_user = User(
        username="admin",
        email="admin@restaurant.com",
        hashed_password=get_password_hash("admin123"),
        role=UserRole.admin
    )
    db.add(admin_user)
    db.commit()
    db.refresh(admin_user)
    
    return {
        "message": "Admin user created successfully",
        "username": "admin",
        "password": "admin123"
    }

@router.get("/users", response_model=List[UserRead])
def get_all_users(db: Session = Depends(get_db), current_user: User = Depends(get_current_admin_user)):
    """Tüm kullanıcıları listele (sadece admin)"""
    return db.query(User).all()

@router.put("/users/{user_id}/toggle-status")
def toggle_user_status(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_admin_user)):
    """Kullanıcı durumunu değiştir (sadece admin)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    user.is_active = not user.is_active
    db.commit()
    return {"message": f"User {'activated' if user.is_active else 'deactivated'}"}

@router.put("/users/me", response_model=UserRead)
def update_my_profile(user_update: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Kullanıcının kendi profilini günceller - Tüm kullanıcı türleri için"""
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")
    
    # Müşteri kendi profilini güncellerken sadece belirli alanları güncelleyebilir
    if current_user.role == UserRole.customer:
        # Müşteri sadece kendi bilgilerini güncelleyebilir, role ve is_active değiştiremez
        allowed_fields = ['username', 'email', 'address', 'phone', 'password']
        for field in user_update.keys():
            if field not in allowed_fields:
                raise HTTPException(status_code=403, detail=f"Bu alanı güncelleme yetkiniz yok: {field}")
    
    # Kullanıcı adı kontrolü (başka kullanıcıda var mı)
    if 'username' in user_update and user_update['username'] != user.username:
        existing_user = db.query(User).filter(User.username == user_update['username']).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Bu kullanıcı adı zaten kullanılıyor")
    
    # Email kontrolü (başka kullanıcıda var mı)
    if 'email' in user_update and user_update['email'] != user.email:
        existing_user = db.query(User).filter(User.email == user_update['email']).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Bu email zaten kullanılıyor")
    
    # Güncelleme
    for field, value in user_update.items():
        if field == 'password' and value:
            user.hashed_password = get_password_hash(value)
        elif field in ['username', 'email', 'address', 'phone']:
            setattr(user, field, value)
        elif field in ['role', 'is_active'] and current_user.role == UserRole.admin:
            # Sadece admin role ve is_active değiştirebilir
            setattr(user, field, value)
    
    db.commit()
    db.refresh(user)
    return user

@router.get("/users/{user_id}", response_model=UserRead)
def get_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_admin_user)):
    """Kullanıcı detaylarını getir (sadece admin)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user

@router.put("/users/{user_id}", response_model=UserRead)
def update_user(user_id: int, user_update: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Kullanıcı güncelle - Admin tüm kullanıcıları, müşteri sadece kendini güncelleyebilir"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Yetki kontrolü: Admin herkesi güncelleyebilir, müşteri sadece kendini
    if current_user.role != UserRole.admin and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Bu kullanıcıyı güncelleme yetkiniz yok")
    
    # Müşteri kendi profilini güncellerken sadece belirli alanları güncelleyebilir
    if current_user.role == UserRole.customer and current_user.id == user_id:
        # Müşteri sadece kendi bilgilerini güncelleyebilir, role ve is_active değiştiremez
        allowed_fields = ['username', 'email', 'address', 'phone', 'password']
        for field in user_update.keys():
            if field not in allowed_fields:
                raise HTTPException(status_code=403, detail=f"Bu alanı güncelleme yetkiniz yok: {field}")
    
    # Kullanıcı adı kontrolü (başka kullanıcıda var mı)
    if 'username' in user_update and user_update['username'] != user.username:
        existing_user = db.query(User).filter(User.username == user_update['username']).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already exists")
    
    # Email kontrolü (başka kullanıcıda var mı)
    if 'email' in user_update and user_update['email'] != user.email:
        existing_user = db.query(User).filter(User.email == user_update['email']).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already exists")
    
    # Güncelleme
    for field, value in user_update.items():
        if field == 'password' and value:
            user.hashed_password = get_password_hash(value)
        elif field in ['username', 'email', 'address', 'phone']:
            setattr(user, field, value)
        elif field in ['role', 'is_active'] and current_user.role == UserRole.admin:
            # Sadece admin role ve is_active değiştirebilir
            setattr(user, field, value)
    
    db.commit()
    db.refresh(user)
    return user

@router.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_admin_user)):
    """Kullanıcı sil (sadece admin)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Admin kullanıcısını silmeyi engelle
    if user.role == UserRole.admin:
        raise HTTPException(status_code=400, detail="Admin kullanıcısı silinemez")
    
    try:
        # Kullanıcıya ait siparişleri bul
        orders = db.query(Order).filter(Order.user_id == user_id).all()
        
        # Tüm order_items'ları sil
        for order in orders:
            db.query(OrderItem).filter(OrderItem.order_id == order.id).delete()
        
        # Şimdi siparişleri sil
        for order in orders:
            db.delete(order)
        
        # Kullanıcıya ait wallet'ı sil
        wallet = db.query(Wallet).filter(Wallet.user_id == user_id).first()
        if wallet:
            db.delete(wallet)
        
        # Kullanıcıyı sil (cascade delete ile restoran da silinecek)
        db.delete(user)
        db.commit()
        return {"message": "Kullanıcı başarıyla silindi"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Kullanıcı silinirken hata: {str(e)}")
