# 📧 Email Configuration Guide - Contact Request Endpoint

## Overview

Sistema de envío automático de emails para solicitudes de planes desde el checkout. Usa **Flask-Mail** (librería estándar de Flask) con Gmail SMTP.

---

## 🚀 Quick Start

### 1. Instalar Dependencias

```bash
pip install Flask-Mail==0.9.1
```

O simplemente:
```bash
pip install -r requirements.txt
```

### 2. Configurar Variables de Entorno

Copia las variables de `.env.example` a tu `.env`:

```bash
# Email Configuration (Flask-Mail)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=tu-email@gmail.com
MAIL_PASSWORD=tu-app-password-aqui
MAIL_DEFAULT_SENDER=noreply@budyai.com
```

### 3. Obtener Gmail App Password

**⚠️ IMPORTANTE:** NO uses tu contraseña normal de Gmail. Necesitas un "App Password".

**Pasos:**
1. Ve a https://myaccount.google.com/
2. **Seguridad** → **Verificación en 2 pasos** (debe estar activada)
3. **Contraseñas de aplicaciones**
4. Selecciona **"Correo"** y **"Otro (nombre personalizado)"**
5. Escribe "RFX Backend" como nombre
6. Copia la contraseña de 16 caracteres (sin espacios)
7. Pégala en `MAIL_PASSWORD` en tu `.env`

### 4. Reiniciar el Backend

```bash
# Si usas PM2:
pm2 restart all

# Si usas Python directamente:
python backend/app.py
```

---

## 📡 Endpoints Disponibles

### 1. POST `/api/contact-request` - Enviar Email

Envía un email automático cuando un usuario solicita un plan.

**Request:**
```bash
curl -X POST http://localhost:5001/api/contact-request \
  -H "Content-Type: application/json" \
  -d '{
    "plan_name": "Starter",
    "plan_price": "$49",
    "user_email": "user@example.com",
    "user_name": "John Doe",
    "recipient_email": "iriyidan@gmail.com"
  }'
```

**Response (Success):**
```json
{
  "status": "success",
  "message": "Contact request sent successfully"
}
```

**Response (Error):**
```json
{
  "status": "error",
  "message": "Failed to send email. Please try again or contact support."
}
```

### 2. GET `/api/contact-request/test` - Verificar Configuración

Verifica que el email esté configurado correctamente (sin exponer credenciales).

**Request:**
```bash
curl http://localhost:5001/api/contact-request/test
```

**Response (Configurado):**
```json
{
  "status": "success",
  "message": "Email service configured",
  "configured": true,
  "config": {
    "mail_server": true,
    "mail_username": true,
    "mail_password": true,
    "mail_server_value": "smtp.gmail.com"
  }
}
```

**Response (No Configurado):**
```json
{
  "status": "warning",
  "message": "Email service partially configured",
  "configured": false,
  "config": {
    "mail_server": true,
    "mail_username": false,
    "mail_password": false,
    "mail_server_value": "smtp.gmail.com"
  }
}
```

---

## 📧 Formato del Email Enviado

**Subject:**
```
🎯 New Plan Request: Starter Plan
```

**Body:**
```
Hello,

A new plan request has been received from the checkout page.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
USER INFORMATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Name:  John Doe
Email: user@example.com

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PLAN DETAILS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Plan:  Starter
Price: $49/month

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Please contact the user to set up this plan.

Best regards,
RFX Automation System
```

---

## 🔧 Troubleshooting

### Error: "Flask-Mail not configured"

**Causa:** Variables de entorno no están configuradas.

**Solución:**
1. Verifica que tu `.env` tenga todas las variables de email
2. Reinicia el backend después de agregar las variables
3. Usa el endpoint `/api/contact-request/test` para verificar

### Error: "Authentication failed"

**Causa:** Contraseña incorrecta o no es un App Password.

**Solución:**
1. Verifica que estés usando un **App Password**, NO tu contraseña normal
2. Verifica que la verificación en 2 pasos esté activada en Gmail
3. Genera un nuevo App Password si es necesario

### Error: "SMTP connection failed"

**Causa:** Puerto o servidor SMTP incorrecto.

**Solución:**
1. Verifica que `MAIL_SERVER=smtp.gmail.com`
2. Verifica que `MAIL_PORT=587`
3. Verifica que `MAIL_USE_TLS=True`

### Emails no llegan

**Posibles causas:**
1. **Spam folder:** Revisa la carpeta de spam del destinatario
2. **Gmail limits:** Gmail tiene límite de 500 emails/día para cuentas gratuitas
3. **Sender reputation:** Emails desde nuevas cuentas pueden ser marcados como spam

