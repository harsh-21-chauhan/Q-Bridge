"""No real model requests: fake transport tests the complete tool-call loop."""
import json
from pathlib import Path
import pytest
pytest.importorskip('fastapi')
pytest.importorskip('httpx')
from fastapi.testclient import TestClient
from backend.app.main import create_app
from backend.app.config import Settings
from backend.app.services.assistant_service import AssistantService

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.delenv('QBRIDGE_ASSISTANT_MODE', raising=False)
    monkeypatch.delenv('QBRIDGE_LIVE_AUTHORIZED', raising=False)
    monkeypatch.delenv('QBRIDGE_ASSISTANT_DISABLED', raising=False)
    app = create_app(Settings(tmp_path / 'experiments', Path(__file__).resolve().parents[1] / 'research'))
    with TestClient(app) as client:
        yield client

def body(client, **extra):
    record = client.post('/api/experiments', json={}).json()
    return dict(experiment_id=record['experiment_id'], question='Why?', **extra)

def test_mock_has_no_network_and_no_truth(client, monkeypatch):
    import httpx
    monkeypatch.setattr(httpx.HTTPTransport, 'handle_request', lambda *a, **k: pytest.fail('Network attempted'))
    result = client.post('/api/assistant/ask', json=body(client, compare_shots=50))
    assert result.status_code == 200
    data = result.json()
    assert data['mode'] == 'mock'
    assert data['usage']['provider_calls'] == 0
    assert data['trace'][0]['evidence']['current']['shots'] == 50
    for secret in ('truth_mode', 'true_error_rates', 'oracle_loss', 'evaluation'):
        assert secret not in result.text

def test_live_requires_authorization_and_key(client, monkeypatch):
    monkeypatch.setenv('QBRIDGE_ASSISTANT_MODE', 'live')
    response = client.post('/api/assistant/ask', json=body(client))
    assert response.status_code == 503
    assert client.get('/api/assistant/status').json()['provider_calls'] == 0

def test_disable_persists(client):
    query = body(client)
    client.post('/api/assistant/disable')
    old = client.app.state.assistant_service
    client.app.state.assistant_service = AssistantService(old.experiments, old.directory)
    assert client.post('/api/assistant/ask', json=query).status_code == 503

def test_budget_is_durable_and_atomic(client):
    service = client.app.state.assistant_service
    service.BUDGET_CENTS = 50
    service.reserve(); service.reserve()
    with pytest.raises(Exception) as error:
        service.reserve()
    assert error.value.status_code == 429
    restarted = AssistantService(service.experiments, service.directory)
    assert restarted.status()['reserved_usd'] == .5

def install_transport(monkeypatch, replies):
    import httpx
    sent = []
    class Transport:
        def __init__(self, **kwargs):
            assert kwargs['trust_env'] is False
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self, url, **kwargs):
            assert url == 'https://api.meta.ai/v1/chat/completions'
            sent.append(kwargs['json'])
            reply = replies.pop(0)
            if isinstance(reply, Exception): raise reply
            return httpx.Response(200, json=reply, request=httpx.Request('POST', url))
    monkeypatch.setattr(httpx, 'Client', Transport)
    monkeypatch.setenv('QBRIDGE_ASSISTANT_MODE', 'live')
    monkeypatch.setenv('QBRIDGE_LIVE_AUTHORIZED', 'yes')
    monkeypatch.setenv('MODEL_API_KEY', 'test-secret-never-real')
    return sent

def tool_reply(name='get_experiment_evidence', arguments='{}'):
    return {'choices':[{'finish_reason':'tool_calls','message':{'role':'assistant','content':None,'tool_calls':[{'id':'call-1','type':'function','function':{'name':name,'arguments':arguments}}]}}]}

def test_live_protocol_with_fake_provider(client, monkeypatch):
    query = body(client)
    sent = install_transport(monkeypatch, [tool_reply(), {'choices':[{'finish_reason':'stop','message':{'role':'assistant','content':'Evidence explanation'}}], 'usage':{'prompt_tokens':500,'completion_tokens':20}}])
    response = client.post('/api/assistant/ask', json=query)
    assert response.status_code == 200
    assert len(sent) == 2
    assert sent[1]['messages'][-1]['tool_call_id'] == 'call-1'
    assert sent[1]['tool_choice'] == 'none'
    assert response.json()['usage']['reserved_usd'] == .5
    assert 'test-secret' not in response.text
    assert 'truth_mode' not in json.dumps(sent)

@pytest.mark.parametrize('reply', [tool_reply('delete_file'), tool_reply(arguments='{"path":"secret"}'), RuntimeError('test-secret-never-real')])
def test_bad_tool_or_failure_never_retries(client, monkeypatch, reply):
    query = body(client)
    sent = install_transport(monkeypatch, [reply])
    response = client.post('/api/assistant/ask', json=query)
    assert response.status_code == 502
    assert len(sent) == 1
    assert 'test-secret' not in response.text
    assert client.get('/api/assistant/status').json()['reserved_usd'] == .25

def test_emergency_stop_between_provider_steps(client, monkeypatch):
    query = body(client)
    service = client.app.state.assistant_service
    original_tool = service.tool
    def stop_after_tool(*args):
        evidence = original_tool(*args)
        service.disable()
        return evidence
    monkeypatch.setattr(service, 'tool', stop_after_tool)
    sent = install_transport(monkeypatch, [tool_reply()])
    assert client.post('/api/assistant/ask', json=query).status_code == 503
    assert len(sent) == 1

def test_payload_limit_blocks_before_reservation(client, monkeypatch):
    query = body(client)
    client.app.state.assistant_service.MAX_INPUT_BYTES = 10
    sent = install_transport(monkeypatch, [])
    assert client.post('/api/assistant/ask', json=query).status_code == 413
    assert not sent
    assert client.get('/api/assistant/status').json()['provider_calls'] == 0

def test_rate_limit_survives_service_restart(client):
    old = client.app.state.assistant_service
    for _ in range(4): old.reserve()
    new = AssistantService(old.experiments, old.directory)
    with pytest.raises(Exception) as error: new.reserve()
    assert error.value.status_code == 429
