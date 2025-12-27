import pytest
from fastapi.testclient import TestClient
from src.backend.app import app

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] is True
    assert "operational" in response.json()["message"]

def test_search_endpoint():
    # Searching for 'Smith' which we know is in the sample data
    response = client.get("/api/v1/search?q=Smith")
    assert response.status_code == 200
    assert response.json()["status"] is True
    assert len(response.json()["data"]) > 0

def test_customer_not_found():
    response = client.get("/api/v1/customer/NonExistentUser123")
    assert response.status_code == 200 # We return 200 with status=False in our utility
    assert response.json()["status"] is False
    assert "not found" in response.json()["message"].lower()
