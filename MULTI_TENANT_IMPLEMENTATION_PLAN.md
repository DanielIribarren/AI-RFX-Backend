# 📋 Plan de Implementación Multi-Tenant - Checklist Completo

**Fecha:** 5 de Diciembre, 2025  
**Objetivo:** Implementar multi-tenancy siguiendo principios KISS  
**Duración Estimada:** 5 días  
**Filosofía:** Cambios incrementales, testing continuo, backward compatible

---

## 🎯 FASE 0: PREPARACIÓN Y VALIDACIÓN

### Pre-requisitos (Día 0 - 2 horas)

- [ ] **Backup completo de base de datos**
  - [ ] Exportar schema actual: `pg_dump --schema-only`
  - [ ] Exportar datos: `pg_dump --data-only`
  - [ ] Guardar en: `/migration_backups/pre_multitenant_YYYYMMDD/`
  - [ ] Verificar que backup se puede restaurar

- [ ] **Crear branch de Git**
  - [ ] Crear branch: `git checkout -b feature/multi-tenant-implementation`
  - [ ] Push inicial: `git push -u origin feature/multi-tenant-implementation`

- [ ] **Validar entorno de desarrollo**
  - [ ] PostgreSQL corriendo localmente
  - [ ] Backend puede conectarse a DB
  - [ ] Tests actuales pasan: `pytest backend/tests/`
  - [ ] No hay migraciones pendientes

- [ ] **Documentar estado actual**
  - [ ] Contar usuarios actuales: `SELECT COUNT(*) FROM users;`
  - [ ] Contar RFX actuales: `SELECT COUNT(*) FROM rfx_v2;`
  - [ ] Listar tablas con user_id: Documentar en checklist

---

## 🗄️ FASE 1: CAMBIOS EN BASE DE DATOS

### 1.1 Crear Tabla Organizations (Día 1 - 1 hora)

- [ ] **Crear script SQL: `001_create_organizations_table.sql`**
  ```sql
  -- Script de creación
  BEGIN;
  
  CREATE TABLE organizations (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      name VARCHAR(255) NOT NULL,
      slug VARCHAR(100) UNIQUE NOT NULL,
      plan_tier VARCHAR(20) DEFAULT 'free' CHECK (plan_tier IN ('free', 'pro', 'enterprise')),
      max_users INTEGER DEFAULT 2,
      max_rfx_per_month INTEGER DEFAULT 10,
      is_active BOOLEAN DEFAULT true,
      trial_ends_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '14 days'),
      created_at TIMESTAMPTZ DEFAULT NOW(),
      updated_at TIMESTAMPTZ DEFAULT NOW()
  );
  
  CREATE INDEX idx_organizations_slug ON organizations(slug);
  CREATE INDEX idx_organizations_plan ON organizations(plan_tier);
  CREATE INDEX idx_organizations_active ON organizations(is_active) WHERE is_active = true;
  
  COMMENT ON TABLE organizations IS 'Organizaciones multi-tenant - cada empresa cliente';
  COMMENT ON COLUMN organizations.slug IS 'Identificador único URL-friendly (sabra-corp)';
  COMMENT ON COLUMN organizations.plan_tier IS 'Plan: free, pro, enterprise (hardcodeado)';
  
  COMMIT;
  ```

- [ ] **Ejecutar script en desarrollo**
  - [ ] Conectar a DB local
  - [ ] Ejecutar: `psql -d rfx_db -f 001_create_organizations_table.sql`
  - [ ] Verificar tabla creada: `\d organizations`
  - [ ] Verificar índices: `\di organizations*`

- [ ] **Validar creación**
  - [ ] Tabla existe: `SELECT * FROM organizations LIMIT 1;`
  - [ ] Constraints funcionan: Intentar insertar plan inválido (debe fallar)
  - [ ] Slug único funciona: Intentar duplicar slug (debe fallar)

### 1.2 Agregar Campos a Tablas Existentes (Día 1 - 1 hora)

