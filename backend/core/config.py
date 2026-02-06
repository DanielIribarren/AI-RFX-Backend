"""
⚙️ Backend Configuration - Robust environment and settings management
Centralized configuration with validation and environment-specific settings
"""
import os
from typing import Optional, List
from dataclasses import dataclass
from enum import Enum


class Environment(str, Enum):
    """Application environments"""
    DEVELOPMENT = "development"
    STAGING = "staging" 
    PRODUCTION = "production"
    TESTING = "testing"


@dataclass
class DatabaseConfig:
    """Database configuration settings"""
    url: str
    anon_key: str
    service_role_key: Optional[str] = None
    
    @property
    def connection_params(self) -> dict:
        """Return connection parameters for Supabase client"""
        return {
            "url": self.url,
            "key": self.anon_key
        }


@dataclass
class OpenAIConfig:
    """
    Unified OpenAI API configuration.
    Consolidates all OpenAI-related settings from config.py and ai_config.py.
    """
    api_key: str
    
    # ==================== Model Configuration ====================
    # Default model for general use (extraction, analysis)
    model: str = "gpt-4o"  # 🚀 GPT-4o with 128k context window
    max_tokens: int = 4096  # 🚀 4096 tokens response
    temperature: float = 0.1
    timeout: int = 60  # 🚀 60s timeout
    context_window: int = 128000  # 🚀 128k context limit
    
    # Chat model (more economical for conversational use)
    chat_model: str = "gpt-4o-mini"
    chat_max_tokens: int = 2000
    chat_temperature: float = 0.3
    
    # ==================== Límites y Restricciones ====================
    max_retries: int = 3
    max_file_size_mb: int = 10
    max_context_products: int = 100
    max_message_length: int = 2000
    
    # ==================== Costos (USD por 1M tokens) ====================
    # Precios de gpt-4o-mini (más económico)
    cost_input_per_1m_gpt4o_mini: float = 0.15
    cost_output_per_1m_gpt4o_mini: float = 0.60
    
    # Precios de gpt-4o (más potente)
    cost_input_per_1m_gpt4o: float = 2.50
    cost_output_per_1m_gpt4o: float = 10.00
    
    # ==================== Umbrales de Decisión ====================
    # Confidence thresholds
    min_confidence_for_auto_apply: float = 0.85
    min_confidence_for_suggestion: float = 0.70
    
    # Similarity thresholds
    product_similarity_threshold: float = 0.80
    
    # Confirmation thresholds
    max_price_for_auto_delete: float = 100.00
    max_products_for_auto_delete: int = 1
    min_quantity_for_confirmation: int = 1000
    
    # ==================== Timeouts ====================
    confirmation_expiry_hours: int = 1
    chat_history_retention_days: int = 90
    
    # ==================== Feature Flags ====================
    enable_file_attachments: bool = True
    enable_duplicate_detection: bool = True
    enable_auto_pricing: bool = True
    enable_confidence_scores: bool = True
    
    def validate(self) -> bool:
        """Validate OpenAI configuration"""
        if not self.api_key or not self.api_key.startswith("sk-"):
            raise ValueError("Invalid OpenAI API key format")
        
        if self.max_tokens < 100:
            raise ValueError(f"max_tokens ({self.max_tokens}) is too low. Must be at least 100.")
        
        if not 0 <= self.temperature <= 2:
            raise ValueError(f"temperature ({self.temperature}) must be between 0 and 2.")
        
        return True
    
    def get_cost_per_token(self, model: str, token_type: str = "input") -> float:
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
                self.cost_input_per_1m_gpt4o_mini 
                if token_type == "input" 
                else self.cost_output_per_1m_gpt4o_mini
            )
        else:  # gpt-4o
            cost_per_1m = (
                self.cost_input_per_1m_gpt4o 
                if token_type == "input" 
                else self.cost_output_per_1m_gpt4o
            )
        
        return cost_per_1m / 1_000_000
    
    def calculate_cost(self, input_tokens: int, output_tokens: int, model: str) -> float:
        """
        Calcula el costo total de una llamada a la API.
        
        Args:
            input_tokens: Número de tokens de entrada
            output_tokens: Número de tokens de salida
            model: Nombre del modelo usado
            
        Returns:
            Costo total en USD
        """
        input_cost = input_tokens * self.get_cost_per_token(model, "input")
        output_cost = output_tokens * self.get_cost_per_token(model, "output")
        return input_cost + output_cost


