import json
import os
import asyncio
import time
import websockets
import aiohttp
from fastapi import WebSocket, WebSocketDisconnect, APIRouter
from dotenv import load_dotenv
import asyncpg

load_dotenv()

router = APIRouter()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_REALTIME_URL = "wss://api.openai.com/v1/realtime?model=gpt-realtime-2025-08-28"

print(f"🔑 API Key loaded: {OPENAI_API_KEY[:20] if OPENAI_API_KEY else 'None'}...")
print(f"🔑 API Key length: {len(OPENAI_API_KEY) if OPENAI_API_KEY else 0}")
print(f"🔑 API Key valid: {OPENAI_API_KEY is not None and len(OPENAI_API_KEY) > 50}")

class RealtimeManager:
    """OpenAI Realtime API ile function call'ları yöneten sınıf"""
    def __init__(self):
        self.active_connections = {}
        self.openai_connections = {}
        # Her WebSocket bağlantısı için ayrı context
        self.connection_context = {}
    
    async def connect(self, websocket: WebSocket, websocket_id: str):
        await websocket.accept()
        self.active_connections[websocket_id] = websocket
        print(f"✅ WebSocket bağlandı: {websocket_id}")
    
    def disconnect(self, websocket_id: str):
        if websocket_id in self.active_connections:
            del self.active_connections[websocket_id]
        if websocket_id in self.openai_connections:
            del self.openai_connections[websocket_id]
        if websocket_id in self.connection_context:
            del self.connection_context[websocket_id]
        print(f"🔌 WebSocket bağlantısı temizlendi: {websocket_id}")

manager = RealtimeManager()

# GA Format restaurant tools
RESTAURANT_TOOLS = [
    {
        "type": "function",
        "name": "show_menu",
        "description": "Restoran menüsünü gösterir. Kullanıcı menü istediğinde çağrılır.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "type": "function",
        "name": "add_to_cart",
        "description": "Belirtilen ürünü sepete ekler. Kullanıcı ürün eklemek istediğinde çağrılır.",
        "parameters": {
            "type": "object",
            "properties": {
                "item_name": {
                    "type": "string",
                    "description": "Sepete eklenecek ürün adı"
                },
                "quantity": {
                    "type": "number",
                    "description": "Eklenecek ürün adedi (varsayılan: 1)"
                }
            },
            "required": ["item_name"]
        }
    },
    {
        "type": "function",
        "name": "show_cart",
        "description": "Sepet içeriğini gösterir. Kullanıcı sepetini görmek istediğinde çağrılır.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "type": "function",
        "name": "create_order",
        "description": "Sipariş oluşturur. Kullanıcı sipariş vermek istediğinde çağrılır. Adres ve telefon bilgisi gerekir.",
        "parameters": {
            "type": "object",
            "properties": {
                "address": {
                    "type": "string",
                    "description": "Teslimat adresi"
                },
                "phone": {
                    "type": "string",
                    "description": "Telefon numarası"
                }
            },
            "required": ["address", "phone"]
        }
    },
    {
        "type": "function",
        "name": "ask_for_address",
        "description": "Kullanıcıdan teslimat adresi ister. Sipariş oluştururken adres bilgisi gerektiğinde çağrılır.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "type": "function",
        "name": "ask_for_phone",
        "description": "Kullanıcıdan telefon numarası ister. Sipariş oluştururken telefon bilgisi gerektiğinde çağrılır.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "type": "function",
        "name": "remove_from_cart",
        "description": "Belirtilen ürünü sepetten çıkarır. Kullanıcı ürün çıkarmak istediğinde çağrılır.",
        "parameters": {
            "type": "object",
            "properties": {
                "item_name": {
                    "type": "string",
                    "description": "Sepetten çıkarılacak ürün adı"
                },
                "quantity": {
                    "type": "number",
                    "description": "Çıkarılacak ürün adedi (varsayılan: 1)"
                }
            },
            "required": ["item_name"]
        }
    },
    {
        "type": "function",
        "name": "clear_cart",
        "description": "Sepeti tamamen boşaltır. Kullanıcı sepeti boşaltmak istediğinde çağrılır.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "type": "function",
        "name": "confirm_order",
        "description": "Siparişi onaylar. Kullanıcı siparişi onayladığında çağrılır.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "type": "function",
        "name": "cancel_order",
        "description": "Belirtilen siparişi iptal eder. Kullanıcı sipariş iptal etmek istediğinde çağrılır.",
        "parameters": {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": "İptal edilecek sipariş numarası"
                }
            },
            "required": ["order_id"]
        }
    },
    {
        "type": "function",
        "name": "get_order_status",
        "description": "Sipariş durumunu sorgular. Kullanıcı sipariş durumu öğrenmek istediğinde çağrılır.",
        "parameters": {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": "Sorgulanacak sipariş numarası (opsiyonel, belirtilmezse son sipariş)"
                }
            },
            "required": []
        }
    }
]

# Function implementations
async def show_menu(restaurant_id: int):
    """Menüyü getir - Hem combo menüleri hem de tek ürünleri"""
    print(f"🍽️ SHOW_MENU ÇALIŞTIRILIYOR: restaurant_id={restaurant_id}")
    try:
        async with aiohttp.ClientSession() as session:
            # Combo menüleri getir
            print(f"📡 Combo menüleri getiriliyor: /menu/{restaurant_id}/menus")
            async with session.get(f"http://localhost:8000/menu/{restaurant_id}/menus") as menus_response:
                if menus_response.status == 200:
                    menus_data = await menus_response.json()
                    print(f"✅ Combo menüleri alındı: {len(menus_data)} adet")
                else:
                    menus_data = []
                    print(f"❌ Combo menüleri alınamadı: {menus_response.status}")

            # Tek ürünleri getir
            print(f"📡 Tek ürünler getiriliyor: /menu/{restaurant_id}/items")
            async with session.get(f"http://localhost:8000/menu/{restaurant_id}/items") as items_response:
                if items_response.status == 200:
                    items_data = await items_response.json()
                    print(f"✅ Tek ürünler alındı: {len(items_data)} adet")
                else:
                    items_data = []
                    print(f"❌ Tek ürünler alınamadı: {items_response.status}")

            # Kategorilere göre grupla
            categories = {}

            # Combo menüleri ekle
            for menu in menus_data:
                category_name = "🍱 KOMBO MENÜLER"
                if category_name not in categories:
                    categories[category_name] = []
                categories[category_name].append({
                    "name": menu["name"],
                    "price": menu["price"],
                    "description": menu.get("description", "")
                })

            # Tek ürünleri kategorilere göre grupla
            for item in items_data:
                item_type = item.get("type", "unknown")
                if item_type == "food":
                    category_name = "🍽️ YEMEKLER"
                elif item_type == "drink":
                    category_name = "🥤 İÇECEKLER"
                elif item_type == "dessert":
                    category_name = "🍰 TATLILAR"
                else:
                    category_name = "🍽️ DİĞER"

                if category_name not in categories:
                    categories[category_name] = []
                categories[category_name].append({
                    "name": item["name"],
                    "price": item["price"],
                    "description": item.get("description", "")
                })

            # Kategorileri listeye çevir
            menu_categories = []
            for category_name, items in categories.items():
                if items:  # Sadece dolu kategorileri ekle
                    menu_categories.append({
                        "name": category_name,
                        "items": items
                    })

            print(f"📋 Toplam kategori: {len(menu_categories)}")
            for cat in menu_categories:
                print(f"  - {cat['name']}: {len(cat['items'])} ürün")

            return {"success": True, "data": menu_categories}

    except Exception as e:
        print(f"❌ SHOW_MENU HATASI: {e}")
        return {"success": False, "message": f"Hata: {str(e)}"}

