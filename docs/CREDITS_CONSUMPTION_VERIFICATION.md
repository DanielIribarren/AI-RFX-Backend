# 💳 Verificación de Consumo de Créditos

**Fecha:** 17 de Diciembre, 2025  
**Versión:** 1.0

---

## 🎯 Resumen del Sistema de Créditos

### **Usuarios Personales (sin organización):**
- ✅ Tabla: `user_credits`
- ✅ Créditos: 100/mes (plan free)
- ✅ Consumo real rastreado en `credits_used`
- ✅ Reset mensual automático

### **Usuarios Organizacionales:**
- ✅ Tabla: `organizations`
- ✅ Créditos: Según plan (100-5000/mes)
- ✅ Consumo compartido entre todos los miembros
- ✅ Reset mensual según plan

---

## 📊 Endpoints de Créditos

### **1. GET /api/credits/info**
**Descripción:** Obtener información de créditos del usuario actual

**Requiere:** JWT token

**Respuesta:**
```json
{
  "status": "success",
  "data": {
    "credits_total": 100,
    "credits_used": 15,
    "credits_available": 85,
    "credits_percentage": 85.0,
    "reset_date": "2025-01-17T00:00:00Z",
    "plan_tier": "free",
    "plan_type": "personal"
  }
}
```

**Lógica:**
```python
# backend/api/credits.py:21-59
@credits_bp.route("/info", methods=["GET"])
@jwt_required
def get_credits_info():
    user_id = get_current_user_id()
    credits_service = get_credits_service()
    credits_info = credits_service.get_credits_info_for_user(user_id)
    # Retorna créditos de user_credits o organizations según contexto
```

**Flujo:**
1. Usuario hace request con JWT
2. Extrae `user_id` del token
3. Consulta `users.organization_id`
4. Si `organization_id` existe → consulta `organizations`
5. Si `organization_id` es NULL → consulta `user_credits`

---

## 🔄 Consumo de Créditos en Operaciones

### **1. Procesar RFX (Extracción de Datos)**

**Endpoint:** `POST /api/rfx/process`  
**Costo:** 5 créditos  
**Archivo:** `backend/api/rfx.py:186-240`

**Flujo:**
```python
# 1. VERIFICAR CRÉDITOS
has_credits, available, msg = credits_service.check_credits_available(
    organization_id,  # None para usuarios personales
    'extraction',     # 5 créditos
    user_id=current_user_id
)

if not has_credits:
    return 402  # Payment Required

# 2. PROCESAR RFX
rfx_processed = processor_service.process_rfx_case(...)

# 3. CONSUMIR CRÉDITOS
consume_result = credits_service.consume_credits(
    organization_id=organization_id,  # None para personales
    operation='extraction',
    rfx_id=actual_rfx_id,
    user_id=current_user_id
)
```

**Verificación:**
- ✅ Verifica créditos ANTES de procesar
- ✅ Retorna 402 si no hay créditos
- ✅ Consume créditos DESPUÉS de procesar exitosamente
- ✅ Funciona para usuarios personales y organizacionales

---

### **2. Chat con RFX**

**Endpoint:** `POST /api/rfx/<rfx_id>/chat`  
**Costo:** 1 crédito por mensaje  
**Archivo:** `backend/api/rfx_chat.py:134-221`

**Flujo:**
```python
# 1. VERIFICAR CRÉDITOS
has_credits, available, msg = credits_service.check_credits_available(
    organization_id,  # None para usuarios personales
    'chat_message',   # 1 crédito
    user_id=user_id
)

if not has_credits:
    return 402  # Payment Required

# 2. PROCESAR MENSAJE CON IA
response = chat_agent.process_message(...)

# 3. GUARDAR EN HISTORIAL
chat_service.save_chat_message(...)

# 4. CONSUMIR CRÉDITO
consume_result = credits_service.consume_credits(
    organization_id=organization_id,  # None para personales
    operation='chat_message',
    rfx_id=rfx_id,
    user_id=user_id
)
```

**Verificación:**
- ✅ Verifica créditos ANTES de procesar mensaje
- ✅ Retorna 402 si no hay créditos
- ✅ Consume 1 crédito DESPUÉS de procesar
- ✅ Funciona para usuarios personales y organizacionales

