# 🔧 FIX: user_id NULL en RFX - Problema y Solución

## 📊 Problema Identificado

Cuando se crea un RFX mediante `/api/rfx/process`, el campo `user_id` **NO se está guardando** en la tabla `rfx_v2`, quedando como `NULL`.

### Evidencia del Log:
```
🔍 DEBUG: user_id from rfx_data: None
⚠️ user_id is None in rfx_data, attempting to get from RFX DB
✅ Retrieved user_id from DB: None  ← ❌ PROBLEMA: user_id es NULL en BD
⚠️ user_id still None, using known fallback from memories
🔧 Using fallback user_id: 186ea35f-3cf8-480f-a7d3-0af178c09498
```

### Impacto:
- ❌ No se puede recuperar el branding del usuario correcto
- ❌ Sistema usa fallback hardcodeado (user_id de memorias)
- ❌ Template-based generation falla porque no encuentra el usuario real
- ❌ Logo funciona por casualidad (usa fallback user_id)

---

## 🔍 Análisis del Flujo Actual

### 1. Frontend envía RFX (POST `/api/rfx/process`)
```javascript
// Frontend NO envía user_id actualmente
FormData {
  files: [archivo.pdf],
  tipo_rfx: "catering",
  // ❌ FALTA: user_id
}
```

### 2. Backend procesa RFX (`rfx_processor.py` línea 2330-2349)
```python
rfx_data = {
    "id": str(rfx_processed.id),
    "company_id": company_record.get("id"),
    "requester_id": requester_record.get("id"),
    "rfx_type": rfx_processed.rfx_type.value,
    # ... otros campos ...
    # ❌ FALTA: "user_id": ???
}
```

### 3. Database guarda RFX sin user_id (`database.py` línea 168-182)
```python
def insert_rfx(self, rfx_data: Dict[str, Any]) -> Dict[str, Any]:
    # Simplemente inserta lo que recibe
    response = self.client.table("rfx_v2").insert(rfx_data).execute()
    # Si rfx_data no tiene user_id, se guarda como NULL
```

---

## ✅ Solución Implementada (Temporal)

### Fix 1: Remover columna inexistente `analysis_completed_at`
**Archivo:** `backend/core/database.py` línea 791-798

**ANTES:**
```python
select_fields = (
    "user_id, "
    "logo_filename, logo_path, logo_url, logo_uploaded_at, "
    "template_filename, template_path, template_url, template_uploaded_at, "
    "logo_analysis, template_analysis, "
    "analysis_status, analysis_error, "
    "analysis_started_at, analysis_completed_at, "  # ❌ NO EXISTE
    "is_active, created_at, updated_at"
)
```

**DESPUÉS:**
```python
select_fields = (
    "user_id, "
    "logo_filename, logo_path, logo_url, logo_uploaded_at, "
    "template_filename, template_path, template_url, template_uploaded_at, "
    "logo_analysis, template_analysis, "
    "analysis_status, analysis_error, "
    "analysis_started_at, "  # ✅ REMOVIDO analysis_completed_at
    "is_active, created_at, updated_at"
)
```

**Resultado:** Query a `company_branding_assets` ahora funciona correctamente.

---

## 🎯 Solución Definitiva Requerida

### Opción A: Frontend envía user_id (RECOMENDADO)

#### 1. Frontend debe obtener user_id del usuario autenticado
```javascript
// En el componente de creación de RFX
const userId = getCurrentUserId(); // Desde contexto de autenticación

const formData = new FormData();
formData.append('files', file);
formData.append('tipo_rfx', 'catering');
formData.append('user_id', userId); // ✅ AGREGAR ESTO
```

#### 2. Backend recibe y usa user_id
**Archivo:** `backend/api/rfx.py` línea 31-178

```python
@rfx_bp.route("/process", methods=["POST"])
def process_rfx():
    # ... código existente ...
    
    # 🆕 AGREGAR: Obtener user_id del request
    user_id = request.form.get('user_id')
    
    if not user_id:
        return jsonify({
            "status": "error",
            "message": "user_id is required",
            "error": "Missing user_id"
        }), 400
    
    # Pasar user_id al procesador
    processor_service = RFXProcessorService()
    rfx_processed = processor_service.process_rfx_case(
        rfx_input, 
        valid_files,
        user_id=user_id  # ✅ PASAR user_id
    )
```

