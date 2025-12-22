# 🎨 Guía de Implementación - Sistema de Branding Personalizado

## ✅ Implementación Completada

Se ha implementado exitosamente el sistema de branding personalizado que permite a cada empresa adjuntar su logo y template de presupuesto para generar documentos personalizados.

---

## 📋 Resumen de Implementación

### **Enfoque Final**
- ✅ **Logo**: Se usa DIRECTAMENTE en el HTML (NO se analiza ni recrea)
- ✅ **Template**: Se analiza SOLO el formato visual (colores, espaciados, distribución, orden)
- ✅ **Análisis**: Se hace UNA VEZ y se cachea en base de datos
- ✅ **Generación**: Usa análisis cacheado (rápido, sin costos repetidos)

---

## 🗄️ 1. Migración de Base de Datos

### **Archivo**: `Database/migration_branding_v1.sql`

**Ejecutar migración**:
```bash
# Conectar a tu base de datos PostgreSQL
psql -U tu_usuario -d tu_base_de_datos -f Database/migration_branding_v1.sql
```

**Tabla creada**: `company_branding_assets`
- Almacena logo y template por empresa
- Campos JSONB para análisis cacheado:
  - `logo_analysis`: Colores extraídos del logo
  - `template_analysis`: Formato visual del template
- Estado de análisis: `pending`, `analyzing`, `completed`, `failed`

---

## 🔧 2. Dependencias

### **Ya incluidas en requirements.txt**:
- `Pillow==10.1.0` - Extracción de colores del logo
- `pdf2image==1.16.3` - Conversión de PDF a imagen para análisis
- `openai>=1.7.2` - GPT-4 Vision para análisis de template

### **Instalar dependencias**:
```bash
pip install -r requirements.txt
```

### **Dependencia del sistema (para pdf2image)**:
```bash
# macOS
brew install poppler

# Ubuntu/Debian
sudo apt-get install poppler-utils

# Windows
# Descargar desde: https://github.com/oschwartz10612/poppler-windows/releases/
```

---

## 🚀 3. Iniciar el Backend

```bash
# Desde el directorio raíz del proyecto
python start_backend.py

# O directamente
python backend/app.py
```

El servidor estará disponible en: `http://localhost:5000`

---

## 📡 4. Endpoints API

### **4.1. Subir Branding**

**Endpoint**: `POST /api/branding/upload`

**Request** (multipart/form-data):
```bash
curl -X POST http://localhost:5000/api/branding/upload \
  -F "company_id=tu-company-uuid" \
  -F "logo=@/ruta/a/logo.png" \
  -F "template=@/ruta/a/template.pdf"
```

**Response**:
```json
{
  "status": "success",
  "company_id": "tu-company-uuid",
  "logo_url": "/static/branding/tu-company-uuid/logo.png",
  "template_url": "/static/branding/tu-company-uuid/template.pdf",
  "analysis_status": "analyzing",
  "message": "Files uploaded successfully. Analysis in progress."
}
```

**Notas**:
- El análisis se ejecuta **asíncronamente** (no bloquea la respuesta)
- Tarda aproximadamente 10-15 segundos
- Puedes verificar el estado con el endpoint de status

---

### **4.2. Verificar Estado del Análisis**

**Endpoint**: `GET /api/branding/analysis-status/<company_id>`

**Request**:
```bash
curl http://localhost:5000/api/branding/analysis-status/tu-company-uuid
```

**Response** (en progreso):
```json
{
  "status": "success",
  "analysis_status": "analyzing",
  "progress": "Analyzing logo and template with AI...",
  "error": null
}
```

**Response** (completado):
```json
{
  "status": "success",
  "analysis_status": "completed",
  "progress": "Analysis completed successfully",
  "error": null,
  "completed_at": "2024-10-01T16:30:00Z"
}
```

---

### **4.3. Obtener Configuración de Branding**

**Endpoint**: `GET /api/branding/<company_id>`

**Request**:
```bash
curl http://localhost:5000/api/branding/tu-company-uuid
```

