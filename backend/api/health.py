"""
🏥 Health Check API - Monitoreo y diagnóstico del sistema

Proporciona endpoints para verificar el estado del sistema:
- Health check básico
- Verificación de dependencias (DB, OpenAI, Cloudinary)
- Métricas del sistema
- Readiness check

Usage:
    GET /api/health - Health check básico
    GET /api/health/ready - Readiness check (todas las dependencias)
    GET /api/health/live - Liveness check (servidor funcionando)
"""
import os
import logging
from datetime import datetime
from typing import Dict, Any
from flask import Blueprint, jsonify

from backend.utils.api_response import success_response, error_response
from backend.core.database import get_database_client
from backend.core.config import get_openai_config

logger = logging.getLogger(__name__)

health_bp = Blueprint('health', __name__, url_prefix='/api/health')


@health_bp.route('', methods=['GET'])
@health_bp.route('/', methods=['GET'])
def health_check():
    """
    Health check básico - verifica que el servidor esté funcionando.
    
    Returns:
        200: Servidor funcionando correctamente
    
    Example:
        GET /api/health
        
        Response:
        {
            "status": "success",
            "message": "Service is healthy",
            "data": {
                "service": "RFX Automation Backend",
                "version": "3.0.0",
                "status": "healthy",
                "timestamp": "2026-02-05T12:00:00Z"
            }
        }
    """
    try:
        data = {
            "service": "RFX Automation Backend",
            "version": "3.0.0",
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "environment": os.getenv("ENVIRONMENT", "development")
        }
        
        return success_response(
            data=data,
            message="Service is healthy"
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return error_response(
            message="Health check failed",
            status_code=500,
            details=str(e)
        )


@health_bp.route('/live', methods=['GET'])
def liveness_check():
    """
    Liveness check - verifica que el proceso esté vivo.
    Usado por Kubernetes/Docker para restart automático.
    
    Returns:
        200: Proceso vivo
        500: Proceso con problemas
    
    Example:
        GET /api/health/live
    """
    try:
        return success_response(
            data={"status": "alive"},
            message="Service is alive"
        )
    except Exception as e:
        logger.error(f"Liveness check failed: {e}")
        return error_response(
            message="Service is not alive",
            status_code=500
        )


@health_bp.route('/ready', methods=['GET'])
def readiness_check():
    """
    Readiness check - verifica que todas las dependencias estén disponibles.
    Usado por Kubernetes/Docker para routing de tráfico.
    
    Verifica:
    - Conexión a base de datos
    - Configuración de OpenAI
    - Variables de entorno críticas
    
    Returns:
        200: Todas las dependencias disponibles
        503: Alguna dependencia no disponible
    
    Example:
        GET /api/health/ready
        
        Response:
        {
            "status": "success",
            "message": "Service is ready",
            "data": {
                "status": "ready",
                "checks": {
                    "database": {"status": "healthy", "message": "Connected"},
                    "openai": {"status": "healthy", "message": "Configured"},
                    "environment": {"status": "healthy", "message": "All variables set"}
                }
            }
        }
    """
    checks = {}
    all_healthy = True
    
    # Check 1: Database
    try:
        db_client = get_database_client()
        # Intentar una query simple para verificar conexión
        result = db_client.client.table("users").select("id").limit(1).execute()
        checks["database"] = {
            "status": "healthy",
            "message": "Database connection successful"
        }
    except Exception as e:
        all_healthy = False
        checks["database"] = {
            "status": "unhealthy",
            "message": f"Database connection failed: {str(e)}"
        }
        logger.error(f"Database health check failed: {e}")
    
    # Check 2: OpenAI Configuration
    try:
        openai_config = get_openai_config()
        if openai_config.api_key:
            checks["openai"] = {
                "status": "healthy",
                "message": "OpenAI API key configured"
            }
        else:
            all_healthy = False
            checks["openai"] = {
                "status": "unhealthy",
                "message": "OpenAI API key not configured"
            }
    except Exception as e:
        all_healthy = False
        checks["openai"] = {
            "status": "unhealthy",
            "message": f"OpenAI configuration failed: {str(e)}"
        }
        logger.error(f"OpenAI health check failed: {e}")
    
    # Check 3: Critical Environment Variables
    critical_vars = ["SUPABASE_URL", "SUPABASE_ANON_KEY", "JWT_SECRET_KEY"]
    missing_vars = [var for var in critical_vars if not os.getenv(var)]
    
    if not missing_vars:
        checks["environment"] = {
            "status": "healthy",
            "message": "All critical environment variables set"
        }
    else:
        all_healthy = False
        checks["environment"] = {
            "status": "unhealthy",
            "message": f"Missing environment variables: {', '.join(missing_vars)}"
        }
    
    # Resultado final
    if all_healthy:
        return success_response(
            data={
                "status": "ready",
                "checks": checks,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            },
            message="Service is ready"
        )
    else:
        return error_response(
            message="Service is not ready",
            status_code=503,
            error_code="SERVICE_NOT_READY",
            details={"checks": checks}
        )


@health_bp.route('/metrics', methods=['GET'])
def metrics():
    """
    Métricas del sistema - información sobre uso y performance.
    
    Returns:
        200: Métricas del sistema
    
    Example:
        GET /api/health/metrics
        
        Response:
        {
            "status": "success",
            "data": {
                "uptime_seconds": 3600,
                "python_version": "3.12.0",
                "environment": "production"
            }
        }
    """
    try:
        import sys
        import psutil
        import time
        
        # Información del proceso
        process = psutil.Process()
        
        metrics_data = {
            "system": {
                "python_version": sys.version.split()[0],
                "platform": sys.platform,
                "environment": os.getenv("ENVIRONMENT", "development")
            },
            "process": {
                "memory_mb": round(process.memory_info().rss / 1024 / 1024, 2),
                "cpu_percent": process.cpu_percent(interval=0.1),
                "threads": process.num_threads(),
                "uptime_seconds": int(time.time() - process.create_time())
            },
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        return success_response(
            data=metrics_data,
            message="Metrics retrieved successfully"
        )
        
    except ImportError:
        # psutil no instalado - retornar métricas básicas
        metrics_data = {
            "system": {
                "python_version": sys.version.split()[0],
                "environment": os.getenv("ENVIRONMENT", "development")
            },
            "note": "Install psutil for detailed metrics",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        return success_response(
            data=metrics_data,
            message="Basic metrics retrieved"
        )
        
    except Exception as e:
        logger.error(f"Metrics retrieval failed: {e}")
        return error_response(
            message="Failed to retrieve metrics",
            status_code=500,
            details=str(e)
        )


@health_bp.route('/dependencies', methods=['GET'])
def dependencies_check():
    """
    Verificación detallada de todas las dependencias externas.
    
    Returns:
        200: Estado de todas las dependencias
    
    Example:
        GET /api/health/dependencies
    """
    dependencies = {}
    
    # Database
    try:
        db_client = get_database_client()
        db_client.client.table("users").select("id").limit(1).execute()
        dependencies["database"] = {
            "status": "available",
            "type": "supabase",
            "url": os.getenv("SUPABASE_URL", "").split("//")[-1].split(".")[0] + ".supabase.co"
        }
    except Exception as e:
        dependencies["database"] = {
            "status": "unavailable",
            "error": str(e)
        }
    
    # OpenAI
    try:
        openai_config = get_openai_config()
        dependencies["openai"] = {
            "status": "configured" if openai_config.api_key else "not_configured",
            "model": openai_config.model,
            "timeout": openai_config.timeout
        }
    except Exception as e:
        dependencies["openai"] = {
            "status": "error",
            "error": str(e)
        }
    
    # Cloudinary
    cloudinary_configured = all([
        os.getenv("CLOUDINARY_CLOUD_NAME"),
        os.getenv("CLOUDINARY_API_KEY"),
        os.getenv("CLOUDINARY_API_SECRET")
    ])
    
    dependencies["cloudinary"] = {
        "status": "configured" if cloudinary_configured else "not_configured",
        "cloud_name": os.getenv("CLOUDINARY_CLOUD_NAME", "not_set")
    }
    
    # Playwright
    try:
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
        
        dependencies["playwright"] = {
            "status": "available",
            "browser": "chromium",
            "message": "Playwright chromium installed and functional"
        }
    except ImportError:
        dependencies["playwright"] = {
            "status": "not_installed",
            "message": "Playwright not installed",
            "action": "Run: pip install playwright && playwright install chromium"
        }
    except Exception as e:
        dependencies["playwright"] = {
            "status": "error",
            "message": f"Playwright installed but not functional: {str(e)}",
            "action": "Run: playwright install chromium"
        }
    
    return success_response(
        data={
            "dependencies": dependencies,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        },
        message="Dependencies status retrieved"
    )
