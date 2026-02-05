# 🤖 Catalog Import System - AI-First Architecture

**Fecha:** 2 de Febrero, 2026  
**Versión:** 2.0 - AI-First Simple

---

## 🎯 PROBLEMA RESUELTO

### **Antes (Sistema Complejo):**
- ❌ Dos servicios duplicados (sync + async)
- ❌ Mapeo hardcodeado limitado
- ❌ No detectaba columnas como "Descripción" o "Precio Unitario"
- ❌ Lógica de matching débil con falsos positivos
- ❌ Productos con código duplicado en nombre (PRD-0001 → PRD-0001)

### **Ahora (AI-First Simple):**
- ✅ Un solo servicio: `CatalogImportService`
- ✅ AI mapea columnas inteligentemente (sin hardcoding)
- ✅ Detecta cualquier variación de nombres de columnas
- ✅ Mapeo consistente: Código Excel → Código DB, Nombre Excel → Nombre DB
- ✅ Upsert inteligente por código primero, luego nombre

---

## 🏗️ ARQUITECTURA

### **Flujo Completo:**

```
1. Usuario sube Excel/CSV
   ↓
2. Pandas parsea archivo → DataFrame
   ↓
3. AI lee columnas del Excel
   ↓
4. AI mapea a columnas de BD (semántico)
   ↓
5. Validación de mapeo crítico
   ↓
6. Extracción de productos con mapeo correcto
   ↓
7. Upsert inteligente (por código primero)
   ↓
8. Invalidación de cache Redis
   ↓
9. Retornar estadísticas
```

---

## 📋 COLUMNAS DE BASE DE DATOS

```python
DB_SCHEMA = {
    'product_code': 'Código único del producto (SKU, referencia, código)',
    'product_name': 'Nombre descriptivo del producto',
    'unit_cost': 'Costo unitario (número decimal)',
    'unit_price': 'Precio de venta unitario (número decimal)',
    'unit': 'Unidad de medida (opcional: kg, unidad, caja, etc.)'
}
```

---

## 🤖 MAPEO INTELIGENTE CON AI

### **Prompt al AI:**

```
Eres un experto en mapeo de datos de catálogos de productos.

COLUMNAS DEL EXCEL DEL CLIENTE:
["Codigo", "Descripción", "Costo Unitario", "Precio de Venta", "Unidad"]

COLUMNAS REQUERIDAS EN BASE DE DATOS:
{
  "product_code": "Código único del producto",
  "product_name": "Nombre descriptivo del producto",
  "unit_cost": "Costo unitario",
  "unit_price": "Precio de venta unitario",
  "unit": "Unidad de medida"
}

REGLAS CRÍTICAS:
1. product_code = Columna con códigos/SKU (ej: "PRD-0001")
2. product_name = Columna con nombres (ej: "Tequeños")
3. unit_cost = Columna con costos
4. unit_price = Columna con precios
5. unit = Columna con unidades

IMPORTANTE:
- NO confundas código con nombre
- Responde SOLO con JSON
```

### **Respuesta del AI:**

```json
{
  "product_code": "Codigo",
  "product_name": "Descripción",
  "unit_cost": "Costo Unitario",
  "unit_price": "Precio de Venta",
  "unit": "Unidad"
}
```

---

## ✅ VALIDACIÓN DE MAPEO

### **Validaciones Automáticas:**

1. **Columnas críticas presentes:**
   - `product_code` (requerido)
   - `product_name` (requerido)

2. **Columnas existen en Excel:**
   - Verifica que cada columna mapeada existe en el archivo

3. **Logs detallados:**
   ```
   🤖 AI mapping: {'product_code': 'Codigo', 'product_name': 'Descripción'}
   ✅ Mapping validation passed
   ```

---

## 📊 EXTRACCIÓN DE PRODUCTOS

### **Proceso:**

```python
for row in dataframe:
    product = {
        'organization_id': org_id,
        'product_code': row[mapping['product_code']],  # ← Mapeo correcto
        'product_name': row[mapping['product_name']],  # ← Mapeo correcto
        'unit_cost': float(row[mapping['unit_cost']]),
        'unit_price': float(row[mapping['unit_price']]),
        'unit': row[mapping['unit']],
        'is_active': True
    }
```

### **Resultado Garantizado:**

| Excel Column | DB Column | Ejemplo |
|--------------|-----------|---------|
| Codigo | product_code | PRD-0001 |
| Descripción | product_name | Tequeños de Queso |
| Costo Unitario | unit_cost | 3.05 |
| Precio de Venta | unit_price | 4.43 |
| Unidad | unit | kg |

---

## 🔄 UPSERT INTELIGENTE

### **Estrategia de Búsqueda:**

```python
# 1. Buscar por product_code (más confiable)
existing = db.find_by_code(product_code)

# 2. Fallback: buscar por nombre si no encontró
if not existing:
    existing = db.find_by_name(product_name)

# 3. Update o Insert
if existing:
    db.update(existing.id, product)  # Update
else:
    db.insert(product)  # Insert
```

### **Beneficios:**

