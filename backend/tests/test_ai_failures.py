import json
from dataclasses import replace

import httpx
import pytest
from fastapi.testclient import TestClient
from helpdesk import rag
from helpdesk.db import connect
from helpdesk.main import create_app

from .conftest import login_demo


@pytest.mark.parametrize(('failure', 'category'), [
    (httpx.ReadTimeout('PRIVATE-ERROR'), 'read_timeout'),
    (httpx.ConnectTimeout('PRIVATE-ERROR'), 'connect_timeout'),
    (httpx.WriteTimeout('PRIVATE-ERROR'), 'other_timeout'),
    (httpx.ConnectError('PRIVATE-ERROR'), 'network'),
    (ValueError('PRIVATE-ERROR'), 'invalid_response'),
    *[(httpx.HTTPStatusError('PRIVATE-ERROR',
                            request=httpx.Request('POST', 'https://private.test/?key=PRIVATE-URL'),
                            response=httpx.Response(status)), category)
      for status, category in [(401, 'authentication'), (403, 'authentication'),
                               (429, 'rate_limit'), (503, 'provider_server'), (400, 'http_status')]],
])
def test_failures_are_classified_without_leaks_or_retry(settings, monkeypatch, caplog, failure, category):
    settings = replace(settings, llm_url='https://private.test', llm_key='PRIVATE-KEY')
    calls = []

    def fail(*args):
        calls.append(args)
        raise failure

    monkeypatch.setattr(rag, 'gateway', fail)
    with TestClient(create_app(settings)) as client:
        headers = login_demo(client)
        response = client.post('/api/chat', json={'question': 'VPNにつながらない PRIVATE-QUESTION'},
                               headers=headers)
        assert response.status_code == 200
        result = response.json()
        assert result['mode'] == 'extractive' and result['reason'] == 'provider_error'
        assert result['failure_code'] == category
        assert result['sources'][0]['document_id'] == 'remote-access'
    assert len(calls) == 1
    with connect(settings.database) as db:
        usage = [dict(row) for row in db.execute('SELECT * FROM usage')]
        audit = [dict(row) for row in db.execute('SELECT * FROM audit')]
    assert len(usage) == 1 and usage[0]['status'] == 'error'
    assert any(row['event'] == f'ai_failure_generation_{category}' for row in audit)
    public_records = caplog.text + json.dumps(result) + json.dumps(audit)
    assert 'PRIVATE-' not in public_records
    assert f'category={category}' in caplog.text and 'elapsed_ms=' in caplog.text


@pytest.mark.parametrize('payload', [[], {'usage': [1]}, {'choices': [{'message': {'content': '[]'}}]}])
def test_malformed_provider_payload_falls_back(settings, monkeypatch, payload):
    settings = replace(settings, llm_url='https://proxy.test', llm_key='dummy')
    monkeypatch.setattr(rag, 'gateway', lambda *_: payload)
    with TestClient(create_app(settings)) as client:
        response = client.post('/api/chat', json={'question': 'VPNにつながらない'},
                               headers=login_demo(client))
        assert response.status_code == 200
        assert response.json()['failure_code'] == 'invalid_response'


def test_gateway_separates_timeouts_and_does_not_retry(settings, monkeypatch):
    seen = []

    class FakeClient:
        def __init__(self, **kwargs):
            seen.append(kwargs)

        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

        def post(self, url, **kwargs):
            seen.append(url)
            raise httpx.ReadTimeout('test timeout')

    monkeypatch.setattr(rag.httpx, 'Client', FakeClient)
    for value, expected in [(45, 45), (1000, 60), (-1, 5)]:
        with pytest.raises(httpx.ReadTimeout):
            rag.gateway(replace(settings, llm_read_timeout=value), 'chat/completions', {})
        timeout = seen[-2]['timeout']
        assert timeout.read == expected and timeout.connect == 5 and timeout.write == 10
        assert seen[-2]['follow_redirects'] is False and seen[-2]['trust_env'] is False
    assert len(seen) == 6


def test_embedding_failure_is_identified(settings, monkeypatch, caplog):
    settings = replace(settings, llm_url='https://proxy.test', llm_key='dummy', embedding_model='embed')
    monkeypatch.setattr(rag, 'gateway', lambda *_: (_ for _ in ()).throw(httpx.ReadTimeout('PRIVATE-ERROR')))
    with TestClient(create_app(settings)) as client:
        response = client.post('/api/chat', json={'question': 'VPNにつながらない'},
                               headers=login_demo(client))
        assert response.json()['failure_code'] == 'read_timeout'
    assert 'stage=embedding' in caplog.text
