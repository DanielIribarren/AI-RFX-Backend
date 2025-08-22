"""
Servicio de detección automática de dominio/industria para RFX.
Analiza el contenido y determina qué evaluadores específicos aplicar.
"""
from typing import Dict, Any, List, Tuple, Optional
import re
from collections import Counter
from backend.core.feature_flags import FeatureFlags
import logging

logger = logging.getLogger(__name__)


class DomainDetectorService:
    """Detecta automáticamente el dominio/industria del RFX basado en contenido"""
    
    def __init__(self):
        self.debug_mode = FeatureFlags.eval_debug_enabled()
        
        # Keywords por dominio/industria (expandible)
        self.domain_keywords = {
            'catering': {
                'primary': ['catering', 'evento', 'comida', 'alimentación', 'banquete', 'coctel'],
                'products': ['tequeño', 'empanada', 'pasapalo', 'bebida', 'refresco', 'café', 'té', 
                           'sandwich', 'bocadillo', 'shot', 'brownie', 'postre', 'torta', 'buffet'],
                'services': ['servicio', 'atención', 'mesero', 'coordinación', 'montaje', 'desmontaje'],
                'venues': ['salón', 'hotel', 'restaurante', 'terraza', 'auditorio']
            },
            'construction': {
                'primary': ['construcción', 'obra', 'edificación', 'infraestructura', 'proyecto'],
                'products': ['cemento', 'acero', 'concreto', 'ladrillo', 'pintura', 'tubería', 
                           'cable', 'material', 'herramienta', 'equipo', 'maquinaria'],
                'services': ['instalación', 'montaje', 'soldadura', 'excavación', 'demolición'],
                'venues': ['terreno', 'edificio', 'casa', 'oficina', 'local']
            },
            'it_services': {
                'primary': ['software', 'sistema', 'tecnología', 'informática', 'digital'],
                'products': ['aplicación', 'app', 'plataforma', 'base de datos', 'servidor', 
                           'computadora', 'laptop', 'hardware', 'licencia'],
                'services': ['desarrollo', 'programación', 'diseño', 'mantenimiento', 'soporte',
                           'consultoría', 'implementación', 'migración', 'backup'],
                'venues': ['oficina', 'data center', 'nube', 'cloud']
            },
            'events': {
                'primary': ['evento', 'celebración', 'fiesta', 'ceremonia', 'conferencia'],
                'products': ['decoración', 'flores', 'mobiliario', 'equipo de sonido', 'iluminación',
                           'pantalla', 'proyector', 'micrófono', 'tarima', 'escenario'],
                'services': ['organización', 'coordinación', 'protocolo', 'logística', 'montaje'],
                'venues': ['salón', 'auditorio', 'teatro', 'parque', 'playa', 'hotel']
            },
            'logistics': {
                'primary': ['transporte', 'logística', 'envío', 'distribución', 'entrega'],
                'products': ['vehículo', 'camión', 'furgoneta', 'embalaje', 'contenedor', 'pallet'],
                'services': ['traslado', 'almacenamiento', 'carga', 'descarga', 'distribución'],
                'venues': ['almacén', 'depósito', 'puerto', 'aeropuerto']
            },
            'marketing': {
                'primary': ['marketing', 'publicidad', 'promoción', 'campaña', 'branding'],
                'products': ['banner', 'flyer', 'brochure', 'website', 'video', 'fotografía',
                           'logo', 'diseño', 'contenido', 'redes sociales'],
                'services': ['estrategia', 'creatividad', 'producción', 'gestión', 'análisis'],
                'venues': ['oficina', 'estudio', 'locación', 'set']
            }
        }
        
        # Pesos para diferentes tipos de matches
        self.match_weights = {
            'primary': 3.0,     # Keywords principales tienen más peso
            'products': 2.0,    # Productos son muy indicativos
            'services': 1.5,    # Servicios son moderadamente indicativos
            'venues': 1.0       # Venues son menos indicativos pero útiles
        }
    
    def detect_domain(self, rfx_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detecta el dominio principal del RFX basado en análisis de contenido
        
        Args:
            rfx_data: Diccionario con datos del RFX
            
        Returns:
            Dict con información de detección:
            {
                'primary_domain': 'catering',
                'confidence': 0.85,
                'domain_scores': {'catering': 0.85, 'events': 0.23},
                'secondary_domains': ['events'],
                'keywords_found': {'catering': ['evento', 'comida', 'tequeño']},
                'analysis_details': {...}
            }
        """
        try:            
            # 1. Extraer todo el texto relevante del RFX
            full_text = self._extract_full_text(rfx_data)
            
            if not full_text.strip():
                return self._create_default_result('generic', 'No text content found')
            
            # 2. Analizar keywords por dominio
            domain_analysis = self._analyze_domains(full_text)
            
            # 3. Calcular scores finales
            domain_scores = self._calculate_domain_scores(domain_analysis)
            
            # 4. Determinar dominio principal y secundarios
            if not domain_scores:
                return self._create_default_result('generic', 'No domain-specific keywords found')
            
            primary_domain = max(domain_scores, key=domain_scores.get)
            primary_confidence = domain_scores[primary_domain]
            
            # Dominios secundarios (score > 30% del principal)
            threshold = primary_confidence * 0.3
            secondary_domains = [
                domain for domain, score in domain_scores.items() 
                if domain != primary_domain and score > threshold
            ]
            
            # 5. Crear resultado
            result = {
                'primary_domain': primary_domain,
                'confidence': round(primary_confidence, 3),
                'domain_scores': {k: round(v, 3) for k, v in domain_scores.items()},
                'secondary_domains': secondary_domains,
                'keywords_found': domain_analysis['keywords_by_domain'],
                'analysis_details': {
                    'total_text_length': len(full_text),
                    'total_keywords_found': domain_analysis['total_matches'],
                    'domains_analyzed': len(self.domain_keywords),
                    'confidence_level': self._get_confidence_level(primary_confidence)
                }
            }
            
            if self.debug_mode:
                result['debug'] = {
                    'full_text_sample': full_text[:200] + '...' if len(full_text) > 200 else full_text,
                    'raw_domain_analysis': domain_analysis,
                    'score_calculation': self._get_score_calculation_debug(domain_analysis),
                    'match_weights_used': self.match_weights
                }
            
            if self.debug_mode:
                logger.info(f"Domain detection result: {primary_domain} ({primary_confidence:.2f})")
            
            return result
            
        except Exception as e:
            logger.error(f"Error en domain detection: {e}")
            return self._create_default_result('generic', f'Error: {str(e)}')
    
    def _extract_full_text(self, rfx_data: Dict[str, Any]) -> str:
        """Extrae todo el texto relevante del RFX para análisis"""
        text_parts = []
        
        # Función recursiva para extraer texto de estructuras anidadas
        def extract_text_recursive(obj, depth=0):
            if depth > 5:  # Evitar recursión infinita
                return
                
            if isinstance(obj, str):
                text_parts.append(obj)
            elif isinstance(obj, dict):
                for key, value in obj.items():
                    # Incluir nombres de keys que pueden ser descriptivos
                    if isinstance(key, str):
                        text_parts.append(key)
                    extract_text_recursive(value, depth + 1)
            elif isinstance(obj, list):
                for item in obj:
                    extract_text_recursive(item, depth + 1)
        
        extract_text_recursive(rfx_data)
        
        # Unir todo el texto
        full_text = ' '.join(text_parts)
        
        # Limpiar texto
        full_text = re.sub(r'\s+', ' ', full_text)  # Múltiples espacios → uno
        full_text = full_text.strip()
        
        return full_text
    
    def _analyze_domains(self, full_text: str) -> Dict[str, Any]:
        """Analiza el texto buscando keywords de cada dominio"""
        text_lower = full_text.lower()
        
        domain_analysis = {
            'keywords_by_domain': {},
            'matches_by_category': {},
            'total_matches': 0
        }
        
        for domain, categories in self.domain_keywords.items():
            domain_matches = {}
            domain_total = 0
            
            for category, keywords in categories.items():
                category_matches = []
                
                for keyword in keywords:
                    # Buscar keyword como palabra completa (no substring)
                    pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
                    matches = re.findall(pattern, text_lower)
                    
                    if matches:
                        category_matches.extend(matches)
                        domain_total += len(matches)
                
                if category_matches:
                    domain_matches[category] = category_matches
            
            if domain_matches:
                domain_analysis['keywords_by_domain'][domain] = domain_matches
                domain_analysis['matches_by_category'][domain] = domain_total
                domain_analysis['total_matches'] += domain_total
        
        return domain_analysis
    
    def _calculate_domain_scores(self, domain_analysis: Dict[str, Any]) -> Dict[str, float]:
        """Calcula scores ponderados para cada dominio"""
        domain_scores = {}
        
        for domain, matches_by_category in domain_analysis['keywords_by_domain'].items():
            weighted_score = 0.0
            
            for category, matches in matches_by_category.items():
                # Score base: número de matches únicos
                unique_matches = len(set(matches))
                
                # Aplicar peso por categoría
                category_weight = self.match_weights.get(category, 1.0)
                weighted_score += unique_matches * category_weight
            
            # Normalizar score por número total de keywords en el dominio
            total_keywords_in_domain = sum(
                len(keywords) for keywords in self.domain_keywords[domain].values()
            )
            
            normalized_score = weighted_score / total_keywords_in_domain if total_keywords_in_domain > 0 else 0.0
            
            domain_scores[domain] = normalized_score
        
        return domain_scores
    
    def _get_confidence_level(self, confidence: float) -> str:
        """Determina nivel de confianza textual"""
        if confidence >= 0.8:
            return 'very_high'
        elif confidence >= 0.6:
            return 'high'
        elif confidence >= 0.4:
            return 'medium'
        elif confidence >= 0.2:
            return 'low'
        else:
            return 'very_low'
    
    def _get_score_calculation_debug(self, domain_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Información debug sobre cálculo de scores"""
        debug_info = {}
        
        for domain, matches in domain_analysis['keywords_by_domain'].items():
            domain_debug = {}
            total_weighted = 0.0
            
            for category, category_matches in matches.items():
                unique_count = len(set(category_matches))
                weight = self.match_weights.get(category, 1.0)
                category_score = unique_count * weight
                total_weighted += category_score
                
                domain_debug[category] = {
                    'matches': category_matches,
                    'unique_count': unique_count,
                    'weight': weight,
                    'weighted_score': category_score
                }
            
            total_keywords = sum(len(kw) for kw in self.domain_keywords[domain].values())
            final_score = total_weighted / total_keywords if total_keywords > 0 else 0.0
            
            domain_debug['total_weighted_score'] = total_weighted
            domain_debug['total_keywords_in_domain'] = total_keywords
            domain_debug['final_normalized_score'] = final_score
            
            debug_info[domain] = domain_debug
        
        return debug_info
    
    def _create_default_result(self, domain: str, reason: str) -> Dict[str, Any]:
        """Crea resultado por defecto cuando no se puede detectar dominio"""
        return {
            'primary_domain': domain,
            'confidence': 1.0 if domain == 'generic' else 0.0,
            'domain_scores': {domain: 1.0 if domain == 'generic' else 0.0},
            'secondary_domains': [],
            'keywords_found': {},
            'analysis_details': {
                'reason': reason,
                'total_text_length': 0,
                'total_keywords_found': 0,
                'domains_analyzed': len(self.domain_keywords),
                'confidence_level': 'default'
            }
        }
    
    def get_available_domains(self) -> List[str]:
        """Retorna lista de dominios disponibles para detección"""
        return list(self.domain_keywords.keys())
    
    def add_domain_keywords(self, domain: str, keywords: Dict[str, List[str]]) -> None:
        """Permite agregar keywords para un nuevo dominio dinámicamente"""
        if domain not in self.domain_keywords:
            self.domain_keywords[domain] = {}
        
        for category, keyword_list in keywords.items():
            if category not in self.domain_keywords[domain]:
                self.domain_keywords[domain][category] = []
            
            self.domain_keywords[domain][category].extend(keyword_list)
        
        if self.debug_mode:
            logger.info(f"Added keywords for domain '{domain}': {keywords}")
    
    def get_domain_keywords(self, domain: str) -> Optional[Dict[str, List[str]]]:
        """Retorna keywords para un dominio específico"""
        return self.domain_keywords.get(domain)


# Factory function para facilitar uso
def detect_rfx_domain(rfx_data: Dict[str, Any]) -> Dict[str, Any]:
    """Función helper para detectar dominio fácilmente"""
    detector = DomainDetectorService()
    return detector.detect_domain(rfx_data)


# Función para verificar si un dominio es soportado
def is_domain_supported(domain: str) -> bool:
    """Verifica si un dominio específico es soportado por el detector"""
    detector = DomainDetectorService()
    return domain in detector.get_available_domains()


# Función para obtener evaluadores recomendados por dominio
def get_recommended_evaluators_for_domain(domain: str) -> Dict[str, List[str]]:
    """
    Retorna evaluadores recomendados para un dominio específico
    
    Returns:
        {
            'generic': ['completeness', 'format_validation', 'consistency'],
            'specific': ['product_count', 'product_quality'] # si aplica
        }
    """
    # Evaluadores genéricos que siempre aplican
    generic_evaluators = ['completeness', 'format_validation', 'consistency']
    
    # Evaluadores específicos por dominio
    domain_specific_mapping = {
        'catering': ['product_count', 'product_quality'],
        'construction': [],  # Expandir en futuro
        'it_services': [],   # Expandir en futuro
        'events': [],        # Expandir en futuro
        'logistics': [],     # Expandir en futuro
        'marketing': [],     # Expandir en futuro
        'generic': []        # Sin evaluadores específicos
    }
    
    specific_evaluators = domain_specific_mapping.get(domain, [])
    
    return {
        'generic': generic_evaluators,
        'specific': specific_evaluators
    }