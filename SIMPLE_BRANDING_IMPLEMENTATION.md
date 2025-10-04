# 🎨 Plan Simplificado: Personalización de Documentos (Bajo Impacto)

## 📋 Resumen Ejecutivo

**Objetivo**: Permitir que usuarios adjunten logo y formato de presupuesto con **implementación mínima y rápida**.

**Filosofía**: 
- ✅ Usar infraestructura existente al máximo
- ✅ Evitar servicios complejos (S3, Vision AI costoso)
- ✅ Implementación incremental (MVP primero)
- ✅ Sin cambios grandes en arquitectura

**Tiempo estimado**: 1-2 semanas (vs 6 semanas del plan completo)

---

## 🎯 Enfoque Simplificado

### **Decisiones Clave de Simplificación**

| Aspecto | Plan Original | Plan Simplificado |
|---------|---------------|-------------------|
| **Storage** | S3 + CDN | Sistema de archivos local |
| **Análisis de IA** | GPT-4 Vision | Extracción básica con Pillow |
| **Tablas nuevas** | 3 tablas | 1 tabla |
| **Endpoints** | 6 endpoints | 3 endpoints |
| **Servicios** | 3 servicios nuevos | 1 servicio simple |
| **Complejidad** | Alta | Baja |

---

## 🗄️ Base de Datos Simplificada

### **Una sola tabla: `company_branding_assets`**

```sql
CREATE TABLE company_branding_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    
    -- Logo
    logo_filename TEXT,
    logo_path TEXT,
    logo_url TEXT,  -- URL relativa: /static/branding/{company_id}/logo.png
    
    -- Template (imagen o PDF del ejemplo)
    template_filename TEXT,
    template_path TEXT,
    template_url TEXT,  -- URL relativa: /static/branding/{company_id}/template.pdf
    
    -- Colores extraídos automáticamente (simple)
    primary_color VARCHAR(7) DEFAULT '#2c5f7c',  -- Hex color
    secondary_color VARCHAR(7) DEFAULT '#ffffff',
    
    -- Estado
    is_active BOOLEAN DEFAULT true,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraint: Una configuración por empresa
    UNIQUE(company_id)
);

-- Índice simple
CREATE INDEX idx_company_branding_company_id ON company_branding_assets(company_id);

-- Trigger para updated_at
CREATE TRIGGER update_company_branding_updated_at 
    BEFORE UPDATE ON company_branding_assets 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();
```

**Total**: 1 tabla, sin complejidad

---

## 🔌 API Endpoints Simplificados

### **Solo 3 endpoints necesarios**

#### 1. `POST /api/branding/upload`
**Descripción**: Sube logo Y/O template en una sola llamada

**Request** (multipart/form-data):
```
company_id: uuid
logo: file (opcional)
template: file (opcional)
```

**Response**:
```json
{
  "status": "success",
  "message": "Branding uploaded successfully",
  "logo_url": "/static/branding/{company_id}/logo.png",
  "template_url": "/static/branding/{company_id}/template.pdf",
  "primary_color": "#2c5f7c"
}
```

#### 2. `GET /api/branding/<company_id>`
**Descripción**: Obtiene configuración de branding

**Response**:
```json
{
  "status": "success",
  "company_id": "uuid",
  "logo_url": "/static/branding/{company_id}/logo.png",
  "template_url": "/static/branding/{company_id}/template.pdf",
  "primary_color": "#2c5f7c",
  "secondary_color": "#ffffff"
}
```

#### 3. `DELETE /api/branding/<company_id>`
**Descripción**: Elimina configuración de branding

---

## 🛠️ Implementación Backend Simplificada

### **1. Servicio Simple: `SimpleBrandingService`**

