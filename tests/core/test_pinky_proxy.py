import importlib
import os

from fastapi.testclient import TestClient

REQUIRED_VARS = {
    "AZURE_SQL_SERVER": "stub.server.local",
    "AZURE_SQL_PORT": "1433",
    "AZURE_SQL_USER": "test",
    "AZURE_SQL_PASSWORD": "secret",
    "AZURE_SQL_DATABASE": "testdb",
}
for k,v in REQUIRED_VARS.items(): os.environ.setdefault(k,v)

class FakeUserStore:
    def __init__(self, main):
        self.users={"techno":{"id":2,"username":"Techno","role":main.ROLE_ADMIN,"password_hash":None}}
    def get_user_by_username(self, username):
        u=self.users.get(username.lower()); return dict(u) if u else None
    def set_user_password_hash(self, user_id, password_hash):
        self.users['techno']['password_hash']=password_hash
    def record_user_login(self, user_id): return None

class Resp:
    def __init__(self, ok=True, status=200, payload=None, text=''):
        self.ok=ok; self.status_code=status; self._payload=payload if payload is not None else {}; self.text=text; self.headers={'content-type':'application/json'}
    def json(self): return self._payload


def load_main(monkeypatch):
    main=importlib.import_module('main')
    monkeypatch.setattr(main,'db_manager',FakeUserStore(main))
    return main

def login_admin(client):
    assert client.post('/login',json={"username":"Techno","password":"","new_password":"x"}).status_code==204


def test_pinky_chat_proxy(monkeypatch):
    os.environ['PINKY_API_KEY']='abc'
    main=load_main(monkeypatch)
    def fake_request(method,url,headers,json,params,timeout):
        assert headers['Authorization']=='Bearer abc'
        assert url.endswith('/api/chat')
        return Resp(payload={'response':'hi','conversation_id':'c1'})
    monkeypatch.setattr(main.requests,'request',fake_request)
    c=TestClient(main.app); login_admin(c)
    r=c.post('/api/pinky/chat',json={'message':'hello'})
    assert r.status_code==200
    assert r.json()['conversation_id']=='c1'


def test_pinky_health_no_auth(monkeypatch):
    main=load_main(monkeypatch)
    def fake_request(method,url,headers,json,params,timeout):
        assert 'Authorization' not in headers
        return Resp(payload={'status':'ok'})
    monkeypatch.setattr(main.requests,'request',fake_request)
    c=TestClient(main.app); login_admin(c)
    assert c.get('/api/pinky/health').status_code==200


def test_pinky_config_missing_key(monkeypatch):
    os.environ.pop('PINKY_API_KEY',None)
    main=load_main(monkeypatch)
    c=TestClient(main.app); login_admin(c)
    r=c.get('/api/pinky/status')
    assert r.status_code==503
