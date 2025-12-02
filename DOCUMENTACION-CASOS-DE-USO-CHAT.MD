# 📋 CASOS DE USO: MODIFICACIÓN DE RFX
## Documentación Conceptual Breve

**Proyecto:** AI-RFX Backend  
**Feature:** Actualización Conversacional de RFX  
**Fecha:** Noviembre 27, 2025  
**Versión:** 1.0

---

## 🎯 OVERVIEW

Esta documentación cubre **TODOS** los casos de uso de cómo un usuario puede modificar un RFX existente usando el chat conversacional.

**Métodos de actualización:**
1. **Texto simple** - Usuario escribe lo que necesita
2. **Archivo adjunto** - Usuario sube PDF/imagen con cambios
3. **Combinado** - Texto + archivo

---

## 📊 CATEGORÍAS DE MODIFICACIÓN

```
┌─────────────────────────────────────────────────┐
│              TIPOS DE MODIFICACIÓN              │
├─────────────────────────────────────────────────┤
│                                                 │
│  1. AGREGAR      → Productos nuevos             │
│  2. MODIFICAR    → Cantidades, precios, info    │
│  3. ELIMINAR     → Quitar productos             │
│  4. REEMPLAZAR   → Cambio completo de RFX       │
│  5. CORREGIR     → Arreglar errores             │
│  6. CONSULTAR    → Preguntar (sin cambios)      │
│                                                 │
└─────────────────────────────────────────────────┘
```

---

## 1️⃣ AGREGAR PRODUCTOS

### 1.1 Agregar Producto Simple (Texto)

**Usuario escribe:**
```
"Agregar 20 refrescos"
"Necesito 50 servilletas"
"Incluir 10 manteles blancos"
```

**Agente hace:**
1. Identifica: Intent = "agregar productos"
2. Extrae: nombre="Refrescos", cantidad=20
3. Busca en catálogo (si existe precio)
4. Agrega al RFX
5. Calcula nuevo total

**RFX antes:**
```
1. Pasos salados (50) - $250.00
2. Café y té (20)     - $40.00
────────────────────────────────
Total: $290.00
```

**RFX después:**
```
1. Pasos salados (50)  - $250.00
2. Café y té (20)      - $40.00
3. 🆕 Refrescos (20)   - $50.00  ← Nuevo con glow
────────────────────────────────
Total: $340.00  ← Actualizado
```

**Frecuencia:** ⭐⭐⭐⭐⭐ (Muy común, ~40%)

---

### 1.2 Agregar Múltiples Productos (Texto)

**Usuario escribe:**
```
"Agregar:
- 20 refrescos
- 30 jugos naturales
- 50 servilletas decoradas"
```

**Agente hace:**
1. Detecta lista de productos
2. Procesa cada uno individualmente
3. Agrega todos al RFX
4. Calcula nuevo total

**RFX después:**
```
...productos anteriores...
3. 🆕 Refrescos (20)           - $50.00
4. 🆕 Jugos naturales (30)     - $90.00
5. 🆕 Servilletas decoradas (50) - $25.00
────────────────────────────────
Total: $505.00
```

**Frecuencia:** ⭐⭐⭐ (Común, ~15%)

---

### 1.3 Agregar Desde Archivo (Sin Duplicados)

**Usuario adjunta:**
- PDF con nueva solicitud
- Imagen de lista escrita a mano
- Documento Word

**Usuario escribe (opcional):**
```
"Cliente envió productos adicionales"
```

**Agente hace:**
1. Extrae productos del archivo
2. Compara con RFX actual
3. Identifica solo productos nuevos
4. Agrega solo los nuevos

**Ejemplo:**
```
Archivo contiene:
- Bocadillos dulces (30)
- Bebidas frías (15)

RFX ya tiene:
- (nada similar)

Resultado: Agrega ambos ✅
```

**Frecuencia:** ⭐⭐⭐ (Común, ~15%)

---

