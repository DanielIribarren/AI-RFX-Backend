"""
Evaluadores genéricos para cualquier tipo de RFX.
Funcionan independientemente del dominio o industria.
"""
from typing import Dict, Any, List, Optional, Union
import re
from datetime import datetime, timedelta
from backend.evals.base_evaluator import BaseEvaluator, EvaluationResult
from backend.core.feature_flags import FeatureFlags

class CompletenessEvaluator(BaseEvaluator):
    """Evalúa si el RFX tiene todos los campos críticos necesarios"""
    
    def __init__(self, required_fields: List[str] = None, threshold: float = 0.8):
        super().__init__(threshold=threshold, debug_mode=FeatureFlags.eval_debug_enabled())
        
        # Campos requeridos universales para cualquier RFX
        self.required_fields = required_fields or [
            'cliente', 'productos', 'fecha', 'lugar'
        ]
        
        # Campos opcionales que mejoran el score
        self.optional_fields = [
            'email', 'telefono', 'contacto', 'descripcion', 'presupuesto'
        ]
    
    def evaluate(self, data: Dict[str, Any]) -> EvaluationResult:
        """
        Evalúa completitud de datos del RFX
        
        Score basado en:
        - Campos requeridos: 70% del score
        - Campos opcionales: 30% del score
        """
        try:
            # Verificar campos requeridos
            missing_required = []
            present_required = []
            
            for field in self.required_fields:
                value = data.get(field)
                if self._is_field_complete(value):
                    present_required.append(field)
                else:
                    missing_required.append(field)
            
            # Verificar campos opcionales
            present_optional = []
            for field in self.optional_fields:
                value = data.get(field)
                if self._is_field_complete(value):
                    present_optional.append(field)
            
            # Calcular score
            required_score = len(present_required) / len(self.required_fields) if self.required_fields else 1.0
            optional_score = len(present_optional) / len(self.optional_fields) if self.optional_fields else 0.0
            
            # Score combinado: 70% requeridos + 30% opcionales
            final_score = (required_score * 0.7) + (optional_score * 0.3)
            
            details = {
                'required_fields': {
                    'total': len(self.required_fields),
                    'present': len(present_required),
                    'missing': missing_required,
                    'score': required_score
                },
                'optional_fields': {
                    'total': len(self.optional_fields),
                    'present': len(present_optional),
                    'present_list': present_optional,
                    'score': optional_score
                },
                'completeness_percentage': round(final_score * 100, 1),
                'quality_level': self._get_quality_level(final_score)
            }
            
            if self.debug_mode:
                details['debug'] = {
                    'all_data_keys': list(data.keys()),
                    'required_analysis': {field: self._analyze_field(data.get(field)) for field in self.required_fields},
                    'calculation': f'({required_score:.2f} * 0.7) + ({optional_score:.2f} * 0.3) = {final_score:.2f}'
                }
            
            return self._create_result(
                score=final_score,
                category='completeness',
                details=details
            )
            
        except Exception as e:
            self.logger.error(f"Error en CompletenessEvaluator: {e}")
            return self._create_result(
                score=0.0,
                category='completeness',
                details={'error': str(e), 'exception_type': type(e).__name__}
            )
    
    def _is_field_complete(self, value: Any) -> bool:
        """Determina si un campo está completo y es útil"""
        if value is None:
            return False
        
        if isinstance(value, str):
            # String no vacío y no placeholder
            return len(value.strip()) > 0 and not self._is_placeholder(value)
        
        if isinstance(value, list):
            # Lista no vacía con elementos válidos
            return len(value) > 0 and any(self._is_field_complete(item) for item in value)
        
        if isinstance(value, dict):
            # Dict con al menos un campo completo
            return any(self._is_field_complete(v) for v in value.values())
        
        return True  # Números, fechas, etc.
    
    def _is_placeholder(self, text: str) -> bool:
        """Detecta si el texto es un placeholder común"""
        placeholders = [
            'por definir', 'por confirmar', 'no especificado', 'n/a', 'tbd',
            'pendiente', 'sin definir', 'cliente-', 'producto-', 'ubicación por'
        ]
        text_lower = text.lower()
        return any(placeholder in text_lower for placeholder in placeholders)
    
    def _analyze_field(self, value: Any) -> Dict[str, Any]:
        """Analiza un campo para debug"""
        return {
            'type': type(value).__name__,
            'is_complete': self._is_field_complete(value),
            'length': len(value) if hasattr(value, '__len__') else 'N/A',
            'is_placeholder': self._is_placeholder(str(value)) if isinstance(value, str) else False
        }
    
    def _get_quality_level(self, score: float) -> str:
        """Determina nivel de calidad basado en score"""
        if score >= 0.9:
            return 'excellent'
        elif score >= 0.8:
            return 'good'
        elif score >= 0.6:
            return 'acceptable'
        elif score >= 0.4:
            return 'poor'
        else:
            return 'critical'


