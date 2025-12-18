# 📊 ANÁLISIS DE IMPLEMENTACIÓN DE PLANES - Sistema de Créditos

**Fecha:** 8 de Diciembre, 2025  
**Status:** 🔍 ANÁLISIS COMPLETADO

---

## 🔍 ESTADO ACTUAL

### ✅ Lo que YA EXISTE

#### 1. Tabla `organizations` (Parcial)
```sql
✅ id (UUID)
✅ name (VARCHAR)
✅ slug (VARCHAR)
✅ plan_tier (VARCHAR) DEFAULT 'free'  ← YA EXISTE
✅ max_users (INTEGER) DEFAULT 2       ← YA EXISTE
✅ max_rfx_per_month (INTEGER) DEFAULT 10  ← YA EXISTE
✅ is_active (BOOLEAN)
✅ trial_ends_at (TIMESTAMPTZ)
✅ created_at (TIMESTAMPTZ)
✅ updated_at (TIMESTAMPTZ)

❌ credits_total (NO EXISTE)
❌ credits_used (NO EXISTE)
❌ credits_reset_date (NO EXISTE)
```

#### 2. Tabla `users` (Sin columnas de planes)
```sql
✅ id (UUID)
✅ email (TEXT)
✅ full_name (TEXT)
✅ organization_id (UUID)  ← YA EXISTE (multi-tenant)
✅ role (VARCHAR)  ← YA EXISTE (owner/admin/member)
✅ created_at (TIMESTAMPTZ)

❌ personal_plan_tier (NO EXISTE)
❌ credits_total (NO EXISTE)
❌ credits_used (NO EXISTE)
❌ credits_reset_date (NO EXISTE)
```

#### 3. Código Backend
```
✅ backend/core/plans.py - EXISTE (hardcoded, pero desactualizado)
❌ backend/services/credits_service.py - NO EXISTE
❌ backend/api/credits.py - NO EXISTE
❌ Tabla credit_transactions - NO EXISTE
```

---

## 🎯 PLAN DE IMPLEMENTACIÓN (KISS)

### FASE 1: Migración de Base de Datos ✅ PRIORIDAD ALTA

**Objetivo:** Agregar columnas de créditos a tablas existentes

#### 1.1 Actualizar Tabla `users`
```sql
-- Agregar columnas de plan personal
ALTER TABLE users ADD COLUMN IF NOT EXISTS 
    personal_plan_tier VARCHAR(20) DEFAULT 'free';
    
ALTER TABLE users ADD COLUMN IF NOT EXISTS 
    credits_total INTEGER DEFAULT 100;
    
ALTER TABLE users ADD COLUMN IF NOT EXISTS 
    credits_used INTEGER DEFAULT 0;
    
ALTER TABLE users ADD COLUMN IF NOT EXISTS 
    credits_reset_date TIMESTAMPTZ DEFAULT NOW() + INTERVAL '1 month';

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_users_plan_tier 
    ON users(personal_plan_tier);
    
CREATE INDEX IF NOT EXISTS idx_users_credits_reset 
    ON users(credits_reset_date);
```

#### 1.2 Actualizar Tabla `organizations`
```sql
-- Agregar columnas de créditos (plan_tier ya existe)
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS 
    credits_total INTEGER DEFAULT 500;
    
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS 
    credits_used INTEGER DEFAULT 0;
    
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS 
    credits_reset_date TIMESTAMPTZ DEFAULT NOW() + INTERVAL '1 month';

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_orgs_plan_tier 
    ON organizations(plan_tier);
    
CREATE INDEX IF NOT EXISTS idx_orgs_credits_reset 
    ON organizations(credits_reset_date);
```

