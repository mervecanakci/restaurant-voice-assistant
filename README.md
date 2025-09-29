# 🍽️ Restaurant Voice Assistant

Modern AI destekli sesli restoran sipariş sistemi. OpenAI Realtime API, FastAPI ve PostgreSQL kullanarak geliştirilmiş, Docker ile containerize edilmiş tam kapsamlı bir restoran yönetim platformu.

## 🚀 Özellikler

### 🎤 Sesli Asistan
- **OpenAI Realtime API** ile gerçek zamanlı konuşma
- **Web Speech API** ile sesli komut tanıma
- **Text-to-Speech** ile sesli yanıtlar
- Türkçe dil desteği

### 🛒 Sipariş Yönetimi
- Sesli sipariş oluşturma
- Sepet yönetimi (ekleme, çıkarma, temizleme)
- Gerçek zamanlı sipariş durumu takibi
- Otomatik ödeme sistemi (wallet entegrasyonu)

### 🏪 Restoran Yönetimi
- Menü yönetimi (tek ürünler ve combo menüler)
- Sipariş durumu güncelleme
- Müşteri bilgileri yönetimi
- Admin paneli

### 👥 Kullanıcı Rolleri
- **Admin**: Sistem yönetimi
- **Restoran**: Menü ve sipariş yönetimi
- **Müşteri**: Sipariş verme ve takip

## 🏗️ Sistem Mimarisi

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   FastAPI       │    │   PostgreSQL    │
│   (HTML/JS)     │◄──►│   Backend       │◄──►│   Database      │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │
         │                       │
         ▼                       ▼
┌─────────────────┐    ┌─────────────────┐
│ OpenAI Realtime│    │   WebSocket     │
│      API       │    │   Connection    │
└─────────────────┘    └─────────────────┘
```

## 🐳 Docker Kurulumu

### Gereksinimler
- Docker ve Docker Compose
- OpenAI API Key

### Hızlı Başlangıç

1. **Projeyi klonlayın:**
```bash
git clone <repository-url>
cd restaurant-voice-assistant
```

2. **Docker ile başlatın:**
```bash
chmod +x docker-start.sh
./docker-start.sh
```

3. **Tarayıcıda açın:**
- Frontend: http://localhost:9000
- API: http://localhost:8000
- PostgreSQL: localhost:5433

### Manuel Kurulum

1. **Environment dosyası oluşturun:**
```bash
cp env.example .env
# .env dosyasını düzenleyin ve OpenAI API key'inizi ekleyin
```

2. **Docker Compose ile başlatın:**
```bash
docker-compose up -d
```

3. **Veritabanını başlatın:**
```bash
docker-compose exec app python -m app.db.init_db
```

## 🔑 Kullanıcı Bilgileri

### Admin Kullanıcısı
- **Kullanıcı Adı:** `admin`
- **Şifre:** `123`
- **E-posta:** admin@restaurant.com
- **Rol:** admin

### Restoran Kullanıcıları
| Kullanıcı Adı | Restoran Adı | Şifre | Telefon |
|---------------|--------------|-------|---------|
| pideci23 | pideci23 | 123 | 05523388778 |
| guzelresto | Güzel Resto | 123 | 055599988777 |
| pizzapalace | Pizza Palace | 123 | 05551234567 |
| burgerking | burger king | 123 | 05523388778 |
| test_restaurant | Updated Restaurant | 123 | 05559998877 |

### Müşteri Kullanıcıları
| Kullanıcı Adı | E-posta | Şifre |
|---------------|---------|-------|
| system | mervecanakci95@gmail.com | 123 |
| merve | merve@test.com | 123 |
| customer1 | customer1@test.com | 123 |
| testcustomer | test@test.com | 123 |
| testuser1 | test1@example.com | 123 |
| testuser2 | test2@example.com | 123 |
| testuser3 | test3@example.com | 123 |
| testuser5 | test5@test.com | 123 |
| mervekullanici11 | mervecanakci23@gmail.com | 123 |
| mervekullanici114 | mervecanakci2i3@gmail.com | 123 |
| testmerve | testmerve@test.com | 123 |

## 🎯 Kullanım Kılavuzu

### Sesli Asistan Kullanımı

1. **Giriş Yapın:** http://localhost:9000/login.html
2. **Restoran Seçin:** Giriş yaptıktan sonra restoran seçin
3. **Sesli Asistan:** http://localhost:9000/voice_assistant.html?restaurant_id=X

### Sesli Komutlar

#### Menü İşlemleri
- "Menüyü göster"
- "Pizza küçük boy sepete ekle"
- "Hamburger 2 adet sepete ekle"

#### Sepet İşlemleri
- "Sepeti göster"
- "Sepeti temizle"
- "Pizza'yı sepetten çıkar"

#### Sipariş İşlemleri
- "Siparişi oluştur"
- "Sipariş numarası 65'in durumu ne?"
- "Siparişi iptal et"

### Admin Paneli

1. **Admin Girişi:** admin / 123
2. **Panel:** http://localhost:9000/admin.html
3. **Özellikler:**
   - Kullanıcı yönetimi
   - Restoran yönetimi
   - Sipariş takibi
   - Sistem istatistikleri

### Restoran Paneli

1. **Restoran Girişi:** restoran_kullanici_adi / 123
2. **Panel:** http://localhost:9000/restaurant.html
3. **Özellikler:**
   - Menü yönetimi
   - Sipariş durumu güncelleme
   - Müşteri bilgileri

## 🔧 API Endpoints

### Authentication
- `POST /auth/login` - Kullanıcı girişi
- `POST /auth/register` - Kullanıcı kaydı

### Menu Management
- `GET /menu/{restaurant_id}/items` - Tek ürünler
- `GET /menu/{restaurant_id}/menus` - Combo menüler
- `POST /menu/{restaurant_id}/items` - Ürün ekleme

### Order Management
- `GET /orders/{order_id}` - Sipariş detayı
- `POST /orders` - Sipariş oluşturma
- `PUT /orders/{order_id}/status` - Sipariş durumu güncelleme

### Wallet Management
- `GET /wallet/{user_id}` - Wallet bakiyesi
- `POST /wallet/{user_id}/add` - Bakiye ekleme

## 🗄️ Veritabanı Yapısı

### Ana Tablolar
- **users**: Kullanıcı bilgileri
- **restaurants**: Restoran bilgileri
- **items**: Tek ürünler
- **menus**: Combo menüler
- **orders**: Siparişler
- **order_items**: Sipariş detayları
- **wallets**: Cüzdan bilgileri

### İlişkiler
- Users → Orders (1:N)
- Restaurants → Orders (1:N)
- Orders → Order_Items (1:N)
- Items → Order_Items (1:N)
- Menus → Order_Items (1:N)

## 🛠️ Geliştirme

### Gereksinimler
- Python 3.8+
- Node.js (frontend için)
- Docker & Docker Compose

### Yerel Geliştirme

1. **Virtual Environment:**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# veya
venv\Scripts\activate     # Windows
```

