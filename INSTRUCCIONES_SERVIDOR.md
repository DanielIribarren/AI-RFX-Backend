# 🔧 Instrucciones para Actualizar ecosystem.dev.config.js en el Servidor

## ⚠️ Problema Actual
El archivo `ecosystem.dev.config.js` en el servidor tiene la versión antigua con el formato incorrecto de hooks.

## ✅ Solución: Editar Archivo en el Servidor

### **Opción 1: Editar con nano (Recomendado)**

```bash
# En el servidor, ejecutar:
nano /home/ubuntu/nodejs/AI-RFX-Backend-Clean/ecosystem.dev.config.js
```

**Buscar estas líneas (alrededor de la línea 50-55):**
```javascript
post_update: './scripts/post_deploy_setup.sh',
pre_start: './scripts/post_deploy_setup.sh',
```

**Cambiarlas por:**
```javascript
post_update: ['./scripts/post_deploy_setup.sh'],
pre_start: ['./scripts/post_deploy_setup.sh'],
```

**Guardar:** `Ctrl + O`, luego `Enter`, luego `Ctrl + X`

---

### **Opción 2: Usar sed (Automático)**

```bash
# En el servidor, ejecutar estos comandos:
cd /home/ubuntu/nodejs/AI-RFX-Backend-Clean

# Backup del archivo original
cp ecosystem.dev.config.js ecosystem.dev.config.js.backup

# Reemplazar la línea post_update
sed -i "s/post_update: '\.\/scripts\/post_deploy_setup\.sh',/post_update: ['.\/scripts\/post_deploy_setup.sh'],/" ecosystem.dev.config.js

# Reemplazar la línea pre_start
sed -i "s/pre_start: '\.\/scripts\/post_deploy_setup\.sh',/pre_start: ['.\/scripts\/post_deploy_setup.sh'],/" ecosystem.dev.config.js

# Verificar cambios
grep -A 1 "post_update" ecosystem.dev.config.js
grep -A 1 "pre_start" ecosystem.dev.config.js
```

---

### **Opción 3: Copiar Archivo Completo desde Local**

```bash
# Desde tu máquina LOCAL (no en el servidor):
scp ecosystem.dev.config.js ubuntu@TU-IP-SERVIDOR:/home/ubuntu/nodejs/AI-RFX-Backend-Clean/

# Luego en el servidor:
pm2 reload ecosystem.dev.config.js --env development
```

---

## 🎯 Verificar que Funcionó

Después de hacer el cambio, ejecutar:

```bash
pm2 delete all
pm2 start ecosystem.dev.config.js
```

**Si ya NO aparece el warning `[PM2][WARN] Expect "post_update"...`** → ✅ Éxito!

---

## 📋 Estado Actual

### ✅ **Lo que YA funciona:**
- Playwright instalado correctamente
- Navegadores descargados (Chromium)
- Tests de funcionalidad exitosos
- PDFs deberían generarse correctamente

### ⚠️ **Lo que falta:**
- Actualizar formato de hooks en `ecosystem.dev.config.js`
- Esto solo afecta el warning, NO la funcionalidad

---

## 🚀 Después de Actualizar el Archivo

```bash
# Reiniciar PM2 sin warnings
pm2 delete all
pm2 start ecosystem.dev.config.js

# Verificar estado
pm2 status
pm2 logs RFX-dev --lines 20

# Probar descarga de PDF desde el frontend
```

---

## 🎉 Resultado Esperado

```bash
pm2 start ecosystem.dev.config.js
# ✅ Sin warnings
# ✅ Aplicación iniciada correctamente
# ✅ PDFs se generan sin errores
# ✅ Logos visibles en preview y PDFs
```
