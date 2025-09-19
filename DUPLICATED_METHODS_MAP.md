# 📋 **Mapeo de Métodos Duplicados - DatabaseClient**

## 🔍 **MÉTODOS REDUNDANTES IDENTIFICADOS**

### **🎯 EN USO ACTIVO (Requieren consolidación cuidadosa)**

| Legacy Method               | Modern Equivalent         | Used In                                               | Status      |
| --------------------------- | ------------------------- | ----------------------------------------------------- | ----------- |
| `get_rfx_by_id()`           | `get_project_by_id()`     | `rfx.py` (8x), `proposals.py` (1x), `pricing.py` (2x) | **11 usos** |
| `insert_rfx()`              | `insert_project()`        | **NO ENCONTRADO**                                     | **0 usos**  |
| `get_proposals_by_rfx_id()` | `get_quotes_by_project()` | **NO ENCONTRADO**                                     | **0 usos**  |

### **🚨 MÉTODOS CON USO ACTIVO (Requieren updates sistemáticos)**

| Legacy Method              | Modern Equivalent                | Active Uses | Files Affected                          |
| -------------------------- | -------------------------------- | ----------- | --------------------------------------- |
| `get_rfx_history()`        | `get_projects_by_organization()` | **4 usos**  | `rfx.py`                                |
| `get_latest_rfx()`         | `get_latest_projects()`          | **3 usos**  | `rfx.py`                                |
| `get_rfx_products()`       | `get_project_items()`            | **8 usos**  | `rfx.py`, `proposals.py`, `pricing.py`  |
| `find_rfx_by_identifier()` | `find_project_by_identifier()`   | **5 usos**  | `pricing.py`                            |
| `get_document_by_id()`     | `get_quote_by_id()`              | **3 usos**  | `proposals.py`, `app.py`, `download.py` |
| `update_rfx_status()`      | `update_project_status()`        | **1 uso**   | `rfx.py`                                |

### **⚠️ MÉTODOS SIN USO DIRECTO (Eliminables)**

| Legacy Method               | Modern Equivalent        | Implementation                | Status            |
| --------------------------- | ------------------------ | ----------------------------- | ----------------- |
| `insert_rfx()`              | `insert_project()`       | Mapeo `_map_rfx_to_project()` | **✅ Eliminable** |
| `insert_rfx_products()`     | `insert_project_items()` | Direct call                   | **✅ Eliminable** |
| `save_generated_document()` | `insert_quote()`         | Direct call                   | **✅ Eliminable** |
| `update_rfx_data()`         | `update_project_data()`  | Direct call                   | **✅ Eliminable** |

## 🚨 **MÉTODO CRÍTICO: `get_rfx_by_id()`**

**USAGES ENCONTRADOS:**

- `backend/api/rfx.py`: 8 llamadas
- `backend/api/proposals.py`: 1 llamada
- `backend/api/pricing.py`: 2 llamadas
- **TOTAL: 11 llamadas activas**

**IMPACTO:** Este método es el único realmente usado. Los demás parecen ser legacy sin uso.

## 📊 **ESTRATEGIA DE CONSOLIDACIÓN**

### **FASE 1: Consolidar método crítico**

1. Reemplazar `get_rfx_by_id()` calls → `get_project_by_id()`
2. Añadir adaptador en endpoints para response format
3. Mantener temporalmente el método legacy

### **FASE 2: Eliminar métodos sin uso**

1. Verificar que no hay uso indirecto
2. Eliminar métodos con 0 references
3. Mantener solo aliases críticos

### **FASE 3: Cleanup final**

1. Eliminar funciones de mapeo obsoletas
2. Consolidar documentación
3. Tests de regresión

## 🎯 **PLAN DE ACCIÓN INMEDIATO**

```python
# STEP 1: Identificar transformaciones necesarias
get_rfx_by_id() → get_project_by_id() + format_adapter_if_needed()

# STEP 2: Update APIs sistemáticamente
rfx.py:609         → Actualizar + adapter
proposals.py:80    → Actualizar + adapter
pricing.py:52,195  → Actualizar + adapter

# STEP 3: Eliminar métodos legacy
- Eliminar 9 métodos sin uso
- Mantener get_rfx_by_id() como alias temporal
```

## ✅ **CRITERIO DE ÉXITO**

- ✅ 0 regresiones en APIs existentes
- ✅ Response format idéntico
- ✅ Reducción ~10 métodos redundantes
- ✅ Código más limpio y mantenible