2. **Bağımlılıkları yükleyin:**
```bash
pip install -r requirements.txt
```

3. **Veritabanını başlatın:**
```bash
# PostgreSQL'i başlatın
# DATABASE_URL'i .env dosyasında ayarlayın
python -m app.db.init_db
```

4. **Uygulamayı başlatın:**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Docker Geliştirme

```bash
# Development environment
docker-compose -f docker-compose.dev.yml up -d

# Production environment
docker-compose up -d
```

## 🔒 Güvenlik

- **Şifreleme:** SHA256 hash ile şifre koruması
- **JWT Token:** Güvenli kimlik doğrulama
- **CORS:** Cross-origin istek koruması
- **Input Validation:** Giriş verisi doğrulama

## 📊 Monitoring ve Logging

- **WebSocket Bağlantıları:** Gerçek zamanlı izleme
- **API İstekleri:** Detaylı loglama
- **Hata Yönetimi:** Kapsamlı hata yakalama
- **Performance:** Response time izleme

## 🚀 Deployment

### Production Deployment

1. **Environment Variables:**
```bash
OPENAI_API_KEY=your_openai_api_key
DATABASE_URL=postgresql://user:pass@host:port/db
SECRET_KEY=your_secret_key
ENVIRONMENT=production
```

2. **Docker Compose:**
```bash
docker-compose -f docker-compose.prod.yml up -d
```

3. **SSL Certificate:** Nginx reverse proxy ile SSL

### Scaling

- **Horizontal Scaling:** Multiple app instances
- **Database Scaling:** PostgreSQL read replicas
- **Load Balancing:** Nginx load balancer
- **Caching:** Redis cache layer

## 🤝 Katkıda Bulunma

1. Fork yapın
2. Feature branch oluşturun (`git checkout -b feature/amazing-feature`)
3. Commit yapın (`git commit -m 'Add amazing feature'`)
4. Push yapın (`git push origin feature/amazing-feature`)
5. Pull Request oluşturun

## 📝 Lisans

Bu proje MIT lisansı altında lisanslanmıştır. Detaylar için `LICENSE` dosyasına bakın.

## 📞 Destek

- **Issues:** GitHub Issues
- **Email:** support@restaurant-voice-assistant.com
- **Documentation:** Wiki sayfası

## 🙏 Teşekkürler

- OpenAI Realtime API
- FastAPI framework
- PostgreSQL database
- Docker containerization
- Web Speech API

---

**Not:** Bu sistem demo amaçlı geliştirilmiştir. Production kullanımı için ek güvenlik önlemleri alınması önerilir.
