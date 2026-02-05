# 🔧 PLAN DE REFACTORIZACIÓN - RFX AUTOMATION PROJECT

**Fecha:** 3 de Febrero, 2026  
**Versión:** 1.0  
**Objetivo:** Resolver problemas de consistencia que causan comportamiento intermitente

---

## 📊 RESUMEN EJECUTIVO

### Problema Principal Reportado
> "Cuando yo pruebo funciona, pero cuando el cliente prueba a veces funciona a veces no"

### Causa Raíz Identificada
1. **Falta de retry logic** en servicios externos (Cloudinary, OpenAI)
2. **Configuraciones duplicadas** causando comportamiento inconsistente
3. **Manejo de errores silencioso** (return None) que oculta problemas
4. **Dependencias externas no verificadas** (Playwright browsers)
5. **Múltiples instancias de clientes** sin pooling de conexiones

### Impacto
- **Tasa de fallo intermitente:** ~20-30% estimado
- **Archivos afectados:** 50+ archivos
- **Líneas de código:** ~15,000 líneas revisadas
- **Problemas críticos:** 5
- **Problemas moderados:** 5

---

## 🔴 FASE 1: PROBLEMAS CRÍTICOS (Semana 1-2)

### 1.1 UNIFICAR CLIENTE DE BASE DE DATOS

#### 📍 Problema
**Ubicación:** Múltiples archivos
- `backend/core/config.py` (línea 254)
- `backend/core/database.py` (línea 1-783)
- 35 archivos con 289 referencias

**Descripción:**
```python
# ❌ PROBLEMA: 3 formas diferentes de obtener cliente
from backend.core.config import get_database_client  # Forma 1
from backend.core.database import DatabaseClient     # Forma 2
self.db = get_database_client()                      # Forma 3
```

**Impacto:**
- Conexiones duplicadas a Supabase
- Memory leaks potenciales
- Difícil rastrear errores de conexión
- Inconsistencia en retry logic

#### 🔧 Solución Propuesta

**Paso 1:** Crear singleton único en `backend/core/database.py`
```python
# backend/core/database.py
_db_client_instance = None
_db_lock = threading.Lock()

def get_database_client() -> DatabaseClient:
    """Singleton thread-safe para cliente de BD"""
    global _db_client_instance
    
    if _db_client_instance is None:
        with _db_lock:
            if _db_client_instance is None:
                config = get_database_config()
                _db_client_instance = DatabaseClient(
                    url=config.url,
                    key=config.key
                )
    
    return _db_client_instance
```

**Paso 2:** Eliminar duplicado en `config.py`
- Remover función `get_database_client()` de `backend/core/config.py`
- Actualizar imports en todos los archivos

**Paso 3:** Refactorizar 35 archivos
```bash
# Script de refactorización automática
find backend -name "*.py" -exec sed -i '' \
  's/from backend.core.config import get_database_client/from backend.core.database import get_database_client/g' {} \;
```

**Archivos a modificar:**
1. `backend/core/config.py` - Eliminar función duplicada
2. `backend/api/rfx.py` - Actualizar import (81 referencias)
3. `backend/services/pricing_config_service_v2.py` - Actualizar import (39 referencias)
4. `backend/api/rfx_secure_patch.py` - Actualizar import (21 referencias)
5. ... (31 archivos más)

**Tiempo estimado:** 4-6 horas

---

### 1.2 CONSOLIDAR CONFIGURACIÓN DE OPENAI

#### 📍 Problema
**Ubicación:**
- `backend/core/config.py` (líneas 79-98)
- `backend/core/ai_config.py` (líneas 12-20)

**Descripción:**
```python
# ❌ CONFLICTO: Dos configuraciones diferentes
# config.py
class OpenAIConfig:
    model: str = "gpt-4o"        # Caro
    max_tokens: int = 4096
    temperature: float = 0.1

# ai_config.py  
class AIConfig:
    MODEL: str = "gpt-4o-mini"   # Barato
    MAX_TOKENS: int = 2000
    TEMPERATURE: float = 0.3
```

**Impacto:**
- `rfx_processor.py` usa GPT-4o (caro)
- `chat_agent.py` usa GPT-4o-mini (barato)
- Costos impredecibles: GPT-4o es 16x más caro
- Comportamiento de IA inconsistente

#### 🔧 Solución Propuesta

