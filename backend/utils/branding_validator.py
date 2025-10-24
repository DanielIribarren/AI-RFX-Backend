"""
🔍 Branding Validator - MEJORA #5
Valida que el HTML generado siga el branding configurado
"""

import re
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)


class BrandingValidator:
    """Valida que el HTML generado use SOLO los colores y estilos del branding"""
    
    @staticmethod
    def validate_branding_consistency(
        html_content: str,
        branding_config: Dict
    ) -> Tuple[bool, List[str]]:
        """
        Valida que el HTML use SOLO los colores y estilos del branding
        
        Args:
            html_content: HTML generado por el LLM
            branding_config: Configuración de branding con colores y estilos
        
        Returns:
            (is_valid, list_of_issues)
        """
        issues = []
        
        logger.info("🔍 Validando consistencia de branding en HTML generado...")
        
        # 1. Validar colores
        expected_primary = branding_config.get('primary_color', '#0e2541')
        expected_secondary = branding_config.get('secondary_color', '#ffffff')
        table_header_bg = branding_config.get('table_header_bg', '#0e2541')
        table_header_text = branding_config.get('table_header_text', '#ffffff')
        
        # Encontrar todos los colores en el HTML
        color_pattern = r'#[0-9a-fA-F]{6}|#[0-9a-fA-F]{3}|rgb\([^)]+\)'
        found_colors = set(re.findall(color_pattern, html_content, re.IGNORECASE))
        
        # Normalizar colores encontrados (lowercase)
        found_colors = {color.lower() for color in found_colors}
        
        # Colores permitidos (branding + blancos/negros/grises básicos)
        allowed_colors = {
            expected_primary.lower(),
            expected_secondary.lower(),
            table_header_bg.lower(),
            table_header_text.lower(),
            '#ffffff', '#fff',  # Blanco
            '#000000', '#000',  # Negro
            '#f0f0f0', '#f5f5f5', '#fafafa',  # Grises claros comunes
            '#333333', '#333', '#666666', '#666',  # Grises oscuros comunes
            '#cccccc', '#ccc',  # Gris medio
        }
        
        # Verificar si hay colores no permitidos
        unauthorized_colors = found_colors - allowed_colors
        if unauthorized_colors:
            issues.append(f"⚠️ Colores no autorizados encontrados: {unauthorized_colors}")
            logger.warning(f"Colores no autorizados: {unauthorized_colors}")
        
        # 2. Validar que el primary_color se usa
        if expected_primary.lower() not in html_content.lower():
            issues.append(f"⚠️ Color primario del branding ({expected_primary}) no se usa en el HTML")
            logger.warning(f"Color primario {expected_primary} no encontrado")
        
        # 3. Validar logo
        if '<img' not in html_content and 'logo' not in html_content.lower():
            issues.append("⚠️ Logo no encontrado en el HTML")
            logger.warning("Logo no encontrado en HTML")
        
        # 4. Validar estructura básica
        required_elements = ['<!DOCTYPE', '<html', '<head', '<body', '<table']
        for element in required_elements:
            if element.lower() not in html_content.lower():
                issues.append(f"⚠️ Elemento HTML requerido '{element}' no encontrado")
                logger.warning(f"Elemento {element} no encontrado")
        
        # 5. Validar que NO haya estilos inline excesivos (señal de improvisación)
        inline_style_count = html_content.count('style="')
        if inline_style_count > 50:  # Threshold razonable
            issues.append(f"⚠️ Demasiados estilos inline ({inline_style_count}), posible improvisación")
            logger.warning(f"Estilos inline excesivos: {inline_style_count}")
        
        # 6. Validar que NO haya términos y condiciones (si está prohibido)
        forbidden_terms = ['términos y condiciones', 'terms and conditions', 'T&C', 'T & C']
        for term in forbidden_terms:
            if term.lower() in html_content.lower():
                issues.append(f"⚠️ Términos y Condiciones encontrados (prohibido): '{term}'")
                logger.warning(f"Términos prohibidos encontrados: {term}")
        
        is_valid = len(issues) == 0
        
        if is_valid:
            logger.info("✅ Validación de branding exitosa - HTML cumple con el branding")
        else:
            logger.warning(f"❌ Validación de branding falló - {len(issues)} problemas encontrados")
        
        return is_valid, issues
    
    @staticmethod
    def get_validation_report(html_content: str, branding_config: Dict) -> Dict:
        """
        Genera un reporte completo de validación de branding
        
        Returns:
            Dict con: is_valid, issues, warnings, stats
        """
        is_valid, issues = BrandingValidator.validate_branding_consistency(
            html_content, branding_config
        )
        
        # Estadísticas adicionales
        color_pattern = r'#[0-9a-fA-F]{6}|#[0-9a-fA-F]{3}'
        colors_used = set(re.findall(color_pattern, html_content, re.IGNORECASE))
        
        report = {
            'is_valid': is_valid,
            'issues': issues,
            'issue_count': len(issues),
            'stats': {
                'html_length': len(html_content),
                'colors_used': list(colors_used),
                'color_count': len(colors_used),
                'inline_styles': html_content.count('style="'),
                'has_logo': '<img' in html_content,
                'has_table': '<table' in html_content,
            }
        }
        
        return report