async def add_to_cart(item_name: str, quantity: int, restaurant_id: int, user_id: str):
    """Sepete ürün ekle - Fiyat bilgisi ile"""
    print(f"🛒 IN-MEMORY ADD_TO_CART ÇALIŞTIRILIYOR: {item_name}, {quantity}, {restaurant_id}, {user_id}")
    try:
        # Ürün fiyatını menüden al
        async with aiohttp.ClientSession() as session:
            # Önce items'dan ara
            async with session.get(f"http://localhost:8000/menu/{restaurant_id}/items") as items_response:
                items_data = await items_response.json() if items_response.status == 200 else []

            # Sonra menus'dan ara
            async with session.get(f"http://localhost:8000/menu/{restaurant_id}/menus") as menus_response:
                menus_data = await menus_response.json() if menus_response.status == 200 else []

        # Ürünü bul ve fiyatını al
        found_item = None
        item_type = "item"

        # Items'da ara
        for item in items_data:
            if item["name"].lower() == item_name.lower():
                found_item = item
                break

        # Menus'da ara
        if not found_item:
            for menu in menus_data:
                if menu["name"].lower() == item_name.lower():
                    found_item = menu
                    item_type = "menu"
                    break

        if not found_item:
            return {"success": False, "message": f"Ürün '{item_name}' menüde bulunamadı"}

        # Basit cart sistemi
        cart_key = f"cart_{restaurant_id}_{user_id}"

        if not hasattr(add_to_cart, 'carts'):
            add_to_cart.carts = {}

        if cart_key not in add_to_cart.carts:
            add_to_cart.carts[cart_key] = []

        # Ürünü sepete ekle - FİYAT BİLGİSİ İLE
        add_to_cart.carts[cart_key].append({
                "item_name": item_name,
                "quantity": quantity,
            "price": found_item["price"],
            "item_id": found_item["id"],
            "item_type": item_type,
                "restaurant_id": restaurant_id,
                "user_id": user_id
        })

        total_price = found_item["price"] * quantity

        return {
            "success": True,
            "message": f"{quantity} adet {item_name} sepete eklendi ({total_price} TL)",
            "data": add_to_cart.carts[cart_key]
        }

    except Exception as e:
        print(f"❌ ADD_TO_CART HATASI: {e}")
        return {"success": False, "message": f"Hata: {str(e)}"}

async def show_cart(restaurant_id: int, user_id: str):
    """Sepeti göster - Fiyat bilgisi ile"""
    print(f"📋 IN-MEMORY SHOW_CART ÇALIŞTIRILIYOR: {restaurant_id}, {user_id}")
    try:
        cart_key = f"cart_{restaurant_id}_{user_id}"

        # Mevcut cart'ı al
        if not hasattr(add_to_cart, 'carts'):
            add_to_cart.carts = {}

        if cart_key not in add_to_cart.carts or not add_to_cart.carts[cart_key]:
            return {"success": True, "data": [], "message": "Sepetiniz boş"}

        cart_data = add_to_cart.carts[cart_key]

        # Toplam fiyatı hesapla
        total_price = 0
        for item in cart_data:
            if "price" in item:
                total_price += item["price"] * item["quantity"]

        return {
            "success": True,
            "data": cart_data,
            "message": f"Sepet başarıyla getirildi. Toplam: {total_price} TL"
        }

    except Exception as e:
        return {"success": False, "message": f"Hata: {str(e)}"}

async def remove_from_cart(item_name: str, quantity: int, restaurant_id: int, user_id: str):
    """Sepetten ürün çıkar - Basit in-memory cart"""
    try:
        cart_key = f"cart_{restaurant_id}_{user_id}"

        # Mevcut cart'ı al
        if not hasattr(add_to_cart, 'carts'):
            add_to_cart.carts = {}

        if cart_key not in add_to_cart.carts:
            return {"success": False, "message": "Sepet boş"}

        # Ürünü bul ve çıkar
        cart = add_to_cart.carts[cart_key]
        for i, item in enumerate(cart):
            if item["item_name"] == item_name:
                if item["quantity"] <= quantity:
                    cart.pop(i)
                else:
                    item["quantity"] -= quantity
                break
        else:
            return {"success": False, "message": "Ürün sepette bulunamadı"}

        return {"success": True, "message": f"{quantity} adet {item_name} sepetten çıkarıldı", "data": cart}

    except Exception as e:
        return {"success": False, "message": f"Hata: {str(e)}"}

async def clear_cart(restaurant_id: int, user_id: str):
    """Sepeti boşalt - Basit in-memory cart"""
    try:
        cart_key = f"cart_{restaurant_id}_{user_id}"

        # Mevcut cart'ı al
        if not hasattr(add_to_cart, 'carts'):
            add_to_cart.carts = {}

        # Sepeti boşalt
        add_to_cart.carts[cart_key] = []

        return {"success": True, "message": "Sepet başarıyla boşaltıldı", "data": []}

    except Exception as e:
        return {"success": False, "message": f"Hata: {str(e)}"}

async def get_db_connection():
    """PostgreSQL bağlantısı al - .env'den"""
    try:
        conn = await asyncpg.connect(
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", "12345"),
            database=os.getenv("DB_NAME", "restaurant_db"),
            host=os.getenv("DB_HOST", "127.0.0.1"),
            port=int(os.getenv("DB_PORT", "5432"))
        )
        return conn
    except Exception as e:
        print(f"❌ DB bağlantı hatası: {e}")
        return None

