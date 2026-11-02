"""Deterministic extraction contracts over preserved UTF-8 source bytes.

This is consistency checking, not authentication of a hostile database writer.
The original object is retained even when a project projection is indexed.
"""
import json
from pathlib import PurePosixPath

TEXT_EXTRACTOR = 'utf8_lines_v1'
PROJECT_EXTRACTOR = 'project_jsonl_v1'
EXTRACTORS = {TEXT_EXTRACTOR, PROJECT_EXTRACTOR}
CLAIM_REGISTRY = 'data/knowledge/claims.jsonl'
PROJECTS = {'bojart.jarvis', 'bojart.creative', 'bojart.sites'}


def _unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON object key.')
        result[key] = value
    return result


def project_records(text):
    """Validate every nonblank record; retain its original line and spelling."""
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line, object_pairs_hook=_unique_keys)
        if not isinstance(value, dict) or value.get('project') not in PROJECTS:
            raise ValueError('Project JSONL requires a recognized project on every record.')
        yield number, line, value


def choose_extractor(text, source_path, projection=None):
    """Explicit projection is general; the BOJART ledger always requires it.

Other JSONL files are projected automatically when they contain a recognized
BOJART project field. Mixed or malformed records then fail closed.
"""
    if projection not in (None, PROJECT_EXTRACTOR):
        raise ValueError('Unknown projection contract.')
    if projection == PROJECT_EXTRACTOR or source_path == CLAIM_REGISTRY:
        list(project_records(text))
        return PROJECT_EXTRACTOR
    if PurePosixPath(source_path).suffix.lower() == '.jsonl':
        identified = False
        for line in text.splitlines():
            try:
                value = json.loads(line)
            except (ValueError, TypeError):
                continue
            if isinstance(value, dict) and value.get('project') in PROJECTS:
                identified = True
                break
        if identified:
            list(project_records(text))
            return PROJECT_EXTRACTOR
    return TEXT_EXTRACTOR


def extract(text, extraction, project, chunker):
    if extraction == TEXT_EXTRACTOR:
        return list(chunker(text))
    if extraction != PROJECT_EXTRACTOR:
        raise ValueError('Unknown extraction contract.')
    result = []
    for number, line, record in project_records(text):
        if record['project'] == project:
            # Split unusually long JSON records without reserializing them.
            for offset in range(0, len(line), 2800):
                result.append((number, number, line[offset:offset + 2800]))
    return result
