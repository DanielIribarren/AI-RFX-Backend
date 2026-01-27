# 🔄 Sistema de Refresh Selectivo - Chat RFX

**Versión:** 1.0  
**Fecha:** 13 de Enero, 2026  
**Propósito:** Actualizar componentes específicos del frontend cuando el chat hace cambios, sin recargar toda la página

---

## 📋 Resumen Ejecutivo

El sistema de refresh selectivo permite que el frontend actualice **solo los componentes afectados** cuando el chat hace cambios al RFX, mejorando la UX con actualizaciones instantáneas y eficientes.

### Beneficios

✅ **UX Mejorada:** Actualizaciones instantáneas sin recargar página  
✅ **Performance:** Solo refresca lo necesario (no todo el RFX)  
✅ **Eficiencia:** Menos llamadas a la API  
✅ **Simplicidad:** Backend indica qué refrescar, frontend solo ejecuta  

---

## 🏗️ Arquitectura

```
Usuario envía mensaje al chat
         ↓
Backend procesa con IA
         ↓
Detecta cambios aplicados
         ↓
Determina qué componentes necesitan refresh
         ↓
Retorna respuesta con metadata de refresh
         ↓
Frontend actualiza solo componentes afectados
```

---

## 📡 API - Endpoint POST /chat

### Request

```http
POST /api/rfx/{rfx_id}/chat
Authorization: Bearer <jwt_token>
Content-Type: multipart/form-data

message: "Agrega 10 sillas a $50 cada una"
context: {"current_products": [...], "current_total": 0}
files: [archivo1.xlsx, archivo2.pdf]  # Opcional
```

### Response (ACTUALIZADA)

```json
{
  "status": "success",
  "message": "✅ He agregado 10 sillas a $50 cada una.",
  "confidence": 0.95,
  "changes": [
    {
      "type": "add_product",
      "target": "new",
      "data": {
        "nombre": "Sillas",
        "cantidad": 10,
        "precio": 50,
        "unidad": "unidades"
      },
      "description": "Agregado: Sillas (10 unidades)"
    }
  ],
  "requires_confirmation": false,
  "refresh": {
    "needs_refresh": true,
    "scope": "products",
    "components": ["products", "pricing", "totals"]
  }
}
```

### Campos de Refresh

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `refresh.needs_refresh` | `boolean` | `true` si se necesita refrescar algo |
| `refresh.scope` | `string` | Alcance: `"none"`, `"products"`, `"details"`, `"full"` |
| `refresh.components` | `string[]` | Lista específica de componentes a refrescar |

---

## 🎯 Tipos de Cambios y Refresh

### 1. Cambios en Productos

**Tipos:** `add_product`, `update_product`, `delete_product`

**Refresh:**
```json
{
  "needs_refresh": true,
  "scope": "products",
  "components": ["products", "pricing", "totals"]
}
```

**Razón:** Cambios en productos requieren recalcular pricing y totales.

---

### 2. Cambios en Detalles del RFX

**Tipo:** `update_field`

**Refresh (Fecha/Lugar):**
```json
{
  "needs_refresh": true,
  "scope": "details",
  "components": ["details"]
}
```

**Refresh (Cliente):**
```json
{
  "needs_refresh": true,
  "scope": "details",
  "components": ["header"]
}
```

**Razón:** Solo actualizar el componente específico afectado.

---

### 3. Sin Cambios

**Refresh:**
```json
{
  "needs_refresh": false,
  "scope": "none",
  "components": []
}
```

**Razón:** El chat solo respondió una pregunta, no hizo cambios.

---

## 💻 Implementación Frontend

### Opción A: Actualización Optimista (Recomendado)

```typescript
async function handleChatMessage(message: string, context: any) {
  // 1. Enviar mensaje al chat
  const response = await fetch(`/api/rfx/${rfxId}/chat`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${getAuthToken()}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ message, context })
  });
  
  const data = await response.json();
  
  // 2. Aplicar cambios al estado local inmediatamente
  applyChangesToLocalState(data.changes);
  
  // 3. Refrescar solo si es necesario
  if (data.refresh.needs_refresh) {
    await refreshComponents(data.refresh.components);
  }
  
  return data;
}

function applyChangesToLocalState(changes: Change[]) {
  for (const change of changes) {
    switch (change.type) {
      case 'add_product':
        // Agregar producto al estado local
        setProducts(prev => [...prev, change.data]);
        break;
        
      case 'update_product':
        // Actualizar producto en estado local
        setProducts(prev => 
          prev.map(p => p.id === change.target ? { ...p, ...change.data } : p)
        );
        break;
        
      case 'delete_product':
        // Eliminar producto del estado local
        setProducts(prev => prev.filter(p => p.id !== change.target));
        break;
        
      case 'update_field':
        // Actualizar campo del RFX
        setRfxDetails(prev => ({ ...prev, [change.target]: change.data }));
        break;
    }
  }
}

async function refreshComponents(components: string[]) {
  // Solo refrescar componentes específicos
  const refreshPromises = components.map(component => {
    switch (component) {
      case 'products':
        return refreshProducts();
      case 'pricing':
        return refreshPricing();
      case 'totals':
        return refreshTotals();
      case 'details':
        return refreshDetails();
      case 'header':
        return refreshHeader();
      default:
        return Promise.resolve();
    }
  });
  
  await Promise.all(refreshPromises);
}
```

