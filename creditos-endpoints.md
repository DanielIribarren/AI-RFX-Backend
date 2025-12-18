# 💳 API de Créditos - Documentación de Endpoints

**Versión:** 1.0  
**Fecha:** 9 de Diciembre, 2025  
**Base URL:** `http://localhost:5001/api`

---

## 📋 Tabla de Contenidos

1. [Introducción](#introducción)
2. [Autenticación](#autenticación)
3. [Modelo de Créditos](#modelo-de-créditos)
4. [Endpoints de Consulta](#endpoints-de-consulta)
5. [Endpoints de Operaciones](#endpoints-de-operaciones)
6. [Códigos de Respuesta](#códigos-de-respuesta)
7. [Ejemplos de Uso](#ejemplos-de-uso)

---

## 🎯 Introducción

El sistema de créditos permite controlar el uso de operaciones costosas en la plataforma RFX. Cada operación consume una cantidad específica de créditos según su complejidad.

### Operaciones que Consumen Créditos

| Operación | Créditos | Endpoint | Descripción |
|-----------|----------|----------|-------------|
| **Extracción de Datos** | 5 | `POST /api/rfx/process` | Extraer datos de documentos PDF/DOCX |
| **Generación de Propuesta** | 5 | `POST /api/rfx/<id>/generate-proposal` | Generar propuesta comercial |
| **Mensaje de Chat** | 1 | `POST /api/rfx/<id>/chat` | Actualizar RFX via chat |
| **Regeneración** | 5 o 0 | `POST /api/rfx/<id>/generate-proposal` | Regenerar propuesta (puede ser gratis) |

---

## 🔐 Autenticación

La mayoría de endpoints requieren autenticación JWT.

### Header Requerido

```http
Authorization: Bearer <jwt_token>
```

### Obtener Token

```bash
POST /api/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123"
}
```

**Respuesta:**
```json
{
  "status": "success",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "organization_id": "org-uuid"
  }
}
```

---

## 💰 Modelo de Créditos

### Costos por Operación

```json
{
  "extraction": 5,        // Extraer datos de documento (POST /api/rfx/process)
  "generation": 5,        // Generar propuesta inicial (POST /api/rfx/<id>/generate-proposal)
  "chat_message": 1,      // Mensaje de chat para actualizar RFX (POST /api/rfx/<id>/chat)
  "regeneration": 5       // Regenerar propuesta (o gratis según plan)
}
```

**Nota:** El flujo completo (extracción + generación) consume **10 créditos en total** (5 + 5), pero se facturan en dos pasos separados.

### Regeneraciones Gratuitas por Plan

| Plan | Regeneraciones Gratis | Créditos/Mes |
|------|----------------------|--------------|
| **FREE** | 1 por RFX | 100 |
| **STARTER** | 3 por RFX | 250 |
| **PRO** | Ilimitadas | 1,500 |
| **ENTERPRISE** | Ilimitadas | Ilimitados |

---

## 📊 Endpoints de Consulta

### 1. Obtener Información de Créditos

Consulta los créditos disponibles de tu organización.

**Endpoint:**
```http
GET /api/credits/info
```

**Autenticación:** 🔒 Requerida (JWT)

**Respuesta Exitosa (200):**
```json
{
  "status": "success",
  "data": {
    "credits_total": 1500,
    "credits_used": 250,
    "credits_available": 1250,
    "credits_percentage": 83.33,
    "reset_date": "2026-01-09T00:00:00Z",
    "plan_tier": "pro"
  }
}
```

**Campos de Respuesta:**
- `credits_total`: Total de créditos del plan mensual
- `credits_used`: Créditos consumidos en el mes actual
- `credits_available`: Créditos disponibles restantes
- `credits_percentage`: Porcentaje de créditos disponibles
- `reset_date`: Fecha del próximo reset mensual
- `plan_tier`: Tier del plan actual (free, starter, pro, enterprise)

**Ejemplo de Uso:**
```bash
curl -X GET "http://localhost:5001/api/credits/info" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Casos de Uso:**
- Mostrar indicador de créditos en el dashboard
- Verificar si hay créditos antes de operaciones costosas
- Alertar al usuario cuando créditos están bajos

---

### 2. Obtener Historial de Transacciones

Consulta el historial completo de consumo de créditos.

**Endpoint:**
```http
GET /api/credits/history?limit=50&offset=0
```

**Autenticación:** 🔒 Requerida (JWT)

**Query Parameters:**
- `limit` (opcional): Número de transacciones a retornar (default: 50, max: 100)
- `offset` (opcional): Offset para paginación (default: 0)

**Respuesta Exitosa (200):**
```json
{
  "status": "success",
  "data": [
    {
      "id": "txn-uuid-1",
      "organization_id": "org-uuid",
      "user_id": "user-uuid",
      "amount": -10,
      "type": "complete",
      "description": "Complete RFX processing: extraction + generation",
      "rfx_id": "rfx-uuid",
      "metadata": {},
      "created_at": "2025-12-09T10:30:00Z"
    },
    {
      "id": "txn-uuid-2",
      "organization_id": "org-uuid",
      "user_id": "user-uuid",
      "amount": -5,
      "type": "generation",
      "description": "Generation of proposal for RFX rfx-uuid",
      "rfx_id": "rfx-uuid",
      "metadata": {},
      "created_at": "2025-12-09T09:15:00Z"
    },
    {
      "id": "txn-uuid-3",
      "organization_id": "org-uuid",
      "user_id": null,
      "amount": 1500,
      "type": "monthly_reset",
      "description": "Monthly credits reset for pro plan",
      "rfx_id": null,
      "metadata": {},
      "created_at": "2025-12-01T00:00:00Z"
    }
  ],
  "count": 3,
  "pagination": {
    "limit": 50,
    "offset": 0
  }
}
```

**Tipos de Transacciones:**
- `complete`: Proceso completo (-10 créditos)
- `extraction`: Extracción de datos (-5 créditos)
- `generation`: Generación de propuesta (-5 créditos)
- `regeneration`: Regeneración de propuesta (-5 créditos)
- `chat_message`: Mensaje de chat (-1 crédito)
- `monthly_reset`: Reset mensual (+créditos del plan)

**Ejemplo de Uso:**
```bash
curl -X GET "http://localhost:5001/api/credits/history?limit=10&offset=0" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Casos de Uso:**
- Mostrar historial de consumo en dashboard
- Auditoría de uso de créditos
- Análisis de patrones de consumo
- Facturación detallada

---

### 3. Obtener Información de Regeneraciones

Consulta las regeneraciones gratuitas disponibles para un RFX específico.

**Endpoint:**
```http
GET /api/credits/regenerations/<rfx_id>
```

**Autenticación:** 🔒 Requerida (JWT)

**Path Parameters:**
- `rfx_id`: UUID del RFX

**Respuesta Exitosa (200):**
```json
{
  "status": "success",
  "data": {
    "rfx_id": "rfx-uuid",
    "has_free_regeneration": true,
    "free_regenerations_used": 1,
    "free_regenerations_limit": 3,
    "regeneration_count": 2,
    "plan_tier": "starter",
    "message": "2 free regenerations remaining"
  }
}
```

**Campos de Respuesta:**
- `has_free_regeneration`: Si tiene regeneración gratis disponible
- `free_regenerations_used`: Regeneraciones gratuitas ya usadas
- `free_regenerations_limit`: Límite de regeneraciones gratuitas del plan
- `regeneration_count`: Total de regeneraciones realizadas (gratis + pagadas)
- `plan_tier`: Plan actual
- `message`: Mensaje descriptivo del estado

**Ejemplo de Uso:**
```bash
curl -X GET "http://localhost:5001/api/credits/regenerations/rfx-uuid-123" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Casos de Uso:**
- Mostrar si la regeneración será gratis o pagada
- Indicar cuántas regeneraciones gratuitas quedan
- Decidir si mostrar botón "Regenerar Gratis" o "Regenerar (5 créditos)"

---

### 4. Obtener Planes Disponibles

Consulta todos los planes de suscripción disponibles.

**Endpoint:**
```http
GET /api/credits/plans
```

**Autenticación:** 🔓 Pública (no requiere JWT)

**Respuesta Exitosa (200):**
```json
{
  "status": "success",
  "data": [
    {
      "tier": "free",
      "name": "Free Plan",
      "max_users": 2,
      "max_rfx_per_month": 10,
      "credits_per_month": 100,
      "price_monthly_usd": 0,
      "free_regenerations": 1,
      "features": [
        "Up to 2 users",
        "100 credits per month (~10 RFX)",
        "1 free regeneration per proposal",
        "Basic proposal generation",
        "Email support"
      ]
    },
    {
      "tier": "starter",
      "name": "Starter Plan",
      "max_users": 5,
      "max_rfx_per_month": 25,
      "credits_per_month": 250,
      "price_monthly_usd": 29,
      "free_regenerations": 3,
      "features": [
        "Up to 5 users",
        "250 credits per month (~25 RFX)",
        "3 free regenerations per proposal",
        "Advanced proposal generation",
        "Basic branding",
        "Priority email support"
      ]
    },
    {
      "tier": "pro",
      "name": "Professional Plan",
      "max_users": 50,
      "max_rfx_per_month": 500,
      "credits_per_month": 1500,
      "price_monthly_usd": 99,
      "free_regenerations": "unlimited",
      "features": [
        "Up to 50 users",
        "1,500 credits per month (~150 RFX)",
        "Unlimited free regenerations",
        "Advanced AI features",
        "Full branding customization",
        "Priority support",
        "API access"
      ]
    },
    {
      "tier": "enterprise",
      "name": "Enterprise Plan",
      "max_users": "unlimited",
      "max_rfx_per_month": "unlimited",
      "credits_per_month": "unlimited",
      "price_monthly_usd": 499,
      "free_regenerations": "unlimited",
      "features": [
        "Unlimited users",
        "Unlimited credits",
        "Unlimited free regenerations",
        "Custom AI models",
        "White-label solution",
        "Dedicated support",
        "SLA guarantee",
        "Custom integrations"
      ]
    }
  ],
  "count": 4
}
```

**Ejemplo de Uso:**
```bash
curl -X GET "http://localhost:5001/api/credits/plans"
```

**Casos de Uso:**
- Mostrar página de pricing
- Comparar planes en modal de upgrade
- Calcular ROI de upgrade

---

### 5. Obtener Detalles de un Plan

Consulta los detalles de un plan específico.

**Endpoint:**
```http
GET /api/credits/plan/<tier>
```

**Autenticación:** 🔓 Pública (no requiere JWT)

**Path Parameters:**
- `tier`: Tier del plan (free, starter, pro, enterprise)

**Respuesta Exitosa (200):**
```json
{
  "status": "success",
  "data": {
    "tier": "pro",
    "name": "Professional Plan",
    "max_users": 50,
    "max_rfx_per_month": 500,
    "credits_per_month": 1500,
    "price_monthly_usd": 99,
    "free_regenerations": "unlimited",
    "features": [
      "Up to 50 users",
      "1,500 credits per month (~150 RFX)",
      "Unlimited free regenerations",
      "Advanced AI features",
      "Full branding customization",
      "Priority support",
      "API access"
    ]
  }
}
```

**Respuesta de Error (404):**
```json
{
  "status": "error",
  "message": "Plan not found: premium",
  "available_tiers": ["free", "starter", "pro", "enterprise"]
}
```

**Ejemplo de Uso:**
```bash
curl -X GET "http://localhost:5001/api/credits/plan/pro"
```

**Casos de Uso:**
- Mostrar detalles de plan en página de upgrade
- Comparar plan actual vs plan objetivo

---

### 6. Obtener Costos de Operaciones

Consulta los costos en créditos de cada operación.

**Endpoint:**
```http
GET /api/credits/costs
```

**Autenticación:** 🔓 Pública (no requiere JWT)

**Respuesta Exitosa (200):**
```json
{
  "status": "success",
  "data": {
    "extraction": 5,
    "generation": 5,
    "complete": 10,
    "chat_message": 1,
    "regeneration": 5
  }
}
```

**Ejemplo de Uso:**
```bash
curl -X GET "http://localhost:5001/api/credits/costs"
```

**Casos de Uso:**
- Mostrar tooltip con costo de operación
- Calcular créditos necesarios antes de operación
- Documentación de API

---

## 🔄 Endpoints de Operaciones

### 7. Procesar RFX (Consumo: 10 Créditos)

Procesa un documento RFX completo: extracción de datos + generación de propuesta.

**Endpoint:**
```http
POST /api/rfx/process
```

**Autenticación:** 🔒 Requerida (JWT)

**Content-Type:** `multipart/form-data`

**Body Parameters:**
- `files`: Archivo(s) PDF/DOCX (requerido)
- `tipo_rfx`: Tipo de RFX (opcional, default: "catering")

**Flujo de Créditos:**
1. Verifica que el usuario tenga `organization_id`
2. Verifica que haya al menos 10 créditos disponibles
3. Si NO hay créditos → Retorna 402 Payment Required
4. Si hay créditos → Procesa el RFX
5. Consume 10 créditos (5 extracción + 5 generación)
6. Registra transacción en historial
7. Actualiza `rfx_processing_status`

**Respuesta Exitosa (200):**
```json
{
  "status": "success",
  "data": {
    "id": "rfx-uuid",
    "title": "RFX Catering Event",
    "extracted_data": {...},
    "status": "completed"
  }
}
```

**Respuesta de Error - Sin Créditos (402):**
```json
{
  "status": "error",
  "error_type": "insufficient_credits",
  "message": "Insufficient credits for extraction. Required: 10, Available: 8",
  "credits_required": 10,
  "credits_available": 8
}
```

**Ejemplo de Uso:**
```bash
curl -X POST "http://localhost:5001/api/rfx/process" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -F "files=@document.pdf" \
  -F "tipo_rfx=catering"
```

**Casos de Uso:**
- Usuario sube documento RFX para procesamiento completo
- Sistema verifica créditos antes de procesar
- Si sin créditos, mostrar modal de upgrade

---

### 8. Generar Propuesta (Consumo: 5 Créditos o Gratis)

Genera una propuesta comercial basada en datos RFX. Puede ser gratis si hay regeneraciones disponibles.

**Endpoint:**
```http
POST /api/proposals/generate
```

**Autenticación:** 🔒 Requerida (JWT)

**Content-Type:** `application/json`

**Body Parameters:**
```json
{
  "rfx_id": "rfx-uuid",
  "costs": [10.5, 20.0, 15.75]
}
```

**Flujo de Créditos:**
1. Verifica que el usuario tenga `organization_id`
2. Detecta si es primera generación o regeneración
3. **Si es regeneración:**
   - Verifica regeneraciones gratuitas disponibles
   - Si tiene regeneración gratis → 0 créditos ✅
   - Si NO tiene regeneración gratis → 5 créditos
4. **Si es primera generación:** 5 créditos
5. Verifica créditos disponibles (si es necesario)
6. Genera propuesta
7. Consume créditos O marca regeneración gratis usada
8. Actualiza `rfx_processing_status`

**Respuesta Exitosa - Primera Generación (200):**
```json
{
  "status": "success",
  "document_id": "doc-uuid",
  "pdf_url": "/api/download/doc-uuid",
  "proposal": {
    "id": "doc-uuid",
    "rfx_id": "rfx-uuid",
    "content_html": "<html>...</html>",
    "total_cost": 46.25
  },
  "credits_info": {
    "credits_consumed": 5,
    "used_free_regeneration": false,
    "is_regeneration": false
  }
}
```

**Respuesta Exitosa - Regeneración Gratis (200):**
```json
{
  "status": "success",
  "document_id": "doc-uuid-2",
  "pdf_url": "/api/download/doc-uuid-2",
  "proposal": {...},
  "credits_info": {
    "credits_consumed": 0,
    "used_free_regeneration": true,
    "is_regeneration": true
  }
}
```

**Respuesta Exitosa - Regeneración Pagada (200):**
```json
{
  "status": "success",
  "document_id": "doc-uuid-3",
  "pdf_url": "/api/download/doc-uuid-3",
  "proposal": {...},
  "credits_info": {
    "credits_consumed": 5,
    "used_free_regeneration": false,
    "is_regeneration": true
  }
}
```

**Respuesta de Error - Sin Créditos (402):**
```json
{
  "status": "error",
  "error_type": "insufficient_credits",
  "message": "Insufficient credits for generation. Required: 5, Available: 2",
  "credits_required": 5,
  "credits_available": 2
}
```

**Ejemplo de Uso:**
```bash
curl -X POST "http://localhost:5001/api/proposals/generate" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "rfx_id": "rfx-uuid-123",
    "costs": [10.5, 20.0, 15.75]
  }'
```

**Casos de Uso:**
- Usuario genera propuesta por primera vez (5 créditos)
- Usuario regenera propuesta (gratis si tiene regeneraciones disponibles)
- Sistema muestra si será gratis o pagado antes de regenerar

---

### 9. Chat con RFX (Consumo: 1 Crédito por Mensaje) ✅ IMPLEMENTADO

Actualiza un RFX mediante conversación con IA.

**Endpoint:**
```http
POST /api/rfx/<rfx_id>/chat
```

**Autenticación:** 🔒 Requerida (JWT)

**⚠️ IMPORTANTE:** Este endpoint ahora verifica y consume créditos automáticamente.

**Content-Type:** `application/json`

**Body Parameters:**
```json
{
  "message": "Agrega 10 personas más al evento",
  "conversation_history": [
    {"role": "user", "content": "¿Cuántas personas hay?"},
    {"role": "assistant", "content": "Actualmente hay 50 personas"}
  ]
}
```

**Flujo de Créditos:**
1. Verifica que el usuario tenga `organization_id`
2. Verifica que haya al menos 1 crédito disponible
3. Procesa mensaje con IA
4. Actualiza RFX según instrucciones
5. Consume 1 crédito
6. Registra transacción

**Respuesta Exitosa (200):**
```json
{
  "status": "success",
  "message": "RFX updated successfully",
  "response": "He agregado 10 personas más. Ahora el total es de 60 personas.",
  "updated_fields": ["headcount"],
  "credits_consumed": 1
}
```

**Respuesta de Error - Sin Créditos (402):**
```json
{
  "status": "error",
  "error_type": "insufficient_credits",
  "message": "Insufficient credits for chat message. Required: 1, Available: 0",
  "credits_required": 1,
  "credits_available": 0
}
```

**Ejemplo de Uso:**
```bash
curl -X POST "http://localhost:5001/api/rfx/rfx-uuid-123/chat" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Cambia la fecha del evento al 15 de diciembre"
  }'
```

**Casos de Uso:**
- Usuario actualiza RFX mediante chat conversacional
- Cada mensaje consume 1 crédito
- Más económico que regenerar propuesta completa (5 créditos)

---

## 📡 Códigos de Respuesta

### Códigos de Éxito

| Código | Significado | Descripción |
|--------|-------------|-------------|
| **200** | OK | Operación exitosa |
| **201** | Created | Recurso creado exitosamente |

### Códigos de Error del Cliente

| Código | Significado | Descripción |
|--------|-------------|-------------|
| **400** | Bad Request | Datos inválidos en el request |
| **401** | Unauthorized | Token JWT faltante o inválido |
| **402** | Payment Required | **Créditos insuficientes** |
| **403** | Forbidden | Usuario sin organización o sin permisos |
| **404** | Not Found | Recurso no encontrado |

### Códigos de Error del Servidor

| Código | Significado | Descripción |
|--------|-------------|-------------|
| **500** | Internal Server Error | Error interno del servidor |

---

## 💡 Ejemplos de Uso Completos

### Ejemplo 1: Flujo Completo de Procesamiento

```bash
# 1. Login
TOKEN=$(curl -X POST "http://localhost:5001/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"pass123"}' \
  | jq -r '.token')

# 2. Verificar créditos disponibles
curl -X GET "http://localhost:5001/api/credits/info" \
  -H "Authorization: Bearer $TOKEN"
# Respuesta: {"credits_available": 1500, ...}

# 3. Procesar RFX (consume 10 créditos)
curl -X POST "http://localhost:5001/api/rfx/process" \
  -H "Authorization: Bearer $TOKEN" \
  -F "files=@catering_rfx.pdf"
# Respuesta: {"status": "success", "data": {...}}

# 4. Verificar créditos después
curl -X GET "http://localhost:5001/api/credits/info" \
  -H "Authorization: Bearer $TOKEN"
# Respuesta: {"credits_available": 1490, ...}

# 5. Ver historial
curl -X GET "http://localhost:5001/api/credits/history?limit=5" \
  -H "Authorization: Bearer $TOKEN"
```

### Ejemplo 2: Regeneración Gratis vs Pagada

```bash
# 1. Primera generación (5 créditos)
curl -X POST "http://localhost:5001/api/proposals/generate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"rfx_id":"rfx-123","costs":[10,20]}'
# Respuesta: {"credits_consumed": 5, "used_free_regeneration": false}

# 2. Verificar regeneraciones disponibles
curl -X GET "http://localhost:5001/api/credits/regenerations/rfx-123" \
  -H "Authorization: Bearer $TOKEN"
# Respuesta: {"has_free_regeneration": true, "free_regenerations_limit": 3}

# 3. Primera regeneración (GRATIS - Plan STARTER)
curl -X POST "http://localhost:5001/api/proposals/generate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"rfx_id":"rfx-123","costs":[10,20]}'
# Respuesta: {"credits_consumed": 0, "used_free_regeneration": true}

# 4. Verificar regeneraciones después
curl -X GET "http://localhost:5001/api/credits/regenerations/rfx-123" \
  -H "Authorization: Bearer $TOKEN"
# Respuesta: {"free_regenerations_used": 1, "free_regenerations_limit": 3}
```

### Ejemplo 3: Manejo de Créditos Insuficientes

```bash
# 1. Verificar créditos (solo 8 disponibles)
curl -X GET "http://localhost:5001/api/credits/info" \
  -H "Authorization: Bearer $TOKEN"
# Respuesta: {"credits_available": 8}

# 2. Intentar procesar RFX (requiere 10 créditos)
curl -X POST "http://localhost:5001/api/rfx/process" \
  -H "Authorization: Bearer $TOKEN" \
  -F "files=@document.pdf"
# Respuesta 402: {
#   "error_type": "insufficient_credits",
#   "credits_required": 10,
#   "credits_available": 8
# }

# 3. Ver planes disponibles
curl -X GET "http://localhost:5001/api/credits/plans"
# Respuesta: Lista de planes con más créditos

# 4. Upgrade de plan (endpoint de billing - no implementado aún)
# POST /api/billing/upgrade {"plan": "pro"}
```

---

## 🎯 Mejores Prácticas

### 1. Verificar Créditos Antes de Operaciones Costosas

```javascript
// Frontend - React
async function processRFX(file) {
  // 1. Verificar créditos primero
  const credits = await fetch('/api/credits/info', {
    headers: { 'Authorization': `Bearer ${token}` }
  }).then(r => r.json());
  
  if (credits.data.credits_available < 10) {
    showUpgradeModal();
    return;
  }
  
  // 2. Procesar RFX
  const result = await fetch('/api/rfx/process', {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` },
    body: formData
  });
}
```

### 2. Mostrar Indicador de Créditos

```javascript
// Hook personalizado
function useCredits() {
  const [credits, setCredits] = useState(null);
  
  useEffect(() => {
    fetch('/api/credits/info', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    .then(r => r.json())
    .then(data => setCredits(data.data));
  }, []);
  
  return credits;
}

// Componente
function CreditsIndicator() {
  const credits = useCredits();
  
  return (
    <div className="credits-badge">
      {credits?.credits_available} / {credits?.credits_total} créditos
      <ProgressBar value={credits?.credits_percentage} />
    </div>
  );
}
```

### 3. Manejar Errores de Créditos

```javascript
async function handleOperation() {
  try {
    const response = await fetch('/api/rfx/process', {...});
    const data = await response.json();
    
    if (response.status === 402) {
      // Sin créditos
      showModal({
        title: 'Créditos Insuficientes',
        message: data.message,
        actions: [
          { label: 'Ver Planes', onClick: () => navigate('/pricing') },
          { label: 'Cancelar', onClick: () => closeModal() }
        ]
      });
    }
  } catch (error) {
    console.error('Error:', error);
  }
}
```

### 4. Mostrar Costo Antes de Operación

```javascript
function RegenerateButton({ rfxId }) {
  const [regenInfo, setRegenInfo] = useState(null);
  
  useEffect(() => {
    fetch(`/api/credits/regenerations/${rfxId}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    .then(r => r.json())
    .then(data => setRegenInfo(data.data));
  }, [rfxId]);
  
  return (
    <button onClick={handleRegenerate}>
      {regenInfo?.has_free_regeneration 
        ? '🎁 Regenerar Gratis' 
        : '💳 Regenerar (5 créditos)'}
    </button>
  );
}
```

---

## 📞 Soporte

### Contacto

- **Email:** support@rfx-automation.com
- **Documentación:** https://docs.rfx-automation.com
- **Status:** https://status.rfx-automation.com

### Reportar Problemas

Si encuentras algún problema con el sistema de créditos:

1. Verifica tu plan actual: `GET /api/credits/info`
2. Revisa el historial: `GET /api/credits/history`
3. Contacta soporte con el `transaction_id` del error

---

**Última Actualización:** 9 de Diciembre, 2025  
**Versión de API:** 1.0  
**Autor:** RFX Automation Team
