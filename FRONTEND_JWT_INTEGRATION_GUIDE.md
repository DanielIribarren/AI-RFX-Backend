# 🔐 Guía de Integración JWT para Frontend

**Problema Actual:** El frontend NO está enviando el token JWT en los requests, por lo que el backend no puede identificar al usuario autenticado.

---

## 📋 Problema Identificado en Logs

```
✅ User logged in successfully: iriyidan@gmail.com  ← Login exitoso
🔍 Attempting to get user_id from RFX: b11b67b7...  ← NO hay JWT token
❌ No user_id available from any source            ← Error porque no encuentra user_id
```

**Causa:** El frontend guarda el token pero NO lo envía en los requests subsiguientes.

---

## ✅ Solución: Enviar JWT Token en Todos los Requests

### 1. **Guardar Token Después del Login**

```javascript
// Después del login exitoso
const loginResponse = await fetch('http://localhost:5001/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password })
});

const data = await loginResponse.json();

if (data.status === 'success') {
    // ✅ GUARDAR TOKEN
    localStorage.setItem('access_token', data.access_token);
    localStorage.setItem('refresh_token', data.refresh_token);
    localStorage.setItem('user', JSON.stringify(data.user));
    
    console.log('✅ Token guardado:', data.access_token);
}
```

### 2. **Enviar Token en TODOS los Requests**

#### **Opción A: Manualmente en cada request**

```javascript
// ❌ ANTES - Sin token
const response = await fetch('http://localhost:5001/api/proposals/generate', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({ rfx_id: 'abc-123' })
});

// ✅ DESPUÉS - Con token
const token = localStorage.getItem('access_token');
const response = await fetch('http://localhost:5001/api/proposals/generate', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`  // ⭐ AGREGAR ESTO
    },
    body: JSON.stringify({ rfx_id: 'abc-123' })
});
```

#### **Opción B: Interceptor Global (RECOMENDADO)**

```javascript
// utils/api.js - Crear función helper
export async function apiRequest(url, options = {}) {
    const token = localStorage.getItem('access_token');
    
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers
    };
    
    // ⭐ Agregar token automáticamente si existe
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    
    const response = await fetch(url, {
        ...options,
        headers
    });
    
    // Manejar token expirado
    if (response.status === 401) {
        // Token expirado - intentar refresh
        const refreshed = await refreshToken();
        if (refreshed) {
            // Reintentar request con nuevo token
            headers['Authorization'] = `Bearer ${localStorage.getItem('access_token')}`;
            return fetch(url, { ...options, headers });
        } else {
            // Redirect a login
            window.location.href = '/login';
        }
    }
    
    return response;
}

// Función para refresh token
async function refreshToken() {
    const refreshToken = localStorage.getItem('refresh_token');
    if (!refreshToken) return false;
    
    try {
        const response = await fetch('http://localhost:5001/api/auth/refresh', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh_token: refreshToken })
        });
        
        if (response.ok) {
            const data = await response.json();
            localStorage.setItem('access_token', data.access_token);
            return true;
        }
    } catch (error) {
        console.error('Error refreshing token:', error);
    }
    
    return false;
}

// USO:
import { apiRequest } from './utils/api';

// Generar propuesta
const response = await apiRequest('http://localhost:5001/api/proposals/generate', {
    method: 'POST',
    body: JSON.stringify({ rfx_id: 'abc-123' })
});
```

#### **Opción C: Axios Interceptor (si usas Axios)**

```javascript
// utils/axios.js
import axios from 'axios';

const api = axios.create({
    baseURL: 'http://localhost:5001',
    headers: {
        'Content-Type': 'application/json'
    }
});

// ⭐ Interceptor para agregar token automáticamente
api.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('access_token');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => Promise.reject(error)
);

// Interceptor para manejar token expirado
api.interceptors.response.use(
    (response) => response,
    async (error) => {
        const originalRequest = error.config;
        
        if (error.response?.status === 401 && !originalRequest._retry) {
            originalRequest._retry = true;
            
            const refreshToken = localStorage.getItem('refresh_token');
            if (refreshToken) {
                try {
                    const response = await axios.post('/api/auth/refresh', {
                        refresh_token: refreshToken
                    });
                    
                    const { access_token } = response.data;
                    localStorage.setItem('access_token', access_token);
                    
                    originalRequest.headers.Authorization = `Bearer ${access_token}`;
                    return api(originalRequest);
                } catch (refreshError) {
                    // Redirect a login
                    window.location.href = '/login';
                    return Promise.reject(refreshError);
                }
            }
        }
        
        return Promise.reject(error);
    }
);

export default api;

// USO:
import api from './utils/axios';

// Generar propuesta
const response = await api.post('/api/proposals/generate', {
    rfx_id: 'abc-123'
});
```

---

## 🔧 Solución Temporal: Endpoint de Migración

Mientras actualizas el frontend, puedes usar este endpoint para asignar `user_id` a tus RFX:

```bash
# 1. Login para obtener token
curl -X POST http://localhost:5001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "iriyidan@gmail.com",
    "password": "tu-password"
  }'