```python
# backend/services/simple_branding_service.py

import os
import uuid
from pathlib import Path
from typing import Optional, Dict
from PIL import Image
from werkzeug.utils import secure_filename

class SimpleBrandingService:
    """
    Servicio minimalista para branding personalizado
    Sin Vision AI, sin S3, solo lo esencial
    """
    
    def __init__(self):
        self.base_path = Path("backend/static/branding")
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def upload_logo(self, company_id: str, logo_file) -> Dict:
        """
        Sube logo y extrae color dominante simple
        """
        # 1. Crear directorio de empresa
        company_dir = self.base_path / company_id
        company_dir.mkdir(exist_ok=True)
        
        # 2. Guardar archivo
        filename = "logo.png"
        file_path = company_dir / filename
        logo_file.save(str(file_path))
        
        # 3. Extraer color dominante (simple con Pillow)
        primary_color = self._extract_dominant_color(file_path)
        
        # 4. Guardar en BD
        from backend.core.database import get_database_client
        db = get_database_client()
        
        db.execute("""
            INSERT INTO company_branding_assets 
                (company_id, logo_filename, logo_path, logo_url, primary_color)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (company_id) 
            DO UPDATE SET 
                logo_filename = EXCLUDED.logo_filename,
                logo_path = EXCLUDED.logo_path,
                logo_url = EXCLUDED.logo_url,
                primary_color = EXCLUDED.primary_color,
                updated_at = NOW()
        """, (company_id, filename, str(file_path), f"/static/branding/{company_id}/logo.png", primary_color))
        
        return {
            "logo_url": f"/static/branding/{company_id}/logo.png",
            "primary_color": primary_color
        }
    
    def upload_template(self, company_id: str, template_file) -> Dict:
        """
        Sube template de ejemplo (PDF o imagen)
        """
        company_dir = self.base_path / company_id
        company_dir.mkdir(exist_ok=True)
        
        # Detectar extensión
        ext = template_file.filename.split('.')[-1].lower()
        filename = f"template.{ext}"
        file_path = company_dir / filename
        template_file.save(str(file_path))
        
        # Guardar en BD
        from backend.core.database import get_database_client
        db = get_database_client()
        
        db.execute("""
            INSERT INTO company_branding_assets 
                (company_id, template_filename, template_path, template_url)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (company_id) 
            DO UPDATE SET 
                template_filename = EXCLUDED.template_filename,
                template_path = EXCLUDED.template_path,
                template_url = EXCLUDED.template_url,
                updated_at = NOW()
        """, (company_id, filename, str(file_path), f"/static/branding/{company_id}/{filename}"))
        
        return {
            "template_url": f"/static/branding/{company_id}/{filename}"
        }
    
    def get_branding(self, company_id: str) -> Optional[Dict]:
        """
        Obtiene configuración de branding
        """
        from backend.core.database import get_database_client
        db = get_database_client()
        
        result = db.query_one("""
            SELECT logo_url, template_url, primary_color, secondary_color
            FROM company_branding_assets
            WHERE company_id = %s AND is_active = true
        """, (company_id,))
        
        return result if result else None
    
    def _extract_dominant_color(self, image_path: Path) -> str:
        """
        Extrae color dominante de forma simple (sin IA)
        """
        try:
            img = Image.open(image_path)
            img = img.convert('RGB')
            img = img.resize((50, 50))  # Reducir para rapidez
            
            pixels = list(img.getdata())
            
            # Obtener color más común (simple)
            from collections import Counter
            most_common = Counter(pixels).most_common(1)[0][0]
            
            # Convertir a hex
            return f"#{most_common[0]:02x}{most_common[1]:02x}{most_common[2]:02x}"
        except:
            return "#2c5f7c"  # Fallback al azul Sabra
```

### **2. Endpoints Simples**

```python
# backend/api/branding.py

from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import logging

logger = logging.getLogger(__name__)

branding_bp = Blueprint("branding_api", __name__, url_prefix="/api/branding")

@branding_bp.route("/upload", methods=["POST"])
def upload_branding():
    """
    Sube logo y/o template
    """
    try:
        company_id = request.form.get('company_id')
        if not company_id:
            return jsonify({"status": "error", "message": "company_id required"}), 400
        
        from backend.services.simple_branding_service import SimpleBrandingService
        service = SimpleBrandingService()
        
        result = {}
        
        # Procesar logo si existe
        if 'logo' in request.files:
            logo_file = request.files['logo']
            if logo_file.filename:
                logo_result = service.upload_logo(company_id, logo_file)
                result.update(logo_result)
        
        # Procesar template si existe
        if 'template' in request.files:
            template_file = request.files['template']
            if template_file.filename:
                template_result = service.upload_template(company_id, template_file)
                result.update(template_result)
        
        return jsonify({
            "status": "success",
            "message": "Branding uploaded successfully",
            **result
        }), 200
        
    except Exception as e:
        logger.error(f"Error uploading branding: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@branding_bp.route("/<company_id>", methods=["GET"])
def get_branding(company_id: str):
    """
    Obtiene configuración de branding
    """
    try:
        from backend.services.simple_branding_service import SimpleBrandingService
        service = SimpleBrandingService()
        
        branding = service.get_branding(company_id)
        
        if not branding:
            return jsonify({
                "status": "success",
                "message": "No branding configured",
                "company_id": company_id,
                "logo_url": None,
                "template_url": None
            }), 200
        
        return jsonify({
            "status": "success",
            "company_id": company_id,
            **branding
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting branding: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@branding_bp.route("/<company_id>", methods=["DELETE"])
def delete_branding(company_id: str):
    """
    Elimina configuración de branding
    """
    try:
        from backend.core.database import get_database_client
        db = get_database_client()
        
        db.execute("""
            UPDATE company_branding_assets 
            SET is_active = false, updated_at = NOW()
            WHERE company_id = %s
        """, (company_id,))
        
        return jsonify({
            "status": "success",
            "message": "Branding deleted successfully"
        }), 200
        
    except Exception as e:
        logger.error(f"Error deleting branding: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
```

