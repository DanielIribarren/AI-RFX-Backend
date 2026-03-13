# Deploy Checklist - Migracion PM2 -> Vercel

## Estado Actual Detectado

- Frontend local: `http://localhost:3004` (`AI-RFX-Frontend/package.json`)
- Backend local: `http://localhost:5001` (flujo `start_backend.py`)
- PM2 historico: puertos `3186`/`3187` y scripts de Ubuntu
- Dominio legacy backend: `https://recharge-api.akeela.co`

## Objetivo

Eliminar dependencia operativa de PM2 y dejar backend + frontend desplegados en Vercel con comandos minimos.

## Entry Points Oficiales (nuevo flujo)

- Backend local: `python3 start_backend.py`
- Backend Vercel runtime: `api/index.py` (Flask app)
- Frontend local: `npm run dev` (puerto 3004)
- Frontend deploy: `vercel deploy`

## Paso 1 - Vincular y configurar Backend en Vercel (una sola vez)

Desde `AI-RFX-Backend-Clean/`:

```bash
# 1) Vincular proyecto Vercel (si no existe .vercel/project.json)
export VERCEL_PROJECT_NAME=rfx-automation-backend

# 2) Subir variables a preview y production desde .env
./scripts/vercel_sync_env.sh .env production,preview
```

Notas:
- El script corrige automaticamente `UDINARY_CLOUD_NAME` -> `CLOUDINARY_CLOUD_NAME`.
- `ENVIRONMENT` se fuerza a `production` y `UPLOAD_FOLDER` a `/tmp/rfx_uploads`.

## Paso 2 - Deploy Backend

```bash
# Preview
./scripts/vercel_deploy.sh preview

# Produccion
./scripts/vercel_deploy.sh production
```

Guarda la URL de produccion del backend, por ejemplo:
`https://rfx-automation-backend.vercel.app`

## Paso 3 - Ajustar Frontend para el nuevo Backend

Configura en Vercel (proyecto frontend):

- `NEXT_PUBLIC_API_URL=https://<backend-vercel-url>`
- `NEXT_PUBLIC_AUTH_API_URL=https://<backend-vercel-url>/api/auth`
- `AUTH_API_URL=https://<backend-vercel-url>/api/auth`

## Paso 4 - Deploy Frontend

Desde `AI-RFX-Frontend/`:

```bash
# Preview
./scripts/deploy-vercel.sh --preview

# Produccion
./scripts/deploy-vercel.sh --prod
```

## Paso 5 - Retiro Operativo de PM2 en el Servidor Legacy

En Ubuntu (si aplica):

```bash
pm2 stop all
pm2 delete all
pm2 save
pm2 unstartup systemd
```

Y remover cron/jobs/scripts que llamen:
- `start-pm2.sh`
- `setup_pm2.sh`
- `scripts/pm2_start.sh`

## Smoke Tests Minimos

```bash
# Backend
curl https://<backend-vercel-url>/health
curl https://<backend-vercel-url>/api/health

# Frontend
curl -I https://<frontend-vercel-url>
```

## Riesgos Criticos (antes de cortar PM2)

- El backend usa tareas pesadas (PDF/Playwright/branding) que en serverless pueden tener limites de tiempo/memoria.
- `backend/static/branding` no es almacenamiento persistente en Vercel.
- Si la funcionalidad de branding/template depende de disco local, hay que migrarla a storage externo antes del corte total.
- `rfx_chat` queda deshabilitado en startup si falla import de LangChain (evita que caiga todo el backend).
