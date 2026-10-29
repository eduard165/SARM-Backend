from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json()['estado'] == 'ok'


def test_docs():
    assert client.get('/docs').status_code == 200


def test_protected_without_token():
    assert client.get('/auth/me').status_code == 401
    assert client.get('/negocios').status_code == 401