### **3. Integración Simplificada con Generación**

**Modificación mínima en `ProposalGenerationService`**:

```python
# En backend/services/proposal_generator.py

def _build_ai_prompt(self, rfx_data: Dict[str, Any], proposal_request: ProposalRequest) -> str:
    """
    Construye prompt con branding si existe
    """
    # ... código existente ...
    
    # 🆕 AGREGAR: Obtener branding si existe
    company_id = rfx_data.get("company_id")
    branding_context = ""
    logo_url = None
    
    if company_id:
        from backend.services.simple_branding_service import SimpleBrandingService
        branding_service = SimpleBrandingService()
        branding = branding_service.get_branding(company_id)
        
        if branding:
            logo_url = branding.get("logo_url")
            primary_color = branding.get("primary_color", "#2c5f7c")
            template_url = branding.get("template_url")
            
            branding_context = f"""
CONFIGURACIÓN DE BRANDING PERSONALIZADO:
- Logo de la empresa: {logo_url} (usar en header del documento)
- Color corporativo principal: {primary_color} (aplicar a títulos y elementos destacados)
- Template de referencia: {template_url if template_url else "No disponible"}

INSTRUCCIONES DE BRANDING:
1. Si hay logo_url, incluir en el HTML: <img src="{logo_url}" class="company-logo" style="max-width: 200px; height: auto;">
2. Usar el color {primary_color} para:
   - Nombre de la empresa (.company-name)
   - Títulos de sección
   - Bordes destacados
3. Si hay template de referencia, intentar replicar la estructura visual general
"""
    
    # Agregar contexto de branding al prompt
    prompt = f"""
{prompt_base}

{branding_context}

{resto_del_prompt}
"""
    
    return prompt
```

---

## 📂 Estructura de Archivos

```
backend/
├── static/
│   └── branding/
│       ├── {company_id_1}/
│       │   ├── logo.png
│       │   └── template.pdf
│       ├── {company_id_2}/
│       │   ├── logo.png
│       │   └── template.pdf
│       └── ...
├── services/
│   └── simple_branding_service.py  (NUEVO - 150 líneas)
└── api/
    └── branding.py  (NUEVO - 100 líneas)
```

**Total de código nuevo**: ~250 líneas

---

## 🚀 Plan de Implementación (1-2 Semanas)

### **Día 1-2: Base de Datos**
- ✅ Crear migración para tabla `company_branding_assets`
- ✅ Ejecutar migración en desarrollo
- ✅ Verificar constraints

### **Día 3-4: Backend Core**
- ✅ Crear `SimpleBrandingService`
- ✅ Implementar upload de logo con extracción de color
- ✅ Implementar upload de template
- ✅ Tests unitarios básicos

### **Día 5-6: API Endpoints**
- ✅ Crear `backend/api/branding.py`
- ✅ Implementar 3 endpoints
- ✅ Registrar blueprint en `app.py`
- ✅ Configurar static files serving

### **Día 7-8: Integración con Generación**
- ✅ Modificar `_build_ai_prompt()` en `ProposalGenerationService`
- ✅ Agregar contexto de branding al prompt
- ✅ Probar generación con y sin branding

### **Día 9-10: Testing y Ajustes**
- ✅ Tests de integración
- ✅ Validación de archivos
- ✅ Manejo de errores
- ✅ Documentación básica

---

## 🎯 Ventajas del Enfoque Simplificado

| Aspecto | Beneficio |
|---------|-----------|
| **Velocidad** | 1-2 semanas vs 6 semanas |
| **Complejidad** | Baja - solo 1 tabla, 3 endpoints |
| **Riesgo** | Mínimo - no afecta funcionalidad existente |
| **Costos** | Cero - sin APIs externas costosas |
| **Mantenimiento** | Simple - código fácil de entender |
| **Escalabilidad** | Suficiente para 100-500 empresas |