**Response**:
```json
{
  "status": "success",
  "company_id": "tu-company-uuid",
  "has_branding": true,
  "logo_url": "/static/branding/tu-company-uuid/logo.png",
  "template_url": "/static/branding/tu-company-uuid/template.pdf",
  "logo_analysis": {
    "primary_color": "#2c5f7c",
    "secondary_color": "#ffffff",
    "dominant_colors": ["#2c5f7c", "#ffffff", "#f0f0f0"]
  },
  "template_analysis": {
    "layout_structure": "header-client-products-totals",
    "color_scheme": {
      "primary": "#2c5f7c",
      "backgrounds": ["#f0f0f0"],
      "borders": "#000000"
    },
    "table_style": {
      "has_borders": true,
      "border_width": "1px",
      "header_background": "#f0f0f0"
    },
    "typography": {
      "font_family": "Arial, sans-serif",
      "company_name_size": "24px",
      "body_size": "11px"
    }
  },
  "analysis_status": "completed"
}
```

---

### **4.4. Re-analizar Branding**

**Endpoint**: `POST /api/branding/reanalyze/<company_id>`

**Uso**: Si el usuario no está satisfecho con el análisis o cambió el template

**Request**:
```bash
curl -X POST http://localhost:5000/api/branding/reanalyze/tu-company-uuid
```

---

### **4.5. Eliminar Branding**

**Endpoint**: `DELETE /api/branding/<company_id>`

**Request**:
```bash
curl -X DELETE http://localhost:5000/api/branding/tu-company-uuid
```

**Nota**: Marca como inactivo, no elimina archivos físicos

---

## 🎯 5. Generación de Presupuestos con Branding

### **Flujo Automático**

Una vez configurado el branding, **NO necesitas hacer nada adicional**. El sistema automáticamente:

1. Detecta si la empresa tiene branding configurado
2. Lee el análisis cacheado de la base de datos
3. Incluye el contexto de branding en el prompt de IA
4. Genera el presupuesto con:
   - Logo insertado en el HTML
   - Colores corporativos aplicados
   - Estructura del template respetada

### **Endpoint Existente**

```bash
POST /api/proposals/generate
```

**Request** (igual que antes):
```json
{
  "rfx_id": "uuid-del-rfx",
  "costs": [100, 200, 300],
  "notes": "Notas adicionales"
}
```

**El sistema automáticamente**:
- ✅ Obtiene `company_id` del RFX
- ✅ Busca branding configurado
- ✅ Usa análisis cacheado si existe
- ✅ Genera presupuesto personalizado

---

## 🔍 6. Cómo Funciona Internamente

### **6.1. Análisis del Logo (Mínimo)**

**Archivo**: `backend/services/vision_analysis_service.py`

```python
async def analyze_logo(image_path):
    # Solo extrae colores básicos con Pillow
    # NO usa GPT-4 Vision
    # El logo se usa DIRECTAMENTE en el HTML
    return {
        "primary_color": "#2c5f7c",
        "secondary_color": "#ffffff",
        "dominant_colors": ["#2c5f7c", "#ffffff"]
    }
```

**Importante**: El logo NO se analiza con IA, solo se extraen colores de referencia.

---

### **6.2. Análisis del Template (Solo Formato)**

**Archivo**: `backend/services/vision_analysis_service.py`

```python
async def analyze_template(template_path):
    # Usa GPT-4 Vision
    # Analiza SOLO formato visual:
    # - Colores
    # - Espaciados
    # - Distribución
    # - Orden de secciones
    # NO analiza contenido textual ni datos
```

**Prompt enviado a GPT-4 Vision**:
```
Analiza ÚNICAMENTE el FORMATO VISUAL de este documento.

IMPORTANTE: NO analices contenido textual ni datos específicos.
Solo analiza:
- Formato y estructura visual
- Colores utilizados
- Espaciados y márgenes
- Distribución de elementos
- Orden de las secciones
```

---

### **6.3. Generación con Branding**

**Archivo**: `backend/services/proposal_generator.py`

```python
async def generate_proposal(rfx_data, proposal_request):
    # 1. Obtener branding si existe
    company_id = rfx_data.get("company_id")
    branding_context = self._get_branding_context(company_id)
    
    # 2. Construir prompt con branding
    if branding_context:
        prompt = self._build_ai_prompt_with_branding(
            rfx_data,
            proposal_request,
            branding_context  # ← Análisis cacheado
        )
    
    # 3. Generar HTML con IA
    html = await self._call_openai(prompt)
    
    # 4. El HTML ya incluye el logo y estilos personalizados
    return html
```

---

## 📊 7. Estructura de Archivos

```
backend/
├── static/
│   └── branding/
│       └── {company_id}/
│           ├── logo.png          ← Logo original
│           └── template.pdf      ← Template de referencia
│
├── services/
│   ├── vision_analysis_service.py      ← Análisis con IA
│   ├── optimized_branding_service.py   ← Gestión de branding
│   └── proposal_generator.py           ← Generación con branding
│
├── api/
│   └── branding.py                     ← Endpoints API
│
└── app.py                              ← Blueprint registrado

Database/
└── migration_branding_v1.sql           ← Migración de BD
```

