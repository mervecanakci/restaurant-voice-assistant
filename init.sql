-- Restaurant Ordering API - Veritabanı Tabloları
-- PostgreSQL için SQL script

-- Restoranlar tablosu
CREATE TABLE IF NOT EXISTS restaurants (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    address TEXT,
    phone VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Menü öğeleri tablosu
CREATE TABLE IF NOT EXISTS items (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    price DECIMAL(10,2) NOT NULL,
    type VARCHAR(20) NOT NULL CHECK (type IN ('food', 'drink', 'dessert')),
    restaurant_id INTEGER NOT NULL REFERENCES restaurants(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Menüler tablosu
CREATE TABLE IF NOT EXISTS menus (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    restaurant_id INTEGER NOT NULL REFERENCES restaurants(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Menü-Öğe ilişki tablosu (Many-to-Many)
CREATE TABLE IF NOT EXISTS menu_items (
    menu_id INTEGER NOT NULL REFERENCES menus(id) ON DELETE CASCADE,
    item_id INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    PRIMARY KEY (menu_id, item_id)
);

-- Siparişler tablosu
CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    customer_name VARCHAR(255) NOT NULL,
    customer_phone VARCHAR(50) NOT NULL,
    delivery_address TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'created' CHECK (status IN ('created', 'paid', 'preparing', 'delivering', 'delivered', 'cancelled')),
    restaurant_id INTEGER NOT NULL REFERENCES restaurants(id),
    total_price DECIMAL(10,2) DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Sipariş öğeleri tablosu
CREATE TABLE IF NOT EXISTS order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    item_id INTEGER REFERENCES items(id),
    menu_id INTEGER REFERENCES menus(id),
    quantity INTEGER DEFAULT 1,
    unit_price DECIMAL(10,2) DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- İndeksler
CREATE INDEX IF NOT EXISTS idx_items_restaurant_id ON items(restaurant_id);
CREATE INDEX IF NOT EXISTS idx_items_type ON items(type);
CREATE INDEX IF NOT EXISTS idx_menus_restaurant_id ON menus(restaurant_id);
CREATE INDEX IF NOT EXISTS idx_orders_restaurant_id ON orders(restaurant_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items(order_id);

-- Trigger fonksiyonları
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger'ları oluştur
DROP TRIGGER IF EXISTS update_restaurants_updated_at ON restaurants;
CREATE TRIGGER update_restaurants_updated_at
    BEFORE UPDATE ON restaurants
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_items_updated_at ON items;
CREATE TRIGGER update_items_updated_at
    BEFORE UPDATE ON items
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_menus_updated_at ON menus;
CREATE TRIGGER update_menus_updated_at
    BEFORE UPDATE ON menus
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_orders_updated_at ON orders;
CREATE TRIGGER update_orders_updated_at
    BEFORE UPDATE ON orders
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
