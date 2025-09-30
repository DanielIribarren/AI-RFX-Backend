# 📊 JSON del Analyst y Persistencia en BD

## 1️⃣ JSON que Devuelve el ANALYST (Raw)

El Analyst devuelve un JSON con esta estructura completa:

```json
{
  "extracted_data": {
    "project_details": {
      "title": "Servicio de Catering Corporativo - 60 personas",
      "description": "Servicio de catering para evento corporativo interno en Torre Barcelona",
      "scope": "Menú completo para 60 personas incluyendo salados, dulces y bebidas",
      "deliverables": [
        "Menú de salados (3 variedades)",
        "Menú de dulces (3 variedades)",
        "Bebidas variadas",
        "Entrega en ubicación corporativa"
      ],
      "industry_domain": "catering",
      "rfx_type_detected": "solicitud_catering"
    },
    "client_information": {
      "name": "Sofia Elena Camejo Copello",
      "company": "Chevron (SCM Venezuela)",
      "contact": "SofiaElena.Camejo@chevron.com",
      "profile": "corporativo",
      "company_email": "SofiaElena.Camejo@chevron.com",
      "company_phone": "+58 414-123-4567",
      "requester_email": "SofiaElena.Camejo@chevron.com",
      "requester_phone": "+58 414-123-4567",
      "requester_position": "Coordinadora de Eventos"
    },
    "timeline": {
      "start_date": null,
      "end_date": null,
      "delivery_date": "2025-03-15",
      "delivery_time": "14:00",
      "submission_deadline": null,
      "expected_decision_date": null,
      "key_milestones": ["Entrega: 15 marzo 2:00 p.m."],
      "urgency_factors": ["Fecha relativa 'mañana' - requiere confirmación"]
    },
    "requirements": {
      "functional": [
        "Servicio de catering para 60 personas",
        "Menú estructurado por categorías",
        "Entrega en ubicación corporativa"
      ],
      "technical": [
        "Cantidades específicas por producto",
        "Presentación profesional corporativa"
      ],
      "regulatory": [],
      "quality": [
        "Estándares corporativos",
        "Presentación profesional"
      ],
      "special_requirements": []
    },
    "location_logistics": {
      "primary_location": "Torre Barcelona, Piso 12, Av. Principal, Barcelona, Anzoátegui, Venezuela",
      "event_city": "Barcelona",
      "event_state": "Anzoátegui",
      "event_country": "Venezuela",
      "additional_locations": [],
      "logistics_considerations": [
        "Acceso a edificio corporativo",
        "Entrega en piso 12",
        "Coordinación de horario de acceso"
      ]
    },
    "budget_financial": {
      "estimated_budget": null,
      "budget_range_min": null,
      "budget_range_max": null,
      "currency": "USD",
      "payment_terms": null,
      "financial_constraints": []
    },
    "requested_products": [
      {
        "product_name": "Tequeños",
        "quantity": 100,
        "unit": "unidades",
        "specifications": "",
        "category": "salados"
      },
      {
        "product_name": "Mini pizzas caprese",
        "quantity": 75,
        "unit": "unidades",
        "specifications": "",
        "category": "salados"
      },
      {
        "product_name": "Mini empanadas",
        "quantity": 75,
        "unit": "unidades",
        "specifications": "",
        "category": "salados"
      },
      {
        "product_name": "Shots pie de limón",
        "quantity": 15,
        "unit": "shots",
        "specifications": "",
        "category": "dulces"
      },
      {
        "product_name": "Shots de coco",
        "quantity": 15,
        "unit": "shots",
        "specifications": "",
        "category": "dulces"
      },
      {
        "product_name": "Shots de brownie",
        "quantity": 15,
        "unit": "shots",
        "specifications": "",
        "category": "dulces"
      },
      {
        "product_name": "Té Lipton (estándar)",
        "quantity": 15,
        "unit": "unidades",
        "specifications": "",
        "category": "bebidas"
      },
      {
        "product_name": "Latas de refresco",
        "quantity": 25,
        "unit": "latas",
        "specifications": "",
        "category": "bebidas"
      },
      {
        "product_name": "Jugo Frica",
        "quantity": 3,
        "unit": "botellas",
        "specifications": "",
        "category": "bebidas"
      }
    ]
  },
  "inferred_information": {
    "implicit_requirements": [
      "Coordinación logística para entrega en edificio corporativo",
      "Posible necesidad de personal de servicio",
      "Equipamiento desechable o vajilla",
      "Presentación acorde a estándares corporativos"
    ],
    "industry_standards": [
      "Calidad corporativa en presentación",
      "Puntualidad en entrega",
      "Servicio profesional"
    ],
    "best_practices": [
      "Confirmar fecha absoluta (actualmente relativa)",
      "Validar acceso al edificio corporativo",
      "Coordinar horario de montaje previo al evento"
    ],
    "additional_considerations": [
      "Cliente corporativo de alto perfil (Chevron)",
      "Evento interno requiere discreción",
      "Posible necesidad de facturación corporativa"
    ],
    "evaluation_criteria": [
      {
        "criterion": "calidad",
        "weight": 35,
        "description": "Calidad de productos y presentación profesional"
      },
      {
        "criterion": "puntualidad",
        "weight": 30,
        "description": "Entrega exacta a las 2:00 p.m."
      },
      {
        "criterion": "precio",
        "weight": 20,
        "description": "Precio competitivo para servicio corporativo"
      },
      {
        "criterion": "experiencia",
        "weight": 15,
        "description": "Experiencia en eventos corporativos"
      }
    ]
  },
  "quality_assessment": {
    "completeness_score": 8.5,
    "confidence_level": 9.0,
    "products_confidence": 9.5,
    "dates_confidence": 7.0,
    "contact_confidence": 9.5,
    "requirements_confidence": 8.5,
    "missing_information": [
      "Fecha absoluta (solo fecha relativa 'mañana')",
      "Presupuesto estimado",
      "Términos de pago preferidos"
    ],
    "validation_status": "requiere_clarificación",
    "recommended_questions": [
      "¿Confirmar fecha exacta del evento?",
      "¿Requieren personal de servicio?",
      "¿Presupuesto máximo disponible?"
    ]
  },
  "reasoning": "Extracción completada siguiendo estrategia del Orchestrator. Se identificaron y extrajeron los 9 items organizados por categorías..."
}
```

