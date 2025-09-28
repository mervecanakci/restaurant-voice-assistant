# 🐳 Docker Kurulum Rehberi

## Docker Kurulumu (Ubuntu/Debian)

### 1. Docker Engine Kurulumu
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
```

### 2. Kurulumu Test Et
```bash
# Docker versiyonunu kontrol et
docker --version
docker-compose --version

# Test container çalıştır
docker run hello-world
```

### 3. Oturumu Yenile
```bash
# Docker grubuna eklenmek için oturumu kapat ve tekrar aç
# Veya şu komutu çalıştır:
newgrp docker
```

## Projeyi Çalıştırma

### 1. Projeyi Klonla
```bash
git clone <repository-url>
cd restaurant_app
```

### 2. Environment Dosyasını Hazırla
```bash
# Örnek dosyayı kopyala
cp env.example .env

# .env dosyasını düzenle
nano .env
```

### 3. Docker ile Başlat
```bash
# Otomatik başlatma
./docker-start.sh

# Veya manuel başlatma
docker-compose up --build -d
```

## Kontrol Komutları

### Servis Durumu
```bash
# Çalışan container'ları görüntüle
docker-compose ps

# Logları görüntüle
docker-compose logs -f

# Servisleri durdur
docker-compose down
```

### Veritabanı Sıfırlama
```bash
# Tüm verileri sil ve yeniden başlat
docker-compose down -v
docker-compose up --build -d
```

## Sorun Giderme

### Port Çakışması
```bash
# Port kullanımını kontrol et
sudo ss -tlnp | grep :8000
sudo ss -tlnp | grep :5432
sudo ss -tlnp | grep :9000

# Çakışan servisleri durdur
sudo systemctl stop postgresql
sudo pkill -f uvicorn
sudo pkill -f "python.*http.server"
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

## Erişim Adresleri

- **FastAPI Backend:** http://localhost:8000
- **API Dokümantasyonu:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/health
- **Frontend:** http://localhost:9000
- **Sesli Asistan:** http://localhost:9000/voice_assistant.html?restaurant_id=7
- **Admin Panel:** http://localhost:9000/admin.html
- **PostgreSQL:** localhost:5433

## Test Kullanıcıları

- **Admin:** admin / admin123
- **Müşteri:** mervekullanici1 / mervekullanici1
- **Restoran:** guzelresto / guzelresto