---

### Opción B: Refresh Completo (Simple)

```typescript
async function handleChatMessage(message: string, context: any) {
  // 1. Enviar mensaje al chat
  const response = await sendChatMessage(message, context);
  
  // 2. Refrescar todo si hubo cambios
  if (response.refresh.needs_refresh) {
    await refreshRFXData();
  }
  
  return response;
}
```

**Cuándo usar:**
- Implementación rápida
- No necesitas optimización extrema
- Prefieres simplicidad sobre performance

---

## 📊 Ejemplos de Uso

### Ejemplo 1: Agregar Producto

**Mensaje:** "Agrega 20 refrescos a $2.50 cada uno"

**Response:**
```json
{
  "message": "✅ He agregado 20 refrescos a $2.50 cada uno.",
  "changes": [
    {
      "type": "add_product",
      "target": "new",
      "data": {
        "nombre": "Refrescos",
        "cantidad": 20,
        "precio": 2.50
      }
    }
  ],
  "refresh": {
    "needs_refresh": true,
    "scope": "products",
    "components": ["products", "pricing", "totals"]
  }
}
```

**Frontend:**
1. Agrega "Refrescos" al estado local
2. Refresca componentes: `products`, `pricing`, `totals`
3. **NO** refresca: `details`, `header`

---

### Ejemplo 2: Cambiar Fecha de Entrega

**Mensaje:** "Cambia la fecha de entrega a 20 de enero"

**Response:**
```json
{
  "message": "✅ He actualizado la fecha de entrega a 20 de enero de 2026.",
  "changes": [
    {
      "type": "update_field",
      "target": "fechaEntrega",
      "data": "2026-01-20"
    }
  ],
  "refresh": {
    "needs_refresh": true,
    "scope": "details",
    "components": ["details"]
  }
}
```

**Frontend:**
1. Actualiza `fechaEntrega` en estado local
2. Refresca componente: `details`
3. **NO** refresca: `products`, `pricing`, `totals`, `header`

---

### Ejemplo 3: Solo Pregunta (Sin Cambios)

**Mensaje:** "¿Cuántos productos tengo?"

**Response:**
```json
{
  "message": "Actualmente tienes 5 productos en el RFX.",
  "changes": [],
  "refresh": {
    "needs_refresh": false,
    "scope": "none",
    "components": []
  }
}
```

**Frontend:**
1. Muestra mensaje del chat
2. **NO** refresca nada

---

## 🔧 Componentes Disponibles

| Componente | Descripción | Cuándo Refrescar |
|------------|-------------|------------------|
| `products` | Lista de productos | Cambios en productos |
| `pricing` | Configuración de pricing | Cambios en productos (recalcular) |
| `totals` | Totales y subtotales | Cambios en productos |
| `details` | Detalles del RFX (fecha, lugar) | Cambios en campos del RFX |
| `header` | Header con info del cliente | Cambios en datos del cliente |

---

## 📡 API - Endpoint GET /chat/history

### Request

```http
GET /api/rfx/{rfx_id}/chat/history?limit=20
Authorization: Bearer <jwt_token>
```

### Query Parameters

| Parámetro | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| `limit` | `int` | `20` | Número de mensajes a retornar |

### Response

```json
{
  "status": "success",
  "history": [
    {
      "id": "msg-uuid",
      "rfx_id": "rfx-uuid",
      "user_id": "user-uuid",
      "user_message": "Agrega 10 sillas a $50 cada una",
      "user_files": [
        {
          "name": "productos.xlsx",
          "type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
          "size": 15234
        }
      ],
      "assistant_message": "✅ He agregado 10 sillas a $50 cada una.",
      "confidence": 0.95,
      "changes_applied": [
        {
          "type": "add_product",
          "target": "new",
          "data": {
            "nombre": "Sillas",
            "cantidad": 10,
            "precio": 50
          },
          "description": "Agregado: Sillas (10 unidades)"
        }
      ],
      "requires_confirmation": false,
      "tokens_used": 1234,
      "cost_usd": 0.0123,
      "processing_time_ms": 2340,
      "model_used": "gpt-4o-mini",
      "created_at": "2026-01-13T20:45:00Z"
    }
  ],
  "count": 1
}
```

