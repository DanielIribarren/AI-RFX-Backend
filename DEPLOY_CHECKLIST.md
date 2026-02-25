# ✅ Checklist de Deploy - Frontend y Backend

## Configuración Actual

**Frontend (Vercel):**
- URL: `https://rfx-app.anvroc.com`
- Apunta a: `https://recharge-api.akeela.co`

**Backend (Ubuntu Server):**
- Dominio: `https://recharge-api.akeela.co`
- Puerto: `5001`
- IP Servidor: `159.203.105.202`

---

## Pasos para Deploy Garantizado

### 1. En el Servidor Ubuntu

```bash
# Ir al directorio
cd /home/ubuntu/nodejs/AI-RFX-Backend-Clean

# Subir el archivo pm2.config.js actualizado
# (usa scp, git pull, o copia manual)

# Detener procesos viejos
pm2 delete RFX-dev 2>/dev/null || true
pm2 delete rfx-backend 2>/dev/null || true
pm2 delete all 2>/dev/null || true

# Verificar puerto libre
lsof -i :5001 || echo "✅ Puerto 5001 disponible"

# Crear carpeta de logs
mkdir -p logs

# Iniciar backend con nueva configuración
pm2 start pm2.config.js

# Ver logs inmediatamente
pm2 logs rfx-backend --lines 50 --nostream

# Si todo está OK, guardar
pm2 save
```

### 2. Verificar que el Backend Responde

```bash
# Test local en el servidor
curl http://localhost:5001/api/health

# Test con dominio (requiere nginx configurado)
curl https://recharge-api.akeela.co/api/health
```

### 3. Verificar Nginx (CRÍTICO)

El dominio `recharge-api.akeela.co` necesita nginx como proxy inverso:

```bash
# Ver configuración de nginx
cat /etc/nginx/sites-enabled/recharge-api.akeela.co

# Si NO existe, crear configuración:
sudo nano /etc/nginx/sites-available/recharge-api.akeela.co
```

**Configuración mínima de nginx:**

```nginx
server {
    listen 80;
    server_name recharge-api.akeela.co;

    location / {
        proxy_pass http://localhost:5001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
}
```

**Activar y recargar nginx:**

```bash
sudo ln -s /etc/nginx/sites-available/recharge-api.akeela.co /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 4. Verificar CORS desde tu Máquina Local

```bash
# Ejecutar script de verificación
chmod +x test_backend_connection.sh
./test_backend_connection.sh
```

**Deberías ver:**
- ✅ DNS resuelve a `159.203.105.202`
- ✅ HTTP 200 OK
- ✅ Headers CORS: `Access-Control-Allow-Origin: https://rfx-app.anvroc.com`

### 5. Verificar en Vercel (SIN DEPLOY)

Vercel ya tiene configurado:
```json
{
  "env": {
    "NEXT_PUBLIC_API_URL": "https://recharge-api.akeela.co"
  }
}
```

**NO necesitas hacer deploy en Vercel** si el backend ya está funcionando correctamente.

---

## Troubleshooting

### ❌ Error: "Failed to fetch"

**Causa:** CORS no configurado correctamente

**Solución:**
1. Verificar que `pm2.config.js` tenga: `CORS_ORIGINS: 'https://rfx-app.anvroc.com,...'`
2. Reiniciar backend: `pm2 restart rfx-backend`
3. Ver logs: `pm2 logs rfx-backend | grep CORS`

### ❌ Error: "Connection refused"

**Causa:** Backend no está corriendo o nginx no configurado

**Solución:**
1. Verificar backend: `pm2 list`
2. Verificar nginx: `sudo systemctl status nginx`
3. Ver logs: `pm2 logs rfx-backend --err`

### ❌ Error: "SSL certificate problem"

**Causa:** No hay certificado SSL para `recharge-api.akeela.co`

**Solución:**
```bash
sudo certbot --nginx -d recharge-api.akeela.co
```

---

## Verificación Final

### Checklist antes de usar en producción:

- [ ] Backend corriendo: `pm2 list` muestra `rfx-backend` online
- [ ] Puerto 5001 escuchando: `lsof -i :5001`
- [ ] Nginx configurado y corriendo: `sudo nginx -t`
- [ ] DNS correcto: `nslookup recharge-api.akeela.co` → `159.203.105.202`
- [ ] CORS funciona: `./test_backend_connection.sh` muestra headers correctos
- [ ] SSL activo: `curl https://recharge-api.akeela.co` no da error
- [ ] Endpoint responde: `curl https://recharge-api.akeela.co/api/health`

### Test desde el navegador:

1. Abrir: `https://rfx-app.anvroc.com`
2. Abrir DevTools → Network
3. Intentar cualquier acción que llame al backend
4. Verificar que las peticiones a `recharge-api.akeela.co` respondan 200 OK

---

## Archivos Modificados

- ✅ `pm2.config.js` - CORS actualizado con `https://rfx-app.anvroc.com`
- ✅ `test_backend_connection.sh` - Script de verificación
- ✅ Puerto cambiado a `5001` (coincide con frontend)

## Próximos Pasos

1. Subir `pm2.config.js` al servidor
2. Ejecutar comandos de deploy en el servidor
3. Verificar nginx
4. Ejecutar `test_backend_connection.sh` localmente
5. Probar desde `https://rfx-app.anvroc.com`

**NO HACER DEPLOY EN VERCEL** hasta que el backend responda correctamente.
