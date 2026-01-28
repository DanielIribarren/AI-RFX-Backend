# 🚀 Quick Start - Servidor PM2

## Setup Inicial (Una Sola Vez)

```bash
# 1. Clonar y entrar al proyecto
cd /home/ubuntu/nodejs/AI-RFX-Backend-Clean

# 2. Dar permisos a scripts
chmod +x scripts/*.sh

# 3. Iniciar servidor
bash scripts/pm2_start.sh
```

**¡Eso es todo!** El script automáticamente:
- ✅ Crea el entorno virtual
- ✅ Instala todas las dependencias
- ✅ Configura Playwright
- ✅ Inicia el servidor con PM2

---

## Reiniciar el Servidor

```bash
# Opción 1: Con setup automático (RECOMENDADO)
bash scripts/pm2_start.sh

# Opción 2: Solo reiniciar PM2
pm2 reload ecosystem.dev.config.js --env development
```

---

## Ver Logs

```bash
# Logs en tiempo real
pm2 logs RFX-dev

# Solo errores
pm2 logs RFX-dev --err

# Últimas 100 líneas
pm2 logs RFX-dev --lines 100
```

---

## Comandos Útiles

```bash
pm2 status              # Ver estado
pm2 restart RFX-dev     # Reiniciar
pm2 stop RFX-dev        # Detener
pm2 monit               # Monitor en tiempo real
```

---

## Troubleshooting

### Error: "Module not found"
```bash
bash scripts/setup_dependencies.sh
```

### Error: "Playwright browser not found"
```bash
source venv/bin/activate
playwright install chromium --with-deps
```

### Verificar que todo funciona
```bash
# El script de setup incluye tests automáticos
bash scripts/setup_dependencies.sh
```

---

## 📖 Documentación Completa

Ver `DEPLOYMENT_GUIDE.md` para información detallada.