**Solución:**
- Pide al destinatario que agregue `noreply@budyai.com` a sus contactos
- Considera usar un servicio profesional como SendGrid para producción

---

## 📊 Límites de Gmail

| Plan | Límite Diario | Recomendación |
|------|---------------|---------------|
| Gmail Gratuito | 500 emails/día | ✅ Suficiente para tu caso |
| Gmail Workspace | 2,000 emails/día | Para mayor volumen |
| SendGrid Free | 100 emails/día | Alternativa gratuita |
| SendGrid Paid | 40,000+ emails/mes | Para producción |

**Para tu caso:** Gmail gratuito es más que suficiente (no superarás 500 emails/día).

---

## 🔐 Seguridad

### Variables Sensibles

**NUNCA** commitees estas variables a Git:
- ❌ `MAIL_PASSWORD` (App Password)
- ❌ `MAIL_USERNAME` (tu email)

**Siempre** usa `.env` (que está en `.gitignore`).

### App Password vs Contraseña Normal

| Tipo | Seguridad | Uso |
|------|-----------|-----|
| Contraseña Normal | ❌ Menos segura | NO usar en apps |
| App Password | ✅ Más segura | Usar en backend |

**Beneficios de App Password:**
- Puedes revocarla sin cambiar tu contraseña principal
- Tiene permisos limitados (solo email)
- Google la recomienda para aplicaciones

---

## 🧪 Testing

### 1. Test de Configuración

```bash
curl http://localhost:5001/api/contact-request/test
```

**Esperado:** `"configured": true`

### 2. Test de Envío

```bash
curl -X POST http://localhost:5001/api/contact-request \
  -H "Content-Type: application/json" \
  -d '{
    "plan_name": "Test Plan",
    "plan_price": "$0",
    "user_email": "test@example.com",
    "user_name": "Test User",
    "recipient_email": "tu-email@gmail.com"
  }'
```

**Esperado:** Email recibido en tu bandeja de entrada.

### 3. Test desde Frontend

El frontend ya está configurado para llamar automáticamente este endpoint cuando el usuario hace clic en "Contact Us" en el checkout.

---

## 📝 Logs

El sistema genera logs detallados:

**Éxito:**
```
✅ Contact request email sent successfully to iriyidan@gmail.com
📋 Plan: Starter | User: user@example.com
```

**Error:**
```
❌ Error sending contact request email: [error details]
```

**Configuración:**
```
❌ Flask-Mail not configured
```

---

## 🚀 Próximos Pasos

1. ✅ Configurar variables de entorno en `.env`
2. ✅ Obtener Gmail App Password
3. ✅ Reiniciar backend
4. ✅ Probar con `/api/contact-request/test`
5. ✅ Enviar email de prueba
6. ✅ Verificar que llegue correctamente

---

## 📚 Archivos Modificados

| Archivo | Cambios |
|---------|---------|
| `requirements.txt` | Agregado `Flask-Mail==0.9.1` |
| `backend/app.py` | Configuración Flask-Mail + registro blueprint |
| `backend/api/contact.py` | Nuevo endpoint de email |
| `.env.example` | Variables de email con instrucciones |

---

## 💡 Alternativas (Futuro)

Si en el futuro necesitas más volumen o features:

### SendGrid (Recomendado para Producción)

```bash
pip install sendgrid
```

```python
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

message = Mail(
    from_email='noreply@budyai.com',
    to_emails='recipient@example.com',
    subject='Subject',
    html_content='<strong>HTML content</strong>'
)

sg = SendGridAPIClient(os.getenv('SENDGRID_API_KEY'))
response = sg.send(message)
```

**Beneficios:**
- 100 emails/día gratis
- Mejor deliverability
- Analytics incluido
- Más confiable para producción

---

## ✅ Checklist de Implementación

- [x] Flask-Mail agregado a requirements.txt
- [x] Endpoint `/api/contact-request` creado
- [x] Endpoint `/api/contact-request/test` creado
- [x] Flask-Mail configurado en app.py
- [x] Blueprint registrado en app.py
- [x] Variables de entorno documentadas en .env.example
- [x] Documentación completa creada
- [ ] Variables configuradas en tu `.env` local
- [ ] Gmail App Password obtenido
- [ ] Backend reiniciado
- [ ] Endpoint testeado exitosamente

---

## 🆘 Soporte

Si tienes problemas:

1. **Verifica configuración:** `GET /api/contact-request/test`
2. **Revisa logs:** Busca mensajes de error en la consola del backend
3. **Verifica variables:** Asegúrate de que `.env` tenga todas las variables
4. **Reinicia backend:** Cambios en `.env` requieren reinicio

**Contacto:** Si nada funciona, revisa esta documentación paso a paso.