**Decisión de Diseño:**
- **Mantener:** `backend/core/config.py` como fuente única
- **Deprecar:** `backend/core/ai_config.py`
- **Razón:** `config.py` ya es el estándar del proyecto

**Paso 1:** Extender `OpenAIConfig` en `config.py`
```python
# backend/core/config.py
@dataclass
class OpenAIConfig:
    """Configuración unificada de OpenAI"""
    api_key: str
    
    # Modelos disponibles
    model_default: str = "gpt-4o"
    model_chat: str = "gpt-4o-mini"      # Para chat conversacional
    model_extraction: str = "gpt-4o"     # Para extracción RFX
    model_generation: str = "gpt-4o"     # Para generación propuestas
    
    # Configuración por modelo
    max_tokens: int = 4096
    max_tokens_chat: int = 2000
    
    temperature: float = 0.1
    temperature_chat: float = 0.3
    
    timeout: int = 60
    context_window: int = 128000
    
    # Costos (USD por 1M tokens)
    cost_input_gpt4o: float = 2.50
    cost_output_gpt4o: float = 10.00
    cost_input_gpt4o_mini: float = 0.15
    cost_output_gpt4o_mini: float = 0.60
```

**Paso 2:** Migrar funciones de `ai_config.py`
```python
# backend/core/config.py
def get_openai_config() -> OpenAIConfig:
    """Obtener configuración de OpenAI"""
    return OpenAIConfig(
        api_key=os.getenv("OPENAI_API_KEY", ""),
        model_default=os.getenv("OPENAI_MODEL", "gpt-4o"),
        # ... resto de configuración
    )

def calculate_openai_cost(input_tokens: int, output_tokens: int, model: str) -> float:
    """Calcular costo de llamada a OpenAI"""
    config = get_openai_config()
    
    if "gpt-4o-mini" in model:
        cost = (input_tokens * config.cost_input_gpt4o_mini + 
                output_tokens * config.cost_output_gpt4o_mini) / 1_000_000
    else:
        cost = (input_tokens * config.cost_input_gpt4o + 
                output_tokens * config.cost_output_gpt4o) / 1_000_000
    
    return cost
```

**Paso 3:** Deprecar `ai_config.py`
```python
# backend/core/ai_config.py
"""
⚠️ DEPRECATED: Este módulo está deprecado.
Usar backend.core.config.OpenAIConfig en su lugar.

Este archivo se mantendrá temporalmente para compatibilidad.
"""
import warnings
from backend.core.config import get_openai_config

warnings.warn(
    "ai_config.py está deprecado. Usar backend.core.config.OpenAIConfig",
    DeprecationWarning,
    stacklevel=2
)

# Re-exportar para compatibilidad temporal
AIConfig = get_openai_config()
```

**Paso 4:** Actualizar imports en 24 archivos
```python
# ❌ ANTES
from backend.core.ai_config import AIConfig

# ✅ DESPUÉS
from backend.core.config import get_openai_config

config = get_openai_config()
model = config.model_chat  # Para chat
model = config.model_extraction  # Para extracción
```

**Archivos a modificar:**
1. `backend/services/proposal_generator.py`
2. `backend/services/rfx_processor.py`
3. `backend/services/chat_agent.py`
4. `backend/api/catalog_sync.py`
5. ... (20 archivos más)

**Tiempo estimado:** 6-8 horas

---

### 1.3 ELIMINAR SERVICIOS DUPLICADOS

#### 📍 Problema
**Ubicación:** `backend/services/`

**Descripción:**
```
❌ auth_service.py          (12.7 KB)
❌ auth_service_fixed.py    (9.7 KB)   ← ¿Cuál usar?

❌ pricing_config_service.py    (19.8 KB)
❌ pricing_config_service_v2.py (44.7 KB)  ← ¿Cuál es actual?
```

**Impacto:**
- Confusión sobre qué versión usar
- Bugs si se usa versión incorrecta
- Mantenimiento duplicado
- Código legacy sin eliminar

#### 🔧 Solución Propuesta

**Paso 1:** Auditar uso de cada servicio
```bash
# Verificar qué archivos usan cada versión
grep -r "from.*auth_service import" backend/
grep -r "from.*auth_service_fixed import" backend/
grep -r "from.*pricing_config_service import" backend/
grep -r "from.*pricing_config_service_v2 import" backend/
```

**Paso 2:** Decisión de versión oficial