- ✅ Evita duplicados por código
- ✅ Actualiza productos existentes
- ✅ Fallback robusto por nombre
- ✅ Logs detallados de cada operación

---

## 📦 RESPUESTA DE LA API

### **Endpoint:**

```
POST /api/catalog/import
Content-Type: multipart/form-data
Authorization: Bearer <token>

Body:
- file: catalog.xlsx
```

### **Respuesta Exitosa:**

```json
{
  "status": "success",
  "products_imported": 50,
  "products_updated": 10,
  "duration_seconds": 2.3,
  "mapping_used": {
    "product_code": "Codigo",
    "product_name": "Descripción",
    "unit_cost": "Costo Unitario",
    "unit_price": "Precio de Venta",
    "unit": "Unidad"
  }
}
```

### **Respuesta de Error:**

```json
{
  "status": "error",
  "message": "AI mapping missing critical columns: ['product_name']"
}
```

---

## 🗑️ ARCHIVOS ELIMINADOS (BASURA)

- ❌ `backend/services/catalog_import_service_sync.py` (194 líneas)
- ❌ `backend/api/catalog.py` (versión async obsoleta)

---

## ✅ ARCHIVOS ACTUALES

- ✅ `backend/services/catalog_import_service.py` (260 líneas) - AI-First
- ✅ `backend/api/catalog_sync.py` - Endpoint actualizado

---

## 🧪 TESTING

### **Caso 1: Excel con columnas estándar**

```
Columnas: ["Codigo", "Nombre", "Costo", "Precio"]
Resultado: ✅ Mapeo correcto automático
```

### **Caso 2: Excel con columnas variadas**

```
Columnas: ["SKU", "Descripción del Producto", "Costo Unitario", "Precio de Venta"]
Resultado: ✅ AI detecta y mapea correctamente
```

### **Caso 3: Excel con columnas en inglés**

```
Columnas: ["Code", "Product Name", "Cost", "Price"]
Resultado: ✅ AI detecta y mapea correctamente
```

---

## 📊 LOGS DE EJEMPLO

```
📥 Starting AI-First catalog import for org abc-123
📊 Parsed 60 rows with columns: ['Codigo', 'Descripción', 'Costo Unitario', 'Precio de Venta']
🤖 AI mapping: {'product_code': 'Codigo', 'product_name': 'Descripción', 'unit_cost': 'Costo Unitario', 'unit_price': 'Precio de Venta'}
✅ Mapping validation passed
✅ Extracted 60 products
✅ Saved 50 new, 10 updated products
```

---

## 🚀 VENTAJAS DEL SISTEMA AI-FIRST

### **1. Flexibilidad Total**
- Detecta cualquier nombre de columna
- No requiere configuración manual
- Funciona con Excel en español, inglés, etc.

### **2. Simplicidad**
- Un solo servicio (260 líneas)
- Lógica clara y directa
- Sin mapeos hardcodeados

### **3. Inteligencia**
- AI entiende contexto semántico
- Distingue código de nombre
- Maneja variaciones de nombres

### **4. Consistencia Garantizada**
- Código Excel → Código DB (siempre)
- Nombre Excel → Nombre DB (siempre)
- Costos y precios correctos (siempre)

### **5. Mantenibilidad**
- Código limpio y legible
- Fácil de extender
- Logs detallados para debugging

---

## 🔧 CONFIGURACIÓN

### **Dependencias:**

```python
# requirements.txt
pandas>=2.0.0
openpyxl>=3.1.0  # Para Excel
openai>=1.0.0
redis>=5.0.0  # Opcional
```

### **Variables de Entorno:**

```bash
OPENAI_API_KEY=sk-...
REDIS_URL=redis://localhost:6379  # Opcional
```

---

## 📝 PRÓXIMOS PASOS (OPCIONAL)

### **Mejoras Futuras:**

1. **Preview de Mapeo:**
   - Mostrar al usuario el mapeo antes de importar
   - Permitir ajustes manuales si es necesario

2. **Validación de Datos:**
   - Verificar que códigos sean únicos
   - Validar rangos de precios razonables

3. **Importación Incremental:**
   - Solo importar filas nuevas/modificadas
   - Detectar cambios en productos existentes

4. **Reportes Detallados:**
   - Productos duplicados detectados
   - Productos con datos faltantes
   - Sugerencias de limpieza

---

## ✅ ESTADO FINAL

| Componente | Estado | Notas |
|------------|--------|-------|
| Servicio AI-First | ✅ Implementado | 260 líneas, simple y claro |
| Endpoint /import | ✅ Actualizado | Usa servicio AI-First |
| Mapeo Inteligente | ✅ Funcional | Detecta cualquier columna |
| Upsert por Código | ✅ Implementado | Busca por código primero |
| Validación | ✅ Implementado | Columnas críticas + existencia |
| Logs Detallados | ✅ Implementado | Debugging completo |

**Sistema:** ✅ LISTO PARA PRODUCCIÓN

**Complejidad:** ⬇️ REDUCIDA (de 2 servicios a 1)

**Inteligencia:** ⬆️ MEJORADA (AI semántico vs hardcoded)
