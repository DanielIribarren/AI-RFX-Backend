"""
🔄 Retry Decorator - Unified retry logic for external services

Provides robust retry mechanisms with exponential backoff for:
- API calls (OpenAI, Cloudinary, etc.)
- Network operations
- Temporary failures

Usage:
    @retry_on_failure(max_retries=3, initial_delay=0.5)
    def call_external_api():
        return api.call()
"""
import time
import logging
from functools import wraps
from typing import Callable, Type, Tuple, Optional

logger = logging.getLogger(__name__)


def retry_on_failure(
    max_retries: int = 3,
    initial_delay: float = 0.5,
    backoff_factor: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable] = None
):
    """
    Decorator para reintentar operaciones que pueden fallar temporalmente.
    
    Args:
        max_retries: Número máximo de reintentos (default: 3)
        initial_delay: Delay inicial en segundos (default: 0.5s)
        backoff_factor: Factor de multiplicación para exponential backoff (default: 2.0)
        exceptions: Tupla de excepciones que activan retry (default: todas)
        on_retry: Callback opcional que se ejecuta antes de cada retry
    
    Ejemplo:
        @retry_on_failure(max_retries=3, initial_delay=0.5)
        def upload_to_cloudinary(file):
            return cloudinary.uploader.upload(file)
        
        @retry_on_failure(
            max_retries=5,
            exceptions=(openai.RateLimitError, openai.APIError)
        )
        def call_openai_api(prompt):
            return openai.ChatCompletion.create(...)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_retries + 1):  # +1 porque el primer intento no es retry
                try:
                    if attempt > 0:
                        logger.info(
                            f"🔄 Retry {attempt}/{max_retries} for {func.__name__} "
                            f"after {delay:.2f}s delay"
                        )
                        time.sleep(delay)
                        
                        # Ejecutar callback si existe
                        if on_retry:
                            on_retry(attempt, last_exception)
                    
                    # Intentar ejecutar la función
                    result = func(*args, **kwargs)
                    
                    if attempt > 0:
                        logger.info(f"✅ {func.__name__} succeeded after {attempt} retries")
                    
                    return result
                    
                except exceptions as e:
                    last_exception = e
                    
                    # Si es el último intento, lanzar la excepción
                    if attempt == max_retries:
                        logger.error(
                            f"❌ {func.__name__} failed after {max_retries} retries: {str(e)}"
                        )
                        raise
                    
                    # Logging del error
                    logger.warning(
                        f"⚠️ {func.__name__} attempt {attempt + 1} failed: {str(e)}"
                    )
                    
                    # Calcular próximo delay con exponential backoff
                    delay *= backoff_factor
            
            # Fallback (no debería llegar aquí)
            raise last_exception
        
        return wrapper
    return decorator


def retry_on_rate_limit(max_retries: int = 5, initial_delay: float = 1.0):
    """
    Decorator especializado para rate limits de APIs.
    Usa delays más largos y más reintentos.
    
    Args:
        max_retries: Número máximo de reintentos (default: 5)
        initial_delay: Delay inicial en segundos (default: 1.0s)
    
    Ejemplo:
        @retry_on_rate_limit(max_retries=5)
        def call_openai_with_rate_limit():
            return openai.ChatCompletion.create(...)
    """
    return retry_on_failure(
        max_retries=max_retries,
        initial_delay=initial_delay,
        backoff_factor=2.0,
        exceptions=(Exception,)  # Captura todas las excepciones por defecto
    )


def retry_on_network_error(max_retries: int = 3, initial_delay: float = 0.3):
    """
    Decorator especializado para errores de red.
    Usa delays cortos para reconexión rápida.
    
    Args:
        max_retries: Número máximo de reintentos (default: 3)
        initial_delay: Delay inicial en segundos (default: 0.3s)
    
    Ejemplo:
        @retry_on_network_error()
        def fetch_from_api():
            return requests.get(url)
    """
    return retry_on_failure(
        max_retries=max_retries,
        initial_delay=initial_delay,
        backoff_factor=2.0,
        exceptions=(Exception,)
    )


class RetryableOperation:
    """
    Context manager para operaciones que requieren retry.
    Útil cuando no puedes usar decoradores.
    
    Ejemplo:
        with RetryableOperation(max_retries=3) as retry:
            result = retry.execute(lambda: external_api_call())
    """
    
    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 0.5,
        backoff_factor: float = 2.0
    ):
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.backoff_factor = backoff_factor
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        return False
    
    def execute(self, func: Callable, *args, **kwargs):
        """Ejecutar función con retry logic"""
        delay = self.initial_delay
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                if attempt > 0:
                    logger.info(f"🔄 Retry {attempt}/{self.max_retries} after {delay:.2f}s")
                    time.sleep(delay)
                
                return func(*args, **kwargs)
                
            except Exception as e:
                last_exception = e
                
                if attempt == self.max_retries:
                    logger.error(f"❌ Operation failed after {self.max_retries} retries: {str(e)}")
                    raise
                
                logger.warning(f"⚠️ Attempt {attempt + 1} failed: {str(e)}")
                delay *= self.backoff_factor
        
        raise last_exception
