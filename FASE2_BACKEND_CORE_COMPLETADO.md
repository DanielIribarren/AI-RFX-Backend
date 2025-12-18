# ✅ FASE 2: BACKEND CORE COMPLETADO
## Sistema de Créditos - Implementación Backend

**Fecha:** 9 de Diciembre, 2025  
**Status:** ✅ COMPLETADO  
**Tiempo Total:** ~15 minutos

---

## 📊 RESUMEN EJECUTIVO

### ✅ Todas las Implementaciones Exitosas

| Componente | Archivo | Status | Líneas |
|------------|---------|--------|--------|
| Plans v2.1 | `backend/core/plans.py` | ✅ | 376 líneas |
| Credits Service | `backend/services/credits_service.py` | ✅ | 450 líneas |
| Database Methods | `backend/core/database.py` | ✅ | +156 líneas |
| Exceptions | `backend/exceptions.py` | ✅ | 150 líneas |

---

## 🎯 CAMBIOS IMPLEMENTADOS

### 1. `backend/core/plans.py` - Modelo Granular v2.1

**Versión:** 2.1 - Modelo Granular de Créditos

#### **A. Constantes de Costos**

```python
CREDIT_COSTS = {
    'extraction': 5,        # Extraer datos de documento
    'generation': 5,        # Generar propuesta inicial
    'complete': 10,         # Proceso completo (extracción + generación)
    'chat_message': 1,      # Mensaje de chat para actualizar RFX
    'regeneration': 5       # Regenerar propuesta
}
```

#### **B. Regeneraciones Gratuitas por Plan**

```python
FREE_REGENERATIONS = {
    'free': 1,              # 1 regeneración gratis
    'starter': 3,           # 3 regeneraciones gratis
    'pro': float('inf'),    # Regeneraciones ilimitadas
    'enterprise': float('inf')  # Regeneraciones ilimitadas
}
```

#### **C. Plan STARTER Agregado**

```python
'starter': SubscriptionPlan(
    tier='starter',
    name='Starter Plan',
    max_users=5,
    max_rfx_per_month=25,
    credits_per_month=250,  # ~25 RFX completos
    price_monthly_usd=29.0,
    free_regenerations=3,
    features=[
        'Up to 5 users',
        '250 credits per month (~25 RFX)',
        '3 free regenerations per proposal',
        'Advanced proposal generation',
        'Basic branding',
        'Priority email support'
    ]
)
```

#### **D. Planes Actualizados**

| Plan | Usuarios | RFX/mes | Créditos/mes | Precio | Regeneraciones |
|------|----------|---------|--------------|--------|----------------|
| FREE | 2 | 10 | 100 | $0 | 1 gratis |
| STARTER | 5 | 25 | 250 | $29 | 3 gratis |
| PRO | 50 | 500 | 1500 | $99 | Ilimitadas |
| ENTERPRISE | ∞ | ∞ | ∞ | $499 | Ilimitadas |

#### **E. Nuevas Funciones**

```python
get_operation_cost(operation)           # Obtener costo de operación
get_free_regenerations(tier)            # Obtener regeneraciones gratuitas
has_unlimited_regenerations(tier)       # Verificar si son ilimitadas
calculate_credits_needed(...)           # Calcular créditos necesarios
```

---

### 2. `backend/services/credits_service.py` - Servicio de Créditos

**Clase Principal:** `CreditsService`

#### **A. Verificación de Créditos**

```python
# Verificar disponibilidad
has_credits, available, msg = service.check_credits_available(
    organization_id=org_id,
    operation='extraction'
)

if not has_credits:
    raise InsufficientCreditsError(msg)
```

#### **B. Consumo de Créditos**

```python
# Consumir créditos y registrar transacción
result = service.consume_credits(
    organization_id=org_id,
    operation='extraction',
    rfx_id=rfx_id,
    user_id=user_id,
    description="Data extraction from PDF"
)
```

#### **C. Regeneraciones Gratuitas**

```python
# Verificar regeneración gratis disponible
has_free, used, msg = service.check_free_regeneration_available(
    organization_id=org_id,
    rfx_id=rfx_id
)

if has_free:
    service.use_free_regeneration(rfx_id)
else:
    # Consumir créditos
    service.consume_credits(org_id, 'regeneration', rfx_id=rfx_id)
```