#### 3. RFXProcessorService guarda user_id
**Archivo:** `backend/services/rfx_processor.py` línea 2330-2349

```python
def _save_to_database_v2(self, rfx_processed: RFXProcessed, user_id: str):
    """Save processed RFX to database V2.0 schema"""
    try:
        # ... código existente ...
        
        rfx_data = {
            "id": str(rfx_processed.id),
            "user_id": user_id,  # ✅ AGREGAR ESTO
            "company_id": company_record.get("id"),
            "requester_id": requester_record.get("id"),
            # ... resto de campos ...
        }
        
        rfx_record = self.db_client.insert_rfx(rfx_data)
```

---

### Opción B: Backend infiere user_id desde autenticación

Si el backend tiene middleware de autenticación:

```python
from flask import g

@rfx_bp.route("/process", methods=["POST"])
@require_auth  # Middleware que establece g.user_id
def process_rfx():
    user_id = g.user_id  # Obtener desde contexto de autenticación
    
    # ... resto del código ...
```

---

## 🧪 Testing

### 1. Verificar que user_id se guarda correctamente
```bash
# Crear RFX con user_id
curl -X POST http://localhost:5000/api/rfx/process \
  -F "files=@test.pdf" \
  -F "tipo_rfx=catering" \
  -F "user_id=186ea35f-3cf8-480f-a7d3-0af178c09498"

# Verificar en logs:
# ✅ RFX inserted successfully: <rfx_id>

# Consultar RFX creado
curl http://localhost:5000/api/rfx/<rfx_id>

# Verificar que user_id NO sea null:
# "user_id": "186ea35f-3cf8-480f-a7d3-0af178c09498"
```

### 2. Verificar template-based generation
```bash
# Generar propuesta - debería usar template del usuario correcto
curl -X POST http://localhost:5000/api/proposals/generate \
  -H "Content-Type: application/json" \
  -d '{"rfx_id": "<rfx_id>"}'

# Logs esperados:
# 🎯 Attempting template-based generation for user: 186ea35f-3cf8-480f-a7d3-0af178c09498
# ✅ Retrieved branding data for user: 186ea35f-3cf8-480f-a7d3-0af178c09498
# ✅ Found HTML template with X placeholders
# 🚀 Template-based generation successful!
```

---

## 📝 Checklist de Implementación

### Backend (Opción A - user_id desde frontend):
- [ ] Modificar `/api/rfx/process` para recibir `user_id` del request
- [ ] Validar que `user_id` no sea None/vacío
- [ ] Pasar `user_id` a `RFXProcessorService.process_rfx_case()`
- [ ] Modificar `_save_to_database_v2()` para incluir `user_id` en `rfx_data`
- [ ] Agregar logs de debug para rastrear `user_id`

### Frontend:
- [ ] Obtener `user_id` del contexto de autenticación
- [ ] Incluir `user_id` en FormData al crear RFX
- [ ] Manejar error si backend rechaza por falta de `user_id`

### Testing:
- [ ] Crear RFX y verificar que `user_id` se guarda en BD
- [ ] Generar propuesta y verificar que usa template del usuario correcto
- [ ] Verificar logs: sin fallbacks a user_id hardcodeado

---

## 🎯 Estado Actual

### ✅ Completado:
- Fix columna `analysis_completed_at` inexistente
- Query a `company_branding_assets` ahora funciona

### ⏳ Pendiente:
- Implementar paso de `user_id` desde frontend → backend → database
- Requiere coordinación con equipo de frontend
- Testing end-to-end con user_id real

---

## 💡 Workaround Temporal

Mientras se implementa la solución definitiva, el sistema usa fallback:

```python
# En proposal_generator.py línea 95-115
user_id = rfx_data.get("user_id")

if not user_id:
    # Fallback 1: Consultar BD
    rfx_result = db.client.table("rfx_v2").select("user_id").eq("id", rfx_id).single().execute()
    user_id = rfx_result.data.get("user_id")

if not user_id:
    # Fallback 2: User ID conocido (de memorias)
    user_id = "186ea35f-3cf8-480f-a7d3-0af178c09498"
    logger.warning(f"⚠️ Using fallback user_id: {user_id}")
```

**Limitación:** Solo funciona para el usuario hardcodeado. Multi-usuario requiere fix definitivo.
