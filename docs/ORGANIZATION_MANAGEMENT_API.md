# 📘 API de Gestión de Organizaciones

**Fecha:** 16 de Diciembre, 2025  
**Versión:** 1.0  
**Base URL:** `http://localhost:5001` (desarrollo) | `https://tu-servidor.com` (producción)

---

## 🎯 Nuevos Endpoints Implementados

### 1. Actualizar Información de la Organización

```
PATCH /api/organization/current
```

**Permisos:** Solo `owner` y `admin`

**Request Body:**
```json
{
  "name": "New Organization Name",  // opcional
  "slug": "new-org-slug"            // opcional
}
```

**Validaciones:**
- Slug debe tener al menos 3 caracteres
- Slug debe ser único (no puede estar en uso por otra organización)
- Solo se pueden actualizar los campos `name` y `slug`

**Respuesta Exitosa (200):**
```json
{
  "status": "success",
  "message": "Organization updated successfully",
  "data": {
    "id": "uuid",
    "name": "New Organization Name",
    "slug": "new-org-slug",
    "plan_tier": "pro",
    "created_at": "2025-01-01T00:00:00Z",
    "updated_at": "2025-12-16T13:00:00Z"
  }
}
```

**Errores:**
- `400` - No data provided / No valid fields to update
- `400` - Slug must be at least 3 characters
- `403` - Insufficient permissions (not owner/admin)
- `409` - Slug already in use by another organization
- `500` - Failed to update organization

**Ejemplo de uso:**
```javascript
const response = await fetch('/api/organization/current', {
  method: 'PATCH',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    name: "Sabra Corporation Inc.",
    slug: "sabra-corp-inc"
  })
});
```

---

### 2. Cambiar Rol de un Miembro

```
PATCH /api/organization/members/{user_id}/role
```

**Permisos:** Solo `owner` y `admin`

**Request Body:**
```json
{
  "role": "admin"  // "owner", "admin", o "member"
}
```

**Restricciones:**
- ❌ No puedes cambiar tu propio rol
- ❌ Solo owners pueden asignar/modificar el rol de owner
- ❌ No puedes quitar el rol de owner si es el último owner de la organización

**Respuesta Exitosa (200):**
```json
{
  "status": "success",
  "message": "User role updated to admin",
  "data": {
    "id": "user-uuid",
    "email": "user@example.com",
    "full_name": "John Doe",
    "role": "admin"
  }
}
```

**Errores:**
- `400` - Role is required
- `400` - Invalid role. Must be one of: owner, admin, member
- `403` - You cannot change your own role
- `403` - Only owners can assign the owner role
- `403` - Cannot remove the last owner. Assign another owner first.
- `403` - User does not belong to your organization
- `404` - User not found
- `500` - Failed to update user role

**Ejemplo de uso:**
```javascript
// Cambiar usuario a admin
const response = await fetch(`/api/organization/members/${userId}/role`, {
  method: 'PATCH',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    role: "admin"
  })
});
```

---

### 3. Eliminar un Miembro de la Organización

```
DELETE /api/organization/members/{user_id}
```

**Permisos:** Solo `owner` y `admin`

**Restricciones:**
- ❌ No puedes eliminarte a ti mismo
- ❌ No puedes eliminar al último owner

**Respuesta Exitosa (200):**
```json
{
  "status": "success",
  "message": "User removed from organization successfully",
  "data": {
    "removed_user_id": "user-uuid",
    "removed_user_email": "user@example.com"
  }
}
```

**Errores:**
- `403` - You cannot remove yourself from the organization
- `403` - Cannot remove the last owner
- `403` - User does not belong to your organization
- `404` - User not found
- `500` - Failed to remove user from organization

**Ejemplo de uso:**
```javascript
// Eliminar usuario de la organización
const response = await fetch(`/api/organization/members/${userId}`, {
  method: 'DELETE',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
});

if (response.ok) {
  console.log('Usuario eliminado exitosamente');
  // Actualizar lista de miembros en UI
  refreshMembersList();
}
```

---

### 4. Invitar Nuevo Usuario a la Organización

```
POST /api/organization/invite
```

**Permisos:** Solo `owner` y `admin`

**Request Body:**
```json
{
  "email": "newuser@example.com",
  "role": "member"  // "admin" o "member" (solo owners pueden invitar owners)
}
```

**Validaciones:**
- Email es requerido
- Rol debe ser válido según permisos del usuario actual
- Verifica límite de usuarios del plan
- Verifica si el usuario ya pertenece a una organización

