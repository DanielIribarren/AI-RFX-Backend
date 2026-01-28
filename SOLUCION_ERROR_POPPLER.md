# 🔧 Solución: Error "Unable to get page count. Is poppler installed and in PATH?"

## Error Identificado

**Mensaje:** `pdf2image.exceptions.PDFInfoNotInstalledError: Unable to get page count. Is poppler installed and in PATH?`

**Archivo:** `backend/services/vision_analysis_service.py:222`

**Causa:** Poppler no está instalado en el servidor Ubuntu

---

## ✅ Solución Inmediata (5 minutos)

### Paso 1: Conectarse al Servidor

```bash
ssh ubuntu@<tu-servidor>
cd /home/ubuntu/nodejs/AI-RFX-Backend-Clean
```

### Paso 2: Instalar Poppler

```bash
# Actualizar repositorios
sudo apt-get update

# Instalar Poppler
sudo apt-get install -y poppler-utils

# Verificar instalación
pdfinfo -v
```

**Salida esperada:**
```
pdfinfo version 22.02.0
Copyright 2005-2022 The Poppler Developers - http://poppler.freedesktop.org
```

### Paso 3: Reiniciar PM2

```bash
# Reiniciar el proceso
pm2 restart RFX-dev

# Ver logs para confirmar
pm2 logs RFX-dev --lines 50
```

### Paso 4: Probar Upload de Template

1. Ir a la aplicación web
2. Navegar a **Budget Settings** (Configuración de Presupuestos)
3. Subir un archivo PDF como template
4. **Resultado esperado:** ✅ "Files uploaded. Analysis in progress."
5. **Antes:** ❌ "Error en análisis: Unable to get page count..."

---

## 🔍 ¿Por Qué Ocurrió Este Error?

### Flujo del Error

```
1. Usuario sube template PDF
   ↓
2. Backend recibe archivo en /api/branding/upload
   ↓
3. vision_analysis_service.py intenta convertir PDF a imagen
   ↓
4. pdf2image llama a Poppler (herramienta del sistema)
   ↓
5. ❌ Poppler no encontrado → Error
```

### Dependencias Involucradas

| Componente | Tipo | Status |
|------------|------|--------|
| `pdf2image` | Librería Python | ✅ Instalada (en requirements.txt) |
| `poppler-utils` | Sistema operativo | ❌ NO instalada (faltaba) |

**Nota:** `pdf2image` es solo un wrapper de Python. El trabajo real lo hace Poppler.

---

## 🚀 Prevención Futura

El script `scripts/setup_dependencies.sh` ahora ha sido mejorado para:

1. ✅ Detectar si Poppler está instalado
2. ✅ Intentar instalarlo automáticamente
3. ✅ Verificar que la instalación fue exitosa
4. ✅ **FALLAR el inicio** si Poppler no está disponible

### Próximo Deploy

```bash
# El script ahora instalará Poppler automáticamente
bash scripts/pm2_start.sh
```

**Antes:**
```
⚠️  Poppler no encontrado - PDF processing puede fallar
✅ Setup completado  # ← Continuaba sin Poppler
```

**Ahora:**
```
⚠️  Poppler no encontrado - PDF processing FALLARÁ
📦 Instalando Poppler (Ubuntu/Debian)...
✅ Poppler instalado correctamente  # ← Verifica instalación
```

**Si falla:**
```
❌ Error: Poppler no se pudo instalar automáticamente
   💡 Ejecutar manualmente: sudo apt-get install -y poppler-utils
[SCRIPT TERMINA - NO INICIA SERVIDOR]
```

---

## 📋 Verificación Post-Instalación

### 1. Verificar Poppler

```bash
pdfinfo -v
```

### 2. Verificar Python puede usar pdf2image

```bash
cd /home/ubuntu/nodejs/AI-RFX-Backend-Clean
source venv/bin/activate
python -c "from pdf2image import convert_from_path; print('✅ pdf2image funciona')"
```

### 3. Test Completo

```bash
# Crear PDF de prueba
echo "Test" | ps2pdf - test.pdf

# Intentar convertir
python -c "
from pdf2image import convert_from_path
images = convert_from_path('test.pdf', first_page=1, last_page=1)
print(f'✅ PDF convertido: {len(images)} página(s)')
"

# Limpiar
rm test.pdf
```

---

## 🐛 Debugging

### Si el error persiste después de instalar Poppler:

**1. Verificar PATH:**
```bash
which pdfinfo
# Debe mostrar: /usr/bin/pdfinfo
```

**2. Verificar permisos:**
```bash
ls -la /usr/bin/pdfinfo
# Debe ser ejecutable: -rwxr-xr-x
```

**3. Verificar que PM2 usa el entorno correcto:**
```bash
pm2 logs RFX-dev | grep "Poppler"
# Debe mostrar: ✅ Poppler instalado
```

**4. Reiniciar PM2 completamente:**
```bash
pm2 delete RFX-dev
bash scripts/pm2_start.sh
```

---

## 📚 Archivos Modificados

- ✅ `scripts/setup_dependencies.sh` - Verificación mejorada de Poppler
- 📄 `SOLUCION_ERROR_POPPLER.md` - Este documento

---

## 🎯 Resumen

**Problema:** Poppler no instalado → PDF analysis falla  
**Solución:** `sudo apt-get install -y poppler-utils`  
**Prevención:** Script de setup mejorado  
**Tiempo:** ~5 minutos  

**Status:** ✅ SOLUCIONADO
