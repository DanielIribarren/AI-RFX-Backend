"""
AI Product Selector - Selección Inteligente de Variantes

Cuando hay múltiples variantes de un producto en el catálogo,
este servicio usa AI para elegir la más apropiada según el contexto del RFX.

Ejemplo:
    RFX dice: "Tequeños" (100 unidades)
    Catálogo tiene:
    - "Tequeños Salados" ($3.05 / $4.43)
    - "Tequeños de Queso" ($3.50 / $5.00)
    - "Tequeños Dulces" ($4.00 / $6.00)
    
    AI analiza contexto y elige el más apropiado.
"""
import logging
from typing import List, Dict, Any, Optional
from openai import OpenAI

logger = logging.getLogger(__name__)


class AIProductSelector:
    """
    Selector inteligente de productos usando AI
    """
    
    def __init__(self, openai_client: OpenAI):
        self.openai = openai_client
    
    def select_best_variant(
        self, 
        query: str,
        variants: List[Dict[str, Any]],
        rfx_context: Optional[Dict[str, Any]] = None,
        max_retries: int = 2
    ) -> Dict[str, Any]:
        """
        Selecciona la mejor variante usando AI
        
        Args:
            query: Nombre del producto solicitado en el RFX
            variants: Lista de variantes encontradas en el catálogo
            rfx_context: Contexto del RFX (tipo de evento, descripción, etc.)
            max_retries: Número de reintentos si AI falla
        
        Returns:
            La variante seleccionada con metadata de selección
        """
        
        # Si solo hay 1 variante, retornar directamente
        if len(variants) == 1:
            logger.info(f"✅ Only 1 variant, no AI selection needed")
            return {
                **variants[0],
                'selection_method': 'single_variant',
                'ai_reasoning': 'Only one variant available'
            }
        
        # Si todas tienen el mismo precio, retornar la primera
        if self._all_same_price(variants):
            logger.info(f"✅ All variants have same price, using first one")
            return {
                **variants[0],
                'selection_method': 'same_price',
                'ai_reasoning': 'All variants have identical pricing'
            }
        
        # Usar AI para seleccionar
        logger.info(f"🤖 Using AI to select best variant from {len(variants)} options")
        
        try:
            selected = self._ai_select(query, variants, rfx_context)
            
            if selected:
                logger.info(f"✅ AI selected: {selected['product_name']}")
                logger.info(f"   Reasoning: {selected.get('ai_reasoning', 'N/A')}")
                return selected
            
            # Fallback: usar precio promedio
            logger.warning("⚠️ AI selection failed, using average pricing")
            return self._use_average_pricing(query, variants)
            
        except Exception as e:
            logger.error(f"❌ AI selection error: {e}")
            return self._use_average_pricing(query, variants)
    
    def _ai_select(
        self, 
        query: str,
        variants: List[Dict[str, Any]],
        rfx_context: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Usa AI para seleccionar la mejor variante
        """
        
        # Construir prompt
        variants_text = "\n".join([
            f"{i+1}. {v['product_name']} - Costo: ${v.get('unit_cost', 0):.2f}, Precio: ${v.get('unit_price', 0):.2f} (confidence: {v.get('confidence', 0):.2f})"
            for i, v in enumerate(variants)
        ])
        
        context_text = ""
        if rfx_context:
            context_text = f"""
Contexto del RFX:
- Tipo de evento: {rfx_context.get('rfx_type', 'N/A')}
- Descripción: {rfx_context.get('description', 'N/A')}
- Ubicación: {rfx_context.get('location', 'N/A')}
"""
        
        prompt = f"""Eres un experto en catering y eventos. El cliente solicitó "{query}" en su RFX.

Encontramos estas variantes en el catálogo:
{variants_text}

{context_text}

Analiza las opciones y selecciona la MÁS APROPIADA según:
1. Similitud con lo solicitado
2. Contexto del evento (si disponible)
3. Relación calidad-precio
4. Confidence score del match

Responde SOLO con el número de la opción (1, 2, 3, etc.) seguido de una breve razón (máximo 20 palabras).
Formato: "Número: Razón"

Ejemplo: "1: Es la opción más común y económica para eventos corporativos"
"""
        
        try:
            response = self.openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Eres un experto en selección de productos de catering. Responde de forma concisa."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=100
            )
            
            ai_response = response.choices[0].message.content.strip()
            logger.info(f"🤖 AI response: {ai_response}")
            
            # Parsear respuesta
            parts = ai_response.split(":", 1)
            if len(parts) == 2:
                try:
                    selected_index = int(parts[0].strip()) - 1
                    reasoning = parts[1].strip()
                    
                    if 0 <= selected_index < len(variants):
                        return {
                            **variants[selected_index],
                            'selection_method': 'ai_intelligent',
                            'ai_reasoning': reasoning,
                            'ai_confidence': variants[selected_index].get('confidence', 0)
                        }
                except ValueError:
                    logger.warning(f"⚠️ Could not parse AI response number: {parts[0]}")
            
            return None
            
        except Exception as e:
            logger.error(f"❌ AI selection API error: {e}")
            return None
    
    def _all_same_price(self, variants: List[Dict[str, Any]]) -> bool:
        """
        Verifica si todas las variantes tienen el mismo precio
        """
        if not variants:
            return False
        
        first_cost = variants[0].get('unit_cost', 0)
        first_price = variants[0].get('unit_price', 0)
        
        return all(
            v.get('unit_cost', 0) == first_cost and 
            v.get('unit_price', 0) == first_price 
            for v in variants
        )
    
    def _use_average_pricing(
        self, 
        query: str,
        variants: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Fallback: usar precio promedio de todas las variantes
        """
        
        avg_cost = sum(v.get('unit_cost', 0) for v in variants) / len(variants)
        avg_price = sum(v.get('unit_price', 0) for v in variants) / len(variants)
        
        # Usar el nombre de la variante con mayor confidence
        best_variant = max(variants, key=lambda x: x.get('confidence', 0))
        
        return {
            'id': best_variant['id'],
            'product_name': f"{query} (promedio de {len(variants)} variantes)",
            'unit_cost': round(avg_cost, 2),
            'unit_price': round(avg_price, 2),
            'match_type': 'average',
            'confidence': sum(v.get('confidence', 0) for v in variants) / len(variants),
            'selection_method': 'average_pricing',
            'ai_reasoning': f'Promedio de {len(variants)} variantes: {", ".join(v["product_name"] for v in variants)}',
            'variants_used': len(variants)
        }
