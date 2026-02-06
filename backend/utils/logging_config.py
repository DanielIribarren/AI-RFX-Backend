"""
📊 Logging Configuration - Logging estructurado con correlation IDs

Proporciona configuración centralizada de logging con:
- JSON logging estructurado
- Correlation IDs para tracing
- Contexto de request automático
- Niveles de log configurables

Usage:
    from backend.utils.logging_config import get_logger, log_with_context
    
    logger = get_logger(__name__)
    logger.info("Processing RFX", extra={"rfx_id": "123", "user_id": "456"})
"""
import logging
import json
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from contextvars import ContextVar
from functools import wraps
import traceback

# Context variable para correlation ID (thread-safe)
correlation_id_var: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)


class StructuredFormatter(logging.Formatter):
    """
    Formatter que produce logs en formato JSON estructurado.
    
    Formato de salida:
        {
            "timestamp": "2026-02-05T12:00:00.000Z",
            "level": "INFO",
            "logger": "backend.api.rfx",
            "message": "RFX created successfully",
            "correlation_id": "req-abc-123",
            "rfx_id": "rfx-456",
            "user_id": "user-789",
            "duration_ms": 234
        }
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Formatear log record como JSON estructurado"""
        
        # Datos base del log
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Agregar correlation ID si existe
        correlation_id = correlation_id_var.get()
        if correlation_id:
            log_data["correlation_id"] = correlation_id
        
        # Agregar campos extra del record
        if hasattr(record, 'extra_fields'):
            log_data.update(record.extra_fields)
        
        # Agregar información de excepción si existe
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info)
            }
        
        # Agregar información de ubicación en código (solo en DEBUG)
        if record.levelno == logging.DEBUG:
            log_data["location"] = {
                "file": record.pathname,
                "line": record.lineno,
                "function": record.funcName
            }
        
        return json.dumps(log_data, ensure_ascii=False)


class ContextFilter(logging.Filter):
    """
    Filter que agrega contexto automático a los logs.
    Incluye correlation_id y otros datos de contexto.
    """
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Agregar contexto al record"""
        
        # Agregar correlation ID
        correlation_id = correlation_id_var.get()
        if correlation_id:
            record.correlation_id = correlation_id
        
        # Agregar campos extra si existen
        if not hasattr(record, 'extra_fields'):
            record.extra_fields = {}
        
        return True


def setup_logging(
    level: str = "INFO",
    json_format: bool = True,
    log_file: Optional[str] = None
) -> None:
    """
    Configurar logging para toda la aplicación.
    
    Args:
        level: Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: Si True, usa JSON estructurado. Si False, formato legible.
        log_file: Path al archivo de log (opcional)
    
    Example:
        setup_logging(level="INFO", json_format=True)
    """
    
    # Obtener logger raíz
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # Limpiar handlers existentes
    root_logger.handlers.clear()
    
    # Crear handler para console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, level.upper()))
    
    # Configurar formatter
    if json_format:
        formatter = StructuredFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    console_handler.setFormatter(formatter)
    
    # Agregar context filter
    context_filter = ContextFilter()
    console_handler.addFilter(context_filter)
    
    # Agregar handler al logger
    root_logger.addHandler(console_handler)
    
    # Agregar file handler si se especifica
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(getattr(logging, level.upper()))
        file_handler.setFormatter(formatter)
        file_handler.addFilter(context_filter)
        root_logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """
    Obtener logger configurado para un módulo.
    
    Args:
        name: Nombre del logger (usualmente __name__)
    
    Returns:
        Logger configurado
    
    Example:
        logger = get_logger(__name__)
        logger.info("Processing started")
    """
    return logging.getLogger(name)


def set_correlation_id(correlation_id: Optional[str] = None) -> str:
    """
    Establecer correlation ID para el contexto actual.
    
    Args:
        correlation_id: ID de correlación (si None, genera uno nuevo)
    
    Returns:
        Correlation ID establecido
    
    Example:
        correlation_id = set_correlation_id()
        # Todos los logs subsecuentes incluirán este ID
    """
    if correlation_id is None:
        correlation_id = f"req-{uuid.uuid4().hex[:12]}"
    
    correlation_id_var.set(correlation_id)
    return correlation_id


def get_correlation_id() -> Optional[str]:
    """
    Obtener correlation ID del contexto actual.
    
    Returns:
        Correlation ID o None si no está establecido
    
    Example:
        correlation_id = get_correlation_id()
    """
    return correlation_id_var.get()


def clear_correlation_id() -> None:
    """
    Limpiar correlation ID del contexto actual.
    
    Example:
        clear_correlation_id()
    """
    correlation_id_var.set(None)


def log_with_context(logger: logging.Logger, level: str, message: str, **kwargs) -> None:
    """
    Log con contexto adicional.
    
    Args:
        logger: Logger a usar
        level: Nivel de log (info, warning, error, etc.)
        message: Mensaje a loggear
        **kwargs: Campos adicionales de contexto
    
    Example:
        log_with_context(
            logger, 
            "info", 
            "RFX created",
            rfx_id="123",
            user_id="456",
            duration_ms=234
        )
    """
    log_func = getattr(logger, level.lower())
    
    # Crear record con campos extra
    extra = {"extra_fields": kwargs}
    log_func(message, extra=extra)


def with_correlation_id(func):
    """
    Decorator para agregar correlation ID automáticamente a una función.
    
    Example:
        @with_correlation_id
        def process_rfx(rfx_id):
            logger.info("Processing RFX")  # Incluirá correlation_id automáticamente
            # ...
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Generar correlation ID si no existe
        if get_correlation_id() is None:
            set_correlation_id()
        
        try:
            return func(*args, **kwargs)
        finally:
            # Limpiar correlation ID al finalizar
            clear_correlation_id()
    
    return wrapper


