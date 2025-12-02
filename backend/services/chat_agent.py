"""
Agente de IA para procesar mensajes del chat conversacional RFX.

Responsabilidad: Llamar a OpenAI y retornar cambios estructurados.
NO tiene lógica de negocio - la IA decide TODO.

Filosofía KISS:
- Una sola responsabilidad: comunicarse con OpenAI
- Sin validación de negocio (la IA lo hace)
- Sin lógica compleja (la IA lo hace)
- Solo formatear entrada y parsear salida
"""

from openai import AsyncOpenAI
from typing import List, Dict, Any
import json
import time
import logging

from backend.prompts.chat_system_prompt import CHAT_SYSTEM_PROMPT
from backend.models.chat_models import (
    ChatResponse, 
    RFXChange, 
    ConfirmationOption,
    ChatMetadata
)
from backend.core.ai_config import AIConfig

logger = logging.getLogger(__name__)


class ChatAgent:
    """
    Agente de IA para el chat conversacional.
    
    KISS: Solo hace 3 cosas:
    1. Formatear el contexto para la IA
    2. Llamar a OpenAI
    3. Parsear la respuesta
    
    La IA decide TODO lo demás.
    """
    
    def __init__(self):
        """Inicializa el cliente de OpenAI."""
        self.client = AsyncOpenAI(api_key=AIConfig.OPENAI_API_KEY)
        self.model = AIConfig.MODEL
    
    async def process_message(
        self,
        message: str,
        context: Dict[str, Any],
        rfx_id: str = "",
        files: List[Dict[str, Any]] = None
    ) -> ChatResponse:
        """
        Procesa un mensaje del usuario.
        
        Args:
            message: Mensaje del usuario
            context: Contexto actual del RFX
            rfx_id: ID del RFX (para logging)
            files: Archivos adjuntos (opcional)
            
        Returns:
            ChatResponse con mensaje y cambios a aplicar
        """
        start_time = time.time()
        files = files or []
        
        try:
            # 1. Construir prompt del usuario (KISS: simple y directo)
            user_prompt = self._build_user_prompt(message, context, files)
            
            logger.info(f"[ChatAgent] Processing message for RFX {rfx_id}")
            
            # 2. Llamar a OpenAI con JSON mode
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": CHAT_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=AIConfig.TEMPERATURE,
                max_tokens=AIConfig.MAX_TOKENS,
                timeout=AIConfig.TIMEOUT
            )
            
            # 3. Parsear respuesta
            ai_response = json.loads(response.choices[0].message.content)
            
            # 4. Calcular métricas
            processing_time_ms = int((time.time() - start_time) * 1000)
            tokens_used = response.usage.total_tokens
            cost_usd = AIConfig.calculate_cost(
                response.usage.prompt_tokens,
                response.usage.completion_tokens,
                self.model
            )
            
            logger.info(
                f"[ChatAgent] Response received: "
                f"confidence={ai_response.get('confidence', 0):.2f}, "
                f"changes={len(ai_response.get('changes', []))}, "
                f"tokens={tokens_used}, "
                f"cost=${cost_usd:.6f}"
            )
            
            # 5. Construir ChatResponse (KISS: conversión directa)
            return ChatResponse(
                status="success",
                message=ai_response.get("message", ""),
                confidence=ai_response.get("confidence", 0.0),
                changes=[
                    RFXChange(**change) 
                    for change in ai_response.get("changes", [])
                ],
                requires_confirmation=ai_response.get("requires_confirmation", False),
                options=[
                    ConfirmationOption(**opt) 
                    for opt in ai_response.get("options", [])
                ],
                metadata=ChatMetadata(
                    tokens_used=tokens_used,
                    cost_usd=cost_usd,
                    processing_time_ms=processing_time_ms,
                    model_used=self.model
                )
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"[ChatAgent] JSON parse error: {e}")
            return self._error_response(
                "La respuesta de la IA no es válida. Por favor intenta de nuevo.",
                start_time
            )
            
        except Exception as e:
            logger.error(f"[ChatAgent] Processing error: {e}", exc_info=True)
            return self._error_response(
                "Lo siento, no pude procesar tu solicitud. ¿Podrías reformularla?",
                start_time
            )
    
    def _build_user_prompt(
        self,
        message: str,
        context: Dict[str, Any],
        files: List[Dict[str, Any]]
    ) -> str:
        """
        Construye el prompt del usuario con contexto.
        
        KISS: Template simple y directo, sin lógica compleja.
        """
        # Productos actuales
        products_text = ""
        for i, product in enumerate(context.get("current_products", []), 1):
            products_text += (
                f"{i}. {product.get('nombre', 'Sin nombre')}\n"
                f"   - ID: {product.get('id', 'N/A')}\n"
                f"   - Cantidad: {product.get('cantidad', 0)} {product.get('unidad', 'unidades')}\n"
                f"   - Precio: ${product.get('precio', 0):.2f}\n\n"
            )
        
        if not products_text:
            products_text = "No hay productos en el RFX actualmente.\n"
        
        # Archivos adjuntos
        files_text = ""
        if files:
            files_text = "\n## Archivos Adjuntos:\n"
            for file in files:
                files_text += f"- {file.get('name', 'archivo')} ({file.get('type', 'unknown')})\n"
        
        # Construir prompt completo
        prompt = f"""# SOLICITUD DEL USUARIO

{message}

# CONTEXTO ACTUAL DEL RFX

## Productos Actuales:
{products_text}

## Información del RFX:
- Total actual: ${context.get('current_total', 0):.2f}
- Fecha de entrega: {context.get('delivery_date', 'No especificada')}
- Lugar de entrega: {context.get('delivery_location', 'No especificado')}
- Cliente: {context.get('client_name', 'No especificado')}
- Moneda: {context.get('currency', 'MXN')}
{files_text}

Por favor responde en formato JSON con la estructura especificada en el system prompt.
"""
        
        return prompt
    
    def _error_response(self, message: str, start_time: float) -> ChatResponse:
        """
        Crea una respuesta de error amigable.
        
        KISS: Respuesta simple y consistente para todos los errores.
        """
        return ChatResponse(
            status="error",
            message=message,
            confidence=0.0,
            changes=[],
            requires_confirmation=False,
            options=[],
            metadata=ChatMetadata(
                processing_time_ms=int((time.time() - start_time) * 1000),
                model_used=self.model
            )
        )


# Exportar
__all__ = ["ChatAgent"]