- [ ] **Crear script SQL: `002_add_organization_fields.sql`**
  ```sql
  BEGIN;
  
  -- Agregar campos a users
  ALTER TABLE users ADD COLUMN organization_id UUID REFERENCES organizations(id);
  ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'member' CHECK (role IN ('owner', 'admin', 'member'));
  
  -- Agregar campo a rfx_v2
  ALTER TABLE rfx_v2 ADD COLUMN organization_id UUID REFERENCES organizations(id);
  
  -- Crear índices
  CREATE INDEX idx_users_organization ON users(organization_id);
  CREATE INDEX idx_users_role ON users(organization_id, role);
  CREATE INDEX idx_rfx_organization ON rfx_v2(organization_id);
  CREATE INDEX idx_rfx_org_created ON rfx_v2(organization_id, created_at DESC);
  
  -- Comentarios
  COMMENT ON COLUMN users.organization_id IS 'Organización a la que pertenece el usuario';
  COMMENT ON COLUMN users.role IS 'Rol en la organización: owner, admin, member';
  COMMENT ON COLUMN rfx_v2.organization_id IS 'Organización dueña del RFX (aislamiento de datos)';
  
  COMMIT;
  ```

- [ ] **Ejecutar script en desarrollo**
  - [ ] Ejecutar: `psql -d rfx_db -f 002_add_organization_fields.sql`
  - [ ] Verificar columnas agregadas: `\d users`, `\d rfx_v2`
  - [ ] Verificar índices: `\di users*`, `\di rfx_v2*`

- [ ] **Validar cambios**
  - [ ] Columnas existen y aceptan NULL (por ahora)
  - [ ] Foreign keys funcionan
  - [ ] Constraints de role funcionan

### 1.3 Migrar Datos Existentes (Día 1 - 2 horas)

- [ ] **Crear script SQL: `003_migrate_existing_data.sql`**
  ```sql
  BEGIN;
  
  -- 1. Crear organización por cada usuario existente
  INSERT INTO organizations (name, slug, plan_tier, max_users, max_rfx_per_month)
  SELECT 
      COALESCE(company_name, full_name || '''s Organization') as name,
      LOWER(REGEXP_REPLACE(COALESCE(company_name, full_name), '[^a-zA-Z0-9]', '-', 'g')) || '-' || SUBSTRING(id::text, 1, 8) as slug,
      'free' as plan_tier,
      2 as max_users,
      10 as max_rfx_per_month
  FROM users
  WHERE email_verified = true;  -- Solo usuarios verificados
  
  -- 2. Asignar usuarios a sus organizaciones
  UPDATE users u
  SET 
      organization_id = o.id,
      role = 'owner'
  FROM organizations o
  WHERE o.slug LIKE '%' || SUBSTRING(u.id::text, 1, 8);
  
  -- 3. Asignar RFX a organizaciones (basado en user_id del creador)
  UPDATE rfx_v2 r
  SET organization_id = u.organization_id
  FROM users u
  WHERE r.user_id = u.id
  AND u.organization_id IS NOT NULL;
  
  -- 4. Verificar migración
  SELECT 
      'Organizations created' as metric,
      COUNT(*) as count
  FROM organizations
  UNION ALL
  SELECT 
      'Users with organization' as metric,
      COUNT(*) as count
  FROM users
  WHERE organization_id IS NOT NULL
  UNION ALL
  SELECT 
      'RFX with organization' as metric,
      COUNT(*) as count
  FROM rfx_v2
  WHERE organization_id IS NOT NULL;
  
  COMMIT;
  ```

- [ ] **Ejecutar script en desarrollo**
  - [ ] Ejecutar: `psql -d rfx_db -f 003_migrate_existing_data.sql`
  - [ ] Revisar output de verificación

- [ ] **Validar migración de datos**
  - [ ] Todos los usuarios tienen organization_id: `SELECT COUNT(*) FROM users WHERE organization_id IS NULL;` → debe ser 0
  - [ ] Todos los RFX tienen organization_id: `SELECT COUNT(*) FROM rfx_v2 WHERE organization_id IS NULL;` → debe ser 0
  - [ ] Cada organización tiene al menos 1 owner: `SELECT o.name, COUNT(u.id) FROM organizations o JOIN users u ON o.id = u.organization_id WHERE u.role = 'owner' GROUP BY o.name;`
  - [ ] No hay slugs duplicados: `SELECT slug, COUNT(*) FROM organizations GROUP BY slug HAVING COUNT(*) > 1;` → debe estar vacío