class FormatValidationEvaluator(BaseEvaluator):
    """Evalúa formato correcto de datos comunes (fechas, emails, cantidades)"""
    
    def __init__(self, threshold: float = 0.8):
        super().__init__(threshold=threshold, debug_mode=FeatureFlags.eval_debug_enabled())
        
        # Patrones de validación
        self.email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        self.phone_pattern = re.compile(r'^[\+]?[\d\s\-\(\)]{7,20}$')
        self.date_patterns = [
            re.compile(r'^\d{4}-\d{2}-\d{2}$'),  # YYYY-MM-DD
            re.compile(r'^\d{2}/\d{2}/\d{4}$'),  # DD/MM/YYYY
            re.compile(r'^\d{2}-\d{2}-\d{4}$'),  # DD-MM-YYYY
        ]
    
    def evaluate(self, data: Dict[str, Any]) -> EvaluationResult:
        """
        Valida formatos de campos críticos
        """
        try:
            validations = []
            total_score = 0.0
            
            # Validar email si existe
            email = data.get('email') or data.get('clientes', {}).get('email')
            if email:
                is_valid = bool(self.email_pattern.match(str(email)))
                validations.append({
                    'field': 'email',
                    'value': email,
                    'is_valid': is_valid,
                    'message': 'Valid email format' if is_valid else 'Invalid email format'
                })
                total_score += 1.0 if is_valid else 0.0
            
            # Validar fecha si existe
            fecha = data.get('fecha') or data.get('fecha_entrega')
            if fecha:
                is_valid = self._validate_date_format(str(fecha))
                is_future = self._is_future_date(str(fecha)) if is_valid else False
                validations.append({
                    'field': 'fecha',
                    'value': fecha,
                    'is_valid': is_valid,
                    'is_future': is_future,
                    'message': self._get_date_message(is_valid, is_future)
                })
                # Score: 1.0 si válida y futura, 0.5 si válida pero pasada, 0.0 si inválida
                total_score += 1.0 if (is_valid and is_future) else (0.5 if is_valid else 0.0)
            
            # Validar cantidades en productos
            productos = data.get('productos', [])
            if isinstance(productos, list) and productos:
                valid_quantities = 0
                total_quantities = 0
                
                for producto in productos:
                    if isinstance(producto, dict) and 'cantidad' in producto:
                        total_quantities += 1
                        try:
                            cantidad = float(producto['cantidad'])
                            if cantidad > 0:
                                valid_quantities += 1
                        except (ValueError, TypeError):
                            pass
                
                if total_quantities > 0:
                    quantity_score = valid_quantities / total_quantities
                    validations.append({
                        'field': 'product_quantities',
                        'valid_count': valid_quantities,
                        'total_count': total_quantities,
                        'is_valid': quantity_score > 0.8,
                        'score': quantity_score,
                        'message': f'{valid_quantities}/{total_quantities} quantities are valid numbers > 0'
                    })
                    total_score += quantity_score
            
            # Calcular score final
            final_score = total_score / len(validations) if validations else 1.0
            
            details = {
                'validations': validations,
                'total_validations': len(validations),
                'passed_validations': sum(1 for v in validations if v.get('is_valid', False)),
                'format_score': round(final_score, 3)
            }
            
            if self.debug_mode:
                details['debug'] = {
                    'score_calculation': f'{total_score} / {len(validations)} = {final_score}',
                    'validation_details': validations
                }
            
            return self._create_result(
                score=final_score,
                category='format_validation',
                details=details
            )
            
        except Exception as e:
            self.logger.error(f"Error en FormatValidationEvaluator: {e}")
            return self._create_result(
                score=0.0,
                category='format_validation',
                details={'error': str(e), 'exception_type': type(e).__name__}
            )
    
    def _validate_date_format(self, date_str: str) -> bool:
        """Valida si la fecha tiene formato correcto"""
        return any(pattern.match(date_str.strip()) for pattern in self.date_patterns)
    
    def _is_future_date(self, date_str: str) -> bool:
        """Verifica si la fecha es futura"""
        try:
            # Intentar parsear la fecha
            for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y']:
                try:
                    parsed_date = datetime.strptime(date_str.strip(), fmt).date()
                    return parsed_date > datetime.now().date()
                except ValueError:
                    continue
            return False
        except:
            return False
    
    def _get_date_message(self, is_valid: bool, is_future: bool) -> str:
        """Mensaje descriptivo para validación de fecha"""
        if not is_valid:
            return 'Invalid date format (expected YYYY-MM-DD, DD/MM/YYYY, or DD-MM-YYYY)'
        elif not is_future:
            return 'Valid format but date is in the past'
        else:
            return 'Valid future date'