### 1.4 Agregar Desde Archivo (CON Duplicados) ⚠️

**Escenario más complejo y frecuente**

**Usuario adjunta:** PDF que tiene productos nuevos Y productos que ya existen

**Archivo contiene:**
```
- Pasos salados (50)        ← Ya existe
- Café y té (20)            ← Ya existe
- Pasos dulces (30)         ← NUEVO
- Jugos naturales (15)      ← NUEVO
```

**RFX actual tiene:**
```
1. Pasos salados variados (50)  ← Similar
2. Café y té (20)               ← Exacto
```

**Agente detecta:**
1. "Pasos salados" vs "Pasos salados variados" → 95% similar ⚠️
2. "Café y té" → 100% exacto ⚠️
3. "Pasos dulces" → No existe ✅
4. "Jugos naturales" → No existe ✅

**Agente pregunta:**
```
⚠️ Encontré productos duplicados:

Del archivo:
• Pasos salados (50)
• Café y té (20)

Ya existen en el RFX:
• Pasos salados variados (50)
• Café y té (20)

Productos nuevos detectados:
• Pasos dulces (30)
• Jugos naturales (15)

¿Qué deseas hacer?

1️⃣ Solo agregar productos nuevos ⭐
   (Ignora duplicados, agrega: Pasos dulces, Jugos)
   
2️⃣ Agregar todo como productos independientes
   (Mantiene existentes + agrega todo del archivo)
   
3️⃣ Reemplazar productos existentes
   (Elimina antiguos, usa versión del archivo)
```

**Usuario selecciona:** "1" (más común)

**Resultado:**
```
RFX actualizado:
1. Pasos salados variados (50)  - $250.00  ← Mantiene
2. Café y té (20)               - $40.00   ← Mantiene
3. 🆕 Pasos dulces (30)         - $90.00   ← Agrega
4. 🆕 Jugos naturales (15)      - $45.00   ← Agrega
────────────────────────────────────────────
Total: $425.00
```

**Frecuencia:** ⭐⭐⭐⭐⭐ (MUY común, ~30%)  
**Criticidad:** 🔥🔥🔥 (Caso más importante a manejar bien)

---

### 1.5 Agregar con Especificaciones Detalladas

**Usuario escribe:**
```
"Agregar 50 pasos salados gourmet, 
variedad premium con quesos importados,
precio unitario $8.00"
```

**Agente hace:**
1. Extrae: nombre completo con especificaciones
2. Extrae: cantidad=50, precio=$8.00
3. Agrega con toda la información
4. Respeta precio especificado por usuario

**RFX después:**
```
3. 🆕 Pasos salados gourmet (50)
   Variedad premium con quesos importados
   $8.00 c/u - Total: $400.00
```

**Frecuencia:** ⭐⭐ (Ocasional, ~5%)

---

## 2️⃣ MODIFICAR PRODUCTOS/INFORMACIÓN

### 2.1 Modificar Cantidad (Aumentar)

**Usuario escribe:**
```
"Aumentar pasos salados a 80 unidades"
"Cambiar café a 30 servicios"
"Necesito 100 pasos en lugar de 50"
```

**Agente hace:**
1. Identifica producto a modificar
2. Actualiza cantidad: 50 → 80
3. Recalcula precio (80 × precio_unitario)
4. Actualiza total

**RFX antes:**
```
1. Pasos salados (50) - $250.00
```

**RFX después:**
```
1. Pasos salados (80) - $400.00  ← Cantidad y total actualizados
   ✏️ Modificado  ← Badge temporal
```

**Frecuencia:** ⭐⭐⭐⭐ (Muy común, ~20%)

---

### 2.2 Modificar Cantidad (Disminuir)

**Usuario escribe:**
```
"Reducir café a 10 servicios"
"Bajar pasos salados a 30"
```

**Agente hace:**
1. Identifica producto
2. Actualiza cantidad: 20 → 10
3. Recalcula precio
4. Actualiza total

