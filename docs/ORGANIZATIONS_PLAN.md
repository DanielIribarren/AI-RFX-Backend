# 📄 RESUMEN EJECUTIVO - ORGANIZACIONES V3

## ✅ LISTO PARA IMPLEMENTAR

**Documento completo:** `ORGANIZACIONES_FINAL_V3.md`

---

## 🎯 Decisiones Finales Implementadas

### 1. **Normalización Real**
```sql
users
├─ is_in_organization (BOOLEAN) ← Solo flag de búsqueda
└─ NO tiene current_organization_id (elimina redundancia)

organization_members (PIVOT)
├─ user_id FK
├─ organization_id FK
└─ Source of truth única
```

### 2. **Plan Personal: CANCELAR (Opción B)**
```
Usuario se une a org:
├─ Stripe: subscription.cancel() ✅
├─ Plan personal: downgrade a "free"
├─ Créditos personales: 100
└─ Usa: créditos de la organización

Usuario sale de org:
├─ Plan personal: sigue "free"
├─ Debe suscribirse manualmente si quiere plan pago
└─ Sin auto-reactivación
```

### 3. **Sin Fallback de Créditos**
```python
if organization.credits_remaining < cost:
    raise Error("Contact organization owner")
    # NO usar créditos personales ❌
```

---

## 📊 Tablas Creadas

| Tabla | Propósito | Registros Típicos |
|-------|-----------|-------------------|
| `organizations` | Orgs con plan y créditos compartidos | 100-1000 |
| `organization_members` | Pivot normalizada (many-to-many) | 500-5000 |
| `organization_invitations` | Invitaciones con token | 200-1000 |

**Actualizadas:**
- `users` (+`is_in_organization`)
- `rfx_v2` (+`organization_id`)
- `credit_transactions` (+`organization_id`)

---

## 🔧 Servicios Principales

```python
# Core functions
get_user_active_organization(user_id)
  → Consulta pivot, retorna Organization | None

get_effective_plan(user)
  → Retorna plan activo (personal u org)

consume_credits(user, cost)
  → Consume de plan efectivo
  → Sin fallback si insufficient

# Lifecycle
join_organization(user, org)
  → Cancela plan personal en Stripe
  → Downgrade a free
  → Crea membership

leave_organization(user, org)
  → Remueve membership
  → Se queda en free

create_organization(owner, ...)
  → Cancela plan personal owner
  → Crea org con Stripe propio
  → Owner se une como owner

invite_member(org, inviter, email)
  → Crea invitación con token
  → Envía email

accept_invitation(user, token)
  → Valida token
  → Llama join_organization()
```

---

## 🔌 Endpoints API (11 endpoints)

```
Organizaciones:
├─ POST   /api/organizations             (crear)
├─ GET    /api/organizations/<id>        (ver)
├─ GET    /api/organizations/my          (mi org)
└─ POST   /api/organizations/<id>/leave  (salir)

Miembros:
├─ GET    /api/organizations/<id>/members                (listar)
├─ POST   /api/organizations/<id>/invite                 (invitar)
└─ DELETE /api/organizations/<id>/members/<user_id>     (remover)

Invitaciones:
└─ POST   /api/invitations/accept/<token>  (aceptar)

Créditos:
└─ GET    /api/credits/info  (plan efectivo)
```

---

## 📋 Casos de Uso Documentados

1. **Usuario FREE se une a org** → Sin cambios, usa créditos de org
2. **Usuario PAGO ($49) se une a org** → Stripe cancela, downgrade a free
3. **Usuario sale de org** → Se queda en free, debe suscribirse si quiere pago
4. **Org sin créditos** → Error, owner debe recargar, NO fallback

---

## ✅ Checklist de Implementación

### Fase 1: BD (1-2 días)
- [ ] Ejecutar 6 migraciones SQL
- [ ] Verificar índices y triggers

### Fase 2: Backend Core (2-3 días)
- [ ] Implementar `organization_service.py` (9 funciones)
- [ ] Actualizar `credits_service.py`
- [ ] Actualizar modelos

### Fase 3: API (2-3 días)
- [ ] Implementar 11 endpoints
- [ ] Manejo de errores
- [ ] Permisos por roles

### Fase 4: Testing (3-4 días)
- [ ] Unit tests (8 tests)
- [ ] Integration tests (4 flows)
- [ ] E2E tests (5 scenarios)

### Fase 5: Integraciones (2-3 días)
- [ ] Stripe webhooks
- [ ] Email templates
- [ ] Notificaciones

### Fase 6: Frontend (3-4 días)
- [ ] 4 páginas nuevas
- [ ] 5 componentes
- [ ] Actualizar header/sidebar

### Fase 7: Deploy (1-2 días)
- [ ] Staging tests
- [ ] Production deploy
- [ ] Monitoreo

**Total: 14-21 días (3-4 semanas)**

---

## 🎯 Key Points para Empezar

1. **Empezar con BD:** Ejecutar migraciones SQL primero
2. **Luego servicios:** `organization_service.py` es el core
3. **Testing continuo:** No esperar al final
4. **Branch:** `feature/organizations`

---

## 📊 Métricas de Éxito

- [ ] Usuarios pueden crear orgs
- [ ] Invitaciones funcionan
- [ ] Planes personales se cancelan correctamente
- [ ] Créditos de org se consumen bien
- [ ] Sin fallback a créditos personales
- [ ] Billing limpio (una suscripción a la vez)

---

## 🚨 Puntos Críticos

### ⚠️ CRÍTICO 1: Normalización
```python
# ❌ NUNCA hacer:
org_id = user.current_organization_id

# ✅ SIEMPRE hacer:
org = get_user_active_organization(user.id)
```

### ⚠️ CRÍTICO 2: Cancelación Stripe
```python
# Al unirse a org:
if user.personal_plan_tier != 'free':
    stripe.Subscription.cancel(user.stripe_subscription_id)
    user.personal_plan_tier = 'free'
    user.stripe_subscription_id = None
```

### ⚠️ CRÍTICO 3: Sin Fallback
```python
# Si org sin créditos:
if org.credits_remaining < cost:
    raise InsufficientCreditsError()
    # NO usar user.credits ❌
```

---

## 📚 Archivos de Referencia

- **Documento completo:** `ORGANIZACIONES_FINAL_V3.md` (1300+ líneas)
- **Schema SQL:** Sección "Migraciones SQL" (6 tablas)
- **Servicios Python:** Sección "Servicios Backend" (código completo)
- **API Endpoints:** Sección "Endpoints API" (código completo)
- **Casos de uso:** Sección "Casos de Uso" (4 escenarios detallados)

---

## 🎯 Siguiente Paso

**¿Listo para empezar?**

1. Revisar documento completo
2. Crear branch `feature/organizations`
3. Empezar con Fase 1 (migraciones BD)

**Pregunta:** ¿Alguna duda o ajuste antes de empezar la implementación?