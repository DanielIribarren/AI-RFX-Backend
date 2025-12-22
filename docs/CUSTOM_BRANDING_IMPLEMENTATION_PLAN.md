# 🎨 Plan de Implementación: Personalización de Documentos con Logo y Formato

## 📋 Resumen Ejecutivo

Este documento detalla el plan completo para implementar la funcionalidad que permite a los usuarios personalizar la generación de presupuestos mediante:
1. **Logo personalizado** de la empresa del usuario
2. **Formato/template personalizado** del presupuesto

### Objetivo
Permitir que cada usuario adjunte su logo corporativo y un ejemplo de formato de presupuesto para que el modelo de IA genere documentos personalizados que reflejen la identidad visual y estructura preferida del usuario.

---

## 🔍 Análisis del Sistema Actual

### Componentes Identificados

#### 1. **Generación de Propuestas**
- **Archivo**: `backend/services/proposal_generator.py`
- **Clase**: `ProposalGenerationService`
- **Funcionalidad actual**:
  - Usa un template HTML fijo (`test_design.html`)
  - Genera propuestas mediante OpenAI con prompt estructurado
  - Almacena HTML generado en base de datos
  - Soporta configuraciones de pricing dinámicas

#### 2. **API de Propuestas**
- **Archivo**: `backend/api/proposals.py`
- **Endpoints**:
  - `POST /api/proposals/generate` - Genera propuesta
  - `GET /api/proposals/<proposal_id>` - Obtiene propuesta
  - `GET /api/proposals/rfx/<rfx_id>/proposals` - Lista propuestas por RFX

#### 3. **Conversión a PDF**
- **Archivo**: `backend/api/download.py`
- **Funcionalidad**:
  - Conversión HTML → PDF con Playwright
  - Optimización de estilos para PDF
  - Descarga de documentos

#### 4. **Base de Datos**
- **Schema**: `Database/Complete-Schema-V2.2.sql`
- **Tablas relevantes**:
  - `companies` - Empresas
  - `rfx_v2` - Solicitudes RFX
  - `generated_documents` - Documentos generados
  - `rfx_pricing_configurations` - Configuraciones de pricing

---

## 🏗️ Arquitectura de la Solución

### Componentes Nuevos a Implementar

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (Futuro)                        │
│  - Upload de logo (imagen)                                  │
│  - Upload de template ejemplo (PDF/imagen)                  │
│  - Gestión de configuraciones por empresa                   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    BACKEND (A Implementar)                  │
│                                                             │
│  1. API Endpoints:                                          │
│     - POST /api/branding/logo                               │
│     - POST /api/branding/template                           │
│     - GET /api/branding/<company_id>                        │
│     - PUT /api/branding/<company_id>                        │
│     - DELETE /api/branding/<company_id>                     │
│                                                             │
│  2. Storage Service:                                        │
│     - Almacenamiento de archivos (S3/local)                 │
│     - Procesamiento de imágenes                             │
│     - Extracción de información de templates                │
│                                                             │
│  3. Vision AI Integration:                                  │
│     - Análisis de logo (colores, dimensiones)               │
│     - Análisis de template (estructura, layout)             │
│     - Extracción de elementos visuales                      │
│                                                             │
│  4. Enhanced Proposal Generator:                            │
│     - Inyección de logo en HTML                             │
│     - Aplicación de estilos personalizados                  │
│     - Generación basada en template de referencia           │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    DATABASE                                 │
│                                                             │
│  Nuevas Tablas:                                             │
│  - company_branding_configurations                          │
│  - branding_assets (logos, templates)                       │
│  - branding_analysis_cache                                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 Diseño de Base de Datos

### Nuevas Tablas

