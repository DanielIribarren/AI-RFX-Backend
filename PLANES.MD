# 🚀 CHEAT SHEET - IMPLEMENTACIÓN DE PLANES
## Ready-to-Code Reference

**Arquitectura:** Híbrida (Planes hardcoded + Créditos en BD)  
**Filosofía:** KISS - Simple, mantenible, sin overengineering  
**Versión:** 2.1 - Modelo Granular (5+5)  
**Status:** ✅ Revisado y ajustado (9 Dic 2025)

> ⚠️ **CAMBIO IMPORTANTE:** Modelo granular implementado - Extracción (5 cr) + Generación (5 cr) = 10 cr total

> 📋 **Análisis Completo:** Ver [PLANES_ANALISIS_IMPLEMENTACION.md](./PLANES_ANALISIS_IMPLEMENTACION.md)

---

## 🎯 ARQUITECTURA HÍBRIDA (RECOMENDADA)

### ✅ Por Qué Híbrido?

**Planes Hardcoded:**
- ✅ Fácil de modificar (cambiar código, deploy)
- ✅ No requiere admin UI complejo
- ✅ Simple de testear
- ✅ Menos queries a BD

**Créditos en BD:**
- ✅ Tracking real-time preciso
- ✅ Historial de transacciones
- ✅ Auditoría completa
- ✅ No se pierden datos

**Resultado:** Lo mejor de ambos mundos sin complejidad innecesaria.

---

## 📊 CONSTANTES DE PLANES

```python
# backend/core/plans.py

from enum import Enum

class PlanTier(str, Enum):
    FREE = "free"
    STARTER = "starter"
    PRO = "pro"
    ENTERPRISE = "enterprise"

# Créditos por plan
PLAN_CREDITS = {
    PlanTier.FREE: 100,
    PlanTier.STARTER: 500,
    PlanTier.PRO: 1500,
    PlanTier.ENTERPRISE: 5000,
}

# Precio por plan (USD cents)
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

# Costos de operaciones (en créditos) - MODELO GRANULAR
CREDIT_COSTS = {
    # Operaciones separadas (modelo granular)
    "rfx_extract": 5,           # Extraer datos del documento (~$0.03 costo IA)
    "proposal_generate": 5,     # Generar presupuesto (~$0.04 costo IA)
    
    # Operación completa (wrapper de ambas)
    "rfx_process_complete": 10, # Extracción + Generación
    
    # Chat
    "chat_message": 1,          # Mensaje en chat agent (~$0.005 costo IA)
}

# Regeneraciones gratis por plan
FREE_REGENERATIONS = {
    PlanTier.FREE: 1,
    PlanTier.STARTER: 3,
    PlanTier.PRO: float('inf'),      # Ilimitado
    PlanTier.ENTERPRISE: float('inf'), # Ilimitado
}

# Features por plan (para display)
PLAN_FEATURES = {
    PlanTier.FREE: [
        "1 usuario",
        "100 créditos/mes (~10 RFX completos)",
        "Extracción: 5 créditos",
        "Generación: 5 créditos",
        "1 regeneración gratis",
        "Chat agent básico",
        "Soporte por email"
    ],
    PlanTier.STARTER: [
        "2 usuarios",
        "500 créditos/mes (~50 RFX completos)",
        "Extracción: 5 créditos",
        "Generación: 5 créditos",
        "3 regeneraciones gratis por RFX",
        "Chat agent ilimitado",
        "Branding personalizado",
        "Soporte prioritario"
    ],
    PlanTier.PRO: [
        "5 usuarios",
        "1500 créditos/mes (~150 RFX completos)",
        "Extracción: 5 créditos",
        "Generación: 5 créditos",
        "Regeneraciones ilimitadas GRATIS",
        "Todo de Starter +",
        "Analytics avanzados",
        "API access",
        "Integraciones custom"
    ],
    PlanTier.ENTERPRISE: [
        "Usuarios ilimitados",
        "5000+ créditos/mes (~500+ RFX completos)",
        "Extracción: 5 créditos",
        "Generación: 5 créditos",
        "Regeneraciones ilimitadas GRATIS",
        "Todo de Pro +",
        "Soporte 24/7",
        "SLA garantizado",
        "Account manager dedicado",
        "White-label"
    ]
}
```

---

## 🗄️ SQL - MIGRACIONES

### 📊 Estado Actual de la BD

**Tabla `organizations`:**
- ✅ Ya existe: `plan_tier`, `max_users`, `max_rfx_per_month`
- ❌ Falta: `credits_total`, `credits_used`, `credits_reset_date`