**RFX antes:**
```
2. Café y té (20) - $40.00
```

**RFX después:**
```
2. Café y té (10) - $20.00  ← Reducido
```

**Frecuencia:** ⭐⭐⭐ (Común, ~10%)

---

### 2.3 Modificar Precio Unitario

**Usuario escribe:**
```
"El precio de los pasos salados es $6.00 cada uno"
"Actualizar precio del café a $2.50 por servicio"
```

**Agente hace:**
1. Identifica producto
2. Actualiza precio unitario
3. Recalcula total del producto
4. Actualiza total general

**RFX antes:**
```
1. Pasos salados (50) - $5.00 c/u - $250.00
```

**RFX después:**
```
1. Pasos salados (50) - $6.00 c/u - $300.00  ← Precio actualizado
```

**Frecuencia:** ⭐⭐⭐ (Común, ~10%)

---

### 2.4 Modificar Nombre/Descripción

**Usuario escribe:**
```
"Cambiar 'Pasos salados' a 'Bocadillos salados gourmet'"
"Actualizar descripción del café: 'Café premium y té de hierbas'"
```

**Agente hace:**
1. Identifica producto a modificar
2. Actualiza nombre/descripción
3. Mantiene cantidad y precio

**RFX antes:**
```
1. Pasos salados (50) - $250.00
```

**RFX después:**
```
1. Bocadillos salados gourmet (50) - $250.00  ← Nombre actualizado
```

**Frecuencia:** ⭐⭐ (Ocasional, ~5%)

---

### 2.5 Modificar Información del Evento

**Usuario escribe:**
```
"Cambiar fecha al 15 de diciembre"
"Actualizar lugar: Salón Gardenia"
"El evento es para 150 personas ahora"
"Cliente: María Rodríguez"
```

**Agente hace:**
1. Identifica campo a modificar (fecha/lugar/personas/cliente)
2. Actualiza el campo correspondiente
3. NO modifica productos (a menos que sea necesario)

**RFX antes:**
```
Cliente: Sofia Elena Catering
Fecha: 10 Diciembre 2024
Lugar: Por definir
Personas: 100
```

**RFX después:**
```
Cliente: María Rodríguez  ← Actualizado
Fecha: 15 Diciembre 2024  ← Actualizado
Lugar: Salón Gardenia     ← Actualizado
Personas: 150             ← Actualizado
```

**Frecuencia:** ⭐⭐⭐⭐ (Muy común, ~15%)

---

## 3️⃣ ELIMINAR PRODUCTOS

### 3.1 Eliminar Producto Específico

**Usuario escribe:**
```
"Eliminar los refrescos"
"Quitar café y té"
"Ya no necesito las servilletas"
```

**Agente hace:**
1. Identifica producto(s) a eliminar
2. Pide confirmación (opcional según configuración)
3. Elimina del RFX
4. Recalcula total

**RFX antes:**
```
1. Pasos salados (50) - $250.00
2. Café y té (20)     - $40.00
3. Refrescos (20)     - $50.00
────────────────────────────────
Total: $340.00
```

**Agente pregunta:**
```
⚠️ Vas a eliminar:
• Café y té (20 servicios) - $40.00

¿Confirmas?
1️⃣ Sí, eliminar
2️⃣ No, cancelar
```

**Usuario:** "1"

**RFX después:**
```
1. Pasos salados (50) - $250.00
2. Refrescos (20)     - $50.00
────────────────────────────────
Total: $300.00  ← Recalculado
```

**Frecuencia:** ⭐⭐⭐ (Común, ~10%)

---

### 3.2 Eliminar Múltiples Productos

**Usuario escribe:**
```
"Eliminar café, refrescos y servilletas"
```

**Agente hace:**
1. Identifica todos los productos
2. Lista para confirmación
3. Elimina todos
4. Recalcula

**Agente pregunta:**
```
⚠️ Vas a eliminar 3 productos:
• Café y té (20) - $40.00
• Refrescos (20) - $50.00
• Servilletas (50) - $25.00

Total a restar: $115.00

¿Confirmas?
```

