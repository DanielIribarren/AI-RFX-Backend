# 🚀 **GUÍA DE MIGRACIÓN: APIs Legacy → Nuevo Flujo SaaS con BudyAgent**

## 📋 **RESUMEN EJECUTIVO**

El sistema ha sido refactorizado de RFX legacy a un **flujo SaaS moderno con BudyAgent**. Esta guía documenta todas las nuevas APIs que debes usar en el frontend.

### **🔄 Flujo Nuevo vs Legacy:**

**LEGACY (RFX):**

```
Frontend → /api/rfx/process → Procesador Legacy → Respuesta
```

**NUEVO (SaaS + BudyAgent):**

```
Frontend → /api/projects/ → BudyAgent (3 Momentos) → BD SaaS → Respuesta
```

---

## 🎯 **NUEVAS APIs PRINCIPALES**

### **1. PROCESAMIENTO DE PROYECTOS**

#### **🆕 POST `/api/projects/`**

_Reemplaza: `/api/rfx/process`_

**Descripción:** Crea y procesa un nuevo proyecto usando BudyAgent

**Request:**

```javascript
// Opción 1: Solo archivos
const formData = new FormData();
formData.append("files", file1);
formData.append("files", file2);
formData.append("project_type", "catering"); // opcional
formData.append("name", "Mi Proyecto"); // opcional

// Opción 2: Solo texto
const formData = new FormData();
formData.append("text_content", "Solicitud de catering para 60 personas...");
formData.append("project_type", "catering");

// Opción 3: Archivos + texto (recomendado)
const formData = new FormData();
formData.append("files", file);
formData.append("text_content", "Información adicional...");
```

**Response:**

```json
{
  "status": "success",
  "project": {
    "id": "proj_12345",
    "name": "Solicitud de Catering Corporativo",
    "project_type": "catering",
    "status": "analyzed",
    "organization_id": "org_67890",
    "user_id": "user_54321"
  },
  "extracted_data": {
    "project_title": "Catering para 60 personas",
    "client_name": "Juan Pérez",
    "client_company": "Empresa XYZ",
    "requirements": {...},
    "timeline": {...},
    "budget_info": {...}
  },
  "analysis_metadata": {
    "primary_industry": "catering",
    "complexity_score": 7,
    "confidence_level": 9.2,
    "implicit_needs": [...],
    "critical_factors": [...]
  },
  "suggestions": [
    "Proyecto identificado como: catering",
    "Nivel de complejidad: 7/10",
    "¿Restricciones dietéticas específicas?"
  ],
  "ready_for_review": true
}
```

---

### **2. GESTIÓN DE PROYECTOS**

#### **🆕 GET `/api/projects/recent`**

_Reemplaza: `/api/rfx/recent`_

**Descripción:** Obtiene proyectos recientes

**Response:**

```json
{
  "status": "success",
  "projects": [
    {
      "id": "proj_12345",
      "name": "Catering Corporativo",
      "project_type": "catering",
      "status": "analyzed",
      "created_at": "2025-09-19T20:00:00Z",
      "client_name": "Juan Pérez",
      "estimated_budget": 5000
    }
  ],
  "total": 15,
  "pagination": {
    "page": 1,
    "per_page": 10,
    "has_more": true
  }
}
```

#### **🆕 GET `/api/projects/history`**

_Reemplaza: `/api/rfx/history`_

#### **🆕 GET `/api/projects/{project_id}`**

_Reemplaza: `/api/rfx/{rfx_id}`_

**Response:**

```json
{
  "status": "success",
  "project": {
    "id": "proj_12345",
    "name": "Catering Corporativo",
    "description": "Evento para 60 personas...",
    "project_type": "catering",
    "status": "analyzed",
    "organization": {
      "id": "org_67890",
      "name": "Empresa XYZ",
      "industry": "technology"
    },
    "user": {
      "id": "user_54321",
      "name": "Juan Pérez",
      "email": "juan@empresa.com"
    },
    "timeline": {
      "start_date": "2025-10-01",
      "end_date": "2025-10-01",
      "delivery_date": "2025-10-01"
    },
    "budget": {
      "estimated_budget": 5000,
      "currency": "USD",
      "budget_range_min": 4000,
      "budget_range_max": 6000
    },
    "requirements": [...],
    "location": "Ciudad de México",
    "created_at": "2025-09-19T20:00:00Z"
  },
  "items": [
    {
      "id": "item_111",
      "name": "Menú Principal",
      "description": "Plato fuerte para 60 personas",
      "quantity": 60,
      "unit": "porciones",
      "unit_price": 25.0,
      "category": "food"
    }
  ],
  "analysis_context": {
    "budy_agent_analysis": {...},
    "confidence_scores": {...},
    "recommendations": [...]
  }
}
```

