#!/bin/bash

# Docker ile projeyi başlatma scripti

echo "🐳 Restaurant App Docker Başlatılıyor..."

# .env dosyasını kontrol et
if [ ! -f .env ]; then
    echo "❌ .env dosyası bulunamadı!"
    echo "📝 .env dosyası oluşturuluyor..."
    cat > .env << EOF
# OpenAI API Key
OPENAI_API_KEY=sk-proj-uhqbjqF4p76kwK2HRB3OkO50R0ne_E7hHesikHpgiY7ImA5Y950O0ggqNsfvpkoCgJkP-YYTNT3BlbkFJUwAF9GTwflh61u-vJVnobWPD9O29lIdaLnEn_8yVTU3bXAsp0ipQQLTJwBfaaR4aymDYzXZlMA

# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/restaurant_db
EOF
    echo "✅ .env dosyası oluşturuldu!"
fi

# Docker Compose ile servisleri başlat
echo "🚀 Docker Compose ile servisler başlatılıyor..."
docker-compose up --build -d

# Servislerin hazır olmasını bekle
echo "⏳ Servislerin hazır olması bekleniyor..."
sleep 10

# Servis durumunu kontrol et
echo "📊 Servis durumu:"
docker-compose ps

echo ""
echo "🎉 Restaurant App başarıyla başlatıldı!"
echo ""
echo "🌐 Erişim Adresleri:"
echo "   📱 Ana Uygulama: http://localhost:8000"
echo "   🤖 Sesli Asistan: http://localhost:9000/voice_assistant.html?restaurant_id=7"
echo "   👨‍💼 Admin Panel: http://localhost:9000/admin.html"
echo ""
echo "🔑 Test Kullanıcıları:"
echo "   👤 Admin: admin / admin123"
echo "   👤 Müşteri: mervekullanici1 / mervekullanici1"
echo "   👤 Restoran: guzelresto / guzelresto"
echo ""
echo "📋 Kullanım:"
echo "   1. Sesli asistan ile sipariş verin!"
echo "   2. Admin panelinden sistemi yönetin"
echo "   3. Müşteri olarak siparişlerinizi takip edin"
echo ""
echo "🛑 Durdurmak için: docker-compose down"
