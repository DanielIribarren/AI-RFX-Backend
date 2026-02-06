"""
Catalog API Router - SYNC VERSION
Compatible con Flask (sin async/await)

Endpoints:
- POST /api/catalog/import - Importar catálogo desde Excel/CSV
- GET /api/catalog/products - Listar productos con paginación
- GET /api/catalog/search - Buscar producto específico
- DELETE /api/catalog/products/{product_id} - Eliminar producto
- PUT /api/catalog/products/{product_id} - Actualizar producto
- GET /api/catalog/stats - Estadísticas del catálogo
"""

from flask import Blueprint, request, jsonify
import logging
from backend.utils.auth_middleware import jwt_required, get_current_user_id, get_current_user_organization_id
from backend.core.database import get_database_client

logger = logging.getLogger(__name__)

catalog_bp = Blueprint('catalog', __name__, url_prefix='/api/catalog')


@catalog_bp.route('/import', methods=['POST'])
@jwt_required
def import_catalog():
    """
    📥 Importar catálogo desde Excel/CSV
    
    POST /api/catalog/import
    """
    
    try:
        user_id = get_current_user_id()
        organization_id = get_current_user_organization_id()
        
        if 'file' not in request.files:
            return jsonify({
                'status': 'error',
                'message': 'No file provided'
            }), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({
                'status': 'error',
                'message': 'Empty filename'
            }), 400
        
        # Validar extensión
        allowed_extensions = {'.xlsx', '.xls', '.csv'}
        if not any(file.filename.lower().endswith(ext) for ext in allowed_extensions):
            return jsonify({
                'status': 'error',
                'message': f'Invalid file type. Allowed: {", ".join(allowed_extensions)}'
            }), 400
        
        # Importar servicio AI-First
        from backend.services.catalog_import_service import CatalogImportService
        from openai import OpenAI
        from backend.core.config import config, get_openai_config
        import redis
        
        # Inicializar servicio AI-First
        db = get_database_client()
        openai_config = get_openai_config()
        openai_client = OpenAI(api_key=openai_config.api_key)
        
        # Redis es opcional
        try:
            redis_client = redis.from_url(config.redis.url, decode_responses=True)
        except Exception as e:
            logger.warning(f"⚠️ Redis not available, continuing without cache: {e}")
            redis_client = None
        
        import_service = CatalogImportService(db, openai_client, redis_client)
        
        # Importar catálogo con AI mapping
        result = import_service.import_catalog(file, organization_id, user_id)
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"❌ Import failed: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Import failed: {str(e)}'
        }), 500