**Tabla `users`:**
- ✅ Ya existe: `organization_id`, `role`
- ❌ Falta: `personal_plan_tier`, `credits_total`, `credits_used`, `credits_reset_date`

**Tabla `credit_transactions`:**
- ❌ No existe (crear completa)

---

### 🔧 Migraciones Necesarias

```sql
-- =====================================================
-- USERS TABLE - Agregar columnas de planes personales
-- =====================================================
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

-- =====================================================
-- ORGANIZATIONS TABLE - Agregar columnas de créditos
-- NOTA: plan_tier, max_users, max_rfx_per_month YA EXISTEN
-- =====================================================
-- NO MODIFICAR plan_tier (ya existe con default 'free')
-- Solo agregar columnas de créditos:
    
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

-- =====================================================
-- CREDIT TRANSACTIONS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS credit_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    
    amount INTEGER NOT NULL,
    type VARCHAR(50) NOT NULL,  -- rfx_extract, proposal_generate, rfx_process_complete, chat_message, monthly_reset
    description TEXT,
    metadata JSONB,
    
    rfx_id UUID REFERENCES rfx_v2(id) ON DELETE SET NULL,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CHECK (amount != 0),
    CHECK (user_id IS NOT NULL OR organization_id IS NOT NULL)
);

-- =====================================================
-- RFX_PROCESSING_STATUS - Estado de procesamiento (NORMALIZADO)
-- =====================================================
-- ✅ DISEÑO CORRECTO: Separación de concerns
-- ✅ rfx_v2: Solo datos de negocio
-- ✅ rfx_processing_status: Solo estado de procesamiento
-- ✅ Escalable: Agregar operaciones = nuevos campos, no ALTER TABLE rfx_v2

CREATE TABLE IF NOT EXISTS rfx_processing_status (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rfx_id UUID NOT NULL REFERENCES rfx_v2(id) ON DELETE CASCADE,
    
    -- Estados de extracción
    has_extracted_data BOOLEAN DEFAULT FALSE,
    extraction_completed_at TIMESTAMPTZ,
    extraction_credits_consumed INTEGER DEFAULT 0,
    
    -- Estados de generación
    has_generated_proposal BOOLEAN DEFAULT FALSE,
    generation_completed_at TIMESTAMPTZ,
    generation_credits_consumed INTEGER DEFAULT 0,
    
    -- Regeneraciones
    regeneration_count INTEGER DEFAULT 0,
    last_regeneration_at TIMESTAMPTZ,
    free_regenerations_used INTEGER DEFAULT 0,
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    UNIQUE(rfx_id),  -- Un solo registro de estado por RFX
    CHECK (regeneration_count >= 0),
    CHECK (extraction_credits_consumed >= 0),
    CHECK (generation_credits_consumed >= 0)
);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_rfx_processing_rfx_id 
    ON rfx_processing_status(rfx_id);
    
CREATE INDEX IF NOT EXISTS idx_rfx_processing_extracted 
    ON rfx_processing_status(has_extracted_data);
    
CREATE INDEX IF NOT EXISTS idx_rfx_processing_generated 
    ON rfx_processing_status(has_generated_proposal);
    
CREATE INDEX IF NOT EXISTS idx_rfx_processing_updated 
    ON rfx_processing_status(updated_at DESC);

-- Trigger para actualizar updated_at automáticamente
CREATE OR REPLACE FUNCTION update_rfx_processing_status_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_rfx_processing_status_timestamp
    BEFORE UPDATE ON rfx_processing_status
    FOR EACH ROW
    EXECUTE FUNCTION update_rfx_processing_status_timestamp();

-- Índices para queries rápidas
CREATE INDEX IF NOT EXISTS idx_credit_trans_user 
    ON credit_transactions(user_id, created_at DESC);
    
CREATE INDEX IF NOT EXISTS idx_credit_trans_org 
    ON credit_transactions(organization_id, created_at DESC);
    
CREATE INDEX IF NOT EXISTS idx_credit_trans_type 
    ON credit_transactions(type);
    
CREATE INDEX IF NOT EXISTS idx_credit_trans_rfx 
    ON credit_transactions(rfx_id);
```

---

## 🔧 BACKEND - SERVICIO DE CRÉDITOS

### Ubicación: `backend/services/credits_service.py`

**Responsabilidad:** Gestionar créditos de usuarios y organizaciones (KISS)