#### 1.3 Crear Tabla `credit_transactions`
```sql
CREATE TABLE IF NOT EXISTS credit_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    
    amount INTEGER NOT NULL,
    type VARCHAR(50) NOT NULL,
    description TEXT,
    metadata JSONB,
    
    rfx_id UUID REFERENCES rfx_v2(id) ON DELETE SET NULL,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CHECK (amount != 0),
    CHECK (user_id IS NOT NULL OR organization_id IS NOT NULL)
);

-- Índices para queries rápidas
CREATE INDEX idx_credit_trans_user 
    ON credit_transactions(user_id, created_at DESC);
    
CREATE INDEX idx_credit_trans_org 
    ON credit_transactions(organization_id, created_at DESC);
    
CREATE INDEX idx_credit_trans_type 
    ON credit_transactions(type);
    
CREATE INDEX idx_credit_trans_rfx 
    ON credit_transactions(rfx_id);
```

#### 1.4 Inicializar Créditos para Sabra Corp
```sql
-- Actualizar Sabra Corporation con plan PRO
UPDATE organizations
SET 
    plan_tier = 'pro',
    credits_total = 1500,
    credits_used = 0,
    credits_reset_date = NOW() + INTERVAL '1 month'
WHERE slug = 'sabra-corp-official';
```

---

### FASE 2: Backend Core ✅ PRIORIDAD ALTA

#### 2.1 Actualizar `backend/core/plans.py`

**Cambios necesarios:**
- ✅ Agregar plan STARTER
- ✅ Actualizar límites según tu especificación
- ✅ Agregar costos de operaciones

```python
from enum import Enum

class PlanTier(str, Enum):
    FREE = "free"
    STARTER = "starter"
    PRO = "pro"
    ENTERPRISE = "enterprise"

# Créditos mensuales por plan
PLAN_CREDITS = {
    PlanTier.FREE: 100,
    PlanTier.STARTER: 500,
    PlanTier.PRO: 1500,
    PlanTier.ENTERPRISE: 5000,
}

# Precio mensual (USD cents)
PLAN_PRICES = {
    PlanTier.FREE: 0,
    PlanTier.STARTER: 4900,    # $49
    PlanTier.PRO: 9900,        # $99
    PlanTier.ENTERPRISE: 29900, # $299
}

# Usuarios máximos por plan
PLAN_MAX_USERS = {
    PlanTier.FREE: 1,
    PlanTier.STARTER: 2,
    PlanTier.PRO: 5,
    PlanTier.ENTERPRISE: None,  # Unlimited
}

# Costos de operaciones (en créditos)
CREDIT_COSTS = {
    "rfx_process": 10,      # Procesar un RFX
    "chat_message": 1,      # Mensaje de chat
    "proposal_generate": 5, # Generar propuesta
}
```

#### 2.2 Crear `backend/services/credits_service.py`

**Funciones principales:**
- `get_credits_remaining(user)` - Obtener créditos disponibles
- `check_credits(user, cost)` - Verificar si hay suficientes créditos
- `consume_credits(user, cost, type, rfx_id)` - Consumir créditos y registrar transacción
- `get_credit_transactions(user, limit)` - Historial de transacciones

#### 2.3 Crear `backend/models/credit_transaction.py`

**Modelo para tabla credit_transactions:**
- Mapeo ORM de la tabla
- Métodos helper para crear transacciones
- Método `to_dict()` para JSON responses

---

### FASE 3: Integración en Endpoints Existentes ✅ PRIORIDAD MEDIA

#### 3.1 Integrar en `/api/rfx/process`

**Antes de procesar RFX:**
```python
# 1. Verificar créditos
cost = CREDIT_COSTS["rfx_process"]  # 10 créditos
if not CreditsService.check_credits(user, cost):
    return jsonify({
        "status": "error",
        "error": "insufficient_credits",
        "message": f"Need {cost} credits, have {remaining}"
    }), 402

# 2. Procesar RFX
result = process_rfx(...)

# 3. Consumir créditos DESPUÉS de éxito
CreditsService.consume_credits(user, cost, "rfx_process", rfx_id)
```

#### 3.2 Integrar en Chat Agent

**Antes de cada mensaje:**
```python
cost = CREDIT_COSTS["chat_message"]  # 1 crédito
if not CreditsService.check_credits(user, cost):
    raise InsufficientCreditsError()

# Procesar mensaje
response = chat_agent.send(message)

# Consumir crédito
CreditsService.consume_credits(user, cost, "chat_message")
```