---

## 🎨 Ejemplo de Implementación Completa

```typescript
// hooks/useRFXChat.ts
import { useState, useCallback } from 'react';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

export function useRFXChat(rfxId: string) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  
  // Cargar historial al montar
  useEffect(() => {
    loadChatHistory();
  }, [rfxId]);
  
  const loadChatHistory = async () => {
    try {
      const response = await fetch(`/api/rfx/${rfxId}/chat/history?limit=20`, {
        headers: {
          'Authorization': `Bearer ${getAuthToken()}`
        }
      });
      
      const data = await response.json();
      
      if (data.status === 'success') {
        const formattedMessages = data.history.flatMap(entry => [
          {
            role: 'user' as const,
            content: entry.user_message,
            timestamp: entry.created_at
          },
          {
            role: 'assistant' as const,
            content: entry.assistant_message,
            timestamp: entry.created_at
          }
        ]);
        
        setMessages(formattedMessages);
      }
    } catch (error) {
      console.error('Error loading chat history:', error);
    }
  };
  
  const sendMessage = useCallback(async (message: string, context: any) => {
    setIsLoading(true);
    
    // Agregar mensaje del usuario inmediatamente
    const userMessage: ChatMessage = {
      role: 'user',
      content: message,
      timestamp: new Date().toISOString()
    };
    setMessages(prev => [...prev, userMessage]);
    
    try {
      const response = await fetch(`/api/rfx/${rfxId}/chat`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${getAuthToken()}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ message, context })
      });
      
      const data = await response.json();
      
      // Agregar respuesta del asistente
      const assistantMessage: ChatMessage = {
        role: 'assistant',
        content: data.message,
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, assistantMessage]);
      
      // Aplicar cambios al estado local
      if (data.changes && data.changes.length > 0) {
        applyChangesToLocalState(data.changes);
      }
      
      // Refrescar componentes si es necesario
      if (data.refresh.needs_refresh) {
        await refreshComponents(data.refresh.components);
      }
      
      return data;
      
    } catch (error) {
      console.error('Error sending message:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, [rfxId]);
  
  return {
    messages,
    sendMessage,
    isLoading,
    loadChatHistory
  };
}
```

---

## 🚀 Mejores Prácticas

### 1. Actualización Optimista

✅ **Hacer:** Actualizar estado local inmediatamente  
❌ **No hacer:** Esperar a que el backend confirme antes de actualizar UI

### 2. Refresh Selectivo

✅ **Hacer:** Refrescar solo componentes afectados  
❌ **No hacer:** Refrescar todo el RFX en cada mensaje

### 3. Manejo de Errores

✅ **Hacer:** Revertir cambios locales si el backend falla  
❌ **No hacer:** Dejar el estado inconsistente

### 4. Feedback Visual

✅ **Hacer:** Mostrar indicador de "Aplicando cambios..."  
❌ **No hacer:** Cambios silenciosos sin feedback

---

## 🐛 Troubleshooting

### Problema: Componentes no se refrescan

**Causa:** `refresh.needs_refresh` es `false`

**Solución:** Verificar que el chat hizo cambios reales (revisar `changes` array)

---

### Problema: Se refresca todo en lugar de componentes específicos

**Causa:** Frontend no implementa refresh selectivo

**Solución:** Implementar `refreshComponents()` con switch por tipo de componente

---

### Problema: Estado local desincronizado con backend

**Causa:** Cambios locales no se persistieron en backend

**Solución:** Agregar persistencia después de cada cambio local

---

## 📚 Referencias

- **Endpoint POST /chat:** `/backend/api/rfx_chat.py:83-244`
- **Endpoint GET /history:** `/backend/api/rfx_chat.py:267-297`
- **Funciones Helper:** `/backend/api/rfx_chat.py:27-80`
- **Modelos:** `/backend/models/chat_models.py`

---

## ✅ Checklist de Implementación

### Backend
- [x] Endpoint POST /chat retorna metadata de refresh
- [x] Endpoint GET /history con límite de 20 mensajes
- [x] Funciones helper para detectar refresh needs
- [x] Modelo RefreshMetadata

### Frontend
- [ ] Hook useRFXChat para manejar mensajes
- [ ] Función loadChatHistory() para cargar historial
- [ ] Función applyChangesToLocalState() para cambios optimistas
- [ ] Función refreshComponents() para refresh selectivo
- [ ] UI para mostrar historial de chat
- [ ] Feedback visual de cambios aplicados

---

**Estado:** ✅ Backend Implementado - Listo para Integración Frontend