---

## 🔒 Validaciones Básicas

```python
# Validaciones simples en SimpleBrandingService

ALLOWED_LOGO_EXTENSIONS = {'png', 'jpg', 'jpeg', 'svg'}
ALLOWED_TEMPLATE_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}
MAX_LOGO_SIZE = 5 * 1024 * 1024  # 5MB
MAX_TEMPLATE_SIZE = 10 * 1024 * 1024  # 10MB

def validate_file(file, allowed_extensions, max_size):
    """Validación simple de archivo"""
    # 1. Verificar extensión
    ext = file.filename.split('.')[-1].lower()
    if ext not in allowed_extensions:
        raise ValueError(f"Extension not allowed: {ext}")
    
    # 2. Verificar tamaño
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    
    if size > max_size:
        raise ValueError(f"File too large: {size} bytes")
    
    return True
```

---

## 📊 Limitaciones Aceptables

| Limitación | Impacto | Mitigación |
|------------|---------|------------|
| Storage local | No escalable a millones | Suficiente para MVP, migrar a S3 después |
| Sin análisis IA avanzado | Menos precisión en colores | Extracción básica funciona en 80% casos |
| Sin versionado de assets | No historial de cambios | Agregar después si se necesita |
| Sin CDN | Latencia en carga | Agregar nginx/CDN después |

---

## 🔄 Migración Futura (Opcional)

Si el sistema crece, migración incremental:

```
Fase 1 (Actual): Local storage + extracción simple
    ↓
Fase 2: Agregar S3 para storage (sin cambiar API)
    ↓
Fase 3: Agregar Vision AI para análisis avanzado
    ↓
Fase 4: Agregar versionado y historial
```

**Ventaja**: API no cambia, solo implementación interna

---

## 📝 Registro en `app.py`

```python
# backend/app.py

# Agregar import
from backend.api.branding import branding_bp

# Registrar blueprint
app.register_blueprint(branding_bp)

# Configurar static files
app.config['BRANDING_FOLDER'] = 'backend/static/branding'
```

---

## 🧪 Testing Rápido

```python
# tests/test_simple_branding.py

def test_upload_logo():
    """Test básico de upload"""
    service = SimpleBrandingService()
    
    # Mock file
    with open('test_logo.png', 'rb') as f:
        result = service.upload_logo('test-company-id', f)
    
    assert result['logo_url'] is not None
    assert result['primary_color'].startswith('#')

def test_get_branding():
    """Test de obtención"""
    service = SimpleBrandingService()
    branding = service.get_branding('test-company-id')
    
    assert branding is not None
    assert 'logo_url' in branding
```

---

## 📦 Dependencias Mínimas

```txt
# Agregar a requirements.txt
Pillow>=10.0.0  # Para extracción de colores
```

**Total**: 1 dependencia nueva

---

## ✅ Checklist de Implementación

### Backend
- [ ] Crear migración de BD
- [ ] Implementar `SimpleBrandingService`
- [ ] Crear endpoints en `branding.py`
- [ ] Registrar blueprint en `app.py`
- [ ] Modificar `ProposalGenerationService`
- [ ] Agregar validaciones
- [ ] Tests básicos

### Frontend (Futuro)
- [ ] Formulario de upload
- [ ] Preview de logo
- [ ] Gestión de branding

---

## 🎯 Resultado Final

**Con esta implementación simplificada**:

✅ Usuario puede subir logo y template
✅ Sistema extrae color dominante automáticamente
✅ IA usa logo y colores en generación
✅ Implementación en 1-2 semanas
✅ Sin complejidad innecesaria
✅ Fácil de mantener y extender

**Ejemplo de uso**:
```bash
# Subir branding
curl -X POST http://localhost:5000/api/branding/upload \
  -F "company_id=abc-123" \
  -F "logo=@logo.png" \
  -F "template=@template.pdf"

# Generar propuesta (automáticamente usa branding)
curl -X POST http://localhost:5000/api/proposals/generate \
  -H "Content-Type: application/json" \
  -d '{"rfx_id": "xyz-789", "costs": [100, 200]}'
```

---

**Documento creado**: 2024-09-30
**Versión**: 2.0 - Simplificada
**Tiempo estimado**: 1-2 semanas
**Complejidad**: Baja ⭐⭐☆☆☆
