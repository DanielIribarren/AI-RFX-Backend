# 🔄 Flujo: Orchestrator → Analyst

## Arquitectura del Flujo

```
┌─────────────────────────────────────────────────────────────┐
│  PASO 1: PARSER                                              │
│  Input: Documento (PDF/DOCX/XLSX/TXT)                       │
│  Output: Texto completo limpio                              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  PASO 2: ORCHESTRATOR                                        │
│  Input: Texto completo del documento                        │
│  Output: Estrategia de extracción (JSON)                    │
│  ⚠️ NO extrae campos, solo analiza contexto                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  PASO 3: ANALYST                                             │
│  Input: Texto completo + Estrategia del Orchestrator        │
│  Output: Datos estructurados extraídos (JSON)               │
│  ✅ Extrae TODOS los campos específicos                     │
└─────────────────────────────────────────────────────────────┘
```

---

## Ejemplo Completo: Solicitud de Catering

### INPUT: Texto del Documento (del Parser)

```
===== FILE: Solicitud de catering para 60p.docx (docx) =====

Solicitud de Servicio de Catering

Estimados,

Solicito cotización para servicio de catering corporativo para evento interno.

Detalles del Evento:
- Fecha: Mañana 15 de marzo a las 2:00 p.m.
- Ubicación: Torre Barcelona, Piso 12, Av. Principal, Barcelona, Anzoátegui
- Número de personas: 60 personas

Requerimientos de Menú:

Salados:
- 100 Tequeños
- 75 Mini pizzas caprese
- 75 Mini empanadas

Dulces:
- 15 Shots pie de limón
- 15 Shots de coco
- 15 Shots de brownie

Bebidas:
- 15 Té Lipton (estándar)
- 25 Latas de refresco
- 3 Botellas jugo Frica

Saludos cordiales,

Sofia Elena Camejo Copello
Coordinadora de Eventos
SCM Venezuela / Chevron
SofiaElena.Camejo@chevron.com
+58 414-123-4567
```

---

## OUTPUT 1: Respuesta del ORCHESTRATOR

El Orchestrator **NO extrae valores**, solo analiza el contexto y define estrategia:

```json
{
  "document_analysis": {
    "document_type": "solicitud_catering",
    "primary_industry": "catering",
    "secondary_industries": ["eventos_corporativos"],
    "complexity_score": 6,
    "estimated_scope": "mediano",
    "urgency_level": "alto",
    "formality_level": "formal"
  },
  "context_understanding": {
    "client_profile": "corporativo",
    "project_nature": "Evento corporativo interno con servicio de catering para 60 personas. Incluye menú completo (salados, dulces, bebidas) con cantidades específicas por categoría.",
    "explicit_needs_detected": [
      "Servicio de catering para 60 personas",
      "Menú estructurado por categorías (salados, dulces, bebidas)",
      "Fecha y hora específicas del evento",
      "Ubicación corporativa definida"
    ],
    "implicit_needs_inferred": [
      "Coordinación logística para entrega en edificio corporativo",
      "Presentación profesional acorde a evento corporativo",
      "Posible necesidad de personal de servicio",
      "Equipamiento desechable o vajilla"
    ],
    "critical_success_factors": [
      "Cumplimiento exacto de cantidades solicitadas",
      "Puntualidad en entrega (evento corporativo)",
      "Calidad acorde a estándares corporativos",
      "Presentación profesional"
    ],
    "potential_challenges": [
      "Fecha relativa ('mañana') requiere anclar a fecha absoluta",
      "Acceso a edificio corporativo (Torre Barcelona)",
      "Coordinación de horario de entrega vs inicio de evento"
    ]
  },
  "extraction_strategy": {
    "priority_fields": [
      "client_information",
      "items_list",
      "dates_timeline",
      "location",
      "requirements"
    ],
    "focus_areas": [
      "Extraer TODOS los items de las 3 categorías con cantidades exactas",
      "Identificar fecha relativa y convertir a fecha absoluta si es posible",
      "Diferenciar entre solicitante (Sofia) y empresa (Chevron)",
      "Capturar ubicación completa incluyendo piso y torre",
      "Extraer información de contacto completa (email corporativo + teléfono)"
    ],
    "data_patterns_to_look_for": [
      "Listas organizadas por categorías (Salados, Dulces, Bebidas)",
      "Cantidades numéricas seguidas de nombre de producto",
      "Fecha en formato español con referencia relativa ('mañana')",
      "Información de firma con nombre completo, cargo, empresa, email, teléfono",
      "Ubicación estructurada (Torre + Piso + Avenida + Ciudad + Estado)"
    ],
    "validation_points": [
      "Verificar que se extraigan los 9 items (3 salados + 3 dulces + 3 bebidas)",
      "Confirmar que cada item tenga cantidad numérica",
      "Validar email corporativo (@chevron.com)",
      "Asegurar que ubicación incluya todos los componentes",
      "Verificar coherencia entre número de personas (60) y cantidades de items"
    ],
    "special_instructions": "Este es un documento de catering corporativo con estructura clara por categorías. El Analyst debe mantener la categorización (salados/dulces/bebidas) y extraer cada item como entrada independiente. La fecha es relativa ('mañana') por lo que debe marcarse como requiere validación."
  },
  "recommended_approach": {
    "extraction_order": [
      "Primero: Identificar y extraer información del solicitante (nombre, cargo, empresa, contacto)",
      "Segundo: Extraer lista completa de items organizados por categoría",
      "Tercero: Procesar fechas y horarios (marcar fecha relativa para validación)",
      "Cuarto: Capturar ubicación completa del evento",
      "Quinto: Identificar número de personas y requerimientos especiales"
    ],
    "quality_checks": [
      "Validar que se extrajeron exactamente 9 items",
      "Verificar que todas las cantidades son numéricas",
      "Confirmar que email es corporativo",
      "Asegurar que ubicación es completa y específica"
    ],
    "fallback_strategies": [
      "Si fecha absoluta no está clara, extraer fecha relativa y marcar para validación humana",
      "Si falta información de contacto secundaria, usar solo la disponible",
      "Si categoría de item no es clara, asignar a 'general'"
    ]
  },
  "reasoning": "Este documento es una solicitud de catering corporativo bien estructurada con información clara. La principal complejidad es la fecha relativa ('mañana') que requiere validación. La lista de items está perfectamente categorizada y debe extraerse ítem por ítem. El cliente es corporativo (Chevron) lo que implica estándares de calidad y formalidad altos. La estrategia se enfoca en extracción precisa de la lista de items (prioridad #1) y captura completa de información de contacto corporativa."
}
```

