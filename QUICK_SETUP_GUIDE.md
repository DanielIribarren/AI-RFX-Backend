# 🔧 Guía Rápida de Configuración V3.0

## ✅ **Estado**: Listo para Testing

### **1. 🔐 Configurar JWT en .env**

Abre tu archivo `backend/.env` y agrega:

```env
# ========================
# JWT AUTHENTICATION V3.0  
# ========================
JWT_SECRET_KEY=Cwy7YxamMIprktPtSx_zA_9ehho-XzXbmrUcnasoTU3QFlw8WXzsuB-r-JEUbXedC1_O9RYCGBV3tQWgYOqd5w
JWT_EXPIRE_MINUTES=120  # 2 horas
JWT_ALGORITHM=HS256

# ========================
# SECURITY SETTINGS
# ========================
FLASK_ENV=development
FLASK_DEBUG=True
```

### **2. 📦 Instalar Dependencias**

```bash
cd backend
pip install -r requirements.txt
```

### **3. 🗄️ Ejecutar Migración de Base de Datos**

```bash
psql -U your_user -d your_database -f Database/Migration-V3.0-MVP-Users-Auth.sql
```

### **4. 🚀 Iniciar Servidor**

```bash
cd backend
python app.py
```

**Deberías ver:**
```
🚀 Application created successfully in development mode
🔐 V3.0 Authentication endpoints available:
   POST /api/auth/login
   POST /api/auth/signup
   GET  /api/auth/me
🔒 V3.0 Secure endpoints available:
   GET  /api/rfx-secure/my-rfx
   POST /api/rfx-secure/create
   POST /api/user-branding/upload
```

---

## 🧪 **Testing Rápido**

### **1. Test de Registro:**
```bash
curl -X POST http://localhost:5000/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@ejemplo.com",
    "password": "MiPassword123",
    "full_name": "Usuario Test",
    "company_name": "Mi Empresa"
  }'
```

**Respuesta esperada:**
```json
{
  "status": "success",
  "access_token": "eyJ0eXAiOiJKV1Q...",
  "user": {
    "id": "uuid-usuario",
    "email": "test@ejemplo.com",
    "status": "pending_verification"
  }
}
```

### **2. Test de Login:**
```bash
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@ejemplo.com", 
    "password": "MiPassword123"
  }'
```

### **3. Test de Endpoint Seguro:**
```bash
# Usar el token del login anterior
export TOKEN="eyJ0eXAiOiJKV1Q..."

curl -X GET http://localhost:5000/api/auth/me \
  -H "Authorization: Bearer $TOKEN"
```

### **4. Test de Creación RFX Seguro:**
```bash
curl -X POST http://localhost:5000/api/rfx-secure/create \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Mi Primer RFX Seguro",
    "description": "RFX creado con autenticación"
  }'
```

---

## 📋 **Checklist de Verificación**

- [ ] ✅ JWT_SECRET_KEY configurado en .env
- [ ] ✅ Migración de BD ejecutada
- [ ] ✅ Servidor iniciado sin errores
- [ ] ✅ Test de signup funciona
- [ ] ✅ Test de login funciona
- [ ] ✅ Test de endpoint protegido funciona
- [ ] ✅ RFX se crean con user_id automático

---

## 🔧 **Endpoints Disponibles**

### **🔐 Autenticación (NO requieren token)**
```
POST /api/auth/signup           # Registro
POST /api/auth/login            # Login
POST /api/auth/verify-email     # Verificar email
POST /api/auth/forgot-password  # Reset contraseña
POST /api/auth/reset-password   # Confirmar reset
GET  /api/auth/health           # Health check
```

### **🔒 Endpoints Seguros (Requieren JWT)**
```
GET  /api/auth/me                      # Mi perfil
POST /api/auth/refresh                 # Renovar token
POST /api/auth/resend-verification     # Reenviar verificación

GET  /api/rfx-secure/<rfx_id>          # Ver MI RFX
GET  /api/rfx-secure/my-rfx            # Listar MIS RFX  
POST /api/rfx-secure/create            # Crear RFX
PUT  /api/rfx-secure/<rfx_id>          # Actualizar MI RFX
DELETE /api/rfx-secure/<rfx_id>        # Eliminar MI RFX

POST /api/user-branding/upload         # Subir MI branding
GET  /api/user-branding/               # Ver MI branding
GET  /api/user-branding/status         # Estado análisis
POST /api/user-branding/reanalyze      # Re-analizar
DELETE /api/user-branding/             # Eliminar MI branding
```

---

## ⚠️ **IMPORTANTE - Seguridad**

### **❌ NO USAR (Inseguros):**
```
/api/rfx/<rfx_id>              # Sin filtro user_id
/api/branding/*                # Sin autenticación
```

### **✅ USAR (Seguros):**
```
/api/rfx-secure/<rfx_id>       # Con filtro user_id
/api/user-branding/*           # Con autenticación
```

---

## 🚨 **Troubleshooting**

### **Error: "Module not found"**
```bash
pip install python-jose[cryptography] passlib[bcrypt]
```

### **Error: "Invalid JWT token"**
- Verifica que JWT_SECRET_KEY esté en .env
- Verifica que el token no haya expirado
- Usa formato: `Authorization: Bearer <token>`

### **Error: "RFX not found or access denied"**
- El RFX pertenece a otro usuario
- Usar endpoints `/api/rfx-secure/*`
- Verificar que el JWT sea válido

### **Error: "Database connection failed"**
- Ejecutar migración: `Migration-V3.0-MVP-Users-Auth.sql`
- Verificar DATABASE_URL en .env

---

## 🎯 **Próximos Pasos**

1. **Testing completo** con diferentes usuarios
2. **Migrar datos existentes** con endpoint temporal
3. **Actualizar frontend** para usar endpoints seguros
4. **Configurar email service** para verificaciones
5. **Deploy a producción** con JWT seguro

---

**🔒 Tu sistema ahora es SEGURO - Cada usuario solo puede ver sus propios datos**