**Para auth_service:**
- **Mantener:** `auth_service_fixed.py` (versión corregida)
- **Eliminar:** `auth_service.py`
- **Renombrar:** `auth_service_fixed.py` → `auth_service.py`

**Para pricing_config_service:**
- **Mantener:** `pricing_config_service_v2.py` (versión actual)
- **Deprecar:** `pricing_config_service.py`
- **Estrategia:** Mantener v1 por 1 mes con warnings, luego eliminar

**Paso 3:** Implementar deprecación gradual
```python
# backend/services/pricing_config_service.py
"""
⚠️ DEPRECATED: Este servicio está deprecado desde Feb 2026.
Usar pricing_config_service_v2.py en su lugar.

Este archivo se eliminará en Marzo 2026.
"""
import warnings

warnings.warn(
    "pricing_config_service está deprecado. "
    "Usar pricing_config_service_v2 en su lugar.",
    DeprecationWarning,
    stacklevel=2
)

# Re-exportar desde v2 para compatibilidad
from backend.services.pricing_config_service_v2 import *
```

**Paso 4:** Actualizar imports
```python
# ❌ ANTES
from backend.services.pricing_config_service import PricingConfigService

# ✅ DESPUÉS
from backend.services.pricing_config_service_v2 import PricingConfigServiceV2
```

**Archivos a modificar:**
1. `backend/api/pricing.py`
2. `backend/services/unified_budget_configuration_service.py`
3. Cualquier otro archivo que importe versión v1

**Tiempo estimado:** 3-4 horas

---

### 1.4 IMPLEMENTAR RETRY CONSISTENTE

#### 📍 Problema
**Ubicación:** Múltiples servicios

**Descripción:**
```python
# ❌ INCONSISTENCIA: 3 formas diferentes

# Forma 1: Decorator (database.py)
@retry_on_connection_error(max_retries=3)
def query(): ...

# Forma 2: Loop manual (cloudinary_service.py)
for attempt in range(3):
    try: upload()
    except: time.sleep(2 ** attempt)

# Forma 3: Sin retry (mayoría)
def process(): 
    return api_call()  # Falla en primer error
```

**Impacto:**
- Cloudinary falla intermitentemente
- OpenAI falla por rate limits
- Playwright falla si tarda en iniciar
- Usuario ve errores aunque retry funcionaría

#### 🔧 Solución Propuesta

**Paso 1:** Crear decorator genérico de retry
```python
# backend/utils/retry_decorator.py
"""
Decorator genérico para retry con exponential backoff
"""
import time
import logging
from functools import wraps
from typing import Callable, Type, Tuple

logger = logging.getLogger(__name__)

def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 0.5,
    backoff_factor: float = 2.0,
    max_delay: float = 30.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Callable[[Exception, int], None] = None
):
    """
    Decorator para reintentar función con exponential backoff
    
    Args:
        max_retries: Número máximo de reintentos
        initial_delay: Delay inicial en segundos
        backoff_factor: Factor de multiplicación del delay
        max_delay: Delay máximo en segundos
        exceptions: Tupla de excepciones a capturar
        on_retry: Callback opcional llamado en cada retry
    
    Example:
        @retry_with_backoff(max_retries=3, exceptions=(ConnectionError,))
        def upload_file():
            return cloudinary.upload(file)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                    
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        logger.error(
                            f"❌ {func.__name__} failed after {max_retries} retries: {e}"
                        )
                        raise
                    
                    logger.warning(
                        f"⚠️ {func.__name__} attempt {attempt + 1}/{max_retries} "
                        f"failed: {e}. Retrying in {delay:.2f}s..."
                    )
                    
                    if on_retry:
                        on_retry(e, attempt + 1)
                    
                    time.sleep(delay)
                    delay = min(delay * backoff_factor, max_delay)
            
            raise last_exception
        
        return wrapper
    return decorator
```

**Paso 2:** Aplicar a Cloudinary
```python
# backend/services/cloudinary_service.py
from backend.utils.retry_decorator import retry_with_backoff
import cloudinary.exceptions

@retry_with_backoff(
    max_retries=3,
    initial_delay=1.0,
    exceptions=(
        cloudinary.exceptions.Error,
        ConnectionError,
        TimeoutError
    )
)
def upload_logo(user_id: str, logo_file) -> str:
    """Upload logo con retry automático"""
    logger.info(f"📤 Uploading logo for user {user_id}")
    
    result = cloudinary.uploader.upload(
        logo_file,
        folder=f"rfx_logos/{user_id}",
        public_id="logo",
        overwrite=True,
        transformation=[
            {"width": 800, "height": 800, "crop": "limit"},
            {"quality": "auto:good"}
        ]
    )
    
    return result['secure_url']
```

