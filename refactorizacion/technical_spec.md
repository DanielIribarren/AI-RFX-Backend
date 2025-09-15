# ESPECIFICACIÓN TÉCNICA ACTUALIZADA 🤖
## SaaS de Generación Inteligente de Presupuestos con Workflow Contextual

### 🎯 CAMBIOS PRINCIPALES VS VERSIÓN ORIGINAL
- ✅ **Mantiene 85% de la arquitectura original**
- 🔄 **Agrega 4 tablas para contexto inteligente**
- 🚀 **Implementa workflow contextual con human-in-the-loop**
- 🧠 **Orquestador inteligente que entiende contexto**
- 📊 **Configuración dinámica por tipo de proyecto**

---

## 1. MATRIZ COMPLETA DE ACCESO POR ROLES 🔐

### 1.1 Tipos de Usuario (MANTIENE ORIGINAL)
- **Organization Owner (Owner)**: Control total de la organización
- **Admin**: Administración del workspace
- **Manager**: Gestión de proyectos y equipo
- **User**: Usuario estándar
- **Guest**: Acceso limitado específico
- **Client**: Cliente externo (acceso público)

### 1.2 Matriz de Acceso Actualizada con Nuevas Funcionalidades

| VISTA/FUNCIONALIDAD | Owner | Admin | Manager | User | Guest | Client |
|---------------------|-------|-------|---------|------|-------|--------|
| 🏠 Dashboard Principal | ✅ Full | ✅ Full | ✅ Limited | ✅ Personal | ❌ | ❌ |
| 📊 Analytics Avanzados | ✅ Full | ✅ Full | ✅ Team | ✅ Personal | ❌ | ❌ |
| 📁 Gestión Proyectos | ✅ All | ✅ All | ✅ Team | ✅ Own | 👁 Assigned | ❌ |
| 📄 Gestión Presupuestos | ✅ All | ✅ All | ✅ Team | ✅ Own | 👁 Assigned | 👁 Public |
| 🎨 Gestión Plantillas | ✅ All | ✅ Edit | ✅ Use | ✅ Use | ❌ | ❌ |
| **🧠 Workflow Inteligente** | **✅ Full** | **✅ Full** | **✅ Team** | **✅ Own** | **👁 View** | **❌** |
| **📊 Análisis Contextual** | **✅ Full** | **✅ Full** | **✅ Team** | **✅ Own** | **❌** | **❌** |
| **⚙️ Config. Presupuestos** | **✅ Full** | **✅ Full** | **✅ Team** | **✅ Own** | **❌** | **❌** |
| 👥 Gestión Usuarios | ✅ Full | ✅ Manage | 👁 View | 👁 View | ❌ | ❌ |
| 💳 Facturación/Planes | ✅ Full | 👁 View | ❌ | ❌ | ❌ | ❌ |
| 🔗 Webhooks/API | ✅ Full | ✅ Manage | ❌ | ❌ | ❌ | ❌ |
| 🔍 Audit Logs | ✅ Full | ✅ View | 👁 Team | 👁 Own | ❌ | ❌ |

---

## 2. ESQUEMA ACTUALIZADO DE BASE DE DATOS 🗄

### 2.1 Arquitectura Multi-Tenant (MANTIENE ORIGINAL)
- Row Level Security (RLS) por organization_id
- Índices particionados por organización
- Soft deletes para integridad referencial
- Audit trail automático

### 2.2 Tablas Principales (34 tablas total - 4 nuevas)

#### **TABLAS ORIGINALES MANTENIDAS (30 tablas)**
- ✅ organizations (25 campos)
- ✅ users (22 campos)  
- ✅ organization_users (15 campos)
- ✅ projects (48 campos)
- ✅ project_items (35 campos)
- ✅ project_documents (28 campos)
- ✅ quotes (32 campos)
- ✅ templates (25 campos)
- ✅ usage_tracking (20 campos)
- ✅ [... resto de tablas originales]

#### **NUEVAS TABLAS PARA WORKFLOW INTELIGENTE**

