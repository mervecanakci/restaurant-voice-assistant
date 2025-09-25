from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.models import User, UserRole, Restaurant

# JWT ayarları
SECRET_KEY = "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"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer token
security = HTTPBearer()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Şifre doğrulama"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Şifre hashleme"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """JWT token oluşturma"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    """Token doğrulama - hem users hem restaurants tablosunda arar"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # Önce users tablosunda ara (admin ve customer kullanıcıları)
    user = db.query(User).filter(User.username == username).first()
    if user is not None:
        return user
    
    # Sonra restaurants tablosunda ara (restaurant kullanıcıları)
    restaurant = db.query(Restaurant).filter(Restaurant.username == username).first()
    if restaurant is not None:
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
        return user
    
    raise credentials_exception

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    """Mevcut kullanıcıyı getir"""
    print(f"DEBUG: get_current_user called")
    user = verify_token(credentials, db)
    print(f"DEBUG: get_current_user returning user: {user.username}, role: {user.role}")
    return user

def require_role(required_role: UserRole):
    """Rol kontrolü decorator"""
    def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role != required_role and current_user.role != UserRole.admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        return current_user
    return role_checker

def require_admin(current_user: User = Depends(get_current_user)):
    """Admin kontrolü"""
    if current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

def require_restaurant_owner_or_admin(restaurant_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Restoran sahibi veya admin kontrolü"""
    if current_user.role == UserRole.admin:
        return current_user
    
    if current_user.role == UserRole.restaurant:
        restaurant = db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()
        if restaurant and restaurant.owner_id == current_user.id:
            return current_user
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Restaurant owner access required"
    )

def get_current_admin_user(current_user: User = Depends(get_current_user)):
    """Admin kullanıcı kontrolü"""
    if current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

def get_current_restaurant_owner(current_user: User = Depends(get_current_user)):
    """Restoran sahibi kontrolü"""
    if current_user.role != UserRole.restaurant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Restaurant owner access required"
        )
    return current_user

def get_current_customer_user(current_user: User = Depends(get_current_user)):
    """Müşteri kontrolü"""
    if current_user.role != UserRole.customer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Customer access required"
        )
    return current_user