async def create_order(restaurant_id: int, user_id: str, address: str = None, phone: str = None, username: str = None):
    """Sipariş oluştur - PostgreSQL veritabanına kaydet"""
    print(f"📦 CREATE_ORDER ÇALIŞTIRILIYOR: restaurant_id={restaurant_id}, user_id={user_id}, address={address}, phone={phone}")
    try:
        cart_key = f"cart_{restaurant_id}_{user_id}"

        # Mevcut cart'ı al
        if not hasattr(add_to_cart, 'carts'):
            add_to_cart.carts = {}

        if cart_key not in add_to_cart.carts or not add_to_cart.carts[cart_key]:
            return {"success": False, "message": "Sepet boş, sipariş oluşturulamaz"}

        cart_items = add_to_cart.carts[cart_key]

        # Toplam fiyatı hesapla
        total_price = 0
        for item in cart_items:
            if "price" in item:
                total_price += item["price"] * item["quantity"]

        # Adres ve telefon kontrolü
        if not address:
            return {"success": False, "message": "Adres bilgisi gerekli", "action": "ask_address"}
        if not phone:
            return {"success": False, "message": "Telefon numarası gerekli", "action": "ask_phone"}

        # Wallet kontrolü - PostgreSQL'den direkt kontrol
        if str(user_id).isdigit():
            print(f"💰 Wallet kontrolü yapılıyor: user_id={user_id}, total_price={total_price}")
            try:
                conn = await get_db_connection()
                if conn:
                    # Wallet tablosundan direkt kontrol
                    wallet_query = "SELECT balance FROM wallets WHERE user_id = $1"
                    wallet_balance = await conn.fetchval(wallet_query, int(user_id))

                    if wallet_balance is None:
                        # Wallet yoksa oluştur
                        insert_wallet = "INSERT INTO wallets (user_id, balance) VALUES ($1, 0.0) RETURNING balance"
                        wallet_balance = await conn.fetchval(insert_wallet, int(user_id))
                        print(f"🆕 Yeni wallet oluşturuldu: {wallet_balance} TL")
                    else:
                        print(f"💰 Mevcut wallet bakiyesi: {wallet_balance} TL")

                    if wallet_balance < total_price:
                        await conn.close()
                        return {
                            "success": False,
                            "message": f"Yetersiz bakiye! Mevcut: {wallet_balance} TL, Gerekli: {total_price} TL"
                        }

                    # Ödeme işlemi - wallet'tan düş
                    update_wallet = "UPDATE wallets SET balance = balance - $1 WHERE user_id = $2 RETURNING balance"
                    new_balance = await conn.fetchval(update_wallet, float(total_price), int(user_id))
                    print(f"✅ Ödeme başarılı: {total_price} TL düşüldü, yeni bakiye: {new_balance} TL")

                    await conn.close()
                else:
                    print(f"⚠️ PostgreSQL bağlantısı yok - wallet kontrolü atlanıyor")
            except Exception as wallet_error:
                print(f"⚠️ Wallet kontrolü hatası: {wallet_error}")
                print(f"🔄 Wallet kontrolü atlanıyor - test modu")
        else:
            print(f"🔄 Wallet kontrolü atlanıyor - user_id numeric değil: {user_id}")

        # PostgreSQL'e sipariş kaydet
        conn = await get_db_connection()
        if not conn:
            # Fallback: In-memory sistem
            if not hasattr(create_order, 'orders'):
                create_order.orders = {}
            order_id = f"order_{restaurant_id}_{user_id}_{int(time.time())}"
            create_order.orders[order_id] = {
                "id": order_id,
                "restaurant_id": restaurant_id,
                "user_id": user_id,
                "items": cart_items.copy(),
                "total_price": total_price,
                "status": "pending",
                "created_at": time.time()
            }
            return {"success": True, "data": create_order.orders[order_id], "message": f"Sipariş başarıyla oluşturuldu (ID: {order_id})"}

        try:
            # Orders tablosuna sipariş ekle
            order_number = f"#{int(time.time())}"
            order_query = """
                INSERT INTO orders (order_number, customer_name, customer_phone, delivery_address, status, restaurant_id, user_id, total_price, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                RETURNING id, created_at, updated_at
            """
            # Kullanıcı adını belirle
            customer_name = username if username else f"User_{user_id}"
            
            order_result = await conn.fetchrow(
                order_query,
                order_number,
                customer_name,
                phone,
                address,
                "created",
                int(restaurant_id),
                int(user_id) if str(user_id).isdigit() else None,
                float(total_price)
            )
            order_id = order_result['id']
            print(f"✅ Sipariş veritabanına kaydedildi: {order_id}")

            # Order items'ları ekle
            for item in cart_items:
                item_query = """
                    INSERT INTO order_items (order_id, item_id, menu_id, quantity, unit_price)
                    VALUES ($1, $2, $3, $4, $5)
                """
                await conn.execute(
                    item_query,
                    order_id,
                    item["item_id"] if item["item_type"] == "item" else None,
                    item["item_id"] if item["item_type"] == "menu" else None,
                    item["quantity"],
                    float(item["price"])
                )
            print(f"✅ Sipariş detayları kaydedildi: {len(cart_items)} ürün")

            # Sepeti temizle
            add_to_cart.carts[cart_key] = []

            # Sipariş detaylarını veritabanından al
            order_details_query = """
                SELECT o.*,
                COALESCE(
                    json_agg(
                        json_build_object(
                            'item_name', COALESCE(i.name, m.name),
                            'quantity', oi.quantity,
                            'unit_price', oi.unit_price,
                            'total_price', oi.quantity * oi.unit_price
                        )
                    ) FILTER (WHERE oi.id IS NOT NULL),
                    '[]'::json
                ) as items
                FROM orders o
                LEFT JOIN order_items oi ON o.id = oi.order_id
                LEFT JOIN items i ON oi.item_id = i.id
                LEFT JOIN menus m ON oi.menu_id = m.id
                WHERE o.id = $1
                GROUP BY o.id
            """
            
            order_details = await conn.fetchrow(order_details_query, order_id)
            await conn.close()

            if order_details:
                order_dict = dict(order_details)
                
                # Items JSON string'ini parse et
                if isinstance(order_dict.get('items'), str):
                    try:
                        import json
                        order_dict['items'] = json.loads(order_dict['items'])
                    except:
                        order_dict['items'] = []
                
                # Sipariş detaylarını formatla
                items_text = ""
                if order_dict['items'] and len(order_dict['items']) > 0:
                    items_text = "\n\n📋 Sipariş İçeriği:\n"
                    for item in order_dict['items']:
                        if item and item.get('item_name'):
                            items_text += f"• {item['item_name']} x{item['quantity']} = {item['total_price']} TL\n"

                created_time = ""
                if order_dict['created_at']:
                    created_time = f"\n🕐 Sipariş Zamanı: {order_dict['created_at'].strftime('%d.%m.%Y %H:%M')}"

                detailed_message = f"🎉  Sipariş Başarıyla Oluşturuldu!\n\n"
                detailed_message += f"📦 Sipariş ID: {order_dict['id']}\n"
                detailed_message += f"💰 Toplam Tutar: {order_dict['total_price']} TL\n"
                detailed_message += f"👤 Müşteri: {order_dict['customer_name']}\n"
                detailed_message += f"📞 Telefon: {order_dict['customer_phone']}\n"
                detailed_message += f"📍 Adres: {order_dict['delivery_address']}"
                detailed_message += created_time
                detailed_message += items_text
                detailed_message += f"\n\n✅ Siparişiniz alındı!"

                return {
                    "success": True,
                    "data": {
                        "id": order_dict['id'],
                        "order_number": order_dict['order_number'],
                        "restaurant_id": order_dict['restaurant_id'],
                        "user_id": order_dict['user_id'],
                        "status": order_dict['status'],
                        "total_price": float(order_dict['total_price']),
                        "customer_name": order_dict['customer_name'],
                        "customer_phone": order_dict['customer_phone'],
                        "delivery_address": order_dict['delivery_address'],
                        "created_at": order_dict['created_at'].isoformat() if order_dict['created_at'] else None,
                        "updated_at": order_dict['updated_at'].isoformat() if order_dict['updated_at'] else None,
                        "items": order_dict['items']
                    },
                    "message": detailed_message
                }
                
                return {
                    "success": True,
                    "data": {
                        "id": order_id,
                        "restaurant_id": restaurant_id,
                        "user_id": user_id,
                        "items": cart_items,
                        "total_price": total_price,
                        "status": "created"
                    },
                    "message": f"Sipariş başarıyla oluşturuldu! Sipariş No: {order_id} (Toplam: {total_price} TL)"
                }

        except Exception as db_error:
            await conn.close()
            print(f"❌ Veritabanı hatası: {db_error}")
            # Fallback: In-memory sistem
            if not hasattr(create_order, 'orders'):
                create_order.orders = {}
            order_id = f"order_{restaurant_id}_{user_id}_{int(time.time())}"
            create_order.orders[order_id] = {
                "id": order_id,
                "restaurant_id": restaurant_id,
                "user_id": user_id,
                "items": cart_items.copy(),
                "total_price": total_price,
                "status": "pending",
                "created_at": time.time()
            }
            # Fallback için detaylı mesaj oluştur
            items_text = ""
            if cart_items:
                items_text = "\n\n📋 Sipariş İçeriği:\n"
                for item in cart_items:
                    if item.get('name'):
                        items_text += f"• {item['name']} x{item['quantity']} = {item['price'] * item['quantity']} TL\n"
            
            fallback_message = f"🎉 Sipariş Başarıyla Oluşturuldu!\n\n"
            fallback_message += f"📦 Sipariş ID: {order_id}\n"
            fallback_message += f"💰 Toplam Tutar: {total_price} TL\n"
            fallback_message += f"👤 Müşteri: {username if username else f'User_{user_id}'}\n"
            fallback_message += f"📞 Telefon: {phone}\n"
            fallback_message += f"📍 Adres: {address}"
            fallback_message += items_text
            fallback_message += f"\n\n✅ Siparişiniz alındı ve hazırlanmaya başlandı!"
            
            return {"success": True, "data": create_order.orders[order_id], "message": fallback_message}

    except Exception as e:
        print(f"❌ CREATE_ORDER HATASI: {e}")
        return {"success": False, "message": f"Hata: {str(e)}"}

