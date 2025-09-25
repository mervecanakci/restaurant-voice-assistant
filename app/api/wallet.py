from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.models import Wallet, User
from app.services.auth import get_current_user

router = APIRouter(prefix="/wallet", tags=["wallet"])

# Service fonksiyonları (doğrudan çağrı için)
def get_balance_service(user_id: str, db: Session, current_user):
    """Service fonksiyonu - doğrudan çağrı için"""
    # Kullanıcıyı bul
    user = db.query(User).filter(User.username == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")
    
    # Wallet'ı bul veya oluştur
    wallet = db.query(Wallet).filter(Wallet.user_id == user.id).first()
    if not wallet:
        wallet = Wallet(user_id=user.id, balance=0.0)
        db.add(wallet)
        db.commit()
        db.refresh(wallet)
    
    return {"user_id": user_id, "balance": wallet.balance}

def deduct_balance_service(user_id: str, amount: float, db: Session, current_user):
    """Service fonksiyonu - doğrudan çağrı için"""
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Miktar pozitif olmalı")
    
    # Kullanıcıyı bul
    user = db.query(User).filter(User.username == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")
    
    # Wallet'ı bul
    wallet = db.query(Wallet).filter(Wallet.user_id == user.id).first()
    if not wallet:
        raise HTTPException(status_code=404, detail="Cüzdan bulunamadı")
    
    # Yetersiz bakiye kontrolü
    if wallet.balance < amount:
        raise HTTPException(status_code=400, detail=f"Yetersiz bakiye. Mevcut: {wallet.balance}₺, Gerekli: {amount}₺")
    
    # Bakiyeyi düş
    wallet.balance -= amount
    db.commit()
    db.refresh(wallet)
    
    return {"user_id": user_id, "balance": wallet.balance}

def top_up_service(user_id: str, amount: float, db: Session, current_user):
    """Service fonksiyonu - doğrudan çağrı için"""
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Miktar pozitif olmalı")
    
    # Kullanıcıyı bul
    user = db.query(User).filter(User.username == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")
    
    # Wallet'ı bul veya oluştur
    wallet = db.query(Wallet).filter(Wallet.user_id == user.id).first()
    if not wallet:
        wallet = Wallet(user_id=user.id, balance=0.0)
        db.add(wallet)
    
    # Bakiyeyi güncelle
    wallet.balance += amount
    db.commit()
    db.refresh(wallet)
    
    return {"user_id": user_id, "balance": wallet.balance}

# HTTP Endpoint fonksiyonları
@router.get("/{user_id}")
def get_balance(user_id: str, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    # Kullanıcı kendi bakiyesini veya admin tüm bakiyeleri görebilir
    if current_user.username != user_id and current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Bu bakiyeyi görme yetkiniz yok")
    
    return get_balance_service(user_id, db, current_user)

@router.post("/{user_id}/topup")
def top_up(user_id: str, amount: float, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    # Kullanıcı kendi bakiyesini veya admin tüm bakiyeleri güncelleyebilir
    if current_user.username != user_id and current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Bu bakiyeyi güncelleme yetkiniz yok")
    
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Miktar pozitif olmalı")
    
    # Kullanıcıyı bul
    user = db.query(User).filter(User.username == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")
    
    # Wallet'ı bul veya oluştur
    wallet = db.query(Wallet).filter(Wallet.user_id == user.id).first()
    if not wallet:
        wallet = Wallet(user_id=user.id, balance=0.0)
        db.add(wallet)
    
    # Bakiyeyi güncelle
    wallet.balance += amount
    db.commit()
    db.refresh(wallet)
    
    return {"user_id": user_id, "balance": wallet.balance}

@router.post("/{user_id}/deduct")
def deduct_balance(user_id: str, amount: float, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    # Kullanıcı kendi bakiyesini veya admin tüm bakiyeleri güncelleyebilir
    if current_user.username != user_id and current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Bu bakiyeyi güncelleme yetkiniz yok")
    
    return deduct_balance_service(user_id, amount, db, current_user)
