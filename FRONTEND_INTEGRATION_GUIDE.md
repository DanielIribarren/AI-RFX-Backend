# 🎨 GUÍA DE INTEGRACIÓN FRONTEND - ORGANIZACIONES, PLANES Y CRÉDITOS

**Fecha:** 11 de Febrero, 2026  
**Objetivo:** Integrar sistema de organizaciones, planes y créditos en el frontend

---

## 📋 ÍNDICE

1. [Endpoints Disponibles](#endpoints-disponibles)
2. [Flujo de Autenticación](#flujo-de-autenticación)
3. [Vista: Crear Organización](#vista-crear-organización)
4. [Vista: Dashboard de Organización](#vista-dashboard-de-organización)
5. [Vista: Solicitar Plan](#vista-solicitar-plan)
6. [Vista: Panel Admin - Aprobar Planes](#vista-panel-admin-aprobar-planes)
7. [Vista: Consumo de Créditos](#vista-consumo-de-créditos)
8. [Componentes Reutilizables](#componentes-reutilizables)
9. [Manejo de Errores](#manejo-de-errores)

---

## 🔌 ENDPOINTS DISPONIBLES

### Organizaciones

```javascript
// Crear organización
POST /api/organization
Headers: { Authorization: "Bearer <token>" }
Body: { name: string, slug?: string }

// Obtener organización actual del usuario
GET /api/organization/current
Headers: { Authorization: "Bearer <token>" }

// Obtener miembros de la organización
GET /api/organization/members
Headers: { Authorization: "Bearer <token>" }

// Actualizar organización
PATCH /api/organization/current
Headers: { Authorization: "Bearer <token>" }
Body: { name?: string, slug?: string }

// Cambiar rol de miembro
PATCH /api/organization/members/<user_id>/role
Headers: { Authorization: "Bearer <token>" }
Body: { role: "owner" | "admin" | "member" }

// Remover miembro
DELETE /api/organization/members/<user_id>
Headers: { Authorization: "Bearer <token>" }

// Invitar miembro
POST /api/organization/invite
Headers: { Authorization: "Bearer <token>" }
Body: { email: string, role: "admin" | "member" }
```

### Planes y Suscripciones

```javascript
// Solicitar cambio de plan
POST /api/subscription/request
Headers: { Authorization: "Bearer <token>" }
Body: { 
  requested_tier: "free" | "starter" | "pro" | "enterprise",
  user_notes?: string 
}

// Ver mis solicitudes de plan
GET /api/subscription/my-requests
Headers: { Authorization: "Bearer <token>" }

// Ver plan y créditos actuales
GET /api/subscription/current
Headers: { Authorization: "Bearer <token>" }

// [ADMIN] Ver solicitudes pendientes
GET /api/subscription/admin/pending
Headers: { Authorization: "Bearer <admin_token>" }

// [ADMIN] Aprobar/Rechazar solicitud
POST /api/subscription/admin/review/<request_id>
Headers: { Authorization: "Bearer <admin_token>" }
Body: { 
  action: "approve" | "reject",
  admin_notes?: string 
}

// [ADMIN] Reset manual de créditos
POST /api/subscription/admin/reset-credits
Headers: { Authorization: "Bearer <admin_token>" }
```

### Créditos

```javascript
// Obtener información de créditos
GET /api/credits/info
Headers: { Authorization: "Bearer <token>" }

// Obtener historial de transacciones
GET /api/credits/history
Headers: { Authorization: "Bearer <token>" }
Query: { limit?: number, offset?: number }
```

### Planes Disponibles

```javascript
// Obtener lista de planes disponibles
GET /api/organization/plans
Headers: { Authorization: "Bearer <token>" }

// Obtener información de upgrade
GET /api/organization/upgrade-info
Headers: { Authorization: "Bearer <token>" }
```

---

## 🔐 FLUJO DE AUTENTICACIÓN

### 1. Obtener Token JWT

```javascript
// utils/auth.js
export const getAuthToken = () => {
  return localStorage.getItem('auth_token');
};

export const setAuthToken = (token) => {
  localStorage.setItem('auth_token', token);
};

export const clearAuthToken = () => {
  localStorage.removeItem('auth_token');
};

export const isAuthenticated = () => {
  return !!getAuthToken();
};
```

### 2. Configurar Headers Automáticamente

```javascript
// utils/api.js
import { getAuthToken } from './auth';

export const apiCall = async (endpoint, options = {}) => {
  const token = getAuthToken();
  
  const headers = {
    'Content-Type': 'application/json',
    ...(token && { Authorization: `Bearer ${token}` }),
    ...options.headers,
  };

  const response = await fetch(`${process.env.REACT_APP_API_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.message || 'API Error');
  }

  return response.json();
};
```

---

## 🏢 VISTA: CREAR ORGANIZACIÓN

### Cuándo Mostrar

- Usuario autenticado NO tiene organización (`organization_id === null`)
- Primera vez que accede a la plataforma
- Botón "Crear Organización" en dashboard personal

### Componente: CreateOrganization.jsx

```jsx
import React, { useState } from 'react';
import { apiCall } from '../utils/api';

const CreateOrganization = ({ onSuccess }) => {
  const [formData, setFormData] = useState({
    name: '',
    slug: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const response = await apiCall('/api/organization', {
        method: 'POST',
        body: JSON.stringify(formData),
      });

      console.log('✅ Organización creada:', response.data);
      onSuccess(response.data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleNameChange = (e) => {
    const name = e.target.value;
    const slug = name
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-|-$/g, '');

    setFormData({ name, slug });
  };

  return (
    <div className="max-w-md mx-auto p-6 bg-white rounded-lg shadow">
      <h2 className="text-2xl font-bold mb-4">Crear Organización</h2>
      
      {error && (
        <div className="mb-4 p-3 bg-red-100 text-red-700 rounded">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div className="mb-4">
          <label className="block text-sm font-medium mb-2">
            Nombre de la Organización
          </label>
          <input
            type="text"
            value={formData.name}
            onChange={handleNameChange}
            className="w-full px-3 py-2 border rounded"
            placeholder="Mi Empresa S.A."
            required
            minLength={2}
          />
        </div>

        <div className="mb-4">
          <label className="block text-sm font-medium mb-2">
            Slug (URL amigable)
          </label>
          <input
            type="text"
            value={formData.slug}
            onChange={(e) => setFormData({ ...formData, slug: e.target.value })}
            className="w-full px-3 py-2 border rounded"
            placeholder="mi-empresa"
            pattern="[a-z0-9-]+"
          />
          <p className="text-xs text-gray-500 mt-1">
            Solo letras minúsculas, números y guiones
          </p>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? 'Creando...' : 'Crear Organización'}
        </button>
      </form>

      <div className="mt-4 p-3 bg-blue-50 rounded">
        <p className="text-sm text-blue-800">
          ℹ️ Al crear la organización, serás asignado como <strong>Owner</strong> con plan <strong>Free</strong> (100 créditos/mes).
        </p>
      </div>
    </div>
  );
};

export default CreateOrganization;
```

### Flujo Completo

```
1. Usuario completa formulario
2. Frontend envía POST /api/organization
3. Backend crea organización con:
   - plan_tier: 'free'
   - credits_total: 100
   - credits_used: 0
   - credits_reset_date: NOW() + 30 días
4. Backend asigna usuario como 'owner'
5. Frontend recibe organización creada
6. Redirigir a dashboard de organización
```

---

## 📊 VISTA: DASHBOARD DE ORGANIZACIÓN

### Componente: OrganizationDashboard.jsx

```jsx
import React, { useState, useEffect } from 'react';
import { apiCall } from '../utils/api';

const OrganizationDashboard = () => {
  const [organization, setOrganization] = useState(null);
  const [credits, setCredits] = useState(null);
  const [members, setMembers] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      const [orgData, creditsData, membersData] = await Promise.all([
        apiCall('/api/organization/current'),
        apiCall('/api/subscription/current'),
        apiCall('/api/organization/members'),
      ]);

      setOrganization(orgData.data);
      setCredits(creditsData.data);
      setMembers(membersData.data);
    } catch (err) {
      console.error('Error loading dashboard:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="p-6">Cargando...</div>;
  }

  const creditsPercentage = (credits.credits_available / credits.credits_total) * 100;
  const isLowCredits = creditsPercentage < 20;

  return (
    <div className="p-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold">{organization.name}</h1>
        <p className="text-gray-600">@{organization.slug}</p>
      </div>

      {/* Plan y Créditos */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        {/* Plan Actual */}
        <div className="bg-white p-6 rounded-lg shadow">
          <h2 className="text-xl font-semibold mb-4">Plan Actual</h2>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-3xl font-bold capitalize">{credits.plan_tier}</p>
              <p className="text-sm text-gray-600">
                {credits.max_users} usuarios • {credits.max_rfx_per_month} RFX/mes
              </p>
            </div>
            <button
              onClick={() => window.location.href = '/upgrade'}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              Upgrade
            </button>
          </div>

          {/* Solicitud Pendiente */}
          {credits.pending_request && (
            <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded">
              <p className="text-sm text-yellow-800">
                ⏳ Solicitud de plan <strong>{credits.pending_request.requested_tier}</strong> pendiente de aprobación
              </p>
            </div>
          )}
        </div>

        {/* Créditos */}
        <div className="bg-white p-6 rounded-lg shadow">
          <h2 className="text-xl font-semibold mb-4">Créditos</h2>
          
          {/* Barra de Progreso */}
          <div className="mb-4">
            <div className="flex justify-between text-sm mb-1">
              <span>{credits.credits_available} disponibles</span>
              <span>{credits.credits_total} totales</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-3">
              <div
                className={`h-3 rounded-full transition-all ${
                  isLowCredits ? 'bg-red-500' : 'bg-green-500'
                }`}
                style={{ width: `${creditsPercentage}%` }}
              />
            </div>
          </div>

          {/* Alerta de Créditos Bajos */}
          {isLowCredits && (
            <div className="p-3 bg-red-50 border border-red-200 rounded">
              <p className="text-sm text-red-800">
                ⚠️ Créditos bajos. Considera hacer upgrade de plan.
              </p>
            </div>
          )}

          {/* Fecha de Reset */}
          <p className="text-sm text-gray-600 mt-4">
            Próximo reset: {new Date(credits.credits_reset_date).toLocaleDateString()}
          </p>
        </div>
      </div>

      {/* Miembros */}
      <div className="bg-white p-6 rounded-lg shadow">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold">Miembros del Equipo</h2>
          <button
            onClick={() => window.location.href = '/invite'}
            className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
          >
            Invitar Miembro
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left">Usuario</th>
                <th className="px-4 py-2 text-left">Email</th>
                <th className="px-4 py-2 text-left">Rol</th>
                <th className="px-4 py-2 text-left">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {members.map((member) => (
                <tr key={member.id} className="border-t">
                  <td className="px-4 py-3">
                    <div className="flex items-center">
                      {member.avatar_url && (
                        <img
                          src={member.avatar_url}
                          alt={member.name}
                          className="w-8 h-8 rounded-full mr-2"
                        />
                      )}
                      <span>{member.name || member.username}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3">{member.email}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded text-xs ${
                      member.role === 'owner' ? 'bg-purple-100 text-purple-800' :
                      member.role === 'admin' ? 'bg-blue-100 text-blue-800' :
                      'bg-gray-100 text-gray-800'
                    }`}>
                      {member.role}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    {member.role !== 'owner' && (
                      <button className="text-red-600 hover:text-red-800 text-sm">
                        Remover
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default OrganizationDashboard;
```

---

## 🎫 VISTA: SOLICITAR PLAN

### Componente: RequestPlanUpgrade.jsx

```jsx
import React, { useState, useEffect } from 'react';
import { apiCall } from '../utils/api';

const RequestPlanUpgrade = () => {
  const [plans, setPlans] = useState([]);
  const [currentPlan, setCurrentPlan] = useState(null);
  const [selectedPlan, setSelectedPlan] = useState(null);
  const [userNotes, setUserNotes] = useState('');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    loadPlansData();
  }, []);

  const loadPlansData = async () => {
    try {
      const [plansData, currentData] = await Promise.all([
        apiCall('/api/organization/plans'),
        apiCall('/api/subscription/current'),
      ]);

      setPlans(plansData.data);
      setCurrentPlan(currentData.data);
    } catch (err) {
      console.error('Error loading plans:', err);
    }
  };

  const handleRequestPlan = async () => {
    if (!selectedPlan) return;

    setLoading(true);
    try {
      await apiCall('/api/subscription/request', {
        method: 'POST',
        body: JSON.stringify({
          requested_tier: selectedPlan.tier,
          user_notes: userNotes,
        }),
      });

      setSuccess(true);
      setTimeout(() => {
        window.location.href = '/dashboard';
      }, 2000);
    } catch (err) {
      alert(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="max-w-2xl mx-auto p-6 text-center">
        <div className="bg-green-50 p-6 rounded-lg">
          <h2 className="text-2xl font-bold text-green-800 mb-2">
            ✅ Solicitud Enviada
          </h2>
          <p className="text-green-700">
            Tu solicitud de plan <strong>{selectedPlan.name}</strong> ha sido enviada.
            Un administrador la revisará pronto.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto p-6">
      <h1 className="text-3xl font-bold mb-2">Upgrade de Plan</h1>
      <p className="text-gray-600 mb-6">
        Plan actual: <strong className="capitalize">{currentPlan?.plan_tier}</strong>
      </p>

      {/* Planes Disponibles */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
        {plans.map((plan) => {
          const isCurrent = plan.tier === currentPlan?.plan_tier;
          const isDowngrade = plans.findIndex(p => p.tier === plan.tier) < 
                             plans.findIndex(p => p.tier === currentPlan?.plan_tier);

          return (
            <div
              key={plan.tier}
              className={`border rounded-lg p-6 cursor-pointer transition-all ${
                selectedPlan?.tier === plan.tier
                  ? 'border-blue-500 bg-blue-50'
                  : isCurrent
                  ? 'border-green-500 bg-green-50'
                  : 'border-gray-200 hover:border-blue-300'
              } ${isDowngrade ? 'opacity-50' : ''}`}
              onClick={() => !isCurrent && !isDowngrade && setSelectedPlan(plan)}
            >
              {isCurrent && (
                <span className="inline-block px-2 py-1 bg-green-500 text-white text-xs rounded mb-2">
                  Plan Actual
                </span>
              )}

              <h3 className="text-xl font-bold mb-2 capitalize">{plan.tier}</h3>
              <p className="text-3xl font-bold mb-4">
                ${plan.price_monthly_usd}
                <span className="text-sm text-gray-600">/mes</span>
              </p>

              <ul className="space-y-2 text-sm">
                <li>✓ {plan.max_users} usuarios</li>
                <li>✓ {plan.credits_per_month} créditos/mes</li>
                <li>✓ {plan.max_rfx_per_month} RFX/mes</li>
                {plan.free_regenerations === Infinity ? (
                  <li>✓ Regeneraciones ilimitadas</li>
                ) : (
                  <li>✓ {plan.free_regenerations} regeneraciones gratis</li>
                )}
              </ul>

              {!isCurrent && !isDowngrade && (
                <button
                  className={`w-full mt-4 py-2 rounded ${
                    selectedPlan?.tier === plan.tier
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                  }`}
                >
                  {selectedPlan?.tier === plan.tier ? 'Seleccionado' : 'Seleccionar'}
                </button>
              )}
            </div>
          );
        })}
      </div>

      {/* Formulario de Solicitud */}
      {selectedPlan && (
        <div className="bg-white p-6 rounded-lg shadow">
          <h2 className="text-xl font-semibold mb-4">
            Solicitar Plan {selectedPlan.name}
          </h2>

          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">
              Notas para el Administrador (Opcional)
            </label>
            <textarea
              value={userNotes}
              onChange={(e) => setUserNotes(e.target.value)}
              className="w-full px-3 py-2 border rounded"
              rows={4}
              placeholder="Ej: Necesitamos más usuarios para el equipo de ventas..."
            />
          </div>

          <div className="bg-yellow-50 p-4 rounded mb-4">
            <p className="text-sm text-yellow-800">
              ⚠️ <strong>Importante:</strong> Esta solicitud requiere aprobación manual del administrador.
              Recibirás una notificación cuando sea revisada.
            </p>
          </div>

          <button
            onClick={handleRequestPlan}
            disabled={loading}
            className="w-full bg-blue-600 text-white py-3 rounded hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? 'Enviando Solicitud...' : 'Enviar Solicitud de Upgrade'}
          </button>
        </div>
      )}
    </div>
  );
};

export default RequestPlanUpgrade;
```

---

## 👨‍💼 VISTA: PANEL ADMIN - APROBAR PLANES

### Componente: AdminPlanRequests.jsx

```jsx
import React, { useState, useEffect } from 'react';
import { apiCall } from '../utils/api';

const AdminPlanRequests = () => {
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [reviewingId, setReviewingId] = useState(null);

  useEffect(() => {
    loadPendingRequests();
  }, []);

  const loadPendingRequests = async () => {
    try {
      const response = await apiCall('/api/subscription/admin/pending');
      setRequests(response.data);
    } catch (err) {
      console.error('Error loading requests:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleReview = async (requestId, action, adminNotes = '') => {
    setReviewingId(requestId);

    try {
      await apiCall(`/api/subscription/admin/review/${requestId}`, {
        method: 'POST',
        body: JSON.stringify({ action, admin_notes: adminNotes }),
      });

      // Recargar lista
      await loadPendingRequests();
      alert(`Solicitud ${action === 'approve' ? 'aprobada' : 'rechazada'} exitosamente`);
    } catch (err) {
      alert(err.message);
    } finally {
      setReviewingId(null);
    }
  };

  if (loading) {
    return <div className="p-6">Cargando solicitudes...</div>;
  }

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <h1 className="text-3xl font-bold mb-6">Solicitudes de Plan Pendientes</h1>

      {requests.length === 0 ? (
        <div className="bg-gray-50 p-6 rounded-lg text-center">
          <p className="text-gray-600">No hay solicitudes pendientes</p>
        </div>
      ) : (
        <div className="space-y-4">
          {requests.map((request) => (
            <div key={request.id} className="bg-white p-6 rounded-lg shadow">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h3 className="text-xl font-semibold">
                    {request.organization_name || request.user_email}
                  </h3>
                  <p className="text-sm text-gray-600">
                    Solicitud creada: {new Date(request.created_at).toLocaleString()}
                  </p>
                </div>
                <span className="px-3 py-1 bg-yellow-100 text-yellow-800 rounded text-sm">
                  Pendiente
                </span>
              </div>

              <div className="grid grid-cols-2 gap-4 mb-4">
                <div>
                  <p className="text-sm text-gray-600">Plan Actual</p>
                  <p className="text-lg font-semibold capitalize">{request.current_tier}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Plan Solicitado</p>
                  <p className="text-lg font-semibold capitalize text-blue-600">
                    {request.requested_tier}
                  </p>
                </div>
              </div>

              {request.user_notes && (
                <div className="mb-4 p-3 bg-gray-50 rounded">
                  <p className="text-sm font-medium mb-1">Notas del Usuario:</p>
                  <p className="text-sm text-gray-700">{request.user_notes}</p>
                </div>
              )}

              <div className="flex gap-3">
                <button
                  onClick={() => {
                    const notes = prompt('Notas del admin (opcional):');
                    if (notes !== null) {
                      handleReview(request.id, 'approve', notes);
                    }
                  }}
                  disabled={reviewingId === request.id}
                  className="flex-1 bg-green-600 text-white py-2 rounded hover:bg-green-700 disabled:opacity-50"
                >
                  {reviewingId === request.id ? 'Procesando...' : '✓ Aprobar'}
                </button>
                <button
                  onClick={() => {
                    const notes = prompt('Razón del rechazo:');
                    if (notes !== null && notes.trim()) {
                      handleReview(request.id, 'reject', notes);
                    }
                  }}
                  disabled={reviewingId === request.id}
                  className="flex-1 bg-red-600 text-white py-2 rounded hover:bg-red-700 disabled:opacity-50"
                >
                  ✗ Rechazar
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default AdminPlanRequests;
```

---

## 💳 VISTA: CONSUMO DE CRÉDITOS

### Componente: CreditsUsage.jsx

```jsx
import React, { useState, useEffect } from 'react';
import { apiCall } from '../utils/api';

const CreditsUsage = () => {
  const [creditsInfo, setCreditsInfo] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const limit = 20;

  useEffect(() => {
    loadCreditsData();
  }, [page]);

  const loadCreditsData = async () => {
    try {
      const [infoData, historyData] = await Promise.all([
        apiCall('/api/credits/info'),
        apiCall(`/api/credits/history?limit=${limit}&offset=${page * limit}`),
      ]);

      setCreditsInfo(infoData.data);
      setHistory(historyData.data);
    } catch (err) {
      console.error('Error loading credits:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="p-6">Cargando...</div>;
  }

  const usagePercentage = (creditsInfo.credits_used / creditsInfo.credits_total) * 100;

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <h1 className="text-3xl font-bold mb-6">Consumo de Créditos</h1>

      {/* Resumen */}
      <div className="bg-white p-6 rounded-lg shadow mb-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div>
            <p className="text-sm text-gray-600 mb-1">Créditos Disponibles</p>
            <p className="text-3xl font-bold text-green-600">
              {creditsInfo.credits_available}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-600 mb-1">Créditos Usados</p>
            <p className="text-3xl font-bold text-blue-600">
              {creditsInfo.credits_used}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-600 mb-1">Total del Plan</p>
            <p className="text-3xl font-bold text-gray-800">
              {creditsInfo.credits_total}
            </p>
          </div>
        </div>

        {/* Barra de Progreso */}
        <div className="mt-6">
          <div className="flex justify-between text-sm mb-2">
            <span>Uso del Mes</span>
            <span>{usagePercentage.toFixed(1)}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-4">
            <div
              className={`h-4 rounded-full transition-all ${
                usagePercentage > 80 ? 'bg-red-500' :
                usagePercentage > 50 ? 'bg-yellow-500' :
                'bg-green-500'
              }`}
              style={{ width: `${usagePercentage}%` }}
            />
          </div>
        </div>

        {/* Fecha de Reset */}
        <div className="mt-4 p-3 bg-blue-50 rounded">
          <p className="text-sm text-blue-800">
            📅 Próximo reset de créditos: {' '}
            <strong>{new Date(creditsInfo.credits_reset_date).toLocaleDateString()}</strong>
          </p>
        </div>
      </div>

      {/* Historial de Transacciones */}
      <div className="bg-white p-6 rounded-lg shadow">
        <h2 className="text-xl font-semibold mb-4">Historial de Transacciones</h2>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left">Fecha</th>
                <th className="px-4 py-2 text-left">Tipo</th>
                <th className="px-4 py-2 text-left">Descripción</th>
                <th className="px-4 py-2 text-right">Créditos</th>
              </tr>
            </thead>
            <tbody>
              {history.map((transaction) => (
                <tr key={transaction.id} className="border-t">
                  <td className="px-4 py-3 text-sm">
                    {new Date(transaction.created_at).toLocaleString()}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded text-xs ${
                      transaction.type === 'consumption' ? 'bg-red-100 text-red-800' :
                      transaction.type === 'reset' ? 'bg-green-100 text-green-800' :
                      'bg-blue-100 text-blue-800'
                    }`}>
                      {transaction.type}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm">{transaction.description}</td>
                  <td className={`px-4 py-3 text-right font-semibold ${
                    transaction.amount > 0 ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {transaction.amount > 0 ? '+' : ''}{transaction.amount}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Paginación */}
        <div className="flex justify-between items-center mt-4">
          <button
            onClick={() => setPage(Math.max(0, page - 1))}
            disabled={page === 0}
            className="px-4 py-2 bg-gray-200 rounded disabled:opacity-50"
          >
            Anterior
          </button>
          <span className="text-sm text-gray-600">Página {page + 1}</span>
          <button
            onClick={() => setPage(page + 1)}
            disabled={history.length < limit}
            className="px-4 py-2 bg-gray-200 rounded disabled:opacity-50"
          >
            Siguiente
          </button>
        </div>
      </div>
    </div>
  );
};

export default CreditsUsage;
```

---

## 🧩 COMPONENTES REUTILIZABLES

### 1. CreditsBadge.jsx - Mostrar Créditos en Navbar

```jsx
import React, { useState, useEffect } from 'react';
import { apiCall } from '../utils/api';

const CreditsBadge = () => {
  const [credits, setCredits] = useState(null);

  useEffect(() => {
    loadCredits();
    // Actualizar cada 5 minutos
    const interval = setInterval(loadCredits, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  const loadCredits = async () => {
    try {
      const response = await apiCall('/api/credits/info');
      setCredits(response.data);
    } catch (err) {
      console.error('Error loading credits:', err);
    }
  };

  if (!credits) return null;

  const percentage = (credits.credits_available / credits.credits_total) * 100;
  const isLow = percentage < 20;

  return (
    <div
      className={`px-3 py-1 rounded-full text-sm font-medium ${
        isLow ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'
      }`}
      title={`${credits.credits_used} usados de ${credits.credits_total}`}
    >
      {isLow && '⚠️ '}
      {credits.credits_available} créditos
    </div>
  );
};

export default CreditsBadge;
```

### 2. PlanBadge.jsx - Mostrar Plan Actual

```jsx
import React from 'react';

const PlanBadge = ({ tier, size = 'md' }) => {
  const colors = {
    free: 'bg-gray-100 text-gray-800',
    starter: 'bg-blue-100 text-blue-800',
    pro: 'bg-purple-100 text-purple-800',
    enterprise: 'bg-yellow-100 text-yellow-800',
  };

  const sizes = {
    sm: 'text-xs px-2 py-1',
    md: 'text-sm px-3 py-1',
    lg: 'text-base px-4 py-2',
  };

  return (
    <span className={`rounded-full font-medium capitalize ${colors[tier]} ${sizes[size]}`}>
      {tier}
    </span>
  );
};

export default PlanBadge;
```

### 3. CreditsGuard.jsx - Verificar Créditos Antes de Acción

```jsx
import React, { useState, useEffect } from 'react';
import { apiCall } from '../utils/api';

const CreditsGuard = ({ operation = 'complete', children, onInsufficientCredits }) => {
  const [hasCredits, setHasCredits] = useState(true);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkCredits();
  }, [operation]);

  const checkCredits = async () => {
    try {
      const response = await apiCall('/api/credits/info');
      const cost = getOperationCost(operation);
      setHasCredits(response.data.credits_available >= cost);
    } catch (err) {
      console.error('Error checking credits:', err);
    } finally {
      setLoading(false);
    }
  };

  const getOperationCost = (op) => {
    const costs = {
      extraction: 5,
      generation: 5,
      complete: 10,
      regeneration: 5,
      chat_message: 1,
    };
    return costs[op] || 0;
  };

  if (loading) {
    return <div>Verificando créditos...</div>;
  }

  if (!hasCredits) {
    return (
      <div className="p-4 bg-red-50 border border-red-200 rounded">
        <p className="text-red-800 font-medium mb-2">
          ⚠️ Créditos Insuficientes
        </p>
        <p className="text-sm text-red-700 mb-3">
          No tienes suficientes créditos para realizar esta operación.
        </p>
        <button
          onClick={onInsufficientCredits || (() => window.location.href = '/upgrade')}
          className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
        >
          Upgrade de Plan
        </button>
      </div>
    );
  }

  return <>{children}</>;
};

export default CreditsGuard;
```

**Uso:**
```jsx
<CreditsGuard operation="complete">
  <button onClick={processRFX}>Procesar RFX</button>
</CreditsGuard>
```

---

## ⚠️ MANEJO DE ERRORES

### Hook Personalizado: useApiError.js

```javascript
import { useState } from 'react';

export const useApiError = () => {
  const [error, setError] = useState(null);

  const handleError = (err) => {
    // Errores específicos del sistema de créditos
    if (err.message?.includes('Insufficient credits')) {
      setError({
        type: 'insufficient_credits',
        message: 'No tienes suficientes créditos para esta operación',
        action: 'upgrade',
      });
    } else if (err.message?.includes('already have a pending plan request')) {
      setError({
        type: 'pending_request',
        message: 'Ya tienes una solicitud de plan pendiente',
        action: 'wait',
      });
    } else if (err.message?.includes('already have the')) {
      setError({
        type: 'same_plan',
        message: 'Ya tienes este plan activo',
        action: 'dismiss',
      });
    } else if (err.message?.includes('already created an organization')) {
      setError({
        type: 'org_exists',
        message: 'Ya tienes una organización creada',
        action: 'dashboard',
      });
    } else {
      setError({
        type: 'generic',
        message: err.message || 'Error desconocido',
        action: 'retry',
      });
    }
  };

  const clearError = () => setError(null);

  return { error, handleError, clearError };
};
```

### Componente: ErrorAlert.jsx

```jsx
import React from 'react';

const ErrorAlert = ({ error, onDismiss, onAction }) => {
  if (!error) return null;

  const actions = {
    upgrade: {
      label: 'Upgrade de Plan',
      className: 'bg-blue-600 hover:bg-blue-700',
      onClick: () => window.location.href = '/upgrade',
    },
    wait: {
      label: 'Ver Mis Solicitudes',
      className: 'bg-yellow-600 hover:bg-yellow-700',
      onClick: () => window.location.href = '/my-requests',
    },
    dashboard: {
      label: 'Ir al Dashboard',
      className: 'bg-green-600 hover:bg-green-700',
      onClick: () => window.location.href = '/dashboard',
    },
    retry: {
      label: 'Reintentar',
      className: 'bg-gray-600 hover:bg-gray-700',
      onClick: onAction,
    },
    dismiss: {
      label: 'Entendido',
      className: 'bg-gray-600 hover:bg-gray-700',
      onClick: onDismiss,
    },
  };

  const action = actions[error.action] || actions.dismiss;

  return (
    <div className="fixed bottom-4 right-4 max-w-md bg-red-50 border-l-4 border-red-500 p-4 rounded shadow-lg">
      <div className="flex items-start">
        <div className="flex-shrink-0">
          <span className="text-2xl">⚠️</span>
        </div>
        <div className="ml-3 flex-1">
          <p className="text-sm font-medium text-red-800">{error.message}</p>
          <div className="mt-3 flex gap-2">
            <button
              onClick={action.onClick}
              className={`px-4 py-2 text-white rounded text-sm ${action.className}`}
            >
              {action.label}
            </button>
            {error.action !== 'dismiss' && (
              <button
                onClick={onDismiss}
                className="px-4 py-2 bg-gray-200 text-gray-700 rounded text-sm hover:bg-gray-300"
              >
                Cerrar
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ErrorAlert;
```

---

## 🎯 RESUMEN DE INTEGRACIÓN

### Flujo Completo del Usuario

```
1. REGISTRO/LOGIN
   └─ Obtener JWT token
   └─ Guardar en localStorage

2. PRIMERA VEZ (Sin Organización)
   └─ Mostrar CreateOrganization
   └─ Usuario crea org → Plan FREE (100 créditos)
   └─ Redirigir a Dashboard

3. DASHBOARD
   └─ Mostrar plan actual, créditos, miembros
   └─ CreditsBadge en navbar
   └─ Botón "Upgrade" si quiere más créditos

4. SOLICITAR UPGRADE
   └─ Ver planes disponibles
   └─ Seleccionar plan
   └─ Enviar solicitud con notas
   └─ Estado: "Pendiente de aprobación"

5. ADMIN APRUEBA
   └─ Admin ve solicitudes pendientes
   └─ Aprueba → Plan actualizado + créditos reseteados
   └─ Usuario puede usar nuevo plan inmediatamente

6. USAR CRÉDITOS
   └─ Cada operación consume créditos
   └─ CreditsGuard verifica antes de permitir
   └─ Si no hay créditos → Mostrar upgrade

7. RESET MENSUAL
   └─ Automático (si implementas cron) o manual (admin)
   └─ credits_used = 0
   └─ credits_total = según plan actual
   └─ credits_reset_date = +30 días
```

### Checklist de Implementación

- [ ] Configurar autenticación JWT
- [ ] Implementar CreateOrganization
- [ ] Implementar OrganizationDashboard
- [ ] Implementar RequestPlanUpgrade
- [ ] Implementar AdminPlanRequests (solo admins)
- [ ] Implementar CreditsUsage
- [ ] Agregar CreditsBadge en navbar
- [ ] Agregar CreditsGuard en operaciones críticas
- [ ] Implementar manejo de errores
- [ ] Testing de flujo completo

---

**Fecha:** 11 de Febrero, 2026  
**Estado:** ✅ Guía Completa de Integración Frontend