def log_function_call(logger: logging.Logger):
    """
    Decorator para loggear entrada/salida de funciones automáticamente.
    
    Args:
        logger: Logger a usar
    
    Example:
        @log_function_call(logger)
        def process_rfx(rfx_id):
            # ...
            return result
        
        # Logs:
        # INFO: Calling process_rfx with args=(rfx_id='123',)
        # INFO: process_rfx completed in 234ms
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            func_name = func.__name__
            
            # Log entrada
            log_with_context(
                logger,
                "info",
                f"Calling {func_name}",
                function=func_name,
                args=str(args)[:100],  # Limitar longitud
                kwargs=str(kwargs)[:100]
            )
            
            start_time = datetime.utcnow()
            
            try:
                result = func(*args, **kwargs)
                
                # Log salida exitosa
                duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                log_with_context(
                    logger,
                    "info",
                    f"{func_name} completed",
                    function=func_name,
                    duration_ms=duration_ms,
                    status="success"
                )
                
                return result
                
            except Exception as e:
                # Log error
                duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                log_with_context(
                    logger,
                    "error",
                    f"{func_name} failed: {str(e)}",
                    function=func_name,
                    duration_ms=duration_ms,
                    status="error",
                    error_type=type(e).__name__
                )
                raise
        
        return wrapper
    return decorator


# ==================== LOGGING HELPERS ====================

def log_api_request(logger: logging.Logger, method: str, path: str, **kwargs) -> None:
    """Helper para loggear requests de API"""
    log_with_context(
        logger,
        "info",
        f"API Request: {method} {path}",
        method=method,
        path=path,
        **kwargs
    )


def log_api_response(logger: logging.Logger, status_code: int, duration_ms: int, **kwargs) -> None:
    """Helper para loggear responses de API"""
    log_with_context(
        logger,
        "info",
        f"API Response: {status_code}",
        status_code=status_code,
        duration_ms=duration_ms,
        **kwargs
    )


def log_database_query(logger: logging.Logger, operation: str, table: str, duration_ms: int, **kwargs) -> None:
    """Helper para loggear queries de base de datos"""
    log_with_context(
        logger,
        "debug",
        f"Database {operation}: {table}",
        operation=operation,
        table=table,
        duration_ms=duration_ms,
        **kwargs
    )


def log_external_api_call(logger: logging.Logger, service: str, operation: str, duration_ms: int, **kwargs) -> None:
    """Helper para loggear llamadas a APIs externas"""
    log_with_context(
        logger,
        "info",
        f"External API: {service}.{operation}",
        service=service,
        operation=operation,
        duration_ms=duration_ms,
        **kwargs
    )