---

## 🧪 8. Testing

### **8.1. Test Manual Completo**

```bash
# 1. Subir branding
curl -X POST http://localhost:5000/api/branding/upload \
  -F "company_id=test-company-123" \
  -F "logo=@test_logo.png" \
  -F "template=@test_template.pdf"

# 2. Esperar 15 segundos para análisis

# 3. Verificar estado
curl http://localhost:5000/api/branding/analysis-status/test-company-123

# 4. Ver configuración completa
curl http://localhost:5000/api/branding/test-company-123

# 5. Generar presupuesto (usa branding automáticamente)
curl -X POST http://localhost:5000/api/proposals/generate \
  -H "Content-Type: application/json" \
  -d '{
    "rfx_id": "rfx-con-company-test-company-123",
    "costs": [100, 200]
  }'
```

---

### **8.2. Verificar en Base de Datos**

```sql
-- Ver branding configurado
SELECT 
    company_id,
    logo_url,
    template_url,
    analysis_status,
    created_at
FROM company_branding_assets
WHERE is_active = true;

-- Ver análisis cacheado
SELECT 
    company_id,
    logo_analysis->>'primary_color' as primary_color,
    template_analysis->>'layout_structure' as layout,
    analysis_status
FROM company_branding_assets
WHERE company_id = 'test-company-123';
```

---

## ⚠️ 9. Troubleshooting

### **Problema**: Análisis se queda en "analyzing"

**Solución**:
```bash
# Ver logs del backend
tail -f backend.log

# Verificar error en BD
SELECT analysis_error FROM company_branding_assets 
WHERE company_id = 'tu-company-id';
```

---

### **Problema**: "pdf2image not installed"

**Solución**:
```bash
pip install pdf2image
brew install poppler  # macOS
```

---

### **Problema**: Logo no aparece en el presupuesto

**Verificar**:
1. Análisis completado: `analysis_status = 'completed'`
2. Logo URL existe: `logo_url` no es NULL
3. Archivo existe: Verificar en `backend/static/branding/{company_id}/`

---

## 📈 10. Performance y Costos

### **Análisis Inicial** (Una vez por empresa)
- **Tiempo**: 10-15 segundos
- **Costo**: ~$0.02 (GPT-4 Vision para template)
- **Frecuencia**: Solo al subir o cambiar branding

### **Generación de Presupuesto** (Cada vez)
- **Tiempo**: 5-8 segundos (igual que antes)
- **Costo**: ~$0.02 (sin costo adicional de análisis)
- **Frecuencia**: Cada presupuesto generado

### **Ahorro**
- **Sin cache**: $0.05 por presupuesto (análisis + generación)
- **Con cache**: $0.02 por presupuesto (solo generación)
- **Ahorro**: 60% en costos repetidos

---

## 🎯 11. Próximos Pasos

### **Para Desarrollo**
1. ✅ Migración de BD ejecutada
2. ✅ Backend funcionando
3. ⏳ Testing con datos reales
4. ⏳ Integración con frontend

### **Para Frontend**
1. Crear interfaz de upload de logo
2. Crear interfaz de upload de template
3. Mostrar preview de configuración
4. Indicador de estado de análisis

---

## 📞 12. Soporte

### **Archivos de Referencia**
- **Plan completo**: `OPTIMIZED_BRANDING_IMPLEMENTATION.md`
- **Migración BD**: `Database/migration_branding_v1.sql`
- **Servicios**: `backend/services/vision_analysis_service.py`
- **API**: `backend/api/branding.py`

### **Logs**
```bash
# Ver logs en tiempo real
tail -f backend.log

# Filtrar por branding
grep "branding" backend.log
grep "🎨" backend.log
```

---

## ✅ Checklist de Implementación

- [x] Migración de base de datos ejecutada
- [x] Dependencias instaladas (`pip install -r requirements.txt`)
- [x] Poppler instalado (para pdf2image)
- [x] Backend iniciado y funcionando
- [x] Directorio `backend/static/branding/` creado
- [ ] Test de upload completado
- [ ] Test de análisis verificado
- [ ] Test de generación con branding verificado
- [ ] Integración con frontend iniciada

---

**Implementación completada**: 2024-10-01
**Versión**: 1.0
**Estado**: ✅ Listo para testing
