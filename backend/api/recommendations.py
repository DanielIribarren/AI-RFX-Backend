"""
API endpoints para el sistema de recomendaciones y aprendizaje de IA.

KISS: Endpoints simples que delegan todo a los servicios.
Sin lógica de negocio en los endpoints.
"""

from flask import Blueprint, request, jsonify
import logging

from backend.services.learning_service import learning_service
from backend.utils.auth_middleware import jwt_required, get_current_user, get_current_user_organization_id

logger = logging.getLogger(__name__)

# Crear blueprint
recommendations_bp = Blueprint('recommendations', __name__, url_prefix='/api/recommendations')


@recommendations_bp.route('/pricing-preference', methods=['GET'])
@jwt_required
def get_pricing_preference():
    """
    Obtiene la configuración de pricing más usada por el usuario.
    
    Returns:
        {
            'status': 'success',
            'data': {
                'coordination_enabled': bool,
                'coordination_rate': float,
                'taxes_enabled': bool,
                'tax_rate': float,
                'cost_per_person_enabled': bool
            }
        }
    """
    try:
        current_user = get_current_user()
        user_id = current_user.get('id') or current_user.get('sub')
        
        preference = learning_service.get_pricing_preference(user_id)
        
        if preference:
            logger.info(f"✅ Pricing preference found for user {user_id}")
            return jsonify({
                'status': 'success',
                'data': preference
            }), 200
        else:
            logger.info(f"📭 No pricing preference for user {user_id}")
            return jsonify({
                'status': 'success',
                'data': None,
                'message': 'No pricing preferences found'
            }), 200
            
    except Exception as e:
        logger.error(f"❌ Error getting pricing preference: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Error al obtener preferencias de pricing'
        }), 500


@recommendations_bp.route('/frequent-products', methods=['GET'])
@jwt_required
def get_frequent_products():
    """
    Obtiene productos más usados por el usuario.
    
    Query params:
        - limit: int (default: 10)
    
    Returns:
        {
            'status': 'success',
            'data': [
                {'product_name': str, 'usage_count': int, 'details': dict},
                ...
            ]
        }
    """
    try:
        current_user = get_current_user()
        user_id = current_user.get('id') or current_user.get('sub')
        
        limit = request.args.get('limit', 10, type=int)
        
        products = learning_service.get_frequent_products(user_id, limit)
        
        logger.info(f"✅ Found {len(products)} frequent products for user {user_id}")
        return jsonify({
            'status': 'success',
            'data': products,
            'count': len(products)
        }), 200
            
    except Exception as e:
        logger.error(f"❌ Error getting frequent products: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Error al obtener productos frecuentes'
        }), 500


@recommendations_bp.route('/learned-price', methods=['GET'])
@jwt_required
def get_learned_price():
    """
    Obtiene precio aprendido para un producto.
    
    Query params:
        - product_name: str (required)
        - quantity: int (optional)
    
    Returns:
        {
            'status': 'success',
            'data': {
                'product_name': str,
                'learned_price': float or null
            }
        }
    """
    try:
        current_user = get_current_user()
        user_id = current_user.get('id') or current_user.get('sub')
        
        product_name = request.args.get('product_name')
        if not product_name:
            return jsonify({
                'status': 'error',
                'message': 'product_name es requerido'
            }), 400
        
        quantity = request.args.get('quantity', type=int)
        
        learned_price = learning_service.get_learned_price(user_id, product_name, quantity)
        
        if learned_price:
            logger.info(f"✅ Learned price found for {product_name}: ${learned_price}")
        else:
            logger.info(f"📭 No learned price for {product_name}")
        
        return jsonify({
            'status': 'success',
            'data': {
                'product_name': product_name,
                'learned_price': learned_price
            }
        }), 200
            
    except Exception as e:
        logger.error(f"❌ Error getting learned price: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Error al obtener precio aprendido'
        }), 500


