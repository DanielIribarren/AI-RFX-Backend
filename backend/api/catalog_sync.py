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
from backend.services.budy_domain_service import is_virtual_business_unit_id

logger = logging.getLogger(__name__)

catalog_bp = Blueprint('catalog', __name__, url_prefix='/api/catalog')


def _get_catalog_owner():
    """
    Determina el owner del catálogo: organization_id primero, user_id como fallback.
    Retorna (owner_field, owner_id, user_id) para usar en queries.
    """
    organization_id = get_current_user_organization_id()
    user_id = get_current_user_id()
    
    if organization_id:
        return 'organization_id', organization_id, user_id
    else:
        return 'user_id', user_id, user_id


def _apply_owner_filter(query_builder, owner_field, owner_id):
    """
    Aplica el filtro de owner al query builder de Supabase.
    Si es user_id, también filtra organization_id IS NULL.
    """
    query_builder = query_builder.eq(owner_field, owner_id)
    if owner_field == 'user_id':
        query_builder = query_builder.is_('organization_id', 'null')
    return query_builder


def _validate_business_unit_access(organization_id: str, business_unit_id: str):
    if is_virtual_business_unit_id(business_unit_id):
        raise ValueError(
            "La organización no tiene una business unit persistida. "
            "Configure el service_role de Supabase antes de importar al catálogo."
        )
    db = get_database_client()
    response = (
        db.client.table("business_units")
        .select("id")
        .eq("organization_id", organization_id)
        .eq("id", business_unit_id)
        .eq("is_active", True)
        .limit(1)
        .execute()
    )
    if not response.data:
        raise ValueError("Invalid business_unit_id for the current organization")


def _get_catalog_scope_context():
    organization_id = get_current_user_organization_id()
    user_id = get_current_user_id()
    payload = request.get_json(silent=True) or {}

    scope = str(
        request.args.get("scope")
        or request.form.get("scope")
        or payload.get("scope")
        or ("business_unit" if organization_id else "personal")
    ).strip().lower()
    business_unit_id = str(
        request.args.get("business_unit_id")
        or request.form.get("business_unit_id")
        or payload.get("business_unit_id")
        or ""
    ).strip() or None

    if organization_id:
        if scope not in {"business_unit", "shared"}:
            raise ValueError("scope must be 'business_unit' or 'shared'")
        if scope == "business_unit":
            if not business_unit_id:
                raise ValueError("business_unit_id is required when scope is 'business_unit'")
            _validate_business_unit_access(organization_id, business_unit_id)
        return {
            "organization_id": organization_id,
            "user_id": user_id,
            "scope": scope,
            "business_unit_id": business_unit_id if scope == "business_unit" else None,
        }

    return {
        "organization_id": None,
        "user_id": user_id,
        "scope": "personal",
        "business_unit_id": None,
    }


def _apply_catalog_scope_filter(query_builder, scope_context, *, include_shared: bool = False):
    organization_id = scope_context["organization_id"]
    user_id = scope_context["user_id"]
    scope = scope_context["scope"]
    business_unit_id = scope_context["business_unit_id"]

    if organization_id:
        query_builder = query_builder.eq("organization_id", organization_id)
        if scope == "shared":
            return query_builder.is_("business_unit_id", "null")
        if include_shared:
            return query_builder.or_(f"business_unit_id.eq.{business_unit_id},business_unit_id.is.null")
        return query_builder.eq("business_unit_id", business_unit_id)

    return query_builder.eq("user_id", user_id).is_("organization_id", "null")


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
        scope_context = _get_catalog_scope_context()
        
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
        openai_client = OpenAI(
            api_key=openai_config.api_key,
            max_retries=0  # Desactivar reintentos automáticos del SDK
        )
        
        # Redis es opcional
        try:
            redis_client = redis.from_url(config.redis.url, decode_responses=True)
        except Exception as e:
            logger.warning(f"⚠️ Redis not available, continuing without cache: {e}")
            redis_client = None
        
        import_service = CatalogImportService(db, openai_client, redis_client)
        
        # Importar catálogo con AI mapping
        result = import_service.import_catalog(
            file,
            organization_id=organization_id,
            user_id=user_id,
            scope=scope_context["scope"],
            business_unit_id=scope_context["business_unit_id"],
        )
        
        return jsonify(result), 200
        
    except ValueError as e:
        logger.error(f"❌ Import validation failed: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400
    except Exception as e:
        logger.error(f"❌ Import failed: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Import failed: {str(e)}'
        }), 500


