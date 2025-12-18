# 📘 Guía de API - Sistema de Organizaciones y Créditos

**Para:** Equipo Frontend  
**Fecha:** 11 de Diciembre, 2025  
**Base URL:** `http://localhost:5001` (desarrollo) | `https://tu-servidor.com` (producción)

---

## 🔐 Autenticación

**TODOS los endpoints requieren JWT token en el header:**

```javascript
headers: {
  'Authorization': `Bearer ${token}`,
  'Content-Type': 'application/json'
}
```

---

## 📋 ENDPOINTS DE ORGANIZACIONES

### 1. Obtener Organización Actual del Usuario

```
GET /api/organization/current
```

**Cuándo usarlo:**
- Al cargar la aplicación (después del login)
- Para mostrar información de la organización en el dashboard
- Para verificar si el usuario pertenece a una organización

**Reglas:**
- Esto es CRÍTICO para saber si el usuario tiene acceso al sistema
- Si no tiene organización, debe mostrar error o pantalla de onboarding
- Usar para obtener los créditos disponibles y límites del plan

**Respuesta exitosa (200):**
```json
{
  "status": "success",
  "data": {
    "id": "8ed7f53e-86c7-4dec-861b-822b8a25ed6d",
    "name": "Sabra Corporation",
    "slug": "sabra-corp-official",
    "is_active": true,
    "trial_ends_at": "2025-12-25T00:00:00Z",
    "created_at": "2025-12-11T12:00:00Z",
    "plan": {
      "tier": "pro",
      "name": "Professional Plan",
      "max_users": 50,
      "max_rfx_per_month": 500,
      "credits_per_month": 1500,
      "price_monthly_usd": 99.0,
      "features": [
        "Up to 50 users",
        "1500 credits per month (~150 RFX)",
        "Unlimited free regenerations",
        "Advanced proposal generation",
        "Custom branding",
        "Priority email support",
        "Advanced analytics",
        "API access"
      ],
      "free_regenerations": "unlimited"
    },
    "usage": {
      "users": {
        "current": 5,
        "limit": 50,
        "can_add_more": true
      },
      "rfx_this_month": {
        "current": 102,
        "limit": 500,
        "can_create_more": true
      }
    }
  }
}
```

**Ejemplo de uso en Frontend:**
```javascript
// Al cargar la app
async function loadOrganization() {
  try {
    const response = await fetch('/api/organization/current', {
      headers: {
        'Authorization': `Bearer ${getToken()}`
      }
    });
    
    const data = await response.json();
    
    if (data.status === 'success') {
      // Guardar en estado global
      setOrganization(data.data);
      
      // Mostrar nombre de la org en navbar
      setOrgName(data.data.name);
      
      // Verificar si puede crear más RFX
      if (!data.data.usage.rfx_this_month.can_create_more) {
        showUpgradeModal();
      }
    }
  } catch (error) {
    console.error('Error loading organization:', error);
    // Redirigir a página de error o onboarding
  }
}
```

---

### 2. Obtener Miembros de la Organización

```
GET /api/organization/members
```

**Cuándo usarlo:**
- En la página de "Equipo" o "Miembros"
- Para mostrar quién tiene acceso a la organización
- Para gestión de usuarios (futuro)

**Reglas:**
- Solo muestra usuarios de la misma organización
- Incluye roles (owner, admin, member)
- Útil para saber quién procesó cada RFX

**Respuesta exitosa (200):**
```json
{
  "status": "success",
  "data": [
    {
      "id": "186ea35f-3cf8-480f-a7d3-0af178c09498",
      "email": "daniel@sabra.com",
      "full_name": "Daniel Iribarren",
      "username": "daniel",
      "role": "owner",
      "created_at": "2025-06-06T16:55:32Z"
    },
    {
      "id": "abc-123-def",
      "email": "maria@sabra.com",
      "full_name": "Maria Garcia",
      "username": "maria",
      "role": "admin",
      "created_at": "2025-07-15T10:30:00Z"
    }
  ],
  "count": 2
}
```

