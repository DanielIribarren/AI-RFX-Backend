# 🔧 Fix: User Not Found - JWT Auth Error

## 🔴 Problema Identificado

```
❌ JWT Auth: User not found - user_id: 186ea35f-3cf8-480f-a7d3-0af178c09498
❌ JWT Auth: User not found - user_id: c17f0d49-501c-40e4-8a63-c02c4f09ed90
```

### Causa Raíz

Los usuarios **existen en `auth.users` (Supabase Auth)** pero **NO en la tabla `users` (custom)**:

```
✅ JWT Token válido → Decodifica correctamente
✅ user_id extraído del token
❌ Query a tabla users → NO encuentra registro
❌ Retorna 401 Unauthorized
```

**Razón:** Usuarios se registraron antes de implementar la tabla `users` o la sincronización está rota.

---

## ✅ Solución: Sincronizar Usuarios

### Opción 1: Script Python (Recomendado)

**En el servidor Ubuntu:**

```bash
cd /home/ubuntu/nodejs/AI-RFX-Backend-Clean

# Ejecutar sincronización
python3 sync_missing_users.py
```

**El script:**
1. ✅ Verifica si usuarios existen en tabla `users`
2. ✅ Obtiene datos de `auth.users` usando Admin API
3. ✅ Extrae metadata (full_name, username, avatar_url)
4. ✅ Inserta usuarios faltantes en tabla `users`
5. ✅ Asigna organización por defecto
6. ✅ Configura status correcto (active/pending_verification)
7. ✅ Verifica sincronización exitosa

**Output esperado:**
```
🔄 INICIANDO SINCRONIZACIÓN DE USUARIOS
✅ Usuario sincronizado exitosamente:
   - Full Name: Daniel Iribarren
   - Username: daniel
   - Status: active
   - Organization: uuid-org-default

📊 RESUMEN DE SINCRONIZACIÓN
✅ Usuarios sincronizados: 2/2
```

### Opción 2: SQL Directo (Alternativa)

**Ejecutar en Supabase SQL Editor:**

```bash
# Subir archivo SQL a servidor
scp migrations/sync_auth_users_to_users_table.sql ubuntu@server:/tmp/

# En servidor, ejecutar con psql (si tienes acceso directo)
# O ejecutar desde Supabase Dashboard → SQL Editor
```

---

## 🔍 Verificación Post-Sincronización

### 1. Verificar usuarios en tabla

**En Supabase SQL Editor:**

```sql
-- Verificar usuarios específicos
SELECT 
    id,
    email,
    full_name,
    status,
    organization_id,
    role,
    created_at
FROM users
WHERE id IN (
    '186ea35f-3cf8-480f-a7d3-0af178c09498',
    'c17f0d49-501c-40e4-8a63-c02c4f09ed90'
);
```

**Output esperado:**
```
id                                   | email              | status | role
-------------------------------------|--------------------|---------|---------
186ea35f-3cf8-480f-a7d3-0af178c09498 | user@example.com   | active | admin
c17f0d49-501c-40e4-8a63-c02c4f09ed90 | user2@example.com  | active | admin
```

### 2. Reiniciar PM2

```bash
pm2 restart all
```

### 3. Probar desde Frontend

```bash
# Verificar logs en tiempo real
pm2 logs RFX-dev --lines 50

# Deberías ver:
✅ Authenticated user: user@example.com (ID: 186ea35f...)
```

---

## 📋 Archivos Creados

1. **`sync_missing_users.py`** - Script Python de sincronización
2. **`migrations/sync_auth_users_to_users_table.sql`** - Migración SQL
3. **`debug_missing_users.py`** - Script de diagnóstico (opcional)

---

## 🎯 Flujo Completo de Autenticación

```
1. Usuario hace login → Supabase Auth genera JWT
2. JWT contiene user_id en payload.sub
3. Frontend envía JWT en header: Authorization: Bearer <token>
4. Backend decodifica JWT → extrae user_id
5. Backend consulta tabla users → ✅ DEBE EXISTIR
6. Si existe y status='active' → ✅ Autenticado
7. Si NO existe → ❌ 401 User not found
```