@dataclass
class ServerConfig:
    """Flask server configuration"""
    host: str = "0.0.0.0"
    port: int = 3186
    debug: bool = False
    cors_origins: List[str] = None
    cors_methods: List[str] = None
    cors_headers: List[str] = None
    
    def __post_init__(self):
        if self.cors_origins is None:
            # Default CORS origins based on environment
            self.cors_origins = ["http://localhost:3000"]
        
        if self.cors_methods is None:
            self.cors_methods = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]  # ✅ Added PATCH
        
        if self.cors_headers is None:
            self.cors_headers = ["Content-Type", "Authorization", "X-Requested-With", "Accept"]


@dataclass
class FileUploadConfig:
    """File upload configuration"""
    max_file_size: int = 16 * 1024 * 1024  # 16MB
    allowed_extensions: List[str] = None
    upload_folder: str = "/tmp/rfx_uploads"
    
    def __post_init__(self):
        if self.allowed_extensions is None:
            self.allowed_extensions = ['.pdf', '.docx', '.txt']
        
        # Ensure upload folder exists
        os.makedirs(self.upload_folder, exist_ok=True)


@dataclass
class RedisConfig:
    """Redis configuration for caching"""
    url: str = "redis://localhost:6379/0"
    ttl: int = 86400  # 24 hours default TTL
    
    @property
    def is_available(self) -> bool:
        """Check if Redis URL is configured"""
        return bool(self.url and self.url != "redis://localhost:6379/0")


class Config:
    """Main configuration class with environment-specific settings"""
    
    def __init__(self):
        self.environment = Environment(os.getenv("ENVIRONMENT", "development"))
        self.secret_key = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
        
        # Initialize sub-configurations
        self.database = self._load_database_config()
        self.openai = self._load_openai_config()
        self.server = self._load_server_config()
        self.file_upload = self._load_file_upload_config()
        self.redis = self._load_redis_config()
        
        # Validate configuration
        self._validate_config()
    
    def _load_database_config(self) -> DatabaseConfig:
        """Load database configuration from environment"""
        return DatabaseConfig(
            url=self._get_required_env("SUPABASE_URL"),
            anon_key=self._get_required_env("SUPABASE_ANON_KEY"),
            service_role_key=os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        )
    
    def _load_openai_config(self) -> OpenAIConfig:
        """Load OpenAI configuration from environment - Optimized for GPT-4o"""
        return OpenAIConfig(
            api_key=self._get_required_env("OPENAI_API_KEY"),
            model=os.getenv("OPENAI_MODEL", "gpt-4o"),  # 🚀 Default to GPT-4o
            max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", "4096")),  # 🚀 4k response tokens
            temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.1")),
            timeout=int(os.getenv("OPENAI_TIMEOUT", "60")),  # 🚀 60s timeout
            context_window=int(os.getenv("OPENAI_CONTEXT_WINDOW", "128000"))  # 🚀 128k context
        )
    
    def _load_server_config(self) -> ServerConfig:
        """Load server configuration from environment"""
        cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000")
        
        # Environment-specific CORS origins
        if self.environment == Environment.PRODUCTION:
            # Add production URLs
            default_origins = ["https://*.vercel.app", "https://*.netlify.app"]
            if cors_origins == "http://localhost:3000":
                cors_origins = ",".join(default_origins)
        elif self.environment == Environment.DEVELOPMENT:
            # Development defaults
            default_origins = ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3001"]
            if cors_origins == "http://localhost:3000":
                cors_origins = ",".join(default_origins)
        
        return ServerConfig(
            host=os.getenv("HOST", "0.0.0.0"),
            port=int(os.getenv("PORT", "3186")),
            debug=self.environment == Environment.DEVELOPMENT,
            cors_origins=cors_origins.split(",") if cors_origins else [],
            cors_methods=os.getenv("CORS_METHODS", "GET,POST,PUT,PATCH,DELETE,OPTIONS").split(","),  # ✅ Added PATCH
            cors_headers=os.getenv("CORS_HEADERS", "Content-Type,Authorization,X-Requested-With,Accept").split(",")
        )
    
    def _load_file_upload_config(self) -> FileUploadConfig:
        """Load file upload configuration from environment"""
        return FileUploadConfig(
            max_file_size=int(os.getenv("MAX_FILE_SIZE", str(16 * 1024 * 1024))),
            upload_folder=os.getenv("UPLOAD_FOLDER", "/tmp/rfx_uploads")
        )
    
    def _load_redis_config(self) -> RedisConfig:
        """Load Redis configuration from environment"""
        return RedisConfig(
            url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            ttl=int(os.getenv("REDIS_TTL", "86400"))  # 24 hours default
        )
    
    def _get_required_env(self, key: str) -> str:
        """Get required environment variable or raise error"""
        value = os.getenv(key)
        if not value:
            raise ValueError(f"Required environment variable '{key}' is not set")
        return value
    
    def _validate_config(self) -> None:
        """Validate all configuration settings"""
        try:
            # Validate OpenAI configuration
            self.openai.validate()
            
            # Validate database URL format
            if not self.database.url.startswith(("http://", "https://")):
                raise ValueError("SUPABASE_URL must be a valid HTTP(S) URL")
            
            # Validate server configuration
            if not (1 <= self.server.port <= 65535):
                raise ValueError("PORT must be between 1 and 65535")
            
            print(f"✅ Configuration loaded successfully for {self.environment.value} environment")
            
        except Exception as e:
            print(f"❌ Configuration validation failed: {e}")
            raise
    
    @property
    def is_development(self) -> bool:
        return self.environment == Environment.DEVELOPMENT
    
    @property
    def is_production(self) -> bool:
        return self.environment == Environment.PRODUCTION
    
    @property
    def is_testing(self) -> bool:
        return self.environment == Environment.TESTING