### 1.4 Hacer Campos Obligatorios (Día 1 - 30 min)

- [ ] **Crear script SQL: `004_make_fields_required.sql`**
  ```sql
  BEGIN;
  
  -- Hacer campos NOT NULL (después de migración)
  ALTER TABLE users ALTER COLUMN organization_id SET NOT NULL;
  ALTER TABLE rfx_v2 ALTER COLUMN organization_id SET NOT NULL;
  
  -- Agregar constraint para asegurar que owner existe
  CREATE OR REPLACE FUNCTION check_organization_has_owner()
  RETURNS TRIGGER AS $$
  BEGIN
      IF NOT EXISTS (
          SELECT 1 FROM users 
          WHERE organization_id = NEW.id 
          AND role = 'owner'
      ) THEN
          RAISE EXCEPTION 'Organization must have at least one owner';
      END IF;
      RETURN NEW;
  END;
  $$ LANGUAGE plpgsql;
  
  -- Trigger para validar owner (solo en updates/deletes de users)
  -- No aplicar en INSERT de organizations (chicken-egg problem)
  
  COMMIT;
  ```

- [ ] **Ejecutar script**
  - [ ] Ejecutar: `psql -d rfx_db -f 004_make_fields_required.sql`
  - [ ] Verificar constraints: `\d users`, `\d rfx_v2`

- [ ] **Validar constraints**
  - [ ] Intentar insertar user sin organization_id (debe fallar)
  - [ ] Intentar insertar rfx sin organization_id (debe fallar)

---

## 🐍 FASE 2: CAMBIOS EN BACKEND

### 2.1 Crear Middleware de Organización (Día 2 - 2 horas)

- [ ] **Crear archivo: `backend/utils/organization_middleware.py`**
  ```python
  """
  🏢 Organization Middleware - Multi-Tenancy Context
  Inyecta organization_id y role en el contexto de Flask
  """
  from functools import wraps
  from flask import g, jsonify
  import logging
  
  logger = logging.getLogger(__name__)
  
  def require_organization(f):
      """
      Decorator que inyecta organization_id en el contexto.
      Requiere que @jwt_required se ejecute primero.
      
      Usage:
          @app.route("/rfx")
          @jwt_required
          @require_organization
          def get_rfx_list():
              org_id = g.organization_id  # Disponible
              role = g.user_role          # Disponible
      """
      @wraps(f)
      def decorated(*args, **kwargs):
          # Usuario ya debe estar en g.current_user (del @jwt_required)
          user = getattr(g, 'current_user', None)
          
          if not user:
              return jsonify({
                  "error": "Authentication required",
                  "message": "Use @jwt_required before @require_organization"
              }), 401
          
          # Validar que usuario tiene organización
          org_id = user.get('organization_id')
          if not org_id:
              logger.error(f"User {user['id']} has no organization_id")
              return jsonify({
                  "error": "User not associated with organization",
                  "message": "Contact support to join an organization"
              }), 403
          
          # Inyectar en contexto
          g.organization_id = str(org_id)
          g.user_role = user.get('role', 'member')
          
          logger.debug(f"✅ Organization context: {g.organization_id}, role: {g.user_role}")
          
          return f(*args, **kwargs)
      
      return decorated
  
  def require_role(required_role: str):
      """
      Decorator que valida rol del usuario.
      
      Usage:
          @require_role('owner')
          def delete_organization():
              # Solo owners pueden ejecutar esto
      """
      def decorator(f):
          @wraps(f)
          def decorated(*args, **kwargs):
              user_role = getattr(g, 'user_role', 'member')
              
              role_hierarchy = {'owner': 3, 'admin': 2, 'member': 1}
              
              if role_hierarchy.get(user_role, 0) < role_hierarchy.get(required_role, 99):
                  return jsonify({
                      "error": "Insufficient permissions",
                      "required_role": required_role,
                      "your_role": user_role
                  }), 403
              
              return f(*args, **kwargs)
          
          return decorated
      return decorator
  
  logger.info("🏢 Organization Middleware initialized")
  ```