```sql
-- TABLA 1: Contexto de Proyectos (Análisis Orquestador)
CREATE TABLE project_context (
    -- Identificación
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id),
    
    -- Análisis del Orquestador
    project_type_detected project_type_enum NOT NULL,
    complexity_score DECIMAL(5,4), -- 0.0000 a 1.0000
    budget_range_detected budget_range_enum,
    client_type_detected client_type_enum,
    
    -- Contexto Inferido por IA
    implicit_requirements JSONB DEFAULT '{}',
    market_context JSONB DEFAULT '{}',
    typical_costs_structure JSONB DEFAULT '{}',
    
    -- Estrategia de Extracción
    extraction_strategy JSONB DEFAULT '{}',
    expected_elements JSONB DEFAULT '{}',
    context_reasoning TEXT, -- Explicación del análisis
    
    -- Metadatos de Análisis
    analysis_confidence DECIMAL(5,4),
    analysis_method VARCHAR(100) DEFAULT 'openai_gpt4',
    analysis_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    tokens_used INTEGER DEFAULT 0,
    
    -- Control
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(project_id)
);

-- TABLA 2: Iteraciones de Extracción (Mejora Continua)
CREATE TABLE extraction_iterations (
    -- Identificación
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id),
    iteration_number INTEGER NOT NULL,
    
    -- Método y Configuración
    extraction_method extraction_method_enum,
    extraction_prompt TEXT,
    context_used JSONB DEFAULT '{}',
    
    -- Resultados
    extracted_data JSONB NOT NULL,
    confidence_score DECIMAL(5,4),
    quality_issues JSONB DEFAULT '{}',
    
    -- Mejoras Aplicadas
    improvements_from_previous JSONB DEFAULT '{}',
    validation_results JSONB DEFAULT '{}',
    
    -- Performance
    processing_time_seconds DECIMAL(8,2),
    tokens_used INTEGER DEFAULT 0,
    cost_usd DECIMAL(10,4) DEFAULT 0,
    
    -- Control
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(project_id, iteration_number)
);

-- TABLA 3: Configuraciones Flexibles de Presupuestos
CREATE TABLE quote_configurations (
    -- Identificación
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id),
    
    -- Estructura de Costos Dinámica
    pricing_model pricing_model_enum NOT NULL,
    cost_structure JSONB NOT NULL, -- {"per_person": true, "services_separate": true}
    calculation_rules JSONB DEFAULT '{}',
    
    -- Márgenes e Impuestos Flexibles
    profit_margin_percent DECIMAL(5,2) DEFAULT 25.00,
    tax_configuration JSONB DEFAULT '{}', -- {"iva": 16, "islr": 3, "municipal": 0}
    discount_rules JSONB DEFAULT '{}',
    
    -- Servicios Adicionales Contextuales
    additional_services JSONB DEFAULT '{}',
    service_calculations JSONB DEFAULT '{}',
    recommended_services JSONB DEFAULT '{}', -- Sugerencias de IA
    
    -- Personalización de Presentación
    template_preferences JSONB DEFAULT '{}',
    style_configuration JSONB DEFAULT '{}',
    content_customization JSONB DEFAULT '{}',
    branding_options JSONB DEFAULT '{}',
    
    -- Términos Inteligentes
    payment_terms TEXT,
    validity_days INTEGER DEFAULT 30,
    special_conditions JSONB DEFAULT '{}',
    auto_generated_terms BOOLEAN DEFAULT FALSE,
    
    -- Metadatos
    configuration_reason TEXT, -- Por qué se eligió esta config
    context_basis JSONB DEFAULT '{}',
    
    -- Control
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(project_id)
);

-- TABLA 4: Estados del Workflow Inteligente
CREATE TABLE workflow_states (
    -- Identificación
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id),
    
    -- Estado Actual del Workflow
    current_stage workflow_stage_enum NOT NULL DEFAULT 'document_uploaded',
    stage_progress DECIMAL(5,2) DEFAULT 0.00, -- % completitud etapa actual
    overall_progress DECIMAL(5,2) DEFAULT 0.00, -- % completitud total
    
    -- Historial y Transiciones
    stage_history JSONB DEFAULT '[]',
    stage_transitions_log JSONB DEFAULT '[]',
    stage_durations JSONB DEFAULT '{}', -- tiempo en cada etapa
    
    -- Intervención Humana
    requires_human_intervention BOOLEAN DEFAULT FALSE,
    human_intervention_reason TEXT,
    human_intervention_stage workflow_stage_enum,
    human_intervention_completed BOOLEAN DEFAULT FALSE,
    human_intervention_notes TEXT,
    
    -- Calidad y Validaciones
    overall_confidence DECIMAL(5,4),
    quality_gates_passed INTEGER DEFAULT 0,
    quality_gates_total INTEGER DEFAULT 6,
    quality_issues JSONB DEFAULT '{}',
    
    -- Contexto del Workflow
    workflow_context JSONB DEFAULT '{}',
    ai_decisions_log JSONB DEFAULT '[]',
    user_overrides JSONB DEFAULT '{}',
    
    -- Metadata Técnica
    workflow_version VARCHAR(20) DEFAULT '1.0',
    estimated_completion_time INTERVAL,
    
    -- Control
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(project_id)
);
```