---

## 🔧 Prevención Futura

### Trigger Automático (Recomendado)

Crear trigger que sincronice automáticamente cuando se crea usuario en `auth.users`:

```sql
-- Función para sincronizar nuevo usuario
CREATE OR REPLACE FUNCTION sync_new_user_to_users_table()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO users (
        id,
        email,
        full_name,
        username,
        status,
        organization_id,
        role,
        created_at
    )
    VALUES (
        NEW.id,
        NEW.email,
        COALESCE(
            NEW.raw_user_meta_data->>'full_name',
            SPLIT_PART(NEW.email, '@', 1)
        ),
        SPLIT_PART(NEW.email, '@', 1),
        CASE 
            WHEN NEW.email_confirmed_at IS NOT NULL THEN 'active'
            ELSE 'pending_verification'
        END,
        (SELECT id FROM organizations WHERE name = 'Default Organization' LIMIT 1),
        'admin',
        NEW.created_at
    )
    ON CONFLICT (id) DO NOTHING;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger en auth.users
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION sync_new_user_to_users_table();
```

**Nota:** Los triggers en `auth.users` requieren permisos especiales en Supabase.

---

## 🚨 Troubleshooting

### Problema: Script falla con "Module not found"

```bash
# Instalar dependencias
cd /home/ubuntu/nodejs/AI-RFX-Backend-Clean
pip3 install -r requirements.txt
```

### Problema: "SUPABASE_SERVICE_ROLE_KEY not found"

```bash
# Verificar .env
cat .env | grep SUPABASE_SERVICE_ROLE_KEY

# Si no existe, agregar:
echo "SUPABASE_SERVICE_ROLE_KEY=tu_service_role_key" >> .env
```

### Problema: Usuario sincronizado pero sigue error 401

**Verificar status del usuario:**

```sql
SELECT id, email, status FROM users 
WHERE id = '186ea35f-3cf8-480f-a7d3-0af178c09498';

-- Si status != 'active', actualizar:
UPDATE users 
SET status = 'active' 
WHERE id = '186ea35f-3cf8-480f-a7d3-0af178c09498';
```

### Problema: Usuario NO existe en auth.users

```bash
# Significa que el JWT es de otro ambiente (dev vs prod)
# Verificar que SUPABASE_URL en .env coincida con el ambiente del frontend
```

---

## 📊 Comandos Útiles

```bash
# Ver logs en tiempo real
pm2 logs RFX-dev --lines 100

# Filtrar solo errores de auth
pm2 logs RFX-dev | grep "JWT Auth"

# Reiniciar servidor
pm2 restart RFX-dev

# Ver status
pm2 status
```

---

## ✅ Checklist de Resolución

- [ ] Ejecutar `sync_missing_users.py` en servidor
- [ ] Verificar usuarios en tabla `users` (SQL query)
- [ ] Reiniciar PM2: `pm2 restart all`
- [ ] Probar login desde frontend
- [ ] Verificar logs: NO más "User not found"
- [ ] Confirmar autenticación exitosa: "✅ Authenticated user"
- [ ] (Opcional) Implementar trigger para prevención futura

---

## 📞 Contacto

Si el problema persiste después de seguir estos pasos, verificar:

1. ¿Los usuarios existen en `auth.users`? (Supabase Dashboard → Authentication)
2. ¿El `SUPABASE_URL` en `.env` coincide con el ambiente del frontend?
3. ¿El `SUPABASE_SERVICE_ROLE_KEY` es correcto y tiene permisos?

---

**Estado:** ✅ Solución lista para ejecutar
**Archivos:** `sync_missing_users.py`, `migrations/sync_auth_users_to_users_table.sql`
**Acción requerida:** Ejecutar script en servidor Ubuntu
