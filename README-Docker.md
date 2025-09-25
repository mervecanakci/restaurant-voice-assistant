# Restaurant App - Docker Kurulumu

## 🐳 Docker ile Çalıştırma

### Gereksinimler
- Docker
- Docker Compose

### Hızlı Başlatma

```bash
# Projeyi klonlayın
git clone <repository-url>
cd restaurant_app

# Docker ile başlatın
./docker-start.sh
```

### Manuel Kurulum

1. **Environment dosyasını oluşturun:**
```bash
cp .env.example .env
# .env dosyasını düzenleyin
```

2. **Docker Compose ile başlatın:**
```bash
docker-compose up --build -d
```

3. **Servisleri kontrol edin:**
```bash
docker-compose ps
```

### Erişim Adresleri

- **Ana Uygulama:** http://localhost:8000
- **Sesli Asistan:** http://localhost:9000/voice_assistant.html?restaurant_id=7
- **Admin Panel:** http://localhost:9000/admin.html

### Test Kullanıcıları

- **Admin:** admin / admin123
- **Müşteri:** mervekullanici1 / mervekullanici1
- **Restoran:** guzelresto / guzelresto

### Docker Komutları

```bash
# Servisleri başlat
docker-compose up -d

# Servisleri durdur
docker-compose down

# Logları görüntüle
docker-compose logs -f

# Veritabanını sıfırla
docker-compose down -v
docker-compose up --build -d
```

### Sorun Giderme

1. **Port çakışması:**
   - `docker-compose.yml` dosyasındaki port numaralarını değiştirin

2. **Veritabanı bağlantı hatası:**
   - PostgreSQL servisinin tamamen başlamasını bekleyin
   - `docker-compose logs postgres` ile logları kontrol edin

3. **OpenAI API hatası:**
   - `.env` dosyasındaki API key'i kontrol edin
   - API key'in geçerli olduğundan emin olun

### Geliştirme

```bash
# Geliştirme modunda çalıştır (hot reload)
docker-compose -f docker-compose.dev.yml up

# Sadece veritabanını çalıştır
docker-compose up postgres -d
```