#### **NUEVOS ENUMS REQUERIDOS**

```sql
-- Modelos de precios flexibles
CREATE TYPE pricing_model_enum AS ENUM (
    'per_person_plus_services',    -- Catering: por persona + servicios
    'total_project_cost',          -- Consultoría: costo total fijo
    'per_category_breakdown',      -- Eventos: por categorías
    'hourly_rate',                 -- Servicios: por horas
    'per_square_meter',            -- Construcción: por m²
    'value_based_pricing',         -- Consultoría: basado en valor
    'per_unit_service'             -- General: por unidad de servicio
);

-- Rangos de presupuesto detectados
CREATE TYPE budget_range_enum AS ENUM (
    'low',           -- < $1,000
    'medium_low',    -- $1,000 - $5,000
    'medium',        -- $5,000 - $15,000
    'medium_high',   -- $15,000 - $50,000
    'high',          -- $50,000 - $100,000
    'premium'        -- > $100,000
);

-- Tipos de cliente detectados
CREATE TYPE client_type_enum AS ENUM (
    'individual',     -- Persona natural
    'small_business', -- Pequeña empresa
    'corporate',      -- Empresa grande
    'government',     -- Sector público
    'nonprofit'       -- Sin fines de lucro
);

-- Etapas del workflow inteligente
CREATE TYPE workflow_stage_enum AS ENUM (
    'document_uploaded',        -- 1. Documento cargado
    'context_analysis',         -- 2. Análisis contextual IA
    'intelligent_extraction',   -- 3. Extracción inteligente
    'extraction_validation',    -- 4. Validación automática
    'human_review_required',    -- 5. Revisión humana requerida
    'configuration_setup',      -- 6. Configuración de presupuesto
    'quote_generation',         -- 7. Generación inteligente
    'quality_evaluation',       -- 8. Evaluación de calidad
    'ready_for_delivery'        -- 9. Listo para entrega
);
```

#### **MODIFICACIONES A TABLAS EXISTENTES**

```sql
-- Expandir tabla quotes con metadata de generación inteligente
ALTER TABLE quotes ADD COLUMN generation_context JSONB DEFAULT '{}';
ALTER TABLE quotes ADD COLUMN quality_score DECIMAL(5,4);
ALTER TABLE quotes ADD COLUMN optimization_applied JSONB DEFAULT '{}';
ALTER TABLE quotes ADD COLUMN template_customizations JSONB DEFAULT '{}';
ALTER TABLE quotes ADD COLUMN ai_generation_metadata JSONB DEFAULT '{}';

-- Expandir tabla projects con contexto básico
ALTER TABLE projects ADD COLUMN context_analyzed BOOLEAN DEFAULT FALSE;
ALTER TABLE projects ADD COLUMN workflow_enabled BOOLEAN DEFAULT TRUE;
ALTER TABLE projects ADD COLUMN ai_confidence_overall DECIMAL(5,4);
```

---

## 3. ENDPOINTS API ACTUALIZADOS 🔌