@recommendations_bp.route('/related-products', methods=['GET'])
@jwt_required
def get_related_products():
    """
    Obtiene productos relacionados que frecuentemente van juntos.
    
    Query params:
        - product_name: str (required)
        - min_confidence: float (default: 0.3)
        - limit: int (default: 5)
    
    Returns:
        {
            'status': 'success',
            'data': ['Producto B', 'Producto C', ...]
        }
    """
    try:
        organization_id = get_current_user_organization_id()
        
        product_name = request.args.get('product_name')
        if not product_name:
            return jsonify({
                'status': 'error',
                'message': 'product_name es requerido'
            }), 400
        
        min_confidence = request.args.get('min_confidence', 0.3, type=float)
        limit = request.args.get('limit', 5, type=int)
        
        related = learning_service.get_related_products(
            organization_id, 
            product_name, 
            min_confidence, 
            limit
        )
        
        logger.info(f"✅ Found {len(related)} related products for {product_name}")
        return jsonify({
            'status': 'success',
            'data': related,
            'count': len(related)
        }), 200
            
    except Exception as e:
        logger.error(f"❌ Error getting related products: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Error al obtener productos relacionados'
        }), 500


@recommendations_bp.route('/save-pricing-preference', methods=['POST'])
@jwt_required
def save_pricing_preference():
    """
    Guarda configuración de pricing como preferencia del usuario.
    
    Body:
        {
            'coordination_enabled': bool,
            'coordination_rate': float,
            'taxes_enabled': bool,
            'tax_rate': float,
            'cost_per_person_enabled': bool
        }
    """
    try:
        current_user = get_current_user()
        user_id = current_user.get('id') or current_user.get('sub')
        organization_id = get_current_user_organization_id()
        
        pricing_config = request.get_json()
        if not pricing_config:
            return jsonify({
                'status': 'error',
                'message': 'Configuración de pricing requerida'
            }), 400
        
        success = learning_service.save_pricing_preference(
            user_id, 
            organization_id,
            pricing_config
        )
        
        if success:
            logger.info(f"✅ Pricing preference saved for user {user_id}")
            return jsonify({
                'status': 'success',
                'message': 'Preferencia guardada exitosamente'
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': 'Error al guardar preferencia'
            }), 500
            
    except Exception as e:
        logger.error(f"❌ Error saving pricing preference: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Error al guardar preferencia de pricing'
        }), 500


@recommendations_bp.route('/record-price-correction', methods=['POST'])
@jwt_required
def record_price_correction():
    """
    Registra una corrección de precio para aprendizaje.
    
    Body:
        {
            'product_name': str,
            'original_price': float,
            'corrected_price': float,
            'rfx_id': str (optional),
            'quantity': int (optional),
            'context': dict (optional)
        }
    """
    try:
        current_user = get_current_user()
        user_id = current_user.get('id') or current_user.get('sub')
        organization_id = get_current_user_organization_id()
        
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'Datos requeridos'
            }), 400
        
        required_fields = ['product_name', 'original_price', 'corrected_price']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'status': 'error',
                    'message': f'{field} es requerido'
                }), 400
        
        success = learning_service.record_price_correction(
            user_id=user_id,
            organization_id=organization_id,
            product_name=data['product_name'],
            original_price=data['original_price'],
            corrected_price=data['corrected_price'],
            rfx_id=data.get('rfx_id'),
            quantity=data.get('quantity'),
            context=data.get('context')
        )
        
        if success:
            logger.info(f"✅ Price correction recorded: {data['product_name']}")
            return jsonify({
                'status': 'success',
                'message': 'Corrección registrada exitosamente'
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': 'Error al registrar corrección'
            }), 500
            
    except Exception as e:
        logger.error(f"❌ Error recording price correction: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Error al registrar corrección de precio'
        }), 500


# Exportar blueprint
__all__ = ['recommendations_bp']
