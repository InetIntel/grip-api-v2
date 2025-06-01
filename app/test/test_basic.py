import pytest
from app import create_app  # assuming you have a factory pattern

@pytest.fixture
def client():
    app = create_app({
        "TESTING": True,
        "CONFIG_PATH": "instance/config.toml"
    })
    with app.test_client() as client:
        yield client

def test_api_endpoint(client):
    response = client.get("/your-endpoint")
    assert response.status_code == 200