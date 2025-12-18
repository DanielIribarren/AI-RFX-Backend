# 🔧 Solución: Error 401 en Endpoints de Organizaciones

**Fecha:** 16 de Diciembre, 2025  
**Problema:** Endpoints retornan 401 Unauthorized  
**Causa:** Frontend NO está enviando el token JWT en el header `Authorization`

---

## 🎯 Diagnóstico

### Logs del Backend:
```
2025-12-16 12:54:49 - werkzeug - INFO - 127.0.0.1 - - [16/Dec/2025 12:54:49] "GET /api/organization/current HTTP/1.1" 401 -
2025-12-16 12:57:58 - werkzeug - INFO - 127.0.0.1 - - [16/Dec/2025 12:57:58] "GET /api/credits/info HTTP/1.1" 401 -
2025-12-16 12:57:58 - werkzeug - INFO - 127.0.0.1 - - [16/Dec/2025 12:57:58] "GET /api/organization/members HTTP/1.1" 401 -
```

### Causa Raíz:
El backend está funcionando **correctamente**. El problema es que el frontend está haciendo requests sin el header `Authorization: Bearer <token>`.

---

## ✅ Solución para el Frontend

### 1. Verificar que el Token Existe

```javascript
// Obtener token del localStorage/sessionStorage
const token = localStorage.getItem('authToken');

if (!token) {
  console.error('❌ No JWT token found!');
  // Redirigir a login
  window.location.href = '/login';
}
```

### 2. Agregar Header Authorization en TODAS las Peticiones

**Opción A: Manualmente en cada fetch**
```javascript
const response = await fetch('/api/organization/current', {
  method: 'GET',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
});
```

**Opción B: Crear función helper (RECOMENDADO)**
```javascript
// utils/api.js
export async function authenticatedFetch(url, options = {}) {
  const token = localStorage.getItem('authToken');
  
  if (!token) {
    throw new Error('No authentication token found');
  }
  
  const headers = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
    ...options.headers
  };
  
  return fetch(url, {
    ...options,
    headers
  });
}

// Uso:
const response = await authenticatedFetch('/api/organization/current');
```

**Opción C: Interceptor Global (MEJOR PRÁCTICA)**
```javascript
// Si usas Axios:
import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:5001'
});

// Interceptor que agrega el token automáticamente
api.interceptors.request.use(
  config => {
    const token = localStorage.getItem('authToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  error => Promise.reject(error)
);

// Uso:
const response = await api.get('/api/organization/current');
```

### 3. Verificar el Token en DevTools

**Abrir Chrome DevTools → Network Tab:**
1. Hacer request a `/api/organization/current`
2. Click en el request
3. Ver "Request Headers"
4. Verificar que existe: `Authorization: Bearer eyJhbGc...`

**Si NO aparece el header:**
- ❌ El frontend no está enviando el token
- ✅ Implementar una de las soluciones arriba

**Si aparece el header pero sigue dando 401:**
- El token puede estar expirado
- El token puede ser inválido
- Verificar en backend logs el error específico

---

## 🧪 Endpoint de Prueba (Sin Autenticación)

He creado un endpoint de prueba para verificar que el backend funciona:

```bash
# Este endpoint NO requiere autenticación
GET http://localhost:5001/api/organization/test
```

**Respuesta esperada:**
```json
{
  "status": "success",
  "message": "✅ Backend is working! This is a test endpoint without authentication.",
  "note": "For production, use /api/organization/current with JWT token",
  "data": {
    "id": "8ed7f53e-86c7-4dec-861b-822b8a25ed6d",
    "name": "Sabra Corporation",
    "plan": { ... },
    "usage": { ... }
  }
}
```

**Prueba en terminal:**
```bash
curl http://localhost:5001/api/organization/test
```

Si este endpoint funciona (200 OK), confirma que el backend está bien y el problema es la autenticación del frontend.

---

## 📋 Checklist de Implementación

### Para el Frontend Developer:

- [ ] **Verificar que el token se guarda después del login**
  ```javascript
  // Después de login exitoso:
  localStorage.setItem('authToken', response.data.token);
  ```

- [ ] **Implementar función helper o interceptor**
  - Opción recomendada: Interceptor global con Axios

- [ ] **Actualizar TODAS las llamadas a la API**
  - `/api/organization/current`
  - `/api/organization/members`
  - `/api/credits/info`
  - `/api/credits/history`
  - Cualquier otro endpoint protegido

- [ ] **Manejar token expirado (401)**
  ```javascript
  if (response.status === 401) {
    // Token expirado o inválido
    localStorage.removeItem('authToken');
    window.location.href = '/login';
  }
  ```

- [ ] **Verificar en DevTools que el header se envía**
  - Network tab → Request Headers → Authorization