#### **D. Información de Créditos**

```python
# Obtener info completa
info = service.get_credits_info(organization_id)
# {
#     "credits_total": 1500,
#     "credits_used": 250,
#     "credits_available": 1250,
#     "credits_percentage": 83.33,
#     "reset_date": "2026-01-09",
#     "plan_tier": "pro"
# }
```

#### **E. Historial de Transacciones**

```python
# Obtener historial
history = service.get_transaction_history(
    organization_id=org_id,
    limit=50,
    offset=0
)
```

#### **F. Reset Mensual (Cron Job)**

```python
# Llamar mensualmente desde cron job
result = service.reset_monthly_credits()
# Reset automático de créditos para todas las organizaciones
```

---

### 3. `backend/core/database.py` - Métodos para Processing Status

**Nuevos Métodos Agregados:**

#### **A. Obtener Estado**

```python
# Obtener estado de procesamiento
status = db.get_processing_status(rfx_id)

if status and status['has_extracted_data']:
    print("RFX ya tiene datos extraídos")
```

#### **B. Actualizar Estado**

```python
# Marcar extracción completada
db.upsert_processing_status(rfx_id, {
    "has_extracted_data": True,
    "extraction_completed_at": datetime.now().isoformat(),
    "extraction_credits_consumed": 5
})
```

#### **C. Regeneraciones**

```python
# Obtener contador
count = db.get_regeneration_count(rfx_id)

# Incrementar contador
db.increment_regeneration_count(rfx_id)
```

#### **D. Verificar Operación Completada**

```python
# Verificar si ya se extrajo
if db.is_operation_completed(rfx_id, 'extraction'):
    return {"error": "Already extracted"}

# Verificar si ya se generó
if db.is_operation_completed(rfx_id, 'generation'):
    return {"error": "Already generated"}
```

---

### 4. `backend/exceptions.py` - Excepciones Personalizadas

#### **A. InsufficientCreditsError**

```python
raise InsufficientCreditsError(
    "Insufficient credits for extraction",
    credits_required=5,
    credits_available=2,
    plan_tier="free"
)

# Respuesta JSON:
# {
#     "status": "error",
#     "error_type": "insufficient_credits",
#     "message": "Insufficient credits for extraction",
#     "credits_required": 5,
#     "credits_available": 2,
#     "plan_tier": "free",
#     "suggestion": "Consider upgrading your plan..."
# }
```

#### **B. PlanLimitExceededError**

```python
raise PlanLimitExceededError(
    "User limit reached for Free plan",
    limit_type="users",
    current_value=2,
    limit_value=2,
    plan_tier="free"
)
```

#### **C. ProcessingStatusError**

```python
raise ProcessingStatusError(
    "Cannot generate proposal: extraction not completed",
    rfx_id=rfx_id,
    required_status="extracted"
)
```

#### **D. Otras Excepciones**

- `OrganizationNotFoundError`
- `RFXNotFoundError`

---

## 🔗 INTEGRACIÓN EN ENDPOINTS (Guía)

### Ejemplo: Endpoint de Extracción