**Respuesta Exitosa (200):**
```json
{
  "status": "success",
  "message": "User newuser@example.com added to organization",
  "data": {
    "email": "newuser@example.com",
    "role": "member",
    "user_id": "user-uuid"
  }
}
```

**Nota Importante:**
Si el usuario ya existe en el sistema pero NO tiene organización, se le asigna automáticamente a tu organización.

Si el usuario NO existe, actualmente retorna:
```json
{
  "status": "success",
  "message": "Invitation functionality coming soon",
  "note": "For now, ask the user to register first, then you can add them to your organization",
  "data": {
    "email": "newuser@example.com",
    "role": "member",
    "organization_id": "org-uuid"
  }
}
```

**Errores:**
- `400` - Email is required
- `400` - Invalid role. You can invite: admin, member
- `403` - User limit reached. Upgrade your plan to add more users.
- `409` - User already belongs to an organization
- `500` - Failed to invite member

**Ejemplo de uso:**
```javascript
// Invitar nuevo miembro
const response = await fetch('/api/organization/invite', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    email: "newuser@example.com",
    role: "member"
  })
});

const data = await response.json();
if (data.status === 'success') {
  if (data.data.user_id) {
    // Usuario agregado exitosamente
    console.log('Usuario agregado:', data.data.email);
  } else {
    // Usuario debe registrarse primero
    console.log('Invitación pendiente:', data.note);
  }
}
```

---

## 📊 Matriz de Permisos

| Acción | Owner | Admin | Member |
|--------|-------|-------|--------|
| Ver organización | ✅ | ✅ | ✅ |
| Ver miembros | ✅ | ✅ | ✅ |
| Actualizar nombre/slug | ✅ | ✅ | ❌ |
| Cambiar roles | ✅ | ✅* | ❌ |
| Eliminar miembros | ✅ | ✅ | ❌ |
| Invitar usuarios | ✅ | ✅* | ❌ |

\* Admin puede cambiar roles e invitar, pero NO puede asignar el rol de `owner`

---

## 🔒 Reglas de Negocio Importantes

### Protección del Rol Owner

1. **Siempre debe haber al menos un owner**
   - No puedes eliminar al último owner
   - No puedes cambiar el rol del último owner

2. **Solo owners pueden gestionar owners**
   - Solo un owner puede asignar el rol de owner a otro usuario
   - Admins no pueden crear o modificar owners

3. **No puedes modificarte a ti mismo**
   - No puedes cambiar tu propio rol
   - No puedes eliminarte de la organización

### Límites de Plan

- El sistema verifica automáticamente los límites de usuarios antes de invitar
- Si alcanzas el límite, debes hacer upgrade del plan
- Los límites se definen en `backend/core/plans.py`

---

## 🧪 Testing de Endpoints

### Test 1: Actualizar Organización

```bash
curl -X PATCH http://localhost:5001/api/organization/current \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My New Company Name",
    "slug": "my-new-company"
  }'
```

### Test 2: Cambiar Rol de Usuario

```bash
curl -X PATCH http://localhost:5001/api/organization/members/USER_ID/role \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "role": "admin"
  }'
```

### Test 3: Eliminar Usuario

```bash
curl -X DELETE http://localhost:5001/api/organization/members/USER_ID \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json"
```

### Test 4: Invitar Usuario

```bash
curl -X POST http://localhost:5001/api/organization/invite \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser@example.com",
    "role": "member"
  }'
```

---

## 🎨 Ejemplo Completo de UI de Gestión

