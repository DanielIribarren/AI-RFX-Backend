"""
Agente de IA para procesar mensajes del chat conversacional RFX.

ARQUITECTURA SIMPLIFICADA (Estilo TypeScript/NestJS):
- Un solo system prompt simple e inteligente
- El agente decide cuándo usar tools
- Streaming de respuestas para mejor UX
- Sin construcción dinámica de prompts

Filosofía AI-FIRST:
- El agente es inteligente, toma decisiones
- Las tools proveen datos, el agente razona
- Respuestas conversacionales, NO JSON
- El backend solo ejecuta lo que el agente decide
"""

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.messages import HumanMessage, AIMessage
from langchain.agents import create_openai_functions_agent, AgentExecutor
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
from backend.services.tools import (
    get_request_data_tool,
    add_products_tool,
    update_product_tool,
    delete_product_tool,
    modify_request_details_tool,
    parse_file_tool
)

logger = logging.getLogger(__name__)


class ChatAgent:
    """
    Agente de IA conversacional con arquitectura simplificada.
    
    Inspirado en arquitectura TypeScript/NestJS:
    - Un solo system prompt inteligente
    - El agente decide cuándo usar tools
    - Streaming para mejor UX
    - Sin construcción dinámica de prompts
    
    El agente es INTELIGENTE:
    - Decide cuándo consultar datos (get_request_data_tool)
    - Decide cuándo modificar (add/update/delete tools)
    - Responde conversacionalmente, NO en JSON
    """
    
    def __init__(self):
        """Inicializa el agente con LangChain + Tools"""
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
        
        # ✅ FASE 2: Tools disponibles para el agente
        self.tools = [
            get_request_data_tool,
            add_products_tool,
            update_product_tool,
            delete_product_tool,
            modify_request_details_tool,
            parse_file_tool,
        ]
        
        # Output parser (JSON)
        self.parser = JsonOutputParser()
        
        # ✅ PROMPT SIMPLE: Solo system prompt + historia + input
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", CHAT_SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])
        
        # ✅ FASE 2: Crear agente con tools
        self.agent = create_openai_functions_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=self.prompt
        )
        
        # ✅ FASE 2: AgentExecutor (reemplaza chain simple)
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=True,  # Para debugging
            return_intermediate_steps=False
        )
        
        self.model = AIConfig.MODEL
        
        logger.info(f"🦜 ChatAgent initialized with LangChain + {len(self.tools)} tools")
    
    async def process_message(
        self,
        message: str,
        context: Dict[str, Any],
        rfx_id: str = "",
        files: List[Dict[str, Any]] = None
    ) -> ChatResponse:
        """
        Procesa mensaje del usuario con streaming (estilo TypeScript).
        
        Flujo Simplificado:
        1. Preparar input (mensaje + archivos si hay)
        2. Ejecutar agent con streaming
        3. Capturar respuesta final
        4. Retornar ChatResponse
        
        El agente decide TODO: cuándo usar tools, qué responder, etc.
        """
        chat_log = get_chat_logger(rfx_id)
        start_time = time.time()
        files = files or []
        
        try:
            # 1. Log input
            chat_log.user_input(message, has_files=bool(files))
            
            # 2. Procesar archivos si hay
            if files:
                files_content = self._extract_files_content(files, chat_log)
                if files_content:
                    message = f"{message}\n\n### ARCHIVOS ADJUNTOS:\n{files_content}"
            
            # 3. Configurar historial
            history_store = {}
            
            def get_session_history(session_id: str):
                if session_id not in history_store:
                    history_store[session_id] = RFXMessageHistory(session_id)
                return history_store[session_id]
            
            # 4. Agent con historial
            agent_with_history = RunnableWithMessageHistory(
                self.agent_executor,
                get_session_history,
                input_messages_key="input",
                history_messages_key="history"
            )
            
            # 5. ✅ STREAMING (estilo TypeScript)
            response_message = None
            intermediate_steps = []
            
            # Preparar input simple: mensaje + contexto del RFX ID
            # El agente sabrá que request_id = rfx_id del contexto
            agent_input = {
                "input": f"{message}\n\n[CONTEXT: request_id={rfx_id}]"
            }
            
            # Stream execution
            async for step in agent_with_history.astream(
                agent_input,
                config={"configurable": {"session_id": rfx_id}}
            ):
                # Capturar output final
                if "output" in step:
                    response_message = step["output"]
                    logger.info(f"🤖 Agent raw response: {response_message}")
                
                # Capturar intermediate steps (tools usadas)
                if "intermediate_steps" in step:
                    intermediate_steps = step["intermediate_steps"]
            
            # 6. Si no hay respuesta, usar fallback
            if not response_message:
                response_message = "Lo siento, no pude procesar tu solicitud."
            
            # 7. Parsear respuesta JSON del agente
            try:
                # El agente puede retornar JSON embebido en markdown o texto plano
                agent_json = self._parse_agent_response(response_message)
                
                # Extraer campos del JSON
                message_text = agent_json.get("message", response_message)
                confidence = agent_json.get("confidence", 0.95)
                reasoning = agent_json.get("reasoning", "")
                agent_changes = agent_json.get("changes", [])
                requires_confirmation = agent_json.get("requires_confirmation", False)
                options = agent_json.get("options", [])
                
                # Log completo para observabilidad
                logger.info(f"📊 Agent parsed response:")
                logger.info(f"   - message: {message_text[:100]}...")
                logger.info(f"   - confidence: {confidence}")
                logger.info(f"   - reasoning: {reasoning[:100]}..." if reasoning else "   - reasoning: None")
                logger.info(f"   - changes: {len(agent_changes)}")
                logger.info(f"   - requires_confirmation: {requires_confirmation}")
                
            except Exception as e:
                logger.warning(f"⚠️ Could not parse agent JSON response: {e}")
                # Fallback: usar respuesta como texto plano
                message_text = response_message
                confidence = 0.95
                reasoning = ""
                agent_changes = []
                requires_confirmation = False
                options = []
            
            # 8. Extraer cambios de tools usadas (fallback si el agente no los incluyó)
            if not agent_changes:
                agent_changes = self._extract_changes_from_steps(intermediate_steps)
            
            # 9. Log respuesta
            chat_log.agent_response(message_text)
            chat_log.agent_decision(message_text, len(agent_changes))
            
            # 10. Construir ChatResponse con TODOS los campos
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            return ChatResponse(
                status="success",
                message=message_text,
                confidence=confidence,
                reasoning=reasoning,  # Campo interno para logs
                changes=[
                    RFXChange(**change) if isinstance(change, dict) else change
                    for change in agent_changes
                ],
                requires_confirmation=requires_confirmation,
                options=[
                    ConfirmationOption(**opt) if isinstance(opt, dict) else opt
                    for opt in options
                ],
                metadata=ChatMetadata(
                    processing_time_ms=processing_time_ms,
                    model_used=self.model
                )
            )
            
        except Exception as e:
            chat_log.error("Processing Error", str(e))
            logger.error(f"[ChatAgent] Processing error: {e}", exc_info=True)
            return self._error_response(
                "Lo siento, no pude procesar tu solicitud. ¿Podrías reformularla?",
                start_time
            )
    
    def _parse_agent_response(self, response: str) -> Dict[str, Any]:
        """
        Parsea la respuesta del agente que puede venir como:
        1. JSON puro: {"message": "...", "confidence": 0.95, ...}
        2. JSON en markdown: ```json\n{...}\n```
        3. Texto plano (fallback)
        
        Returns:
            Dict con campos: message, confidence, reasoning, changes, requires_confirmation, options
        """
        try:
            # Caso 1: Intentar parsear directamente como JSON
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        
        # Caso 2: Buscar JSON embebido en markdown
        import re
        json_match = re.search(r'```(?:json)?\s*\n?(\{.*?\})\s*\n?```', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Caso 3: Buscar JSON sin markdown delimiters
        json_match = re.search(r'(\{[^{]*"message"[^}]*\})', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Fallback: retornar como texto plano
        logger.warning(f"⚠️ Could not parse JSON from agent response, using as plain text")
        return {
            "message": response,
            "confidence": 0.95,
            "reasoning": "",
            "changes": [],
            "requires_confirmation": False,
            "options": []
        }
    
    def _extract_changes_from_steps(self, intermediate_steps: List) -> List[Dict[str, Any]]:
        """
        Extrae cambios estructurados de las tools ejecutadas.
        
        Args:
            intermediate_steps: Lista de (action, observation) del AgentExecutor
            
        Returns:
            Lista de cambios en formato RFXChange
        """
        changes = []
        
        for action, observation in intermediate_steps:
            tool_name = action.tool
            tool_input = action.tool_input
            
            # Solo extraer de tools CRUD (no de get_request_data_tool)
            if tool_name in ["add_products_tool", "update_product_tool", "delete_product_tool", "modify_request_details_tool"]:
                try:
                    # Parsear observation si es string
                    tool_result = json.loads(observation) if isinstance(observation, str) else observation
                    
                    # Solo agregar si fue exitoso
                    if tool_result.get("status") == "success":
                        changes.append({
                            "type": tool_name.replace("_tool", ""),
                            "field": tool_input.get("product_id") or tool_input.get("request_id"),
                            "old_value": None,
                            "new_value": tool_input.get("updates") or tool_input.get("products"),
                            "confidence": 1.0
                        })
                except Exception as e:
                    logger.warning(f"⚠️ Could not parse tool result: {e}")
        
        return changes
    
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
