# 🚀 AI-RFX Backend - Deployment Guide

Guía completa para hacer deploy del backend usando GitHub Actions + self-hosted runner + Docker.

## 📋 Resumen del Setup

- **Backend**: Flask + Gunicorn en Docker
- **CI/CD**: GitHub Actions con self-hosted runner
- **Registry**: GitHub Container Registry (GHCR)
- **Deployment**: Docker Compose en tu VPS/PC

## 🛠️ Configuración del VPS/PC (Self-hosted Runner)

### 1. Instalar Docker y Docker Compose

```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Instalar Docker Compose plugin
sudo apt-get update
sudo apt-get install docker-compose-plugin

# Reiniciar sesión para aplicar cambios de grupo
```

### 2. Configurar GitHub Self-hosted Runner

1. Ve a tu repo → **Settings** → **Actions** → **Runners** → **New self-hosted runner**
2. Sigue las instrucciones para tu OS, pero usa estos comandos:

```bash
# Descargar y configurar (ajusta la URL y token)
./config.sh --url https://github.com/TU-USUARIO/TU-REPO --token TU-TOKEN --labels prod --unattended

# Instalar como servicio (recomendado)
sudo ./svc.sh install
sudo ./svc.sh start

# Verificar que está corriendo
sudo ./svc.sh status
```

### 3. Crear directorio y archivo de environment

```bash
# Crear directorio para configuración
sudo mkdir -p /opt/airfx
sudo chown $USER:$USER /opt/airfx

# Copiar y editar el archivo de environment
cp env.production.example /opt/airfx/.env.production
nano /opt/airfx/.env.production
```

**Importante**: Completa todas las variables en `/opt/airfx/.env.production` con tus valores reales.

## 🔧 Configuración del Repositorio

### 1. Actualizar docker-compose.yml

Edita `docker-compose.yml` y reemplaza `OWNER/REPO` con tus valores:

```yaml
services:
  web:
    image: ghcr.io/TU-USUARIO/TU-REPO-web:latest
    # ... resto de la configuración
```

### 2. Verificar permisos de GitHub

Asegúrate de que tu repositorio tenga habilitado:

- **Settings** → **Actions** → **General** → **Workflow permissions** → **Read and write permissions**
- **Settings** → **Packages** → Habilitar Container Registry

## 🚀 Proceso de Deployment

### Automático (Recomendado)

1. Haz push a la rama `main`:

```bash
git add .
git commit -m "Add Docker deployment setup"
git push origin main
```

2. El workflow se ejecutará automáticamente y:
   - Construirá la imagen Docker
   - La publicará en GHCR
   - Hará pull y restart del contenedor

### Manual (Para testing)

```bash
# En tu VPS, clona el repo si no lo tienes
git clone https://github.com/TU-USUARIO/TU-REPO.git
cd TU-REPO

# Actualizar docker-compose.yml con tu imagen
# Luego ejecutar:
docker compose pull
docker compose up -d
```

## 🔍 Verificación del Deployment

### 1. Verificar que el contenedor está corriendo

```bash
docker ps
# Deberías ver: airfx-backend corriendo en puerto 8080
```

### 2. Probar health check

```bash
curl http://localhost:8080/health
# Respuesta esperada: {"status": "healthy", ...}
```

### 3. Probar health check detallado

```bash
curl http://localhost:8080/health/detailed
# Verifica conexión a base de datos y OpenAI
```

## 🌐 Configuración de Dominio y HTTPS (Opcional)

### Con Caddy (Recomendado)

1. Instalar Caddy:

```bash
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install caddy
```

2. Configurar Caddyfile (`/etc/caddy/Caddyfile`):

```caddy
tu-dominio.com {
    reverse_proxy localhost:8080
}
```

3. Reiniciar Caddy:

```bash
sudo systemctl reload caddy
```

## 📊 Monitoreo y Logs

### Ver logs del contenedor

```bash
docker logs airfx-backend -f
```

### Ver logs del runner

```bash
# Si está como servicio
sudo journalctl -u actions.runner.* -f

# Si está corriendo manualmente
tail -f _diag/Runner_*.log
```

### Verificar uso de recursos

```bash
docker stats airfx-backend
```

## 🔧 Troubleshooting

### El workflow falla en "Build and Push Image"

- Verifica que el runner tenga Docker instalado y el usuario esté en el grupo `docker`
- Reinicia el runner: `sudo ./svc.sh restart`

### El contenedor no inicia

- Revisa logs: `docker logs airfx-backend`
- Verifica que `/opt/airfx/.env.production` existe y tiene las variables correctas
- Verifica que las credenciales de Supabase y OpenAI son válidas

### Error de permisos en GHCR

- Verifica que el repositorio tenga permisos de escritura en packages
- El token `GITHUB_TOKEN` debe tener scope `write:packages`

### El health check falla

- Verifica conexión a Supabase: `curl -I https://tu-proyecto.supabase.co`
- Verifica que la API key de OpenAI es válida
- Revisa logs del contenedor para errores específicos

## 📝 Notas Importantes

1. **Seguridad**: El archivo `.env.production` contiene secretos. Nunca lo subas al repositorio.

2. **Recursos**: La imagen incluye dependencias pesadas (WeasyPrint, Tesseract, Playwright). Si no las necesitas en producción, usa `requirements-minimal.txt` en el Dockerfile.

3. **Escalabilidad**: Para mayor tráfico, ajusta `--workers` y `--threads` en el comando de Gunicorn del Dockerfile.

4. **Backup**: Considera hacer backup del volumen `airfx_uploads` regularmente.

5. **Updates**: Cada push a `main` redesplegará automáticamente. Para deployments manuales, usa tags o ramas específicas.

## 🎯 Próximos Pasos

1. Configura monitoreo (Prometheus + Grafana)
2. Implementa backup automático de la base de datos
3. Configura alertas para fallos de deployment
4. Considera usar un load balancer para múltiples instancias