```python
# backend/services/credits_service.py

from backend.core.plans import CREDIT_COSTS, PLAN_CREDITS, PlanTier
from backend.core.database import get_database_client
from backend.exceptions import InsufficientCreditsError
import logging

logger = logging.getLogger(__name__)

class CreditsService:
    """Servicio simple para gestión de créditos (KISS)"""
    
    def __init__(self):
        self.db = get_database_client()
    
    def get_credits_remaining(self, user_id: str, organization_id: str = None) -> int:
        """Obtiene créditos restantes del usuario u organización"""
        if organization_id:
            # Créditos de organización
            org = self.db.get_organization(organization_id)
            return org['credits_total'] - org['credits_used']
        else:
            # Créditos personales
            user = self.db.client.table('users').select('credits_total, credits_used').eq('id', user_id).single().execute()
            return user.data['credits_total'] - user.data['credits_used']
    
    def check_credits(self, user_id: str, cost: int, organization_id: str = None) -> bool:
        """Verifica si hay créditos suficientes"""
        remaining = self.get_credits_remaining(user_id, organization_id)
        return remaining >= cost
    
    def consume_credits(self, user_id: str, cost: int, type: str, organization_id: str = None, rfx_id: str = None):
        """Consume créditos y registra transacción"""
        # 1. Verificar créditos
        if not self.check_credits(user_id, cost, organization_id):
            remaining = self.get_credits_remaining(user_id, organization_id)
            raise InsufficientCreditsError(
                f"Need {cost} credits, have {remaining}"
            )
        
        # 2. Actualizar créditos
        if organization_id:
            # Créditos de organización
            self.db.client.table('organizations').update({
                'credits_used': self.db.client.table('organizations')
                    .select('credits_used')
                    .eq('id', organization_id)
                    .single()
                    .execute()
                    .data['credits_used'] + cost
            }).eq('id', organization_id).execute()
            
            # Log transaction
            self.db.client.table('credit_transactions').insert({
                'organization_id': organization_id,
                'amount': -cost,
                'type': type,
                'rfx_id': rfx_id,
                'description': f'{type} operation'
            }).execute()
        else:
            # Créditos personales
            self.db.client.table('users').update({
                'credits_used': self.db.client.table('users')
                    .select('credits_used')
                    .eq('id', user_id)
                    .single()
                    .execute()
                    .data['credits_used'] + cost
            }).eq('id', user_id).execute()
            
            # Log transaction
            self.db.client.table('credit_transactions').insert({
                'user_id': user_id,
                'amount': -cost,
                'type': type,
                'rfx_id': rfx_id,
                'description': f'{type} operation'
            }).execute()
        
        # 3. Log y notificación
        remaining = self.get_credits_remaining(user_id, organization_id)
        logger.info(f"✅ Consumed {cost} credits. Remaining: {remaining}")
        
        # TODO: Implementar notificación si quedan pocos créditos
```

---

## 🎯 INTEGRACIÓN EN RFX PROCESSING (MODELO GRANULAR)

### Ubicación: `backend/api/rfx.py`

**Patrón:** Verificar → Procesar → Consumir (solo si éxito)

---

### Opción 1: Extracción de Datos (5 créditos)

```python
@rfx_bp.route("/extract", methods=["POST"])
@jwt_required
def extract_rfx_data():
    """Extrae datos del documento RFX (5 créditos)"""
    
    user_id = get_current_user_id()
    organization_id = get_user_organization(user_id)
    
    # 1. Verificar créditos
    credits_service = CreditsService()
    cost = CREDIT_COSTS["rfx_extract"]  # 5 créditos
    
    if not credits_service.check_credits(user_id, cost, organization_id):
        remaining = credits_service.get_credits_remaining(user_id, organization_id)
        return jsonify({
            "status": "error",
            "error": "insufficient_credits",
            "message": f"Need {cost} credits, have {remaining}."
        }), 402
    
    # 2. Extraer datos
    try:
        extracted_data = extractor_service.extract_rfx_data(...)
        
        # Actualizar estado de procesamiento (tabla normalizada)
        db.upsert_processing_status(rfx_id, {
            "has_extracted_data": True,
            "extraction_completed_at": datetime.now(),
            "extraction_credits_consumed": cost
        })
        
        # 3. Consumir créditos
        credits_service.consume_credits(
            user_id=user_id,
            cost=cost,
            type="rfx_extract",
            organization_id=organization_id,
            rfx_id=rfx_id
        )
        
        return jsonify({
            "status": "success",
            "data": extracted_data,
            "credits_consumed": cost
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Extraction failed: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
```

