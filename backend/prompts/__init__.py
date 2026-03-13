"""
Prompts module - Centralized AI prompts separated from business logic.
"""
from .rfx_extraction import RFXExtractionPrompt
from .proposal_generation import ProposalPrompts

__all__ = ['RFXExtractionPrompt', 'ProposalPrompts']
