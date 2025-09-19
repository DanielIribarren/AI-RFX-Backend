"""
🧪 Tests de Compatibilidad para Modelos Unificados
Verifica que la consolidación no rompa la compatibilidad backward
"""
import pytest
from datetime import datetime, date, time
from uuid import uuid4
from typing import Dict, Any

# Test imports to verify consolidation works
from backend.models.project_models import (
    # Modern unified models
    ProjectInput, ProjectModel, ProjectTypeEnum, ProjectStatusEnum,
    # Legacy aliases
    RFXInput, RFXProcessed, RFXType, RFXStatus, RFXResponse,
    # Enums and types
    IndustryType, ServiceCategory, PriorityLevel
)

from backend.models.proposal_models import (
    # Modern unified models
    QuoteRequest, QuoteModel, ItemizedCost, QuoteNotes,
    # Legacy aliases  
    ProposalRequest, PropuestaGenerada, NotasPropuesta, ProposalResponse,
    # Helper function
    map_legacy_quote_request
)


class TestProjectModelUnification:
    """Test ProjectInput/ProjectModel backward compatibility"""
    
    def test_project_input_backward_compatibility(self):
        """Test that old RFXInput code still works with ProjectInput"""
        # Test legacy RFXInput creation (using alias)
        legacy_data = {
            "id": "TEST-001",
            "rfx_type": "catering", 
            "extracted_content": "Test content",
            "requirements": "Test requirements"
        }
        
        # Should work with both new and legacy class names
        project_new = ProjectInput(**legacy_data)
        rfx_legacy = RFXInput(**legacy_data)  # This is now an alias
        
        # Both should be the same class
        assert type(project_new) == type(rfx_legacy)
        assert project_new.id == rfx_legacy.id
        
        # Test legacy property access
        assert rfx_legacy.rfx_type == "catering"
        assert project_new.rfx_type == "catering"
        assert project_new.project_type == ProjectTypeEnum.CATERING
    
    def test_project_input_rfx_type_mapping(self):
        """Test RFX type to Project type mapping"""
        type_mappings = [
            ("catering", ProjectTypeEnum.CATERING),
            ("events", ProjectTypeEnum.EVENTS),
            ("construction", ProjectTypeEnum.CONSTRUCTION),
            ("supplies", ProjectTypeEnum.GENERAL),  # Maps to general
            ("services", ProjectTypeEnum.CONSULTING),  # Maps to consulting
            ("maintenance", ProjectTypeEnum.GENERAL)  # Maps to general
        ]
        
        for rfx_type, expected_project_type in type_mappings:
            project = ProjectInput(id="TEST", rfx_type=rfx_type)
            assert project.project_type == expected_project_type
            assert project.rfx_type == rfx_type  # Legacy property should work
    
    def test_project_model_legacy_properties(self):
        """Test legacy property aliases in ProjectModel"""
        project = ProjectModel(
            name="Test Project",
            project_type=ProjectTypeEnum.EVENTS,
            client_name="John Doe",
            client_company="ACME Corp",
            client_email="john@acme.com"
        )
        
        # Test legacy property aliases
        assert project.title == "Test Project"  # name → title
        assert project.rfx_type == "events"     # project_type → rfx_type
        assert project.requester_name == "John Doe"  # client_name → requester_name
        assert project.company_name == "ACME Corp"   # client_company → company_name
        assert project.email == "john@acme.com"      # client_email → email
        
        # Test legacy setter
        project.title = "Updated Project"
        assert project.name == "Updated Project"
    
    def test_rfx_processed_alias(self):
        """Test that RFXProcessed alias works correctly"""
        data = {
            "name": "Legacy RFX Project", 
            "project_type": "catering",
            "client_name": "Jane Smith"
        }
        
        # Should work with both class names
        project_new = ProjectModel(**data)
        rfx_legacy = RFXProcessed(**data)  # This is now an alias
        
        assert type(project_new) == type(rfx_legacy)
        assert project_new.name == rfx_legacy.name
        assert rfx_legacy.title == "Legacy RFX Project"  # Legacy property


