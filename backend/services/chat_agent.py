"""
Agente de IA para procesar mensajes del chat conversacional RFX.

FASE 1: LangChain con memoria conversacional, parsing manual.
- Reutiliza RFXProcessorService para parsing de archivos
- Logging orientado a razonamiento del agente
- Memoria conversacional con RunnableWithMessageHistory

Responsabilidad: Llamar a OpenAI y retornar cambios estructurados.
NO tiene lógica de negocio - la IA decide TODO.

Filosofía KISS:
- Una sola responsabilidad: comunicarse con OpenAI
- Sin validación de negocio (la IA lo hace)
- Sin lógica compleja (la IA lo hace)
- Solo formatear entrada y parsear salida
"""

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.messages import HumanMessage, AIMessage
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
from backend.services.chat_history import RFXMessageHistory
from backend.services.rfx_processor import RFXProcessorService
from backend.utils.chat_logger import get_chat_logger

logger = logging.getLogger(__name__)


class ChatAgent:
    """
    Agente de IA para el chat conversacional con LangChain.
    
    FASE 1: Sin tools, parsing manual antes del agente.
    - Reutiliza RFXProcessorService para parsing de archivos
    - Logging orientado a razonamiento del agente
    - Memoria conversacional con RunnableWithMessageHistory
    
    KISS: Solo hace 3 cosas:
    1. Formatear el contexto para la IA
    2. Llamar a OpenAI (vía LangChain)
    3. Parsear la respuesta
    
    La IA decide TODO lo demás.
    """
    
    def __init__(self):
        """Inicializa el agente LangChain"""
        # LangChain LLM (reemplaza AsyncOpenAI)
        self.llm = ChatOpenAI(
            model=AIConfig.MODEL,
            temperature=AIConfig.TEMPERATURE,
            max_tokens=AIConfig.MAX_TOKENS,
            timeout=AIConfig.TIMEOUT,
            api_key=AIConfig.OPENAI_API_KEY
        )
        
        # ✅ REUTILIZAR: Parser de archivos existente
        self.file_processor = RFXProcessorService()
        
        # Output parser (JSON)
        self.parser = JsonOutputParser()
        
        # Prompt con placeholder de historia
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", CHAT_SYSTEM_PROMPT),
            ("system", "⚠️ REGLA CRÍTICA: Si no se menciona precio, USA 0.00. NO inventes precios."),
            ("system", "Por favor responde en formato JSON con la estructura especificada."),
            MessagesPlaceholder(variable_name="history"),  # ← Memoria inyectada
            ("human", "{input}")
        ])
        
        # Chain base (sin historial todavía)
        self.chain = self.prompt | self.llm | self.parser
        
        self.model = AIConfig.MODEL
        
        logger.info("🦜 ChatAgent initialized with LangChain")
    
    async def process_message(
        self,
        message: str,
        context: Dict[str, Any],
        rfx_id: str = "",
        files: List[Dict[str, Any]] = None
    ) -> ChatResponse:
        """
        Procesa mensaje del usuario con memoria conversacional.
        
        Flujo:
        1. Log input del usuario
        2. Si hay archivos, extraer contenido (REUTILIZA RFXProcessor)
        3. Recuperar historial (log mensajes reales)
        4. Ejecutar chain con memoria
        5. Log razonamiento y respuesta del agente
        
        Args:
            message: Mensaje del usuario
            context: Contexto actual del RFX
            rfx_id: ID del RFX (para logging y memoria)
            files: Archivos adjuntos (opcional)
            
        Returns:
            ChatResponse con mensaje y cambios a aplicar
        """
        chat_log = get_chat_logger(rfx_id)
        start_time = time.time()
        files = files or []
        
        try:
            # 1. Log input del usuario
            chat_log.user_input(message, has_files=bool(files))
            
            # 2. Si hay archivos, extraer contenido (REUTILIZA parsing existente)
            files_content = ""
            if files:
                files_content = self._extract_files_content(files, chat_log)
                # Agregar al mensaje del usuario
                if files_content:
                    message = f"{message}\n\n### ARCHIVOS ADJUNTOS:\n{files_content}"
            
            # 3. Crear instancia de historial (debe ser la misma para todo el request)
            history_store = {}
            
            def get_session_history(session_id: str):
                if session_id not in history_store:
                    history_store[session_id] = RFXMessageHistory(session_id)
                return history_store[session_id]
            
            # 4. Recuperar y loggear historial
            history = get_session_history(rfx_id)
            history_messages = history.messages
            
            # Convertir a formato para logging
            history_for_log = [
                {"role": "human" if isinstance(m, HumanMessage) else "assistant", 
                 "content": m.content}
                for m in history_messages
            ]
            chat_log.history_context(history_for_log)
            
            # 5. Log contexto del agente
            context_summary = f"{len(context.get('current_products', []))} products, " \
                            f"total: ${context.get('current_total', 0):.2f}"
            chat_log.agent_thinking(context_summary)
            
            # 6. Configurar chain con historial
            chain_with_history = RunnableWithMessageHistory(
                self.chain,
                get_session_history,
                input_messages_key="input",
                history_messages_key="history"
            )
            
            # 7. Ejecutar chain (LangChain inyecta historial automáticamente)
            ai_response = await chain_with_history.ainvoke(
                {
                    "input": self._format_input(message, context)
                },
                config={"configurable": {"session_id": rfx_id}}
            )
            
            # 8. Log decisión y respuesta del agente
            chat_log.agent_decision(
                ai_response.get("message", ""),
                len(ai_response.get("changes", []))
            )
            chat_log.agent_response(ai_response.get("message", ""))
            
            # 9. Calcular métricas (para guardar en BD, NO para logs)
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            # 10. Construir ChatResponse (KISS: conversión directa)
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
                    processing_time_ms=processing_time_ms,
                    model_used=self.model
                )
            )
            
        except json.JSONDecodeError as e:
            chat_log.error("JSON Parse Error", str(e))
            logger.error(f"[ChatAgent] JSON parse error: {e}")
            return self._error_response(
                "La respuesta de la IA no es válida. Por favor intenta de nuevo.",
                start_time
            )
            
        except Exception as e:
            chat_log.error("Processing Error", str(e))
            logger.error(f"[ChatAgent] Processing error: {e}", exc_info=True)
            return self._error_response(
                "Lo siento, no pude procesar tu solicitud. ¿Podrías reformularla?",
                start_time
            )
    
    def _extract_files_content(
        self, 
        files: List[Dict[str, Any]], 
        chat_log
    ) -> str:
        """
        ✅ REUTILIZA el parser multi-formato de RFXProcessor.
        
        NO duplica código, solo llama a métodos existentes.
        Los archivos vienen como bytes desde FormData (igual que /api/rfx/process).
        """
        extracted_parts = []
        
        for file in files:
            filename = file.get('name', 'unknown')
            content_bytes = file.get('content', b'')
            file_type = file.get('type', 'unknown')
            
            chat_log.file_parsing_start(filename, file_type)
            
            try:
                # Validar que content es bytes
                if not isinstance(content_bytes, bytes):
                    raise ValueError(f"Content debe ser bytes, recibido: {type(content_bytes)}")
                
                # ✅ REUTILIZA método existente de RFXProcessor
                text = self.file_processor._extract_text_from_document(content_bytes)
                
                if text and text.strip():
                    extracted_parts.append(f"### {filename}:\n{text}")
                    chat_log.file_parsing_success(filename, text)
                else:
                    chat_log.file_parsing_error(filename, "No text extracted")
                    
            except Exception as e:
                chat_log.file_parsing_error(filename, str(e))
                logger.error(f"❌ Error parsing {filename}: {e}", exc_info=True)
        
        return "\n\n".join(extracted_parts) if extracted_parts else ""
    
    def _format_input(self, message: str, context: Dict[str, Any]) -> str:
        """
        Formatea input para el agente (igual que antes).
        KISS: Template simple y directo.
        """
        # Productos actuales
        products_text = ""
        for i, product in enumerate(context.get("current_products", []), 1):
            if isinstance(product, dict):
                products_text += (
                    f"{i}. {product.get('nombre', 'Sin nombre')}\n"
                    f"   - ID: {product.get('id', 'N/A')}\n"
                    f"   - Cantidad: {product.get('cantidad', 0)} {product.get('unidad', 'unidades')}\n"
                    f"   - Precio: ${product.get('precio', 0):.2f}\n\n"
                )
        
        if not products_text:
            products_text = "No hay productos en el RFX actualmente.\n"
        
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

Por favor responde en formato JSON con la estructura especificada.
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