#### **🆕 GET `/api/projects/{project_id}/items`**

_Reemplaza: `/api/rfx/{rfx_id}/products`_

**Descripción:** Obtiene items/productos del proyecto

---

### **3. GENERACIÓN DE PROPUESTAS**

#### **🆕 POST `/api/proposals/generate`**

_Reemplaza: Funcionalidad de generación de propuestas_

**Descripción:** Genera propuesta comercial usando BudyAgent (MOMENTO 3)

**Request:**

```json
{
  "project_id": "proj_12345",
  "confirmed_data": {
    "client_name": "Juan Pérez",
    "project_title": "Catering Corporativo",
    "items": [
      {
        "name": "Menú Principal",
        "quantity": 60,
        "unit_price": 25.0
      }
    ]
  },
  "pricing_config": {
    "currency": "USD",
    "tax_rate": 0.16,
    "coordination_fee": 0.15,
    "payment_terms": "50% adelanto, 50% contra entrega"
  }
}
```

**Response:**

```json
{
  "status": "success",
  "quote": {
    "id": "quote_98765",
    "quote_number": "QUOTE-20250919-A1B2C3D4",
    "project_title": "Catering Corporativo",
    "client_name": "Juan Pérez",
    "industry": "catering",
    "subtotal": 1500.0,
    "coordination_amount": 225.0,
    "tax_amount": 276.0,
    "total_amount": 2001.0,
    "currency": "USD",
    "html_content": "<html>... propuesta completa ...</html>",
    "sections": [
      {
        "title": "Servicios de Catering",
        "items": [...],
        "subtotal": 1500.0
      }
    ],
    "valid_until": "2025-10-19",
    "payment_terms": "50% adelanto, 50% contra entrega",
    "delivery_terms": "Entrega el día del evento",
    "complexity_level": "medium",
    "estimated_duration": "1 día",
    "recommendations": [
      "Confirmar restricciones dietéticas",
      "Coordinar horarios de montaje"
    ]
  },
  "metadata": {
    "generation_method": "budy_agent",
    "model_used": "gpt-4o",
    "generation_time": 8.5,
    "reasoning": "Propuesta generada considerando...",
    "quality_indicators": {
      "context_used": true,
      "sections_count": 3,
      "total_items": 5
    }
  }
}
```

#### **🆕 GET `/api/proposals/{quote_id}`**

_Obtiene propuesta generada_

#### **🆕 GET `/api/proposals/quotes`**

_Lista todas las propuestas_

---

### **4. CONFIGURACIÓN DE PRECIOS**

#### **🆕 GET `/api/pricing/{project_id}/configuration`**

_Obtiene configuración de precios del proyecto_

#### **🆕 PUT `/api/pricing/{project_id}/configuration`**

_Actualiza configuración de precios_

#### **🆕 POST `/api/pricing/{project_id}/calculate`**

_Calcula precios automáticamente_

---

### **5. WORKFLOW INTELIGENTE (NUEVO)**

#### **🆕 GET `/api/projects/{project_id}/workflow`**

_Obtiene estado del workflow del proyecto_

**Response:**

```json
{
  "status": "success",
  "workflow": {
    "current_step": 2,
    "total_steps": 3,
    "steps": [
      {
        "step": 1,
        "name": "Análisis y Extracción",
        "status": "completed",
        "completed_at": "2025-09-19T20:00:00Z",
        "description": "BudyAgent analizó el documento"
      },
      {
        "step": 2,
        "name": "Revisión y Confirmación",
        "status": "in_progress",
        "description": "Usuario revisa datos extraídos"
      },
      {
        "step": 3,
        "name": "Generación de Propuesta",
        "status": "pending",
        "description": "Generar propuesta comercial"
      }
    ]
  }
}
```

#### **🆕 POST `/api/projects/{project_id}/workflow/{step_number}`**

_Avanza al siguiente paso del workflow_

#### **🆕 POST `/api/projects/{project_id}/analyze-context`**

_Ejecuta análisis contextual adicional_

---

### **6. GESTIÓN DE DATOS**

#### **🆕 PUT `/api/projects/{project_id}/data`**

_Actualiza datos del proyecto_

#### **🆕 PUT `/api/projects/{project_id}/items/costs`**

_Actualiza costos de items_

#### **🆕 PUT `/api/projects/{project_id}/currency`**

_Actualiza moneda del proyecto_

---

## 🔄 **TABLA DE MIGRACIÓN COMPLETA**

