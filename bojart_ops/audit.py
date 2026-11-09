"""Read-only audit of tracked bytes; documents are never executed as instructions."""
from __future__ import annotations
import ast
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import subprocess
from collections import Counter, defaultdict

TEXT_LIMIT = 4 * 1024 * 1024
TEXT_EXT = {'.py', '.json', '.jsonl', '.md', '.txt', '.yml', '.yaml', '.toml', '.html', '.js', '.ts', '.tsx', '.css', '.sh', '.cmd'}


def strict_json(text):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate JSON key')
            result[key] = value
        return result
    def invalid(value):
        raise ValueError('non-finite JSON number')
    return json.loads(text, object_pairs_hook=pairs, parse_constant=invalid)


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args])


def tracked_paths(root):
    return [x.decode('utf-8') for x in git(root, 'ls-files', '-z').split(b'\0') if x]


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def audit(root, paths=None, revision=None):
    root = Path(root).resolve()
    paths = sorted(set(tracked_paths(root) if paths is None else paths))
    revision = revision or git(root, 'rev-parse', 'HEAD').decode().strip()
    inventory, issues, documents = [], [], {}
    groups = defaultdict(list)

    def issue(level, code, path, message):
        issues.append(dict(level=level, code=code, path=path, message=message))

    for name in paths:
        relative = PurePosixPath(name)
        p = root / name
        if relative.is_absolute() or '..' in relative.parts or not p.resolve().is_relative_to(root):
            issue('error', 'unsafe_path', name, 'Path escapes the repository.'); continue
        if p.is_symlink():
            issue('warning', 'symlink_not_read', name, 'Symbolic link was not followed.'); continue
        if not p.is_file():
            issue('warning' if p.is_dir() else 'error', 'not_a_regular_file', name, 'Tracked entry not read.'); continue
        size = p.stat().st_size
        sha = digest(p)
        inventory.append(dict(path=name, bytes=size, sha256=sha))
        if size:
            groups[sha].append(name)
        if size > 50 * 1024 * 1024:
            issue('warning', 'large_blob', name, 'Consider content-addressed media storage or LFS.');
        with p.open('rb') as header:
            if header.read(200).startswith(b'version https://git-lfs.github.com/spec/v1'):
                issue('warning', 'lfs_pointer', name, 'Pointer exists; media bytes were not checked.');
        if p.suffix.lower() not in TEXT_EXT:
            continue
        if size > TEXT_LIMIT:
            issue('warning', 'text_not_parsed', name, 'Hash verified; text exceeds the parser limit.'); continue
        try:
            text = p.read_text(encoding='utf-8-sig')
        except UnicodeError:
            issue('error', 'invalid_utf8', name, 'Expected UTF-8 text.'); continue
        # Match actual credential shapes, never echo the matching value.
        if re.search(r'\bgh[pousr]_[A-Za-z0-9]{36,}\b|\bgithub_pat_[A-Za-z0-9_]{60,}\b|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----', text):
            issue('error', 'credential_pattern', name, 'Potential credential; inspect privately.');
        if re.search(r'https?://[^\s"<>]+[?&](?:X-Amz-Signature|X-Goog-Signature|sig)=', text, re.I):
            issue('error', 'signed_url', name, 'Temporary signed URL; use a stable asset identifier.');
        if name.endswith('.py'):
            try:
                ast.parse(text, filename=name)
            except SyntaxError:
                issue('error', 'python_syntax', name, 'Python syntax is invalid.');
        if name.endswith(('.json', '.jsonl')):
            try:
                obj = [strict_json(line) for line in text.splitlines() if line.strip()] if name.endswith('.jsonl') else strict_json(text)
                documents[name] = obj
            except (ValueError, RecursionError):
                issue('error', 'invalid_json', name, 'Malformed JSON, repeated keys or non-finite number.');

    for name, obj in documents.items():
        if not isinstance(obj, dict):
            continue
        # Validate known edit decisions without treating old plans as final films.
        if 'shots' in obj and 'frames' in obj and 'fps' in obj:
            try:
                fps, frames, shots = obj['fps'], obj['frames'], obj['shots']
                assert number(fps) and fps > 0 and type(frames) is int and frames > 0
                assert isinstance(shots, list) and shots
                cursor, ids = 0, set()
                if obj.get('format') == 'bojart.brand-film.v1':
                    # Site recipes express ranges in seconds and declare crossfades.
                    overlaps = []
                    for shot in shots:
                        assert isinstance(shot, dict) and isinstance(shot.get('id'), str) and shot['id']
                        assert shot['id'] not in ids
                        ids.add(shot['id'])
                        start, end = shot['output']
                        assert all(number(v) for v in (start, end, shot['duration'], shot['start']))
                        assert start >= 0 and end > start and shot['start'] >= 0
                        assert abs(end-start-shot['duration']) < 1e-6
                        assert start <= cursor+1e-6 and end > cursor
                        if start < cursor-1e-6: overlaps.append((start, cursor))
                        cursor = end
                    transitions = obj.get('transitions', [])
                    assert isinstance(transitions, list) and len(transitions) == len(overlaps)
                    for transition, expected in zip(transitions, overlaps):
                        assert transition['type'] == 'crossfade'
                        actual = transition['output_seconds']
                        assert len(actual) == 2 and all(number(v) for v in actual)
                        assert all(abs(a-b) < 1e-6 for a, b in zip(actual, expected))
                    assert abs(cursor-frames/fps) < 1e-6
                else:
                    for shot in shots:
                        assert isinstance(shot, dict) and isinstance(shot.get('shot'), str)
                        assert shot['shot'] not in ids
                        ids.add(shot['shot'])
                        assert type(shot['frames']) is int and shot['frames'] > 0
                        assert number(shot['in']) and shot['in'] >= 0
                        assert shot['timeline_in_frame'] == cursor
                        cursor += shot['frames']
                        assert shot['timeline_out_frame_exclusive'] == cursor
                    assert cursor == frames
                durations = [obj[key] for key in ('duration_seconds', 'duration_s') if key in obj]
                assert durations and all(number(v) and abs(v-frames/fps) < 1e-6 for v in durations)
            except (AssertionError, KeyError, TypeError, ValueError):
                issue('error', 'invalid_timeline', name, 'Check frame totals, unique shots, source offsets and contiguous cuts.');
        if name.endswith('ASSETS.json') and isinstance(obj.get('assets'), list):
            for item in obj['assets']:
                try:
                    rel = item['path']
                    assert isinstance(rel, str) and rel and not PurePosixPath(rel).is_absolute()
                    assert '..' not in PurePosixPath(rel).parts
                    parent = (root / name).parent.resolve()
                    target = parent / rel
                    assert target.resolve().is_relative_to(parent) and not target.is_symlink()
                    assert type(item['bytes']) is int and item['bytes'] >= 0
                    assert re.fullmatch('[0-9a-f]{64}', item['sha256'])
                    if not target.is_file():
                        issue('warning', 'asset_not_materialized', name, 'Required source absent: ' + rel)
                    elif target.stat().st_size != item['bytes'] or digest(target) != item['sha256']:
                        issue('error', 'asset_integrity', name, 'Source size or hash differs: ' + rel)
                except (AssertionError, KeyError, TypeError):
                    issue('error', 'invalid_asset_record', name, 'Unsafe or incomplete asset record.');
        if name.endswith('G1_PARAMETRES.json') and obj.get('status') == 'completed' and not obj.get('job_id'):
            issue('warning', 'missing_job_id', name, 'Completed generation lacks its provider receipt ID.');
    duplicates = [dict(sha256=sha, paths=names) for sha, names in sorted(groups.items()) if len(names) > 1]
    summary = dict(Counter(i['level'] for i in issues))
    summary.update(files=len(inventory), duplicates=len(duplicates))
    return dict(schema_version=1, revision=revision, scope='tracked working-tree files',
                summary=summary, ok=summary.get('error', 0) == 0,
                limitations=['No binary media decode or perceptual review.',
                             'No proof that missing conversations or external media were recovered.',
                             'No provider, GPU, microphone or printer connection tested.',
                             'No general semantic validation of every document.'],
                files=inventory, duplicates=duplicates, issues=issues)


def markdown(report):
    def safe(s):
        return str(s).replace('`', '').replace('\n', ' ').replace('|', '\\|')
    s = report['summary']
    lines = ['# BOJ.ART — audit technique', '', f"Révision : `{safe(report['revision'])}`", '',
             f"{s['files']} fichiers ; {s.get('error',0)} erreurs ; {s.get('warning',0)} avertissements ; {s['duplicates']} groupes identiques.", '',
             '| Niveau | Code | Fichier | Constat |', '|---|---|---|---|']
    for item in report['issues'][:100]:
        lines.append('| ' + ' | '.join(safe(item[x]) for x in ('level','code','path','message')) + ' |')
    if len(report['issues']) > 100:
        lines.append('\nVoir le JSON pour tous les constats.')
    lines += ['', 'Les doublons sont signalés avec leurs chemins et SHA-256 dans le JSON ; aucun original supprimé.', '', '## Limites', '']
    lines += ['- ' + x for x in report['limitations']]
    return '\n'.join(lines) + '\n'
