"""
Logger especializado para conversaciones del Chat Agent.
Enfoque: Razonamiento del agente, no métricas técnicas.

Principios:
- Mostrar INPUT del usuario (texto + archivos)
- Mostrar RAZONAMIENTO del agente (qué pensó, qué decidió)
- Mostrar MENSAJES del historial (contenido real, no solo count)
- Mostrar PARSING de archivos (éxito/fallo con detalles)
- NO mostrar: Confidence (ya en UI), tokens, costos
"""
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class ChatLogger:
    """Logger conversacional para debugging del agente"""
    
    def __init__(self, rfx_id: str):
        self.rfx_id = rfx_id
        self.logger = logging.getLogger(f"chat.{rfx_id}")
    
    def user_input(self, message: str, has_files: bool = False):
        """Log input del usuario"""
        preview = message[:200] + "..." if len(message) > 200 else message
        file_indicator = " 📎 [WITH FILES]" if has_files else ""
        self.logger.info(f"\n{'='*80}")
        self.logger.info(f"💬 USER INPUT{file_indicator}:")
        self.logger.info(f"   {preview}")
    
    def file_parsing_start(self, filename: str, file_type: str):
        """Log inicio de parsing"""
        self.logger.info(f"📄 Parsing {file_type.upper()}: {filename}")
    
    def file_parsing_success(self, filename: str, content_preview: str):
        """Log éxito de parsing con preview del contenido"""
        preview = content_preview[:300].replace('\n', ' ') if content_preview else ""
        self.logger.info(f"✅ Extracted from {filename}:")
        self.logger.info(f"   Preview: {preview}...")
    
    def file_parsing_error(self, filename: str, error: str):
        """Log error de parsing"""
        self.logger.error(f"❌ Failed to parse {filename}: {error}")
    
    def history_context(self, messages: List[Dict[str, str]]):
        """Log mensajes del historial que el agente está leyendo"""
        if not messages:
            self.logger.info("📚 No previous conversation history")
            return
        
        self.logger.info(f"📚 CONVERSATION HISTORY ({len(messages)} messages):")
        for i, msg in enumerate(messages[-5:], 1):  # Últimos 5 mensajes
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')[:150]
            emoji = "👤" if role == "human" else "🤖"
            self.logger.info(f"   {emoji} [{role.upper()}]: {content}...")
    
    def agent_thinking(self, context_summary: str):
        """Log cuando el agente está procesando"""
        self.logger.info(f"🤔 AGENT ANALYZING:")
        self.logger.info(f"   Context: {context_summary}")
    
    def agent_reasoning(self, reasoning: str):
        """Log razonamiento del agente (si está disponible en response)"""
        self.logger.info(f"🧠 AGENT REASONING:")
        self.logger.info(f"   {reasoning}")
    
    def agent_decision(self, decision: str, changes_count: int):
        """Log decisión del agente"""
        self.logger.info(f"🎯 AGENT DECISION:")
        self.logger.info(f"   {decision}")
        self.logger.info(f"   Changes to apply: {changes_count}")
    
    def agent_response(self, message: str):
        """Log respuesta final del agente"""
        preview = message[:300] if len(message) > 300 else message
        self.logger.info(f"💬 AGENT RESPONSE:")
        self.logger.info(f"   {preview}")
        self.logger.info(f"{'='*80}\n")
    
    def error(self, error_type: str, details: str):
        """Log error conversacional"""
        self.logger.error(f"❌ {error_type}:")
        self.logger.error(f"   {details}")


# Función helper para crear logger
def get_chat_logger(rfx_id: str) -> ChatLogger:
    """Factory function para crear chat logger"""
    return ChatLogger(rfx_id)