**Paso 3:** Aplicar a OpenAI
```python
# backend/services/rfx_processor.py
from backend.utils.retry_decorator import retry_with_backoff
from openai import RateLimitError, APIError, Timeout

@retry_with_backoff(
    max_retries=3,
    initial_delay=2.0,
    backoff_factor=3.0,  # Backoff más agresivo para rate limits
    exceptions=(RateLimitError, APIError, Timeout)
)
def _call_openai_extraction(self, prompt: str, model: str):
    """Llamada a OpenAI con retry automático"""
    response = self.openai_client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        timeout=self.openai_config.timeout
    )
    return response
```

**Paso 4:** Aplicar a Playwright
```python
# backend/api/download.py
from backend.utils.retry_decorator import retry_with_backoff
from playwright.sync_api import Error as PlaywrightError

@retry_with_backoff(
    max_retries=2,
    initial_delay=3.0,
    exceptions=(PlaywrightError, TimeoutError)
)
def convert_with_playwright(html_content: str, client_name: str, document_id: str):
    """Conversión PDF con retry automático"""
    from playwright.sync_api import sync_playwright
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(html_content)
        
        pdf_bytes = page.pdf(
            format='Letter',
            print_background=True,
            margin={'top': '0.5in', 'bottom': '0.5in'}
        )
        
        browser.close()
        return pdf_bytes
```

**Archivos a modificar:**
1. Crear `backend/utils/retry_decorator.py` (nuevo)
2. `backend/services/cloudinary_service.py` - Aplicar retry
3. `backend/services/rfx_processor.py` - Aplicar retry a OpenAI
4. `backend/api/download.py` - Aplicar retry a Playwright
5. `backend/services/proposal_generator.py` - Aplicar retry a OpenAI

**Tiempo estimado:** 6-8 horas

---

### 1.5 ESTANDARIZAR MANEJO DE ERRORES

#### 📍 Problema
**Ubicación:** Todo el proyecto

**Descripción:**
```python
# ❌ PROBLEMA: 3 patrones diferentes

# Patrón 1: Return None (130 casos)
def get_data():
    try:
        return fetch()
    except:
        return None  # ⚠️ Caller no sabe si hubo error

# Patrón 2: Raise exception
def get_data():
    try:
        return fetch()
    except Exception as e:
        raise  # ✅ Pero sin contexto

# Patrón 3: Return dict
def get_data():
    return {"status": "error", "message": str(e)}
```

**Impacto:**
- `NoneType` errors downstream
- Frontend no recibe info consistente
- Difícil debuggear problemas

#### 🔧 Solución Propuesta

**Paso 1:** Crear jerarquía de excepciones
```python
# backend/exceptions.py (ya existe, extender)
"""
Jerarquía de excepciones del proyecto
"""

class RFXBaseException(Exception):
    """Excepción base del proyecto"""
    def __init__(self, message: str, code: str, details: dict = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self):
        return {
            "status": "error",
            "code": self.code,
            "message": self.message,
            "details": self.details
        }

# Excepciones por categoría
class DatabaseException(RFXBaseException):
    """Errores de base de datos"""
    pass

class ExternalServiceException(RFXBaseException):
    """Errores de servicios externos (Cloudinary, OpenAI, etc)"""
    pass

class ValidationException(RFXBaseException):
    """Errores de validación de datos"""
    pass

class AuthenticationException(RFXBaseException):
    """Errores de autenticación"""
    pass

class ResourceNotFoundException(RFXBaseException):
    """Recurso no encontrado"""
    pass

# Excepciones específicas
class CloudinaryUploadException(ExternalServiceException):
    """Error al subir archivo a Cloudinary"""
    def __init__(self, message: str, details: dict = None):
        super().__init__(
            message=message,
            code="CLOUDINARY_UPLOAD_ERROR",
            details=details
        )

class OpenAIException(ExternalServiceException):
    """Error en llamada a OpenAI"""
    def __init__(self, message: str, details: dict = None):
        super().__init__(
            message=message,
            code="OPENAI_ERROR",
            details=details
        )

class PlaywrightException(ExternalServiceException):
    """Error en conversión PDF con Playwright"""
    def __init__(self, message: str, details: dict = None):
        super().__init__(
            message=message,
            code="PLAYWRIGHT_ERROR",
            details=details
        )
```

