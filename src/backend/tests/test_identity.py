import pytest
from src.backend.relationship_engine.identity_resolution import (
    name_similarity, 
    address_similarity, 
    string_similarity,
    IdentityResolutionEngine,
    ConfidenceLevel
)

def test_string_similarity():
    assert string_similarity("John", "John") == 1.0
    assert string_similarity("John", "Jon") > 0.5
    assert string_similarity("John", "Apple") < 0.3

def test_name_similarity():
    name1 = {"first_name": "John", "last_name": "Smith", "full_name": "John Smith"}
    name2 = {"first_name": "Jonathan", "last_name": "Smith", "full_name": "Jonathan Smith"}
    
    score = name_similarity(name1, name2)
    assert score >= 0.85  # Nickname/Partial match

def test_address_similarity():
    addr1 = {"zip5": "15213", "street_line1": "123 Main St", "city": "Pittsburgh"}
    addr2 = {"zip5": "15213", "street_line1": "123 Main Street", "city": "Pittsburgh"}
    # With city matching and zip matching, it should be higher
    assert address_similarity(addr1, addr2) > 0.7

def test_match_score_calculation():
    engine = IdentityResolutionEngine()
    e1 = {
        "source_id": "CON-001",
        "source_system": "CONSUMER",
        "name": {"first_name": "John", "middle_name": "R", "last_name": "Smith", "full_name": "John R Smith"},
        "tax_id_last4": "1234",
        "date_of_birth": "1980-01-01",
        "address": {"zip5": "15213", "street_line1": "123 Main St", "city": "Pittsburgh", "full_address": "123 Main St, Pittsburgh, PA 15213"},
        "entity_type": "PERSON"
    }
    e2 = {
        "source_id": "WM-001",
        "source_system": "WEALTH",
        "name": {"first_name": "John", "middle_name": "R", "last_name": "Smith", "full_name": "John R Smith"},
        "tax_id_last4": "1234",
        "date_of_birth": "1980-01-01",
        "address": {"zip5": "15213", "street_line1": "123 Main St", "city": "Pittsburgh", "full_address": "123 Main St, Pittsburgh, PA 15213"},
        "entity_type": "PERSON"
    }
    
    score = engine.calculate_match_score(e1, e2)
    # Name match will now be 1.0
    # 0.4 + 0.2 + 0.15 + 0.15 = 0.9
    assert score.total_score >= 0.9
    assert score.confidence_level in ["MEDIUM", "HIGH"]