---

### Opción 2: Generación de Presupuesto (5 créditos)

```python
@rfx_bp.route("/<rfx_id>/generate-proposal", methods=["POST"])
@jwt_required
def generate_proposal(rfx_id: str):
    """Genera presupuesto desde datos extraídos (5 créditos)"""
    
    user_id = get_current_user_id()
    organization_id = get_user_organization(user_id)
    
    # 0. Verificar que ya se extrajo (tabla normalizada)
    processing_status = db.get_processing_status(rfx_id)
    if not processing_status or not processing_status.get('has_extracted_data'):
        return jsonify({
            "status": "error",
            "message": "Must extract data first"
        }), 400
    
    # 1. Verificar si es regeneración gratis
    regeneration_count = processing_status.get('regeneration_count', 0)
    user_plan = get_user_plan(user_id, organization_id)
    free_regens = FREE_REGENERATIONS[user_plan]
    
    is_free_regen = (
        processing_status.get('has_generated_proposal') and 
        regeneration_count < free_regens
    )
    
    cost = 0 if is_free_regen else CREDIT_COSTS["proposal_generate"]  # 0 o 5
    
    # 2. Verificar créditos (si no es gratis)
    if cost > 0:
        credits_service = CreditsService()
        if not credits_service.check_credits(user_id, cost, organization_id):
            remaining = credits_service.get_credits_remaining(user_id, organization_id)
            return jsonify({
                "status": "error",
                "error": "insufficient_credits",
                "message": f"Need {cost} credits, have {remaining}."
            }), 402
    
    # 3. Generar presupuesto
    try:
        proposal = proposal_service.generate_proposal(rfx_id)
        
        # Actualizar estado de procesamiento (tabla normalizada)
        db.upsert_processing_status(rfx_id, {
            "has_generated_proposal": True,
            "generation_completed_at": datetime.now(),
            "generation_credits_consumed": cost,
            "regeneration_count": regeneration_count + 1,
            "last_regeneration_at": datetime.now() if is_free_regen else None,
            "free_regenerations_used": processing_status.get('free_regenerations_used', 0) + (1 if is_free_regen else 0)
        })
        
        # 4. Consumir créditos (si no es gratis)
        if cost > 0:
            credits_service.consume_credits(
                user_id=user_id,
                cost=cost,
                type="proposal_generate",
                organization_id=organization_id,
                rfx_id=rfx_id
            )
        
        return jsonify({
            "status": "success",
            "data": proposal,
            "credits_consumed": cost,
            "was_free_regeneration": is_free_regen,
            "regenerations_remaining": max(0, free_regens - regeneration_count - 1)
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Generation failed: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
```

---

### Opción 3: Proceso Completo (10 créditos)

```python
@rfx_bp.route("/process-complete", methods=["POST"])
@jwt_required
def process_rfx_complete():
    """Extrae datos Y genera presupuesto (10 créditos total)"""
    
    user_id = get_current_user_id()
    organization_id = get_user_organization(user_id)
    
    # 1. Verificar créditos para TODO
    credits_service = CreditsService()
    cost = CREDIT_COSTS["rfx_process_complete"]  # 10 créditos
    
    if not credits_service.check_credits(user_id, cost, organization_id):
        remaining = credits_service.get_credits_remaining(user_id, organization_id)
        return jsonify({
            "status": "error",
            "error": "insufficient_credits",
            "message": f"Need {cost} credits, have {remaining}."
        }), 402
    
    # 2. Procesar completo (extracción + generación)
    try:
        # Extracción
        extracted_data = extractor_service.extract_rfx_data(...)
        
        # Generación
        proposal = proposal_service.generate_proposal(rfx_id)
        
        # Actualizar estado completo (tabla normalizada)
        db.upsert_processing_status(rfx_id, {
            "has_extracted_data": True,
            "extraction_completed_at": datetime.now(),
            "extraction_credits_consumed": 5,
            "has_generated_proposal": True,
            "generation_completed_at": datetime.now(),
            "generation_credits_consumed": 5,
            "regeneration_count": 1
        })
        
        # 3. Consumir créditos (una sola transacción)
        credits_service.consume_credits(
            user_id=user_id,
            cost=cost,
            type="rfx_process_complete",
            organization_id=organization_id,
            rfx_id=rfx_id
        )
        
        return jsonify({
            "status": "success",
            "data": {
                "extracted_data": extracted_data,
                "proposal": proposal
            },
            "credits_consumed": cost,
            "breakdown": {
                "extraction": 5,
                "generation": 5
            }
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Complete processing failed: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
```

