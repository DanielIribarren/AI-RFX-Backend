#!/bin/bash

echo "🔍 VERIFICACIÓN DE BACKEND - https://recharge-api.akeela.co"
echo "============================================================"
echo ""

# Test 1: Verificar que el dominio resuelve
echo "1️⃣ Verificando DNS..."
nslookup recharge-api.akeela.co
echo ""

# Test 2: Verificar conectividad HTTP
echo "2️⃣ Verificando conectividad HTTP..."
curl -I https://recharge-api.akeela.co 2>&1 | head -10
echo ""

# Test 3: Verificar endpoint de health/status
echo "3️⃣ Verificando endpoint de API..."
curl -s https://recharge-api.akeela.co/api/health 2>&1 || echo "❌ No hay endpoint /api/health"
echo ""

# Test 4: Verificar CORS headers
echo "4️⃣ Verificando CORS headers..."
curl -I -X OPTIONS https://recharge-api.akeela.co/api/rfx/history \
  -H "Origin: https://rfx-app.anvroc.com" \
  -H "Access-Control-Request-Method: GET" 2>&1 | grep -i "access-control"
echo ""

echo "============================================================"
echo "✅ Si ves respuestas HTTP 200 y headers CORS, está funcionando"
echo "❌ Si ves errores de conexión, el backend no está corriendo"