**Ejemplo de uso en Frontend:**
```javascript
// En página de equipo
async function loadTeamMembers() {
  const response = await fetch('/api/organization/members', {
    headers: { 'Authorization': `Bearer ${getToken()}` }
  });
  
  const data = await response.json();
  
  // Mostrar en tabla
  setMembers(data.data);
  
  // Mostrar badge según rol
  data.data.forEach(member => {
    const badge = member.role === 'owner' ? '👑 Owner' : 
                  member.role === 'admin' ? '⚙️ Admin' : 
                  '👤 Member';
  });
}
```

---

### 3. Obtener Planes Disponibles

```
GET /api/organization/plans
```

**Cuándo usarlo:**
- En página de "Pricing" o "Planes"
- Para mostrar opciones de upgrade
- NO requiere autenticación (es público)

**Reglas:**
- Este endpoint es PÚBLICO (no requiere token)
- Mostrar para comparar planes
- Útil para página de marketing/ventas

**Respuesta exitosa (200):**
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
      "price_monthly_usd": 0.0,
      "free_regenerations": 1,
      "features": [
        "Up to 2 users",
        "100 credits per month (~10 RFX)",
        "1 free regeneration per proposal",
        "Basic proposal generation",
        "Email support",
        "Community access"
      ]
    },
    {
      "tier": "starter",
      "name": "Starter Plan",
      "max_users": 5,
      "max_rfx_per_month": 25,
      "credits_per_month": 250,
      "price_monthly_usd": 29.0,
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
      "price_monthly_usd": 99.0,
      "free_regenerations": "unlimited",
      "features": [
        "Up to 50 users",
        "1500 credits per month (~150 RFX)",
        "Unlimited free regenerations",
        "Advanced proposal generation",
        "Custom branding",
        "Priority email support",
        "Advanced analytics",
        "API access"
      ]
    },
    {
      "tier": "enterprise",
      "name": "Enterprise Plan",
      "max_users": 999999,
      "max_rfx_per_month": 999999,
      "credits_per_month": 999999,
      "price_monthly_usd": 499.0,
      "free_regenerations": "unlimited",
      "features": [
        "Unlimited users",
        "Unlimited RFX",
        "Unlimited credits",
        "Unlimited free regenerations",
        "White-label branding",
        "Dedicated account manager",
        "24/7 phone support",
        "Custom integrations",
        "SLA guarantee",
        "Advanced security features",
        "Custom training"
      ]
    }
  ],
  "count": 4
}
```

**Ejemplo de uso en Frontend:**
```javascript
// En página de pricing (sin autenticación)
async function loadPricingPlans() {
  const response = await fetch('/api/organization/plans');
  const data = await response.json();
  
  // Renderizar cards de planes
  data.data.forEach(plan => {
    renderPlanCard({
      name: plan.name,
      price: plan.price_monthly_usd,
      features: plan.features,
      isPopular: plan.tier === 'pro'
    });
  });
}
```

---

### 4. Obtener Información de Upgrade

```
GET /api/organization/upgrade-info
```

**Cuándo usarlo:**
- Cuando el usuario está cerca de alcanzar límites
- En modal de "Upgrade Plan"
- Para mostrar beneficios del siguiente plan

**Reglas:**
- Compara plan actual vs siguiente plan disponible
- Muestra beneficios específicos del upgrade
- Si ya está en Enterprise, no hay upgrade disponible

**Respuesta exitosa (200):**
```json
{
  "status": "success",
  "data": {
    "current_plan": {
      "tier": "free",
      "name": "Free Plan",
      "max_users": 2,
      "max_rfx_per_month": 10,
      "credits_per_month": 100,
      "price_monthly_usd": 0.0
    },
    "upgrade_available": true,
    "next_plan": {
      "tier": "starter",
      "name": "Starter Plan",
      "max_users": 5,
      "max_rfx_per_month": 25,
      "credits_per_month": 250,
      "price_monthly_usd": 29.0
    },
    "benefits": [
      "Increase users from 2 to 5",
      "Increase RFX from 10 to 25/month",
      "Advanced proposal generation",
      "Basic branding",
      "Priority email support"
    ]
  }
}
```

**Ejemplo de uso en Frontend:**
```javascript
// Cuando usuario alcanza límite
async function showUpgradeModal() {
  const response = await fetch('/api/organization/upgrade-info', {
    headers: { 'Authorization': `Bearer ${getToken()}` }
  });
  
  const data = await response.json();
  
  if (data.data.upgrade_available) {
    openModal({
      title: `Upgrade to ${data.data.next_plan.name}`,
      price: `$${data.data.next_plan.price_monthly_usd}/month`,
      benefits: data.data.benefits,
      onConfirm: () => redirectToCheckout(data.data.next_plan.tier)
    });
  }
}
```

---

## 💳 ENDPOINTS DE CRÉDITOS

### 5. Obtener Información de Créditos

```
GET /api/credits/info
```

**Cuándo usarlo:**
- Al cargar el dashboard
- Antes de procesar un RFX (verificar si hay créditos)
- Para mostrar barra de progreso de créditos

**Reglas:**
- **CRÍTICO:** Verificar ANTES de permitir crear RFX
- Si `credits_available <= 0`, mostrar modal de upgrade
- Actualizar después de cada operación que consuma créditos

**Respuesta exitosa (200):**
```json
{
  "status": "success",
  "data": {
    "status": "success",
    "credits_total": 1500,
    "credits_used": 84,
    "credits_available": 1416,
    "credits_percentage": 94.4,
    "reset_date": "2026-01-11T12:00:00Z",
    "plan_tier": "pro"
  }
}
```

**Ejemplo de uso en Frontend:**
```javascript
// En dashboard - mostrar barra de créditos
async function loadCreditsInfo() {
  const response = await fetch('/api/credits/info', {
    headers: { 'Authorization': `Bearer ${getToken()}` }
  });
  
  const data = await response.json();
  const credits = data.data;
  
  // Mostrar barra de progreso
  setCreditsBar({
    percentage: credits.credits_percentage,
    used: credits.credits_used,
    total: credits.credits_total,
    available: credits.credits_available
  });
  
  // Alerta si quedan pocos créditos
  if (credits.credits_percentage < 20) {
    showWarning(`Solo quedan ${credits.credits_available} créditos. Se resetean el ${formatDate(credits.reset_date)}`);
  }
  
  // Bloquear acciones si no hay créditos
  if (credits.credits_available <= 0) {
    disableCreateRFXButton();
    showUpgradeModal();
  }
}

