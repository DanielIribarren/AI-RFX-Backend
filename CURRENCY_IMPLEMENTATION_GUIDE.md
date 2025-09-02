# 💰 **CURRENCY IMPLEMENTATION GUIDE**

## 📋 **RESUMEN DE IMPLEMENTACIÓN**

Se ha implementado soporte completo para manejo de monedas en el sistema RFX con **impacto mínimo** y **máxima compatibilidad** hacia atrás.

### **🎯 ESTRATEGIA ADOPTADA**

- **Bajo impacto**: Solo exposición de datos existentes + endpoint simple de actualización
- **Sin breaking changes**: Todos los endpoints existentes siguen funcionando
- **Fuente única de verdad**: `rfx_v2.currency` controla toda la moneda del RFX
- **Seguridad primero**: No se permiten cambios de moneda si hay productos valorados

---

## 🔗 **NUEVOS ENDPOINTS IMPLEMENTADOS**

### **1. GET RFX con Moneda**

```http
GET /api/rfx/{rfx_id}
```

**✅ Cambios realizados:**

- Agregado campo `currency` en la respuesta del RFX
- Compatible con estructura existente

**Respuesta:**

```json
{
  "status": "success",
  "data": {
    "id": "uuid-here",
    "title": "RFX Title",
    "currency": "MXN", // ✅ NUEVO
    "estimated_budget": 5000.0,
    "actual_cost": 4500.0
    // ... otros campos existentes
  }
}
```

### **2. GET Productos del RFX**

```http
GET /api/rfx/{rfx_id}/products
```

**✅ Endpoint completamente nuevo:**

- Obtiene productos con información de moneda
- Incluye subtotal calculado
- Moneda a nivel de respuesta (no por producto)

**Respuesta:**

```json
{
  "status": "success",
  "data": {
    "rfx_id": "uuid-here",
    "currency": "MXN", // ✅ Moneda del RFX
    "products": [
      {
        "id": "product-uuid",
        "product_name": "Catering Service",
        "quantity": 100,
        "estimated_unit_price": 25.5,
        "total_estimated_cost": 2550.0
        // ... otros campos
      }
    ],
    "total_items": 5,
    "subtotal": 12750.0 // ✅ En la moneda del RFX
  }
}
```

### **3. PUT Actualizar Moneda del RFX**

```http
PUT /api/rfx/{rfx_id}/currency
Content-Type: application/json

{
  "currency": "USD"
}
```

**✅ Endpoint nuevo - Seguro por diseño:**

- Valida formato ISO 4217 (3 letras)
- **Rechaza cambios si hay productos con precios**
- Registra cambios en historial
- Idempotente (no falla si ya está en esa moneda)

**Respuesta exitosa:**

```json
{
  "status": "success",
  "message": "Currency updated successfully from MXN to USD",
  "data": {
    "rfx_id": "uuid-here",
    "old_currency": "MXN",
    "new_currency": "USD",
    "changed": true
  }
}
```

**Respuesta de seguridad (productos valorados):**

```json
{
  "status": "error",
  "message": "Cannot change currency for RFX with priced products",
  "error": "This RFX has products with estimated prices. Changing currency would affect cost calculations.",
  "suggestion": "Clear product prices first or create a new RFX for the new currency",
  "data": {
    "current_currency": "MXN",
    "requested_currency": "USD",
    "priced_products_count": 3
  }
}
```

### **4. Endpoints de Pricing con Moneda**

**✅ Mejorados endpoints existentes:**

#### GET `/api/pricing/config/{rfx_id}`

```json
{
  "status": "success",
  "data": {
    "rfx_id": "uuid-here",
    "currency": "MXN", // ✅ NUEVO
    "coordination_enabled": true,
    "coordination_rate": 0.18,
    "cost_per_person_enabled": true,
    "headcount": 120
    // ... otros campos
  }
}
```

#### POST `/api/pricing/calculate/{rfx_id}`

```json
{
  "status": "success",
  "data": {
    "rfx_id": "uuid-here",
    "currency": "MXN", // ✅ NUEVO
    "summary": {
      "subtotal": 10000.0,
      "coordination_amount": 1800.0,
      "total_cost": 11800.0
    }
  }
}
```