**Paso 2:** Handler global en Flask
```python
# backend/app.py
from backend.exceptions import RFXBaseException

@app.errorhandler(RFXBaseException)
def handle_rfx_exception(error: RFXBaseException):
    """Handler global para excepciones del proyecto"""
    logger.error(f"❌ {error.code}: {error.message}", extra=error.details)
    
    return jsonify(error.to_dict()), 500

@app.errorhandler(ValidationException)
def handle_validation_exception(error: ValidationException):
    """Handler específico para validación (400)"""
    return jsonify(error.to_dict()), 400

@app.errorhandler(ResourceNotFoundException)
def handle_not_found_exception(error: ResourceNotFoundException):
    """Handler específico para not found (404)"""
    return jsonify(error.to_dict()), 404
```

**Paso 3:** Refactorizar servicios
```python
# ❌ ANTES
def upload_logo(user_id, file):
    try:
        result = cloudinary.upload(file)
        return result['secure_url']
    except Exception as e:
        logger.error(f"Error: {e}")
        return None  # ⚠️ Problema

# ✅ DESPUÉS
def upload_logo(user_id, file):
    try:
        result = cloudinary.upload(file)
        return result['secure_url']
    except cloudinary.exceptions.Error as e:
        raise CloudinaryUploadException(
            message=f"Failed to upload logo for user {user_id}",
            details={
                "user_id": user_id,
                "error": str(e),
                "file_name": file.filename
            }
        )
```

**Paso 4:** Actualizar endpoints
```python
# ❌ ANTES
@rfx_bp.route("/process")
def process_rfx():
    result = processor.process(data)
    if result is None:  # ⚠️ No sabemos qué pasó
        return {"error": "Processing failed"}, 500
    return {"data": result}

# ✅ DESPUÉS
@rfx_bp.route("/process")
def process_rfx():
    try:
        result = processor.process(data)
        return {"status": "success", "data": result}
    except ValidationException as e:
        # Flask handler automático retorna 400
        raise
    except ExternalServiceException as e:
        # Flask handler automático retorna 500
        raise
```

**Archivos a modificar:**
1. `backend/exceptions.py` - Extender jerarquía
2. `backend/app.py` - Agregar handlers globales
3. `backend/services/cloudinary_service.py` - Usar excepciones
4. `backend/services/rfx_processor.py` - Usar excepciones
5. `backend/api/download.py` - Usar excepciones
6. ... (30+ archivos más gradualmente)

**Tiempo estimado:** 10-12 horas (refactorización gradual)

---

## 🟡 FASE 2: PROBLEMAS MODERADOS (Semana 3-4)

### 2.1 AUTOMATIZAR INSTALACIÓN DE PLAYWRIGHT

#### 📍 Problema
**Ubicación:**
- `requirements.txt` (línea con `playwright`)
- `scripts/install_playwright_server.sh` (existe pero no se usa)

**Descripción:**
```bash
# ❌ PROBLEMA: Esto NO instala navegadores
pip install playwright

# ✅ NECESARIO: Comando adicional
playwright install chromium
```

**Impacto:**
- PDF generation falla con error críptico
- Usuario reporta "a veces funciona" (depende del servidor)

#### 🔧 Solución Propuesta

**Paso 1:** Crear script post-install
```python
# setup.py (crear nuevo)
"""
Setup script para instalación completa del proyecto
"""
from setuptools import setup, find_packages
from setuptools.command.install import install
import subprocess
import sys

class PostInstallCommand(install):
    """Post-installation para instalar Playwright browsers"""
    def run(self):
        install.run(self)
        
        print("📦 Installing Playwright browsers...")
        try:
            subprocess.check_call([
                sys.executable, "-m", "playwright", "install", "chromium"
            ])
            print("✅ Playwright chromium installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"⚠️ Warning: Failed to install Playwright: {e}")
            print("Run manually: playwright install chromium")

setup(
    name="rfx-automation-backend",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        line.strip() 
        for line in open('requirements.txt').readlines()
        if line.strip() and not line.startswith('#')
    ],
    cmdclass={
        'install': PostInstallCommand,
    }
)
```