#### 1. `company_branding_configurations`
```sql
CREATE TABLE company_branding_configurations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    
    -- Estado de la configuración
    is_active BOOLEAN DEFAULT true,
    configuration_name TEXT DEFAULT 'Default Branding',
    
    -- Referencias a assets
    logo_asset_id UUID REFERENCES branding_assets(id),
    template_asset_id UUID REFERENCES branding_assets(id),
    
    -- Configuración de colores extraídos del logo
    primary_color VARCHAR(7),  -- Hex color #RRGGBB
    secondary_color VARCHAR(7),
    accent_color VARCHAR(7),
    
    -- Configuración de tipografía
    font_family TEXT DEFAULT 'Arial, sans-serif',
    font_size_base INTEGER DEFAULT 11,
    
    -- Preferencias de layout
    layout_preferences JSONB DEFAULT '{}',
    
    -- Metadatos
    created_by TEXT,
    updated_by TEXT,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraint: Solo una configuración activa por empresa
    CONSTRAINT unique_active_branding_per_company 
        EXCLUDE (company_id WITH =) WHERE (is_active = true)
);
```

#### 2. `branding_assets`
```sql
CREATE TYPE asset_type AS ENUM ('logo', 'template_example', 'watermark', 'signature');
CREATE TYPE asset_status AS ENUM ('uploaded', 'processing', 'ready', 'failed');

CREATE TABLE branding_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    
    -- Información del asset
    asset_type asset_type NOT NULL,
    asset_name TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    
    -- Almacenamiento
    file_path TEXT NOT NULL,  -- Ruta en storage (S3 o local)
    file_url TEXT,  -- URL pública si aplica
    file_size_bytes INTEGER,
    mime_type TEXT NOT NULL,
    
    -- Dimensiones (para imágenes)
    width_px INTEGER,
    height_px INTEGER,
    
    -- Estado del procesamiento
    status asset_status DEFAULT 'uploaded',
    processing_error TEXT,
    
    -- Análisis de IA (almacenado como JSONB)
    ai_analysis JSONB DEFAULT '{}',
    -- Ejemplo para logo:
    -- {
    --   "dominant_colors": ["#2c5f7c", "#ffffff"],
    --   "has_transparency": true,
    --   "recommended_position": "top-left",
    --   "optimal_size": {"width": 200, "height": 80}
    -- }
    -- Ejemplo para template:
    -- {
    --   "layout_structure": "header-table-footer",
    --   "has_logo_space": true,
    --   "table_columns": 4,
    --   "color_scheme": ["#2c5f7c", "#f0f0f0"],
    --   "sections_detected": ["header", "client_info", "products", "totals"]
    -- }
    
    -- Versión (para control de cambios)
    version INTEGER DEFAULT 1,
    replaces_asset_id UUID REFERENCES branding_assets(id),
    
    -- Metadatos
    uploaded_by TEXT,
    metadata JSONB DEFAULT '{}',
    
    -- Timestamps
    uploaded_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ,
    
    -- Índices
    CONSTRAINT valid_dimensions CHECK (
        (width_px IS NULL AND height_px IS NULL) OR 
        (width_px > 0 AND height_px > 0)
    )
);

CREATE INDEX idx_branding_assets_company_id ON branding_assets(company_id);
CREATE INDEX idx_branding_assets_type ON branding_assets(asset_type);
CREATE INDEX idx_branding_assets_status ON branding_assets(status);
```

#### 3. `branding_usage_history`
```sql
CREATE TABLE branding_usage_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    branding_config_id UUID NOT NULL REFERENCES company_branding_configurations(id) ON DELETE CASCADE,
    document_id UUID REFERENCES generated_documents(id) ON DELETE SET NULL,
    
    -- Información de uso
    used_logo BOOLEAN DEFAULT false,
    used_template BOOLEAN DEFAULT false,
    
    -- Resultado
    generation_successful BOOLEAN DEFAULT true,
    generation_notes TEXT,
    
    -- Timestamp
    used_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_branding_usage_config_id ON branding_usage_history(branding_config_id);
CREATE INDEX idx_branding_usage_document_id ON branding_usage_history(document_id);
```

---

## 🔌 API Endpoints a Implementar

### 1. **Gestión de Logo**

#### `POST /api/branding/logo`
**Descripción**: Sube un logo para una empresa

**Request**:
```json
{
  "company_id": "uuid",
  "file": "multipart/form-data",
  "replace_existing": false
}
```

