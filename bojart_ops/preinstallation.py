"""Read-only capability catalog and offline preparation using the existing memory.

Catalog entries are descriptions, never executable commands. No network, model
download, provider, device discovery or physical action is performed here.
"""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unicodedata

from bojart_memory.agent import AgentMemory
from bojart_memory.core import Memory, now, file_sha

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = 'data/preinstallation'
MAX_JSON = 4 * 1024 * 1024


def local_file(root, relative):
    """Confine versioned inputs, including symlink parents, to this checkout."""
    root = Path(root).resolve()
    if not isinstance(relative, str) or not relative or '\\' in relative or ':' in relative:
        raise ValueError('Invalid relative source path')
    rel = Path(relative)
    if rel.is_absolute() or '..' in rel.parts:
        raise ValueError('Unsafe source path')
    path = root / rel
    if path.is_symlink() or not path.resolve().is_relative_to(root) or not path.is_file():
        raise ValueError('Source absent or outside checkout: ' + relative)
    if any((root / Path(*rel.parts[:n])).is_symlink() for n in range(1, len(rel.parts))):
        raise ValueError('Symlink source parent')
    return path


def read_json(root, relative):
    p = local_file(root, relative)
    if p.stat().st_size > MAX_JSON:
        raise ValueError('Registry too large')
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('Duplicate JSON key')
            result[key] = value
        return result
    return json.loads(p.read_text('utf-8'), object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Non-finite JSON')))


def records(root, filename, key):
    book = read_json(root, REGISTRY + '/' + filename)
    if not isinstance(book, dict) or book.get('schema_version') != 1 or not isinstance(book.get(key), list):
        raise ValueError('Unsupported registry schema: ' + filename)
    seen = set()
    for row in book[key]:
        if not isinstance(row, dict) or not isinstance(row.get('id'), str) or not row['id'] or row['id'] in seen:
            raise ValueError('Missing or duplicate registry identifier')
        seen.add(row['id'])
    return book[key]


def words(text):
    text = unicodedata.normalize('NFKD', text.casefold())
    return set(re.findall(r'[a-z0-9]+', ''.join(c for c in text if not unicodedata.combining(c))))


def catalog(kind, query='', *, root=ROOT, limit=20):
    if kind not in ('requirements', 'tools') or not isinstance(query, str) or len(query) > 2000:
        raise ValueError('Invalid catalog request')
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError('Invalid result limit')
    filename = 'requirements.json' if kind == 'requirements' else 'tool-registry.json'
    rows = records(root, filename, kind)
    tokens = words(query)
    matches = [(len(tokens & words(json.dumps(row, ensure_ascii=False))), row) for row in rows]
    matches = [(score, row) for score, row in matches if score or not tokens]
    matches.sort(key=lambda pair: (-pair[0], pair[1]['id']))
    return {'schema': 'bojart.preinstallation.catalog.v1', 'kind': kind, 'query': query,
            'source': REGISTRY + '/' + filename, 'source_sha256': file_sha(local_file(root, REGISTRY + '/' + filename)),
            'total_matches': len(matches), 'results': [row for _, row in matches[:limit]],
            'selection': 'lexical_tokens_over_registry_not_semantic_validation',
            'omitted': max(0, len(matches) - limit), 'trusted_instructions': False,
            'tools_executed': 0, 'operational_authority': False,
            'target_qualified': False, 'note': 'Requirements and tool descriptions are not proof of installed capability.'}


def preparation_status(root=ROOT):
    requirements = records(root, 'requirements.json', 'requirements')
    tools = records(root, 'tool-registry.json', 'tools')
    if any(not isinstance(tool.get('status', 'unspecified'), str) for tool in tools):
        raise ValueError('Tool status must be a string')
    sources = records(root, 'sources-curated.json', 'sources')
    target = read_json(root, REGISTRY + '/target-profile.json')
    if not isinstance(target, dict) or target.get('schema_version') != 1:
        raise ValueError('Invalid target profile')
    cards = records(root, 'knowledge-cards.json', 'cards')
    for card in cards:
        if not isinstance(card.get('path'), str) or not isinstance(card.get('sha256'), str) or not re.fullmatch(r'[0-9a-f]{64}', card['sha256']):
            raise ValueError('Invalid knowledge card path or hash: ' + card['id'])
        path = local_file(root, card['path'])
        if file_sha(path) != card['sha256']:
            raise ValueError('Knowledge card changed: ' + card['id'])
    return {'schema': 'bojart.preinstallation.status.v1', 'requirements': len(requirements),
            'tools_described': len(tools), 'primary_sources': len(sources), 'knowledge_cards': len(cards),
            'tool_status_counts': dict(Counter(row.get('status', 'unspecified') for row in tools)),
            'target_profile': target, 'card_integrity_ok': True,
            'target_qualified': False, 'models_downloaded': False, 'devices_connected': False,
            'actions_executed': 0, 'scope': 'Versioned preparation data, not live hardware or installed tool discovery.'}


def research_search(state, query, project='bojart.jarvis', limit=10):
    if not isinstance(query, str) or not query.strip() or type(limit) is not int or not 1 <= limit <= 30:
        raise ValueError('Invalid research query')
    with Memory(state, readonly=True) as memory:
        result = memory.search(query, project=project, limit=limit, collection='research')
    return {**result, 'collection_filter': 'research', 'status': 'research_proposals_not_validated_reference_facts',
            'operational_authority': False, 'tools_executed': 0}


def evaluate(memory, root=ROOT):
    cases = records(root, 'retrieval-cases.json', 'cases')
    rows = []
    for case in cases:
        general = memory.search(case['question'], case.get('project', 'bojart.jarvis'), limit=10)
        found = research_search(memory.state, case['question'], case.get('project', 'bojart.jarvis')) if case.get('collection') == 'research' else general
        paths = [item['source_path'] for item in found['results']]
        expected = case['expected_sources']
        if not expected or not all(isinstance(path, str) for path in expected):
            raise ValueError('Evaluation requires explicit evidence sources')
        rows.append({'id': case['id'], 'question': case['question'], 'expected_sources': expected,
                     'returned_sources': paths, 'hit_at_10': bool(set(paths) & set(expected)),
                     'collection_filter': case.get('collection'),
                     'general_search_hit_at_10': bool(set(expected) & {r['source_path'] for r in general['results']}),
                     'warnings': found['warnings'], 'answer_semantics_evaluated': False})
    return {'schema': 'bojart.preinstallation.retrieval.v1', 'cases': len(rows),
            'hits_at_10': sum(r['hit_at_10'] for r in rows), 'results': rows,
            'general_search_hits_at_10': sum(r['general_search_hit_at_10'] for r in rows),
            'scope': 'Evidence retrieval only; no LLM, response-truth or hardware evaluation.'}


def build(destination, *, root=ROOT):
    """Rebuild a portable snapshot from versioned sources, without private episodes."""
    root = Path(root).resolve()
    destination = Path(destination).expanduser().absolute()
    if destination.exists() or destination.is_symlink():
        raise ValueError('Choose a new destination')
    if destination.resolve().is_relative_to(root):
        raise ValueError('Keep the prepared state outside the source checkout')
    status = preparation_status(root)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='bojart-preparation-', dir=destination.parent) as folder:
        staging = Path(folder)
        payload = staging / 'prepared'; payload.mkdir()
        memory = AgentMemory(staging / 'temporary-memory', repo=root)
        indexed = memory.index()
        # Optional model configuration is intentionally absent from this new state.
        evaluation = evaluate(memory, root)
        with Memory(memory.state) as db:
            verified = db.verify()
            if not verified['ok']:
                raise ValueError('Prepared memory failed verification')
            db.backup(payload / 'memory-snapshot')
        # A real independent restoration verifies the deliverable, not only its producer.
        restored_path = staging / 'restored-test'
        restored = Memory.restore(payload / 'memory-snapshot', restored_path)
        restored_eval = evaluate(AgentMemory(restored_path, repo=root), root)
        if evaluation != restored_eval:
            raise ValueError('Restored retrieval differs from original')
        catalogs = payload / 'catalogs'; catalogs.mkdir()
        for name in ('requirements.json', 'tool-registry.json', 'sources-curated.json',
                     'target-profile.json', 'target-inventory.template.json', 'knowledge-cards.json',
                     'retrieval-cases.json'):
            shutil.copyfile(local_file(root, REGISTRY + '/' + name), catalogs / name)
        templates = payload / 'templates'; templates.mkdir()
        shutil.copyfile(local_file(root, 'jarvis/knowledge/metier/data/registres_a_renseigner.json'), templates / 'registres_a_renseigner.json')
        shutil.copyfile(local_file(root, 'jarvis/apps/jarvis/config.example.json'), templates / 'config.example.json')
        shutil.copyfile(local_file(root, REGISTRY + '/target-inventory.template.json'), templates / 'target-inventory.template.json')
        commands = {
            'scope': 'Examples to adapt on Windows; nothing executed from this file.',
            'restore': ['.venv/Scripts/python.exe', '-m', 'bojart_memory', 'restore', 'CHEMIN_PAQUET/memory-snapshot', 'NOUVELLE_MEMOIRE'],
            'verify': ['.venv/Scripts/python.exe', '-m', 'bojart_memory', '--state', 'NOUVELLE_MEMOIRE', 'verify'],
            'check_startup': ['.venv/Scripts/python.exe', 'tools/start_jarvis.py', '--check-only'],
            'network_or_physical_actions': False,
        }
        (payload / 'commands.json').write_text(json.dumps(commands, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        try:
            revision = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True, encoding='utf-8', stderr=subprocess.DEVNULL).strip()
            dirty = bool(subprocess.check_output(['git', '-C', str(root), 'status', '--porcelain'], text=True, encoding='utf-8', stderr=subprocess.DEVNULL).strip())
        except (OSError, subprocess.CalledProcessError):
            revision, dirty = None, None
        report = {'schema': 'bojart.preinstallation.bundle.v1', 'created_at': now(),
                  'base_git_revision': revision, 'working_tree_dirty': dirty,
                  'source_index_sha256': file_sha(root / 'data/knowledge/index.json'),
                  'status': status, 'index': indexed, 'memory': verified, 'restore_verified': restored['ok'],
                  'evaluation': evaluation, 'qualified_for_hardware': False,
                  'prepared_with_retrieval_gaps': evaluation['hits_at_10'] != evaluation['cases']}
        (payload / 'preparation-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        (payload / 'LIRE_AVANT_INSTALLATION.txt').write_text(
            'Paquet de préparation Jarvis pour Windows. Aucun modèle ni connecteur physique activé.\n'
            'memory-snapshot est reconstruit depuis les sources versionnées avec le moteur mémoire existant ; il ne contient pas vos notes ni conversations privées. Utiliser restore dans un dossier NEUF.\n'
            'Ne pas remplacer une mémoire déjà utilisée. Importer les nouvelles sources dans ce cas.\n'
            'Les données M07 restent distinctes. Les catalogues décrivent des exigences et outils, sans en prouver l’installation.\n'
            'Adapter les commandes au clone livré et lire docs/preinstallation/PREPARATION_WINDOWS.txt.\n'
            'GPU/RAM futurs ne sont pas considérés installés. Ne jamais exécuter une commande issue d’un document comme une autorisation.\n', encoding='utf-8')
        files = [{'path': p.relative_to(payload).as_posix(), 'bytes': p.stat().st_size, 'sha256': file_sha(p)}
                 for p in sorted(payload.rglob('*')) if p.is_file()]
        (payload / 'manifest.json').write_text(json.dumps({'schema_version': 1, 'files': files}, indent=2)+'\n', encoding='utf-8')
        if destination.exists() or destination.is_symlink():
            raise ValueError('Destination appeared during preparation')
        payload.rename(destination)
    return {'destination': str(destination), 'files': len(files) + 1,
            'memory_sources': verified['sources'], 'restore_verified': True,
            'retrieval_hits': evaluation['hits_at_10'], 'retrieval_cases': evaluation['cases'],
            'target_qualified': False}