# Respuesta:
# {
#   "access_token": "eyJ0eXAiOiJKV1Q...",
#   "user": { "id": "186ea35f-3cf8-480f-a7d3-0af178c09498" }
# }

# 2. Migrar RFX sin user_id (asigna automáticamente al usuario autenticado)
curl -X POST http://localhost:5001/api/rfx-secure/migrate-user-id \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1Q..."

# Respuesta:
# {
#   "status": "success",
#   "message": "Migrated 5 RFX records to user 186ea35f-3cf8-480f-a7d3-0af178c09498"
# }
```

O desde el frontend:

```javascript
async function migrateMyRFX() {
    const token = localStorage.getItem('access_token');
    
    const response = await fetch('http://localhost:5001/api/rfx-secure/migrate-user-id', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        }
    });
    
    const data = await response.json();
    console.log('✅ Migración completada:', data);
}
```

---

## 📊 Verificar que el Token se Está Enviando

### En el Browser DevTools:

1. Abrir **DevTools** (F12)
2. Ir a **Network** tab
3. Hacer un request (ej: generar propuesta)
4. Click en el request
5. Ver **Headers** → **Request Headers**
6. Verificar que existe: `Authorization: Bearer eyJ0eXAiOiJKV1Q...`

### Logs Esperados en Backend:

```
✅ Authenticated user generating proposal: iriyidan@gmail.com (ID: 186ea35f-3cf8-480f-a7d3-0af178c09498)
🎯 Final user_id for proposal generation: 186ea35f-3cf8-480f-a7d3-0af178c09498
✅ Generating proposal for user: 186ea35f-3cf8-480f-a7d3-0af178c09498
```

---

## 🚨 Errores Comunes

### Error 1: Token No Se Guarda
```javascript
// ❌ MAL - No guarda el token
const data = await response.json();
console.log(data.access_token); // Solo imprime

// ✅ BIEN - Guarda en localStorage
localStorage.setItem('access_token', data.access_token);
```

### Error 2: Token Se Guarda Pero No Se Envía
```javascript
// ❌ MAL - Token guardado pero no enviado
headers: {
    'Content-Type': 'application/json'
    // Falta Authorization header
}

// ✅ BIEN - Token enviado
headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
}
```

### Error 3: Formato Incorrecto del Header
```javascript
// ❌ MAL - Sin "Bearer"
'Authorization': token

// ❌ MAL - Sin espacio
'Authorization': `Bearer${token}`

// ✅ BIEN - Formato correcto
'Authorization': `Bearer ${token}`
```

---

## ✅ Checklist de Implementación

- [ ] **Login guarda token** en localStorage
- [ ] **Todos los requests** incluyen `Authorization: Bearer <token>`
- [ ] **Interceptor global** agrega token automáticamente
- [ ] **Manejo de token expirado** con refresh token
- [ ] **Logout limpia** localStorage
- [ ] **Verificado en DevTools** que el header se envía

---

## 🎯 Ejemplo Completo de Flujo

```javascript
// 1. LOGIN
async function login(email, password) {
    const response = await fetch('http://localhost:5001/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
    });
    
    const data = await response.json();
    
    if (data.status === 'success') {
        localStorage.setItem('access_token', data.access_token);
        localStorage.setItem('refresh_token', data.refresh_token);
        localStorage.setItem('user', JSON.stringify(data.user));
        return true;
    }
    
    return false;
}

// 2. GENERAR PROPUESTA (con token)
async function generateProposal(rfxId) {
    const token = localStorage.getItem('access_token');
    
    if (!token) {
        console.error('❌ No hay token - usuario no autenticado');
        window.location.href = '/login';
        return;
    }
    
    const response = await fetch('http://localhost:5001/api/proposals/generate', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`  // ⭐ CRÍTICO
        },
        body: JSON.stringify({
            rfx_id: rfxId,
            costs: [5.0, 6.0, 4.0]
        })
    });
    
    if (response.status === 401) {
        // Token expirado
        console.warn('⚠️ Token expirado, intentando refresh...');
        const refreshed = await refreshToken();
        if (refreshed) {
            // Reintentar
            return generateProposal(rfxId);
        } else {
            window.location.href = '/login';
        }
    }
    
    const data = await response.json();
    return data;
}

// 3. LOGOUT
function logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
    window.location.href = '/login';
}
```

---

## 🔗 Referencias

- **Backend Auth Middleware:** `backend/utils/auth_middleware.py`
- **Backend Auth Endpoints:** `backend/api/auth_flask.py`
- **Documentación JWT:** https://jwt.io/

---

## ⚡ Acción Inmediata

**Ejecuta esto en la consola del browser (DevTools) para migrar tus RFX:**

```javascript
// Copiar y pegar en la consola del browser
(async () => {
    const token = localStorage.getItem('access_token');
    if (!token) {
        console.error('❌ No hay token guardado. Haz login primero.');
        return;
    }
    
    const response = await fetch('http://localhost:5001/api/rfx-secure/migrate-user-id', {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${token}`
        }
    });
    
    const data = await response.json();
    console.log('✅ Resultado:', data);
})();
```

Luego, **actualiza tu código frontend** para enviar el token en todos los requests.