| **Legacy Endpoint**            | **Nuevo Endpoint**             | **Cambios Principales**                                                      |
| ------------------------------ | ------------------------------ | ---------------------------------------------------------------------------- |
| `POST /api/rfx/process`        | `POST /api/projects/`          | ✅ BudyAgent integration<br>✅ SaaS database<br>✅ Mejor análisis contextual |
| `GET /api/rfx/recent`          | `GET /api/projects/recent`     | ✅ Paginación mejorada<br>✅ Filtros avanzados                               |
| `GET /api/rfx/history`         | `GET /api/projects/history`    | ✅ Historial completo<br>✅ Búsqueda por organización                        |
| `GET /api/rfx/{id}`            | `GET /api/projects/{id}`       | ✅ Datos enriquecidos<br>✅ Contexto de análisis                             |
| `GET /api/rfx/{id}/products`   | `GET /api/projects/{id}/items` | ✅ Modelo unificado<br>✅ Categorización automática                          |
| `POST /api/proposals/generate` | `POST /api/proposals/generate` | ✅ BudyAgent MOMENTO 3<br>✅ Propuestas contextualizadas                     |

---

## 🎯 **FLUJO COMPLETO RECOMENDADO**

### **Paso 1: Crear Proyecto**

```javascript
const formData = new FormData();
formData.append("files", selectedFile);
formData.append("text_content", additionalInfo);

const response = await fetch("/api/projects/", {
  method: "POST",
  body: formData,
});

const result = await response.json();
const projectId = result.project.id;
```

### **Paso 2: Revisar Datos Extraídos**

```javascript
const projectData = await fetch(`/api/projects/${projectId}`);
const project = await projectData.json();

// Mostrar datos extraídos para revisión del usuario
// project.extracted_data contiene toda la información
```

### **Paso 3: Actualizar Datos (si necesario)**

```javascript
await fetch(`/api/projects/${projectId}/data`, {
  method: "PUT",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    client_name: "Nombre Corregido",
    timeline: { delivery_date: "2025-10-15" },
  }),
});
```

### **Paso 4: Configurar Precios**

```javascript
await fetch(`/api/projects/${projectId}/items/costs`, {
  method: "PUT",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    items: [
      { id: "item_111", unit_price: 30.0 },
      { id: "item_222", unit_price: 15.0 },
    ],
  }),
});
```

### **Paso 5: Generar Propuesta**

```javascript
const proposal = await fetch("/api/proposals/generate", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    project_id: projectId,
    confirmed_data: {
      /* datos confirmados */
    },
    pricing_config: {
      currency: "USD",
      tax_rate: 0.16,
      coordination_fee: 0.15,
    },
  }),
});

const quote = await proposal.json();
// quote.quote.html_content contiene la propuesta completa
```

---

## ⚡ **VENTAJAS DEL NUEVO FLUJO**

1. **🤖 Inteligencia Contextual:** BudyAgent entiende el contexto completo
2. **🏗️ Arquitectura SaaS:** Multi-organización, escalable
3. **📊 Análisis Avanzado:** Scoring de complejidad, recomendaciones automáticas
4. **🔄 Workflow Inteligente:** Pasos guiados y estado persistente
5. **💾 Persistencia Completa:** Todo se guarda en BD estructurada
6. **🎯 Propuestas Contextualizadas:** Generación basada en análisis completo

---

## 🚨 **BREAKING CHANGES**

### **Campos Renombrados:**

- `rfx_id` → `project_id`
- `rfx_type` → `project_type`
- `products` → `items`
- `company_id` → `organization_id`

### **Nuevos Campos Requeridos:**

- `project_type` (enum: catering, events, construction, consulting, general)
- `name` (opcional en ProjectInput, requerido en ProjectCreateRequest)

### **Respuestas Enriquecidas:**

- Todas las respuestas incluyen `analysis_metadata`
- Nuevos campos de contexto y recomendaciones
- IDs de organización y usuario

---

## 🔧 **COMPATIBILIDAD TEMPORAL**

Los endpoints legacy (`/api/rfx/*`) están configurados como **redirects automáticos** a los nuevos endpoints, pero es **altamente recomendado migrar** al nuevo flujo para aprovechar todas las funcionalidades.

**Redirects activos:**

- `/api/rfx/process` → `/api/projects/`
- `/api/rfx/recent` → `/api/projects/recent`
- `/api/rfx/{id}` → `/api/projects/{id}`

---

## 📞 **SOPORTE**

Para dudas sobre la migración, revisa los logs del backend que incluyen información detallada sobre cada paso del proceso BudyAgent.