async def ask_for_address(restaurant_id: int, user_id: str):
    """Adres bilgisi iste"""
    print(f"🏠 ADRES SORULUYOR: restaurant_id={restaurant_id}, user_id={user_id}")
    return {
        "success": True,
        "message": "Lütfen teslimat adresinizi belirtiniz. Örnek: 'Elazığ Merkez, Atatürk Caddesi No:15'",
        "data": {"type": "address_request"}
    }

async def ask_for_phone(restaurant_id: int, user_id: str):
    """Telefon numarası iste"""
    print(f"📞 TELEFON SORULUYOR: restaurant_id={restaurant_id}, user_id={user_id}")
    return {
        "success": True,
        "message": "Lütfen telefon numaranızı belirtiniz. Örnek: '0555 123 45 67'",
        "data": {"type": "phone_request"}
    }

async def confirm_order(restaurant_id: int, user_id: str):
    """Siparişi onayla - Basit in-memory order"""
    try:
        # En son siparişi bul
        if not hasattr(create_order, 'orders'):
            return {"success": False, "message": "Onaylanacak sipariş bulunamadı"}

        # Bu kullanıcının en son siparişini bul
        user_orders = [order for order in create_order.orders.values()
                      if order["restaurant_id"] == restaurant_id and order["user_id"] == user_id]

        if not user_orders:
            return {"success": False, "message": "Onaylanacak sipariş bulunamadı"}

        # En son siparişi al
        latest_order = max(user_orders, key=lambda x: x["created_at"])

        if latest_order["status"] != "pending":
            return {"success": False, "message": "Sipariş zaten işlenmiş"}

        # Siparişi onayla
        latest_order["status"] = "confirmed"
        latest_order["confirmed_at"] = time.time()

        return {"success": True, "data": latest_order, "message": "Sipariş başarıyla onaylandı"}

    except Exception as e:
        return {"success": False, "message": f"Hata: {str(e)}"}