- [ ] **Testing del middleware**
  - [ ] Crear test: `backend/tests/test_organization_middleware.py`
  - [ ] Test: Usuario sin organization_id → 403
  - [ ] Test: Usuario con organization_id → contexto inyectado
  - [ ] Test: require_role('owner') con member → 403
  - [ ] Test: require_role('admin') con owner → OK
  - [ ] Ejecutar: `pytest backend/tests/test_organization_middleware.py -v`

### 2.2 Crear Helpers en DatabaseClient (Día 2 - 2 horas)

- [ ] **Modificar: `backend/core/database.py`**
  - [ ] Agregar método `filter_by_organization()`
  - [ ] Agregar método `get_organization()`
  - [ ] Agregar método `check_organization_limit()`
  - [ ] Modificar `get_rfx_by_id()` para aceptar `organization_id`
  - [ ] Modificar `get_rfx_history()` para filtrar por org

- [ ] **Código a agregar:**
  ```python
  # En class DatabaseClient:
  
  def filter_by_organization(self, table: str, org_id: str):
      """Helper para filtrar cualquier tabla por organization_id"""
      return self.client.table(table).select("*").eq("organization_id", org_id)
  
  def get_organization(self, org_id: str) -> Dict:
      """Obtener organización por ID"""
      try:
          response = self.client.table("organizations")\
              .select("*")\
              .eq("id", org_id)\
              .single()\
              .execute()
          return response.data
      except Exception as e:
          logger.error(f"❌ Error getting organization {org_id}: {e}")
          return None
  
  def check_organization_limit(self, org_id: str, limit_type: str) -> Dict:
      """
      Verificar límites de la organización.
      
      Args:
          org_id: ID de la organización
          limit_type: 'users' o 'rfx_monthly'
      
      Returns:
          {"allowed": bool, "current": int, "limit": int}
      """
      org = self.get_organization(org_id)
      if not org:
          return {"allowed": False, "current": 0, "limit": 0}
      
      if limit_type == 'users':
          current = self.client.table("users")\
              .select("id", count="exact")\
              .eq("organization_id", org_id)\
              .execute()\
              .count
          
          return {
              "allowed": current < org['max_users'],
              "current": current,
              "limit": org['max_users']
          }
      
      elif limit_type == 'rfx_monthly':
          from datetime import datetime
          first_day = datetime.now().replace(day=1, hour=0, minute=0, second=0)
          
          current = self.client.table("rfx_v2")\
              .select("id", count="exact")\
              .eq("organization_id", org_id)\
              .gte("created_at", first_day.isoformat())\
              .execute()\
              .count
          
          return {
              "allowed": current < org['max_rfx_per_month'],
              "current": current,
              "limit": org['max_rfx_per_month']
          }
      
      return {"allowed": False, "current": 0, "limit": 0}
  
  def get_rfx_by_id(self, rfx_id: str, organization_id: str = None):
      """
      Obtener RFX por ID (con filtro opcional de organización).
      
      Args:
          rfx_id: ID del RFX
          organization_id: Filtrar por organización (seguridad)
      """
      query = self.client.table("rfx_v2").select("*").eq("id", rfx_id)
      
      # Filtro de seguridad multi-tenant
      if organization_id:
          query = query.eq("organization_id", organization_id)
      
      return query.single().execute()
  ```

- [ ] **Testing de helpers**
  - [ ] Test: `filter_by_organization()` solo retorna datos de esa org
  - [ ] Test: `get_organization()` retorna datos correctos
  - [ ] Test: `check_organization_limit('users')` cuenta correctamente
  - [ ] Test: `check_organization_limit('rfx_monthly')` solo cuenta mes actual
  - [ ] Test: `get_rfx_by_id()` con org_id filtra correctamente
  - [ ] Ejecutar: `pytest backend/tests/test_database_client.py -v`

### 2.3 Crear Archivo de Planes (Día 2 - 30 min)