**Frecuencia:** ⭐⭐ (Ocasional, ~5%)

---

## 4️⃣ REEMPLAZAR COMPLETAMENTE

### 4.1 Reemplazar Todo el RFX

**Usuario escribe:**
```
"Cliente cambió todo, adjunto nueva solicitud"
"Reemplazar con esta nueva lista"
```

**Usuario adjunta:** Archivo con solicitud completamente nueva

**Agente detecta:**
- Solicitud nueva es muy diferente (>70% productos diferentes)
- Usuario usa palabras clave: "reemplazar", "cambió todo", "nueva solicitud"

**Agente pregunta:**
```
⚠️ REEMPLAZO COMPLETO

Detecté que quieres reemplazar todo el RFX.

RFX actual tiene:
• 3 productos
• Total: $340.00

Nueva solicitud tiene:
• 5 productos
• Total estimado: $580.00

¿Confirmas reemplazar completamente?

1️⃣ Sí, reemplazar todo ⚠️
2️⃣ No, solo agregar productos nuevos
```

**Usuario:** "1"

**Resultado:**
- Elimina todos los productos anteriores
- Crea RFX nuevo con productos del archivo
- Mantiene: Cliente, fecha (a menos que cambien)
- Actualiza: Productos, totales

**Frecuencia:** ⭐⭐ (Raro pero crítico, ~5%)

---

### 4.2 Reemplazar Producto Individual

**Usuario escribe:**
```
"Cambiar pasos salados por bocadillos gourmet, 50 unidades"
```

**Agente hace:**
1. Identifica que es reemplazo (no modificación)
2. Elimina producto antiguo
3. Agrega producto nuevo
4. Mantiene cantidad o usa nueva

**RFX antes:**
```
1. Pasos salados (50) - $250.00
```

**RFX después:**
```
1. Bocadillos gourmet (50) - $300.00  ← Reemplazado
```

**Frecuencia:** ⭐⭐ (Ocasional, ~5%)

---

## 5️⃣ CORREGIR ERRORES

### 5.1 Corregir Cantidad Errónea

**Usuario escribe:**
```
"El total de pasos salados debe ser 50, no 80"
"Corregir café: son 20 servicios, no 30"
```

**Agente hace:**
1. Identifica que es corrección (no modificación intencional)
2. Actualiza al valor correcto
3. Explica el cambio

**Agente responde:**
```
✅ Corregido:
📦 Pasos salados
   Antes: 80 unidades ❌
   Ahora: 50 unidades ✅
   
💰 Total actualizado: $400 → $250
```

**Frecuencia:** ⭐⭐⭐ (Común, ~8%)

---

### 5.2 Corregir Precio Erróneo

**Usuario escribe:**
```
"El precio de los pasos es $5.00, no $6.00"
"Corregir: café debe costar $2.00 cada uno"
```

**Agente hace:**
1. Actualiza precio al correcto
2. Recalcula totales
3. Muestra diferencia

**Frecuencia:** ⭐⭐⭐ (Común, ~8%)

---

### 5.3 Corregir Nombre de Producto

**Usuario escribe:**
```
"Es 'Pasos salados', no 'Bocadillos salados'"
"El café es 'Café premium', lo escribiste mal"
```

**Agente hace:**
1. Corrige el nombre
2. Mantiene todo lo demás

**Frecuencia:** ⭐⭐ (Ocasional, ~3%)

---

### 5.4 Corregir Información del Evento

**Usuario escribe:**
```
"La fecha correcta es 12 de diciembre, no 15"
"El cliente es Juan Pérez, no María Rodríguez"
```

**Agente hace:**
1. Corrige el campo específico
2. Confirma el cambio

**Frecuencia:** ⭐⭐⭐ (Común, ~7%)

---

## 6️⃣ CONSULTAR (Sin Modificar)