# Global configuration instance
config = Config()


# Convenience functions for common configuration access
# Feature Flags para Agent Improvements
ENABLE_EVALS = os.getenv('ENABLE_EVALS', 'false').lower() == 'true'
ENABLE_META_PROMPTING = os.getenv('ENABLE_META_PROMPTING', 'false').lower() == 'true'
ENABLE_VERTICAL_AGENT = os.getenv('ENABLE_VERTICAL_AGENT', 'false').lower() == 'true'

# Feature Flag para Sistema de 3 Agentes AI (Proposal Generation)
USE_AI_AGENTS = os.getenv('USE_AI_AGENTS', 'true').lower() == 'true'  # ✅ NUEVO: Activado por defecto

# Debug flags
EVAL_DEBUG_MODE = os.getenv('EVAL_DEBUG_MODE', 'false').lower() == 'true'


def get_database_config() -> DatabaseConfig:
    """Get database configuration"""
    return config.database


def get_openai_config() -> OpenAIConfig:
    """Get OpenAI configuration"""
    return config.openai


def get_server_config() -> ServerConfig:
    """Get server configuration"""
    return config.server


def get_file_upload_config() -> FileUploadConfig:
    """Get file upload configuration"""
    return config.file_upload


# 🌍 MULTI-AMBIENTE: Funciones de conveniencia para migración
# NOTE: get_database_client() moved to backend.core.database (singleton pattern)
# Use: from backend.core.database import get_database_client


def get_environment() -> str:
    """Obtener ambiente actual"""
    return config.environment.value


def is_development() -> bool:
    """Verificar si estamos en desarrollo"""
    return config.is_development


def is_production() -> bool:
    """Verificar si estamos en producción"""  
    return config.is_production


def print_environment_info():
    """Imprimir información del ambiente actual para debugging"""
    db_config = get_database_config()
    openai_config = get_openai_config()
    
    print(f"🌍 AMBIENTE ACTUAL: {config.environment.value}")
    print(f"🗄️ Supabase URL: {db_config.url[:30]}..." if db_config.url else "❌ Supabase URL no configurada")
    print(f"🤖 OpenAI configurado: {'✅' if openai_config.api_key else '❌'}")
    print(f"🐛 Debug mode: {'✅' if config.server.debug else '❌'}")