---

## 🏗️ **ARQUITECTURA Y DECISIONES TÉCNICAS**

### **Principios Seguidos:**

1. **Moneda única por RFX**: `rfx_v2.currency` es autoridad para todos los importes
2. **No duplicación**: No se agrega `currency` a `rfx_products`
3. **Compatibilidad total**: Todos los endpoints existentes siguen funcionando
4. **Seguridad primero**: No conversiones automáticas en MVP
5. **Auditoría**: Todos los cambios se registran en `rfx_history`

### **Validaciones Implementadas:**

- **Formato ISO 4217**: 3 letras, alfabético, mayúsculas
- **Productos valorados**: Bloqueo de cambio si hay precios > 0
- **RFX existente**: Validación antes de cualquier operación
- **Idempotencia**: No error si ya está en la moneda solicitada

### **Campos de Base de Datos Utilizados:**

- **Existente**: `rfx_v2.currency` (TEXT DEFAULT 'MXN')
- **Sin cambios**: No se modificó esquema de DB
- **Historial**: Se usa `rfx_history` para auditoría

---

## 📱 **GUÍA DE INTEGRACIÓN FRONTEND**

### **Flujo Recomendado:**

1. **Obtener RFX completo:**

   ```javascript
   const rfx = await fetch(`/api/rfx/${rfxId}`).then((r) => r.json());
   const currency = rfx.data.currency; // "MXN"
   ```

2. **Mostrar productos con moneda:**

   ```javascript
   const products = await fetch(`/api/rfx/${rfxId}/products`).then((r) =>
     r.json()
   );
   // Todos los importes están en products.data.currency
   ```

3. **Mostrar cálculos de pricing:**

   ```javascript
   const pricing = await fetch(`/api/pricing/config/${rfxId}`).then((r) =>
     r.json()
   );
   // Usar pricing.data.currency para display
   ```

4. **Cambiar moneda (si no hay productos):**
   ```javascript
   const result = await fetch(`/api/rfx/${rfxId}/currency`, {
     method: "PUT",
     headers: { "Content-Type": "application/json" },
     body: JSON.stringify({ currency: "USD" }),
   }).then((r) => r.json());
   ```

### **Componentes UI Sugeridos:**

- **Currency Selector**: Solo activo si no hay productos valorados
- **Currency Display**: Mostrar siempre junto a importes
- **Warning Modal**: Si usuario intenta cambiar con productos valorados

---

## 🔮 **EVOLUCIÓN FUTURA (NO IMPLEMENTADO)**

### **Fase 2 - Conversión Automática:**

- Endpoint con `exchange_rate` para conversión masiva
- Integración con APIs de tipos de cambio
- Congelado de tipos de cambio por documento

### **Fase 3 - Multi-moneda Avanzada:**

- Tabla `product_catalog_prices` para catálogo global
- Soporte de excepciones por línea de producto
- Configuración de monedas permitidas por tenant

---

## ✅ **TESTING Y VERIFICACIÓN**

### **Casos de Prueba Cubiertos:**

1. ✅ Obtener RFX con moneda incluida
2. ✅ Obtener productos con moneda del RFX
3. ✅ Cambiar moneda de RFX sin productos
4. ✅ Bloquear cambio de moneda con productos valorados
5. ✅ Validación de formato de moneda
6. ✅ Idempotencia de cambio de moneda
7. ✅ Pricing endpoints con moneda incluida

### **Compatibilidad Verificada:**

- ✅ Endpoints existentes siguen funcionando
- ✅ Respuestas mantienen estructura previa + nuevo campo
- ✅ No breaking changes en frontend existente

---

## 🎉 **RESUMEN DE BENEFICIOS**

1. **Transparencia**: Toda respuesta con importes incluye moneda
2. **Consistencia**: Una sola fuente de verdad por RFX
3. **Seguridad**: No se rompen cálculos existentes
4. **Escalabilidad**: Base sólida para funcionalidades avanzadas
5. **UX mejorada**: Frontend puede mostrar monedas correctamente
6. **Auditoría**: Todos los cambios quedan registrados

**La implementación está lista para producción y es completamente compatible con el sistema existente.**