---

## INPUT 2: Lo que recibe el ANALYST

El Analyst recibe **DOS inputs**:

### Input A: Texto Original Completo
```
===== FILE: Solicitud de catering para 60p.docx (docx) =====

[... TEXTO COMPLETO DEL DOCUMENTO ...]
```

### Input B: Estrategia del Orchestrator
```json
{
  "document_analysis": { ... },
  "context_understanding": { ... },
  "extraction_strategy": {
    "priority_fields": ["client_information", "items_list", ...],
    "focus_areas": ["Extraer TODOS los items...", ...],
    "data_patterns_to_look_for": ["Listas organizadas...", ...],
    ...
  },
  ...
}
```

---

## OUTPUT 2: Respuesta del ANALYST

El Analyst **SÍ extrae valores específicos** siguiendo la estrategia:

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
      "contact": "SofiaElena.Camejo@chevron.com / +58 414-123-4567",
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
      "urgency_factors": ["Fecha relativa 'mañana' - requiere confirmación de fecha absoluta"]
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
      "¿Confirmar fecha exacta del evento? (documento indica 'mañana 15 de marzo')",
      "¿Requieren personal de servicio o solo entrega de productos?",
      "¿Presupuesto máximo disponible para el servicio?"
    ]
  },
  "reasoning": "Extracción completada siguiendo estrategia del Orchestrator. Se identificaron y extrajeron los 9 items organizados por categorías (3 salados, 3 dulces, 3 bebidas) con cantidades exactas. Información de contacto completa extraída incluyendo nombre completo, cargo, empresa y datos de contacto. La principal limitación es la fecha relativa ('mañana') que requiere validación. Ubicación completa capturada con todos los detalles. Confianza alta en productos (9.5/10) y contacto (9.5/10), confianza media en fechas (7.0/10) debido a fecha relativa."
}
```

---

## Resumen del Flujo

| Componente | Input | Output | Responsabilidad |
|------------|-------|--------|-----------------|
| **Parser** | Documento binario | Texto completo limpio | Deserialización |
| **Orchestrator** | Texto completo | Estrategia de extracción (JSON) | Análisis de contexto |
| **Analyst** | Texto + Estrategia | Datos estructurados (JSON) | Extracción de campos |

### Diferencias Clave

**Orchestrator**:
- ❌ NO extrae: nombres, emails, fechas, items específicos
- ✅ SÍ analiza: tipo de documento, industria, complejidad, urgencia
- ✅ SÍ define: qué extraer, cómo extraer, qué validar

**Analyst**:
- ✅ SÍ extrae: TODOS los campos específicos del documento
- ✅ SÍ identifica: valores concretos (nombres, fechas, cantidades)
- ✅ SÍ estructura: datos en formato JSON según schema

**El Orchestrator es el "estratega", el Analyst es el "ejecutor".** 🎯