class ConsistencyEvaluator(BaseEvaluator):
    """Evalúa consistencia lógica entre datos del RFX"""
    
    def __init__(self, threshold: float = 0.7):
        super().__init__(threshold=threshold, debug_mode=FeatureFlags.eval_debug_enabled())
    
    def evaluate(self, data: Dict[str, Any]) -> EvaluationResult:
        """
        Evalúa consistencia entre diferentes campos del RFX
        """
        try:
            consistency_checks = []
            
            # Check 1: Productos vs Presupuesto (si existe)
            productos = data.get('productos', [])
            presupuesto = data.get('presupuesto') or data.get('costo_total')
            
            if productos and presupuesto:
                product_count = len(productos) if isinstance(productos, list) else 0
                try:
                    budget_amount = float(presupuesto)
                    # Estimación: promedio $10-50 per producto
                    estimated_min = product_count * 10
                    estimated_max = product_count * 100
                    
                    is_reasonable = estimated_min <= budget_amount <= estimated_max * 2
                    
                    consistency_checks.append({
                        'check': 'products_budget_consistency',
                        'is_consistent': is_reasonable,
                        'product_count': product_count,
                        'budget_amount': budget_amount,
                        'estimated_range': f'${estimated_min}-${estimated_max}',
                        'message': 'Budget is reasonable for product count' if is_reasonable else 'Budget seems unrealistic for product count'
                    })
                except (ValueError, TypeError):
                    pass
            
            # Check 2: Fecha vs Hora de entrega
            fecha = data.get('fecha') or data.get('fecha_entrega')
            hora = data.get('hora') or data.get('hora_entrega')
            
            if fecha and hora:
                is_business_hours = self._is_business_hours(str(hora))
                consistency_checks.append({
                    'check': 'delivery_time_consistency',
                    'is_consistent': is_business_hours,
                    'fecha': fecha,
                    'hora': hora,
                    'message': 'Delivery time is within business hours' if is_business_hours else 'Delivery time is outside typical business hours'
                })
            
            # Check 3: Cliente vs Email domain (si ambos existen)
            cliente = data.get('cliente') or data.get('clientes', {}).get('nombre', '')
            email = data.get('email') or data.get('clientes', {}).get('email', '')
            
            if cliente and email and '@' in email:
                domain_consistency = self._check_email_domain_consistency(cliente, email)
                consistency_checks.append({
                    'check': 'client_email_consistency',
                    'is_consistent': domain_consistency['is_consistent'],
                    'cliente': cliente,
                    'email_domain': domain_consistency['domain'],
                    'message': domain_consistency['message']
                })
            
            # Calcular score final
            if consistency_checks:
                consistent_count = sum(1 for check in consistency_checks if check['is_consistent'])
                final_score = consistent_count / len(consistency_checks)
            else:
                final_score = 1.0  # Si no hay checks, asumimos consistencia
            
            details = {
                'consistency_checks': consistency_checks,
                'total_checks': len(consistency_checks),
                'passed_checks': sum(1 for check in consistency_checks if check['is_consistent']),
                'consistency_score': round(final_score, 3)
            }
            
            if self.debug_mode:
                details['debug'] = {
                    'score_calculation': f'{sum(1 for c in consistency_checks if c["is_consistent"])} / {len(consistency_checks)} = {final_score}',
                    'all_checks_details': consistency_checks
                }
            
            return self._create_result(
                score=final_score,
                category='consistency',
                details=details
            )
            
        except Exception as e:
            self.logger.error(f"Error en ConsistencyEvaluator: {e}")
            return self._create_result(
                score=0.0,
                category='consistency',
                details={'error': str(e), 'exception_type': type(e).__name__}
            )
    
    def _is_business_hours(self, time_str: str) -> bool:
        """Verifica si la hora está en horario comercial (7 AM - 7 PM)"""
        try:
            # Extraer hora de diferentes formatos
            time_patterns = [
                re.compile(r'(\d{1,2}):(\d{2})'),  # HH:MM
                re.compile(r'(\d{1,2})\s*(am|pm)', re.IGNORECASE),  # H AM/PM
            ]
            
            for pattern in time_patterns:
                match = pattern.search(time_str)
                if match:
                    hour = int(match.group(1))
                    
                    # Convertir AM/PM a 24h si es necesario
                    if len(match.groups()) > 1 and match.group(2):
                        if match.group(2).lower() == 'pm' and hour != 12:
                            hour += 12
                        elif match.group(2).lower() == 'am' and hour == 12:
                            hour = 0
                    
                    return 7 <= hour <= 19  # 7 AM a 7 PM
            
            return True  # Si no puede parsear, asume que es válido
        except:
            return True
    
    def _check_email_domain_consistency(self, cliente: str, email: str) -> Dict[str, Any]:
        """Verifica consistencia entre nombre de cliente y dominio de email"""
        try:
            domain = email.split('@')[1].lower()
            cliente_lower = cliente.lower()
            
            # Extraer palabras clave del nombre del cliente
            client_words = re.findall(r'\b\w+\b', cliente_lower)
            
            # Verificar si alguna palabra del cliente está en el dominio
            word_in_domain = any(word in domain for word in client_words if len(word) > 3)
            
            # Verificar dominios corporativos comunes
            corporate_domains = ['gmail.com', 'hotmail.com', 'yahoo.com', 'outlook.com']
            is_corporate_domain = domain not in corporate_domains
            
            is_consistent = word_in_domain or not is_corporate_domain
            
            if word_in_domain:
                message = 'Client name matches email domain'
            elif is_corporate_domain:
                message = 'Corporate email domain (likely valid)'
            else:
                message = 'Generic email domain with no client name match'
            
            return {
                'is_consistent': is_consistent,
                'domain': domain,
                'message': message,
                'word_in_domain': word_in_domain,
                'is_corporate_domain': is_corporate_domain
            }
            
        except:
            return {
                'is_consistent': True,
                'domain': 'unknown',
                'message': 'Could not analyze email domain'
            }