async def cancel_order(order_id: str, restaurant_id: int, user_id: str):
    """Siparişi iptal et - PostgreSQL + In-memory"""
    print(f"❌ CANCEL_ORDER ÇALIŞTIRILIYOR: {order_id}, {restaurant_id}, {user_id}")
    try:
        # Önce PostgreSQL'den ara
        conn = await get_db_connection()
        if conn:
            try:
                # Order ID ile ara - Items ile birlikte
                if order_id and order_id.isdigit():
                    order_query = """
                        SELECT o.*,
                        COALESCE(
                            json_agg(
                                json_build_object(
                                    'item_name', COALESCE(i.name, m.name),
                                    'quantity', oi.quantity,
                                    'unit_price', oi.unit_price
                                )
                            ) FILTER (WHERE oi.id IS NOT NULL),
                            '[]'::json
                        ) as items
                        FROM orders o
                        LEFT JOIN order_items oi ON o.id = oi.order_id
                        LEFT JOIN items i ON oi.item_id = i.id
                        LEFT JOIN menus m ON oi.menu_id = m.id
                        WHERE o.id = $1 AND o.restaurant_id = $2 AND o.user_id = $3
                        GROUP BY o.id
                    """
                    print(f"🔍 PostgreSQL sorgusu: ID={int(order_id)}, Restaurant={int(restaurant_id)}, User={int(user_id)}")
                    order_data = await conn.fetchrow(order_query, int(order_id), int(restaurant_id), int(user_id))
                    print(f"🔍 Sorgu sonucu: {order_data}")
                else:
                    # Order number ile ara - Items ile birlikte
                    order_query = """
                        SELECT o.*,
                        COALESCE(
                            json_agg(
                                json_build_object(
                                    'item_name', COALESCE(i.name, m.name),
                                    'quantity', oi.quantity,
                                    'unit_price', oi.unit_price
                                )
                            ) FILTER (WHERE oi.id IS NOT NULL),
                            '[]'::json
                        ) as items
                        FROM orders o
                        LEFT JOIN order_items oi ON o.id = oi.order_id
                        LEFT JOIN items i ON oi.item_id = i.id
                        LEFT JOIN menus m ON oi.menu_id = m.id
                        WHERE o.order_number = $1 AND o.restaurant_id = $2 AND o.user_id = $3
                        GROUP BY o.id
                    """
                    print(f"🔍 PostgreSQL sorgusu: Order Number={order_id}, Restaurant={int(restaurant_id)}, User={int(user_id)}")
                    order_data = await conn.fetchrow(order_query, order_id, int(restaurant_id), int(user_id))
                    print(f"🔍 Sorgu sonucu: {order_data}")

                if order_data:
                    order_dict = dict(order_data)
                    current_status = order_dict['status']

                    # İptal edilebilir durumları kontrol et
                    if current_status in ["cancelled", "delivering", "delivered", "on_the_way"]:
                        # Türkçe durum mesajları
                        status_messages = {
                            "cancelled": "iptal edilmiş",
                            "delivering": "yolda",
                            "delivered": "teslim edilmiş",
                            "on_the_way": "yolda"
                        }
                        
                        status_text = status_messages.get(current_status, current_status)
                        await conn.close()
                        return {
                            "success": False,
                            "message": f"Sipariş iptal edilemez! Sipariş durumu: {status_text}. Sadece 'sipariş alındı', 'hazırlanıyor' veya 'hazır' durumundaki siparişler iptal edilebilir."
                        }

                    # Siparişi iptal et
                    update_query = "UPDATE orders SET status = 'cancelled', updated_at = CURRENT_TIMESTAMP WHERE id = $1"
                    await conn.execute(update_query, order_dict['id'])
                    
                    # Wallet'a iade işlemi
                    if str(user_id).isdigit():
                        try:
                            refund_amount = float(order_dict['total_price'])
                            print(f"💰 İade işlemi başlatılıyor: {refund_amount} TL")
                            
                            # Wallet'a iade et
                            refund_query = "UPDATE wallets SET balance = balance + $1 WHERE user_id = $2 RETURNING balance"
                            new_balance = await conn.fetchval(refund_query, refund_amount, int(user_id))
                            print(f"✅ İade başarılı: {refund_amount} TL iade edildi, yeni bakiye: {new_balance} TL")
                        except Exception as refund_error:
                            print(f"⚠️ İade işlemi hatası: {refund_error}")
                    
                    await conn.close()

                    # Datetime objelerini string'e çevir
                    order_dict['created_at'] = order_dict['created_at'].isoformat() if order_dict['created_at'] else None
                    order_dict['updated_at'] = order_dict['updated_at'].isoformat() if order_dict['updated_at'] else None
                    
                    # Items JSON string'ini parse et
                    if isinstance(order_dict.get('items'), str):
                        try:
                            import json
                            order_dict['items'] = json.loads(order_dict['items'])
                        except:
                            order_dict['items'] = []
                    
                    # Detaylı iptal mesajı oluştur
                    items_text = ""
                    if order_dict['items'] and len(order_dict['items']) > 0:
                        items_text = "\n\n📋 İptal Edilen Sipariş İçeriği:\n"
                        for item in order_dict['items']:
                            if item and item.get('item_name'):
                                items_text += f"• {item['item_name']} x{item['quantity']} = {item['unit_price'] * item['quantity']} TL\n"
                    
                    created_time = ""
                    if order_dict['created_at']:
                        created_time = f"\n🕐 Sipariş Zamanı: {order_dict['created_at'][:19].replace('T', ' ')}"
                    
                    detailed_message = f"❌ Sipariş Başarıyla İptal Edildi!\n\n"
                    detailed_message += f"📦 Sipariş ID: {order_dict['id']}\n"
                    detailed_message += f"📊 Sipariş No: {order_dict['order_number']}\n"
                    detailed_message += f"💰 Toplam Tutar: {order_dict['total_price']} TL\n"
                    detailed_message += f"💳 İade Tutarı: {order_dict['total_price']} TL (wallet'a yatırıldı)\n"
                    detailed_message += f"👤 Müşteri: {order_dict['customer_name']}\n"
                    detailed_message += f"📞 Telefon: {order_dict['customer_phone']}\n"
                    detailed_message += f"📍 Adres: {order_dict['delivery_address']}"
                    detailed_message += created_time
                    detailed_message += items_text
                    detailed_message += f"\n\n✅ Siparişiniz iptal edildi ve {order_dict['total_price']} TL wallet'ınıza iade edildi!"
                    
                    return {
                        "success": True,
                        "data": order_dict,
                        "message": detailed_message
                    }
                else:
                    await conn.close()
                    return {"success": False, "message": "Sipariş bulunamadı"}

            except Exception as db_error:
                await conn.close()
                print(f"❌ PostgreSQL iptal hatası: {db_error}")

        # Fallback: In-memory sistem
        if not hasattr(create_order, 'orders'):
            return {"success": False, "message": "Sipariş bulunamadı"}

        if order_id not in create_order.orders:
            return {"success": False, "message": "Sipariş bulunamadı"}

        order = create_order.orders[order_id]

        if order["restaurant_id"] != restaurant_id or order["user_id"] != user_id:
            return {"success": False, "message": "Bu siparişe erişim yetkiniz yok"}

        # İptal edilebilir durumları kontrol et
        if order["status"] in ["cancelled", "delivering", "delivered", "on_the_way"]:
            # Türkçe durum mesajları
            status_messages = {
                "cancelled": "iptal edilmiş",
                "delivering": "yolda",
                "delivered": "teslim edilmiş",
                "on_the_way": "yolda"
            }
            
            status_text = status_messages.get(order["status"], order["status"])
            return {
                "success": False,
                "message": f"Sipariş iptal edilemez! Sipariş durumu: {status_text}. Sadece 'sipariş alındı', 'hazırlanıyor' veya 'hazır' durumundaki siparişler iptal edilebilir."
            }

        order["status"] = "cancelled"
        order["cancelled_at"] = time.time()

        # In-memory için iade işlemi (PostgreSQL wallet'a iade)
        if str(user_id).isdigit():
            try:
                refund_amount = float(order['total_price'])
                print(f"💰 In-memory iade işlemi başlatılıyor: {refund_amount} TL")
                
                # PostgreSQL wallet'a iade et
                conn = await get_db_connection()
                if conn:
                    refund_query = "UPDATE wallets SET balance = balance + $1 WHERE user_id = $2 RETURNING balance"
                    new_balance = await conn.fetchval(refund_query, refund_amount, int(user_id))
                    await conn.close()
                    print(f"✅ In-memory iade başarılı: {refund_amount} TL iade edildi, yeni bakiye: {new_balance} TL")
                else:
                    print(f"⚠️ PostgreSQL bağlantısı yok - iade işlemi atlanıyor")
            except Exception as refund_error:
                print(f"⚠️ In-memory iade işlemi hatası: {refund_error}")

        # Detaylı iptal mesajı oluştur (in-memory)
        items_text = ""
        if order.get("items"):
            items_text = "\n\n📋 İptal Edilen Sipariş İçeriği:\n"
            for item in order["items"]:
                if item and item.get("item_name"):
                    items_text += f"• {item['item_name']} x{item['quantity']} = {item['price'] * item['quantity']} TL\n"
        
        created_time = ""
        if order.get("created_at"):
            created_time = f"\n🕐 Sipariş Zamanı: {time.strftime('%d.%m.%Y %H:%M', time.localtime(order['created_at']))}"
        
        detailed_message = f"❌ Sipariş Başarıyla İptal Edildi!\n\n"
        detailed_message += f"📦 Sipariş ID: {order_id}\n"
        detailed_message += f"💰 Toplam Tutar: {order['total_price']} TL\n"
        detailed_message += f"💳 İade Tutarı: {order['total_price']} TL (wallet'a yatırıldı)\n"
        detailed_message += f"👤 Müşteri: User_{order['user_id']}\n"
        detailed_message += f"🏪 Restoran ID: {order['restaurant_id']}"
        detailed_message += created_time
        detailed_message += items_text
        detailed_message += f"\n\n✅ Siparişiniz iptal edildi ve {order['total_price']} TL wallet'ınıza iade edildi!"

        return {"success": True, "data": order, "message": detailed_message}

    except Exception as e:
        print(f"❌ CANCEL_ORDER HATASI: {e}")
        return {"success": False, "message": f"Hata: {str(e)}"}

