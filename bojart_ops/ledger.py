"""Transactional local receipts. This module NEVER calls a paid provider."""
from __future__ import annotations
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import sqlite3

TERMINAL = {'completed', 'failed', 'blocked', 'cancelled'}
PROVIDER_STATES = {'queued':'submitted', 'pending':'submitted', 'submitted':'submitted',
    'processing':'running', 'running':'running', 'in_progress':'running',
    'completed':'completed', 'failed':'failed', 'error':'failed',
    'ip_detected':'blocked', 'nsfw':'blocked', 'cancelled':'cancelled', 'canceled':'cancelled'}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def units(value):
    try:
        v = Decimal(str(value))
        if not v.is_finite() or v < 0 or v * 1000 != (v * 1000).to_integral_value():
            raise ValueError('Credits must be nonnegative with at most three decimals.')
        return int(v * 1000)
    except InvalidOperation as exc:
        raise ValueError('Invalid credits.') from exc


def now():
    return datetime.now(timezone.utc).isoformat()


class Ledger:
    def __init__(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, timeout=15, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS budgets(id TEXT PRIMARY KEY, ceiling INTEGER NOT NULL CHECK(ceiling>=0));
        CREATE TABLE IF NOT EXISTS runs(
            id TEXT PRIMARY KEY, fingerprint TEXT UNIQUE NOT NULL, payload TEXT NOT NULL,
            budget_id TEXT NOT NULL REFERENCES budgets(id), reservation INTEGER NOT NULL,
            state TEXT NOT NULL, provider_job_id TEXT UNIQUE, raw_status TEXT,
            artifact_sha256 TEXT, artifact_bytes INTEGER);
        CREATE TABLE IF NOT EXISTS events(
            sequence INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL REFERENCES runs(id),
            observed_at TEXT NOT NULL, event TEXT NOT NULL, payload TEXT NOT NULL);
        ''')

    def close(self):
        self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    @contextmanager
    def transaction(self):
        self.db.execute('BEGIN IMMEDIATE')
        try:
            yield
            self.db.commit()
        except BaseException:
            self.db.rollback()
            raise

    def event(self, run_id, kind, payload):
        self.db.execute('INSERT INTO events(run_id,observed_at,event,payload) VALUES(?,?,?,?)',
                        (run_id, now(), kind, canonical(payload)))

    def get(self, run_id):
        row = self.db.execute('SELECT * FROM runs WHERE id=?', (run_id,)).fetchone()
        if row is None:
            raise ValueError('Unknown run.')
        result = dict(row)
        result['payload'] = json.loads(result['payload'])
        result['media_verified'] = result['artifact_sha256'] is not None
        result['artistic_approval'] = 'not_recorded_by_this_ledger'
        return result

    def set_budget(self, budget_id, ceiling):
        if not isinstance(budget_id, str) or not budget_id.strip():
            raise ValueError('Budget ID required.')
        limit = units(ceiling)
        with self.transaction():
            used = self.db.execute('SELECT coalesce(sum(reservation),0) FROM runs WHERE budget_id=?', (budget_id,)).fetchone()[0]
            if limit < used:
                raise ValueError('Ceiling is below existing reservations.')
            self.db.execute('INSERT INTO budgets VALUES(?,?) ON CONFLICT(id) DO UPDATE SET ceiling=excluded.ceiling', (budget_id,limit))
        return dict(budget_id=budget_id, ceiling_credits=limit/1000, reserved_credits=used/1000)

    def plan(self, run_id, payload, budget_id, max_credits):
        if not isinstance(run_id, str) or not run_id.strip() or not isinstance(payload, dict):
            raise ValueError('Run ID and object payload required.')
        for key in ('project', 'shot_id', 'model', 'prompt', 'variation'):
            if not isinstance(payload.get(key), str) or not payload[key].strip():
                raise ValueError('Required request string: ' + key)
        if payload['project'] != 'bojart.creative':
            raise ValueError('Only the BOJART creative domain is supported.')
        if not isinstance(payload.get('parameters'), dict) or not isinstance(payload.get('inputs'), list):
            raise ValueError('Parameters object and input list required.')
        for source in payload['inputs']:
            if not isinstance(source, dict) or not source.get('asset_id') or not source.get('role'):
                raise ValueError('Each input needs a stable asset ID and role.')
            sha = source.get('sha256', '')
            if not isinstance(sha,str) or len(sha)!=64 or any(c not in '0123456789abcdef' for c in sha):
                raise ValueError('Each input needs a SHA-256 of the actual bytes.')
        data = canonical(payload)
        fp = hashlib.sha256(data.encode()).hexdigest()
        reserve = units(max_credits)
        with self.transaction():
            existing = self.db.execute('SELECT id,fingerprint,budget_id,reservation FROM runs WHERE id=? OR fingerprint=?', (run_id,fp)).fetchall()
            if existing:
                if len(existing)==1 and existing[0]['id']==run_id and existing[0]['fingerprint']==fp and existing[0]['budget_id']==budget_id and existing[0]['reservation']==reserve:
                    return self.get(run_id)
                raise ValueError('Duplicate request or changed existing run; reconcile before a new attempt.')
            budget = self.db.execute('SELECT ceiling FROM budgets WHERE id=?', (budget_id,)).fetchone()
            used = self.db.execute('SELECT coalesce(sum(reservation),0) FROM runs WHERE budget_id=?', (budget_id,)).fetchone()[0]
            if budget is None or used + reserve > budget['ceiling']:
                raise ValueError('No budget or insufficient remaining ceiling.')
            self.db.execute('INSERT INTO runs(id,fingerprint,payload,budget_id,reservation,state) VALUES(?,?,?,?,?,?)',
                            (run_id,fp,data,budget_id,reserve,'prepared'))
            self.event(run_id, 'prepared', {'reservation_millicredits':reserve})
        return self.get(run_id)

    def begin(self, run_id):
        with self.transaction():
            result = self.db.execute("UPDATE runs SET state='submitting' WHERE id=? AND state='prepared'", (run_id,))
            if result.rowcount != 1:
                raise ValueError('Run already claimed or unknown; never submit it again blindly.')
            self.event(run_id, 'submission_claimed', {})
        return self.get(run_id)

    def unknown(self, run_id):
        with self.transaction():
            r = self.get(run_id)
            if r['state'] not in {'submitting','submitted','running','unknown'}:
                raise ValueError('Cannot mark this state unknown.')
            if r['state'] != 'unknown':
                self.db.execute("UPDATE runs SET state='unknown' WHERE id=?", (run_id,))
                self.event(run_id, 'reconciliation_required', {})
        return self.get(run_id)

    def receipt(self, run_id, job_id, raw_status):
        if not isinstance(job_id, str) or not job_id.strip():
            raise ValueError('Provider job ID required.')
        if not isinstance(raw_status,str) or not raw_status.strip():
            raise ValueError('Raw provider status required.')
        state = PROVIDER_STATES.get(raw_status, 'unknown')
        with self.transaction():
            r = self.get(run_id)
            if r['state']=='prepared':
                raise ValueError('Claim the request before recording the submission receipt.')
            if r['provider_job_id'] and r['provider_job_id'] != job_id:
                raise ValueError('Provider receipt does not belong to this run.')
            if r['state'] in TERMINAL and state != r['state']:
                raise ValueError('Terminal state conflict; manual reconciliation required.')
            if r['state']=='running' and state=='submitted':
                raise ValueError('Stale provider event; keep the running state.')
            if r['raw_status']==raw_status and r['provider_job_id']==job_id:
                return r
            self.db.execute('UPDATE runs SET state=?,provider_job_id=?,raw_status=? WHERE id=?', (state,job_id,raw_status,run_id))
            self.event(run_id, 'provider_receipt', {'job_id':job_id,'raw_status':raw_status,'state':state})
        return self.get(run_id)

    def attach(self, run_id, path, expected_sha256):
        path = Path(path)
        with path.open('rb') as stream:
            actual = hashlib.file_digest(stream,'sha256').hexdigest()
            size = stream.seek(0, 2)
        if size==0 or actual != expected_sha256:
            raise ValueError('Empty media or hash mismatch.')
        with self.transaction():
            r = self.get(run_id)
            if r['state']!='completed':
                raise ValueError('Provider result is not completed.')
            if r['artifact_sha256'] and r['artifact_sha256']!=actual:
                raise ValueError('A different artifact is already attached.')
            if not r['artifact_sha256']:
                self.db.execute('UPDATE runs SET artifact_sha256=?,artifact_bytes=? WHERE id=?', (actual,size,run_id))
                self.event(run_id, 'bytes_verified', {'sha256':actual,'bytes':size})
        return self.get(run_id)

    def export(self):
        return {'schema_version':1,
            'runs':[self.get(r[0]) for r in self.db.execute('SELECT id FROM runs ORDER BY id')],
            'events':[dict(row) for row in self.db.execute('SELECT * FROM events ORDER BY sequence')],
            'limits':['Local ledger only; no provider call or machine command.',
                      'Reservations remain consumed even on failures; no inferred refund.',
                      'Byte verification does not establish media decoding or artistic quality.']}

    def backup(self, destination):
        destination=Path(destination)
        # O_EXCL reserves a new file, never overwrites another backup.
        with destination.open('xb'):
            pass
        try:
            target = sqlite3.connect(destination)
            try:
                self.db.backup(target)
            finally:
                target.close()
        except BaseException:
            destination.unlink(missing_ok=True)
            raise
        return {'path':str(destination),'status':'sqlite_backup_created'}
