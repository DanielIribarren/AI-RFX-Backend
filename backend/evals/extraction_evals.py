"""
Evaluadores específicos para la extracción de datos RFX.
Enfocados en validar calidad de productos extraídos.
"""
from typing import Dict, Any, List, Optional
from backend.evals.base_evaluator import BaseEvaluator, EvaluationResult
from backend.core.feature_flags import FeatureFlags

class ProductCountEvaluator(BaseEvaluator):
    """Evalúa si la cantidad de productos extraídos es razonable"""
    
    def __init__(self, min_products: int = 1, max_products: int = 50, threshold: float = 0.8):
        super().__init__(threshold=threshold, debug_mode=FeatureFlags.eval_debug_enabled())
        self.min_products = min_products
        self.max_products = max_products
        
        # Validar parámetros
        if min_products < 0:
            raise ValueError(f"min_products debe ser >= 0, recibido: {min_products}")
        if max_products < min_products:
            raise ValueError(f"max_products ({max_products}) debe ser >= min_products ({min_products})")
    
    def evaluate(self, data: Dict[str, Any]) -> EvaluationResult:
        """
        Evalúa si el número de productos extraídos está en rango esperado.
        
        Args:
            data: Dict con 'productos' key conteniendo lista de productos
            
        Returns:
            EvaluationResult con score basado en razonabilidad del count
        """
        try:
            productos = data.get('productos', [])
            
            if not isinstance(productos, list):
                return self._create_result(
                    score=0.0,
                    category='product_count',
                    details={
                        'error': 'productos no es una lista',
                        'type_found': type(productos).__name__,
                        'productos_data': str(productos)[:100] if productos else None,
                        'expectation': 'Lista de productos con nombre y cantidad'
                    }
                )
            
            count = len(productos)
            
            # Lógica de scoring refinada
            if count == 0:
                score = 0.0
                details = {
                    'issue': 'No products found',
                    'count': count,
                    'severity': 'critical',
                    'suggestion': 'Verificar texto de entrada o algoritmo de extracción'
                }
            elif count < self.min_products:
                score = 0.3
                details = {
                    'issue': 'Too few products',
                    'count': count,
                    'min_expected': self.min_products,
                    'severity': 'high',
                    'suggestion': f'Se esperaban al menos {self.min_products} productos'
                }
            elif count > self.max_products:
                score = 0.5
                details = {
                    'issue': 'Too many products',
                    'count': count,
                    'max_expected': self.max_products,
                    'severity': 'medium',
                    'suggestion': f'Revisar si hay productos duplicados o ruido en extracción'
                }
            else:
                score = 1.0
                details = {
                    'status': 'OK',
                    'count': count,
                    'range': f'{self.min_products}-{self.max_products}',
                    'quality': 'optimal'
                }
            
            # Agregar análisis de productos si están disponibles
            if productos and count > 0:
                details['product_analysis'] = self._analyze_products_structure(productos)
            
            # Agregar debug info si está habilitado
            if self.debug_mode:
                details['debug'] = {
                    'productos_sample': productos[:3] if productos else [],  # Solo primeros 3 para debug
                    'threshold_used': self.threshold,
                    'evaluator_config': {
                        'min_products': self.min_products,
                        'max_products': self.max_products
                    },
                    'raw_productos_type': type(productos).__name__,
                    'data_keys': list(data.keys())
                }
            
            return self._create_result(
                score=score,
                category='product_count',
                details=details
            )
            
        except Exception as e:
            self.logger.error(f"Error en ProductCountEvaluator: {e}")
            return self._create_result(
                score=0.0,
                category='product_count',
                details={
                    'error': str(e),
                    'exception_type': type(e).__name__,
                    'severity': 'critical',
                    'suggestion': 'Revisar formato de datos de entrada'
                }
            )
    
    def _analyze_products_structure(self, productos: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analiza la estructura de los productos para validación adicional"""
        analysis = {
            'total_count': len(productos),
            'with_names': 0,
            'with_quantities': 0,
            'unique_names': set(),
            'quantity_stats': {'min': None, 'max': None, 'avg': None}
        }
        
        quantities = []
        
        for producto in productos:
            # Verificar nombres
            if isinstance(producto, dict) and producto.get('nombre'):
                analysis['with_names'] += 1
                analysis['unique_names'].add(producto['nombre'])
            
            # Verificar cantidades
            if isinstance(producto, dict) and 'cantidad' in producto:
                try:
                    cantidad = float(producto['cantidad'])
                    analysis['with_quantities'] += 1
                    quantities.append(cantidad)
                except (ValueError, TypeError):
                    pass
        
        # Estadísticas de cantidades
        if quantities:
            analysis['quantity_stats'] = {
                'min': min(quantities),
                'max': max(quantities),
                'avg': sum(quantities) / len(quantities)
            }
        
        # Convertir set a list para serialización
        analysis['unique_names'] = list(analysis['unique_names'])
        analysis['duplicates_detected'] = len(productos) > len(analysis['unique_names'])
        
        return analysis


class ProductQualityEvaluator(BaseEvaluator):
    """Evalúa la calidad de los nombres de productos extraídos"""
    
    def __init__(self, threshold: float = 0.7):
        super().__init__(threshold=threshold, debug_mode=FeatureFlags.eval_debug_enabled())
        
        # Keywords de productos típicos de catering
        self.catering_keywords = {
            'pasapalos': ['tequeño', 'empanada', 'canapé', 'bruschetta', 'tostada'],
            'dulces': ['shot', 'brownie', 'cheesecake', 'pie', 'mousse', 'tiramisú'],
            'bebidas': ['té', 'café', 'refresco', 'jugo', 'agua', 'smoothie', 'limonada'],
            'principales': ['pasta', 'arroz', 'pollo', 'pescado', 'ensalada']
        }
    
    def evaluate(self, data: Dict[str, Any]) -> EvaluationResult:
        """
        Evalúa la calidad de los nombres de productos basado en keywords de catering
        
        Args:
            data: Dict con 'productos' key conteniendo lista de productos
            
        Returns:
            EvaluationResult con score basado en relevancia de productos para catering
        """
        try:
            productos = data.get('productos', [])
            
            if not isinstance(productos, list) or len(productos) == 0:
                return self._create_result(
                    score=0.0,
                    category='product_quality',
                    details={
                        'error': 'No hay productos válidos para evaluar',
                        'suggestion': 'Verificar extracción de productos'
                    }
                )
            
            total_productos = len(productos)
            productos_catering = 0
            matches_by_category = {category: 0 for category in self.catering_keywords}
            product_details = []
            
            for producto in productos:
                nombre = ''
                if isinstance(producto, dict):
                    nombre = producto.get('nombre', '').lower()
                elif isinstance(producto, str):
                    nombre = producto.lower()
                
                if not nombre:
                    continue
                
                # Verificar matches con keywords de catering
                is_catering = False
                product_matches = []
                
                for category, keywords in self.catering_keywords.items():
                    for keyword in keywords:
                        if keyword in nombre:
                            matches_by_category[category] += 1
                            product_matches.append(f"{category}:{keyword}")
                            is_catering = True
                
                if is_catering:
                    productos_catering += 1
                
                product_details.append({
                    'nombre': nombre[:50],  # Limitar longitud
                    'is_catering': is_catering,
                    'matches': product_matches
                })
            
            # Calcular score basado en porcentaje de productos de catering
            if total_productos > 0:
                catering_percentage = productos_catering / total_productos
                score = min(1.0, catering_percentage * 1.2)  # Boost para scores altos
            else:
                score = 0.0
            
            details = {
                'total_products': total_productos,
                'catering_products': productos_catering,
                'catering_percentage': round(catering_percentage * 100, 1) if total_productos > 0 else 0,
                'matches_by_category': matches_by_category,
                'categories_found': len([cat for cat, count in matches_by_category.items() if count > 0])
            }
            
            if self.debug_mode:
                details['debug'] = {
                    'product_details': product_details,
                    'catering_keywords_used': self.catering_keywords
                }
            
            return self._create_result(
                score=score,
                category='product_quality',
                details=details
            )
            
        except Exception as e:
            self.logger.error(f"Error en ProductQualityEvaluator: {e}")
            return self._create_result(
                score=0.0,
                category='product_quality',
                details={
                    'error': str(e),
                    'exception_type': type(e).__name__
                }
            )


# Factory functions para facilitar uso
def evaluate_product_count(extracted_data: Dict[str, Any], threshold: float = 0.8, 
                          min_products: int = 1, max_products: int = 50) -> EvaluationResult:
    """Función helper para evaluar cantidad de productos fácilmente"""
    evaluator = ProductCountEvaluator(
        min_products=min_products,
        max_products=max_products, 
        threshold=threshold
    )
    return evaluator.evaluate(extracted_data)


def evaluate_product_quality(extracted_data: Dict[str, Any], threshold: float = 0.7) -> EvaluationResult:
    """Función helper para evaluar calidad de productos fácilmente"""
    evaluator = ProductQualityEvaluator(threshold=threshold)
    return evaluator.evaluate(extracted_data)


# Registro en factory
from backend.evals.base_evaluator import EvaluatorFactory

def register_extraction_evaluators():
    """Registra todos los evaluadores de extracción en el factory"""
    EvaluatorFactory.register_evaluator('product_count', ProductCountEvaluator)
    EvaluatorFactory.register_evaluator('product_quality', ProductQualityEvaluator)

# Auto-registro al importar el módulo
register_extraction_evaluators()