**Response**:
```json
{
  "status": "success",
  "message": "Logo uploaded successfully",
  "asset_id": "uuid",
  "asset_url": "https://...",
  "ai_analysis": {
    "dominant_colors": ["#2c5f7c", "#ffffff"],
    "recommended_size": {"width": 200, "height": 80}
  }
}
```

#### `GET /api/branding/logo/<company_id>`
**Descripción**: Obtiene el logo activo de una empresa

**Response**:
```json
{
  "status": "success",
  "logo": {
    "asset_id": "uuid",
    "url": "https://...",
    "uploaded_at": "2024-01-01T00:00:00Z"
  }
}
```

### 2. **Gestión de Template**

#### `POST /api/branding/template`
**Descripción**: Sube un ejemplo de formato de presupuesto

**Request**:
```json
{
  "company_id": "uuid",
  "file": "multipart/form-data (PDF o imagen)",
  "description": "Formato estándar para propuestas técnicas"
}
```

**Response**:
```json
{
  "status": "success",
  "message": "Template uploaded successfully",
  "asset_id": "uuid",
  "ai_analysis": {
    "layout_structure": "header-table-footer",
    "sections_detected": ["header", "client_info", "products", "totals"],
    "color_scheme": ["#2c5f7c", "#f0f0f0"]
  }
}
```

### 3. **Configuración Completa**

#### `GET /api/branding/config/<company_id>`
**Descripción**: Obtiene la configuración completa de branding

**Response**:
```json
{
  "status": "success",
  "config": {
    "company_id": "uuid",
    "is_active": true,
    "logo": {
      "asset_id": "uuid",
      "url": "https://...",
      "colors": ["#2c5f7c"]
    },
    "template": {
      "asset_id": "uuid",
      "url": "https://...",
      "layout": "header-table-footer"
    },
    "colors": {
      "primary": "#2c5f7c",
      "secondary": "#ffffff"
    }
  }
}
```

#### `PUT /api/branding/config/<company_id>`
**Descripción**: Actualiza configuración de branding

#### `DELETE /api/branding/config/<company_id>`
**Descripción**: Elimina configuración de branding

---

## 🤖 Integración con IA

### 1. **Análisis de Logo (Vision AI)**

**Tecnología**: OpenAI GPT-4 Vision o similar

**Funcionalidad**:
```python
async def analyze_logo(image_path: str) -> dict:
    """
    Analiza un logo y extrae:
    - Colores dominantes
    - Dimensiones óptimas
    - Posición recomendada
    - Si tiene transparencia
    """
    # Usar GPT-4 Vision para análisis
    prompt = """
    Analiza este logo corporativo y proporciona:
    1. Los 3 colores dominantes en formato hex
    2. Dimensiones recomendadas para uso en documentos
    3. Posición óptima (top-left, top-center, top-right)
    4. Si tiene fondo transparente
    """
    
    response = await openai_vision_call(image_path, prompt)
    return parse_logo_analysis(response)
```

### 2. **Análisis de Template (Vision AI)**

**Funcionalidad**:
```python
async def analyze_template(template_path: str) -> dict:
    """
    Analiza un template de presupuesto y extrae:
    - Estructura del layout
    - Secciones identificadas
    - Esquema de colores
    - Formato de tabla
    - Posición de elementos clave
    """
    prompt = """
    Analiza este ejemplo de presupuesto y describe:
    1. Estructura general del documento (header, body, footer)
    2. Secciones presentes (info cliente, productos, totales)
    3. Colores utilizados en el diseño
    4. Formato de la tabla de productos (columnas, estilos)
    5. Elementos visuales importantes (bordes, fondos, etc.)
    """
    
    response = await openai_vision_call(template_path, prompt)
    return parse_template_analysis(response)
```

### 3. **Generación Personalizada**