---

## 2️⃣ JSON Formateado para Compatibilidad

El método `_format_analysis_for_compatibility` transforma el JSON del Analyst:

```json
{
  "status": "success",
  "extracted_data": {
    "project_title": "Servicio de Catering Corporativo - 60 personas",
    "project_description": "Servicio de catering para evento corporativo interno en Torre Barcelona",
    "project_type": "catering",
    "complexity_score": 6,
    
    "client_name": "Sofia Elena Camejo Copello",
    "client_company": "Chevron (SCM Venezuela)",
    "client_email": "SofiaElena.Camejo@chevron.com",
    
    "start_date": null,
    "end_date": null,
    "deadline": null,
    
    "requirements": {
      "functional": ["Servicio de catering para 60 personas", ...],
      "technical": ["Cantidades específicas por producto", ...],
      "regulatory": [],
      "quality": ["Estándares corporativos", ...]
    },
    "scope": "Menú completo para 60 personas incluyendo salados, dulces y bebidas",
    "deliverables": ["Menú de salados (3 variedades)", ...],
    
    "location": "Torre Barcelona, Piso 12, Av. Principal, Barcelona, Anzoátegui, Venezuela",
    "service_location": "Torre Barcelona, Piso 12, Av. Principal, Barcelona, Anzoátegui, Venezuela",
    
    "estimated_budget": null,
    "budget_range": "",
    
    "industry": "catering",
    "urgency_level": "alto",
    "client_profile": "corporativo",
    
    "items": [
      {
        "product_name": "Tequeños",
        "quantity": 100,
        "unit": "unidades",
        "specifications": "",
        "category": "salados"
      },
      // ... 8 items más
    ]
  },
  "suggestions": [
    "Proyecto identificado como: catering",
    "Nivel de complejidad: 6/10",
    "Perfil del cliente: corporativo",
    "Urgencia: alto",
    "¿Confirmar fecha exacta del evento?",
    "¿Requieren personal de servicio?",
    "¿Presupuesto máximo disponible?"
  ],
  "ready_for_review": true,
  "confidence_score": 9.0,
  "quality_score": 8.5,
  
  "analysis_metadata": {
    "primary_industry": "catering",
    "secondary_industries": ["eventos_corporativos"],
    "complexity_score": 6,
    "implicit_needs": [
      "Coordinación logística para entrega en edificio corporativo",
      "Posible necesidad de personal de servicio",
      ...
    ],
    "critical_factors": [
      "Cumplimiento exacto de cantidades solicitadas",
      "Puntualidad en entrega",
      ...
    ],
    "potential_risks": [
      "Fecha relativa ('mañana') requiere anclar a fecha absoluta",
      "Acceso a edificio corporativo",
      ...
    ]
  }
}
```

