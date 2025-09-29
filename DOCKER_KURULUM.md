# 🐳 Restaurant Voice Assistant - Docker Kurulum Rehberi

Modern AI destekli sesli restoran sipariş sistemi için Docker kurulum rehberi.

## 🚀 Hızlı Başlangıç

### 1. Docker Kurulumu (Ubuntu/Debian)
```bash
# Sistem paketlerini güncelle
sudo apt update

# Docker'ı kur
sudo apt install docker.io docker-compose

# Docker servisini başlat ve otomatik başlatmayı etkinleştir
sudo systemctl start docker
sudo systemctl enable docker

# Kullanıcıyı docker grubuna ekle
sudo usermod -aG docker $USER

# Oturumu yenile
newgrp docker
```

### 2. Projeyi Başlatma
```bash
# Projeyi klonla
git clone <repository-url>
cd restaurant-voice-assistant

# Otomatik başlatma (önerilen)
chmod +x docker-start.sh
./docker-start.sh

# Veya manuel başlatma
docker-compose up --build -d
```

### 3. Erişim Adresleri
- **Frontend:** http://localhost:9000
- **API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs
- **PostgreSQL:** localhost:5433

## 🔑 Giriş Bilgileri

### Admin
- **Kullanıcı:** `admin`
- **Şifre:** `123`

### Restoranlar
| Kullanıcı | Şifre | Restoran |
|-----------|-------|----------|
| pideci23 | 123 | pideci23 |
| guzelresto | 123 | Güzel Resto |
| pizzapalace | 123 | Pizza Palace |
| burgerking | 123 | burger king |

### Müşteriler
| Kullanıcı | Şifre | E-posta |
|-----------|-------|---------|
| system | 123 | mervecanakci95@gmail.com |
| merve | 123 | merve@test.com |
| customer1 | 123 | customer1@test.com |

## 🎯 Kullanım

### Sesli Asistan
1. Giriş yapın: http://localhost:9000/login.html
2. Restoran seçin
3. Sesli asistan: http://localhost:9000/voice_assistant.html?restaurant_id=7

### Sesli Komutlar
- "Menüyü göster"
- "Pizza küçük boy sepete ekle"
- "Siparişi oluştur"
- "Sipariş durumu ne?"

## 🛠️ Geliştirme

### Environment Dosyası
```bash
# .env dosyasını düzenle
nano .env

# Gerekli değişkenler:
OPENAI_API_KEY=your_openai_api_key
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/restaurant_db
SECRET_KEY=your_secret_key
ENVIRONMENT=development
```

### Kontrol Komutları
```bash
# Servis durumu
docker-compose ps

# Logları görüntüle
docker-compose logs -f

# Servisleri durdur
docker-compose down

# Veritabanını sıfırla
docker-compose down -v
docker-compose up --build -d
```

## 🔧 Sorun Giderme

### Port Çakışması
```bash
# Port kullanımını kontrol et
sudo ss -tlnp | grep :8000
sudo ss -tlnp | grep :5433
sudo ss -tlnp | grep :9000

# Çakışan servisleri durdur
sudo systemctl stop postgresql
sudo pkill -f uvicorn
```

### Docker İzin Hatası
```bash
# Docker grubuna eklenmeyi kontrol et
groups $USER

# Docker grubuna ekle
sudo usermod -aG docker $USER
newgrp docker
```

### Container Başlamıyor
```bash
# Detaylı logları görüntüle
docker-compose logs app
docker-compose logs postgres

# Container'ı yeniden oluştur
docker-compose up --build --force-recreate
```

## 📊 Sistem Mimarisi

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   FastAPI        │    │   PostgreSQL    │
│   (Port 9000)   │◄──►│   (Port 8000)    │◄──►│   (Port 5433)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │
         │                       │
         ▼                       ▼
┌─────────────────┐    ┌─────────────────┐
│ OpenAI Realtime │    │   WebSocket     │
│      API        │    │   Connection    │
└─────────────────┘    └─────────────────┘
```

## 🚀 Production Deployment

### Environment Variables
```bash
OPENAI_API_KEY=your_production_openai_key
DATABASE_URL=postgresql://user:pass@host:port/db
SECRET_KEY=your_production_secret_key
ENVIRONMENT=production
```

### SSL ve Domain
```bash
# Nginx reverse proxy ile SSL
# Domain yapılandırması
# Load balancer ayarları
```

## 📝 Notlar

- Tüm kullanıcılar için şifre: `123`
- Sistem SHA256 hash kullanır
- OpenAI Realtime API gereklidir
- PostgreSQL veritabanı otomatik başlatılır
- WebSocket bağlantıları gerçek zamanlıdır

## 🤝 Destek

- **Issues:** GitHub Issues
- **Documentation:** README.md
- **API Docs:** http://localhost:8000/docs