**Modificación en `ProposalGenerationService`**:
```python
async def generate_proposal(
    self, 
    rfx_data: Dict[str, Any], 
    proposal_request: ProposalRequest
) -> GeneratedProposal:
    """
    Genera propuesta con branding personalizado
    """
    # 1. Obtener configuración de branding
    company_id = rfx_data.get("company_id")
    branding_config = await self.branding_service.get_active_config(company_id)
    
    # 2. Si hay branding personalizado, usarlo
    if branding_config:
        # Obtener logo
        logo_url = branding_config.get("logo", {}).get("url")
        logo_analysis = branding_config.get("logo", {}).get("ai_analysis", {})
        
        # Obtener template analysis
        template_analysis = branding_config.get("template", {}).get("ai_analysis", {})
        
        # 3. Construir prompt mejorado con contexto visual
        ai_prompt = self._build_custom_branded_prompt(
            rfx_data=rfx_data,
            proposal_request=proposal_request,
            logo_url=logo_url,
            logo_analysis=logo_analysis,
            template_analysis=template_analysis
        )
    else:
        # Usar prompt estándar
        ai_prompt = self._build_ai_prompt(rfx_data, proposal_request)
    
    # 4. Generar HTML con IA
    html_content = await self._call_openai(ai_prompt)
    
    # 5. Post-procesamiento: inyectar logo en HTML
    if branding_config and logo_url:
        html_content = self._inject_logo_in_html(html_content, logo_url, logo_analysis)
    
    # 6. Guardar y retornar
    proposal = self._create_proposal_object(rfx_data, html_content, proposal_request)
    await self._save_to_database(proposal)
    
    return proposal
```

---

## 📝 Servicios Backend a Crear

### 1. **BrandingService** (`backend/services/branding_service.py`)

```python
class BrandingService:
    """
    Servicio para gestión de branding personalizado
    """
    
    async def upload_logo(
        self, 
        company_id: str, 
        file: UploadFile
    ) -> BrandingAsset:
        """Sube y procesa un logo"""
        pass
    
    async def upload_template(
        self, 
        company_id: str, 
        file: UploadFile
    ) -> BrandingAsset:
        """Sube y analiza un template"""
        pass
    
    async def get_active_config(
        self, 
        company_id: str
    ) -> Optional[BrandingConfig]:
        """Obtiene configuración activa de branding"""
        pass
    
    async def analyze_logo_with_ai(
        self, 
        image_path: str
    ) -> dict:
        """Analiza logo con Vision AI"""
        pass
    
    async def analyze_template_with_ai(
        self, 
        template_path: str
    ) -> dict:
        """Analiza template con Vision AI"""
        pass
```

### 2. **StorageService** (`backend/services/storage_service.py`)

```python
class StorageService:
    """
    Servicio para almacenamiento de archivos
    """
    
    async def save_file(
        self, 
        file: UploadFile, 
        directory: str
    ) -> str:
        """Guarda archivo en storage (local o S3)"""
        pass
    
    async def get_file_url(
        self, 
        file_path: str
    ) -> str:
        """Obtiene URL pública del archivo"""
        pass
    
    async def delete_file(
        self, 
        file_path: str
    ) -> bool:
        """Elimina archivo del storage"""
        pass
```

### 3. **VisionAIService** (`backend/services/vision_ai_service.py`)

```python
class VisionAIService:
    """
    Servicio para análisis de imágenes con IA
    """
    
    async def analyze_image(
        self, 
        image_path: str, 
        analysis_type: str
    ) -> dict:
        """Analiza imagen con GPT-4 Vision"""
        pass
    
    def extract_colors_from_image(
        self, 
        image_path: str
    ) -> List[str]:
        """Extrae colores dominantes de una imagen"""
        pass
```

---

## 🔄 Flujo de Implementación

### Fase 1: Base de Datos y Modelos (Semana 1)
1. ✅ Crear migraciones de base de datos
2. ✅ Implementar modelos Pydantic para branding
3. ✅ Crear funciones de base de datos

### Fase 2: Storage y Upload (Semana 2)
1. ✅ Implementar `StorageService`
2. ✅ Crear endpoints de upload
3. ✅ Validación de archivos (tamaño, tipo, dimensiones)
4. ✅ Tests unitarios