- [ ] **Probar endpoint de prueba primero**
  ```javascript
  // Debe funcionar sin token:
  fetch('http://localhost:5001/api/organization/test')
  
  // Debe fallar sin token (401):
  fetch('http://localhost:5001/api/organization/current')
  
  // Debe funcionar con token (200):
  fetch('http://localhost:5001/api/organization/current', {
    headers: { 'Authorization': `Bearer ${token}` }
  })
  ```

---

## 🚨 Errores Comunes

### Error 1: "Authorization header missing"
```json
{
  "status": "error",
  "message": "Authentication required",
  "error": "Missing Authorization header"
}
```
**Solución:** Agregar header `Authorization: Bearer <token>`

### Error 2: "Invalid or expired token"
```json
{
  "status": "error",
  "message": "Invalid or expired token"
}
```
**Solución:** Token expirado, hacer login nuevamente

### Error 3: "User not found"
```json
{
  "status": "error",
  "message": "User not found"
}
```
**Solución:** El user_id del token no existe en la BD

### Error 4: "User has no organization assigned"
```json
{
  "status": "error",
  "message": "User has no organization assigned"
}
```
**Solución:** El usuario no tiene `organization_id` en la tabla `users`

---

## 📊 Ejemplo Completo de Integración

```javascript
// api.js - Configuración centralizada
import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5001';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000
});

// Interceptor para agregar token automáticamente
api.interceptors.request.use(
  config => {
    const token = localStorage.getItem('authToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  error => Promise.reject(error)
);

// Interceptor para manejar errores de autenticación
api.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      // Token inválido o expirado
      localStorage.removeItem('authToken');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;

// organizationService.js - Servicio de organizaciones
import api from './api';

export const organizationService = {
  async getCurrent() {
    const response = await api.get('/api/organization/current');
    return response.data;
  },
  
  async getMembers() {
    const response = await api.get('/api/organization/members');
    return response.data;
  },
  
  async getPlans() {
    const response = await api.get('/api/organization/plans');
    return response.data;
  }
};

// creditsService.js - Servicio de créditos
import api from './api';

export const creditsService = {
  async getInfo() {
    const response = await api.get('/api/credits/info');
    return response.data;
  },
  
  async getHistory(limit = 50, offset = 0) {
    const response = await api.get(`/api/credits/history?limit=${limit}&offset=${offset}`);
    return response.data;
  }
};

// App.jsx - Uso en componente
import { useEffect, useState } from 'react';
import { organizationService, creditsService } from './services';

function Dashboard() {
  const [organization, setOrganization] = useState(null);
  const [credits, setCredits] = useState(null);
  
  useEffect(() => {
    loadData();
  }, []);
  
  async function loadData() {
    try {
      // Cargar organización
      const orgData = await organizationService.getCurrent();
      setOrganization(orgData.data);
      
      // Cargar créditos
      const creditsData = await creditsService.getInfo();
      setCredits(creditsData.data);
      
    } catch (error) {
      console.error('Error loading data:', error);
      // El interceptor ya manejó el 401
    }
  }
  
  return (
    <div>
      <h1>{organization?.name}</h1>
      <p>Plan: {organization?.plan?.name}</p>
      <p>Créditos: {credits?.credits_available} / {credits?.credits_total}</p>
    </div>
  );
}
```

---

## 🔍 Debugging

### Ver el token decodificado:
```javascript
// En consola del navegador:
const token = localStorage.getItem('authToken');
const payload = JSON.parse(atob(token.split('.')[1]));
console.log('Token payload:', payload);
console.log('User ID:', payload.sub);
console.log('Expires:', new Date(payload.exp * 1000));
```

### Verificar que el token no está expirado:
```javascript
const payload = JSON.parse(atob(token.split('.')[1]));
const isExpired = Date.now() >= payload.exp * 1000;
console.log('Token expired?', isExpired);
```

---

## ✅ Estado del Backend

**Backend está funcionando correctamente:**
- ✅ Autenticación JWT implementada
- ✅ Middleware de organizaciones funcionando
- ✅ Endpoints protegidos correctamente
- ✅ Endpoint de prueba `/api/organization/test` disponible

**El problema está en el frontend:**
- ❌ No envía header `Authorization`
- ❌ Necesita implementar una de las soluciones arriba

---

## 📞 Soporte

Si después de implementar estas soluciones sigues teniendo problemas:

1. Verificar en DevTools que el header `Authorization` se envía
2. Verificar que el token no está expirado
3. Probar el endpoint `/api/organization/test` (debe funcionar sin token)
4. Revisar logs del backend para errores específicos
5. Contactar al equipo de backend con el `correlation_id` del error

---

**Documentación creada:** 16 de Diciembre, 2025  
**Versión:** 1.0  
**Estado:** ✅ Backend funcionando - Frontend necesita implementar autenticación