---

### **3. Generar Propuesta**

**Endpoint:** `POST /api/proposals/generate`  
**Costo:** 5 créditos (primera vez) o 0 créditos (regeneración gratis)  
**Archivo:** `backend/api/proposals.py:213-281`

**Flujo:**
```python
# 1. VERIFICAR SI TIENE REGENERACIÓN GRATIS
if is_regeneration:
    has_free, used, msg = credits_service.check_free_regeneration_available(
        organization_id, rfx_id
    )
    
    if has_free:
        credits_to_consume = 0  # Regeneración gratis
    else:
        credits_to_consume = 5  # Consumir créditos
else:
    credits_to_consume = 5  # Primera generación

# 2. VERIFICAR CRÉDITOS SI ES NECESARIO
if credits_to_consume > 0:
    has_credits, available, msg = credits_service.check_credits_available(
        organization_id,  # None para usuarios personales
        'generation',
        user_id=user_id
    )
    
    if not has_credits:
        return 402  # Payment Required

# 3. GENERAR PROPUESTA
propuesta_generada = proposal_generator.generate_proposal(...)

# 4. CONSUMIR CRÉDITOS O MARCAR REGENERACIÓN GRATIS
if has_free_regeneration:
    credits_service.use_free_regeneration(rfx_id)
elif credits_to_consume > 0:
    consume_result = credits_service.consume_credits(
        organization_id=organization_id,
        operation='generation',
        rfx_id=rfx_id,
        user_id=user_id
    )
```

**Verificación:**
- ✅ Verifica regeneraciones gratuitas primero
- ✅ Verifica créditos ANTES de generar
- ✅ Retorna 402 si no hay créditos
- ✅ Consume créditos DESPUÉS de generar exitosamente
- ✅ Funciona para usuarios personales y organizacionales

---

## 🧪 Pruebas de Consumo

### **Test 1: Usuario Personal - Procesar RFX**

**Setup:**
```sql
-- Usuario sin organización
SELECT id, email, organization_id FROM users WHERE id = 'user-123';
-- organization_id: NULL

-- Créditos iniciales
SELECT credits_total, credits_used FROM user_credits WHERE user_id = 'user-123';
-- credits_total: 100, credits_used: 0
```

**Request:**
```bash
POST /api/rfx/process
Authorization: Bearer <jwt-token>
Content-Type: multipart/form-data

{
  "files": [<pdf-file>]
}
```

**Resultado Esperado:**
```sql
-- Después del request
SELECT credits_used FROM user_credits WHERE user_id = 'user-123';
-- credits_used: 5 (0 + 5)
```

---

### **Test 2: Usuario Organizacional - Chat**

**Setup:**
```sql
-- Usuario con organización
SELECT id, email, organization_id FROM users WHERE id = 'user-456';
-- organization_id: 'org-789'

-- Créditos de organización
SELECT credits_total, credits_used FROM organizations WHERE id = 'org-789';
-- credits_total: 1500, credits_used: 50
```

**Request:**
```bash
POST /api/rfx/<rfx-id>/chat
Authorization: Bearer <jwt-token>
Content-Type: application/json

{
  "message": "Agrega 10 unidades de café"
}
```

**Resultado Esperado:**
```sql
-- Después del request
SELECT credits_used FROM organizations WHERE id = 'org-789';
-- credits_used: 51 (50 + 1)
```

---

### **Test 3: Usuario Personal - Generar Propuesta (Primera Vez)**

**Setup:**
```sql
-- Créditos iniciales
SELECT credits_used FROM user_credits WHERE user_id = 'user-123';
-- credits_used: 5 (del test anterior)
```

**Request:**
```bash
POST /api/proposals/generate
Authorization: Bearer <jwt-token>
Content-Type: application/json

{
  "rfx_id": "rfx-abc",
  "company_id": "company-123"
}
```

**Resultado Esperado:**
```sql
-- Después del request
SELECT credits_used FROM user_credits WHERE user_id = 'user-123';
-- credits_used: 10 (5 + 5)
```

---

### **Test 4: Usuario Personal - Sin Créditos**