```python
from backend.services.credits_service import get_credits_service
from backend.exceptions import InsufficientCreditsError, ProcessingStatusError

@rfx_bp.route("/extract", methods=["POST"])
@jwt_required
def extract_rfx():
    """Extraer datos de documento RFX (5 créditos)"""
    try:
        rfx_id = request.json.get("rfx_id")
        organization_id = get_current_user_organization_id()
        user_id = get_current_user_id()
        
        # 1. Verificar si ya se extrajo
        db = get_database_client()
        if db.is_operation_completed(rfx_id, 'extraction'):
            return jsonify({
                "status": "error",
                "message": "Data already extracted for this RFX"
            }), 400
        
        # 2. Verificar créditos disponibles
        credits_service = get_credits_service()
        has_credits, available, msg = credits_service.check_credits_available(
            organization_id, 'extraction'
        )
        
        if not has_credits:
            raise InsufficientCreditsError(
                msg,
                credits_required=5,
                credits_available=available
            )
        
        # 3. Ejecutar extracción
        extracted_data = extraction_service.extract(rfx_id)
        
        # 4. Consumir créditos
        credits_service.consume_credits(
            organization_id=organization_id,
            operation='extraction',
            rfx_id=rfx_id,
            user_id=user_id
        )
        
        # 5. Actualizar estado de procesamiento
        db.upsert_processing_status(rfx_id, {
            "has_extracted_data": True,
            "extraction_completed_at": datetime.now().isoformat(),
            "extraction_credits_consumed": 5
        })
        
        return jsonify({
            "status": "success",
            "data": extracted_data,
            "credits_consumed": 5,
            "credits_remaining": available - 5
        }), 200
    
    except InsufficientCreditsError as e:
        return jsonify(e.to_dict()), e.status_code
    
    except Exception as e:
        logger.error(f"Error in extraction: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
```

### Ejemplo: Endpoint de Generación con Regeneraciones

```python
@rfx_bp.route("/<rfx_id>/generate-proposal", methods=["POST"])
@jwt_required
def generate_proposal(rfx_id):
    """Generar propuesta (5 créditos o gratis si hay regeneraciones)"""
    try:
        organization_id = get_current_user_organization_id()
        user_id = get_current_user_id()
        is_regeneration = request.json.get("is_regeneration", False)
        
        db = get_database_client()
        credits_service = get_credits_service()
        
        # 1. Verificar que se extrajo primero
        if not db.is_operation_completed(rfx_id, 'extraction'):
            raise ProcessingStatusError(
                "Cannot generate proposal: extraction not completed",
                rfx_id=rfx_id,
                required_status="extracted"
            )
        
        # 2. Si es regeneración, verificar si es gratis
        credits_to_consume = 0
        
        if is_regeneration:
            has_free, used, msg = credits_service.check_free_regeneration_available(
                organization_id, rfx_id
            )
            
            if has_free:
                # Regeneración gratis
                credits_service.use_free_regeneration(rfx_id)
                logger.info(f"✅ Using free regeneration for RFX {rfx_id}")
            else:
                # Consumir créditos
                credits_to_consume = 5
        else:
            # Primera generación
            credits_to_consume = 5
        
        # 3. Verificar créditos si es necesario
        if credits_to_consume > 0:
            has_credits, available, msg = credits_service.check_credits_available(
                organization_id, 'generation'
            )
            
            if not has_credits:
                raise InsufficientCreditsError(
                    msg,
                    credits_required=credits_to_consume,
                    credits_available=available
                )
        
        # 4. Generar propuesta
        proposal = proposal_service.generate(rfx_id)
        
        # 5. Consumir créditos si es necesario
        if credits_to_consume > 0:
            credits_service.consume_credits(
                organization_id=organization_id,
                operation='generation',
                rfx_id=rfx_id,
                user_id=user_id
            )
        
        # 6. Actualizar estado
        if is_regeneration:
            db.increment_regeneration_count(rfx_id)
        else:
            db.upsert_processing_status(rfx_id, {
                "has_generated_proposal": True,
                "generation_completed_at": datetime.now().isoformat(),
                "generation_credits_consumed": credits_to_consume
            })
        
        return jsonify({
            "status": "success",
            "proposal": proposal,
            "credits_consumed": credits_to_consume,
            "was_free": credits_to_consume == 0
        }), 200
    
    except (InsufficientCreditsError, ProcessingStatusError) as e:
        return jsonify(e.to_dict()), e.status_code
    
    except Exception as e:
        logger.error(f"Error generating proposal: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
```

---

## 🎯 FLUJOS COMPLETOS

### Flujo 1: Proceso Completo (Extracción + Generación)

```
1. Usuario sube documento
2. POST /api/rfx/process
   ├─ Verificar créditos (10 créditos)
   ├─ Extraer datos (5 créditos)
   ├─ Generar propuesta (5 créditos)
   ├─ Consumir 10 créditos total
   └─ Actualizar processing_status
3. Respuesta con propuesta generada
```

### Flujo 2: Regeneración con Créditos Gratis

