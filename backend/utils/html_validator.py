"""
🔍 HTML Validator - Validación robusta de HTML para propuestas
Sistema de scoring de 10 puntos según especificación del usuario
"""

from typing import Dict, List


class HTMLValidator:
    """
    Validador mejorado con sistema de scoring (0-10 puntos)
    """
    
    @staticmethod
    def validate_proposal_html(html_content: str) -> Dict:
        """
        Valida que el HTML tenga todo lo necesario
        
        Returns:
            dict con: is_valid, score, max_score, errors, warnings, details, percentage
        """
        validation = {
            'is_valid': True,
            'score': 0,
            'max_score': 10,
            'errors': [],
            'warnings': [],
            'details': {}
        }
        
        # Check 1: Estructura HTML (2 puntos)
        if HTMLValidator._check_html_structure(html_content):
            validation['score'] += 2
            validation['details']['structure'] = 'OK'
        else:
            validation['errors'].append("HTML structure incomplete")
            validation['details']['structure'] = 'FAIL'
        
        # Check 2: Sección de cliente (2 puntos)
        if HTMLValidator._check_client_section(html_content):
            validation['score'] += 2
            validation['details']['client_info'] = 'OK'
        else:
            validation['errors'].append("Client information missing")
            validation['details']['client_info'] = 'FAIL'
        
        # Check 3: Tabla de productos (2 puntos)
        if HTMLValidator._check_products_table(html_content):
            validation['score'] += 2
            validation['details']['products_table'] = 'OK'
        else:
            validation['errors'].append("Products table missing or incomplete")
            validation['details']['products_table'] = 'FAIL'
        
        # Check 4: Pricing breakdown (2 puntos)
        if HTMLValidator._check_pricing_section(html_content):
            validation['score'] += 2
            validation['details']['pricing'] = 'OK'
        else:
            validation['errors'].append("Pricing breakdown missing")
            validation['details']['pricing'] = 'FAIL'
        
        # Check 5: Términos y condiciones (1 punto)
        if HTMLValidator._check_terms_section(html_content):
            validation['score'] += 1
            validation['details']['terms'] = 'OK'
        else:
            validation['warnings'].append("Terms and conditions missing")
            validation['details']['terms'] = 'MISSING'
        
        # Check 6: Footer/contacto (1 punto)
        if HTMLValidator._check_footer(html_content):
            validation['score'] += 1
            validation['details']['footer'] = 'OK'
        else:
            validation['warnings'].append("Footer/contact info missing")
            validation['details']['footer'] = 'MISSING'
        
        # Determinar si es válido (score >= 8/10)
        validation['is_valid'] = validation['score'] >= 8
        validation['percentage'] = (validation['score'] / validation['max_score']) * 100
        
        return validation
    
    @staticmethod
    def _check_html_structure(html: str) -> bool:
        """Verifica estructura HTML básica"""
        return all([
            '<!DOCTYPE' in html or '<html' in html,
            '<head>' in html,
            '<style>' in html or '<link' in html,
            '<body>' in html,
        ])
    
    @staticmethod
    def _check_client_section(html: str) -> bool:
        """Verifica información del cliente"""
        html_lower = html.lower()
        return any([
            'cliente' in html_lower,
            'client' in html_lower,
        ]) and any([
            'empresa' in html_lower,
            'company' in html_lower,
        ])
    
    @staticmethod
    def _check_products_table(html: str) -> bool:
        """Verifica tabla de productos"""
        return '<table' in html and '<tbody>' in html and '<tr>' in html
    
    @staticmethod
    def _check_pricing_section(html: str) -> bool:
        """Verifica sección de precios"""
        html_lower = html.lower()
        has_price_indicators = '$' in html or 'USD' in html or 'total' in html_lower
        has_breakdown = any([
            'subtotal' in html_lower,
            'coordinación' in html_lower or 'coordination' in html_lower,
            'total' in html_lower,
        ])
        return has_price_indicators and has_breakdown
    
    @staticmethod
    def _check_terms_section(html: str) -> bool:
        """Verifica sección de términos"""
        html_lower = html.lower()
        return any([
            'términos' in html_lower,
            'condiciones' in html_lower,
            'terms' in html_lower,
            'conditions' in html_lower,
        ])
    
    @staticmethod
    def _check_footer(html: str) -> bool:
        """Verifica footer/contacto"""
        html_lower = html.lower()
        return any([
            'contacto' in html_lower or 'contact' in html_lower,
            'email' in html_lower or '@' in html,
            'teléfono' in html_lower or 'phone' in html_lower,
        ])