- [ ] **Crear archivo: `backend/core/plans.py`**
  ```python
  """
  💰 Subscription Plans - Hardcoded Configuration
  Define límites y features por plan (no DB)
  """
  
  PLANS = {
      'free': {
          'name': 'Free Trial',
          'max_users': 2,
          'max_rfx_per_month': 10,
          'max_storage_mb': 500,
          'features': {
              'ai_chat': True,
              'custom_branding': False,
              'analytics': False,
              'api_access': False,
              'priority_support': False
          },
          'price_monthly': 0,
          'price_yearly': 0
      },
      'pro': {
          'name': 'Professional',
          'max_users': 10,
          'max_rfx_per_month': 100,
          'max_storage_mb': 5000,
          'features': {
              'ai_chat': True,
              'custom_branding': True,
              'analytics': True,
              'api_access': False,
              'priority_support': False
          },
          'price_monthly': 49,
          'price_yearly': 470  # ~20% descuento
      },
      'enterprise': {
          'name': 'Enterprise',
          'max_users': 999,
          'max_rfx_per_month': 999,
          'max_storage_mb': 50000,
          'features': {
              'ai_chat': True,
              'custom_branding': True,
              'analytics': True,
              'api_access': True,
              'priority_support': True
          },
          'price_monthly': 199,
          'price_yearly': 1910  # ~20% descuento
      }
  }
  
  def get_plan_config(plan_tier: str) -> dict:
      """Obtener configuración de un plan"""
      return PLANS.get(plan_tier, PLANS['free'])
  
  def has_feature(plan_tier: str, feature: str) -> bool:
      """Verificar si plan tiene feature específico"""
      plan = get_plan_config(plan_tier)
      return plan['features'].get(feature, False)
  
  def get_all_plans() -> dict:
      """Obtener todos los planes (para pricing page)"""
      return PLANS
  ```

- [ ] **Testing de planes**
  - [ ] Test: `get_plan_config('free')` retorna config correcta
  - [ ] Test: `has_feature('pro', 'custom_branding')` → True
  - [ ] Test: `has_feature('free', 'api_access')` → False
  - [ ] Ejecutar: `pytest backend/tests/test_plans.py -v`

---

## 🔌 FASE 3: ACTUALIZAR ENDPOINTS

### 3.1 Actualizar Endpoints de RFX (Día 3 - 3 horas)

- [ ] **Modificar: `backend/api/rfx.py`**

#### Endpoint: GET /api/rfx (Listar RFX)

- [ ] Agregar decorators:
  ```python
  @rfx_bp.route("/", methods=["GET"])
  @jwt_required
  @require_organization  # ← NUEVO
  def get_rfx_list():
  ```

- [ ] Filtrar por organización:
  ```python
  # ANTES:
  rfx_list = db.get_rfx_history(limit=limit, offset=offset)
  
  # DESPUÉS:
  rfx_list = db.client.table("rfx_v2")\
      .select("*")\
      .eq("organization_id", g.organization_id)\  # ← NUEVO
      .order("created_at", desc=True)\
      .limit(limit)\
      .offset(offset)\
      .execute()
  ```

- [ ] Testing:
  - [ ] Test: Usuario Org A solo ve RFX de Org A
  - [ ] Test: Usuario Org B solo ve RFX de Org B
  - [ ] Test: Sin organization_id en contexto → 403

#### Endpoint: POST /api/rfx (Crear RFX)

- [ ] Agregar decorators:
  ```python
  @rfx_bp.route("/", methods=["POST"])
  @jwt_required
  @require_organization  # ← NUEVO
  def create_rfx():
  ```

- [ ] Validar límites:
  ```python
  # Verificar límite de RFX del mes
  limit_check = db.check_organization_limit(g.organization_id, 'rfx_monthly')
  
  if not limit_check['allowed']:
      return jsonify({
          "error": "Monthly RFX limit reached",
          "current": limit_check['current'],
          "limit": limit_check['limit'],
          "upgrade_url": "/pricing"
      }), 429
  ```

- [ ] Inyectar organization_id:
  ```python
  rfx_data = request.get_json()
  rfx_data['organization_id'] = g.organization_id  # ← NUEVO
  rfx_data['user_id'] = g.current_user['id']
  ```

- [ ] Testing:
  - [ ] Test: Crear RFX inyecta organization_id correctamente
  - [ ] Test: Exceder límite mensual → 429
  - [ ] Test: RFX creado solo visible para su organización