async def get_order_status(order_id: str, restaurant_id: int, user_id: str):
    """Sipariş durumunu getir - PostgreSQL'den arama"""
    print(f"📋 GET_ORDER_STATUS ÇALIŞTIRILIYOR: order_id='{order_id}', restaurant_id={restaurant_id}, user_id={user_id}")
    print(f"🔍 Order ID type: {type(order_id)}, isdigit: {order_id.isdigit() if order_id else 'None'}")
    try:
        # Önce PostgreSQL'den ara
        conn = await get_db_connection()
        if conn:
            try:
                # Order ID ile ara (numeric ise)
                if order_id and order_id.isdigit():
                    order_query = """
                        SELECT o.*,
                        COALESCE(
                            json_agg(
                                json_build_object(
                                    'item_name', COALESCE(i.name, m.name),
                                    'quantity', oi.quantity,
                                    'unit_price', oi.unit_price
                                )
                            ) FILTER (WHERE oi.id IS NOT NULL),
                            '[]'::json
                        ) as items
                        FROM orders o
                        LEFT JOIN order_items oi ON o.id = oi.order_id
                        LEFT JOIN items i ON oi.item_id = i.id
                        LEFT JOIN menus m ON oi.menu_id = m.id
                        WHERE o.id = $1 AND o.restaurant_id = $2 AND o.user_id = $3
                        GROUP BY o.id
                    """
                    print(f"🔍 PostgreSQL sorgusu: ID={order_id}, Restaurant={restaurant_id}, User={user_id}")
                    order_data = await conn.fetchrow(order_query, int(order_id), int(restaurant_id), int(user_id) if str(user_id).isdigit() else None)
                    print(f"🔍 Sorgu sonucu: {order_data}")
                elif order_id:
                    # Order number ile ara (#timestamp formatında)
                    order_query = """
                        SELECT o.*,
                        COALESCE(
                            json_agg(
                                json_build_object(
                                    'item_name', COALESCE(i.name, m.name),
                                    'quantity', oi.quantity,
                                    'unit_price', oi.unit_price
                                )
                            ) FILTER (WHERE oi.id IS NOT NULL),
                            '[]'::json
                        ) as items
                        FROM orders o
                        LEFT JOIN order_items oi ON o.id = oi.order_id
                        LEFT JOIN items i ON oi.item_id = i.id
                        LEFT JOIN menus m ON oi.menu_id = m.id
                        WHERE o.order_number = $1 AND o.restaurant_id = $2 AND o.user_id = $3
                        GROUP BY o.id
                    """
                    print(f"🔍 PostgreSQL sorgusu: Order Number={order_id}, Restaurant={restaurant_id}, User={user_id}")
                    order_data = await conn.fetchrow(order_query, order_id, int(restaurant_id), int(user_id) if str(user_id).isdigit() else None)
                    print(f"🔍 Sorgu sonucu: {order_data}")
                else:
                    # Order ID yoksa son siparişi getir
                    order_query = """
                        SELECT o.*,
                        COALESCE(
                            json_agg(
                                json_build_object(
                                    'item_name', COALESCE(i.name, m.name),
                                    'quantity', oi.quantity,
                                    'unit_price', oi.unit_price
                                )
                            ) FILTER (WHERE oi.id IS NOT NULL),
                            '[]'::json
                        ) as items
                        FROM orders o
                        LEFT JOIN order_items oi ON o.id = oi.order_id
                        LEFT JOIN items i ON oi.item_id = i.id
                        LEFT JOIN menus m ON oi.menu_id = m.id
                        WHERE o.restaurant_id = $1 AND o.user_id = $2
                        GROUP BY o.id
                        ORDER BY o.created_at DESC
                        LIMIT 1
                    """
                    print(f"🔍 PostgreSQL sorgusu: Son sipariş, Restaurant={restaurant_id}, User={user_id}")
                    order_data = await conn.fetchrow(order_query, int(restaurant_id), int(user_id) if str(user_id).isdigit() else None)
                    print(f"🔍 Sorgu sonucu: {order_data}")

                await conn.close()

                if order_data:
                    # Record objesini dictionary'ye çevir - asyncpg Record objesi
                    order_dict = dict(order_data)
                    
                    # Items JSON string'ini parse et
                    if isinstance(order_dict.get('items'), str):
                        try:
                            import json
                            order_dict['items'] = json.loads(order_dict['items'])
                        except:
                            order_dict['items'] = []
                    
                    status_messages = {
                        "created": "Sipariş alındı",
                        "sipariş alındı": "Sipariş alındı",
                        "preparing": "Hazırlanıyor",
                        "ready": "Hazır",
                        "on_the_way": "Yolda",
                        "delivering": "Yolda",
                        "delivered": "Teslim edildi",
                        "cancelled": "İptal edildi"
                    }

                    status_text = status_messages.get(order_dict['status'], order_dict['status'])

                    items_text = ""
                    if order_dict['items'] and len(order_dict['items']) > 0:
                        items_text = "\n\n📋 Sipariş İçeriği:\n"
                        for item in order_dict['items']:
                            if item and item.get('item_name'):
                                items_text += f"• {item['item_name']} x{item['quantity']} = {item['unit_price'] * item['quantity']} TL\n"

                    created_time = ""
                    if order_dict['created_at']:
                        created_time = f"\n🕐 Sipariş Zamanı: {order_dict['created_at'].strftime('%d.%m.%Y %H:%M')}"

                    detailed_message = f"📦 Sipariş ID: {order_dict['id']}\n"
                    detailed_message += f"📊 Durum: {status_text}\n"
                    detailed_message += f"💰 Toplam: {order_dict['total_price']} TL\n"
                    detailed_message += f"👤 Müşteri: {order_dict['customer_name']}\n"
                    detailed_message += f"📞 Telefon: {order_dict['customer_phone']}\n"
                    detailed_message += f"📍 Adres: {order_dict['delivery_address']}"
                    detailed_message += created_time
                    detailed_message += items_text

                    return {
                        "success": True,
                        "data": {
                            "id": order_dict['id'],
                            "order_number": order_dict['order_number'],
                            "restaurant_id": order_dict['restaurant_id'],
                            "user_id": order_dict['user_id'],
                            "status": order_dict['status'],
                            "status_text": status_text,
                            "total_price": float(order_dict['total_price']),
                            "customer_name": order_dict['customer_name'],
                            "customer_phone": order_dict['customer_phone'],
                            "delivery_address": order_dict['delivery_address'],
                            "created_at": order_dict['created_at'].isoformat() if order_dict['created_at'] else None,
                            "updated_at": order_dict['updated_at'].isoformat() if order_dict['updated_at'] else None,
                            "items": order_dict['items']
                        },
                        "message": detailed_message
                    }
                else:
                    return {"success": False, "message": "Sipariş bulunamadı"}

            except Exception as db_error:
                await conn.close()
                print(f"❌ PostgreSQL arama hatası: {db_error}")

        # PostgreSQL'de bulunamazsa in-memory'de ara
        if not hasattr(create_order, 'orders'):
            return {"success": False, "message": "Sipariş bulunamadı"}

            if order_id:
            # Belirli siparişi getir
            if order_id not in create_order.orders:
                return {"success": False, "message": "Sipariş bulunamadı"}

            order = create_order.orders[order_id]

            if order["restaurant_id"] != restaurant_id or order["user_id"] != user_id:
                return {"success": False, "message": "Bu siparişe erişim yetkiniz yok"}

            return {"success": True, "data": order, "message": "Sipariş durumu başarıyla getirildi"}
                else:
            # Kullanıcının tüm siparişlerini getir
            user_orders = [order for order in create_order.orders.values()
                          if order["restaurant_id"] == restaurant_id and order["user_id"] == user_id]

            if not user_orders:
                return {"success": False, "message": "Sipariş bulunamadı"}

            return {"success": True, "data": user_orders, "message": "Siparişler başarıyla getirildi"}

    except Exception as e:
        print(f"❌ GET_ORDER_STATUS HATASI: {e}")
        return {"success": False, "message": f"Hata: {str(e)}"}

