"""Offline checks for the selected deployment contract."""
import importlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend_files'))
import rag_utils


def test_mmr_uses_selected_settings_and_preserves_sources():
    settings = rag_utils.load_settings()
    calls = []

    class Store:
        def max_marginal_relevance_search(self, query, **kwargs):
            calls.append((query, kwargs))
            return [SimpleNamespace(page_content='Pets: $100 per stay',
                                    metadata={'source': 'policy.pdf', 'section': 'Pets'})]

    chunks = rag_utils.retrieve('Miami pets?', Store(), settings)
    assert calls == [('Miami pets?', {'k': 5, 'fetch_k': 20, 'lambda_mult': 0.7})]
    assert 'Pets: $100 per stay' in chunks[0]
    assert 'policy.pdf' in chunks[0]


def test_generation_keeps_grounding_and_missing_information_rules():
    class Model:
        def invoke(self, messages):
            system, human = messages
            assert system[0] == 'system'
            assert 'Do not use outside knowledge' in system[1]
            assert 'If information is missing' in system[1]
            assert human[0] == 'human'
            assert 'Question:\nMiami pets?' in human[1]
            assert 'Pets: $100' in human[1]
            return SimpleNamespace(content='Grounded answer')

    assert rag_utils.generate('Miami pets?', ['Pets: $100'], Model()).content == 'Grounded answer'


def test_rag_uses_server_settings_and_returns_message_text(monkeypatch):
    settings = rag_utils.load_settings()
    monkeypatch.setenv('OPENAI_API_KEY', 'offline-test-key')
    seen = {}

    class Model:
        def __init__(self, **kwargs):
            seen.update(kwargs)

        def invoke(self, messages):
            return SimpleNamespace(content='Answer')

    monkeypatch.setattr(rag_utils, 'ChatOpenAI', Model)
    monkeypatch.setattr(rag_utils, 'retrieve', lambda *args: ['Evidence'])
    assert rag_utils.rag('question', object(), settings) == ('Answer', ['Evidence'])
    assert seen['model'] == settings['MODEL']
    assert seen['temperature'] == 0
    assert seen['max_tokens'] == 512
    assert seen['request_timeout'] == 30


def test_rejects_index_from_a_different_embedding_model(monkeypatch):
    original = json.loads

    def fake_loads(text):
        if 'embedding_model' in text:
            return {'embedding_model': 'wrong-model'}
        return original(text)

    monkeypatch.setattr(Path, 'read_text', lambda self: '{"embedding_model":"wrong-model"}')
    monkeypatch.setattr(rag_utils.json, 'loads', fake_loads)
    with pytest.raises(ValueError, match='embedding model'):
        rag_utils.load_vectorstore({'EMBED_MODEL': 'text-embedding-3-small'})


def client_with_stubs(monkeypatch):
    pytest.importorskip('flask')
    app_module = importlib.import_module('app')
    monkeypatch.setattr(app_module, 'rag', lambda *args: ('Answer', ['Evidence']))
    monkeypatch.setattr(app_module, 'retrieve', lambda *args: ['Evidence'])
    return app_module.create_app(vectorstore=object(), settings=rag_utils.load_settings()).test_client()


def test_endpoint_shapes(monkeypatch):
    client = client_with_stubs(monkeypatch)
    assert client.get('/').status_code == 200
    assert client.post('/v1/answer', json={'query': 'Question'}).get_json()['answer'] == 'Answer'
    both = client.post('/v1/answer_with_relevant_chunks', json={'query': 'Question'})
    assert both.status_code == 200
    assert both.get_json()['relevant_chunks'][0]['text'] == 'Evidence'
    assert both.get_json()['relevant_chunks'][0]['document'] == 'Policy document'
    assert client.post('/v1/relevant_chunks', json={'query': 'Question'}).status_code == 200


def test_invalid_requests_and_overrides_are_rejected(monkeypatch):
    client = client_with_stubs(monkeypatch)
    for payload in [None, [], {}, {'query': ' '}, {'query': 'Q', 'k': 99}, {'query': 'x' * 4001}]:
        assert client.post('/v1/answer', json=payload).status_code == 400


def test_upstream_errors_do_not_expose_credentials(monkeypatch):
    client = client_with_stubs(monkeypatch)
    app_module = importlib.import_module('app')

    def fail(*args):
        raise RuntimeError('secret-test-value')

    monkeypatch.setattr(app_module, 'rag', fail)
    response = client.post('/v1/answer', json={'query': 'Q'})
    assert response.status_code == 502
    assert 'secret-test-value' not in response.get_data(as_text=True)


@pytest.mark.parametrize('source', ['/Users/local/data/hotel_policy.pdf', r'C:\data\hotel_policy.pdf'])
def test_public_sources_hide_paths_without_changing_policy_text(source):
    pytest.importorskip('flask')
    app_module = importlib.import_module('app')
    chunk = "Content:\nPets\nPet fee: $100 per stay\n\nMetadata:\n" + repr({
        'source': source, 'section': 'Pets'
    })
    sources, answer = app_module.present_sources([chunk], f"See {source}, section Pets")
    assert sources == [{'document': 'Hotel policy', 'filename': 'hotel_policy.pdf',
                        'section': 'Pets', 'text': 'Pet fee: $100 per stay'}]
    assert answer == 'See hotel_policy.pdf, section Pets'
    assert repr(source) in chunk  # The original evidence passed to generation is untouched.