### 6.1 Consultar Lista de Productos

**Usuario escribe:**
```
"¿Qué productos tiene este RFX?"
"Muéstrame la lista actual"
"¿Cuántos productos hay?"
```

**Agente responde:**
```
📦 Este RFX tiene 3 productos:

1. Pasos salados variados (50) - $250.00
2. Café y té (20) - $40.00
3. Refrescos (20) - $50.00

💰 Total: $340.00

¿Necesitas modificar algo?
```

**NO modifica nada, solo consulta**

**Frecuencia:** ⭐⭐ (Ocasional, ~5%)

---

### 6.2 Consultar Información Específica

**Usuario escribe:**
```
"¿Cuál es el total actual?"
"¿Cuántos pasos salados tenemos?"
"¿Cuándo es el evento?"
```

**Agente responde:**
```
📅 Información del evento:
• Fecha: 10 Diciembre 2024
• Lugar: Salón Gardenia
• Cliente: Sofia Elena Catering
• Personas: 100
• Total: $340.00
```

**Frecuencia:** ⭐⭐ (Ocasional, ~4%)

---

### 6.3 Consultar Precios

**Usuario escribe:**
```
"¿Cuánto cuesta cada paso salado?"
"¿Cuál es el precio unitario del café?"
```

**Agente responde:**
```
💰 Precios:
• Pasos salados: $5.00 c/u
• Total de 50 unidades: $250.00
```

**Frecuencia:** ⭐ (Raro, ~2%)

---

## 🔍 CASOS ESPECIALES Y EDGE CASES

### 7.1 Solicitud Ambigua

**Usuario escribe:**
```
"Agregar más pasos"
```

**Problema:** No especifica cuántos

**Agente responde:**
```
❓ ¿Cuántos pasos salados deseas agregar?

Actualmente tienes: 50 unidades

Por favor especifica:
• Cantidad adicional (ej: "+20" = total 70)
• Cantidad nueva total (ej: "70" = total 70)
```

---

### 7.2 Producto No Existe en Catálogo

**Usuario escribe:**
```
"Agregar 30 canapés de salmón ahumado"
```

**Problema:** Producto no está en catálogo, no hay precio

**Agente responde:**
```
⚠️ Producto no encontrado en catálogo

📦 Canapés de salmón ahumado (30)

No tengo precio para este producto.
¿Qué deseas hacer?

1️⃣ Agregar sin precio (definir después)
2️⃣ Especificar precio ahora
3️⃣ Cancelar
```

**Usuario:** "2 - $8 cada uno"

**Resultado:** Agrega con precio $8.00 c/u

---

### 7.3 Archivo No Procesable

**Usuario adjunta:** Archivo corrupto o formato no soportado

**Agente responde:**
```
❌ No pude procesar el archivo

El archivo parece estar corrupto o en formato
no soportado.

Formatos aceptados:
• PDF
• Imágenes (JPG, PNG)
• Word (DOCX)

Por favor:
1️⃣ Verifica el archivo
2️⃣ Adjunta otro archivo
3️⃣ Describe los cambios manualmente
```

---

### 7.4 Cantidad Inusual (Muy Alta/Baja)

**Usuario escribe:**
```
"Agregar 10,000 pasos salados"
```

**Agente detecta:** Cantidad sospechosamente alta

**Agente pregunta:**
```
⚠️ Confirmación de cantidad

Deseas agregar: 10,000 unidades de pasos salados
Precio estimado: $50,000.00

Esto es una cantidad muy alta.
¿Es correcto?

1️⃣ Sí, confirmar 10,000 unidades
2️⃣ No, cambiar cantidad
```

---

### 7.5 Múltiples Modificaciones en Un Mensaje

**Usuario escribe:**
```
"Agregar 20 refrescos, 
aumentar pasos a 80, 
eliminar café,
cambiar fecha al 15 de diciembre"
```

**Agente hace:**
1. Detecta 4 operaciones diferentes
2. Procesa cada una en orden
3. Aplica todos los cambios
4. Resume todo al final

