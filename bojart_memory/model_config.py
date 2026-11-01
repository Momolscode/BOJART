"""Read and diagnose optional local models without initializing memory or inference."""
import json
import os
import tempfile
from http.client import HTTPException
from pathlib import Path

from .core import MemoryError
from .ollama import ModelError, Ollama

DEFAULT_URL = 'http://127.0.0.1:11434'
ROLES = {'embedding_model': 'embedding', 'chat_model': 'completion'}
MAX_CONFIG_BYTES = 16384


class ModelConfigurationError(MemoryError):
    pass


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ModelConfigurationError('Clé dupliquée dans la configuration modèles.')
        result[key] = value
    return result


def validate_config(config):
    if not isinstance(config, dict) or set(config) - {*ROLES, 'ollama_url'}:
        raise ModelConfigurationError('Configuration modèles invalide.')
    url = config.get('ollama_url', DEFAULT_URL)
    try:
        Ollama('configuration-check', url)  # Constructor only; no request.
        for field in ROLES:
            if field in config:
                Ollama(config[field], url)
    except (ValueError, TypeError) as exc:
        raise ModelConfigurationError('Nom de modèle ou adresse locale invalide dans models.json.') from exc
    return config


def load_config(state):
    path = Path(state).expanduser() / 'models.json'
    try:
        with path.open('rb') as stream:
            raw = stream.read(MAX_CONFIG_BYTES + 1)
    except FileNotFoundError:
        return {}
    if len(raw) > MAX_CONFIG_BYTES:
        raise ModelConfigurationError('Configuration modèles trop volumineuse.')
    try:
        config = json.loads(raw.decode('utf-8'), object_pairs_hook=_unique)
    except (ValueError, UnicodeError) as exc:
        raise ModelConfigurationError('Fichier models.json illisible ; la recherche par mots reste disponible.') from exc
    return validate_config(config)


def save_config(state, config):
    """Replace only a fully validated configuration; leave the original on error."""
    validate_config(config)
    state = Path(state).expanduser()
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(prefix='.models-', suffix='.tmp', dir=state)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as stream:
            json.dump(config, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, state / 'models.json')
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def inspect_models(state, *, probe=False):
    """Optional tags/show requests on loopback; no prompts, inference or downloads."""
    result = {'schema': 'bojart.local-models.v1', 'ok': True,
              'configuration_status': 'valid', 'probe_requested': probe,
              'roles': {}, 'local_metadata_requests': 0,
              'inference_calls': 0, 'model_downloads': 0,
              'inference_qualified': False}
    try:
        config = load_config(state)
    except (ModelConfigurationError, OSError) as exc:
        result.update(ok=False, configuration_status='invalid', error_type=type(exc).__name__)
        result['roles'] = {role: {'configured': False, 'status': 'configuration_invalid'}
                           for role in ROLES}
        return result
    for role, capability in ROLES.items():
        model = config.get(role)
        entry = {'configured': bool(model), 'status': 'not_configured',
                 'required_capability': capability}
        if model:
            entry.update(model=model, status='not_probed')
            if probe:
                client = Ollama(model, config.get('ollama_url', DEFAULT_URL), timeout=2)
                try:
                    entry.update(client.inspect(capability))
                except ModelError as exc:
                    entry.update(status=exc.code)
                    result['ok'] = False
                except (ValueError, OSError, HTTPException) as exc:
                    entry.update(status='unavailable', error_type=type(exc).__name__)
                    result['ok'] = False
                finally:
                    result['local_metadata_requests'] += client.request_count
        result['roles'][role] = entry
    return result
