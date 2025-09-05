"""
🏁 Feature Flags - Control system for Agent AI improvements
Centralized feature flag management for safe rollout of new capabilities
"""
from backend.core.config import ENABLE_EVALS, ENABLE_META_PROMPTING, ENABLE_VERTICAL_AGENT, EVAL_DEBUG_MODE


class FeatureFlags:
    """
    Feature flags management for AI Agent improvements.
    
    This class provides static methods to check feature availability
    in a centralized way across the application.
    """
    
    @staticmethod
    def evals_enabled() -> bool:
        """
        Check if evaluation system is enabled.
        
        When enabled, allows:
        - Automatic evaluation of AI responses
        - Metrics collection and analysis
        - A/B testing capabilities
        
        Returns:
            bool: True if evals feature is enabled
        """
        return ENABLE_EVALS
    
    @staticmethod
    def meta_prompting_enabled() -> bool:
        """
        Check if meta-prompting system is enabled.
        
        When enabled, allows:
        - AI self-improvement cycles
        - Response quality optimization
        - Iterative prompt refinement
        
        Returns:
            bool: True if meta-prompting feature is enabled
        """
        return ENABLE_META_PROMPTING
    
    @staticmethod
    def vertical_agent_enabled() -> bool:
        """
        Check if vertical agent specialization is enabled.
        
        When enabled, allows:
        - Domain-specific optimizations
        - Catering industry specialization
        - Enhanced context awareness
        
        Returns:
            bool: True if vertical agent feature is enabled
        """
        return ENABLE_VERTICAL_AGENT
    
    @staticmethod
    def eval_debug_enabled() -> bool:
        """
        Check if evaluation debug mode is enabled.
        
        When enabled, provides:
        - Detailed eval logging
        - Step-by-step evaluation traces
        - Debug metrics collection
        
        Returns:
            bool: True if eval debug mode is enabled
        """
        return EVAL_DEBUG_MODE
    
    @staticmethod
    def function_calling_enabled() -> bool:
        """
        Check if OpenAI Function Calling is enabled for RFX extraction.
        
        When enabled, uses:
        - OpenAI Function Calling instead of JSON mode
        - Automatic schema validation by OpenAI
        - More robust data extraction
        - Better error handling
        
        Returns:
            bool: True if function calling is enabled
        """
        import os
        return os.getenv("ENABLE_FUNCTION_CALLING", "true").lower() == "true"
    
    @staticmethod
    def json_mode_fallback_enabled() -> bool:
        """
        Check if JSON mode fallback is enabled.
        
        When function calling fails, falls back to:
        - JSON mode extraction (current system)
        - Manual JSON parsing and cleaning
        - Legacy extraction methods
        
        Returns:
            bool: True if JSON mode fallback is enabled
        """
        import os
        return os.getenv("ENABLE_JSON_MODE_FALLBACK", "true").lower() == "true"

    @staticmethod
    def get_enabled_features() -> dict[str, bool]:
        """
        Get status of all feature flags.
        
        Returns:
            dict: Dictionary with all feature flags and their status
        """
        return {
            "evals": FeatureFlags.evals_enabled(),
            "meta_prompting": FeatureFlags.meta_prompting_enabled(),
            "vertical_agent": FeatureFlags.vertical_agent_enabled(),
            "eval_debug": FeatureFlags.eval_debug_enabled(),
            "function_calling": FeatureFlags.function_calling_enabled(),
            "json_mode_fallback": FeatureFlags.json_mode_fallback_enabled()
        }

    @staticmethod
    def is_any_ai_improvement_enabled() -> bool:
        """
        Check if any AI improvement feature is enabled.
        
        Useful for conditional loading of AI improvement modules.
        
        Returns:
            bool: True if any AI improvement feature is active
        """
        return (
            FeatureFlags.evals_enabled() or 
            FeatureFlags.meta_prompting_enabled() or 
            FeatureFlags.vertical_agent_enabled()
        )