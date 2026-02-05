"""
Script de testing para Product Catalog System
Tests: Importación, Exact Match, Fuzzy Match, Semantic Search
"""
import asyncio
import sys
import os
from pathlib import Path

# Agregar backend al path
sys.path.insert(0, str(Path(__file__).parent))

from backend.core.config import config
from backend.core.database import get_database_client
from backend.services.catalog_import_service import CatalogImportService
from backend.services.catalog_search_service import CatalogSearchService
from openai import AsyncOpenAI
import redis.asyncio as redis


async def main():
    print("=" * 80)
    print("🧪 TESTING PRODUCT CATALOG SYSTEM")
    print("=" * 80)
    
    # Inicializar servicios
    print("\n📦 Inicializando servicios...")
    db = get_database_client()
    redis_client = redis.from_url(config.redis.url)
    openai_client = AsyncOpenAI(api_key=config.openai.api_key)
    
    import_service = CatalogImportService(db, redis_client, openai_client)
    search_service = CatalogSearchService(db, redis_client, openai_client)
    
    print("✅ Servicios inicializados")
    
    # Obtener organization_id de prueba
    print("\n🔍 Buscando organización de prueba...")
    orgs_response = db.client.table("organizations").select("id, name").limit(1).execute()
    
    if not orgs_response.data:
        print("❌ No hay organizaciones en la BD. Crea una primero.")
        return
    
    org_id = orgs_response.data[0]['id']
    org_name = orgs_response.data[0]['name']
    print(f"✅ Usando organización: {org_name} ({org_id})")
    
    # TEST 1: Importar catálogo
    print("\n" + "=" * 80)
    print("TEST 1: IMPORTAR CATÁLOGO DE EJEMPLO")
    print("=" * 80)
    
    catalog_file = Path(__file__).parent / "examples" / "catalog_example.csv"
    
    if not catalog_file.exists():
        print(f"❌ Archivo no encontrado: {catalog_file}")
        return
    
    print(f"📁 Archivo: {catalog_file}")
    
    with open(catalog_file, 'rb') as f:
        file_content = f.read()
    
    print("⏳ Importando productos...")
    result = await import_service.import_catalog(
        file_content=file_content,
        filename="catalog_example.csv",
        organization_id=org_id
    )
    
    print(f"\n✅ IMPORTACIÓN COMPLETADA:")
    print(f"   - Productos importados: {result['products_imported']}")
    print(f"   - Productos actualizados: {result['products_updated']}")
    print(f"   - Productos omitidos: {result['products_skipped']}")
    print(f"   - Errores: {len(result['errors'])}")
    print(f"   - Duración: {result['duration_seconds']:.2f}s")
    
    if result['errors']:
        print("\n⚠️ Errores encontrados:")
        for error in result['errors']:
            print(f"   - {error}")
    
    # TEST 2: Verificar productos en BD
    print("\n" + "=" * 80)
    print("TEST 2: VERIFICAR PRODUCTOS EN BASE DE DATOS")
    print("=" * 80)
    
    products_response = db.client.table("product_catalog")\
        .select("id, product_name, unit_cost, unit_price, unit")\
        .eq("organization_id", org_id)\
        .eq("is_active", True)\
        .limit(5)\
        .execute()
    
    print(f"\n✅ Productos en BD: {len(products_response.data)}")
    print("\nPrimeros 5 productos:")
    for p in products_response.data:
        print(f"   - {p['product_name']}: ${p['unit_price']} ({p['unit']})")
    
    # TEST 3: Verificar embeddings en Redis
    print("\n" + "=" * 80)
    print("TEST 3: VERIFICAR EMBEDDINGS EN REDIS")
    print("=" * 80)
    
    cache_key = f"catalog_embeddings:{org_id}"
    cached = await redis_client.get(cache_key)
    
    if cached:
        import json
        cache_data = json.loads(cached)
        print(f"✅ Cache encontrado en Redis")
        print(f"   - Productos cacheados: {len(cache_data['products'])}")
        print(f"   - Generado: {cache_data['generated_at']}")
        
        # Verificar un embedding
        first_product = list(cache_data['products'].values())[0]
        print(f"   - Dimensión embedding: {len(first_product['embedding'])}")
    else:
        print("⚠️ No hay embeddings en Redis (semantic search no disponible)")
    
    # TEST 4: Exact Match
    print("\n" + "=" * 80)
    print("TEST 4: EXACT MATCH")
    print("=" * 80)
    
    test_queries_exact = [
        "Tequeños de queso",
        "Empanadas de carne",
        "Canapés variados"
    ]
    
    for query in test_queries_exact:
        print(f"\n🔍 Buscando: '{query}'")
        result = await search_service.search_product(query, org_id)
        
        if result:
            print(f"✅ MATCH ENCONTRADO:")
            print(f"   - Producto: {result['product_name']}")
            print(f"   - Tipo: {result['match_type']}")
            print(f"   - Confidence: {result['confidence']:.2f}")
            print(f"   - Precio: ${result['unit_price']}")
        else:
            print(f"❌ No match")
    
    # TEST 5: Fuzzy Match
    print("\n" + "=" * 80)
    print("TEST 5: FUZZY MATCH (con typos)")
    print("=" * 80)
    
    test_queries_fuzzy = [
        "tequenos",  # sin tilde
        "empanada de carne",  # singular
        "canapes",  # sin tilde
        "teqeños"  # typo
    ]
    
    for query in test_queries_fuzzy:
        print(f"\n🔍 Buscando: '{query}'")
        result = await search_service.search_product(query, org_id)
        
        if result:
            print(f"✅ MATCH ENCONTRADO:")
            print(f"   - Producto: {result['product_name']}")
            print(f"   - Tipo: {result['match_type']}")
            print(f"   - Confidence: {result['confidence']:.2f}")
            print(f"   - Precio: ${result['unit_price']}")
        else:
            print(f"❌ No match")
    
    # TEST 6: Semantic Search
    print("\n" + "=" * 80)
    print("TEST 6: SEMANTIC SEARCH (sinónimos)")
    print("=" * 80)
    
    test_queries_semantic = [
        "pasapalos de queso",  # sinónimo de tequeños
        "hamburguesas pequeñas",  # sinónimo de mini hamburguesas
        "comida fría",  # categoría
        "bebida alcohólica"  # categoría
    ]
    
    for query in test_queries_semantic:
        print(f"\n🔍 Buscando: '{query}'")
        result = await search_service.search_product(query, org_id)
        
        if result:
            print(f"✅ MATCH ENCONTRADO:")
            print(f"   - Producto: {result['product_name']}")
            print(f"   - Tipo: {result['match_type']}")
            print(f"   - Confidence: {result['confidence']:.2f}")
            print(f"   - Precio: ${result['unit_price']}")
        else:
            print(f"❌ No match")
    
    # TEST 7: Estadísticas
    print("\n" + "=" * 80)
    print("TEST 7: ESTADÍSTICAS DEL CATÁLOGO")
    print("=" * 80)
    
    stats = await search_service.get_catalog_stats(org_id)
    
    print(f"\n📊 Estadísticas:")
    print(f"   - Total productos: {stats['total_products']}")
    print(f"   - Con costo: {stats['products_with_cost']}")
    print(f"   - Con precio: {stats['products_with_price']}")
    print(f"   - Precio promedio: ${stats['avg_price']:.2f}")
    print(f"   - Cache Redis: {stats['cache_status']}")
    print(f"   - Semantic search: {'✅' if stats['semantic_search_available'] else '❌'}")
    
    # Cerrar conexiones
    await redis_client.close()
    
    print("\n" + "=" * 80)
    print("✅ TESTING COMPLETADO")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