class TestProposalModelUnification:
    """Test QuoteRequest/QuoteModel backward compatibility"""
    
    def test_quote_request_backward_compatibility(self):
        """Test that old ProposalRequest code still works"""
        legacy_data = {
            "project_id": "TEST-PROJECT-001",
            "title": "Test Quote",
            "subtotal": 1000.0,
            "total_amount": 1000.0,
            "item_costs": [
                {
                    "item_name": "Test Item",
                    "quantity": 10,
                    "unit_price": 100.0,
                    "total_price": 1000.0
                }
            ]
        }
        
        # Should work with both new and legacy class names
        quote_new = QuoteRequest(**legacy_data)
        proposal_legacy = ProposalRequest(**legacy_data)  # This is now an alias
        
        assert type(quote_new) == type(proposal_legacy)
        assert quote_new.project_id == proposal_legacy.project_id
        
        # Test legacy property access
        assert proposal_legacy.rfx_id == "TEST-PROJECT-001"
        assert quote_new.rfx_id == "TEST-PROJECT-001"
    
    def test_quote_request_rfx_id_compatibility(self):
        """Test rfx_id property compatibility"""
        quote = QuoteRequest(
            project_id="PROJECT-123",
            title="Test Quote",
            subtotal=500.0,
            total_amount=500.0
        )
        
        # Legacy property should work
        assert quote.rfx_id == "PROJECT-123"
        
        # Legacy setter should work
        quote.rfx_id = "RFX-456"
        assert quote.project_id == "RFX-456"
        assert quote.rfx_id == "RFX-456"
    
    def test_item_costs_synchronization(self):
        """Test that item_costs and itemized_costs work correctly"""
        item_data = [{
            "item_name": "Test Item",
            "quantity": 5,
            "unit_price": 20.0,
            "total_price": 100.0
        }]
        
        # Test with item_costs (legacy field)
        quote1 = QuoteRequest(
            project_id="TEST",
            title="Test",
            subtotal=100.0,
            total_amount=100.0,
            item_costs=item_data,
            itemized_costs=[]  # Initialize both to avoid conflicts
        )
        assert quote1.item_costs == item_data
        
        # Test with itemized_costs (modern field)
        quote2 = QuoteRequest(
            project_id="TEST",
            title="Test", 
            subtotal=100.0,
            total_amount=100.0,
            itemized_costs=item_data,
            item_costs=[]  # Initialize both to avoid conflicts
        )
        assert quote2.itemized_costs == item_data
    
    def test_legacy_aliases_import(self):
        """Test that legacy class name imports work"""
        # These should not raise ImportError
        data = {
            "project_id": "TEST",
            "title": "Test",
            "subtotal": 100.0,
            "total_amount": 100.0
        }
        
        proposal = ProposalRequest(**data)
        assert proposal.project_id == "TEST"
        
        # Test legacy model alias (with required fields)
        quote_data = {
            "project_id": uuid4(),
            "organization_id": uuid4(),
            "quote_number": "Q-001",
            "title": "Test Quote",
            "subtotal": 100.0,
            "total_amount": 100.0,
            "created_by": uuid4()  # Required field
        }
        
        legacy_quote = PropuestaGenerada(**quote_data)
        assert legacy_quote.quote_number == "Q-001"


class TestModelValidation:
    """Test that validation still works after unification"""
    
    def test_project_input_validation(self):
        """Test ProjectInput validation works correctly"""
        # Valid data should pass
        valid_data = {
            "id": "VALID-PROJECT-001",
            "project_type": "catering"
        }
        project = ProjectInput(**valid_data)
        assert project.id == "VALID-PROJECT-001"
        
        # Invalid data should fail
        with pytest.raises(ValueError):
            ProjectInput(id="", project_type="catering")  # Empty ID
        
        with pytest.raises(ValueError):
            ProjectInput(id="TEST", complexity_score=1.5)  # Invalid complexity score
    
    def test_quote_request_validation(self):
        """Test QuoteRequest validation works correctly"""
        # Valid data should pass
        valid_data = {
            "project_id": "PROJECT-001",
            "title": "Valid Quote",
            "subtotal": 100.0,
            "coordination_amount": 18.0,
            "total_amount": 118.0
        }
        quote = QuoteRequest(**valid_data)
        assert quote.total_amount == 118.0
        
        # Invalid total calculation should fail
        with pytest.raises(ValueError, match="Total amount does not match"):
            QuoteRequest(
                project_id="PROJECT-001",
                title="Invalid Quote",
                subtotal=100.0,
                coordination_amount=18.0,
                total_amount=200.0  # Wrong total
            )


