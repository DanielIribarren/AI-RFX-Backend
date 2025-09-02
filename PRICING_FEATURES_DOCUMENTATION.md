# 💰 Nuevas Funcionalidades de Pricing - Sistema de Coordinación y Costo por Persona

## 📋 Resumen de Implementación

Se han integrado exitosamente las nuevas funcionalidades de **coordinación/logística** y **costo por persona** en tu aplicación RFX existente, manteniendo la arquitectura actual sin romper funcionalidades existentes.

## 🏗️ Arquitectura Implementada

### Componentes Agregados:

1. **`pricing_models.py`** - Modelos Pydantic para configuraciones de pricing
2. **`pricing_config_service.py`** - Servicio de negocio para manejar configuraciones
3. **`pricing.py`** - API endpoints para configuración y cálculos
4. **Integración con `proposal_generator.py`** - Generación automática con configuraciones

### Base de Datos:

- **Almacenamiento**: Las configuraciones se guardan en `metadata_json` del RFX existente
- **Sin nuevas tablas**: Se adapta perfectamente a tu esquema V2.0 actual
- **Compatibilidad**: No rompe funcionalidades existentes

## 🚀 Nuevos Endpoints API

### 1. Obtener Configuración de Pricing

```http
GET /api/pricing/config/<rfx_id>
```

**Respuesta:**

```json
{
  "status": "success",
  "data": {
    "rfx_id": "uuid-here",
    "coordination_enabled": false,
    "coordination_rate": 0.18,
    "cost_per_person_enabled": false,
    "headcount": null,
    "taxes_enabled": false,
    "has_configuration": true
  }
}
```

### 2. Configurar Pricing para un RFX

```http
PUT /api/pricing/config/<rfx_id>
Content-Type: application/json

{
  "coordination_enabled": true,
  "coordination_rate": 0.18,
  "cost_per_person_enabled": true,
  "headcount": 50,
  "taxes_enabled": false
}
```

### 3. Calcular Pricing con Configuraciones

```http
POST /api/pricing/calculate/<rfx_id>
Content-Type: application/json

{
  "subtotal": 1000.00
}
```

**Respuesta:**

```json
{
  "status": "success",
  "data": {
    "calculation": {
      "subtotal": 1000.0,
      "coordination_amount": 180.0,
      "cost_per_person": 23.6,
      "total_cost": 1180.0,
      "applied_configs": ["coordination_18%", "cost_per_person_50"]
    }
  }
}
```

### 4. Configuración Rápida

```http
POST /api/pricing/quick-config/<rfx_id>
Content-Type: application/json

{
  "config_type": "full",
  "headcount": 75,
  "coordination_rate": 0.20
}
```

**Opciones de `config_type`:**

- `"none"` - Sin configuraciones adicionales
- `"coordination_only"` - Solo coordinación
- `"cost_per_person_only"` - Solo costo por persona
- `"full"` - Coordinación + costo por persona
- `"basic"` - Configuración básica (15% coordinación)

### 5. Calcular Automáticamente desde RFX

```http
GET /api/pricing/calculate-from-rfx/<rfx_id>
```

Calcula automáticamente basado en los productos y precios del RFX.

### 6. Obtener Presets Disponibles

```http
GET /api/pricing/presets
```

**Respuesta:**

```json
{
  "status": "success",
  "data": [
    {
      "id": "catering_basico",
      "name": "Catering Básico",
      "coordination_enabled": true,
      "coordination_rate": 0.15,
      "cost_per_person_enabled": true,
      "default_headcount": 50
    }
  ]
}
```

## 🎯 Casos de Uso Principales

### Caso 1: Solo Coordinación

```javascript
// El usuario quiere agregar 18% de coordinación
await fetch(`/api/pricing/config/${rfxId}`, {
  method: "PUT",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    coordination_enabled: true,
    coordination_rate: 0.18,
    cost_per_person_enabled: false,
  }),
});
```

### Caso 2: Solo Costo por Persona

```javascript
// El usuario quiere mostrar costo por persona para 80 personas
await fetch(`/api/pricing/config/${rfxId}`, {
  method: "PUT",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    coordination_enabled: false,
    cost_per_person_enabled: true,
    headcount: 80,
  }),
});
```

### Caso 3: Configuración Completa

```javascript
// Coordinación + costo por persona
await fetch(`/api/pricing/config/${rfxId}`, {
  method: "PUT",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    coordination_enabled: true,
    coordination_rate: 0.2,
    cost_per_person_enabled: true,
    headcount: 100,
    taxes_enabled: true,
    tax_rate: 0.16,
    tax_type: "IVA",
  }),
});
```

### Caso 4: Usar Configuración Rápida

```javascript
// Configuración rápida para evento completo
await fetch(`/api/pricing/quick-config/${rfxId}`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    config_type: "full",
    headcount: 120,
    coordination_rate: 0.18,
  }),
});
```

## 🔄 Integración con Generación de Propuestas

### Flujo Actualizado:

1. **Usuario configura pricing** usando endpoints de `/api/pricing/`
2. **Usuario genera propuesta** usando endpoint existente `/api/proposals/generate`
3. **Sistema automáticamente aplica** las configuraciones al generar el HTML
4. **Propuesta incluye** coordinación y costo por persona según configuración