// ANTES de crear RFX - verificar créditos
async function beforeCreateRFX() {
  const response = await fetch('/api/credits/info', {
    headers: { 'Authorization': `Bearer ${getToken()}` }
  });
  
  const data = await response.json();
  
  if (data.data.credits_available < 10) { // 10 créditos = 1 RFX completo
    alert('No tienes suficientes créditos. Necesitas 10 créditos para procesar un RFX.');
    return false;
  }
  
  return true; // OK, puede proceder
}
```

---

### 6. Obtener Historial de Transacciones

```
GET /api/credits/history?limit=50&offset=0
```

**Cuándo usarlo:**
- En página de "Historial de Créditos"
- Para auditoría de uso
- Para mostrar qué operaciones consumieron créditos

**Parámetros Query:**
- `limit` (opcional): Número de transacciones (default: 50, max: 100)
- `offset` (opcional): Para paginación (default: 0)

**Reglas:**
- Útil para transparencia con el usuario
- Mostrar qué RFX consumió créditos
- Incluye recargas mensuales

**Respuesta exitosa (200):**
```json
{
  "status": "success",
  "data": [
    {
      "id": "84b50cfa-12e4-4c8e-b06c-312921b65c26",
      "organization_id": "8ed7f53e-86c7-4dec-861b-822b8a25ed6d",
      "user_id": "186ea35f-3cf8-480f-a7d3-0af178c09498",
      "rfx_id": "abc-123",
      "amount": -10,
      "type": "complete",
      "description": "Credits consumed for complete",
      "metadata": {},
      "created_at": "2025-12-11T10:30:00Z"
    },
    {
      "id": "def-456",
      "organization_id": "8ed7f53e-86c7-4dec-861b-822b8a25ed6d",
      "user_id": null,
      "rfx_id": null,
      "amount": 1500,
      "type": "monthly_reset",
      "description": "Monthly credits reset for pro plan",
      "metadata": { "plan_tier": "pro" },
      "created_at": "2025-12-01T00:00:00Z"
    }
  ],
  "count": 2,
  "pagination": {
    "limit": 50,
    "offset": 0
  }
}
```

**Ejemplo de uso en Frontend:**
```javascript
// En página de historial
async function loadCreditsHistory(page = 0) {
  const limit = 20;
  const offset = page * limit;
  
  const response = await fetch(`/api/credits/history?limit=${limit}&offset=${offset}`, {
    headers: { 'Authorization': `Bearer ${getToken()}` }
  });
  
  const data = await response.json();
  
  // Renderizar tabla
  data.data.forEach(transaction => {
    const icon = transaction.amount > 0 ? '➕' : '➖';
    const color = transaction.amount > 0 ? 'green' : 'red';
    
    addRow({
      date: formatDate(transaction.created_at),
      type: transaction.type,
      amount: `${icon} ${Math.abs(transaction.amount)} créditos`,
      description: transaction.description,
      color: color
    });
  });
}
```

---

### 7. Obtener Costos de Operaciones

```
GET /api/credits/costs
```

**Cuándo usarlo:**
- Para mostrar "tooltips" de cuánto cuesta cada operación
- En página de ayuda/FAQ
- NO requiere autenticación (es público)

**Reglas:**
- Endpoint público (sin token)
- Útil para transparencia de precios
- Mostrar al usuario antes de ejecutar operación

**Respuesta exitosa (200):**
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

**Ejemplo de uso en Frontend:**
```javascript
// Mostrar tooltip en botón
<button 
  title="Procesar RFX (costo: 10 créditos)"
  onClick={processRFX}