---

## 3️⃣ Qué se Guarda en la Base de Datos

### Tabla: `projects`

```sql
INSERT INTO projects (
    id,
    name,
    description,
    project_type,
    status,
    organization_id,
    created_by,
    
    -- Datos del cliente (extraídos por Analyst)
    client_name,
    client_company,
    client_email,
    client_phone,
    
    -- Ubicación (extraída por Analyst)
    service_location,
    
    -- Otros campos
    tags,
    priority,
    created_at,
    updated_at
) VALUES (
    '101a1b39-81fd-466c-a881-c62eb838a23f',
    'Project catering - 101a1b39',
    'Project created via API upload for catering',
    'catering',
    'active',  -- ✅ 'active' porque se analizó correctamente
    '8129fd24-ba71-4863-b937-d9ead08ab51e',
    'eb836c5a-89e4-4d3f-8c72-2d0072356000',
    
    -- ✅ Datos extraídos por el Analyst
    'Sofia Elena Camejo Copello',
    'Chevron (SCM Venezuela)',
    'SofiaElena.Camejo@chevron.com',
    '+58 414-123-4567',
    
    'Torre Barcelona, Piso 12, Av. Principal, Barcelona, Anzoátegui, Venezuela',
    
    ['catering', 'api_upload'],
    3,
    '2025-03-30 13:31:49',
    '2025-03-30 13:31:49'
);
```

### Tabla: `project_documents`

```sql
INSERT INTO project_documents (
    project_id,
    filename,
    original_filename,
    file_path,
    file_size_bytes,
    file_type,
    mime_type,
    document_type,
    is_primary,
    uploaded_by,
    is_processed,
    processing_status
) VALUES (
    '101a1b39-81fd-466c-a881-c62eb838a23f',
    'Solicitud de catering para 60p.docx',
    'Solicitud de catering para 60p.docx',
    '/uploads/101a1b39-81fd-466c-a881-c62eb838a23f/Solicitud de catering para 60p.docx',
    9318,
    'docx',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'attachment',
    true,
    'eb836c5a-89e4-4d3f-8c72-2d0072356000',
    true,
    'completed'
);
```

### Tabla: `workflow_states`

```sql
INSERT INTO workflow_states (
    project_id,
    current_stage,
    stage_progress,
    overall_progress,
    requires_human_review,
    quality_score,
    quality_gates_passed,
    quality_gates_total,
    workflow_version
) VALUES (
    '101a1b39-81fd-466c-a881-c62eb838a23f',
    'intelligent_extraction',  -- ✅ Indica que se usó IA
    60.0,
    60.0,
    false,
    0.8,
    4,  -- ✅ 4 gates pasados (con análisis IA)
    7,
    '3.0'
);
```

### Tabla: `project_items` (✅ LOS 9 ITEMS)

