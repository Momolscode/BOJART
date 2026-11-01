"""Reassemble the explicitly approved report; never run its historical audit."""
from pathlib import Path
import hashlib
import io
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]
NAME = 'BOJART_VERIFICATION_SAUVEGARDE_2026-11-01.zip'
EXPECTED_ZIP = '322626473beb2de1c69ae28bea1958d368ccb7bf34fb213c3829397fabf8efec'
EXPECTED = {
    'BILAN_VERIFICATION.md': (3410, '6c4cccbbf9f04a49438ce9f241842aef5828f4d7a42ba1ca6b4ac20b2ecbf078'),
    'comparison.json': (64555, '5973ec47e48a3c19cff2a11f640f0be9801deda30c12827cf2af8cba573429cb'),
    'remote_selected_evidence.json': (3140, '7783009cf3aeb4eb0ef1ca9e0eb0ed00ff699c531ea9680feff53c22aa88597a'),
    'audit.py': (7369, '735d0525bb9b4e94c5481a75a80373a3732ccd733aaeff63d4b7a23b9e48aa13'),
}


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def write_exact(path, raw):
    if path.exists() and path.read_bytes() != raw:
        raise ValueError('Refusing to overwrite different existing file: ' + path.name)
    if not path.exists():
        with path.open('xb') as handle:
            handle.write(raw)


def main():
    parts = [ROOT / '.transfer' / ('report.zip.part%02d' % i) for i in range(6)]
    if any(p.is_symlink() for p in parts):
        raise ValueError('Symlinks are not allowed')
    raw = b''.join(p.read_bytes() for p in parts)
    if len(raw) != 19824 or sha256(raw) != EXPECTED_ZIP:
        raise ValueError('Report ZIP size or checksum mismatch')
    checked = {}
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        if len(archive.namelist()) != 4 or set(archive.namelist()) != set(EXPECTED):
            raise ValueError('Unexpected ZIP members')
        if archive.testzip() is not None:
            raise ValueError('ZIP CRC mismatch')
        for name, (size, expected) in EXPECTED.items():
            content = archive.read(name)
            if len(content) != size or sha256(content) != expected:
                raise ValueError('Member checksum mismatch: ' + name)
            content.decode('utf-8')
            if name.endswith('.json'):
                json.loads(content)
            if name.endswith('.py'):
                compile(content, name, 'exec')
            checked[name] = content
    write_exact(ROOT / NAME, raw)
    for name, content in checked.items():
        write_exact(ROOT / name, content)
    proof = {
        'ok': True,
        'scope': 'Exact publication of the four-file report, not a new restoration of the 1.09 GB project collection.',
        'archive': {'path': NAME, 'bytes': len(raw), 'sha256': sha256(raw), 'crc_ok': True},
        'members': [{'path': name, 'bytes': len(content), 'sha256': sha256(content)} for name, content in checked.items()],
        'historical_audit_executed': False,
        'main_branch_modified': False,
    }
    write_exact(ROOT / 'INTEGRITY.json', (json.dumps(proof, ensure_ascii=False, indent=2) + '\n').encode())
    print(json.dumps(proof, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
