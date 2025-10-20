# ✅ Actualización de Prompts - Estilo Sabra Corporation V2

**Fecha:** 2025-10-20  
**Basado en:** Imagen de referencia proporcionada por el usuario

---

## 🎨 Cambios Implementados

### 1. **Color Corporativo Actualizado**
- **Azul Sabra:** `#0e2541` (extraído de la imagen)
- **Texto blanco:** `#ffffff` sobre fondos azules
- **Bordes tabla:** `1pt solid #000`

### 2. **Información del Cliente en Cajas Azules**

**ANTES:** Texto simple sin formato especial

**DESPUÉS:** Cada campo en cajas con fondo azul y valor en caja blanca
```html
<div style="background: #0e2541; color: white; padding: 2mm 3mm; font-weight: bold;">Cliente:</div>
<div style="border: 1pt solid #0e2541; padding: 2mm 3mm;">[VALOR]</div>
```

Campos con cajas:
- ✅ Cliente
- ✅ Solicitud
- ✅ Empresa
- ✅ Fecha de evento
- ✅ Lugar

### 3. **Tabla de Productos con Header Azul**

**ANTES:** Header con fondo genérico

**DESPUÉS:** Header azul (#0e2541) con texto blanco
```html
<thead>
    <tr style="background: #0e2541; color: white;">
        <th style="color: white; font-weight: bold;">Item</th>
        <th style="color: white; font-weight: bold;">Descripción</th>
        <th style="color: white; font-weight: bold;">Cant</th>
        <th style="color: white; font-weight: bold;">Precio unitario</th>
        <th style="color: white; font-weight: bold;">Total</th>
    </tr>
</thead>
```

### 4. **Pricing Condicional - Solo Mostrar si > $0**

**ANTES:** Siempre mostraba Coordinación, Impuestos, Costo/persona (incluso si eran $0)

**DESPUÉS:** Lógica condicional implementada
```python
# En proposal_prompts.py
coord_val = pricing_data.get('coordination_formatted', '$0.00')
show_coordination = coord_val not in ['$0.00', '$0', '0']

# En el prompt
{f'<tr>...Coordinación...</tr>' if show_coordination else '<!-- Coordinación omitida -->'}
```

**Campos condicionales:**
- ✅ Coordinación: Solo si > $0
- ✅ Impuestos: Solo si > $0
- ✅ Costo por persona: Solo si > $0
- ✅ Subtotal: Siempre mostrar
- ✅ TOTAL: Siempre mostrar

### 5. **Pricing Dentro de la Tabla**

**ANTES:** Sección separada de pricing

**DESPUÉS:** Pricing integrado en la tabla de productos
```html
<tbody>
    <!-- Productos aquí -->
    
    <!-- Fila de Coordinación (si > $0) -->
    <tr>
        <td colspan="3">Coordinación y Logística</td>
        <td colspan="2" style="text-align: right;">$XXX.XX</td>
    </tr>
    
    <!-- Fila de TOTAL -->
    <tr>
        <td colspan="3"></td>
        <td style="font-weight: bold;">TOTAL</td>
        <td style="font-weight: bold; font-size: 12pt;">$XXX.XX</td>
    </tr>
</tbody>
```

### 6. **Términos y Condiciones Eliminados**

**ANTES:** Sección obligatoria de Términos y Condiciones

**DESPUÉS:** 🚫 Completamente eliminada según solicitud del usuario

### 7. **Comentarios HTML Agregados**

**ANTES:** HTML sin comentarios

**DESPUÉS:** Comentarios explicativos en cada sección
```html
<!-- HEADER -->
<div>...</div>

<!-- INFORMACIÓN DEL CLIENTE -->
<div>...</div>

<!-- TABLA DE PRODUCTOS -->
<table>...</table>

<!-- COMENTARIOS ADICIONALES -->
<div>...</div>
```

---

## 📁 Archivos Modificados

### 1. **`backend/services/prompts/proposal_prompts.py`**
- ✅ Reescrito completamente con nuevo estilo
- ✅ Lógica condicional para pricing
- ✅ Instrucciones basadas en imagen de referencia
- ✅ Eliminación de Términos y Condiciones
- ✅ Comentarios HTML obligatorios

### 2. **`backend/services/proposal_generator.py`** (ya modificado anteriormente)
- ✅ Función `_map_rfx_data_for_prompt()` para mapeo correcto de datos
- ✅ Integración con nuevos prompts

---

## 🎯 Resultado Esperado

### Layout del Presupuesto:

```
┌─────────────────────────────────────────────────┐
│ [LOGO]                      PRESUPUESTO         │
│                                                 │
│ Av. Principal, C.C Mini Centro Principal        │
│ Nivel 1, Local 10, Sector el Pedronal          │
│                                                 │
│                          Fecha: 2025-10-20      │
│                          Vigencia: 2025-11-20   │
│                          Código: SABRA-PO-XXX   │
├─────────────────────────────────────────────────┤
│ ┌─────────┐┌──────────────────────────────────┐│
│ │Cliente: ││ Chevron Global Technology...     ││
│ └─────────┘└──────────────────────────────────┘│
│                                                 │
│ ┌─────────┐┌──────────────────────────────────┐│
│ │Solicitud││ Evento corporativo...            ││
│ └─────────┘└──────────────────────────────────┘│
├─────────────────────────────────────────────────┤
│ ┌───────────────────────────────────────────┐  │
│ │ Item │ Descripción │ Cant │ Precio │ Total│  │
│ ├───────────────────────────────────────────┤  │
│ │  1   │ Producto 1  │  10  │ $10.00 │$100 │  │
│ │  2   │ Producto 2  │   5  │ $20.00 │$100 │  │
│ │      │ Coordinación y Logística   │ $50  │  │ (si > $0)
│ │      │              TOTAL          │ $250 │  │
│ └───────────────────────────────────────────┘  │
│                                                 │
│ Comentarios:                                    │
│ ┌─────────────────────────────────────────────┐│
│ │                                             ││
│ └─────────────────────────────────────────────┘│
└─────────────────────────────────────────────────┘
```

### Colores:
- **Cajas azules:** `#0e2541` con texto blanco
- **Header tabla:** `#0e2541` con texto blanco
- **Bordes:** Negro `#000`
- **Fondo:** Blanco

---

## 🧪 Testing

Para probar los cambios:

1. **Generar un presupuesto con branding:**
   ```bash
   # El sistema usará el nuevo prompt con estilo Sabra
   ```

2. **Verificar en logs:**
   ```
   ✅ Mapped data - client: Chevron..., products: 9
   📋 Building prompt with branding
   ```

3. **Verificar en HTML generado:**
   - ✅ Cajas azules para información del cliente
   - ✅ Header de tabla azul con texto blanco
   - ✅ Coordinación solo si > $0
   - ✅ Comentarios HTML presentes
   - ✅ NO hay Términos y Condiciones

---

## 📝 Notas Técnicas

### Lógica Condicional de Pricing:

```python
# Valores que se consideran "cero"
zero_values = ['$0.00', '$0', '0']

# Verificación
show_coordination = coord_val not in zero_values
```

### Formato de Cajas Azules:

```html
<div style="margin-bottom: 3mm;">
    <div style="background: #0e2541; color: white; padding: 2mm 3mm; 
                font-weight: bold; display: inline-block; min-width: 25mm;">
        Cliente:
    </div>
    <div style="border: 1pt solid #0e2541; padding: 2mm 3mm; 
                display: inline-block; min-width: 100mm;">
        [VALOR]
    </div>
</div>
```

### Unidades HTML-to-PDF:

- ✅ **Usar:** `mm`, `pt`, `in`
- 🚫 **NO usar:** `px`, `%`, `em`, `rem`, `vw`, `vh`

---

## ✅ Status: IMPLEMENTADO

Los prompts ahora generan presupuestos con el estilo exacto de la imagen de referencia de Sabra Corporation.

**Backup del archivo anterior:** `proposal_prompts_old.py`
