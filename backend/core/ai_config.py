"""
Configuración del Agente de IA para Chat Conversacional RFX.

Este módulo centraliza toda la configuración relacionada con OpenAI
y el comportamiento del agente de chat.
"""

import os
from typing import Final


class AIConfig:
    """Configuración para el agente de IA del chat conversacional."""
    
    # ==================== OpenAI Configuration ====================
    OPENAI_API_KEY: Final[str] = os.getenv("OPENAI_API_KEY", "")
    MODEL: Final[str] = os.getenv("OPENAI_MODEL", "gpt-4o")
    MAX_TOKENS: Final[int] = int(os.getenv("OPENAI_MAX_TOKENS", "2000"))
    TEMPERATURE: Final[float] = float(os.getenv("OPENAI_TEMPERATURE", "0.3"))
    TIMEOUT: Final[int] = int(os.getenv("OPENAI_TIMEOUT", "60"))
    
    # ==================== Límites y Restricciones ====================
    MAX_RETRIES: Final[int] = 3
    MAX_FILE_SIZE_MB: Final[int] = 10
    MAX_CONTEXT_PRODUCTS: Final[int] = 100
    MAX_MESSAGE_LENGTH: Final[int] = 2000
    
    # ==================== Costos (USD por 1M tokens) ====================
    # Precios de gpt-4o-mini (más económico)
    COST_INPUT_PER_1M_GPT4O_MINI: Final[float] = 0.15
    COST_OUTPUT_PER_1M_GPT4O_MINI: Final[float] = 0.60
    
    # Precios de gpt-4o (más potente)
    COST_INPUT_PER_1M_GPT4O: Final[float] = 2.50
    COST_OUTPUT_PER_1M_GPT4O: Final[float] = 10.00
    
    # ==================== Umbrales de Decisión ====================
    # Confidence thresholds
    MIN_CONFIDENCE_FOR_AUTO_APPLY: Final[float] = 0.85
    MIN_CONFIDENCE_FOR_SUGGESTION: Final[float] = 0.70
    
    # Similarity thresholds
    PRODUCT_SIMILARITY_THRESHOLD: Final[float] = 0.80
    
    # Confirmation thresholds
    MAX_PRICE_FOR_AUTO_DELETE: Final[float] = 100.00
    MAX_PRODUCTS_FOR_AUTO_DELETE: Final[int] = 1
    MIN_QUANTITY_FOR_CONFIRMATION: Final[int] = 1000
    
    # ==================== Timeouts ====================
    CONFIRMATION_EXPIRY_HOURS: Final[int] = 1
    CHAT_HISTORY_RETENTION_DAYS: Final[int] = 90
    
    # ==================== Feature Flags ====================
    ENABLE_FILE_ATTACHMENTS: Final[bool] = True
    ENABLE_DUPLICATE_DETECTION: Final[bool] = True
    ENABLE_AUTO_PRICING: Final[bool] = True
    ENABLE_CONFIDENCE_SCORES: Final[bool] = True
    
    @classmethod
    def get_cost_per_token(cls, model: str, token_type: str = "input") -> float:
        """
        Calcula el costo por token para un modelo específico.
        
        Args:
            model: Nombre del modelo (ej: "gpt-4o", "gpt-4o-mini")
            token_type: "input" o "output"
            
        Returns:
            Costo en USD por token
        """
        if "gpt-4o-mini" in model:
            cost_per_1m = (
                cls.COST_INPUT_PER_1M_GPT4O_MINI 
                if token_type == "input" 
                else cls.COST_OUTPUT_PER_1M_GPT4O_MINI
            )
        else:  # gpt-4o
            cost_per_1m = (
                cls.COST_INPUT_PER_1M_GPT4O 
                if token_type == "input" 
                else cls.COST_OUTPUT_PER_1M_GPT4O
            )
        
        return cost_per_1m / 1_000_000
    
    @classmethod
    def calculate_cost(
        cls, 
        input_tokens: int, 
        output_tokens: int, 
        model: str
    ) -> float:
        """
        Calcula el costo total de una llamada a la API.
        
        Args:
            input_tokens: Número de tokens de entrada
            output_tokens: Número de tokens de salida
            model: Nombre del modelo usado
            
        Returns:
            Costo total en USD
        """
        input_cost = input_tokens * cls.get_cost_per_token(model, "input")
        output_cost = output_tokens * cls.get_cost_per_token(model, "output")
        return input_cost + output_cost
    
    @classmethod
    def validate_config(cls) -> bool:
        """
        Valida que la configuración esté completa.
        
        Returns:
            True si la configuración es válida
            
        Raises:
            ValueError: Si falta alguna configuración crítica
        """
        if not cls.OPENAI_API_KEY:
            raise ValueError(
                "OPENAI_API_KEY no está configurada. "
                "Por favor configura la variable de entorno."
            )
        
        if cls.MAX_TOKENS < 100:
            raise ValueError(
                f"MAX_TOKENS ({cls.MAX_TOKENS}) es muy bajo. "
                "Debe ser al menos 100."
            )
        
        if not 0 <= cls.TEMPERATURE <= 2:
            raise ValueError(
                f"TEMPERATURE ({cls.TEMPERATURE}) debe estar entre 0 y 2."
            )
        
        return True


# Exportar
__all__ = ["AIConfig"]