### 3.1 APIs Originales (MANTIENEN FUNCIONAMIENTO)
- ✅ Todos los endpoints de la documentación original
- ✅ Autenticación y organizaciones
- ✅ Gestión de proyectos básica
- ✅ Sistema de plantillas
- ✅ Generación de PDFs

### 3.2 Nuevos Endpoints para Workflow Inteligente

#### **CONTEXTO Y ANÁLISIS INTELIGENTE**
```python
# Análisis contextual por orquestador IA
POST /api/projects/:id/analyze-context
"""
Trigger del orquestador para analizar contexto del proyecto
Input: project_id
Output: project_context con análisis detallado
"""

GET /api/projects/:id/context
"""
Obtener contexto analizado del proyecto
Output: análisis completo del orquestador
"""

PUT /api/projects/:id/context
"""
Actualizar/corregir contexto analizado
Input: correcciones del usuario
"""

POST /api/projects/:id/context/re-analyze
"""
Re-ejecutar análisis contextual con nuevos parámetros
"""
```

#### **WORKFLOW INTELIGENTE**
```python
# Estado y control del workflow
GET /api/projects/:id/workflow-status
"""
Estado actual del workflow inteligente
Output: etapa actual, progreso, intervenciones requeridas
"""

POST /api/projects/:id/workflow/advance-stage
"""
Avanzar workflow a siguiente etapa
Input: stage_validation_data
"""

POST /api/projects/:id/workflow/require-human-intervention
"""
Marcar que requiere intervención humana
Input: reason, current_stage
"""

PUT /api/projects/:id/workflow/complete-human-intervention
"""
Completar intervención humana y continuar workflow
Input: human_decisions, corrections
"""

GET /api/projects/:id/workflow/history
"""
Historial completo de etapas del workflow
"""
```

#### **EXTRACCIÓN INTELIGENTE ITERATIVA**
```python
# Extracción con mejora continua
POST /api/projects/:id/extraction/iterate
"""
Ejecutar nueva iteración de extracción inteligente
Input: improvements_to_apply, context_updates
"""

GET /api/projects/:id/extraction/iterations
"""
Todas las iteraciones de extracción realizadas
Output: historial con scores y mejoras
"""

PUT /api/projects/:id/extraction/validate
"""
Validar y confirmar extracción actual
Input: human_validation, corrections
"""

POST /api/projects/:id/extraction/optimize
"""
Optimizar extracción usando feedback previo
"""
```

#### **CONFIGURACIÓN DINÁMICA DE PRESUPUESTOS**
```python
# Configuración flexible por contexto
GET /api/projects/:id/quote-configuration
"""
Configuración actual de presupuesto
Output: pricing_model, structure, terms
"""

PUT /api/projects/:id/quote-configuration
"""
Actualizar configuración de presupuesto
Input: nueva configuración validada
"""

GET /api/projects/:id/configuration-schema
"""
Schema de configuración dinámico basado en contexto
Output: campos y opciones disponibles por tipo proyecto
"""

POST /api/projects/:id/configuration/recommend
"""
Recomendaciones IA para configuración
Output: configuración sugerida con reasoning
"""
```

#### **GENERACIÓN INTELIGENTE Y EVALUACIÓN**
```python
# Generación contextual avanzada
POST /api/quotes/:id/generate-intelligent
"""
Generar presupuesto usando workflow completo
Input: finalized_configuration
Output: quote con metadata de generación
"""

GET /api/quotes/:id/generation-metadata
"""
Metadata completa del proceso de generación
Output: análisis, decisiones IA, calidad
"""

POST /api/quotes/:id/optimize
"""
Optimizar presupuesto generado
Input: optimization_criteria
"""

POST /api/quotes/:id/evaluate-quality
"""
Evaluar calidad del presupuesto generado
Output: scores detallados y sugerencias
"""
```

#### **TEMPLATES CONTEXTUALES**
```python
# Selección y personalización inteligente
GET /api/templates/contextual-selection/:project_id
"""
Selección inteligente de template basada en contexto
Output: template recomendado con reasoning
"""

POST /api/templates/:id/customize-for-context
"""
Personalizar template específicamente para contexto
Input: project_context, customization_preferences
"""

GET /api/templates/:id/preview-with-context/:project_id
"""
Preview de template aplicado al contexto específico
"""
```

