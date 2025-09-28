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

- **FastAPI Backend:** http://localhost:8000
- **API Dokümantasyonu:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/health
- **Frontend:** http://localhost:9000
- **Sesli Asistan:** http://localhost:9000/voice_assistant.html?restaurant_id=7
- **Admin Panel:** http://localhost:9000/admin.html
- **PostgreSQL:** localhost:5433

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
   - Çakışan servisleri durdurun: `sudo pkill -f uvicorn`

2. **Veritabanı bağlantı hatası:**
   - PostgreSQL servisinin tamamen başlamasını bekleyin
   - `docker-compose logs postgres` ile logları kontrol edin
   - PostgreSQL portu 5433'e değiştirildi

3. **Python modül hatası:**
   - `httpx` ve `email-validator` modülleri requirements.txt'e eklendi
   - Container'ı yeniden build edin: `docker-compose up --build -d`

4. **OpenAI API hatası:**
   - `.env` dosyasındaki API key'i kontrol edin
   - API key'in geçerli olduğundan emin olun

### Geliştirme

```bash
# Geliştirme modunda çalıştır (hot reload)
docker-compose -f docker-compose.dev.yml up

# Sadece veritabanını çalıştır
docker-compose up postgres -d
```
