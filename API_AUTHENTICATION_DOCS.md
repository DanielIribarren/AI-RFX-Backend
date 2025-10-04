# 🔐 API de Autenticación - Documentación Frontend

**Base URL:** `http://localhost:5001/api/auth`  
**Versión:** V3.0 MVP  
**Autenticación:** JWT Bearer Token

---

## 📋 **Tabla de Contenidos**

1. [Endpoints Públicos (Sin Token)](#endpoints-públicos)
   - [Registro de Usuario](#1-registro-signup)
   - [Login](#2-login)
   - [Verificar Email](#3-verificar-email)
   - [Solicitar Reset de Contraseña](#4-solicitar-reset-de-contraseña)
   - [Confirmar Reset de Contraseña](#5-confirmar-reset-de-contraseña)
   - [Health Check](#6-health-check)

2. [Endpoints Protegidos (Requieren Token)](#endpoints-protegidos)
   - [Obtener Usuario Actual](#7-obtener-usuario-actual-me)
   - [Refresh Token](#8-refresh-token)
   - [Reenviar Verificación de Email](#9-reenviar-verificación)
   - [Actualizar Perfil](#10-actualizar-perfil)
   - [Cambiar Contraseña](#11-cambiar-contraseña)

3. [Modelos de Datos](#modelos-de-datos)
4. [Manejo de Errores](#manejo-de-errores)
5. [Ejemplos de Integración Frontend](#ejemplos-frontend)

---

## 🌐 **Endpoints Públicos**

### **1. Registro (Signup)**

Crear una nueva cuenta de usuario.

**Endpoint:** `POST /api/auth/signup`

**Request Body:**
```json
{
  "email": "usuario@ejemplo.com",
  "password": "miPassword123",
  "full_name": "Juan Pérez",
  "company_name": "Mi Empresa S.A." // Opcional
}
```

**Response (201 Created):**
```json
{
  "status": "success",
  "message": "User registered successfully. Please verify your email.",
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "usuario@ejemplo.com",
    "full_name": "Juan Pérez",
    "company_name": "Mi Empresa S.A.",
    "status": "pending_verification",
    "email_verified": false,
    "created_at": "2024-10-04T12:00:00Z"
  }
}
```

**Errores Comunes:**
- `400` - Email ya registrado
- `400` - Datos de validación incorrectos
- `500` - Error interno del servidor

**Validaciones:**
- Email: Formato válido, único
- Password: Mínimo 6 caracteres
- Full Name: Mínimo 2 caracteres

---

### **2. Login**

Iniciar sesión con credenciales.

**Endpoint:** `POST /api/auth/login`

**Request Body:**
```json
{
  "email": "usuario@ejemplo.com",
  "password": "miPassword123"
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in": 604800,
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "usuario@ejemplo.com",
    "full_name": "Juan Pérez",
    "company_name": "Mi Empresa S.A.",
    "status": "active",
    "email_verified": true,
    "last_login_at": "2024-10-04T12:00:00Z"
  }
}
```

**Errores Comunes:**
- `401` - Credenciales inválidas
- `401` - Usuario no encontrado
- `403` - Cuenta bloqueada (demasiados intentos fallidos)

---

### **3. Verificar Email**

Verificar email usando token enviado por correo.

**Endpoint:** `POST /api/auth/verify-email`

**Request Body:**
```json
{
  "token": "abc123def456..."
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Email verified successfully"
}
```

**Errores Comunes:**
- `400` - Token inválido o expirado
- `404` - Token no encontrado

---

### **4. Solicitar Reset de Contraseña**

Enviar email con link para resetear contraseña.

**Endpoint:** `POST /api/auth/forgot-password`

**Request Body:**
```json
{
  "email": "usuario@ejemplo.com"
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Password reset email sent. Check your inbox."
}
```

**Nota:** Siempre retorna 200 aunque el email no exista (seguridad).

---

### **5. Confirmar Reset de Contraseña**

Establecer nueva contraseña usando token.

**Endpoint:** `POST /api/auth/reset-password`

**Request Body:**
```json
{
  "token": "abc123def456...",
  "new_password": "nuevaPassword456"
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Password reset successfully. You can now login."
}
```

**Errores Comunes:**
- `400` - Token inválido o expirado
- `400` - Password no cumple requisitos

---

### **6. Health Check**

Verificar estado del servicio de autenticación.

**Endpoint:** `GET /api/auth/health`

**Response (200 OK):**
```json
{
  "status": "healthy",
  "service": "authentication",
  "timestamp": "2024-10-04T12:00:00Z"
}
```

---

## 🔒 **Endpoints Protegidos**

**Todos estos endpoints requieren el header:**
```
Authorization: Bearer <access_token>
```

### **7. Obtener Usuario Actual (Me)**

Obtener información del usuario autenticado.

**Endpoint:** `GET /api/auth/me`

**Headers:**
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response (200 OK):**
```json
{
  "status": "success",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "usuario@ejemplo.com",
    "full_name": "Juan Pérez",
    "company_name": "Mi Empresa S.A.",
    "phone": "+1234567890",
    "status": "active",
    "email_verified": true,
    "email_verified_at": "2024-10-01T10:00:00Z",
    "last_login_at": "2024-10-04T12:00:00Z",
    "created_at": "2024-09-01T08:00:00Z",
    "updated_at": "2024-10-04T12:00:00Z"
  }
}
```

**Errores Comunes:**
- `401` - Token inválido o expirado
- `404` - Usuario no encontrado

---

### **8. Refresh Token**

Obtener nuevo access token usando refresh token.

**Endpoint:** `POST /api/auth/refresh`

**Request Body:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in": 604800
}
```

**Errores Comunes:**
- `401` - Refresh token inválido o expirado

---

### **9. Reenviar Verificación**

Reenviar email de verificación.

**Endpoint:** `POST /api/auth/resend-verification`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Verification email sent. Check your inbox."
}
```

**Errores Comunes:**
- `400` - Email ya verificado
- `429` - Demasiadas solicitudes (rate limit)

---

### **10. Actualizar Perfil**

Actualizar información del usuario.

**Endpoint:** `PUT /api/auth/profile`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request Body:**
```json
{
  "full_name": "Juan Carlos Pérez",
  "company_name": "Nueva Empresa S.A.",
  "phone": "+1234567890"
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Profile updated successfully",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "usuario@ejemplo.com",
    "full_name": "Juan Carlos Pérez",
    "company_name": "Nueva Empresa S.A.",
    "phone": "+1234567890",
    "updated_at": "2024-10-04T12:30:00Z"
  }
}
```

---

### **11. Cambiar Contraseña**

Cambiar contraseña del usuario autenticado.

**Endpoint:** `POST /api/auth/change-password`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request Body:**
```json
{
  "current_password": "passwordActual123",
  "new_password": "nuevoPassword456"
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Password changed successfully"
}
```

**Errores Comunes:**
- `401` - Contraseña actual incorrecta
- `400` - Nueva contraseña no cumple requisitos

---

## 📦 **Modelos de Datos**

### **User Object**
```typescript
interface User {
  id: string;                    // UUID
  email: string;                 // Email único
  full_name: string;             // Nombre completo
  company_name?: string;         // Nombre de empresa (opcional)
  phone?: string;                // Teléfono (opcional)
  status: 'active' | 'inactive' | 'pending_verification';
  email_verified: boolean;
  email_verified_at?: string;    // ISO 8601 timestamp
  last_login_at?: string;        // ISO 8601 timestamp
  created_at: string;            // ISO 8601 timestamp
  updated_at: string;            // ISO 8601 timestamp
}
```

### **Auth Response**
```typescript
interface AuthResponse {
  status: 'success' | 'error';
  message?: string;
  access_token?: string;
  refresh_token?: string;
  expires_in?: number;           // Segundos
  user?: User;
}
```

### **Error Response**
```typescript
interface ErrorResponse {
  status: 'error';
  message: string;
  error?: string;                // Detalle técnico
  errors?: string[];             // Lista de errores de validación
}
```

---

## ⚠️ **Manejo de Errores**

### **Códigos de Estado HTTP**

| Código | Significado | Acción Recomendada |
|--------|-------------|-------------------|
| `200` | OK | Continuar |
| `201` | Created | Usuario creado exitosamente |
| `400` | Bad Request | Mostrar errores de validación |
| `401` | Unauthorized | Redirigir a login |
| `403` | Forbidden | Mostrar mensaje de acceso denegado |
| `404` | Not Found | Recurso no encontrado |
| `429` | Too Many Requests | Esperar antes de reintentar |
| `500` | Internal Server Error | Mostrar error genérico |

### **Ejemplo de Error Response**
```json
{
  "status": "error",
  "message": "Validation failed",
  "errors": [
    "Email is required",
    "Password must be at least 6 characters"
  ]
}
```

---

## 💻 **Ejemplos de Integración Frontend**

### **React/TypeScript - Auth Service**

```typescript
// services/authService.ts
import axios from 'axios';

const API_BASE_URL = 'http://localhost:5000/api/auth';

// Configurar axios con interceptores
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor para agregar token automáticamente
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Interceptor para manejar errores 401 (token expirado)
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      // Intentar refresh token
      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        try {
          const { data } = await axios.post(`${API_BASE_URL}/refresh`, {
            refresh_token: refreshToken,
          });
          localStorage.setItem('access_token', data.access_token);
          // Reintentar request original
          error.config.headers.Authorization = `Bearer ${data.access_token}`;
          return axios(error.config);
        } catch {
          // Refresh falló, redirigir a login
          localStorage.clear();
          window.location.href = '/login';
        }
      }
    }
    return Promise.reject(error);
  }
);

export const authService = {
  // Signup
  async signup(email: string, password: string, fullName: string, companyName?: string) {
    const { data } = await api.post('/signup', {
      email,
      password,
      full_name: fullName,
      company_name: companyName,
    });
    
    // Guardar tokens
    localStorage.setItem('access_token', data.access_token);
    if (data.refresh_token) {
      localStorage.setItem('refresh_token', data.refresh_token);
    }
    
    return data;
  },

  // Login
  async login(email: string, password: string) {
    const { data } = await api.post('/login', { email, password });
    
    // Guardar tokens
    localStorage.setItem('access_token', data.access_token);
    localStorage.setItem('refresh_token', data.refresh_token);
    
    return data;
  },

  // Logout
  logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    window.location.href = '/login';
  },

  // Get current user
  async getCurrentUser() {
    const { data } = await api.get('/me');
    return data.user;
  },

  // Forgot password
  async forgotPassword(email: string) {
    const { data } = await api.post('/forgot-password', { email });
    return data;
  },

  // Reset password
  async resetPassword(token: string, newPassword: string) {
    const { data } = await api.post('/reset-password', {
      token,
      new_password: newPassword,
    });
    return data;
  },

  // Verify email
  async verifyEmail(token: string) {
    const { data } = await api.post('/verify-email', { token });
    return data;
  },

  // Update profile
  async updateProfile(updates: Partial<User>) {
    const { data } = await api.put('/profile', updates);
    return data.user;
  },

  // Change password
  async changePassword(currentPassword: string, newPassword: string) {
    const { data } = await api.post('/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    });
    return data;
  },

  // Check if user is authenticated
  isAuthenticated(): boolean {
    return !!localStorage.getItem('access_token');
  },
};
```

---

### **React - Auth Context**

```typescript
// contexts/AuthContext.tsx
import React, { createContext, useContext, useState, useEffect } from 'react';
import { authService } from '../services/authService';

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string, fullName: string) => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Cargar usuario al iniciar
    const loadUser = async () => {
      if (authService.isAuthenticated()) {
        try {
          const currentUser = await authService.getCurrentUser();
          setUser(currentUser);
        } catch (error) {
          console.error('Failed to load user:', error);
          authService.logout();
        }
      }
      setLoading(false);
    };

    loadUser();
  }, []);

  const login = async (email: string, password: string) => {
    const response = await authService.login(email, password);
    setUser(response.user);
  };

  const signup = async (email: string, password: string, fullName: string) => {
    const response = await authService.signup(email, password, fullName);
    setUser(response.user);
  };

  const logout = () => {
    authService.logout();
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        login,
        signup,
        logout,
        isAuthenticated: !!user,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};
```

---

### **React - Protected Route**

```typescript
// components/ProtectedRoute.tsx
import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

interface ProtectedRouteProps {
  children: React.ReactNode;
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return <div>Loading...</div>;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
};
```

---

### **React - Login Component**

```typescript
// pages/Login.tsx
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

export const Login: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await login(email, password);
      navigate('/dashboard');
    } catch (err: any) {
      setError(err.response?.data?.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <h1>Login</h1>
      <form onSubmit={handleSubmit}>
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        {error && <div className="error">{error}</div>}
        <button type="submit" disabled={loading}>
          {loading ? 'Loading...' : 'Login'}
        </button>
      </form>
    </div>
  );
};
```

---

### **Vue.js - Composable**

```typescript
// composables/useAuth.ts
import { ref, computed } from 'vue';
import { authService } from '../services/authService';

const user = ref<User | null>(null);
const loading = ref(false);

export const useAuth = () => {
  const isAuthenticated = computed(() => !!user.value);

  const login = async (email: string, password: string) => {
    loading.value = true;
    try {
      const response = await authService.login(email, password);
      user.value = response.user;
    } finally {
      loading.value = false;
    }
  };

  const logout = () => {
    authService.logout();
    user.value = null;
  };

  const loadUser = async () => {
    if (authService.isAuthenticated()) {
      try {
        user.value = await authService.getCurrentUser();
      } catch (error) {
        logout();
      }
    }
  };

  return {
    user,
    loading,
    isAuthenticated,
    login,
    logout,
    loadUser,
  };
};
```

---

## 🔑 **Flujo de Autenticación Recomendado**

### **1. Registro y Login**
```
Usuario → Signup → Recibe access_token + refresh_token
       → Guardar tokens en localStorage
       → Redirigir a dashboard
       → (Opcional) Mostrar mensaje "Verifica tu email"
```

### **2. Navegación con Token**
```
Cada request → Interceptor agrega "Authorization: Bearer <token>"
            → Si 401: Intentar refresh token
            → Si refresh falla: Logout y redirigir a login
```

### **3. Refresh Token**
```
Token expira (7 días) → Usar refresh_token para obtener nuevo access_token
                      → Actualizar localStorage
                      → Continuar navegación
```

### **4. Logout**
```
Usuario → Logout → Limpiar localStorage
                → Redirigir a login
```

---

## 📝 **Notas Importantes**

1. **Tokens:**
   - `access_token`: Válido por 7 días (configurable)
   - `refresh_token`: Válido por 30 días
   - Guardar en `localStorage` o `sessionStorage`

2. **Seguridad:**
   - Siempre usar HTTPS en producción
   - No exponer tokens en URLs
   - Implementar CSRF protection si usas cookies
   - Rate limiting está implementado en el backend

3. **Email Verification:**
   - Los usuarios pueden usar la app sin verificar email
   - Algunas funciones pueden requerir verificación
   - Reenviar verificación si es necesario

4. **Password Requirements:**
   - Mínimo 6 caracteres
   - Se recomienda incluir mayúsculas y números
   - Máximo 72 caracteres (limitación de bcrypt)

5. **Status de Usuario:**
   - `pending_verification`: Recién registrado
   - `active`: Email verificado y cuenta activa
   - `inactive`: Cuenta desactivada

---

## 🚀 **Testing Rápido con cURL**

```bash
# Signup
curl -X POST http://localhost:5000/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@ejemplo.com","password":"test123","full_name":"Test User"}'

# Login
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@ejemplo.com","password":"test123"}'

# Get User (reemplazar TOKEN)
curl -X GET http://localhost:5000/api/auth/me \
  -H "Authorization: Bearer <TOKEN>"
```

---

## 📞 **Soporte**

Para problemas o preguntas sobre la API:
- Revisar logs del backend en `backend/logs/`
- Verificar que el servidor esté corriendo en puerto 5000
- Confirmar que la base de datos esté configurada correctamente

**¡Listo para integrar en tu frontend! 🎉**