>
  Procesar RFX
</button>

// O cargar costos al inicio
async function loadCosts() {
  const response = await fetch('/api/credits/costs');
  const data = await response.json();
  
  setCosts(data.data);
  
  // Usar en tooltips
  setTooltip('extraction', `Extracción de datos: ${data.data.extraction} créditos`);
  setTooltip('generation', `Generación de propuesta: ${data.data.generation} créditos`);
}
```

---

### 8. Obtener Info de Regeneraciones para un RFX

```
GET /api/credits/regenerations/{rfx_id}
```

**Cuándo usarlo:**
- Antes de regenerar una propuesta
- Para saber si la regeneración es gratis o consumirá créditos
- En la página de detalle de RFX

**Reglas:**
- **IMPORTANTE:** Planes PRO y Enterprise tienen regeneraciones ilimitadas gratis
- Plan FREE: 1 regeneración gratis, luego 5 créditos c/u
- Plan STARTER: 3 regeneraciones gratis, luego 5 créditos c/u

**Respuesta exitosa (200):**
```json
{
  "status": "success",
  "data": {
    "rfx_id": "abc-123",
    "has_free_regeneration": true,
    "free_regenerations_used": 0,
    "free_regenerations_limit": "unlimited",
    "regeneration_count": 2,
    "plan_tier": "pro",
    "message": "Unlimited regenerations available"
  }
}
```

**Ejemplo de uso en Frontend:**
```javascript
// Antes de regenerar propuesta
async function beforeRegenerate(rfxId) {
  const response = await fetch(`/api/credits/regenerations/${rfxId}`, {
    headers: { 'Authorization': `Bearer ${getToken()}` }
  });
  
  const data = await response.json();
  
  if (data.data.has_free_regeneration) {
    // Regeneración gratis
    return confirm('Esta regeneración es GRATIS. ¿Continuar?');
  } else {
    // Consumirá créditos
    const creditsInfo = await fetch('/api/credits/info', {
      headers: { 'Authorization': `Bearer ${getToken()}` }
    }).then(r => r.json());
    
    if (creditsInfo.data.credits_available < 5) {
      alert('No tienes suficientes créditos para regenerar (necesitas 5 créditos)');
      return false;
    }
    
    return confirm('Esta regeneración consumirá 5 créditos. ¿Continuar?');
  }
}
```

---

## 🚨 MANEJO DE ERRORES

### Errores Comunes

**403 - Usuario sin organización:**
```json
{
  "status": "error",
  "message": "User must belong to an organization"
}
```
**Acción:** Redirigir a página de onboarding o contactar soporte

**402 - Créditos insuficientes:**
```json
{
  "status": "error",
  "error_type": "insufficient_credits",
  "message": "Insufficient credits. Required: 10, Available: 5",
  "credits_required": 10,
  "credits_available": 5,
  "plan_tier": "free",
  "suggestion": "Consider upgrading your plan or waiting for monthly credit reset"
}
```
**Acción:** Mostrar modal de upgrade con información del siguiente plan

**403 - Límite de plan alcanzado:**
```json
{
  "status": "error",
  "error_type": "plan_limit_exceeded",
  "message": "Monthly RFX limit reached. Your Free Plan allows up to 10 RFX per month.",
  "limit_type": "rfx",
  "current_value": 10,
  "limit_value": 10,
  "plan_tier": "free",
  "suggestion": "Upgrade your plan to increase rfx limit"
}
```
**Acción:** Mostrar modal de upgrade

---

## 📊 FLUJO COMPLETO DE EJEMPLO

### Flujo: Usuario crea un RFX

```javascript
async function createRFXFlow() {
  // 1. Verificar organización
  const orgResponse = await fetch('/api/organization/current', {
    headers: { 'Authorization': `Bearer ${getToken()}` }
  });
  
  if (!orgResponse.ok) {
    alert('No perteneces a ninguna organización');
    return;
  }
  
  const orgData = await orgResponse.json();
  
  // 2. Verificar límite de RFX del mes
  if (!orgData.data.usage.rfx_this_month.can_create_more) {
    showUpgradeModal('Has alcanzado el límite de RFX de tu plan');
    return;
  }
  
  // 3. Verificar créditos disponibles
  const creditsResponse = await fetch('/api/credits/info', {
    headers: { 'Authorization': `Bearer ${getToken()}` }
  });
  
  const creditsData = await creditsResponse.json();
  
  if (creditsData.data.credits_available < 10) {
    alert(`No tienes suficientes créditos. Disponibles: ${creditsData.data.credits_available}, Necesarios: 10`);
    showUpgradeModal('Necesitas más créditos');
    return;
  }
  
  // 4. Proceder con la creación
  const formData = new FormData();
  formData.append('file', selectedFile);
  
  const createResponse = await fetch('/api/rfx/process', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${getToken()}`
    },
    body: formData
  });
  
  if (createResponse.ok) {
    // 5. Actualizar créditos en UI
    await loadCreditsInfo();
    
    alert('RFX procesado exitosamente!');
  } else if (createResponse.status === 402) {
    // Error de créditos insuficientes
    const error = await createResponse.json();
    alert(error.message);
    showUpgradeModal();
  }
}
```

---

## ✅ CHECKLIST DE INTEGRACIÓN

### Para el Frontend Developer:

- [ ] Guardar token JWT en localStorage/sessionStorage
- [ ] Crear función `getToken()` para obtener token
- [ ] Implementar interceptor para agregar Authorization header automáticamente
- [ ] Llamar `/api/organization/current` al cargar la app
- [ ] Llamar `/api/credits/info` al cargar dashboard
- [ ] Verificar créditos ANTES de permitir crear RFX
- [ ] Mostrar barra de progreso de créditos en navbar/sidebar
- [ ] Implementar modal de upgrade cuando se alcancen límites
- [ ] Manejar errores 402 (créditos) y 403 (límites) específicamente
- [ ] Actualizar créditos después de cada operación que los consuma
- [ ] Mostrar tooltips con costos de operaciones
- [ ] Implementar página de historial de créditos (opcional)

---

## 🔧 CONFIGURACIÓN DEL SERVIDOR

**Los endpoints YA ESTÁN FUNCIONANDO en el servidor** ✅

Los blueprints están registrados en `backend/app.py`:
- Línea 86: `app.register_blueprint(organization_bp)` → `/api/organization/*`
- Línea 87: `app.register_blueprint(credits_bp)` → `/api/credits/*`

**No se requiere configuración adicional en el servidor.**

---

## 📞 SOPORTE

Si encuentras algún problema:
1. Verificar que el token JWT sea válido
2. Verificar que el usuario tenga `organization_id` en la base de datos
3. Revisar logs del backend para errores específicos
4. Contactar al equipo de backend con el `correlation_id` del error

---

**Documentación creada:** 11 de Diciembre, 2025  
**Versión:** 1.0  
**Estado:** ✅ Producción Ready