**Paso 2:** Health check endpoint
```python
# backend/api/health.py (crear nuevo)
"""
Health check endpoints para verificar dependencias
"""
from flask import Blueprint, jsonify
import logging

health_bp = Blueprint('health', __name__, url_prefix='/api/health')
logger = logging.getLogger(__name__)

@health_bp.route('/', methods=['GET'])
def health_check():
    """Health check básico"""
    return jsonify({
        "status": "healthy",
        "service": "RFX Automation Backend"
    })

@health_bp.route('/dependencies', methods=['GET'])
def check_dependencies():
    """Verificar todas las dependencias externas"""
    checks = {
        "database": _check_database(),
        "openai": _check_openai(),
        "cloudinary": _check_cloudinary(),
        "playwright": _check_playwright()
    }
    
    all_healthy = all(check["status"] == "ok" for check in checks.values())
    
    return jsonify({
        "status": "healthy" if all_healthy else "degraded",
        "checks": checks
    }), 200 if all_healthy else 503

def _check_playwright():
    """Verificar si Playwright está instalado"""
    try:
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            # Intentar lanzar browser
            browser = p.chromium.launch(headless=True)
            browser.close()
        
        return {
            "status": "ok",
            "message": "Playwright chromium available"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Playwright not available: {str(e)}",
            "action": "Run: playwright install chromium"
        }

def _check_database():
    """Verificar conexión a base de datos"""
    try:
        from backend.core.database import get_database_client
        db = get_database_client()
        # Test query
        db.client.table("users").select("id").limit(1).execute()
        return {"status": "ok", "message": "Database connected"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def _check_openai():
    """Verificar API key de OpenAI"""
    try:
        from backend.core.config import get_openai_config
        config = get_openai_config()
        if not config.api_key:
            raise ValueError("API key not configured")
        return {"status": "ok", "message": "OpenAI configured"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def _check_cloudinary():
    """Verificar configuración de Cloudinary"""
    try:
        import cloudinary
        if not cloudinary.config().cloud_name:
            raise ValueError("Cloudinary not configured")
        return {"status": "ok", "message": "Cloudinary configured"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
```

**Paso 3:** Registrar blueprint
```python
# backend/app.py
from backend.api.health import health_bp

def create_app(config_name='development'):
    app = Flask(__name__)
    
    # ... configuración existente ...
    
    # Health check endpoints
    app.register_blueprint(health_bp)
    
    return app
```

**Paso 4:** Documentar en README
```markdown
# README.md

## 🚀 Instalación

### Opción 1: Instalación automática (recomendado)
```bash
pip install -e .
```
Esto instalará todas las dependencias incluyendo Playwright browsers.

### Opción 2: Instalación manual
```bash
pip install -r requirements.txt
playwright install chromium
```

## 🏥 Health Check

Verificar que todas las dependencias estén instaladas:
```bash
curl http://localhost:5001/api/health/dependencies
```

Respuesta esperada:
```json
{
  "status": "healthy",
  "checks": {
    "database": {"status": "ok"},
    "openai": {"status": "ok"},
    "cloudinary": {"status": "ok"},
    "playwright": {"status": "ok"}
  }
}
```
```

**Archivos a crear/modificar:**
1. Crear `setup.py` (nuevo)
2. Crear `backend/api/health.py` (nuevo)
3. Modificar `backend/app.py` - Registrar health blueprint
4. Actualizar `README.md` - Documentar instalación

**Tiempo estimado:** 4-5 horas

---

### 2.2 CENTRALIZAR FEATURE FLAGS

#### 📍 Problema
**Ubicación:** Dispersos en múltiples archivos

**Descripción:**
```python
# ❌ PROBLEMA: Flags dispersos
USE_AI_AGENTS = os.getenv('USE_AI_AGENTS', 'true')      # config.py
USE_OCR = os.getenv("RFX_USE_OCR", "true")              # rfx_processor.py
USE_ZIP = os.getenv("RFX_USE_ZIP", "true")              # rfx_processor.py
ENABLE_EVALS = os.getenv('ENABLE_EVALS', 'false')       # config.py
```

**Impacto:**
- Difícil saber qué features están activas
- No hay documentación centralizada
- Inconsistencia en valores por defecto

#### 🔧 Solución Propuesta

