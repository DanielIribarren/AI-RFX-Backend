# 🚀 Instalación Rápida - Backend RFX

## Problema Resuelto

**Antes:** `pip install -r requirements.txt` tardaba **horas** haciendo backtracking para resolver dependencias de LangChain.

**Ahora:** Instalación completa en **menos de 5 minutos** usando versiones específicas.

---

## 📋 Opciones de Instalación

### **Opción 1: Desarrollo Local (Recomendado)**

```bash
# 1. Activar entorno virtual
source venv/bin/activate  # Mac/Linux
# o
venv\Scripts\activate  # Windows

# 2. Instalar dependencias base
pip install -r requirements.txt

# 3. Instalar LangChain (modo rápido)
chmod +x install_langchain_fast.sh
./install_langchain_fast.sh

# 4. Iniciar servidor
python start_backend.py
```

**Tiempo estimado:** 3-5 minutos

---

### **Opción 2: Servidor PM2 (Producción)**

```bash
# 1. Subir código al servidor
git pull origin ChatAgent

# 2. Ejecutar setup completo
chmod +x setup_pm2.sh
./setup_pm2.sh

# 3. Iniciar con PM2
pm2 start ecosystem.dev.config.js
pm2 logs
```

**Tiempo estimado:** 5-7 minutos (incluye instalación de Playwright)

---

## 🔧 Scripts Disponibles

### `install_langchain_fast.sh`
Instala LangChain con versiones específicas usando `--no-deps` para evitar backtracking.

**Versiones instaladas:**
- `langchain==0.1.9`
- `langchain-openai==0.0.5`
- `langchain-community==0.0.25`
- `langchain-core==0.1.23`
- `langchain-text-splitters==0.0.1`

### `setup_pm2.sh`
Setup completo para PM2 que incluye:
1. Instalación de dependencias base
2. Instalación de LangChain (modo rápido)
3. Instalación de navegadores Playwright

---

## ⚡ Por Qué Es Rápido

### **Problema Original:**
```bash
pip install langchain>=0.1.0  # ❌ Backtracking infinito
```

Pip intenta resolver **todas las combinaciones posibles** de versiones compatibles:
- `langchain` tiene 50+ versiones
- `langchain-openai` tiene 60+ versiones
- `langchain-community` tiene 30+ versiones
- **Total:** Miles de combinaciones a probar

### **Solución Implementada:**
```bash
pip install --no-deps langchain==0.1.9  # ✅ Versión específica
```

Instalamos versiones **específicas probadas** que funcionan juntas, sin resolver dependencias.

---

## 📦 Dependencias Instaladas

### **Core (Flask + Supabase)**
- `flask`, `flask-cors`
- `supabase`
- `python-dotenv`
- `pydantic`

### **AI & Processing**
- `openai`
- `langchain` (suite completa)
- `PyPDF2`, `python-docx`
- `pytesseract`, `Pillow`

### **PDF Generation**
- `playwright`
- `pdf2image`

---

## 🐛 Troubleshooting

### Error: "ModuleNotFoundError: No module named 'langchain'"

**Solución:**
```bash
./install_langchain_fast.sh
```

### Error: "Executable doesn't exist at .../chromium"

**Solución:**
```bash
playwright install chromium
```

### Error: Backtracking infinito

**Solución:** Usa `install_langchain_fast.sh` en lugar de `pip install -r requirements.txt` directamente.

---

## 🔄 Actualizar Dependencias

Si necesitas actualizar LangChain en el futuro:

```bash
# 1. Editar versiones en install_langchain_fast.sh
LANGCHAIN_VERSION="0.1.10"  # Nueva versión

# 2. Ejecutar script
./install_langchain_fast.sh

# 3. Actualizar requirements.txt
langchain==0.1.10
```

---

## 📊 Comparación de Tiempos

| Método | Tiempo | Status |
|--------|--------|--------|
| `pip install -r requirements.txt` (sin versiones fijas) | 2-4 horas ⏰ | ❌ Backtracking |
| `pip install -r requirements.txt` (con versiones fijas) | 5-10 minutos | ✅ Funciona |
| `./install_langchain_fast.sh` | 1-2 minutos | ✅✅ Óptimo |

---

## ✅ Verificar Instalación

```bash
python3 -c "
import langchain
import langchain_openai
import langchain_community
print(f'✅ LangChain {langchain.__version__}')
print(f'✅ LangChain OpenAI {langchain_openai.__version__}')
print(f'✅ LangChain Community {langchain_community.__version__}')
"
```

**Output esperado:**
```
✅ LangChain 0.1.9
✅ LangChain OpenAI 0.0.5
✅ LangChain Community 0.0.25
```

---

## 🎯 Resumen

**Para desarrollo local:**
```bash
./install_langchain_fast.sh && python start_backend.py
```

**Para servidor PM2:**
```bash
./setup_pm2.sh && pm2 start ecosystem.dev.config.js
```

**¡Listo en menos de 5 minutos!** 🚀
