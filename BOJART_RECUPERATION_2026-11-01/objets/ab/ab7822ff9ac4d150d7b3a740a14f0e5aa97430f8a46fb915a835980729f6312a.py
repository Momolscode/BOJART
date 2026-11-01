"""Atelier de contrats depuis HAR. Aucun navigateur, LLM ou code généré exécuté."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
import hashlib
import ipaddress
import json
import re
import shutil
import sys
from urllib.parse import parse_qsl, unquote, urlsplit

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / 'legacy'))
from pilote import Ledger

MAX_BYTES = 8_000_000
MAX_ENTRIES = 2000
READ_METHODS = {'GET', 'HEAD', 'OPTIONS'}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def origin_of(value, allow_loopback=False):
    try:
        u = urlsplit(value)
        port = u.port
    except (ValueError, TypeError):
        raise ValueError('Origine invalide') from None
    if u.username or u.password or not u.hostname:
        raise ValueError('Origine sans identifiant requise')
    try:
        local = ipaddress.ip_address(u.hostname).is_loopback
    except ValueError:
        local = u.hostname == 'localhost'
    if u.scheme != 'https' and not (allow_loopback and u.scheme == 'http' and local):
        raise ValueError('HTTPS requis, sauf boucle locale explicitement autorisée')
    host = u.hostname.lower()
    if ':' in host:
        host = '[' + host + ']'
    default = (u.scheme == 'https' and port == 443) or (u.scheme == 'http' and port == 80)
    return u.scheme + '://' + host + (':' + str(port) if port and not default else '')


@dataclass(frozen=True)
class Scope:
    project: str
    origin: str
    authority_ref: str
    allow_loopback: bool = False

    def __post_init__(self):
        if self.project != 'marwin-studio':
            raise ValueError('Projet non pris en charge par cet atelier')
        if not self.authority_ref.strip() or len(self.authority_ref) > 300:
            raise ValueError('Référence de mandat requise')
        normalized = origin_of(self.origin, self.allow_loopback)
        u = urlsplit(self.origin)
        if u.path not in ('', '/') or u.query or u.fragment:
            raise ValueError('Fournir une origine, pas une URL avec chemin ou paramètres')
        object.__setattr__(self, 'origin', normalized)


def safe_path(path):
    """Réduit les identifiants évidents ; une revue reste requise pour les noms métier."""
    parts = []
    for part in unquote(path or '/').split('/'):
        if not part:
            continue
        if part in ('.', '..') or '@' in part or len(part) > 32 or re.fullmatch(r'[0-9a-fA-F-]{16,}', part) or part.isdigit():
            part = '{id}'
        parts.append(part)
    return '/' + '/'.join(parts)


def inspect_har(har, scope):
    """Contrat candidat : méthodes/chemins/noms des paramètres, jamais leurs valeurs."""
    if not isinstance(har, dict) or len(canonical(har).encode()) > MAX_BYTES:
        raise ValueError('HAR absent ou trop volumineux')
    entries = har.get('log', {}).get('entries')
    if not isinstance(entries, list) or len(entries) > MAX_ENTRIES:
        raise ValueError('Liste entries absente ou trop longue')
    endpoints, excluded = {}, 0
    for entry in entries:
        request = entry.get('request', {})
        try:
            url = urlsplit(request.get('url', ''))
            origin = origin_of(request.get('url', ''), scope.allow_loopback)
        except ValueError:
            excluded += 1
            continue
        if origin != scope.origin:
            excluded += 1
            continue
        method = str(request.get('method', '')).upper()
        if method not in {'GET', 'HEAD', 'OPTIONS', 'POST', 'PUT', 'PATCH', 'DELETE'}:
            excluded += 1
            continue
        path = safe_path(url.path)
        key = (method, path)
        item = endpoints.setdefault(key, {'method': method, 'path': path, 'query_names': [],
            'status_codes': [], 'response_types': [], 'read_method': method in READ_METHODS,
            'execution_allowed': False, 'observations': 0})
        query_names = {k for k, _ in parse_qsl(url.query, keep_blank_values=True)}
        query_names.update(q.get('name', '') for q in request.get('queryString', []) if isinstance(q, dict))
        item['query_names'] = sorted(set(item['query_names']) | {k for k in query_names if k and len(k) <= 80})
        response = entry.get('response', {})
        status = response.get('status')
        if type(status) is int and 100 <= status <= 599:
            item['status_codes'] = sorted(set(item['status_codes']) | {status})
        mime = response.get('content', {}).get('mimeType', '').split(';', 1)[0]
        if mime in {'application/json', 'text/json', 'text/html', 'text/plain'}:
            item['response_types'] = sorted(set(item['response_types']) | {mime})
        item['observations'] += 1
    contract = {'openapi': '3.1.0', 'info': {'title': 'Marwin contrat candidat', 'version': '0.1.0'},
                'servers': [{'url': scope.origin}], 'paths': {}}
    for item in sorted(endpoints.values(), key=lambda e: (e['path'], e['method'])):
        if not item['read_method']:
            continue
        contract['paths'].setdefault(item['path'], {})[item['method'].lower()] = {
            'parameters': [{'name': name, 'in': 'query', 'required': False, 'schema': {'type': 'string'}} for name in item['query_names']],
            'responses': {str(code): {'description': 'Statut observé ; schéma de réponse à vérifier'} for code in item['status_codes']},
            'x-marwin-execution-allowed': False}
        # A generalized identifier must be declared as a path parameter.
        if '{id}' in item['path']:
            contract['paths'][item['path']][item['method'].lower()]['parameters'].append(
                {'name': 'id', 'in': 'path', 'required': True, 'schema': {'type': 'string'}})
    return {'schema_version': 1, 'status': 'candidate_not_executed', 'project': scope.project,
            'origin': scope.origin, 'authority_ref': scope.authority_ref,
            'capture_sha256': digest(har), 'contract_sha256': digest(contract),
            'entries': len(entries), 'excluded_entries': excluded,
            'endpoints': sorted(endpoints.values(), key=lambda e: (e['path'], e['method'])),
            'openapi_candidate': contract, 'external_calls': 0, 'generated_client_executed': False,
            'privacy_scope': 'En-têtes, cookies, corps et valeurs de paramètres omis. Les noms de chemins et de paramètres restent à relire.'}


def record_contract(report, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    key = digest({'capture': report['capture_sha256'], 'project': report['project'],
                  'authority_ref': report['authority_ref'], 'origin': report['origin']})
    event = {'event_id': 'api-contract-' + key, 'project': report['project'], 'kind': 'claim',
             'entity_id': 'api-contract-' + key, 'expected_revision': 0,
             'data': {'observed_on': date.today().isoformat(), 'subject': report['origin'],
                      'predicate': 'capture_inspected_locally', 'value': {'contract_sha256': report['contract_sha256'],
                      'endpoints': len(report['endpoints']), 'status': report['status']},
                      'status': 'observed', 'evidence_refs': ['sha256:' + report['capture_sha256']],
                      'scope': 'Structure du HAR fourni ; aucune preuve de permission du site ou de client opérationnel.'}}
    ledger = Ledger(directory / 'journal.sqlite')
    try:
        return ledger.ingest(event)
    finally:
        ledger.close()


def inspect_and_record(har, scope, directory):
    report = inspect_har(har, scope)
    report['journal'] = record_contract(report, directory)
    return report


def rae_preflight_plan(scope, executable=None):
    """Prépare seulement un dry-run du binaire installé ; aucune invocation automatique."""
    binary = executable or shutil.which('reverse-api-engineer')
    return {'status': 'prepared' if binary else 'runtime_missing', 'executable': binary,
            'argv': [binary or 'reverse-api-engineer', 'agent', '--prompt',
                     'Document the read-only endpoints on the authorized origin. Do not submit forms or perform writes.',
                     '--url', scope.origin, '--headless', '--dry-run', '--json'],
            'executes': False, 'opens_browser': False, 'model_call': False,
            'requires_before_capture': ['Official API/SDK coverage checked', 'Site scope confirmed',
                                        'Credential handling reviewed', 'Exact run budget defined', 'Runtime dry-run succeeded']}