---

## 4. COMPONENTES FRONTEND ACTUALIZADOS 🖥

### 4.1 Vistas Originales Mantenidas
- ✅ Dashboard principal
- ✅ Gestión de proyectos
- ✅ Sistema de plantillas
- ✅ Configuración de organización

### 4.2 Nuevas Vistas para Workflow Inteligente

#### **DASHBOARD DE WORKFLOW**
```ascii
┌─────────────────────────────────────────────────────────────┐
│ 🧠 ANÁLISIS INTELIGENTE - Boda Ana & Carlos                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ 🎯 CONTEXTO DETECTADO POR IA:                              │
│ Tipo: Catering para Boda | Invitados: ~150 | Budget: $$$  │
│ Complejidad: ████████▓▓ (82%) | Confianza: ████████▓▓ (87%)│
│                                                             │
│ 🔄 PROGRESO DEL WORKFLOW:                                   │
│ ✅ Análisis Contextual    ✅ Extracción Inteligente        │
│ ✅ Validación Automática  🔄 Revisión Humana (ACTUAL)      │
│ ⏳ Config. Presupuesto   ⏳ Generación Final               │
│                                                             │
│ ⚠️ REQUIERE ATENCIÓN:                                       │
│ • Confirmar servicios adicionales sugeridos por IA         │
│ • Validar estructura de costos por persona vs total        │
│                                                             │
│ [🔄 Continuar Workflow] [✏️ Intervenir] [👁️ Ver Detalles] │
└─────────────────────────────────────────────────────────────┘
```

#### **INTERFAZ DE HUMAN-IN-THE-LOOP**
```ascii
┌─────────────────────────────────────────────────────────────┐
│ 🤝 REVISIÓN HUMANA REQUERIDA                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ 🎯 LA IA NECESITA TU CONFIRMACIÓN:                          │
│                                                             │
│ EXTRACCIÓN DETECTADA:                                       │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ ✅ Cliente: Ana García & Carlos Rodríguez               │ │
│ │ ✅ Evento: Boda - 15 Marzo 2025                         │ │
│ │ ✅ Invitados: 150 personas                              │ │
│ │ ⚠️ Menú: Salmón + Lomito + Acompañantes                 │ │
│ │    [La IA detectó alta calidad pero precio no claro]    │ │
│ │ 🤔 Servicios: Personal + Coordinación                   │ │
│ │    [IA sugiere: "Típico para bodas de este nivel"]     │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ CONFIGURACIÓN RECOMENDADA POR IA:                          │
│ ◉ Costo por persona + servicios adicionales                │
│ ○ Costo total del proyecto                                  │
│ Razón: "Estándar para catering de bodas premium"           │
│                                                             │
│ [✅ Confirmar y Continuar] [✏️ Editar Antes] [🔄 Re-analizar]│
└─────────────────────────────────────────────────────────────┘
```

