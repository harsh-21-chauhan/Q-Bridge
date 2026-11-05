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
    assert sent[0]['max_completion_tokens'] == 1000
    assert sent[1]['max_completion_tokens'] == 4096
    assert sent[0]['tool_choice'] == 'auto'
    assert 'tools' in sent[0]
    assert 'tool_choice' not in sent[1]
    assert 'tools' not in sent[1]
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

def test_resume_preserves_budget_authorization_and_mode(client):
    service = client.app.state.assistant_service
    service.reserve()
    client.post('/api/assistant/disable')
    result = client.post('/api/assistant/resume').json()
    assert result['disabled'] is False
    assert result['reserved_usd'] == .25
    assert result['provider_calls'] == 1
    assert result['mode'] == 'mock'
    assert result['live_authorized'] is False
    assert AssistantService(service.experiments, service.directory).status()['disabled'] is False

def test_resume_cannot_override_server_disable_or_running_request(client, monkeypatch):
    client.post('/api/assistant/disable')
    monkeypatch.setenv('QBRIDGE_ASSISTANT_DISABLED', 'true')
    assert client.post('/api/assistant/resume').status_code == 409
    monkeypatch.delenv('QBRIDGE_ASSISTANT_DISABLED')
    service = client.app.state.assistant_service
    with service.operation():
        assert client.post('/api/assistant/resume').status_code == 409
        assert service.status()['paused'] is True
    assert client.post('/api/assistant/resume').status_code == 200

def test_local_fallback_is_read_only_available_when_paused_and_never_calls_provider(client, monkeypatch):
    query = body(client)
    service = client.app.state.assistant_service
    monkeypatch.setenv('QBRIDGE_ASSISTANT_MODE', 'live')
    monkeypatch.setenv('QBRIDGE_LIVE_AUTHORIZED', 'yes')
    monkeypatch.setattr(service, 'completion', lambda *a: pytest.fail('Model call attempted'))
    monkeypatch.setattr(service.experiments, 'create', lambda *a: pytest.fail('Unexpected calculation'))
    client.post('/api/assistant/disable')
    response = client.post('/api/assistant/explain', json={'experiment_id':query['experiment_id']})
    assert response.status_code == 200
    assert response.json()['mode'] == 'local'
    assert 'same final posterior' in response.json()['answer']
    for hidden in ('truth_mode', 'true_error_rates', 'oracle_loss', 'evaluation'):
        assert hidden not in response.text
    assert service.status()['provider_calls'] == 0

@pytest.mark.parametrize('status,expected', [(400,'request format'),(401,'API key'),(402,'billing'),(403,'denied access'),(404,'model or endpoint'),(429,'quota'),(503,'service error')])
def test_provider_http_errors_are_actionable_without_leaking_body(client, monkeypatch, status, expected):
    import httpx
    query = body(client)
    response = httpx.Response(status, json={'error':{'message':'test-secret-never-real private prompt', 'param':'model'}}, request=httpx.Request('POST','https://api.meta.ai/v1/chat/completions'))
    failure = httpx.HTTPStatusError('test-secret-never-real', request=response.request, response=response)
    sent = install_transport(monkeypatch, [failure])
    result = client.post('/api/assistant/ask', json=query)
    assert result.status_code == 502
    assert f'Meta HTTP {status}' in result.text
    assert expected in result.text
    assert 'test-secret' not in result.text
    assert 'private prompt' not in result.text
    assert len(sent) == 1
    assert client.get('/api/assistant/status').json()['reserved_usd'] == .25

@pytest.mark.parametrize('kind,expected_status,expected', [('timeout',504,'timed out'), ('connection',502,'connect securely')])
def test_network_errors_are_distinct_and_never_retried(client, monkeypatch, kind, expected_status, expected):
    import httpx
    query = body(client)
    failure = httpx.ReadTimeout('private details') if kind == 'timeout' else httpx.ConnectError('private details')
    sent = install_transport(monkeypatch, [failure])
    result = client.post('/api/assistant/ask', json=query)
    assert result.status_code == expected_status
    assert expected in result.text
    assert 'private details' not in result.text
    assert len(sent) == 1


def test_truncated_response_is_reported_and_not_retried(client, monkeypatch):
    query = body(client)
    sent = install_transport(monkeypatch, [tool_reply(), {'choices':[{'finish_reason':'length','message':{'role':'assistant','content':'Incomplete'}}]}])
    result = client.post('/api/assistant/ask', json=query)
    assert result.status_code == 502
    assert 'completion-token limit' in result.text
    assert len(sent) == 2
