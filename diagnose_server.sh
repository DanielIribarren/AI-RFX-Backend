#!/bin/bash

echo "🔍 DIAGNÓSTICO COMPLETO DEL SERVIDOR"
echo "===================================="
echo ""

echo "1️⃣ Verificando procesos PM2..."
pm2 list
echo ""

echo "2️⃣ Verificando puerto 5001..."
lsof -i :5001 || echo "❌ Puerto 5001 no está en uso"
echo ""

echo "3️⃣ Verificando archivo pm2.config.js..."
if [ -f "/home/ubuntu/nodejs/AI-RFX-Backend-Clean/pm2.config.js" ]; then
    echo "✅ Archivo existe"
    head -20 /home/ubuntu/nodejs/AI-RFX-Backend-Clean/pm2.config.js
else
    echo "❌ Archivo NO existe"
fi
echo ""

echo "4️⃣ Últimos logs del backend..."
pm2 logs --lines 50 --nostream
echo ""

echo "5️⃣ Verificando nginx..."
sudo systemctl status nginx | head -10
echo ""

echo "6️⃣ Test de conectividad a Supabase..."
curl -I https://mjwnmzdgxcxubanubvms.supabase.co 2>&1 | head -5
echo ""

echo "7️⃣ Test endpoint de login..."
curl -X POST http://localhost:5001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"test"}' \
  2>&1 | head -20
echo ""

echo "===================================="
echo "✅ Diagnóstico completado"