#### **CONFIGURACIÓN DINÁMICA**
```ascii
┌─────────────────────────────────────────────────────────────┐
│ ⚙️ CONFIGURACIÓN INTELIGENTE DE PRESUPUESTO                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ 💡 RECOMENDACIONES DE IA PARA ESTE CONTEXTO:               │
│                                                             │
│ ESTRUCTURA DE COSTOS: [Basado en análisis de 247 bodas]    │
│ ◉ Por persona ($53.51) + servicios extras                  │
│   ✓ Estándar para bodas premium                            │
│   ✓ Fácil comparación para cliente                         │
│ ○ Costo total del proyecto ($8,025.75)                     │
│   ✗ Menos transparente para eventos                        │
│                                                             │
│ SERVICIOS RECOMENDADOS: [IA detectó necesidades típicas]   │
│ ✅ Personal servicio (1 por cada 19 invitados) - $960      │
│ ✅ Coordinación evento (estándar bodas) - $300             │
│ 🤔 Transporte (25km detectado) - $150                      │
│ 🤔 Vajilla premium (implícito en documento) - $450         │
│                                                             │
│ TÉRMINOS INTELIGENTES:                                      │
│ ✅ 30% adelanto (típico bodas Venezuela)                   │
│ ✅ IVA 16% incluido                                         │
│ ✅ Validez 30 días (eventos con fecha fija)                │
│                                                             │
│ [🎨 Personalizar] [🚀 Usar Recomendado] [💾 Guardar]       │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. PLAN DE IMPLEMENTACIÓN PROGRESIVA 🚀

### **FASE 1: MVP CON CONTEXTO BÁSICO (Semanas 1-4)**

**Implementación mínima viable del workflow:**
- Orquestador básico con 3 tipos: catering, consultoría, general
- Extracción inteligente con 1 iteración
- Human-in-the-loop esencial
- Configuración básica dinámica
- 2 templates adaptativos

```bash
# Claude Code para Fase 1
claude-code "Create FastAPI project with PostgreSQL including 4 new context tables"
claude-code "Implement basic AI orchestrator for project context analysis"
claude-code "Build human-in-the-loop interface for validation and configuration"
claude-code "Create flexible quote configuration system with 3 pricing models"
```

### **FASE 2: WORKFLOW COMPLETO (Semanas 5-8)**

**Workflow inteligente completo:**
- Orquestador avanzado con 6+ tipos de proyecto
- Extracción iterativa con mejora continua
- Configuración completamente dinámica
- Evaluación de calidad automática
- Templates contextuales avanzados

```bash
# Claude Code para Fase 2
claude-code "Expand AI orchestrator with advanced context analysis for 6 project types"
claude-code "Implement iterative extraction system with confidence scoring"
claude-code "Create quality evaluation system with automated optimization"
claude-code "Build contextual template engine with intelligent customization"
```

### **FASE 3: OPTIMIZACIÓN IA (Semanas 9-12)**

**Optimizaciones avanzadas:**
- Fine-tuning de prompts por contexto
- Aprendizaje de decisiones humanas
- Optimización de costos de IA
- Analytics de performance del workflow

---

## 6. MÉTRICAS DE ÉXITO ACTUALIZADAS 📊

### **Métricas Técnicas del Workflow:**
- ✅ Precisión contexto: >85% en detección tipo proyecto
- ✅ Reducción intervención humana: <30% de casos
- ✅ Tiempo workflow completo: <10 minutos promedio
- ✅ Score calidad presupuestos: >90% casos

### **Métricas de Negocio:**
- ✅ Time-to-quote: <15 minutos vs 2+ horas manual
- ✅ Tasa conversión: +25% vs presupuestos manuales
- ✅ Satisfacción usuario: NPS >60
- ✅ Retención: Churn <5% mensual

### **Métricas de IA:**
- ✅ Costo por presupuesto: <$0.25 en prompts OpenAI
- ✅ Tokens promedio: <8,000 por workflow completo
- ✅ Precisión extracción: >90% campos críticos
- ✅ Confianza promedio: >85% en decisiones IA

---

## 🎯 RESUMEN EJECUTIVO

### **✅ LO QUE MANTIENE (85% original):**
- Toda la arquitectura multi-tenant robusta
- Sistema de roles y permisos granular
- 30 tablas originales intactas
- APIs básicas funcionando
- Frontend base con navegación

### **🚀 LO QUE AGREGA (15% nuevas funcionalidades):**
- **4 tablas nuevas** para contexto e inteligencia
- **Workflow contextual** que entiende como humano
- **Human-in-the-loop** inteligente
- **Configuración dinámica** por tipo de proyecto
- **15 endpoints adicionales** para workflow

### **💡 BENEFICIO DIFERENCIAL:**
- **3x más rápido** que competencia en generación
- **Presupuestos contextuales** vs extractores de texto
- **Configuración inteligente** vs templates rígidos
- **Workflow guiado** vs proceso manual completo

Este diseño mantiene la **solidez técnica original** mientras agrega la **inteligencia contextual** que diferencia el producto en el mercado.

**¿Apruebas proceder con esta especificación actualizada?** 🚀