```sql
INSERT INTO project_items (
    project_id,
    name,
    description,
    category,
    quantity,
    unit_of_measure,
    unit_price,
    total_price,
    extracted_from_ai,
    extraction_confidence,
    extraction_method,
    is_validated,
    is_included,
    sort_order
) VALUES
-- Item 1
(
    '101a1b39-81fd-466c-a881-c62eb838a23f',
    'Tequeños',
    '',
    'salados',
    100.0,
    'unidades',
    NULL,
    NULL,
    true,
    0.95,
    'budy_agent_analyst',
    false,
    true,
    0
),
-- Item 2
(
    '101a1b39-81fd-466c-a881-c62eb838a23f',
    'Mini pizzas caprese',
    '',
    'salados',
    75.0,
    'unidades',
    NULL,
    NULL,
    true,
    0.95,
    'budy_agent_analyst',
    false,
    true,
    1
),
-- Item 3
(
    '101a1b39-81fd-466c-a881-c62eb838a23f',
    'Mini empanadas',
    '',
    'salados',
    75.0,
    'unidades',
    NULL,
    NULL,
    true,
    0.95,
    'budy_agent_analyst',
    false,
    true,
    2
),
-- Item 4
(
    '101a1b39-81fd-466c-a881-c62eb838a23f',
    'Shots pie de limón',
    '',
    'dulces',
    15.0,
    'shots',
    NULL,
    NULL,
    true,
    0.95,
    'budy_agent_analyst',
    false,
    true,
    3
),
-- Item 5
(
    '101a1b39-81fd-466c-a881-c62eb838a23f',
    'Shots de coco',
    '',
    'dulces',
    15.0,
    'shots',
    NULL,
    NULL,
    true,
    0.95,
    'budy_agent_analyst',
    false,
    true,
    4
),
-- Item 6
(
    '101a1b39-81fd-466c-a881-c62eb838a23f',
    'Shots de brownie',
    '',
    'dulces',
    15.0,
    'shots',
    NULL,
    NULL,
    true,
    0.95,
    'budy_agent_analyst',
    false,
    true,
    5
),
-- Item 7
(
    '101a1b39-81fd-466c-a881-c62eb838a23f',
    'Té Lipton (estándar)',
    '',
    'bebidas',
    15.0,
    'unidades',
    NULL,
    NULL,
    true,
    0.95,
    'budy_agent_analyst',
    false,
    true,
    6
),
-- Item 8
(
    '101a1b39-81fd-466c-a881-c62eb838a23f',
    'Latas de refresco',
    '',
    'bebidas',
    25.0,
    'latas',
    NULL,
    NULL,
    true,
    0.95,
    'budy_agent_analyst',
    false,
    true,
    7
),
-- Item 9
(
    '101a1b39-81fd-466c-a881-c62eb838a23f',
    'Jugo Frica',
    '',
    'bebidas',
    3.0,
    'botellas',
    NULL,
    NULL,
    true,
    0.95,
    'budy_agent_analyst',
    false,
    true,
    8
);
```

### Tabla: `project_context`

```sql
INSERT INTO project_context (
    project_id,
    detected_project_type,
    complexity_score,
    analysis_confidence,
    analysis_reasoning,
    ai_model_used,
    key_requirements,
    implicit_needs,
    risk_factors,
    tokens_consumed
) VALUES (
    '101a1b39-81fd-466c-a881-c62eb838a23f',
    'catering',
    0.6,  -- Complexity score del Orchestrator
    0.9,  -- Confidence del Analyst
    'Analysis completed via BudyAgent - project created with complete data',
    'gpt-4o',
    [
        "Servicio de catering para 60 personas",
        "Menú estructurado por categorías",
        "Entrega en ubicación corporativa",
        "Cantidades específicas por producto",
        "Presentación profesional corporativa"
    ],
    [],
    [],
    6249  -- Tokens usados en el análisis
);
```

---

## 4️⃣ Resumen del Flujo de Datos

```
Analyst JSON (raw)
    ↓
_format_analysis_for_compatibility()
    ↓
budy_raw_result = {
    'status': 'success',
    'extracted_data': { ... },
    'suggestions': [ ... ],
    'confidence_score': 9.0,
    ...
}
    ↓
projects.py extrae campos específicos:
    ↓
┌─────────────────────────────────────────┐
│  analysis_result.get('client_information')  │
│  analysis_result.get('project_details')     │
│  analysis_result.get('requested_products')  │
└─────────────────────────────────────────┘
    ↓
Se guardan en BD:
    ↓
├─ projects (1 registro con datos del cliente)
├─ project_documents (1 registro por archivo)
├─ workflow_states (1 registro con estado)
├─ project_items (9 registros - uno por item)
└─ project_context (1 registro con análisis)
```

---

## 5️⃣ Campos Clave Extraídos vs Guardados

| Campo del Analyst | Tabla BD | Columna BD |
|-------------------|----------|------------|
| `client_information.name` | `projects` | `client_name` |
| `client_information.company` | `projects` | `client_company` |
| `client_information.company_email` | `projects` | `client_email` |
| `client_information.requester_phone` | `projects` | `client_phone` |
| `location_logistics.primary_location` | `projects` | `service_location` |
| `requested_products[0].product_name` | `project_items` | `name` |
| `requested_products[0].quantity` | `project_items` | `quantity` |
| `requested_products[0].unit` | `project_items` | `unit_of_measure` |
| `requested_products[0].category` | `project_items` | `category` |
| `quality_assessment.confidence_level` | `project_context` | `analysis_confidence` |

**✅ Los 9 items se guardan individualmente en `project_items`**
**✅ Los datos del cliente se guardan en `projects`**
**✅ El contexto del análisis se guarda en `project_context`**