```
1. Usuario regenera propuesta (1ra vez)
2. POST /api/rfx/{id}/generate-proposal (is_regeneration=true)
   ├─ Verificar regeneraciones gratuitas
   ├─ Plan FREE: 1 gratis disponible ✅
   ├─ Regenerar propuesta (0 créditos)
   ├─ Marcar regeneración gratis usada
   └─ Incrementar regeneration_count
3. Respuesta con nueva propuesta (gratis)
```

### Flujo 3: Regeneración con Consumo de Créditos

```
1. Usuario regenera propuesta (2da vez en plan FREE)
2. POST /api/rfx/{id}/generate-proposal (is_regeneration=true)
   ├─ Verificar regeneraciones gratuitas
   ├─ Plan FREE: 0 gratis disponibles ❌
   ├─ Verificar créditos (5 créditos)
   ├─ Regenerar propuesta (5 créditos)
   ├─ Consumir 5 créditos
   └─ Incrementar regeneration_count
3. Respuesta con nueva propuesta (5 créditos consumidos)
```

---

## 📋 CHECKLIST DE INTEGRACIÓN

### Backend

- [x] **Fase 1:** Migraciones de base de datos
- [x] **Fase 2A:** Plans v2.1 con modelo granular
- [x] **Fase 2B:** Credits Service implementado
- [x] **Fase 2C:** Database methods para processing_status
- [x] **Fase 2D:** Excepciones personalizadas
- [ ] **Fase 3A:** Integrar en endpoint `/api/rfx/extract`
- [ ] **Fase 3B:** Integrar en endpoint `/api/rfx/<id>/generate-proposal`
- [ ] **Fase 3C:** Integrar en endpoint `/api/rfx/process`
- [ ] **Fase 3D:** Crear endpoint `/api/credits/info`
- [ ] **Fase 3E:** Crear endpoint `/api/credits/history`
- [ ] **Fase 4:** Crear cron job para reset mensual
- [ ] **Fase 5:** Tests unitarios e integración

### Frontend

- [ ] Mostrar créditos disponibles en dashboard
- [ ] Indicador de créditos en cada operación
- [ ] Warning cuando créditos bajos
- [ ] Botón "Upgrade Plan" cuando sin créditos
- [ ] Historial de transacciones de créditos
- [ ] Indicador de regeneraciones gratuitas

---

## 🚀 PRÓXIMOS PASOS RECOMENDADOS

### Paso 1: Integrar en Endpoints Existentes (2-3 horas)

1. Modificar `/api/rfx/process` para consumir créditos
2. Modificar `/api/rfx/<id>/generate-proposal` para regeneraciones
3. Agregar verificación de créditos en operaciones

### Paso 2: Crear Endpoints de Créditos (1 hora)

1. `GET /api/credits/info` - Información de créditos
2. `GET /api/credits/history` - Historial de transacciones
3. `GET /api/credits/plans` - Planes disponibles

### Paso 3: Cron Job de Reset Mensual (30 min)

1. Crear script `scripts/reset_monthly_credits.py`
2. Configurar cron job en servidor
3. Testing de reset

### Paso 4: Frontend Integration (2-3 horas)

1. Hook `useCredits()` para obtener info
2. Componente `<CreditsIndicator />`
3. Modal de upgrade cuando sin créditos
4. Página de historial de créditos

---

## ✅ ESTADO ACTUAL

### ✅ COMPLETADO

- Base de datos normalizada con `rfx_processing_status`
- Sistema de créditos con modelo granular (5+5)
- Plan STARTER agregado
- Regeneraciones gratuitas por plan
- Servicio de créditos completo
- Métodos de database para processing_status
- Excepciones personalizadas

### ⏳ PENDIENTE

- Integración en endpoints API
- Cron job de reset mensual
- Tests unitarios
- Frontend integration

---

**Última Actualización:** 9 de Diciembre, 2025  
**Status:** ✅ FASE 2 COMPLETADA - BACKEND CORE LISTO  
**Próximo Paso:** Fase 3 - Integración en Endpoints API  
**Tiempo Estimado Fase 3:** 2-3 horas