# Factory functions para facilitar uso
def evaluate_completeness(rfx_data: Dict[str, Any], threshold: float = 0.8, 
                         required_fields: List[str] = None) -> EvaluationResult:
    """Función helper para evaluar completitud fácilmente"""
    evaluator = CompletenessEvaluator(required_fields=required_fields, threshold=threshold)
    return evaluator.evaluate(rfx_data)


def evaluate_format_validation(rfx_data: Dict[str, Any], threshold: float = 0.8) -> EvaluationResult:
    """Función helper para evaluar formato fácilmente"""
    evaluator = FormatValidationEvaluator(threshold=threshold)
    return evaluator.evaluate(rfx_data)


def evaluate_consistency(rfx_data: Dict[str, Any], threshold: float = 0.7) -> EvaluationResult:
    """Función helper para evaluar consistencia fácilmente"""
    evaluator = ConsistencyEvaluator(threshold=threshold)
    return evaluator.evaluate(rfx_data)


# Registro en factory
from backend.evals.base_evaluator import EvaluatorFactory

def register_generic_evaluators():
    """Registra todos los evaluadores genéricos en el factory"""
    EvaluatorFactory.register_evaluator('completeness', CompletenessEvaluator)
    EvaluatorFactory.register_evaluator('format_validation', FormatValidationEvaluator)
    EvaluatorFactory.register_evaluator('consistency', ConsistencyEvaluator)

# Auto-registro al importar el módulo
register_generic_evaluators()