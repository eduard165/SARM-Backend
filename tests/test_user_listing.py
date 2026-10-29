from types import SimpleNamespace
from unittest.mock import Mock
from uuid import UUID
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import Identity, get_identity
from app.db.client import admin_client

SUPER = Identity(UUID(int=1), 'superadministrador', 'superadmin')
ADMIN = Identity(UUID(int=2), 'administrador', 'admin_a')
OPERATIVE = Identity(UUID(int=3), 'usuario', 'operativo_a')
BUSINESS, FOREIGN = str(UUID(int=10)), str(UUID(int=11))
EMPTY = {'items': [], 'total': 0, 'pagina': 1, 'tamano_pagina': 20, 'total_paginas': 0}


@pytest.fixture
def api():
    db = Mock()
    db.rpc.return_value.execute.return_value = SimpleNamespace(data=EMPTY)
    app.dependency_overrides[admin_client] = lambda: db
    app.dependency_overrides[get_identity] = lambda: SUPER
    with TestClient(app) as client:
        yield client, db
    app.dependency_overrides.clear()


def assigned(db, memberships=None, state='activo'):
    rows = memberships if memberships is not None else [{'negocio_id': BUSINESS, 'estado_membresia': 'activo'}]
    def table(name):
        query = Mock()
        query.select.return_value = query
        query.eq.return_value = query
        query.limit.return_value = query
        query.execute.return_value = SimpleNamespace(data=rows if name == 'usuario_negocios' else [{'estado_registro': state}])
        return query
    db.table.side_effect = table


def test_list_rejects_missing_token():
    with TestClient(app) as client:
        assert client.get('/usuarios').status_code == 401


def test_superadmin_uses_verified_actor(api):
    client, db = api
    assert client.get('/usuarios').json() == EMPTY
    params = db.rpc.call_args.args[1]
    assert params['p_actor'] == str(SUPER.id)
    assert params['p_negocio'] is None


def test_filters_are_values_not_query_fragments(api):
    client, db = api
    response = client.get('/usuarios', params={'q': " O'Brien,_% ", 'rol': 'usuario', 'negocio_id': BUSINESS, 'estado': 'activo', 'pagina': 2, 'tamano_pagina': 10})
    assert response.status_code == 200
    assert db.rpc.call_args.args[1] == {'p_actor': str(SUPER.id), 'p_busqueda': "O'Brien,_%", 'p_rol': 'usuario', 'p_negocio': BUSINESS, 'p_estado': 'activo', 'p_pagina': 2, 'p_tamano': 10}


def test_operator_rejected_before_queries(api):
    client, db = api
    app.dependency_overrides[get_identity] = lambda: OPERATIVE
    assert client.get('/usuarios').status_code == 403
    db.rpc.assert_not_called()
    db.table.assert_not_called()


def test_admin_scope_is_automatic(api):
    client, db = api
    app.dependency_overrides[get_identity] = lambda: ADMIN
    assigned(db)
    assert client.get('/usuarios').status_code == 200
    assert db.rpc.call_args.args[1]['p_negocio'] == BUSINESS


def test_admin_cannot_switch_business(api):
    client, db = api
    app.dependency_overrides[get_identity] = lambda: ADMIN
    assigned(db)
    assert client.get('/usuarios', params={'negocio_id': FOREIGN}).status_code == 403
    db.rpc.assert_not_called()


@pytest.mark.parametrize('role', ['superadministrador', 'administrador'])
def test_admin_cannot_request_privileged_roles(api, role):
    client, db = api
    app.dependency_overrides[get_identity] = lambda: ADMIN
    assigned(db)
    assert client.get('/usuarios', params={'rol': role}).status_code == 403
    db.rpc.assert_not_called()


@pytest.mark.parametrize('rows', [[], [{'negocio_id': BUSINESS, 'estado_membresia': 'suspendido'}], [{'negocio_id': BUSINESS, 'estado_membresia': 'activo'}, {'negocio_id': FOREIGN, 'estado_membresia': 'activo'}]])
def test_invalid_admin_memberships_rejected(api, rows):
    client, db = api
    app.dependency_overrides[get_identity] = lambda: ADMIN
    assigned(db, rows)
    assert client.get('/usuarios').status_code == 403
    db.rpc.assert_not_called()


def test_suspended_admin_business_rejected(api):
    client, db = api
    app.dependency_overrides[get_identity] = lambda: ADMIN
    assigned(db, state='suspendido')
    assert client.get('/usuarios').status_code == 403
    db.rpc.assert_not_called()


@pytest.mark.parametrize('query', [{'pagina':0}, {'tamano_pagina':101}, {'tamano_pagina':0}, {'pagina':1000001}, {'q':'a'*101}, {'rol':'root'}, {'estado':'borrado'}, {'negocio_id':'not-uuid'}])
def test_invalid_filters_rejected(api, query):
    client, db = api
    assert client.get('/usuarios', params=query).status_code == 422
    db.rpc.assert_not_called()


class DbError(Exception):
    def __init__(self, code):
        super().__init__('detalle interno que no debe exponerse')
        self.code = code


@pytest.mark.parametrize('code,status', [('42501',403),('22023',422),('PGRST202',503),('42883',503),('other',502)])
def test_database_errors_are_safe(api, code, status):
    client, db = api
    db.rpc.return_value.execute.side_effect = DbError(code)
    response = client.get('/usuarios')
    assert response.status_code == status
    assert 'detalle interno' not in response.text


def test_response_drops_unexpected_secrets(api):
    client, db = api
    db.rpc.return_value.execute.return_value.data = {**EMPTY, 'password': 'secret', 'access_token': 'secret'}
    response = client.get('/usuarios')
    assert response.status_code == 200
    assert response.json() == EMPTY


def test_existing_creation_routes_preserved():
    paths = app.openapi()['paths']
    assert 'post' in paths['/usuarios'] and 'get' in paths['/usuarios']
    assert 'post' in paths['/administradores']
    assert 'post' in paths['/negocios']
