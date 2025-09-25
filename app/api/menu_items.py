from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db.session import SessionLocal
from app.models.models import Item, ItemType, Menu, Restaurant, User, UserRole, menu_items_table
from app.schemas.schemas import ItemCreate, ItemRead, MenuCreate, MenuRead
from app.services.auth import get_current_user
import json

router = APIRouter(prefix="/menu", tags=["menu"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Items
@router.post("/{restaurant_id}/items", response_model=ItemRead)
def create_item(restaurant_id: int, payload: ItemCreate, db: Session = Depends(get_db)):
    restaurant = db.query(Restaurant).get(restaurant_id)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    item = Item(
        name=payload.name,
        description=payload.description,
        price=payload.price,
        type=ItemType(payload.type),
        restaurant_id=restaurant_id,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item

@router.get("/{restaurant_id}/items", response_model=List[ItemRead])
def list_items(restaurant_id: int, db: Session = Depends(get_db)):
    return db.query(Item).filter(Item.restaurant_id == restaurant_id).all()

@router.put("/{restaurant_id}/items/{item_id}", response_model=ItemRead)
def update_item(restaurant_id: int, item_id: int, payload: ItemCreate, db: Session = Depends(get_db)):
    item = db.query(Item).filter(Item.id == item_id, Item.restaurant_id == restaurant_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    item.name = payload.name
    item.description = payload.description
    item.price = payload.price
    item.type = ItemType(payload.type)
    
    db.commit()
    db.refresh(item)
    return item

@router.delete("/{restaurant_id}/items/{item_id}")
def delete_item(restaurant_id: int, item_id: int, db: Session = Depends(get_db)):
    item = db.query(Item).filter(Item.id == item_id, Item.restaurant_id == restaurant_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    # Önce menu_items tablosundan bu item'i kullanan tüm combo menüleri güncelle
    menus_using_item = db.query(Menu).filter(Menu.items.any(Item.id == item_id)).all()
    for menu in menus_using_item:
        # Item'i menüden çıkar
        menu.items = [i for i in menu.items if i.id != item_id]
        # item_ids'i güncelle
        remaining_item_ids = [i.id for i in menu.items]
        menu.item_ids = json.dumps(remaining_item_ids)
    
    db.delete(item)
    db.commit()
    return {"message": "Item deleted successfully"}

# Menus
@router.post("/{restaurant_id}/menus", response_model=MenuRead)
def create_menu(restaurant_id: int, payload: MenuCreate, db: Session = Depends(get_db)):
    restaurant = db.query(Restaurant).get(restaurant_id)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    # Fiyatı kullanıcı belirleyecek, otomatik hesaplama yok
    if payload.item_ids:
        items = db.query(Item).filter(Item.id.in_(payload.item_ids), Item.restaurant_id == restaurant_id).all()
        if len(items) != len(payload.item_ids):
            raise HTTPException(status_code=400, detail="Some items not found or not in restaurant")
        menu = Menu(name=payload.name, description=payload.description, restaurant_id=restaurant_id, price=0, item_ids=json.dumps(payload.item_ids))
        menu.items = items
    else:
        menu = Menu(name=payload.name, description=payload.description, restaurant_id=restaurant_id, price=0, item_ids="[]")
    db.add(menu)
    db.commit()
    db.refresh(menu)
    return MenuRead(
        id=menu.id,
        name=menu.name,
        description=menu.description,
        restaurant_id=menu.restaurant_id,
        item_ids=[i.id for i in menu.items],
    )

@router.get("/{restaurant_id}/menus/{menu_id}")
def get_single_menu(restaurant_id: int, menu_id: int, db: Session = Depends(get_db)):
    """Tek bir kombinasyon menüsünü getir"""
    try:
        menu = db.query(Menu).filter(
            Menu.id == menu_id,
            Menu.restaurant_id == restaurant_id
        ).first()
        
        if not menu:
            raise HTTPException(status_code=404, detail="Kombinasyon menüsü bulunamadı")
        
        # Full response döndür
        return {
            "id": menu.id,
            "name": menu.name,
            "description": menu.description or "",
            "restaurant_id": menu.restaurant_id,
            "price": float(menu.price) if menu.price else 0.0,
            "item_ids": [item.id for item in menu.items],
            "items": [
                {
                    "id": item.id,
                    "name": item.name,
                    "description": item.description or "",
                    "price": float(item.price) if item.price else 0.0,
                    "type": item.type.value if item.type else "unknown"
                }
                for item in menu.items
            ]
        }
    except Exception as e:
        print(f"Error in get_single_menu: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@router.put("/{restaurant_id}/menus/{menu_id}")
def update_combo_menu(
    restaurant_id: int,
    menu_id: int,
    combo_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Kombinasyon menüsünü güncelle"""
    try:
        # Kullanıcının bu restorana erişimi var mı kontrol et
        if current_user.role == UserRole.restaurant:
            # Restaurant kullanıcıları için: current_user.id'den restaurant ID'sini hesapla
            user_restaurant_id = current_user.id - 10000
            if user_restaurant_id != restaurant_id:
                raise HTTPException(status_code=403, detail="Bu restoran için yetkiniz yok")
        elif current_user.role != UserRole.admin:
            raise HTTPException(status_code=403, detail="Bu işlem için yetkiniz yok")
        
        restaurant = db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()
        if not restaurant:
            raise HTTPException(status_code=404, detail="Restoran bulunamadı")
        
        # Menüyü bul
        menu = db.query(Menu).filter(
            Menu.id == menu_id,
            Menu.restaurant_id == restaurant_id
        ).first()
        
        if not menu:
            raise HTTPException(status_code=404, detail="Kombinasyon menüsü bulunamadı")
        
        # Gerekli alanları kontrol et
        required_fields = ['name', 'price', 'item_ids']
        for field in required_fields:
            if field not in combo_data:
                raise HTTPException(status_code=400, detail=f"Eksik alan: {field}")
        
        # Seçilen item'ları kontrol et
        item_ids = combo_data['item_ids']
        if not item_ids or len(item_ids) == 0:
            raise HTTPException(status_code=400, detail="En az bir menü öğesi seçmelisiniz")
        
        # Item'ların bu restorana ait olduğunu kontrol et
        items = db.query(Item).filter(Item.id.in_(item_ids), Item.restaurant_id == restaurant_id).all()
        if len(items) != len(item_ids):
            raise HTTPException(status_code=400, detail="Seçilen menü öğelerinden bazıları bulunamadı")
        
        # Menü bilgilerini güncelle
        menu.name = combo_data['name']
        menu.description = combo_data.get('description', '')
        menu.price = combo_data.get('price', 0)  # Kullanıcının belirlediği fiyat
        menu.item_ids = json.dumps(item_ids)  # Item ID'lerini güncelle
        
        # Mevcut item'ları temizle ve yenilerini ekle
        menu.items.clear()
        menu.items.extend(items)
        
        db.commit()
        db.refresh(menu)
        
        return {
            "message": "Kombinasyon menüsü başarıyla güncellendi",
            "menu": {
                "id": menu.id,
                "name": menu.name,
                "description": menu.description,
                "price": menu.price,  # Toplam fiyat hesapla
                "item_ids": [item.id for item in items],
                "items": [
                    {
                        "id": item.id,
                        "name": item.name,
                        "description": item.description,
                        "price": item.price,
                        "type": item.type.value
                    }
                    for item in items
                ]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Kombinasyon menüsü güncellenirken hata: {str(e)}")

@router.get("/{restaurant_id}/menus")
def list_menus(restaurant_id: int, db: Session = Depends(get_db)):
    menus = db.query(Menu).filter(Menu.restaurant_id == restaurant_id).all()
    result = []
    for m in menus:
        result.append({
            "id": m.id,
            "name": m.name,
            "description": m.description or "",
            "restaurant_id": m.restaurant_id,
            "price": float(m.price) if m.price else 0.0,
            "item_ids": [i.id for i in m.items],
            "items": [
                {
                    "id": item.id,
                    "name": item.name,
                    "description": item.description or "",
                    "price": float(item.price) if item.price else 0.0,
                    "type": item.type.value if item.type else "unknown"
                }
                for item in m.items
            ]
        })
    return result

@router.delete("/{restaurant_id}/menus/{menu_id}")
def delete_combo_menu(
    restaurant_id: int,
    menu_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Kombinasyon menüsünü sil"""
    try:
        # Kullanıcının bu restorana erişimi var mı kontrol et
        if current_user.role == UserRole.restaurant:
            # Restaurant kullanıcıları için: current_user.id'den restaurant ID'sini hesapla
            user_restaurant_id = current_user.id - 10000
            if user_restaurant_id != restaurant_id:
                raise HTTPException(status_code=403, detail="Bu restoran için yetkiniz yok")
        elif current_user.role != UserRole.admin:
            raise HTTPException(status_code=403, detail="Bu işlem için yetkiniz yok")
        
        restaurant = db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()
        if not restaurant:
            raise HTTPException(status_code=404, detail="Restoran bulunamadı")
        
        # Menüyü bul
        menu = db.query(Menu).filter(
            Menu.id == menu_id,
            Menu.restaurant_id == restaurant_id
        ).first()
        
        if not menu:
            raise HTTPException(status_code=404, detail="Kombinasyon menüsü bulunamadı")
        
        # Menüyü sil
        db.delete(menu)
        db.commit()
        
        return {"message": "Kombinasyon menüsü başarıyla silindi"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Kombinasyon menüsü silinirken hata: {str(e)}")

# Manuel kombinasyon menü oluşturma endpoint'i
@router.post("/{restaurant_id}/create-manual-combo")
def create_manual_combo(restaurant_id: int, combo_data: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Manuel kombinasyon menüsü oluştur"""
    # Kullanıcının bu restoranın sahibi olduğunu kontrol et
    if current_user.role == UserRole.restaurant:
        # Restaurant kullanıcıları için: current_user.id'den restaurant ID'sini hesapla
        user_restaurant_id = current_user.id - 10000
        if user_restaurant_id != restaurant_id:
            raise HTTPException(status_code=403, detail="Bu restoran için yetkiniz yok")
    elif current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Bu işlem için yetkiniz yok")
    
    restaurant = db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restoran bulunamadı")
    
    # Gerekli alanları kontrol et
    required_fields = ['name', 'price', 'item_ids']
    for field in required_fields:
        if field not in combo_data:
            raise HTTPException(status_code=400, detail=f"Eksik alan: {field}")
    
    # Seçilen item'ları kontrol et
    item_ids = combo_data['item_ids']
    if not item_ids or len(item_ids) == 0:
        raise HTTPException(status_code=400, detail="En az bir menü öğesi seçmelisiniz")
    
    # Item'ların bu restorana ait olduğunu kontrol et
    items = db.query(Item).filter(Item.id.in_(item_ids), Item.restaurant_id == restaurant_id).all()
    if len(items) != len(item_ids):
        raise HTTPException(status_code=400, detail="Seçilen menü öğelerinden bazıları bulunamadı")
    
    try:
        # Yeni kombinasyon menüsü oluştur
        new_menu = Menu(
            name=combo_data['name'],
            description=combo_data.get('description', ''),
            restaurant_id=restaurant_id,
            price=combo_data.get('price', 0),  # Kullanıcının belirlediği fiyat
            item_ids=json.dumps(item_ids)  # Item ID'lerini JSON string olarak kaydet
        )
        db.add(new_menu)
        db.flush()  # ID'yi almak için flush
        
        # Item'ları menüye ekle (many-to-many relationship)
        new_menu.items.extend(items)
        
        db.commit()
        db.refresh(new_menu)
        
        return {
            "message": "Kombinasyon menüsü başarıyla oluşturuldu",
            "menu": {
                "id": new_menu.id,
                "name": new_menu.name,
                "description": new_menu.description,
                "price": new_menu.price,  # Kullanıcının belirlediği fiyat
                "item_ids": [item.id for item in items],
                "items": [
                    {
                        "id": item.id,
                        "name": item.name,
                        "description": item.description,
                        "price": item.price,
                        "type": item.type.value
                    }
                    for item in items
                ]
            }
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Kombinasyon menüsü oluşturulurken hata: {str(e)}")