---

## 💬 INTEGRACIÓN EN CHAT

### Ubicación: `backend/api/rfx_chat.py` (endpoint `/chat`)

**Patrón:** Mismo que RFX - Verificar → Procesar → Consumir

```python
# En backend/api/rfx_chat.py

from backend.services.credits_service import CreditsService
from backend.core.plans import CREDIT_COSTS

def send_chat_message(message: str, user):
    """Envía mensaje de chat consumiendo créditos"""
    
    # 1. Verificar créditos
    cost = CREDIT_COSTS["chat_message"]  # 1 crédito
    
    if not CreditsService.check_credits(user, cost):
        raise InsufficientCreditsError(
            f"Insufficient credits for chat. Need {cost}, "
            f"have {CreditsService.get_credits_remaining(user)}."
        )
    
    # 2. Procesar mensaje
    try:
        response = ai_chat_completion(message)
        
        # 3. Consumir crédito
        CreditsService.consume_credits(
            user=user,
            cost=cost,
            type="chat_message"
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Chat failed: {e}")
        raise
```

---

## 🌐 ENDPOINTS API

```python
# backend/api/credits.py

from flask import Blueprint, jsonify
from backend.services.credits_service import CreditsService
from backend.auth import require_auth

credits_bp = Blueprint('credits', __name__)

@credits_bp.route('/api/credits/info', methods=['GET'])
@require_auth
def get_credits_info(current_user):
    """GET /api/credits/info - Info de créditos"""
    
    if current_user.is_in_organization:
        org = get_organization(current_user.current_organization_id)
        data = {
            "plan_tier": org.plan_tier,
            "credits_total": org.credits_total,
            "credits_used": org.credits_used,
            "credits_remaining": org.credits_total - org.credits_used,
            "reset_date": org.credits_reset_date.isoformat(),
            "billing_type": "organization"
        }
    else:
        data = {
            "plan_tier": current_user.personal_plan_tier,
            "credits_total": current_user.credits_total,
            "credits_used": current_user.credits_used,
            "credits_remaining": current_user.credits_total - current_user.credits_used,
            "reset_date": current_user.credits_reset_date.isoformat(),
            "billing_type": "personal"
        }
    
    return jsonify({
        "status": "success",
        "data": data
    })

@credits_bp.route('/api/credits/history', methods=['GET'])
@require_auth
def get_credits_history(current_user):
    """GET /api/credits/history - Historial de transacciones"""
    
    if current_user.is_in_organization:
        org = get_organization(current_user.current_organization_id)
        transactions = CreditTransaction.query.filter_by(
            organization_id=org.id
        ).order_by(CreditTransaction.created_at.desc()).limit(100).all()
    else:
        transactions = CreditTransaction.query.filter_by(
            user_id=current_user.id
        ).order_by(CreditTransaction.created_at.desc()).limit(100).all()
    
    return jsonify({
        "status": "success",
        "data": [tx.to_dict() for tx in transactions]
    })
```

---

## ⚠️ EXCEPTION HANDLING

```python
# backend/exceptions.py

class InsufficientCreditsError(Exception):
    """Usuario no tiene créditos suficientes"""
    def __init__(self, message="Insufficient credits"):
        self.message = message
        self.status_code = 402  # Payment Required
        super().__init__(self.message)

# En tu error handler
@app.errorhandler(InsufficientCreditsError)
def handle_insufficient_credits(error):
    return jsonify({
        "status": "error",
        "error": "insufficient_credits",
        "message": error.message
    }), error.status_code
```

---

## 🔄 CRON JOB - RESET MENSUAL

```python
# backend/tasks/credits_reset.py

from datetime import datetime, timedelta
from backend.core.plans import PLAN_CREDITS, PlanTier

def reset_monthly_credits():
    """Resetea créditos cada mes (ejecutar diariamente)"""
    
    today = datetime.now()
    
    # Usuarios individuales
    users = User.query.filter(
        User.credits_reset_date <= today,
        User.is_in_organization == False
    ).all()
    
    for user in users:
        plan = PlanTier(user.personal_plan_tier)
        new_credits = PLAN_CREDITS[plan]
        
        user.credits_used = 0
        user.credits_total = new_credits
        user.credits_reset_date = today + timedelta(days=30)
        
        CreditTransaction.create(
            user_id=user.id,
            amount=new_credits,
            type="monthly_reset",
            description=f"Monthly credit reset: {new_credits} credits"
        )
    
    # Organizaciones
    orgs = Organization.query.filter(
        Organization.credits_reset_date <= today
    ).all()
    
    for org in orgs:
        plan = PlanTier(org.plan_tier)
        new_credits = PLAN_CREDITS[plan]
        
        org.credits_used = 0
        org.credits_total = new_credits
        org.credits_reset_date = today + timedelta(days=30)
        
        CreditTransaction.create(
            organization_id=org.id,
            amount=new_credits,
            type="monthly_reset",
            description=f"Monthly credit reset: {new_credits} credits"
        )
    
    db.session.commit()
    
    logger.info(f"✅ Credits reset: {len(users)} users, {len(orgs)} orgs")

# Configurar en cron o scheduler
# 0 0 * * * python -m backend.tasks.credits_reset
```