@catalog_bp.route('/products', methods=['POST'])
@jwt_required
def add_product():
    """
    ➕ Agregar un producto individual al catálogo
    
    POST /api/catalog/products
    Body: {
        "product_name": "Tequeños de Queso",    (requerido)
        "product_code": "TEQ-001",               (opcional)
        "unit_cost": 15.50,                       (opcional)
        "unit_price": 22.00,                      (opcional)
        "unit": "bandeja"                         (opcional, default: "unidad")
    }
    """
    
    try:
        scope_context = _get_catalog_scope_context()
        organization_id = get_current_user_organization_id()
        user_id = get_current_user_id()
        
        data = request.get_json()
        if not data or not data.get('product_name', '').strip():
            return jsonify({
                'status': 'error',
                'message': 'product_name is required'
            }), 400
        
        db = get_database_client()
        
        product_name = data['product_name'].strip()
        product_code = data.get('product_code', '').strip() or None
        unit_cost = data.get('unit_cost')
        unit_price = data.get('unit_price')
        unit = data.get('unit', 'unidad').strip()
        
        # Validar que costos/precios sean numéricos si se proporcionan
        if unit_cost is not None:
            try:
                unit_cost = float(unit_cost)
            except (ValueError, TypeError):
                return jsonify({
                    'status': 'error',
                    'message': 'unit_cost must be a valid number'
                }), 400
        
        if unit_price is not None:
            try:
                unit_price = float(unit_price)
            except (ValueError, TypeError):
                return jsonify({
                    'status': 'error',
                    'message': 'unit_price must be a valid number'
                }), 400
        
        new_product = {
            'user_id': user_id,
            'product_name': product_name,
            'product_code': product_code,
            'unit_cost': unit_cost,
            'unit_price': unit_price,
            'unit': unit,
            'is_active': True
        }
        # Solo agregar organization_id si existe (usuarios personales no tienen)
        if organization_id:
            new_product['organization_id'] = organization_id
            new_product['user_id'] = None
            new_product['business_unit_id'] = scope_context["business_unit_id"] if scope_context["scope"] == "business_unit" else None
        
        result = db.client.table('product_catalog')\
            .insert(new_product)\
            .execute()
        
        if not result.data:
            return jsonify({
                'status': 'error',
                'message': 'Failed to create product'
            }), 500
        
        created = result.data[0]
        owner_label = organization_id or user_id
        logger.info(f"✅ Product created: {product_name} (owner: {owner_label})")
        
        return jsonify({
            'status': 'success',
            'message': f'Product "{product_name}" created successfully',
            'product': created
        }), 201
        
    except ValueError as e:
        logger.error(f"❌ Add product validation failed: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400
    except Exception as e:
        logger.error(f"❌ Add product failed: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Failed to add product: {str(e)}'
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
        
        owner_field, owner_id, user_id = _get_catalog_owner()
        scope_context = _get_catalog_scope_context()
        
        page = int(request.args.get('page', 1))
        page_size = min(int(request.args.get('page_size', 50)), 100)
        search = request.args.get('search', '').strip()
        
        offset = (page - 1) * page_size
        
        db = get_database_client()
        
        # Query con búsqueda por nombre O código
        if search:
            # Para búsqueda con texto, usar query builder con filtro de owner
            q = db.client.table('product_catalog')\
                .select('id, product_name, product_code, unit_cost, unit_price, unit, created_at, business_unit_id')
            q = _apply_catalog_scope_filter(q, scope_context, include_shared=True)
            products_response = q\
                .eq('is_active', True)\
                .or_(f'product_name.ilike.%{search}%,product_code.ilike.%{search}%')\
                .order('product_name')\
                .range(offset, offset + page_size - 1)\
                .execute()
            
            cq = db.client.table('product_catalog')\
                .select('id', count='exact')
            cq = _apply_catalog_scope_filter(cq, scope_context, include_shared=True)
            count_response = cq\
                .eq('is_active', True)\
                .or_(f'product_name.ilike.%{search}%,product_code.ilike.%{search}%')\
                .execute()
        else:
            # Sin búsqueda
            q = db.client.table('product_catalog')\
                .select('id, product_name, product_code, unit_cost, unit_price, unit, created_at, business_unit_id')
            q = _apply_catalog_scope_filter(q, scope_context, include_shared=True)
            products_response = q\
                .eq('is_active', True)\
                .order('product_name')\
                .range(offset, offset + page_size - 1)\
                .execute()
            
            cq = db.client.table('product_catalog')\
                .select('id', count='exact')
            cq = _apply_catalog_scope_filter(cq, scope_context, include_shared=True)
            count_response = cq\
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
        
    except ValueError as e:
        logger.error(f"❌ List products validation failed: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400
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
        
        scope_context = _get_catalog_scope_context()
        organization_id = scope_context["organization_id"]
        user_id = scope_context["user_id"]
        
        query = request.args.get('query', '').strip()
        
        if not query:
            return jsonify({
                'status': 'error',
                'message': 'Query parameter is required'
            }), 400
        
        # Usar servicio SYNC
        search_service = get_catalog_search_service_sync()
        result = search_service.search_product(
            query, 
            organization_id=organization_id,
            user_id=user_id if not organization_id else None,
            business_unit_id=scope_context["business_unit_id"] if scope_context["scope"] == "business_unit" else None,
        )
        
        if not result:
            return jsonify({
                'status': 'error',
                'message': f'No product found matching: {query}'
            }), 404
        
        return jsonify(result), 200
        
    except ValueError as e:
        logger.error(f"❌ Search validation failed: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400
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
        
        owner_field, owner_id, user_id = _get_catalog_owner()
        
        db = get_database_client()
        
        logger.info(f"🗑️ Attempting to delete product {product_id} ({owner_field}: {owner_id})")
        
        # Verificar que existe
        q = db.client.table('product_catalog')\
            .select('product_name')\
            .eq('id', product_id)
        q = _apply_owner_filter(q, owner_field, owner_id)
        existing = q\
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
        dq = db.client.table('product_catalog')\
            .update({'is_active': False, 'updated_at': 'now()'})\
            .eq('id', product_id)
        _apply_owner_filter(dq, owner_field, owner_id)
        dq.execute()
        
        # Invalidar cache de Redis (sync) - opcional
        try:
            redis_client = redis.from_url(config.redis.url, decode_responses=True)
            redis_client.delete(f"catalog_embeddings:{owner_field}:{owner_id}")
            logger.info(f"✅ Redis cache invalidated for {owner_field}: {owner_id}")
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
        
        owner_field, owner_id, user_id = _get_catalog_owner()
        
        data = request.get_json()
        
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'No data provided'
            }), 400
        
        db = get_database_client()
        
        # Verificar que existe
        q = db.client.table('product_catalog')\
            .select('id')\
            .eq('id', product_id)
        q = _apply_owner_filter(q, owner_field, owner_id)
        existing = q\
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
        
        uq = db.client.table('product_catalog')\
            .update(update_data)\
            .eq('id', product_id)
        _apply_owner_filter(uq, owner_field, owner_id)
        uq.execute()
        
        # Invalidar cache - opcional
        try:
            redis_client = redis.from_url(config.redis.url, decode_responses=True)
            redis_client.delete(f"catalog_embeddings:{owner_field}:{owner_id}")
        except Exception as redis_error:
            # Redis es opcional, no es crítico
            logger.info(f"ℹ️ Redis cache not available (optional): {redis_error}")
        
        # Retornar producto actualizado
        rq = db.client.table('product_catalog')\
            .select('*')\
            .eq('id', product_id)
        rq = _apply_owner_filter(rq, owner_field, owner_id)
        updated = rq\
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
        
        scope_context = _get_catalog_scope_context()
        organization_id = scope_context["organization_id"]
        user_id = scope_context["user_id"]

        db = get_database_client()

        logger.warning(f"⚠️ CLEARING ENTIRE CATALOG for scope={scope_context['scope']} org={organization_id} user={user_id}")
        
        # Contar productos activos antes de eliminar
        cq = db.client.table('product_catalog')\
            .select('id', count='exact')
        cq = _apply_catalog_scope_filter(cq, scope_context, include_shared=False)
        count_result = cq\
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
        dq = db.client.table('product_catalog')\
            .update({'is_active': False, 'updated_at': 'now()'})
        dq = _apply_catalog_scope_filter(dq, scope_context, include_shared=False)
        dq.eq('is_active', True).execute()
        
        # Invalidar cache de Redis - opcional
        try:
            redis_client = redis.from_url(config.redis.url, decode_responses=True)
            if organization_id:
                redis_client.delete(f"catalog_embeddings:org:{organization_id}")
            else:
                redis_client.delete(f"catalog_embeddings:user:{user_id}")
            logger.info("✅ Redis cache invalidated for catalog owner")
        except Exception as redis_error:
            # Redis es opcional, no es crítico
            logger.info(f"ℹ️ Redis cache not available (optional): {redis_error}")
        
        logger.warning(f"✅ CLEARED {products_count} products from catalog scope={scope_context['scope']}")
        
        return jsonify({
            'status': 'success',
            'message': f'Catalog cleared successfully. {products_count} products deleted.',
            'products_deleted': products_count,
            'deleted_count': products_count,
        }), 200
        
    except ValueError as e:
        logger.error(f"❌ Clear catalog validation failed: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400
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
        
        scope_context = _get_catalog_scope_context()
        organization_id = scope_context["organization_id"]
        user_id = scope_context["user_id"]
        
        # Usar servicio SYNC
        search_service = get_catalog_search_service_sync()
        stats = search_service.get_catalog_stats(
            organization_id=organization_id,
            user_id=user_id if not organization_id else None,
            business_unit_id=scope_context["business_unit_id"] if scope_context["scope"] == "business_unit" else None,
        )
        
        return jsonify(stats), 200
        
    except ValueError as e:
        logger.error(f"❌ Get stats validation failed: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400
    except Exception as e:
        logger.error(f"❌ Get stats failed: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


logger.info("🛒 Catalog API (SYNC) initialized")
