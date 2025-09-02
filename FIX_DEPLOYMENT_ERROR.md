# 🔧 Fix para Error de Deployment en Railway

## ❌ Error Detectado

El error en los logs muestra:

```
E: Package 'wkhtmltopdf' has no installation candidate
```

Este error ocurre porque `wkhtmltopdf` no está disponible en los repositorios oficiales de Debian Trixie.

## ✅ Solución Aplicada

He arreglado el `Dockerfile` de dos maneras:

### 1. Dockerfile Principal (Arreglado)

- ✅ Instala `wkhtmltopdf` manualmente desde el paquete oficial
- ✅ Incluye todas las dependencias (WeasyPrint, Tesseract, Playwright)
- ✅ Listo para usar todas las funcionalidades de PDF/OCR

### 2. Dockerfile.minimal (Alternativa Ligera)

- ✅ Sin dependencias pesadas de PDF/OCR
- ✅ Build más rápido (2-3 minutos vs 8-10 minutos)
- ✅ Menor uso de memoria
- ✅ Ideal si no usas funciones de PDF/OCR en producción

## 🚀 Cómo Proceder

### Opción A: Usar Dockerfile Arreglado (Recomendado)

```bash
# El Dockerfile ya está arreglado, solo haz push
git add .
git commit -m "fix: resolve wkhtmltopdf installation issue"
git push origin main
```

### Opción B: Usar Versión Minimal (Más Rápido)

```bash
# Si no necesitas PDF/OCR, usa la versión ligera
mv Dockerfile Dockerfile.full
mv Dockerfile.minimal Dockerfile

git add .
git commit -m "feat: use minimal dockerfile for faster builds"
git push origin main
```

## 🔍 Diferencias entre Versiones

| Característica     | Dockerfile (Full) | Dockerfile.minimal |
| ------------------ | ----------------- | ------------------ |
| **Build Time**     | 8-10 minutos      | 2-3 minutos        |
| **Tamaño Imagen**  | ~2GB              | ~500MB             |
| **WeasyPrint**     | ✅                | ❌                 |
| **pdf2image**      | ✅                | ❌                 |
| **Tesseract OCR**  | ✅                | ❌                 |
| **Playwright**     | ✅                | ❌                 |
| **pdfkit**         | ✅                | ❌                 |
| **Core Flask App** | ✅                | ✅                 |

## 🎯 Recomendación

**Para desarrollo/testing**: Usa `Dockerfile.minimal` (más rápido)
**Para producción completa**: Usa `Dockerfile` (todas las funcionalidades)

## 🔄 Próximo Deploy

El próximo push a `main` debería funcionar correctamente con cualquiera de las dos opciones.

**¿Cuál prefieres usar?**