```javascript
// Componente de gestión de organización
function OrganizationManagement() {
  const [organization, setOrganization] = useState(null);
  const [members, setMembers] = useState([]);
  
  // Cargar datos
  useEffect(() => {
    loadOrganization();
    loadMembers();
  }, []);
  
  // Actualizar nombre de organización
  async function updateOrgName(newName) {
    const response = await fetch('/api/organization/current', {
      method: 'PATCH',
      headers: {
        'Authorization': `Bearer ${getToken()}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ name: newName })
    });
    
    if (response.ok) {
      const data = await response.json();
      setOrganization(data.data);
      toast.success('Organización actualizada');
    }
  }
  
  // Cambiar rol de usuario
  async function changeUserRole(userId, newRole) {
    const confirmed = confirm(`¿Cambiar rol a ${newRole}?`);
    if (!confirmed) return;
    
    const response = await fetch(`/api/organization/members/${userId}/role`, {
      method: 'PATCH',
      headers: {
        'Authorization': `Bearer ${getToken()}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ role: newRole })
    });
    
    if (response.ok) {
      toast.success('Rol actualizado');
      loadMembers(); // Recargar lista
    } else {
      const error = await response.json();
      toast.error(error.message);
    }
  }
  
  // Eliminar usuario
  async function removeMember(userId, userEmail) {
    const confirmed = confirm(`¿Eliminar a ${userEmail} de la organización?`);
    if (!confirmed) return;
    
    const response = await fetch(`/api/organization/members/${userId}`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${getToken()}`,
        'Content-Type': 'application/json'
      }
    });
    
    if (response.ok) {
      toast.success('Usuario eliminado');
      loadMembers(); // Recargar lista
    } else {
      const error = await response.json();
      toast.error(error.message);
    }
  }
  
  // Invitar usuario
  async function inviteUser(email, role) {
    const response = await fetch('/api/organization/invite', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${getToken()}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ email, role })
    });
    
    const data = await response.json();
    
    if (response.ok) {
      if (data.data.user_id) {
        toast.success(`Usuario ${email} agregado`);
        loadMembers();
      } else {
        toast.info(data.note);
      }
    } else {
      toast.error(data.message);
    }
  }
  
  return (
    <div>
      <h1>{organization?.name}</h1>
      
      {/* Formulario de actualización */}
      <input 
        value={organization?.name}
        onChange={(e) => updateOrgName(e.target.value)}
      />
      
      {/* Lista de miembros */}
      <table>
        <thead>
          <tr>
            <th>Email</th>
            <th>Nombre</th>
            <th>Rol</th>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          {members.map(member => (
            <tr key={member.id}>
              <td>{member.email}</td>
              <td>{member.full_name}</td>
              <td>
                <select 
                  value={member.role}
                  onChange={(e) => changeUserRole(member.id, e.target.value)}
                >
                  <option value="owner">Owner</option>
                  <option value="admin">Admin</option>
                  <option value="member">Member</option>
                </select>
              </td>
              <td>
                <button onClick={() => removeMember(member.id, member.email)}>
                  Eliminar
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      
      {/* Formulario de invitación */}
      <form onSubmit={(e) => {
        e.preventDefault();
        inviteUser(e.target.email.value, e.target.role.value);
      }}>
        <input name="email" type="email" placeholder="Email" required />
        <select name="role">
          <option value="member">Member</option>
          <option value="admin">Admin</option>
        </select>
        <button type="submit">Invitar</button>
      </form>
    </div>
  );
}
```

---

## 📝 Métodos Agregados al DatabaseClient

Los siguientes métodos fueron agregados en `backend/core/database.py`:

### `update_organization(organization_id, update_data)`
Actualiza información de la organización (name, slug, etc.)

### `update_user_role(user_id, new_role)`
Cambia el rol de un usuario ('owner', 'admin', 'member')

### `remove_user_from_organization(user_id)`
Elimina un usuario de su organización (set organization_id to NULL)

### `get_user_by_id(user_id)`
Obtiene información completa de un usuario por su ID

---

## ✅ Checklist de Integración Frontend

- [ ] Implementar formulario de actualización de organización
- [ ] Implementar tabla de gestión de miembros con dropdown de roles
- [ ] Agregar confirmación antes de eliminar usuarios
- [ ] Implementar formulario de invitación de usuarios
- [ ] Manejar errores específicos (403, 409, etc.)
- [ ] Mostrar mensajes de éxito/error al usuario
- [ ] Deshabilitar acciones según rol del usuario actual
- [ ] Actualizar listas automáticamente después de cambios
- [ ] Validar límites de plan antes de invitar
- [ ] Mostrar badges de roles (owner 👑, admin ⚙️, member 👤)

---

## 🚀 Próximas Mejoras (Fase 3 - Opcional)

1. **Sistema de Invitaciones por Email**
   - Generar tokens de invitación temporales
   - Enviar emails con links de aceptación
   - Permitir aceptar/rechazar invitaciones

2. **Transferencia de Ownership**
   - Endpoint dedicado para transferir ownership
   - Confirmación por email del nuevo owner

3. **Auditoría de Cambios**
   - Registrar todos los cambios de roles en una tabla de auditoría
   - Mostrar historial de cambios en la UI

4. **Permisos Granulares**
   - Definir permisos específicos más allá de roles
   - Sistema de permisos por recurso (RFX, Companies, etc.)

---

**Documentación creada:** 16 de Diciembre, 2025  
**Versión:** 1.0  
**Estado:** ✅ Implementado y Listo para Usar