#### Endpoint: GET /api/rfx/{rfx_id}

- [ ] Agregar filtro de seguridad:
  ```python
  @rfx_bp.route("/<rfx_id>", methods=["GET"])
  @jwt_required
  @require_organization  # ← NUEVO
  def get_rfx_by_id(rfx_id):
      # Filtrar por organización (seguridad)
      rfx = db.get_rfx_by_id(rfx_id, organization_id=g.organization_id)  # ← NUEVO
      
      if not rfx:
          return jsonify({"error": "RFX not found or access denied"}), 404
  ```

- [ ] Testing:
  - [ ] Test: Usuario Org A intenta ver RFX de Org B → 404
  - [ ] Test: Usuario Org A ve su propio RFX → OK

### 3.2 Actualizar Endpoints de Branding (Día 3 - 2 horas)

- [ ] **Modificar: `backend/api/branding.py`**

- [ ] Agregar decorators a todos los endpoints:
  ```python
  @branding_bp.route("/<user_id>", methods=["GET"])
  @jwt_required
  @require_organization  # ← NUEVO
  def get_branding(user_id):
      # Validar que user_id pertenece a la organización
      user = db.client.table("users")\
          .select("id, organization_id")\
          .eq("id", user_id)\
          .eq("organization_id", g.organization_id)\  # ← NUEVO
          .single()\
          .execute()
      
      if not user.data:
          return jsonify({"error": "Access denied"}), 403
  ```

- [ ] Testing:
  - [ ] Test: Usuario Org A intenta ver branding de usuario Org B → 403
  - [ ] Test: Usuario Org A ve branding de usuario Org A → OK

### 3.3 Crear Endpoints de Organización (Día 3 - 2 horas)

- [ ] **Crear archivo: `backend/api/organization.py`**
  ```python
  """
  🏢 Organization API - Gestión de organizaciones
  """
  from flask import Blueprint, jsonify, request, g
  from backend.utils.auth_middleware import jwt_required
  from backend.utils.organization_middleware import require_organization, require_role
  from backend.core.database import get_database_client
  from backend.core.plans import get_plan_config, get_all_plans
  import logging
  
  logger = logging.getLogger(__name__)
  org_bp = Blueprint('organization', __name__, url_prefix='/api/organization')
  db = get_database_client()
  
  @org_bp.route("/", methods=["GET"])
  @jwt_required
  @require_organization
  def get_current_organization():
      """Obtener organización actual del usuario"""
      org = db.get_organization(g.organization_id)
      
      if not org:
          return jsonify({"error": "Organization not found"}), 404
      
      # Agregar info del plan
      plan_config = get_plan_config(org['plan_tier'])
      org['plan_details'] = plan_config
      
      # Agregar uso actual
      users_check = db.check_organization_limit(g.organization_id, 'users')
      rfx_check = db.check_organization_limit(g.organization_id, 'rfx_monthly')
      
      org['usage'] = {
          'users': {
              'current': users_check['current'],
              'limit': users_check['limit'],
              'percentage': (users_check['current'] / users_check['limit'] * 100) if users_check['limit'] > 0 else 0
          },
          'rfx_monthly': {
              'current': rfx_check['current'],
              'limit': rfx_check['limit'],
              'percentage': (rfx_check['current'] / rfx_check['limit'] * 100) if rfx_check['limit'] > 0 else 0
          }
      }
      
      return jsonify(org)
  
  @org_bp.route("/members", methods=["GET"])
  @jwt_required
  @require_organization
  def get_organization_members():
      """Listar miembros de la organización"""
      members = db.client.table("users")\
          .select("id, email, full_name, role, created_at, last_login_at")\
          .eq("organization_id", g.organization_id)\
          .order("role", desc=True)\
          .order("created_at")\
          .execute()
      
      return jsonify({
          "members": members.data,
          "total": len(members.data)
      })
  
  @org_bp.route("/plans", methods=["GET"])
  def get_available_plans():
      """Obtener planes disponibles (público)"""
      return jsonify(get_all_plans())
  
  logger.info("🏢 Organization API initialized")
  ```