---

## 🎨 FRONTEND - HOOK DE CRÉDITOS

```typescript
// hooks/useCredits.ts

import { useState, useEffect } from 'react';

interface CreditsInfo {
  plan_tier: string;
  credits_total: number;
  credits_used: number;
  credits_remaining: number;
  reset_date: string;
  billing_type: string;
}

export function useCredits() {
  const [credits, setCredits] = useState<CreditsInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const fetchCredits = async () => {
    try {
      const response = await fetch('/api/credits/info');
      const data = await response.json();
      
      if (data.status === 'success') {
        setCredits(data.data);
      } else {
        setError('Failed to fetch credits');
      }
    } catch (err) {
      setError('Network error');
    } finally {
      setLoading(false);
    }
  };
  
  useEffect(() => {
    fetchCredits();
  }, []);
  
  const percentageUsed = credits 
    ? (credits.credits_used / credits.credits_total) * 100 
    : 0;
  
  const isLow = percentageUsed >= 80;
  const isCritical = percentageUsed >= 95;
  
  return {
    credits,
    loading,
    error,
    percentageUsed,
    isLow,
    isCritical,
    refresh: fetchCredits
  };
}
```

---

## 📱 FRONTEND - INDICADOR SIMPLE

```typescript
// components/CreditsIndicator.tsx

import { useCredits } from '@/hooks/useCredits';

export function CreditsIndicator() {
  const { credits, isLow, isCritical } = useCredits();
  
  if (!credits) return null;
  
  return (
    <div className={`flex items-center gap-2 px-3 py-1 rounded-full text-sm ${
      isCritical ? 'bg-red-100 text-red-700' :
      isLow ? 'bg-yellow-100 text-yellow-700' :
      'bg-blue-100 text-blue-700'
    }`}>
      <span className="font-medium">
        {credits.credits_remaining}
      </span>
      <span className="text-xs">credits</span>
      {isCritical && <span className="text-xs">🚨</span>}
      {isLow && !isCritical && <span className="text-xs">⚠️</span>}
    </div>
  );
}
```

---

## ✅ QUICK CHECKLIST

### 🎯 Fase 1: Base de Datos (MCP Server) - NORMALIZADA
- [ ] Migración: Agregar columnas a `users` table (créditos personales)
- [ ] Migración: Agregar columnas a `organizations` table (créditos organizacionales)
- [ ] Migración: Crear tabla `credit_transactions` (historial)
- [ ] Migración: Crear tabla `rfx_processing_status` (estado de procesamiento - NORMALIZADA ✅)
- [ ] Migración: Crear trigger `update_rfx_processing_status_timestamp`
- [ ] Verificar: Índices creados correctamente
- [ ] Verificar: Constraints y foreign keys
- [ ] Inicializar: Sabra Corp con plan PRO y créditos
- [ ] Inicializar: Estados de procesamiento para RFX existentes

### 🎯 Fase 2: Backend Core
- [ ] Actualizar `backend/core/plans.py` (4 planes + features + modelo granular)
- [ ] Agregar `FREE_REGENERATIONS` dict
- [ ] Actualizar `CREDIT_COSTS` con modelo granular (5+5)
- [ ] Crear `backend/services/credits_service.py`
- [ ] Agregar método `get_user_plan()` helper
- [ ] Crear `backend/exceptions.py` (InsufficientCreditsError)
- [ ] **Actualizar `backend/core/database.py` con métodos para `rfx_processing_status`:**
  - [ ] `get_processing_status(rfx_id)` - Obtener estado
  - [ ] `upsert_processing_status(rfx_id, data)` - Crear/actualizar estado
  - [ ] `get_regeneration_count(rfx_id)` - Helper para regeneraciones
  - [ ] `is_operation_completed(rfx_id, operation_type)` - Verificar si operación completada