### Fase 3: Análisis con IA (Semana 3)
1. ✅ Implementar `VisionAIService`
2. ✅ Integrar GPT-4 Vision para análisis de logo
3. ✅ Integrar GPT-4 Vision para análisis de template
4. ✅ Cacheo de análisis

### Fase 4: Integración con Generación (Semana 4)
1. ✅ Modificar `ProposalGenerationService`
2. ✅ Crear prompts mejorados con contexto visual
3. ✅ Inyección de logo en HTML generado
4. ✅ Aplicación de estilos personalizados

### Fase 5: API y Testing (Semana 5)
1. ✅ Completar todos los endpoints
2. ✅ Tests de integración
3. ✅ Documentación de API
4. ✅ Optimización de performance

### Fase 6: Frontend Integration (Semana 6)
1. ✅ Interfaz de upload de logo
2. ✅ Interfaz de upload de template
3. ✅ Preview de configuración
4. ✅ Testing end-to-end

---

## 🔒 Consideraciones de Seguridad

### 1. **Validación de Archivos**
- Validar tipo MIME
- Limitar tamaño de archivo (max 5MB para logos, 10MB para templates)
- Escanear por malware
- Validar dimensiones de imagen

### 2. **Almacenamiento**
- Nombres de archivo únicos (UUID)
- Separación por empresa
- Permisos de acceso controlados
- Backup automático

### 3. **Procesamiento**
- Timeout en análisis de IA (max 30 segundos)
- Rate limiting en uploads
- Validación de ownership (usuario solo puede subir para su empresa)

---

## 📊 Estimación de Recursos

### Storage
- **Logo**: ~100KB - 500KB por empresa
- **Template**: ~500KB - 2MB por empresa
- **Estimación**: 100 empresas × 2.5MB = 250MB

### Costos de IA
- **Análisis de logo**: ~$0.01 por análisis (GPT-4 Vision)
- **Análisis de template**: ~$0.02 por análisis
- **Generación con contexto**: +$0.005 por generación

### Performance
- **Upload + análisis**: 5-10 segundos
- **Generación con branding**: +2-3 segundos vs estándar
- **Cache de análisis**: Reduce costos en 90%

---

## 🎯 Métricas de Éxito

1. **Adopción**: >70% de empresas configuran branding
2. **Satisfacción**: >90% de usuarios satisfechos con resultado
3. **Performance**: <15 segundos para generación completa
4. **Precisión**: >95% de logos correctamente posicionados
5. **Consistencia**: >90% de templates respetados en estructura

---

## 📚 Próximos Pasos

### Inmediatos (Esta Semana)
1. ✅ Revisar y aprobar este plan
2. ✅ Crear branch de desarrollo `feature/custom-branding`
3. ✅ Implementar migraciones de base de datos
4. ✅ Crear modelos Pydantic

### Corto Plazo (Próximas 2 Semanas)
1. ✅ Implementar servicios de storage
2. ✅ Crear endpoints de upload
3. ✅ Integrar Vision AI

### Mediano Plazo (Próximo Mes)
1. ✅ Completar integración con generación
2. ✅ Testing completo
3. ✅ Documentación
4. ✅ Deploy a staging

---

## 🤝 Dependencias

### Librerías Python Nuevas
```txt
# Para procesamiento de imágenes
Pillow>=10.0.0
python-magic>=0.4.27

# Para storage (si usamos S3)
boto3>=1.28.0

# Para análisis de colores
colorthief>=0.2.1
```

### APIs Externas
- **OpenAI GPT-4 Vision**: Para análisis de imágenes
- **AWS S3** (opcional): Para almacenamiento en la nube

---

## 📞 Contacto y Soporte

Para preguntas sobre este plan:
- **Arquitectura**: Revisar con equipo de backend
- **IA/Vision**: Consultar documentación de OpenAI Vision
- **Frontend**: Coordinar con equipo de UI/UX

---

**Documento creado**: 2024-09-30
**Versión**: 1.0
**Estado**: Pendiente de aprobación