async def call_function(function_name: str, arguments: dict, restaurant_id: int, user_id: str, context: dict = None):
    """Function call'ı execute et"""
    print(f"🔧 Executing function: {function_name} with args: {arguments}")
    print(f"🏗️ SİSTEM MİMARİSİ DEBUG:")
    print(f"  📡 1. OpenAI Realtime API (Birincil) - Function call tetiklendi")
    print(f"  🚀 2. FastAPI Backend - Function handler çalışıyor")
    print(f"  🗄️ 3. PostgreSQL Database - Veri işlemleri")
    print(f"  🔄 4. Fallback Sistemleri - In-memory backup")
    print(f"")
    
    if function_name == "show_menu":
        print(f"🍽️ SHOW_MENU: Backend API → Menu endpoints → PostgreSQL")
        return await show_menu(restaurant_id)
    elif function_name == "add_to_cart":
        item_name = arguments.get("item_name", "hamburger")
        quantity = arguments.get("quantity", 1)
        print(f"🛒 ADD_TO_CART: In-memory cart system (PostgreSQL fallback)")
        return await add_to_cart(item_name, quantity, restaurant_id, user_id)
    elif function_name == "show_cart":
        print(f"📋 SHOW_CART: In-memory cart system")
        return await show_cart(restaurant_id, user_id)
    elif function_name == "remove_from_cart":
        item_name = arguments.get("item_name", "hamburger")
        quantity = arguments.get("quantity", 1)
        print(f"🗑️ REMOVE_FROM_CART: In-memory cart system")
        return await remove_from_cart(item_name, quantity, restaurant_id, user_id)
    elif function_name == "clear_cart":
        print(f"🧹 CLEAR_CART: In-memory cart system")
        return await clear_cart(restaurant_id, user_id)
    elif function_name == "create_order":
        address = arguments.get("address", "")
        phone = arguments.get("phone", "")
        # Context'ten username al, yoksa arguments'tan al
        username = (context.get("username") if context else None) or arguments.get("username", None)
        print(f"📦 CREATE_ORDER: PostgreSQL primary + In-memory fallback")
        print(f"👤 Username from context: {username}")
        return await create_order(restaurant_id, user_id, address, phone, username)
    elif function_name == "confirm_order":
        print(f"✅ CONFIRM_ORDER: In-memory order system")
        return await confirm_order(restaurant_id, user_id)
    elif function_name == "cancel_order":
        order_id = arguments.get("order_id", "1")
        print(f"❌ CANCEL_ORDER: In-memory order system")
        return await cancel_order(order_id, restaurant_id, user_id)
    elif function_name == "get_order_status":
        order_id = arguments.get("order_id", "")
        print(f"📋 GET_ORDER_STATUS: PostgreSQL primary + In-memory fallback")
        print(f"🔍 GET_ORDER_STATUS ARGUMENTS: {arguments}")
        print(f"🔍 EXTRACTED ORDER_ID: '{order_id}' (type: {type(order_id)})")
        return await get_order_status(order_id, restaurant_id, user_id)
    elif function_name == "ask_for_address":
        print(f"🏠 ASK_FOR_ADDRESS: Simple response function")
        return await ask_for_address(restaurant_id, user_id)
    elif function_name == "ask_for_phone":
        print(f"📞 ASK_FOR_PHONE: Simple response function")
        return await ask_for_phone(restaurant_id, user_id)
    else:
        print(f"❌ UNKNOWN_FUNCTION: {function_name}")
        return {"success": False, "message": f"Unknown function: {function_name}"}

@router.websocket("/realtime")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint - OpenAI Realtime API ile function call sistemi"""
    websocket_id = str(id(websocket))
    
    try:
        await manager.connect(websocket, websocket_id)
        
        # OpenAI Realtime API'ye bağlan
        openai_ws = await websockets.connect(
            OPENAI_REALTIME_URL,
            extra_headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "OpenAI-Beta": "realtime=v1"
            }
        )
        manager.openai_connections[websocket_id] = openai_ws
        print(f"✅ OpenAI WebSocket bağlandı: {websocket_id}")
        
        # Session oluştur
        session_update = {
            "type": "session.update",
            "session": {
                "modalities": ["text"],
                "instructions": """Sen bir restoran asistanısın. Kullanıcılarla Türkçe konuşuyorsun ve MUTLAKA uygun fonksiyonları çağırmalısın.

FONKSİYON KULLANIM KURALLARI:

1. MENÜ İŞLEMLERİ:
   - "menü", "menüyü göster", "ne var", "yemekler" → show_menu() çağır
   - "X ekle", "X sepete ekle", "X al" → add_to_cart(item_name="X") çağır
   - "sepet", "sepeti göster", "sepetim" → show_cart() çağır

2. SİPARİŞ DURUMU SORGULAMA:
   - "sipariş durumu", "siparişim nerede", "siparişim ne durumda" → get_order_status() çağır
   - "X numaralı sipariş", "sipariş no X", "X. sipariş" → get_order_status(order_id="X") çağır
   - "son siparişim", "en son sipariş" → get_order_status() çağır (order_id olmadan)