### Ejemplo de HTML Generado:

```html
<!-- Con coordinación habilitada -->
<tr>
  <td>Coordinación y logística (18%)</td>
  <td colspan="2"></td>
  <td>$180.00</td>
</tr>

<!-- Con costo por persona habilitado -->
<p>Costo por persona: $23.60 (50 personas)</p>
```

## 📊 Estructura de Datos

### Configuración en Base de Datos:

```json
{
  "metadata_json": {
    "pricing_configuration": {
      "coordination": {
        "config_type": "coordination",
        "is_enabled": true,
        "config_value": {
          "rate": 0.18,
          "description": "Coordinación y logística"
        }
      },
      "cost_per_person": {
        "config_type": "cost_per_person",
        "is_enabled": true,
        "config_value": {
          "headcount": 50,
          "description": "Cálculo para 50 personas"
        }
      }
    }
  }
}
```

## 🧮 Cálculos Implementados

### Fórmulas:

1. **Subtotal** = Suma de (cantidad × precio_unitario) de todos los productos
2. **Coordinación** = subtotal × coordination_rate (si está habilitada)
3. **Total antes de impuestos** = subtotal + coordinación
4. **Impuestos** = total_antes_impuestos × tax_rate (si están habilitados)
5. **Total Final** = total_antes_impuestos + impuestos
6. **Costo por Persona** = total_final ÷ headcount (si está habilitado)

### Ejemplo de Cálculo:

```
Productos: $1,000.00
Coordinación (18%): $180.00
Subtotal con coordinación: $1,180.00
IVA (16%): $188.80
TOTAL FINAL: $1,368.80
Costo por persona (50): $27.38
```

## 🎛️ Presets Disponibles

1. **Catering Básico**: 15% coordinación + costo por persona
2. **Catering Premium**: 18% coordinación + costo por persona + IVA
3. **Eventos Corporativos**: 20% coordinación + costo por persona
4. **Solo Productos**: Sin configuraciones adicionales

## ⚡ Configuraciones Rápidas

- **`"none"`**: Sin coordinación, sin costo por persona
- **`"coordination_only"`**: Solo coordinación (18% default)
- **`"cost_per_person_only"`**: Solo costo por persona (requiere headcount)
- **`"full"`**: Coordinación + costo por persona (requiere headcount)
- **`"basic"`**: Coordinación básica (15%)

## 🔧 Validaciones Implementadas

### Reglas de Negocio:

- ✅ `coordination_rate` debe estar entre 0 y 1 (como decimal)
- ✅ `headcount` debe ser mayor a 0 si está habilitado
- ✅ `tax_rate` debe estar entre 0 y 1 si está habilitado
- ✅ Configuraciones se validan antes de guardar
- ✅ Cálculos se realizan con precisión decimal

### Endpoint de Validación:

```http
POST /api/pricing/validate-config
```

## 🚨 Manejo de Errores

### Errores Comunes:

- **400**: Datos de configuración inválidos
- **404**: RFX no encontrado o sin productos
- **422**: Configuración no aplicable (ej: headcount requerido)
- **500**: Error interno del servidor

## 🎯 Próximos Pasos para Frontend

1. **Crear interfaz de configuración** que llame a `/api/pricing/config/<rfx_id>`
2. **Agregar toggles** para coordinación y costo por persona
3. **Mostrar cálculos en tiempo real** usando `/api/pricing/calculate/<rfx_id>`
4. **Integrar con flujo de generación** de propuestas existente
5. **Mostrar preview** de configuraciones antes de generar propuesta

## 📝 Logs y Debugging

### Logs Importantes:

```bash
# Configuración actualizada
✅ Pricing configuration updated for RFX {rfx_id}

# Cálculo realizado
🧮 Calculating pricing for RFX {rfx_id}, subtotal: ${subtotal}

# Configuración aplicada en propuesta
📊 Applied coordination: 18.0% = $180.00
👥 Cost per person calculation enabled for 50 people
```

### Metadata en Propuestas:

Las propuestas generadas incluyen metadata completa de pricing para auditoría:

```json
{
  "metadata": {
    "pricing": {
      "coordination_enabled": true,
      "coordination_amount": 180.0,
      "cost_per_person": 23.6,
      "applied_configs": ["coordination_18%", "cost_per_person_50"]
    }
  }
}
```

## ✅ Estado de Implementación

- ✅ **Modelos de datos** - Completado
- ✅ **Servicio de configuración** - Completado
- ✅ **Endpoints API** - Completado
- ✅ **Integración con generador** - Completado
- ✅ **Validaciones** - Completado
- ✅ **Manejo de errores** - Completado
- ✅ **Logging** - Completado
- ⏳ **Interfaz Frontend** - Pendiente
- ⏳ **Testing** - Pendiente

---

**¡Las nuevas funcionalidades están listas para usar!** 🎉

El sistema es completamente retrocompatible y no afecta las funcionalidades existentes. Puedes empezar a usar los endpoints inmediatamente desde el frontend.