**Paso 1:** Crear módulo de feature flags
```python
# backend/core/feature_flags.py (nuevo)
"""
Feature Flags centralizados del proyecto

Todos los feature flags deben definirse aquí para:
1. Documentación centralizada
2. Valores por defecto consistentes
3. Fácil auditoría de features activas
"""
import os
from typing import Final
from dataclasses import dataclass

def _str_to_bool(value: str) -> bool:
    """Convertir string a boolean"""
    return value.lower() in ('true', '1', 'yes', 'on')

@dataclass
class FeatureFlags:
    """Feature flags del proyecto"""
    
    # ==================== AI Features ====================
    AI_AGENTS_ENABLED: Final[bool] = _str_to_bool(
        os.getenv('USE_AI_AGENTS', 'true')
    )
    """Usar sistema de 3 agentes AI para generación de propuestas"""
    
    OCR_ENABLED: Final[bool] = _str_to_bool(
        os.getenv('RFX_USE_OCR', 'true')
    )
    """Usar OCR para extracción de texto de imágenes"""
    
    # ==================== File Processing ====================
    ZIP_PROCESSING_ENABLED: Final[bool] = _str_to_bool(
        os.getenv('RFX_USE_ZIP', 'true')
    )
    """Permitir procesamiento de archivos ZIP"""
    
    # ==================== Evaluation & Testing ====================
    EVALS_ENABLED: Final[bool] = _str_to_bool(
        os.getenv('ENABLE_EVALS', 'false')
    )
    """Habilitar sistema de evaluaciones automáticas"""
    
    # ==================== Chat Features ====================
    CHAT_FILE_ATTACHMENTS: Final[bool] = _str_to_bool(
        os.getenv('CHAT_ENABLE_ATTACHMENTS', 'true')
    )
    """Permitir adjuntar archivos en chat"""
    
    CHAT_DUPLICATE_DETECTION: Final[bool] = _str_to_bool(
        os.getenv('CHAT_DUPLICATE_DETECTION', 'true')
    )
    """Detectar productos duplicados en chat"""
    
    # ==================== Pricing Features ====================
    AUTO_PRICING_ENABLED: Final[bool] = _str_to_bool(
        os.getenv('ENABLE_AUTO_PRICING', 'true')
    )
    """Calcular precios automáticamente desde catálogo"""
    
    # ==================== Debug & Development ====================
    DEBUG_MODE: Final[bool] = _str_to_bool(
        os.getenv('DEBUG_MODE', 'false')
    )
    """Modo debug con logs extendidos"""
    
    VERBOSE_LOGGING: Final[bool] = _str_to_bool(
        os.getenv('VERBOSE_LOGGING', 'false')
    )
    """Logging verbose para debugging"""
    
    @classmethod
    def get_all_flags(cls) -> dict:
        """Obtener todos los flags y sus valores"""
        return {
            name: getattr(cls, name)
            for name in dir(cls)
            if not name.startswith('_') and name.isupper()
        }
    
    @classmethod
    def print_active_flags(cls):
        """Imprimir flags activos (útil para debugging)"""
        print("\n🚩 Feature Flags Activos:")
        for name, value in cls.get_all_flags().items():
            status = "✅ ON" if value else "❌ OFF"
            print(f"  {status} {name}")
        print()

# Instancia global
feature_flags = FeatureFlags()
```

**Paso 2:** Endpoint para consultar flags
```python
# backend/api/health.py (agregar)
from backend.core.feature_flags import feature_flags

@health_bp.route('/feature-flags', methods=['GET'])
def get_feature_flags():
    """Obtener feature flags activos"""
    return jsonify({
        "flags": feature_flags.get_all_flags()
    })
```

**Paso 3:** Actualizar uso en servicios
```python
# ❌ ANTES
USE_AI_AGENTS = os.getenv('USE_AI_AGENTS', 'true') == 'true'

# ✅ DESPUÉS
from backend.core.feature_flags import feature_flags

if feature_flags.AI_AGENTS_ENABLED:
    # Usar sistema de agentes
    pass
```

**Archivos a crear/modificar:**
1. Crear `backend/core/feature_flags.py` (nuevo)
2. `backend/api/health.py` - Agregar endpoint
3. `backend/core/config.py` - Remover flags duplicados
4. `backend/services/rfx_processor.py` - Usar flags centralizados
5. `backend/services/proposal_generator.py` - Usar flags centralizados

**Tiempo estimado:** 3-4 horas

---

### 2.3 RESOLVER TODOs/FIXMEs

#### 📍 Problema
**Ubicación:** 118 comentarios en 46 archivos