- [ ] Tests: Unitarios de CreditsService
- [ ] Tests: Unitarios de métodos de processing_status

### 🎯 Fase 3: Integración Endpoints (Modelo Granular)
- [ ] Crear `POST /api/rfx/extract` (5 créditos)
- [ ] Crear `POST /api/rfx/<id>/generate-proposal` (5 créditos + regeneraciones gratis)
- [ ] Crear `POST /api/rfx/process-complete` (10 créditos - wrapper)
- [ ] Mantener endpoint legacy `/process` para compatibilidad
- [ ] Integrar en chat agent (`/api/rfx/<id>/chat`) (1 crédito)
- [ ] Tests: Cada operación separada
- [ ] Tests: Regeneraciones gratis por plan
- [ ] Tests: Proceso completo

### 🎯 Fase 4: API Endpoints
- [ ] Crear `backend/api/credits.py`
- [ ] Endpoint `GET /api/credits/info`
- [ ] Endpoint `GET /api/credits/history`
- [ ] Registrar blueprint en `app.py`
- [ ] Tests: Endpoints de créditos

### 🎯 Fase 5: Cron & Automation (Futuro)
- [ ] Script `backend/tasks/credits_reset.py`
- [ ] Configurar cron job diario
- [ ] Notificaciones de créditos bajos
- [ ] Tests: Reset mensual

### 🎯 Frontend (Opcional - Futuro)
- [ ] Hook `useCredits()`
- [ ] Componente `CreditsIndicator` (header)
- [ ] Alertas de créditos bajos
- [ ] Página `/plans` con comparación

### 🎯 Integración Pagos (Muy Futuro)
- [ ] Stripe products setup
- [ ] Webhook handlers
- [ ] E2E testing

---

## � DOCUMENTACIÓN RELACIONADA

- **[PLANES_ANALISIS_IMPLEMENTACION.md](./PLANES_ANALISIS_IMPLEMENTACION.md)** - Análisis completo del estado actual
- **[MULTI_TENANT_IMPLEMENTATION_PLAN.md](./MULTI_TENANT_IMPLEMENTATION_PLAN.md)** - Plan de multi-tenancy
- **[FASE2_IMPLEMENTACION_COMPLETA.md](./FASE2_IMPLEMENTACION_COMPLETA.md)** - Backend multi-tenant

---

## 🎯 PRINCIPIOS KISS APLICADOS

1. **Híbrido Simple:** Planes en código + Créditos en BD
2. **No Overengineering:** Sin tabla de planes, sin admin UI complejo
3. **Reutilizar:** Usar infraestructura multi-tenant existente
4. **Incremental:** Implementar por fases, no todo de golpe
5. **Testeable:** Cada fase se puede probar independientemente
6. **Granular pero Simple:** Operaciones separadas (5+5) pero con wrapper completo (10)
7. **Generoso con Regeneraciones:** Gratis en planes altos = mejor UX sin costo extra
8. **Normalización Correcta:** Separación de concerns - estado de procesamiento en tabla dedicada ✅
9. **Escalabilidad:** Agregar operaciones no requiere ALTER TABLE en tabla principal

---

**Última Actualización:** 9 de Diciembre, 2025  
**Versión:** 2.1 - Modelo Granular (5+5)  
**Status:** ✅ AJUSTADO CON MODELO GRANULAR  
**Próximo Paso:** Fase 1 - Migraciones de Base de Datos

---

## 💰 ANÁLISIS FINANCIERO (Modelo Granular)

### Costos Reales de IA
- **Extracción:** ~$0.0275 por operación
- **Generación:** ~$0.0413 por operación
- **RFX Completo:** ~$0.07 total
- **Chat:** ~$0.005 por mensaje

### Márgenes por Plan

| Plan | Precio | Créditos | RFX Completos | Costo IA | Margen | % |
|------|--------|----------|---------------|----------|--------|----|
| FREE | $0 | 100 | 10 | $0.70 | -$0.70 | - |
| STARTER | $49 | 500 | 50 | $3.50 | $45.50 | 93% |
| PRO | $99 | 1,500 | 150 | $10.50 | $88.50 | 89% |
| ENTERPRISE | $299+ | 5,000+ | 500+ | $35+ | $264+ | 88% |

### Casos de Uso Típicos