@catalog_bp.route('/products', methods=['GET'])
@jwt_required
def list_products():
    """
    📋 Listar productos del catálogo con paginación
    
    GET /api/catalog/products?page=1&page_size=50&search=tequeños
    """
    
    try:
        from backend.core.database import get_database_client
        
        organization_id = get_current_user_organization_id()
        
        page = int(request.args.get('page', 1))
        page_size = min(int(request.args.get('page_size', 50)), 100)
        search = request.args.get('search', '').strip()
        
        offset = (page - 1) * page_size
        
        db = get_database_client()
        
        # Query con búsqueda por nombre O código
        if search:
            query = """
                SELECT id, product_name, product_code, unit_cost, unit_price, unit, created_at
                FROM product_catalog
                WHERE organization_id = %s AND is_active = true
                  AND (product_name ILIKE %s OR product_code ILIKE %s)
                ORDER BY product_name
                LIMIT %s OFFSET %s
            """
            products_response = db.client.rpc('exec_sql', {
                'query': query,
                'params': [organization_id, f'%{search}%', f'%{search}%', page_size, offset]
            }).execute()
            
            count_query = """
                SELECT COUNT(*) as count
                FROM product_catalog
                WHERE organization_id = %s AND is_active = true
                  AND (product_name ILIKE %s OR product_code ILIKE %s)
            """
            count_response = db.client.rpc('exec_sql', {
                'query': count_query,
                'params': [organization_id, f'%{search}%', f'%{search}%']
            }).execute()
        else:
            # Sin búsqueda
            products_response = db.client.table('product_catalog')\
                .select('id, product_name, product_code, unit_cost, unit_price, unit, created_at')\
                .eq('organization_id', organization_id)\
                .eq('is_active', True)\
                .order('product_name')\
                .range(offset, offset + page_size - 1)\
                .execute()
            
            count_response = db.client.table('product_catalog')\
                .select('id', count='exact')\
                .eq('organization_id', organization_id)\
                .eq('is_active', True)\
                .execute()
        
        products = products_response.data
        total = count_response.count if hasattr(count_response, 'count') else len(products)
        
        return jsonify({
            'products': products,
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': (total + page_size - 1) // page_size
        }), 200
        
    except Exception as e:
        logger.error(f"❌ List products failed: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@catalog_bp.route('/search', methods=['GET'])
@jwt_required
def search_product():
    """
    🔍 Buscar un producto en el catálogo (semantic search)
    
    GET /api/catalog/search?query=tequeños
    """
    
    try:
        from backend.services.catalog_helpers import get_catalog_search_service_sync
        
        organization_id = get_current_user_organization_id()
        query = request.args.get('query', '').strip()
        
        if not query:
            return jsonify({
                'status': 'error',
                'message': 'Query parameter is required'
            }), 400
        
        # Usar servicio SYNC
        search_service = get_catalog_search_service_sync()
        result = search_service.search_product(query, organization_id)
        
        if not result:
            return jsonify({
                'status': 'error',
                'message': f'No product found matching: {query}'
            }), 404
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"❌ Search failed: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@catalog_bp.route('/products/<product_id>', methods=['DELETE'])
@jwt_required
def delete_product(product_id: str):
    """
    🗑️ Eliminar un producto (soft delete)
    
    DELETE /api/catalog/products/{product_id}
    
    Response:
        200: Product deleted successfully
        404: Product not found
        500: Server error
    """
    
    try:
        from backend.core.database import get_database_client
        import redis
        from backend.core.config import config
        
        organization_id = get_current_user_organization_id()
        db = get_database_client()
        
        logger.info(f"🗑️ Attempting to delete product {product_id} for org {organization_id}")
        
        # Verificar que existe
        existing = db.client.table('product_catalog')\
            .select('product_name')\
            .eq('id', product_id)\
            .eq('organization_id', organization_id)\
            .eq('is_active', True)\
            .limit(1)\
            .execute()
        
        if not existing.data:
            logger.warning(f"⚠️ Product {product_id} not found or already deleted")
            return jsonify({
                'status': 'error',
                'message': 'Product not found or already deleted'
            }), 404
        
        product_name = existing.data[0]['product_name']
        
        # Soft delete
        result = db.client.table('product_catalog')\
            .update({'is_active': False, 'updated_at': 'now()'})\
            .eq('id', product_id)\
            .eq('organization_id', organization_id)\
            .execute()
        
        # Invalidar cache de Redis (sync) - opcional
        try:
            redis_client = redis.from_url(config.redis.url, decode_responses=True)
            redis_client.delete(f"catalog_embeddings:{organization_id}")
            logger.info(f"✅ Redis cache invalidated for org {organization_id}")
        except Exception as redis_error:
            # Redis es opcional, no es crítico
            logger.info(f"ℹ️ Redis cache not available (optional): {redis_error}")
        
        logger.info(f"✅ Deleted product {product_id}: {product_name}")
        
        return jsonify({
            'status': 'success',
            'message': f'Product "{product_name}" deleted successfully',
            'product_id': product_id
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Delete failed for product {product_id}: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Failed to delete product: {str(e)}'
        }), 500


@catalog_bp.route('/products/<product_id>', methods=['PUT'])
@jwt_required
def update_product(product_id: str):
    """
    ✏️ Actualizar un producto
    
    PUT /api/catalog/products/{product_id}
    """
    
    try:
        from backend.core.database import get_database_client
        import redis
        from backend.core.config import config
        
        organization_id = get_current_user_organization_id()
        data = request.get_json()
        
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'No data provided'
            }), 400
        
        db = get_database_client()
        
        # Verificar que existe
        existing = db.client.table('product_catalog')\
            .select('id')\
            .eq('id', product_id)\
            .eq('organization_id', organization_id)\
            .eq('is_active', True)\
            .limit(1)\
            .execute()
        
        if not existing.data:
            return jsonify({
                'status': 'error',
                'message': 'Product not found'
            }), 404
        
        # Actualizar
        update_data = {}
        if 'product_name' in data:
            update_data['product_name'] = data['product_name']
        if 'product_code' in data:
            update_data['product_code'] = data['product_code']
        if 'unit_cost' in data:
            update_data['unit_cost'] = data['unit_cost']
        if 'unit_price' in data:
            update_data['unit_price'] = data['unit_price']
        if 'unit' in data:
            update_data['unit'] = data['unit']
        
        if not update_data:
            return jsonify({
                'status': 'error',
                'message': 'No valid fields to update'
            }), 400
        
        db.client.table('product_catalog')\
            .update(update_data)\
            .eq('id', product_id)\
            .eq('organization_id', organization_id)\
            .execute()
        
        # Invalidar cache - opcional
        try:
            redis_client = redis.from_url(config.redis.url, decode_responses=True)
            redis_client.delete(f"catalog_embeddings:{organization_id}")
        except Exception as redis_error:
            # Redis es opcional, no es crítico
            logger.info(f"ℹ️ Redis cache not available (optional): {redis_error}")
        
        # Retornar producto actualizado
        updated = db.client.table('product_catalog')\
            .select('*')\
            .eq('id', product_id)\
            .eq('organization_id', organization_id)\
            .limit(1)\
            .execute()
        
        return jsonify({
            'status': 'success',
            'product': updated.data[0] if updated.data else None
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Update failed: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@catalog_bp.route('/clear', methods=['DELETE'])
@jwt_required
def clear_catalog():
    """
    🗑️💥 Eliminar TODOS los productos del catálogo (soft delete)
    
    DELETE /api/catalog/clear
    
    ADVERTENCIA: Esta operación marca todos los productos como inactivos.
    No se puede deshacer fácilmente.
    
    Response:
        200: Catalog cleared successfully
        500: Server error
    """
    
    try:
        from backend.core.database import get_database_client
        import redis
        from backend.core.config import config
        
        organization_id = get_current_user_organization_id()
        db = get_database_client()
        
        logger.warning(f"⚠️ CLEARING ENTIRE CATALOG for org {organization_id}")
        
        # Contar productos activos antes de eliminar
        count_result = db.client.table('product_catalog')\
            .select('id', count='exact')\
            .eq('organization_id', organization_id)\
            .eq('is_active', True)\
            .execute()
        
        products_count = count_result.count if hasattr(count_result, 'count') else len(count_result.data)
        
        if products_count == 0:
            return jsonify({
                'status': 'success',
                'message': 'Catalog is already empty',
                'products_deleted': 0
            }), 200
        
        # Soft delete de TODOS los productos
        result = db.client.table('product_catalog')\
            .update({'is_active': False, 'updated_at': 'now()'})\
            .eq('organization_id', organization_id)\
            .eq('is_active', True)\
            .execute()
        
        # Invalidar cache de Redis - opcional
        try:
            redis_client = redis.from_url(config.redis.url, decode_responses=True)
            redis_client.delete(f"catalog_embeddings:{organization_id}")
            logger.info(f"✅ Redis cache invalidated for org {organization_id}")
        except Exception as redis_error:
            # Redis es opcional, no es crítico
            logger.info(f"ℹ️ Redis cache not available (optional): {redis_error}")
        
        logger.warning(f"✅ CLEARED {products_count} products from catalog (org: {organization_id})")
        
        return jsonify({
            'status': 'success',
            'message': f'Catalog cleared successfully. {products_count} products deleted.',
            'products_deleted': products_count
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Clear catalog failed: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Failed to clear catalog: {str(e)}'
        }), 500


@catalog_bp.route('/stats', methods=['GET'])
@jwt_required
def get_stats():
    """
    📊 Estadísticas del catálogo
    
    GET /api/catalog/stats
    """
    
    try:
        from backend.services.catalog_helpers import get_catalog_search_service_sync
        
        organization_id = get_current_user_organization_id()
        
        # Usar servicio SYNC
        search_service = get_catalog_search_service_sync()
        stats = search_service.get_catalog_stats(organization_id)
        
        return jsonify(stats), 200
        
    except Exception as e:
        logger.error(f"❌ Get stats failed: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


logger.info("🛒 Catalog API (SYNC) initialized")
