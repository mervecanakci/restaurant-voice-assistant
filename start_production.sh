#!/bin/bash

echo "🚀 Restaurant App Production Başlatılıyor..."
echo "================================================"

# Backend'i başlat
echo "📡 Backend başlatılıyor (port 8000)..."
cd /home/merve/restaurant_app
source .venv/bin/activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

# 3 saniye bekle
sleep 3

# Frontend'i başlat
echo "🌐 Frontend başlatılıyor (port 9000)..."
cd /home/merve/restaurant_app
python3 -m http.server 9000 &
FRONTEND_PID=$!

echo ""
echo "✅ Uygulama başarıyla başlatıldı!"
echo "================================================"
echo "🏠 Ana Sayfa: http://127.0.0.1:9000/"
echo "🔐 Giriş Sayfası: http://127.0.0.1:9000/login.html"
echo "📚 API Dokümantasyonu: http://127.0.0.1:8000/docs"
echo "🔧 Admin Paneli: http://127.0.0.1:9000/admin.html"
echo "👤 Müşteri Paneli: http://127.0.0.1:9000/customer.html"
echo "🤖 Sesli Asistan: http://127.0.0.1:9000/voice_assistant.html?restaurant_id=7"
echo ""
echo "🔑 Test Kullanıcıları:"
echo "   Admin: admin / admin123"
echo "   Müşteri: mervekullanici1 / password123"
echo "   Restoran: guzelresto / password123"
echo ""
echo "📝 Kullanım:"
echo "   1. http://127.0.0.1:9000/ adresine gidin (Ana Sayfa)"
echo "   2. 'Giriş Yap / Kayıt Ol' butonuna tıklayın"
echo "   3. Admin olarak giriş yapın (admin/admin123)"
echo "   4. Restoran ekleyin ve menü oluşturun"
echo "   5. Müşteri olarak giriş yapın (mervekullanici1/password123)"
echo "   6. Sesli asistan ile sipariş verin!"
echo "   7. 'Menüyü göster' → 'X ekle' → 'Siparişimi oluştur'"
echo ""
echo "🎯 Özellikler:"
echo "   ✅ Rol tabanlı kullanıcı yönetimi"
echo "   ✅ Restoran ve menü yönetimi"
echo "   ✅ Gerçek zamanlı sipariş sistemi"
echo "   ✅ Cüzdan ve ödeme sistemi"
echo "   ✅ AI destekli sesli asistan"
echo "   ✅ Kombo menü oluşturma"
echo ""
echo "🛑 Durdurmak için Ctrl+C tuşlayın"
echo "================================================"

# Ctrl+C ile kapatma
trap "echo ''; echo '🛑 Uygulama kapatılıyor...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo '✅ Uygulama kapatıldı'; exit 0" SIGINT SIGTERM

# Process'leri bekle
wait $BACKEND_PID
wait $FRONTEND_PID