3. SİPARİŞ OLUŞTURMA:
   - "sipariş ver", "sipariş oluştur", "sipariş et" → ÖNCE ask_for_address() ve ask_for_phone() çağır, SONRA create_order() çağır

4. SİPARİŞ YÖNETİMİ:
   - "siparişi iptal et", "iptal et" → cancel_order(order_id="X") çağır
   - "siparişi onayla" → confirm_order() çağır

SİPARİŞ DURUMU KONTROLÜ:
- Sipariş durumları: "sipariş alındı", "hazırlanıyor", "hazır", "yolda", "teslim edildi", "iptal edildi"
- "yolda", "yolda gidiyor", "delivering" → aynı durum (yolda)
- "teslim edildi", "delivered" → aynı durum (teslim edildi)
- "iptal edildi", "cancelled" → aynı durum (iptal edildi)

İPTAL KURALLARI:
- Sadece "sipariş alındı", "hazırlanıyor", "hazır" durumundaki siparişler iptal edilebilir
- "yolda", "teslim edildi", "iptal edildi" durumundaki siparişler iptal EDİLEMEZ
- Zaten iptal edilmiş siparişler tekrar iptal edilemez

ÖNEMLİ: Her zaman uygun fonksiyonu çağır, sadece metin cevap verme! Kullanıcı sipariş numarası belirtirse, o numarayı order_id parametresine geçir.""",
                "tools": RESTAURANT_TOOLS,
                "tool_choice": "required",
                "temperature": 0.8
            }
        }
        
        await openai_ws.send(json.dumps(session_update))
        print("📤 Session update gönderildi")
        
        # OpenAI'dan gelen mesajları dinle
        async def handle_openai_messages():
            try:
                async for message in openai_ws:
                    data = json.loads(message)
                    print(f"📥 OpenAI Event: {data.get('type', 'unknown')}")
                    
                    if data.get("type") == "session.updated":
                        print("✅ Session güncellendi")
                    elif data.get("type") == "conversation.item.created":
                        print("✅ Conversation item oluşturuldu")
                    elif data.get("type") == "response.created":
                        print("✅ Response oluşturuldu")
                    elif data.get("type") == "response.output_item.done":
                        print("✅ Response output item tamamlandı")
                        item = data.get("item", {})
                        print(f"🔍 Output item type: {item.get('type')}")
                        
                        # Function call'ları kontrol et
                        if item.get("type") == "function_call":
                            function_name = item.get("name")
                            arguments_str = item.get("arguments", "{}")
                            call_id = item.get("call_id")
                            
                            try:
                                arguments = json.loads(arguments_str)
                            except:
                                arguments = {}
                            
                            print(f"🔧 Function call detected: {function_name}")
                            print(f"🔧 Arguments: {arguments}")
                            print(f"🔧 Call ID: {call_id}")

                            # Değişkenleri al - bu bağlantının context'inden
                            context = manager.connection_context.get(websocket_id, {})
                            current_restaurant_id = context.get("restaurant_id", 10)
                            current_user_id = context.get("user_id", "system")

                            print(f"🎯 Context: restaurant_id={current_restaurant_id}, user_id={current_user_id}")
                            
                            # Function'ı execute et
                            current_context = manager.connection_context.get(websocket_id, {})
                            result = await call_function(function_name, arguments, current_restaurant_id, current_user_id, current_context)
                            
                            # Sonucu OpenAI'a gönder
                            function_output = {
                                "type": "conversation.item.create",
                                "item": {
                                    "type": "function_call_output",
                                    "call_id": call_id,
                                    "output": json.dumps(result)
                                }
                            }
                            
                            await openai_ws.send(json.dumps(function_output))
                            print(f"📤 Function result gönderildi: {function_name}")
                            
                            # Client'a da gönder
                            await websocket.send_text(json.dumps({
                                "type": "function_result",
                                "result": result
                            }))
                    
                            # Eğer menü getirildiyse, menü içeriğini de gönder - KALDIRILDI (duplicate)
                            # if function_name == "show_menu" and result.get("success") and result.get("data"):
                            #     await websocket.send_text(json.dumps({
                            #         "type": "menu_data",
                            #         "data": result["data"]
                            #     }))
                            #     print(f"📋 Menü verisi gönderildi: {len(result['data'])} kategori")
                        else:
                            print(f"❌ Function call değil, type: {item.get('type')}")
                    
                    elif data.get("type") == "response.done":
                        print("✅ Response tamamlandı")
                    elif data.get("type") == "error":
                        print(f"❌ OpenAI Error: {data.get('error', {})}")
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "message": f"OpenAI Error: {data.get('error', {})}"
                        }))
                    elif data.get("type") == "response.text.delta":
                        # Text response'u client'a gönder
                        text_content = data.get("delta", "")
                        if text_content:
                            await websocket.send_text(json.dumps({
                                "type": "response_text",
                                "content": text_content
                            }))
                    elif data.get("type") == "response_completed":
                        await websocket.send_text(json.dumps({
                            "type": "response_completed"
                        }))
                        
            except Exception as e:
                print(f"❌ OpenAI message handling error: {e}")
        
        # OpenAI mesajlarını handle et
        openai_task = asyncio.create_task(handle_openai_messages())
        
        # Client mesajlarını dinle
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            print(f"📨 Client mesajı: {message_data.get('type', 'unknown')}")
            
            if message_data.get("type") == "conversation.item.create":
                user_message = message_data.get("item", {}).get("content", [{}])[0].get("text", "")
                restaurant_id = message_data.get("restaurant_id", 10)
                user_id = message_data.get("user_id", "system")
                username = message_data.get("username", None)  # Frontend'den username al
                
                print(f"💬 User: {user_message}")
                print(f"🏪 Restaurant: {restaurant_id}")
                print(f"👤 User ID: {user_id}")
                print(f"👤 Username: {username}")

                # Bu bağlantı için context'i güncelle
                manager.connection_context[websocket_id] = {
                    "restaurant_id": restaurant_id,
                    "user_id": user_id,
                    "username": username
                }
                
                # OpenAI'a mesaj gönder
                conversation_item = {
                    "type": "conversation.item.create",
                    "item": {
                        "type": "message",
                        "role": "user",
                        "content": [
                            {
                                "type": "input_text",
                                "text": user_message
                            }
                        ]
                    }
                }
                
                await openai_ws.send(json.dumps(conversation_item))
                print("📤 User message OpenAI'a gönderildi")
                
                # Response oluştur
                response_create = {
                    "type": "response.create"
                    }
                await openai_ws.send(json.dumps(response_create))
                print("📤 Response create gönderildi")
                    
    except WebSocketDisconnect:
        print(f"🔌 Client bağlantısı kesildi: {websocket_id}")
    except Exception as e:
        print(f"❌ WebSocket hatası: {e}")
        try:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": f"Sunucu hatası: {str(e)}"
            }))
        except:
            pass
    finally:
        # OpenAI bağlantısını kapat
        if websocket_id in manager.openai_connections:
            await manager.openai_connections[websocket_id].close()
        manager.disconnect(websocket_id)