**Usuario STARTER (500 créditos):**
- 30 RFX completos (300 cr)
- 5 extracciones sin generar (25 cr)
- 10 regeneraciones (3 gratis, 7×5=35 cr)
- 140 chats (140 cr)
- **Total:** 500 créditos ✅
- **Costo real:** $3.19
- **Margen:** $45.81 (94%) ✅

**Usuario PRO (1,500 créditos):**
- 100 RFX completos (1,000 cr)
- 20 extracciones sin generar (100 cr)
- 50 regeneraciones (TODAS GRATIS)
- 400 chats (400 cr)
- **Total:** 1,500 créditos ✅
- **Costo real:** $9.50
- **Margen:** $89.50 (90%) ✅

### Beneficios del Modelo Granular

✅ **Transparencia:** Usuario ve exactamente qué consume  
✅ **Flexibilidad:** Solo extrae si no necesita presupuesto aún  
✅ **Generosidad:** Regeneraciones gratis en planes altos  
✅ **Márgenes:** Iguales o mejores que modelo simple  
✅ **Competitividad:** Diferenciador único vs competencia

---

## 🗄️ DISEÑO DE BASE DE DATOS NORMALIZADA

### Separación de Concerns (3NF)

```
┌─────────────────────────────────────────────────────────────┐
│                    DATOS DE NEGOCIO                          │
├─────────────────────────────────────────────────────────────┤
│ rfx_v2:                                                      │
│ ├─ id, title, description, status                           │
│ ├─ user_id, organization_id                                 │
│ ├─ created_at, updated_at                                   │
│ └─ ... (solo datos de negocio)                              │
└─────────────────────────────────────────────────────────────┘
                            ↓ 1:1
┌─────────────────────────────────────────────────────────────┐
│              ESTADO DE PROCESAMIENTO                         │
├─────────────────────────────────────────────────────────────┤
│ rfx_processing_status:                                       │
│ ├─ rfx_id (FK → rfx_v2.id)                                  │
│ ├─ has_extracted_data, extraction_completed_at              │
│ ├─ has_generated_proposal, generation_completed_at          │
│ ├─ regeneration_count, last_regeneration_at                 │
│ └─ extraction_credits_consumed, generation_credits_consumed │
└─────────────────────────────────────────────────────────────┘
                            ↓ 1:N
┌─────────────────────────────────────────────────────────────┐
│                HISTORIAL DE CRÉDITOS                         │
├─────────────────────────────────────────────────────────────┤
│ credit_transactions:                                         │
│ ├─ rfx_id (FK → rfx_v2.id)                                  │
│ ├─ user_id, organization_id                                 │
│ ├─ amount, type, description                                │
│ └─ created_at                                                │
└─────────────────────────────────────────────────────────────┘
```

### Beneficios de la Normalización

#### ✅ Separación de Concerns
- **rfx_v2:** Solo datos de negocio del RFX
- **rfx_processing_status:** Solo estado de procesamiento
- **credit_transactions:** Solo historial de créditos

#### ✅ Escalabilidad
- Agregar nuevo tipo de operación = nuevos campos en `rfx_processing_status`
- NO requiere ALTER TABLE en `rfx_v2` (tabla principal)
- Fácil agregar metadata por operación

#### ✅ Performance
```sql
-- Query de negocio (tabla principal, sin contaminación)
SELECT * FROM rfx_v2 WHERE organization_id = ?;

-- Query de estado (tabla pequeña, especializada)
SELECT * FROM rfx_processing_status WHERE rfx_id = ?;

-- Query de auditoría (tabla de eventos)
SELECT * FROM credit_transactions WHERE rfx_id = ? ORDER BY created_at DESC;
```

#### ✅ Auditoría Mejorada
- Timestamps específicos por operación
- Créditos consumidos por operación
- Historial completo de regeneraciones
- Trigger automático para `updated_at`

### Queries Comunes

```sql
-- ¿Ya se extrajo?
SELECT has_extracted_data 
FROM rfx_processing_status 
WHERE rfx_id = ?;

-- ¿Cuántas regeneraciones gratis quedan?
SELECT 
    regeneration_count,
    free_regenerations_used
FROM rfx_processing_status 
WHERE rfx_id = ?;

-- Total de créditos consumidos en este RFX
SELECT 
    extraction_credits_consumed + generation_credits_consumed AS total_credits
FROM rfx_processing_status 
WHERE rfx_id = ?;

-- RFX sin procesar completamente
SELECT r.* 
FROM rfx_v2 r
LEFT JOIN rfx_processing_status ps ON r.id = ps.rfx_id
WHERE ps.has_generated_proposal = FALSE OR ps.id IS NULL;
```