- [ ] **Registrar blueprint en app.py**:
  ```python
  from backend.api.organization import org_bp
  app.register_blueprint(org_bp)
  ```

- [ ] Testing:
  - [ ] Test: GET /api/organization retorna org correcta
  - [ ] Test: GET /api/organization/members solo muestra miembros de esa org
  - [ ] Test: GET /api/organization/plans retorna todos los planes

---

## 🧪 FASE 4: TESTING COMPLETO

### 4.1 Tests Unitarios (Día 4 - 2 horas)

- [ ] **Crear: `backend/tests/test_multi_tenant_isolation.py`**
  ```python
  """Tests de aislamiento multi-tenant"""
  
  def test_user_only_sees_own_org_rfx():
      """Usuario solo ve RFX de su organización"""
      # Setup: 2 organizaciones, 2 usuarios, 2 RFX
      # Test: User A solo ve RFX A, no RFX B
      pass
  
  def test_user_cannot_access_other_org_rfx():
      """Usuario no puede acceder a RFX de otra org"""
      # Test: User A intenta GET /rfx/{rfx_b_id} → 404
      pass
  
  def test_organization_limit_enforcement():
      """Límites de organización se respetan"""
      # Test: Org free con 10 RFX → crear 11vo falla
      pass
  ```

- [ ] Ejecutar todos los tests:
  - [ ] `pytest backend/tests/test_multi_tenant_isolation.py -v`
  - [ ] `pytest backend/tests/test_organization_middleware.py -v`
  - [ ] `pytest backend/tests/test_database_client.py -v`
  - [ ] `pytest backend/tests/ -v` (todos)

### 4.2 Tests de Integración (Día 4 - 3 horas)

- [ ] **Escenario 1: Signup y Creación de Org**
  - [ ] Usuario se registra
  - [ ] Se crea organización automáticamente
  - [ ] Usuario es owner de la org
  - [ ] Usuario puede crear RFX

- [ ] **Escenario 2: Aislamiento de Datos**
  - [ ] Org A crea RFX
  - [ ] Org B no puede ver RFX de Org A
  - [ ] Org B crea su propio RFX
  - [ ] Cada org solo ve sus datos

- [ ] **Escenario 3: Límites de Plan**
  - [ ] Org free intenta crear 11vo RFX → falla
  - [ ] Org free intenta invitar 3er usuario → falla
  - [ ] Upgrade a pro → límites aumentan
  - [ ] Ahora puede crear más RFX

### 4.3 Tests Manuales (Día 4 - 2 horas)

- [ ] **Test Manual 1: Flujo Completo**
  - [ ] Crear 2 usuarios en Postman/Insomnia
  - [ ] Verificar que cada uno tiene su org
  - [ ] Crear RFX con usuario 1
  - [ ] Login con usuario 2
  - [ ] Verificar que NO ve RFX de usuario 1
  - [ ] Crear RFX con usuario 2
  - [ ] Verificar que solo ve su RFX

- [ ] **Test Manual 2: Límites**
  - [ ] Crear org free
  - [ ] Crear 10 RFX (debe funcionar)
  - [ ] Intentar crear 11vo (debe fallar con 429)
  - [ ] Verificar mensaje de error claro

- [ ] **Test Manual 3: Roles**
  - [ ] Usuario owner puede ver todos los endpoints
  - [ ] Usuario member puede ver RFX
  - [ ] Usuario member NO puede cambiar plan (si implementamos)

---

## 📝 FASE 5: DOCUMENTACIÓN Y DEPLOYMENT

### 5.1 Documentación (Día 5 - 2 horas)

- [ ] **Crear: `MULTI_TENANT_IMPLEMENTATION_COMPLETE.md`**
  - [ ] Resumen de cambios
  - [ ] Tablas modificadas
  - [ ] Nuevos endpoints
  - [ ] Guía de migración para producción
  - [ ] Troubleshooting común

- [ ] **Actualizar: `README.md`**
  - [ ] Agregar sección de multi-tenancy
  - [ ] Documentar nuevos endpoints
  - [ ] Actualizar diagrama de arquitectura

- [ ] **Crear: `API_MULTI_TENANT.md`**
  - [ ] Documentar todos los endpoints de organization
  - [ ] Ejemplos de uso con curl
  - [ ] Códigos de error específicos

