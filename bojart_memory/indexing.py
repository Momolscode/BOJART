"""Index current references, research proposals and session history in one store."""
import json
from pathlib import Path

from .core import MemoryError, PROJECTS, project_ok, safe_relative

COLLECTIONS = ('canonical', 'research', 'session_log')


def index_repository(memory, root):
    root = Path(root).resolve()
    records = json.loads((root / 'data/knowledge/index.json').read_text('utf-8'))
    if not isinstance(records, list):
        raise MemoryError('Index documentaire invalide.')
    normalized, seen = [], set()
    # Validate the complete routing manifest before changing source selections.
    for record in records:
        if not isinstance(record, dict):
            raise MemoryError('Entrée documentaire invalide.')
        project = record.get('project')
        project_ok(project)
        collection = record.get('collection', 'canonical')
        if collection not in COLLECTIONS:
            raise MemoryError('Collection de référence inconnue.')
        path, provenance = record.get('path'), record.get('provenance')
        if not isinstance(path, str) or not isinstance(provenance, str) or not provenance.strip():
            raise MemoryError('Chemin et provenance documentaires requis.')
        safe_relative(path)
        source = root / path
        if not source.resolve().is_relative_to(root) or not source.is_file() or source.is_symlink():
            raise MemoryError('Source documentaire absente ou hors dépôt.')
        identity = (project, path)
        if identity in seen:
            raise MemoryError('Source classée plusieurs fois dans le même projet.')
        seen.add(identity)
        normalized.append({**record, 'collection': collection})
    with memory.transaction():
        files = [memory.ingest_file(
            root / r['path'], root=root, project=r['project'], collection=r['collection'],
            provenance=r['provenance'],
            kind='reference' if r['collection'] == 'research' else 'project_document',
        ) for r in normalized]
        retired = {
            collection: {
                project: memory.reconcile_collection(
                    project=project, collection=collection,
                    source_paths=[r['path'] for r in normalized
                                  if r['project'] == project and r['collection'] == collection],
                ) for project in sorted(PROJECTS)
            } for collection in COLLECTIONS
        }
    return {'files': files, 'retired': retired['canonical'],
            'research_retired': retired['research'], 'session_retired': retired['session_log']}