**Agente responde:**
```
✅ He aplicado 4 cambios:

1. ➕ Agregado: Refrescos (20) - $50.00
2. ✏️ Modificado: Pasos salados 50 → 80
3. ➖ Eliminado: Café y té
4. 📅 Actualizado: Fecha → 15 Diciembre 2024

💰 Nuevo total: $450.00
```

---

### 7.6 Instrucciones Contradictorias

**Usuario escribe:**
```
"Agregar 20 refrescos pero no los agregues"
"Eliminar café pero mantenerlo"
```

**Agente detecta:** Contradicción

**Agente responde:**
```
❓ Instrucciones contradictorias

Dijiste:
• "Agregar 20 refrescos"
• "Pero no los agregues"

Por favor aclara:
1️⃣ Agregar refrescos
2️⃣ NO agregar refrescos
3️⃣ Explicar mejor lo que necesitas
```

---

## 📊 TABLA RESUMEN DE FRECUENCIA

| Caso de Uso | Frecuencia | Complejidad | Prioridad |
|-------------|------------|-------------|-----------|
| Agregar simple (texto) | ⭐⭐⭐⭐⭐ 40% | Baja | 🔥🔥🔥 Alta |
| Agregar archivo CON duplicados | ⭐⭐⭐⭐⭐ 30% | Alta | 🔥🔥🔥 Crítica |
| Modificar cantidad | ⭐⭐⭐⭐ 20% | Baja | 🔥🔥🔥 Alta |
| Agregar múltiples | ⭐⭐⭐ 15% | Media | 🔥🔥 Media |
| Agregar archivo SIN duplicados | ⭐⭐⭐ 15% | Media | 🔥🔥 Media |
| Modificar info evento | ⭐⭐⭐⭐ 15% | Baja | 🔥🔥 Media |
| Eliminar producto | ⭐⭐⭐ 10% | Baja | 🔥🔥 Media |
| Modificar precio | ⭐⭐⭐ 10% | Baja | 🔥 Baja |
| Corregir cantidad | ⭐⭐⭐ 8% | Baja | 🔥🔥 Media |
| Corregir precio | ⭐⭐⭐ 8% | Baja | 🔥 Baja |
| Corregir info evento | ⭐⭐⭐ 7% | Baja | 🔥 Baja |
| Agregar con specs | ⭐⭐ 5% | Media | 🔥 Baja |
| Reemplazar completo | ⭐⭐ 5% | Alta | 🔥🔥 Media |
| Eliminar múltiples | ⭐⭐ 5% | Media | 🔥 Baja |
| Consultar productos | ⭐⭐ 5% | Baja | 🔥 Baja |
| Reemplazar individual | ⭐⭐ 5% | Media | 🔥 Baja |
| Modificar nombre | ⭐⭐ 5% | Baja | 🔥 Baja |
| Consultar info | ⭐⭐ 4% | Baja | 🔥 Baja |
| Corregir nombre | ⭐⭐ 3% | Baja | 🔥 Baja |
| Consultar precios | ⭐ 2% | Baja | 🔥 Baja |

**Total casos documentados:** 20+

---

## 🎯 CASOS MÁS CRÍTICOS (TOP 5)

### 1. 🔥🔥🔥 Agregar Archivo CON Duplicados (30%)
**Por qué es crítico:**
- Caso más complejo técnicamente
- Requiere detección inteligente de duplicados
- Necesita confirmación del usuario
- Mal manejo = RFX incorrecto

**Prioridad:** Implementar PRIMERO

---

### 2. 🔥🔥🔥 Agregar Simple por Texto (40%)
**Por qué es crítico:**
- Caso más frecuente
- Primera impresión del usuario
- Debe ser RÁPIDO (< 5 seg)
- Core value proposition

**Prioridad:** Implementar PRIMERO

---