### 5.2 Preparar Deployment (Día 5 - 3 horas)

- [ ] **Crear scripts de migración para producción**
  - [ ] `migrations/001_create_organizations.sql`
  - [ ] `migrations/002_add_organization_fields.sql`
  - [ ] `migrations/003_migrate_data.sql`
  - [ ] `migrations/004_make_required.sql`
  - [ ] `migrations/rollback.sql` (por si acaso)

- [ ] **Crear checklist de deployment**
  - [ ] Backup de producción
  - [ ] Modo mantenimiento ON
  - [ ] Ejecutar migraciones
  - [ ] Deploy de código
  - [ ] Smoke tests
  - [ ] Modo mantenimiento OFF

- [ ] **Preparar rollback plan**
  - [ ] Script para revertir cambios SQL
  - [ ] Procedimiento de rollback de código
  - [ ] Tiempo estimado de rollback

---

## ✅ CRITERIOS DE ACEPTACIÓN

### Funcionalidad

- [ ] Usuarios están agrupados por organización
- [ ] RFX están aislados por organización
- [ ] Límites de plan se respetan
- [ ] Roles funcionan correctamente
- [ ] Migraciones de datos completas (100% usuarios y RFX)

### Performance

- [ ] Queries con índices (< 100ms para listar RFX)
- [ ] No hay N+1 queries
- [ ] Filtros por organization_id usan índices

### Seguridad

- [ ] Usuario Org A NO puede ver datos de Org B
- [ ] Filtros de organization_id en TODOS los endpoints críticos
- [ ] Validación de ownership en modificaciones

### Testing

- [ ] 100% tests unitarios pasan
- [ ] Tests de integración pasan
- [ ] Tests manuales documentados y pasados
- [ ] Coverage > 80% en código nuevo

### Documentación

- [ ] README actualizado
- [ ] API documentada
- [ ] Guía de migración completa
- [ ] Troubleshooting documentado

---

## 🚨 ROLLBACK PLAN

### Si algo sale mal:

1. **Inmediatamente:**
   - [ ] Activar modo mantenimiento
   - [ ] Detener deployment

2. **Rollback de Base de Datos:**
   - [ ] Ejecutar: `psql -d rfx_db -f migrations/rollback.sql`
   - [ ] Verificar: `SELECT COUNT(*) FROM organizations;` → debe ser 0
   - [ ] Verificar: `\d users` → no debe tener organization_id

3. **Rollback de Código:**
   - [ ] `git revert <commit-hash>`
   - [ ] Deploy de versión anterior
   - [ ] Reiniciar servicios

4. **Validación Post-Rollback:**
   - [ ] Sistema funciona como antes
   - [ ] Usuarios pueden crear RFX
   - [ ] No hay errores en logs

---

## 📊 MÉTRICAS DE ÉXITO

### Día 1 (Base de Datos)
- [ ] 4 scripts SQL creados y ejecutados
- [ ] 100% de usuarios migrados a organizaciones
- [ ] 100% de RFX asignados a organizaciones
- [ ] 0 errores en constraints

### Día 2 (Backend Core)
- [ ] Middleware funcionando
- [ ] DatabaseClient con helpers
- [ ] Planes hardcodeados
- [ ] Tests unitarios pasando

### Día 3 (Endpoints)
- [ ] 3+ endpoints actualizados
- [ ] Filtros de organización funcionando
- [ ] Límites validándose
- [ ] Tests de integración pasando

### Día 4 (Testing)
- [ ] 100% tests pasando
- [ ] Aislamiento validado
- [ ] Límites validados
- [ ] Tests manuales completados

### Día 5 (Documentación)
- [ ] Documentación completa
- [ ] Scripts de deployment listos
- [ ] Rollback plan probado
- [ ] Listo para producción

---

**Última actualización:** 5 de Diciembre, 2025  
**Status:** ✅ PLAN APROBADO - LISTO PARA EJECUCIÓN  
**Tiempo Estimado Total:** 5 días (40 horas)  
**Complejidad:** Media  
**Riesgo:** Bajo (cambios incrementales, rollback disponible)
