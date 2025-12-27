import pytest
from src.backend.orchestrator import Layer1RegexScrubber, PIIPlaceholder

@pytest.fixture
def scrubber():
    return Layer1RegexScrubber()

def test_ssn_scrubbing(scrubber):
    text = "My SSN is 123-45-6789."
    scrubbed, counts = scrubber.scrub(text)
    assert PIIPlaceholder.SSN.value in scrubbed
    assert counts["SSN"] == 1
    assert "123-45-6789" not in scrubbed

def test_email_scrubbing(scrubber):
    text = "Contact me at john.doe@example.com"
    scrubbed, counts = scrubber.scrub(text)
    assert PIIPlaceholder.EMAIL.value in scrubbed
    assert counts["Email"] == 1
    assert "john.doe@example.com" not in scrubbed

def test_account_number_scrubbing(scrubber):
    text = "Account ending in 12345678"
    scrubbed, counts = scrubber.scrub(text)
    assert PIIPlaceholder.ACCOUNT_NUMBER.value in scrubbed
    assert counts["Account_Number_Suffix"] == 1

def test_currency_scrubbing(scrubber):
    text = "The total is $1,250,000.00"
    scrubbed, counts = scrubber.scrub(text)
    assert PIIPlaceholder.CURRENCY_VALUE.value in scrubbed
    assert counts["Currency"] == 1

def test_multiple_detections(scrubber):
    text = "John (SSN 123-45-6789) has $5,000 in account 9988."
    scrubbed, counts = scrubber.scrub(text)
    assert counts["SSN"] == 1
    assert counts["Currency"] == 1
    assert counts["Account_Number_Suffix"] == 1