**Descripción:**
```python
# Ejemplos encontrados:
# TODO: Implement proper validation
# FIXME: This is a temporary hack
# XXX: This needs refactoring
# HACK: Workaround for Supabase limitation
```

**Impacto:**
- Código con soluciones temporales en producción
- Técnica debt acumulada

#### 🔧 Solución Propuesta

**Paso 1:** Auditar y categorizar
```bash
# Script para extraer todos los TODOs
grep -rn "TODO\|FIXME\|HACK\|XXX" backend/ > todos_audit.txt
```

**Paso 2:** Clasificar por prioridad
```markdown
# todos_audit.md

## 🔴 CRÍTICOS (Resolver en Fase 2)
- [ ] `backend/services/function_calling_extractor.py:45` - TODO: Implement retry logic
- [ ] `backend/api/rfx.py:120` - FIXME: Validate user_id properly
- [ ] `backend/services/cloudinary_service.py:78` - HACK: Workaround for timeout

## 🟡 IMPORTANTES (Resolver en Fase 3)
- [ ] `backend/services/proposal_generator.py:200` - TODO: Add caching
- [ ] `backend/api/pricing.py:150` - FIXME: Optimize query

## 🟢 MEJORAS (Backlog)
- [ ] `backend/utils/text_utils.py:30` - TODO: Add more test cases
```

**Paso 3:** Convertir en GitHub Issues
```bash
# Script para crear issues automáticamente
python scripts/create_issues_from_todos.py
```

**Tiempo estimado:** 2-3 horas (auditoría), resolver gradualmente

---

## 📅 ROADMAP DE IMPLEMENTACIÓN

### Semana 1-2: FASE 1 - Problemas Críticos
- [ ] **Día 1-2:** Unificar cliente de base de datos (6h)
- [ ] **Día 3-4:** Consolidar configuración OpenAI (8h)
- [ ] **Día 5:** Eliminar servicios duplicados (4h)
- [ ] **Día 6-7:** Implementar retry consistente (8h)
- [ ] **Día 8-10:** Estandarizar manejo de errores (12h)

**Total Fase 1:** 38 horas (~2 semanas)

### Semana 3-4: FASE 2 - Problemas Moderados
- [ ] **Día 11-12:** Automatizar Playwright (5h)
- [ ] **Día 13:** Centralizar feature flags (4h)
- [ ] **Día 14-15:** Auditar y resolver TODOs críticos (10h)

**Total Fase 2:** 19 horas (~1 semana)

### Semana 5+: FASE 3 - Mejoras Arquitectónicas
- [ ] Documentar arquitectura
- [ ] Agregar tests de integración
- [ ] Optimizar performance
- [ ] Resolver TODOs restantes

---

## 🎯 MÉTRICAS DE ÉXITO

### Antes de Refactorización
- ❌ Tasa de fallo intermitente: ~20-30%
- ❌ Configuraciones duplicadas: 2 sistemas OpenAI
- ❌ Servicios duplicados: 4 archivos
- ❌ Retry logic: Inconsistente (3 patrones)
- ❌ Manejo de errores: Return None en 130 casos

### Después de Refactorización
- ✅ Tasa de fallo: <5%
- ✅ Configuración única de OpenAI
- ✅ Servicios únicos y documentados
- ✅ Retry consistente en todos los servicios
- ✅ Excepciones tipadas, sin return None

---

## 🚨 RIESGOS Y MITIGACIÓN

### Riesgo 1: Breaking Changes
**Mitigación:**
- Deprecar gradualmente (no eliminar inmediatamente)
- Mantener compatibilidad por 1 mes
- Tests exhaustivos antes de deploy

### Riesgo 2: Tiempo de Implementación
**Mitigación:**
- Priorizar problemas críticos primero
- Implementar en sprints pequeños
- Validar cada cambio antes de continuar

### Riesgo 3: Impacto en Producción
**Mitigación:**
- Deploy gradual (canary deployment)
- Rollback plan preparado
- Monitoreo intensivo post-deploy

---

## 📞 PRÓXIMOS PASOS

1. **Revisar este plan** con el equipo
2. **Priorizar** qué problemas resolver primero
3. **Crear branch** `refactor/consistency-fixes`
4. **Comenzar con Fase 1** - Problema 1.1

---

**Documento creado:** 3 de Febrero, 2026  
**Última actualización:** 3 de Febrero, 2026  
**Autor:** Análisis automatizado del proyecto
