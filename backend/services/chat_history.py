"""
Adaptador de historial para LangChain.
Lee de rfx_chat_history sin modificar el esquema.

Estrategia:
- READ-ONLY: Solo lee de la tabla existente
- NO escribe: RFXService.save_chat_message() maneja la persistencia
- Transforma a formato LangChain (HumanMessage, AIMessage)
- Límite de 20 mensajes (10 turnos) para evitar context overflow
"""
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from typing import List
import logging

from backend.core.database import get_database_client

logger = logging.getLogger(__name__)


class RFXMessageHistory(BaseChatMessageHistory):
    """
    Adaptador READ-ONLY para LangChain.
    
    - Lee de rfx_chat_history existente
    - NO escribe (RFXService.save_chat_message lo hace)
    - Transforma a formato LangChain (HumanMessage, AIMessage)
    """
    
    def __init__(self, session_id: str):
        self.rfx_id = session_id
        self.db = get_database_client()
        logger.debug(f"📚 RFXMessageHistory initialized for RFX: {session_id}")
    
    @property
    def messages(self) -> List[BaseMessage]:
        """
        Recupera mensajes del historial y los transforma a formato LangChain.
        Retorna últimos 20 mensajes (10 turnos de conversación).
        """
        try:
            response = self.db.client.table("rfx_chat_history")\
                .select("user_message, assistant_message, created_at")\
                .eq("rfx_id", self.rfx_id)\
                .order("created_at", desc=False)\
                .limit(20)\
                .execute()
            
            lc_messages = []
            for row in response.data:
                if row.get("user_message"):
                    lc_messages.append(HumanMessage(content=row["user_message"]))
                if row.get("assistant_message"):
                    lc_messages.append(AIMessage(content=row["assistant_message"]))
            
            logger.debug(f"📚 Retrieved {len(lc_messages)} messages from history")
            return lc_messages
            
        except Exception as e:
            logger.error(f"❌ Error retrieving history: {e}")
            return []  # Fallback: sin historial
    
    def add_messages(self, messages: List[BaseMessage]) -> None:
        """
        No-op intencional.
        La persistencia se hace en RFXService.save_chat_message()
        porque necesitamos guardar metadatos (changes, confidence, tokens).
        """
        pass
    
    def clear(self) -> None:
        """No-op: no limpiamos historial desde aquí"""
        pass