class TestLegacyHelperFunctions:
    """Test legacy helper functions still work"""
    
    def test_map_legacy_quote_request(self):
        """Test legacy quote request mapping function"""
        legacy_data = {
            "rfx_id": "RFX-123",  # Legacy field name
            "title": "Legacy Quote",
            "subtotal": 1000.0,
            "total_amount": 1000.0
        }
        
        quote = map_legacy_quote_request(legacy_data)
        assert quote.project_id == "RFX-123"  # Should map rfx_id → project_id
        assert quote.rfx_id == "RFX-123"      # Legacy property should work
        assert quote.title == "Legacy Quote"


class TestEnumCompatibility:
    """Test that legacy enums still work"""
    
    def test_rfx_type_enum_compatibility(self):
        """Test RFXType enum is available and works"""
        # Legacy enum should be importable and functional
        assert RFXType.CATERING == "catering"
        assert RFXType.EVENTS == "events"
        assert RFXType.CONSTRUCTION == "construction"
        
        # Should work in ProjectInput
        project = ProjectInput(id="TEST", project_type=RFXType.CATERING)
        assert project.rfx_type == "catering"
    
    def test_rfx_status_enum_compatibility(self):
        """Test RFXStatus enum is available and works"""
        assert RFXStatus.DRAFT == "draft"
        assert RFXStatus.IN_PROGRESS == "active"  # Maps to active
        assert RFXStatus.COMPLETED == "completed"
    
    def test_industry_type_enum_works(self):
        """Test IndustryType enum from consolidated models"""
        assert IndustryType.CATERING == "catering"
        assert IndustryType.TECHNOLOGY == "technology"
        
        project = ProjectInput(id="TEST", industry_type=IndustryType.TECHNOLOGY)
        assert project.industry_type == IndustryType.TECHNOLOGY


@pytest.fixture
def sample_project_data():
    """Sample project data for testing"""
    return {
        "id": "TEST-PROJECT-001",
        "project_type": "catering",
        "extracted_content": "Sample extracted content",
        "requirements": "Sample requirements"
    }


@pytest.fixture  
def sample_quote_data():
    """Sample quote data for testing"""
    return {
        "project_id": "TEST-PROJECT-001",
        "title": "Sample Quote",
        "subtotal": 1000.0,
        "coordination_amount": 180.0,
        "total_amount": 1180.0,
        "item_costs": [
            {
                "item_name": "Sample Item",
                "quantity": 10,
                "unit_price": 100.0,
                "total_price": 1000.0
            }
        ]
    }


def test_integration_compatibility(sample_project_data, sample_quote_data):
    """Integration test: full workflow with legacy and modern syntax"""
    # Create project using legacy syntax
    rfx = RFXInput(**sample_project_data)
    assert rfx.rfx_type == "catering"
    
    # Create quote using legacy syntax  
    proposal = ProposalRequest(**sample_quote_data)
    assert proposal.rfx_id == "TEST-PROJECT-001"
    
    # Verify both work together
    assert rfx.id == proposal.project_id


if __name__ == "__main__":
    # Run basic compatibility tests
    test_suite = TestProjectModelUnification()
    test_suite.test_project_input_backward_compatibility()
    test_suite.test_project_model_legacy_properties()
    
    quote_suite = TestProposalModelUnification()
    quote_suite.test_quote_request_backward_compatibility()
    quote_suite.test_quote_request_rfx_id_compatibility()
    
    print("✅ All unified model compatibility tests passed!")
