"""Startup behavior without opening ports or contacting a model."""
import os
import pytest
pytest.importorskip('fastapi')
uvicorn = pytest.importorskip('uvicorn')
from backend import run
from backend.app.services.assistant_service import AssistantService

@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.setattr(run, 'port_available', lambda port: True)
    monkeypatch.setenv('QBRIDGE_EXPERIMENT_DIR', str(tmp_path / 'experiments'))
    for key in ('MODEL_API_KEY','QBRIDGE_ASSISTANT_MODE','QBRIDGE_LIVE_AUTHORIZED','QBRIDGE_ASSISTANT_DISABLED'):
        monkeypatch.delenv(key, raising=False)
    launched = []
    monkeypatch.setattr(uvicorn, 'run', lambda *args, **kwargs: launched.append((args,kwargs)))
    return tmp_path, launched

def test_live_launcher_sets_all_flags_and_resumes_without_clearing_budget(setup, monkeypatch, capsys):
    directory, launched = setup
    service = AssistantService(None, directory / 'assistant')
    service.reserve(); service.disable()
    monkeypatch.setattr(run.getpass, 'getpass', lambda prompt: 'private-test-key')
    run.main(['--live'])
    assert os.environ['MODEL_API_KEY'] == 'private-test-key'
    assert service.status()['live_authorized'] is True
    assert service.status()['mode'] == 'live'
    assert service.status()['disabled'] is False
    assert service.status()['reserved_usd'] == .25
    assert 'private-test-key' not in capsys.readouterr().out
    assert launched[0][1]['host'] == '127.0.0.1'

def test_default_launcher_overrides_stale_live_mode(setup, monkeypatch):
    monkeypatch.setenv('QBRIDGE_ASSISTANT_MODE','live')
    monkeypatch.setenv('QBRIDGE_LIVE_AUTHORIZED','yes')
    monkeypatch.setattr(run.getpass,'getpass',lambda prompt: pytest.fail('Unexpected key prompt'))
    run.main([])
    assert os.environ['QBRIDGE_ASSISTANT_MODE'] == 'mock'
    assert os.environ['QBRIDGE_LIVE_AUTHORIZED'] == 'no'

def test_occupied_port_fails_before_requesting_key(setup, monkeypatch):
    monkeypatch.setattr(run,'port_available',lambda port: False)
    monkeypatch.setattr(run.getpass,'getpass',lambda prompt: pytest.fail('Unexpected key prompt'))
    with pytest.raises(SystemExit): run.main(['--live'])
    assert not setup[1]

def test_empty_key_never_starts_server(setup, monkeypatch):
    monkeypatch.setattr(run.getpass,'getpass',lambda prompt: '')
    with pytest.raises(SystemExit): run.main(['--live'])
    assert not setup[1]