---

### FASE 4: Nuevos Endpoints API ✅ PRIORIDAD MEDIA

#### 4.1 `GET /api/credits/info`
```json
{
  "status": "success",
  "data": {
    "plan_tier": "pro",
    "credits_total": 1500,
    "credits_used": 245,
    "credits_remaining": 1255,
    "reset_date": "2025-01-08T00:00:00Z",
    "billing_type": "organization"
  }
}
```

#### 4.2 `GET /api/credits/history`
```json
{
  "status": "success",
  "data": [
    {
      "id": "uuid",
      "amount": -10,
      "type": "rfx_process",
      "description": "RFX processed",
      "rfx_id": "uuid",
      "created_at": "2025-12-08T20:00:00Z"
    }
  ]
}
```

#### 4.3 `GET /api/plans/available`
```json
{
  "status": "success",
  "data": [
    {
      "tier": "free",
      "name": "Free Plan",
      "credits_monthly": 100,
      "max_users": 1,
      "price_usd": 0,
      "features": [...]
    },
    ...
  ]
}
```

---

### FASE 5: Cron Job Reset Mensual ⏰ PRIORIDAD BAJA

**Ejecutar diariamente:**
```python
# backend/tasks/credits_reset.py

def reset_monthly_credits():
    """Resetea créditos cada mes"""
    today = datetime.now()
    
    # Usuarios que necesitan reset
    users = User.query.filter(
        User.credits_reset_date <= today
    ).all()
    
    for user in users:
        plan = PlanTier(user.personal_plan_tier)
        new_credits = PLAN_CREDITS[plan]
        
        user.credits_used = 0
        user.credits_total = new_credits
        user.credits_reset_date = today + timedelta(days=30)
        
        # Log transaction
        CreditTransaction.create(
            user_id=user.id,
            amount=new_credits,
            type="monthly_reset"
        )
    
    db.session.commit()
```

**Configurar en cron:**
```bash
# Ejecutar diariamente a las 00:00
0 0 * * * cd /path/to/backend && python -m backend.tasks.credits_reset
```

---

## 📋 COMPARACIÓN: Hardcoded vs Tu Especificación

| Aspecto | Hardcoded Actual | Tu Especificación | Acción |
|---------|------------------|-------------------|--------|
| **Planes** | free, pro, enterprise | free, starter, pro, enterprise | ✅ Agregar STARTER |
| **Free Credits** | 10 RFX/mes | 100 créditos/mes | ✅ Cambiar a créditos |
| **Starter** | No existe | 500 créditos, 2 users, $49 | ✅ Crear plan |
| **Pro Credits** | 100 RFX/mes | 1500 créditos/mes | ✅ Actualizar |
| **Enterprise** | Unlimited | 5000 créditos/mes | ✅ Cambiar de unlimited |
| **Max Users Free** | 2 | 1 | ✅ Ajustar |
| **Max Users Pro** | 10 | 5 | ✅ Ajustar |
| **Sistema** | Límites fijos | Sistema de créditos | ✅ Implementar créditos |

---

## 🚨 DIFERENCIAS CLAVE: Tu Plan vs Lo Implementado

### ❌ Lo que FALTA Implementar

1. **Sistema de Créditos** - Actualmente solo hay límites fijos (max_rfx_per_month)
2. **Plan STARTER** - No existe en el código actual
3. **Tabla credit_transactions** - No existe
4. **CreditsService** - No existe
5. **Endpoints de créditos** - No existen
6. **Integración en RFX/Chat** - No consume créditos
7. **Reset mensual** - No existe

### ✅ Lo que SÍ Existe (Pero Desactualizado)

1. **Tabla organizations** - Tiene `plan_tier`, `max_users`, `max_rfx_per_month`
2. **backend/core/plans.py** - Existe pero con planes viejos
3. **Multi-tenancy** - Ya implementado (organization_id)
4. **Roles** - Ya implementado (owner/admin/member)

---

## 🎯 RECOMENDACIÓN: Orden de Implementación

