from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db.session import SessionLocal
from app.models.models import Item, Menu, Order, OrderItem, OrderStatus, Restaurant, Wallet
from app.schemas.schemas import OrderCreate, OrderRead
from app.services import wallet
from app.services.auth import get_current_user, get_current_admin_user

router = APIRouter(prefix="/orders", tags=["orders"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _calculate_total(db: Session, items_spec: List[dict], restaurant_id: int) -> float:
    total = 0.0
    for spec in items_spec:
        qty = max(1, int(spec.get("quantity", 1)))
        if spec.get("item_id"):
            item = db.query(Item).get(int(spec["item_id"]))
            if not item or item.restaurant_id != restaurant_id:
                raise HTTPException(status_code=400, detail="Invalid item")
            total += item.price * qty
        elif spec.get("menu_id"):
            menu = db.query(Menu).get(int(spec["menu_id"]))
            if not menu or menu.restaurant_id != restaurant_id:
                raise HTTPException(status_code=400, detail="Invalid menu")
            total += sum(i.price for i in menu.items) * qty
        else:
            raise HTTPException(status_code=400, detail="Each order item must have item_id or menu_id")
    return round(total, 2)

@router.post("/", response_model=OrderRead)
def create_order(payload: OrderCreate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    restaurant = db.query(Restaurant).get(payload.restaurant_id)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    total = _calculate_total(db, [i.dict() for i in payload.items], payload.restaurant_id)
    
    # Cüzdan kontrolü ve para düşme
    from app.api.wallet import get_balance_service, deduct_balance_service
    
    balance_response = get_balance_service(current_user.username, db, current_user)
    current_balance = balance_response["balance"]
    if current_balance < total:
        raise HTTPException(status_code=400, detail=f"Yetersiz bakiye. Mevcut: {current_balance}₺, Gerekli: {total}₺")
    
    # Para düş
    deduct_balance_service(current_user.username, total, db, current_user)
    
    # Order number oluştur - benzersiz olması için timestamp kullan
    import time
    timestamp = int(time.time())
    order_number = f"#{timestamp}"
    
    order = Order(
        order_number=order_number,
        customer_name=payload.customer_name,
        customer_phone=payload.customer_phone,
        delivery_address=payload.delivery_address,
        restaurant_id=payload.restaurant_id,
        user_id=current_user.id,
        total_price=total,
        status=OrderStatus.created,
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    
    # Order items kaydı (opsiyonel detayı tutalım)
    for spec in payload.items:
        item_id = spec.item_id
        menu_id = spec.menu_id
        qty = spec.quantity
        unit_price = 0.0
        if item_id:
            item = db.query(Item).get(item_id)
            unit_price = item.price
        elif menu_id:
            menu = db.query(Menu).get(menu_id)
            unit_price = sum(i.price for i in menu.items)
        db.add(OrderItem(order_id=order.id, item_id=item_id, menu_id=menu_id, quantity=qty, unit_price=unit_price))
    db.commit()
    return OrderRead(id=order.id, status=order.status.value, total_price=order.total_price)

@router.post("/{order_id}/pay")
def pay_order(order_id: int, user_id: str, db: Session = Depends(get_db)):
    order = db.query(Order).get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status not in (OrderStatus.created,):
        raise HTTPException(status_code=400, detail="Order not payable")
    try:
        wallet.charge(user_id, order.total_price)
    except ValueError as e:
        raise HTTPException(status_code=402, detail=str(e))
    order.status = OrderStatus.paid
    db.commit()
    return {"status": order.status.value}

@router.get("/{order_id}")
def get_order(order_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """Tek bir siparişi getir (restoran kontrolü ile)"""
    order = db.query(Order).get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Sipariş bulunamadı")
    
    # Restoran kontrolü
    if current_user.role.value == "restaurant":
        # Restaurant kullanıcıları için: current_user.id'den restaurant ID'sini hesapla
        user_restaurant_id = current_user.id - 10000
        if order.restaurant_id != user_restaurant_id:
            raise HTTPException(status_code=403, detail="Bu sipariş sizin restoranınıza ait değil")
    elif current_user.role.value == "customer":
        # Müşteri sadece kendi siparişlerini görebilir
        if order.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Bu siparişe erişim yetkiniz yok")
    elif current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Bu işlem için yetkiniz yok")
    
    # Sipariş öğelerini al
    order_items = db.query(OrderItem).filter(OrderItem.order_id == order_id).all()
    
    # Sipariş detaylarını hazırla
    order_dict = {
        "id": order.id,
        "order_number": order.order_number,
        "customer_name": order.customer_name,
        "customer_phone": order.customer_phone,
        "delivery_address": order.delivery_address,
        "status": order.status.value,
        "restaurant_id": order.restaurant_id,
        "user_id": order.user_id,
        "total_price": order.total_price,
        "created_at": order.created_at,
        "updated_at": order.updated_at,
        "items": []
    }
    
    # Sipariş öğelerini ekle
    for item in order_items:
        item_dict = {
            "id": item.id,
            "quantity": item.quantity,
            "price": item.unit_price,
            "item_name": None,
            "menu_name": None
        }
        
        # Eğer item_id varsa, item bilgisini al
        if item.item_id:
            item_obj = db.query(Item).get(item.item_id)
            if item_obj:
                item_dict["item_name"] = item_obj.name
        
        # Eğer menu_id varsa, menu bilgisini al
        if item.menu_id:
            menu_obj = db.query(Menu).get(item.menu_id)
            if menu_obj:
                item_dict["menu_name"] = menu_obj.name
        
        order_dict["items"].append(item_dict)
    
    return order_dict

@router.put("/{order_id}/status")
def update_order_status(order_id: int, status_data: dict, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """Sipariş durumunu güncelle (restoran sahibi veya admin)"""
    order = db.query(Order).get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Restoran sahibi kontrolü
    if current_user.role.value == "restaurant":
        # Restaurant kullanıcıları için: current_user.id'den restaurant ID'sini hesapla
        user_restaurant_id = current_user.id - 10000
        if order.restaurant_id != user_restaurant_id:
            raise HTTPException(status_code=403, detail="Bu siparişi güncelleyemezsiniz")
    elif current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Bu işlem için yetkiniz yok")
    
    # Hem "status" hem de "new_status" parametrelerini kontrol et
    new_status = status_data.get("status") or status_data.get("new_status")
    if not new_status:
        raise HTTPException(status_code=400, detail="Sipariş durumu belirtilmedi")
    
    # Geçerli durum kontrolü
    valid_statuses = [status.value for status in OrderStatus]
    if new_status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Geçersiz durum. Geçerli durumlar: {valid_statuses}")
    
    # Eğer sipariş iptal ediliyorsa para iadesi yap
    if new_status == "cancelled":
        try:
            # Kullanıcının cüzdanını bul
            wallet = db.query(Wallet).filter(Wallet.user_id == order.user_id).first()
            if wallet:
                # İade miktarını ekle
                refund_amount = order.total_price
                wallet.balance += refund_amount
                print(f"Para iadesi: {refund_amount}₺ kullanıcı {order.user_id} cüzdanına eklendi")
            else:
                print(f"Kullanıcı {order.user_id} cüzdanı bulunamadı")
        except Exception as e:
            print(f"Para iadesi hatası: {str(e)}")
            # Para iadesi başarısız olsa bile siparişi iptal et
    
    order.status = OrderStatus(new_status)
    db.commit()
    
    message = f"Sipariş durumu '{new_status}' olarak güncellendi"
    if new_status == "cancelled":
        message += f" ve {order.total_price}₺ cüzdanınıza iade edildi"
    
    return {
        "message": message,
        "order_id": order_id,
        "new_status": new_status
    }

@router.get("/restaurant/{restaurant_id}")
def get_restaurant_orders(restaurant_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """Restoran siparişlerini getir"""
    # Restoran sahibi kontrolü
    if current_user.role.value == "restaurant":
        # Restaurant kullanıcıları için: current_user.id'den restaurant ID'sini hesapla
        user_restaurant_id = current_user.id - 10000
        if user_restaurant_id != restaurant_id:
            raise HTTPException(status_code=403, detail="Bu restoranın siparişlerini görüntüleyemezsiniz")
    elif current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Bu işlem için yetkiniz yok")
    
    orders = db.query(Order).filter(Order.restaurant_id == restaurant_id).order_by(Order.created_at.desc()).all()
    return orders

@router.get("/user/{user_id}")
def get_user_orders(user_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """Kullanıcının siparişlerini getirir"""
    if current_user.id != user_id and current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Bu siparişleri görme yetkiniz yok")
    
    orders = db.query(Order).filter(Order.user_id == user_id).order_by(Order.created_at.desc()).all()
    
    # Sipariş detaylarını çek
    orders_with_details = []
    for order in orders:
        # Restaurant bilgisini çek
        restaurant = db.query(Restaurant).filter(Restaurant.id == order.restaurant_id).first()
        
        # Order items bilgisini çek  
        order_items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
        
        items_detail = []
        for order_item in order_items:
            if order_item.item_id:
                item = db.query(Item).filter(Item.id == order_item.item_id).first()
                items_detail.append({
                    "item_name": item.name if item else "Bilinmeyen Ürün",
                    "quantity": order_item.quantity,
                    "price": item.price if item else 0
                })
            elif order_item.menu_id:
                menu = db.query(Menu).filter(Menu.id == order_item.menu_id).first()
                items_detail.append({
                    "menu_name": menu.name if menu else "Bilinmeyen Menü",
                    "quantity": order_item.quantity,
                    "price": menu.price if menu else 0
                })
        
        order_dict = {
            "id": order.id,
            "order_number": order.order_number,
            "restaurant_id": order.restaurant_id,
            "restaurant_name": restaurant.name if restaurant else "Bilinmeyen Restoran",
            "customer_name": order.customer_name,
            "customer_phone": order.customer_phone,
            "delivery_address": order.delivery_address,
            "status": order.status.value,
            "total_amount": order.total_price,
            "created_at": order.created_at.isoformat(),
            "updated_at": order.updated_at.isoformat() if order.updated_at else None,
            "items": items_detail
        }
        orders_with_details.append(order_dict)
    
    return orders_with_details

@router.get("/user/{user_id}/detailed")
def get_user_orders_detailed(user_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """Kullanıcının siparişlerini detaylarıyla getir"""
    # Kullanıcı kendi siparişlerini veya admin tüm siparişleri görebilir
    if current_user.id != user_id and current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Bu siparişleri görme yetkiniz yok")
    
    orders = db.query(Order).filter(Order.user_id == user_id).order_by(Order.created_at.desc()).all()
    
    orders_with_details = []
    for order in orders:
        # Sipariş öğelerini al
        order_items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
        
        # Restoran bilgilerini al
        restaurant = db.query(Restaurant).filter(Restaurant.id == order.restaurant_id).first()
        
        order_dict = {
            "id": order.id,
            "order_number": order.order_number,
            "customer_name": order.customer_name,
            "customer_phone": order.customer_phone,
            "delivery_address": order.delivery_address,
            "restaurant_name": restaurant.name if restaurant else "Bilinmeyen Restoran",
            "restaurant_address": restaurant.address if restaurant else "",
            "restaurant_phone": restaurant.phone if restaurant else "",
            "total_price": order.total_price,
            "status": order.status.value,
            "created_at": order.created_at.isoformat(),
            "items": []
        }
        
        # Sipariş öğelerini ekle
        for item in order_items:
            menu_item = db.query(MenuItem).filter(MenuItem.id == item.menu_item_id).first()
            if menu_item:
                order_dict["items"].append({
                    "name": menu_item.name,
                    "price": menu_item.price,
                    "quantity": item.quantity,
                    "total": menu_item.price * item.quantity
                })
        
        orders_with_details.append(order_dict)
    
    return orders_with_details

@router.get("/user/{user_id}/restaurant/{restaurant_id}")
def get_user_orders_for_restaurant(user_id: int, restaurant_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """Kullanıcının belirli bir restorana ait siparişlerini getir"""
    # Kullanıcı kendi siparişlerini veya admin tüm siparişleri görebilir
    if current_user.id != user_id and current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Bu siparişleri görme yetkiniz yok")
    
    # Sadece belirtilen restorana ait siparişleri getir
    orders = db.query(Order).filter(
        Order.user_id == user_id,
        Order.restaurant_id == restaurant_id
    ).order_by(Order.created_at.desc()).all()
    
    orders_with_details = []
    for order in orders:
        # Sipariş öğelerini al
        order_items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
        
        # Restaurant bilgisini al
        restaurant = db.query(Restaurant).filter(Restaurant.id == order.restaurant_id).first()
        
        order_dict = {
            "id": order.id,
            "order_number": order.order_number,
            "restaurant_id": order.restaurant_id,
            "restaurant_name": restaurant.name if restaurant else "Bilinmeyen Restoran",
            "customer_name": order.customer_name,
            "customer_phone": order.customer_phone,
            "delivery_address": order.delivery_address,
            "status": order.status.value,
            "total_amount": order.total_price,
            "created_at": order.created_at.isoformat(),
            "updated_at": order.updated_at.isoformat() if order.updated_at else None,
            "items": []
        }
        
        # Sipariş öğelerini ekle
        for item in order_items:
            if item.item_id:
                # Tek ürün
                menu_item = db.query(Item).filter(Item.id == item.item_id).first()
                if menu_item:
                    order_dict["items"].append({
                        "item_name": menu_item.name,
                        "quantity": item.quantity,
                        "price": item.unit_price
                    })
            elif item.menu_id:
                # Kombo menü
                menu_item = db.query(MenuItem).filter(MenuItem.id == item.menu_item_id).first()
                if menu_item:
                    order_dict["items"].append({
                        "item_name": menu_item.name,
                        "quantity": item.quantity,
                        "price": menu_item.price,
                        "total": menu_item.price * item.quantity
                    })
        
        orders_with_details.append(order_dict)
    
    return orders_with_details

@router.put("/{order_id}/cancel")
def cancel_order(order_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """Siparişi iptal et (sadece teslim edilmediyse)"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Sipariş bulunamadı")
    
    # Kullanıcı kendi siparişini veya admin tüm siparişleri iptal edebilir
    if current_user.id != order.user_id and current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Bu siparişi iptal etme yetkiniz yok")
    
    # Teslim edildiyse iptal edilemez
    if order.status == OrderStatus.delivered:
        raise HTTPException(status_code=400, detail="Teslim edilmiş sipariş iptal edilemez")
    
    # Para iadesi yap
    from app.api.wallet import get_balance_service, top_up_service
    
    # Kullanıcının cüzdanına para iadesi
    try:
        # Mevcut bakiyeyi al
        balance_response = get_balance_service(current_user.username, db, current_user)
        current_balance = balance_response["balance"]
        
        # İade miktarını ekle
        refund_amount = order.total_price
        from app.api.wallet import top_up_service
        top_up_service(current_user.username, refund_amount, db, current_user)
        
    except Exception as e:
        # Para iadesi başarısız olsa bile siparişi iptal et
        print(f"Para iadesi hatası: {str(e)}")
    
    # Siparişi iptal et
    order.status = OrderStatus.cancelled
    db.commit()
    
    return {"message": f"Sipariş iptal edildi ve {order.total_price}₺ cüzdanınıza iade edildi", "status": order.status.value}

@router.get("/admin/all")
def get_all_orders_admin(db: Session = Depends(get_db), current_user = Depends(get_current_admin_user)):
    """Admin için tüm siparişleri getir"""
    orders = db.query(Order).order_by(Order.created_at.desc()).all()
    
    orders_with_details = []
    for order in orders:
        # Restaurant bilgisini çek
        restaurant = db.query(Restaurant).filter(Restaurant.id == order.restaurant_id).first()
        
        # Order items bilgisini çek  
        order_items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
        
        items_detail = []
        for order_item in order_items:
            if order_item.item_id:
                item = db.query(Item).filter(Item.id == order_item.item_id).first()
                items_detail.append({
                    "item_name": item.name if item else "Bilinmeyen Ürün",
                    "quantity": order_item.quantity,
                    "price": item.price if item else 0
                })
            elif order_item.menu_id:
                menu = db.query(Menu).filter(Menu.id == order_item.menu_id).first()
                items_detail.append({
                    "menu_name": menu.name if menu else "Bilinmeyen Menü",
                    "quantity": order_item.quantity,
                    "price": menu.price if menu else 0
                })
        
        order_dict = {
            "id": order.id,
            "order_number": order.order_number,
            "customer_name": order.customer_name,
            "customer_phone": order.customer_phone,
            "delivery_address": order.delivery_address,
            "restaurant_name": restaurant.name if restaurant else "Bilinmeyen Restoran",
            "restaurant_id": order.restaurant_id,
            "user_id": order.user_id,
            "total_price": order.total_price,
            "status": order.status.value,
            "created_at": order.created_at.isoformat(),
            "updated_at": order.updated_at.isoformat(),
            "items": items_detail
        }
        
        orders_with_details.append(order_dict)
    
    return orders_with_details

@router.get("/admin/count")
def get_orders_count_admin(db: Session = Depends(get_db), current_user = Depends(get_current_admin_user)):
    """Admin için toplam sipariş sayısını getir"""
    count = db.query(Order).count()
    return {"total_orders": count}
