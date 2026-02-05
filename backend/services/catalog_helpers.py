"""
Catalog Service Helpers
Funciones auxiliares para inicializar servicios de catálogo
"""
import redis
from openai import OpenAI
from backend.core.config import config
from backend.core.database import get_database_client
from backend.services.catalog_search_service_sync import CatalogSearchServiceSync


def get_catalog_search_service_sync() -> CatalogSearchServiceSync:
    """
    Inicializa CatalogSearchServiceSync con clientes sync
    Para uso en código sincrónico como RFX Processor
    
    Returns:
        CatalogSearchServiceSync instance
    """
    
    # Database client (ya es sync)
    db = get_database_client()
    
    # Redis SYNC client (no async)
    redis_client = redis.from_url(
        config.redis.url,
        decode_responses=True  # Para obtener strings en lugar de bytes
    )
    
    # OpenAI SYNC client
    openai_client = OpenAI(api_key=config.openai.api_key)
    
    return CatalogSearchServiceSync(db, redis_client, openai_client)


def get_catalog_search_service_for_rfx() -> CatalogSearchServiceSync:
    """
    Alias específico para RFX Processor
    Deja claro que es la versión sync
    
    Returns:
        CatalogSearchServiceSync instance
    """
    return get_catalog_search_service_sync()