**Setup:**
```sql
-- Consumir todos los créditos
UPDATE user_credits SET credits_used = 100 WHERE user_id = 'user-123';
```

**Request:**
```bash
POST /api/rfx/process
Authorization: Bearer <jwt-token>
```

**Resultado Esperado:**
```json
{
  "status": "error",
  "error_type": "insufficient_credits",
  "message": "Insufficient credits. Required: 5, Available: 0. Personal plan (free tier). Consider joining an organization.",
  "credits_required": 5,
  "credits_available": 0
}
```

**HTTP Status:** `402 Payment Required`

---

## 🔍 Debugging

### **Verificar Créditos de Usuario:**

```sql
-- Usuario personal
SELECT 
    u.email,
    uc.credits_total,
    uc.credits_used,
    uc.credits_total - uc.credits_used as available,
    uc.plan_tier
FROM users u
LEFT JOIN user_credits uc ON u.id = uc.user_id
WHERE u.id = '<user-id>';

-- Usuario organizacional
SELECT 
    u.email,
    o.name as organization,
    o.credits_total,
    o.credits_used,
    o.credits_total - o.credits_used as available,
    o.plan_tier
FROM users u
JOIN organizations o ON u.organization_id = o.id
WHERE u.id = '<user-id>';
```

### **Verificar Consumo en Logs:**

```bash
# Buscar logs de consumo
grep "Credits consumed" backend.log

# Ejemplos de logs esperados:
# ✅ Credits consumed (personal): 5 (remaining: 95)
# ✅ Credits consumed (organization): 1 (remaining: 1499)
```

### **Verificar Endpoint de Créditos:**

```bash
# Test endpoint
curl -X GET http://localhost:5000/api/credits/info \
  -H "Authorization: Bearer <jwt-token>"

# Respuesta esperada:
{
  "status": "success",
  "data": {
    "credits_total": 100,
    "credits_used": 10,
    "credits_available": 90,
    ...
  }
}
```

---

## ⚠️ Problemas Comunes

### **1. Error 404 en /api/credits/info**

**Causas:**
- Blueprint no registrado en `app.py`
- Servidor no corriendo
- Ruta incorrecta

**Solución:**
```python
# Verificar en backend/app.py
from backend.api.credits import credits_bp
app.register_blueprint(credits_bp)  # ✅ Debe estar presente
```

### **2. Créditos no se consumen**

**Causas:**
- `organization_id` o `user_id` no se pasa correctamente
- Error en `consume_credits()` no se maneja

**Solución:**
```python
# Verificar logs
logger.info(f"✅ Credits consumed ({context}): {amount} (remaining: {remaining})")

# Si no aparece este log, el consumo falló
```

### **3. Usuario personal no tiene créditos iniciales**

**Causas:**
- Usuario creado antes de la migración
- Función `initialize_user_credits()` no ejecutada

**Solución:**
```sql
-- Inicializar manualmente
SELECT initialize_user_credits('<user-id>');

-- Verificar
SELECT * FROM user_credits WHERE user_id = '<user-id>';
```

---

## ✅ Checklist de Verificación

- [ ] Endpoint `/api/credits/info` retorna 200
- [ ] Procesar RFX consume 5 créditos
- [ ] Chat consume 1 crédito por mensaje
- [ ] Generar propuesta consume 5 créditos (primera vez)
- [ ] Regeneración gratis funciona (no consume créditos)
- [ ] Usuario sin créditos recibe 402 Payment Required
- [ ] Logs muestran consumo correcto
- [ ] Créditos de usuarios personales se rastrean en `user_credits`
- [ ] Créditos de usuarios organizacionales se rastrean en `organizations`

---

## 📝 Notas Finales

**Estado:** ✅ Sistema implementado y funcional

**Archivos Clave:**
- `backend/services/credits_service.py` - Lógica de créditos
- `backend/api/credits.py` - Endpoints de consulta
- `backend/api/rfx.py` - Consumo en procesamiento
- `backend/api/rfx_chat.py` - Consumo en chat
- `backend/api/proposals.py` - Consumo en generación

**Base de Datos:**
- `user_credits` - Créditos de usuarios personales
- `organizations` - Créditos de organizaciones
- `credit_transactions` - Historial (solo organizaciones)
