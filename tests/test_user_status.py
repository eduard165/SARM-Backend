from types import SimpleNamespace
from unittest.mock import Mock
from uuid import UUID
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import Identity, get_identity
from app.db.client import admin_client
from app.api.auth import login
from app.schemas.accounts import LoginRequest

SUPER = Identity(UUID(int=1), 'superadministrador', 'superadmin')
ADMIN = Identity(UUID(int=2), 'administrador', 'admin')
USER = Identity(UUID(int=3), 'usuario', 'usuario')
TARGET, BUSINESS, FOREIGN = [str(UUID(int=i)) for i in (4, 10, 11)]
PATH = f'/usuarios/{TARGET}/estado'


class DbError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__('DETALLE_SQL_PRIVADO')


@pytest.fixture
def api():
    db = Mock()
    db.rpc.return_value.execute.return_value.data = {'usuario_id': TARGET, 'negocio_id': BUSINESS, 'estado_membresia': 'suspendido', 'cambiado': True}
    def table(name):
        q = Mock()
        q.select.return_value = q.eq.return_value = q.limit.return_value = q
        q.execute.return_value.data = ([{'negocio_id': BUSINESS, 'estado_membresia': 'activo'}] if name == 'usuario_negocios' else [{'estado_registro': 'activo'}])
        return q
    db.table.side_effect = table
    app.dependency_overrides[admin_client] = lambda: db
    app.dependency_overrides[get_identity] = lambda: SUPER
    with TestClient(app) as c:
        yield c, db
    app.dependency_overrides.clear()


def body(**kw):
    return {'negocio_id': BUSINESS, 'estado': 'suspendido', 'motivo': 'Baja temporal', **kw}


def test_super_suspends_with_verified_actor(api):
    c, db = api
    assert c.patch(PATH, json=body()).status_code == 200
    assert db.rpc.call_args.args == ('sarm_cambiar_estado_usuario', {'p_actor': str(SUPER.id), 'p_usuario': TARGET, 'p_negocio': BUSINESS, 'p_estado': 'suspendido', 'p_motivo': 'Baja temporal'})


def test_admin_business_inferred(api):
    c, db = api
    app.dependency_overrides[get_identity] = lambda: ADMIN
    data = body(); del data['negocio_id']
    assert c.patch(PATH, json=data).status_code == 200
    assert db.rpc.call_args.args[1]['p_negocio'] == BUSINESS


def test_admin_foreign_denied(api):
    c, db = api
    app.dependency_overrides[get_identity] = lambda: ADMIN
    assert c.patch(PATH, json=body(negocio_id=FOREIGN)).status_code == 403
    db.rpc.assert_not_called()


def test_user_cannot_change_access(api):
    c, db = api
    app.dependency_overrides[get_identity] = lambda: USER
    assert c.patch(PATH, json=body()).status_code == 403
    db.rpc.assert_not_called()


def test_no_self_suspension(api):
    c, db = api
    assert c.patch(f'/usuarios/{SUPER.id}/estado', json=body()).status_code == 403
    db.rpc.assert_not_called()


@pytest.mark.parametrize('data', [body(estado='borrado'), body(motivo='   '), body(motivo='a'*1001), body(p_actor=TARGET), body(negocio_id='no-uuid')])
def test_invalid_status_payload(api, data):
    c, db = api
    assert c.patch(PATH, json=data).status_code == 422
    db.rpc.assert_not_called()


def test_super_requires_business(api):
    c, db = api
    data=body(); del data['negocio_id']
    assert c.patch(PATH, json=data).status_code == 422
    db.rpc.assert_not_called()


def test_reactivate_and_idempotent_result(api):
    c, db = api
    db.rpc.return_value.execute.return_value.data.update(estado_membresia='activo', cambiado=False)
    r=c.patch(PATH, json=body(estado='activo'))
    assert r.status_code == 200
    assert r.json()['cambiado'] is False
    assert db.rpc.call_args.args[1]['p_estado']=='activo'


@pytest.mark.parametrize('code,status', [('42501',403), ('P0002',404), ('23514',422), ('PGRST202',503), ('40001',409), ('other',502)])
def test_status_safe_errors(api, code, status):
    c, db = api
    db.rpc.return_value.execute.side_effect=DbError(code)
    r=c.patch(PATH, json=body())
    assert r.status_code==status
    assert 'DETALLE_SQL_PRIVADO' not in r.text


def identity_db(enabled):
    db=Mock()
    def table(name):
        q=Mock(); q.select.return_value=q.eq.return_value=q.limit.return_value=q
        q.execute.return_value.data=([{'id': str(USER.id), 'nombre_usuario':'usuario', 'bloqueo_global':False, 'rol_id':TARGET}] if name=='usuarios' else [{'codigo':'usuario'}])
        return q
    db.table.side_effect=table
    if enabled:
        db.rpc.return_value.execute.return_value.data={'id':str(USER.id),'nombre_usuario':'usuario','rol':'usuario','negocios':[]}
    else:
        db.rpc.return_value.execute.side_effect=DbError('42501')
    auth=Mock(); auth.auth.get_user.return_value.user=SimpleNamespace(id=str(USER.id))
    return db,auth


def test_live_token_rejected_after_suspension():
    db,auth=identity_db(False)
    with pytest.raises(HTTPException) as exc:
        get_identity('jwt-valido', auth, db)
    assert exc.value.status_code==403
    assert db.rpc.call_args.args[1]=={'p_usuario':str(USER.id)}


def test_same_live_token_accepted_after_reactivation():
    db,auth=identity_db(True)
    assert get_identity('jwt-valido',auth,db).id==USER.id


def test_access_check_missing_migration_fails_closed():
    db,auth=identity_db(True)
    db.rpc.return_value.execute.side_effect=DbError('PGRST202')
    with pytest.raises(HTTPException) as exc:
        get_identity('jwt-valido',auth,db)
    assert exc.value.status_code==503


def test_login_denies_account_without_active_access(monkeypatch):
    db=Mock(); q=Mock(); q.select.return_value=q.eq.return_value=q.limit.return_value=q
    q.execute.return_value.data=[{'id': str(USER.id),'bloqueo_global':False}]
    db.table.return_value=q
    db.auth.admin.get_user_by_id.return_value.user=SimpleNamespace(email='local@example.invalid')
    client=Mock(); client.auth.sign_in_with_password.return_value.session=SimpleNamespace(access_token='secret',refresh_token='secret',expires_in=3600)
    monkeypatch.setattr('app.api.auth.create_client',lambda *args:client)
    db.rpc.return_value.execute.return_value.data=False
    with pytest.raises(HTTPException) as exc:
        login(LoginRequest(nombre_usuario='usuario',password='testing-password-only'),db)
    assert exc.value.status_code==403


def test_status_requires_token():
    with TestClient(app) as c:
        assert c.patch(PATH,json=body()).status_code==401