### Prioridad 1 (Esta Semana)
1. ✅ **Migración BD** - Agregar columnas de créditos
2. ✅ **Actualizar plans.py** - Con tu especificación
3. ✅ **CreditsService** - Lógica core de créditos
4. ✅ **Integrar en RFX** - Consumir créditos al procesar

### Prioridad 2 (Próxima Semana)
5. ✅ **Endpoints API** - `/api/credits/info` y `/api/credits/history`
6. ✅ **Integrar en Chat** - Consumir créditos por mensaje
7. ✅ **Frontend** - Indicador de créditos

### Prioridad 3 (Futuro)
8. ⏰ **Cron Job** - Reset mensual
9. 💳 **Stripe** - Pagos y upgrades
10. 📊 **Analytics** - Dashboard de uso

---

## 📊 ARQUITECTURA: Hardcoded vs Base de Datos

### Opción A: Hardcoded (Actual + Tu Plan)
```
✅ PROS:
- Simple de implementar
- No requiere migraciones complejas
- Cambios rápidos en código
- Fácil de testear

❌ CONTRAS:
- Cambiar plan requiere deploy
- No se pueden crear planes custom
- No hay historial de cambios de planes
```

### Opción B: Base de Datos (Tabla subscription_plans)
```
✅ PROS:
- Planes dinámicos sin deploy
- Planes custom por cliente
- Historial de cambios
- A/B testing de precios

❌ CONTRAS:
- Más complejo de implementar
- Requiere admin UI
- Más queries a BD
```

### ✅ RECOMENDACIÓN: Híbrido (KISS)

**Mantener hardcoded PERO con créditos en BD:**

```python
# Planes hardcoded (fácil de cambiar)
PLAN_CREDITS = {
    "free": 100,
    "starter": 500,
    "pro": 1500,
    "enterprise": 5000
}

# Créditos en BD (tracking real-time)
organizations.credits_total = 1500
organizations.credits_used = 245
```

**Beneficios:**
- ✅ Simple (KISS)
- ✅ Planes fáciles de modificar
- ✅ Tracking preciso de uso
- ✅ No overengineering

---

## ✅ CHECKLIST DE IMPLEMENTACIÓN

### Fase 1: Base de Datos
- [ ] Migración: Agregar columnas a `users`
- [ ] Migración: Agregar columnas a `organizations`
- [ ] Migración: Crear tabla `credit_transactions`
- [ ] Migración: Inicializar Sabra Corp con plan PRO
- [ ] Verificar índices creados

### Fase 2: Backend Core
- [ ] Actualizar `backend/core/plans.py` con 4 planes
- [ ] Crear `backend/services/credits_service.py`
- [ ] Crear `backend/models/credit_transaction.py`
- [ ] Crear excepción `InsufficientCreditsError`
- [ ] Tests unitarios de CreditsService

### Fase 3: Integración
- [ ] Integrar en `POST /api/rfx/process`
- [ ] Integrar en chat agent
- [ ] Integrar en generación de propuestas
- [ ] Tests de integración

### Fase 4: API Endpoints
- [ ] Endpoint `GET /api/credits/info`
- [ ] Endpoint `GET /api/credits/history`
- [ ] Endpoint `GET /api/plans/available`
- [ ] Documentación de API

### Fase 5: Cron & Automation
- [ ] Script `credits_reset.py`
- [ ] Configurar cron job
- [ ] Notificaciones de créditos bajos
- [ ] Tests de reset

---

## 🎯 PRÓXIMO PASO INMEDIATO

**Comenzar con Fase 1: Migración de Base de Datos**

¿Quieres que proceda a crear las migraciones con el MCP server?

**Orden sugerido:**
1. Crear migraciones SQL
2. Ejecutar con MCP server
3. Verificar columnas creadas
4. Inicializar Sabra Corp
5. Continuar con Fase 2

---

**Última actualización:** 8 de Diciembre, 2025  
**Status:** ✅ ANÁLISIS COMPLETO - LISTO PARA IMPLEMENTAR  
**Enfoque:** KISS - Híbrido (Planes hardcoded + Créditos en BD)