### 3. 🔥🔥🔥 Modificar Cantidad (20%)
**Por qué es crítico:**
- Muy frecuente
- Debe recalcular correctamente
- Afecta totales
- Error = pérdida de confianza

**Prioridad:** Implementar PRIMERO

---

### 4. 🔥🔥 Agregar Múltiples (15%)
**Por qué es importante:**
- Demuestra capacidad del agente
- Ahorra tiempo al usuario
- Parsing complejo

**Prioridad:** Implementar SEGUNDO

---

### 5. 🔥🔥 Agregar Archivo SIN Duplicados (15%)
**Por qué es importante:**
- Extracción de PDF debe ser precisa
- Menos complejo que con duplicados
- Base para caso #1

**Prioridad:** Implementar SEGUNDO

---

## 🧪 RECOMENDACIONES DE TESTING

### Casos mínimos a testear (MVP):

1. ✅ **Agregar 1 producto simple**
   ```
   Input: "Agregar 20 refrescos"
   Expect: Producto agregado, total correcto
   ```

2. ✅ **Agregar archivo CON duplicados**
   ```
   Input: PDF con productos existentes + nuevos
   Expect: Detecta duplicados, pide confirmación
   ```

3. ✅ **Modificar cantidad**
   ```
   Input: "Aumentar pasos a 80"
   Expect: Cantidad actualizada, precio recalculado
   ```

4. ✅ **Eliminar producto**
   ```
   Input: "Eliminar café"
   Expect: Producto eliminado, total recalculado
   ```

5. ✅ **Modificar info evento**
   ```
   Input: "Cambiar fecha al 15 de diciembre"
   Expect: Fecha actualizada, productos intactos
   ```

6. ✅ **Caso ambiguo**
   ```
   Input: "Agregar más pasos"
   Expect: Agente pregunta cantidad específica
   ```

7. ✅ **Múltiples operaciones**
   ```
   Input: "Agregar refrescos y aumentar pasos a 80"
   Expect: Ambas operaciones aplicadas correctamente
   ```

---

## 📝 NOTAS FINALES

### Principios de Diseño del Agente:

1. **Inteligencia sobre Reglas**
   - Agente entiende INTENCIÓN, no solo keywords
   - "Agregar", "Incluir", "Necesito" → mismo intent
   - "Aumentar", "Cambiar a", "Modificar" → mismo intent

2. **Confirmación Cuando Hay Duda**
   - Duplicados → Siempre confirmar
   - Eliminaciones → Confirmar si >1 producto o >$100
   - Cantidades altas → Confirmar si >1000 unidades
   - Reemplazo completo → Siempre confirmar

3. **Explicación Clara de Cambios**
   - Siempre mostrar: antes → después
   - Usar emojis para visual clarity
   - Resumir impacto en total

4. **Recuperación de Errores**
   - Si falla, explicar por qué
   - Ofrecer alternativas
   - Permitir reintentar fácilmente

5. **Progresividad**
   - MVP: Casos 1, 2, 3 (agregar, archivo duplicados, modificar)
   - V2: Casos 4, 5 (eliminar, info evento)
   - V3: Casos avanzados (reemplazar, correcciones)

---

## ✅ CHECKLIST DE IMPLEMENTACIÓN

### MVP (Mínimo Viable)
- [ ] Agregar producto simple (texto)
- [ ] Agregar desde archivo CON duplicados
- [ ] Modificar cantidad
- [ ] Modificar info del evento
- [ ] Consultar información

### V2 (Post-MVP)
- [ ] Agregar múltiples productos
- [ ] Eliminar producto(s)
- [ ] Modificar precios
- [ ] Corregir errores simples

### V3 (Avanzado)
- [ ] Reemplazar completo
- [ ] Modificar nombres
- [ ] Múltiples ops en un mensaje
- [ ] Casos ambiguos avanzados

---

**Status:** Casos de uso completos documentados ✅

**Total casos:** 20+ documentados

**Prioridad:** Implementar top 3 primero (70% de uso)