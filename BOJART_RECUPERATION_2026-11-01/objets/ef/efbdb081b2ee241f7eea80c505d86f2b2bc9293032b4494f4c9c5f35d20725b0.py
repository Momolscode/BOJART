#!/usr/bin/env python3
"""Pilote de contexte Marwin 0.1: journal local et contrôle de cohérence.

Aucun appel réseau, modèle, génération ou lancement de tâche externe.
Les références déclarées sont conservées, pas authentifiées par ce module.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
from zoneinfo import ZoneInfo


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


class Conflict(ValueError):
    """Une version ou un identifiant contredit un enregistrement existant."""


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def validate(event, previous=None):
    required = {"event_id", "project", "kind", "entity_id", "expected_revision", "data"}
    if not isinstance(event, dict) or set(event) != required:
        raise ValueError("Champs attendus: " + ", ".join(sorted(required)))
    if not all(nonempty(event[k]) for k in ("event_id", "project", "entity_id")):
        raise ValueError("Identifiants non vides requis")
    if event["kind"] not in {"claim", "handoff"}:
        raise ValueError("Type attendu: claim ou handoff")
    if type(event["expected_revision"]) is not int or event["expected_revision"] < 0:
        raise ValueError("expected_revision doit être un entier positif ou nul")
    d = event["data"]
    if not isinstance(d, dict):
        raise ValueError("data doit être un objet")
    date.fromisoformat(d["observed_on"])
    refs = d.get("evidence_refs", [])
    if not isinstance(refs, list) or not all(nonempty(r) for r in refs):
        raise ValueError("evidence_refs doit contenir des références textuelles")
    if event["kind"] == "handoff":
        if not all(nonempty(d.get(k)) for k in ("owner", "mission_id", "summary", "next_action")):
            raise ValueError("Passation: responsable, mission, bilan et prochaine action requis")
        if not refs:
            raise ValueError("Passation sans référence")
        return
    if not all(nonempty(d.get(k)) for k in ("subject", "predicate")) or "value" not in d:
        raise ValueError("Affirmation: sujet, propriété et valeur requis")
    if d.get("status") not in {"reported", "observed", "hypothesis"}:
        raise ValueError("Statut de preuve inconnu")
    if d["status"] != "hypothesis" and not refs:
        raise ValueError("Fait déclaré ou observé sans référence")
    if "active" in d and type(d["active"]) is not bool:
        raise ValueError("active doit être un booléen")
    if "valid_until" in d:
        date.fromisoformat(d["valid_until"])
    if previous and previous.get("status") == "hypothesis" and d["status"] != "hypothesis":
        if not nonempty(d.get("promotion_reason")):
            raise ValueError("Promotion d'hypothèse: preuve et raison explicites requises")


class Ledger:
    def __init__(self, filename):
        self.db = sqlite3.connect(str(filename), timeout=5, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.executescript("""
          CREATE TABLE IF NOT EXISTS events (
            seq INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT NOT NULL UNIQUE, digest TEXT NOT NULL,
            request TEXT NOT NULL, recorded_at TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS entities (
            project TEXT NOT NULL, kind TEXT NOT NULL, entity_id TEXT NOT NULL,
            revision INTEGER NOT NULL, body TEXT NOT NULL,
            PRIMARY KEY(project, kind, entity_id));
        """)

    def close(self):
        self.db.close()

    def ingest(self, event):
        # Tout contrôle et toute écriture du même événement partagent une transaction.
        validate(event)
        request = canonical(event)
        digest = hashlib.sha256(request.encode()).hexdigest()
        self.db.execute("BEGIN IMMEDIATE")
        try:
            old_event = self.db.execute(
                "SELECT digest FROM events WHERE event_id=?", (event["event_id"],)
            ).fetchone()
            if old_event:
                if old_event["digest"] != digest:
                    raise Conflict("Identifiant d'événement réutilisé avec un autre contenu")
                self.db.execute("COMMIT")
                return {"status": "duplicate", "event_id": event["event_id"]}
            key = (event["project"], event["kind"], event["entity_id"])
            old = self.db.execute(
                "SELECT revision,body FROM entities WHERE project=? AND kind=? AND entity_id=?", key
            ).fetchone()
            revision = old["revision"] if old else 0
            if event["expected_revision"] != revision:
                raise Conflict(f"Version attendue {event['expected_revision']}, version courante {revision}")
            validate(event, json.loads(old["body"]) if old else None)
            self.db.execute(
                "INSERT INTO events(event_id,digest,request,recorded_at) VALUES(?,?,?,?)",
                (event["event_id"], digest, request, datetime.now(timezone.utc).isoformat()),
            )
            self.db.execute(
                "INSERT INTO entities VALUES(?,?,?,?,?) ON CONFLICT(project,kind,entity_id) "
                "DO UPDATE SET revision=excluded.revision,body=excluded.body",
                (*key, revision + 1, canonical(event["data"])),
            )
            self.db.execute("COMMIT")
            return {"status": "applied", "revision": revision + 1, "event_id": event["event_id"]}
        except Exception:
            self.db.execute("ROLLBACK")
            raise

    def snapshot(self, project):
        rows = self.db.execute(
            "SELECT * FROM entities WHERE project=? ORDER BY kind,entity_id", (project,)
        ).fetchall()
        return [{"project": r["project"], "kind": r["kind"], "entity_id": r["entity_id"],
                 "revision": r["revision"], "data": json.loads(r["body"])} for r in rows]

    def events(self):
        return [json.loads(r["request"]) for r in self.db.execute("SELECT request FROM events ORDER BY seq")]


def audit(entities, project, on=None):
    today = date.fromisoformat(on) if on else datetime.now(ZoneInfo("Europe/Paris")).date()
    groups = defaultdict(list)
    expired, hypotheses, missing = [], [], []
    for e in entities:
        if e["project"] != project or e["kind"] != "claim":
            continue
        d = e["data"]
        if not d.get("active", True):
            continue
        if d["status"] == "hypothesis":
            hypotheses.append(e["entity_id"])
            continue
        if not d.get("evidence_refs"):
            missing.append(e["entity_id"])
        if d.get("valid_until") and date.fromisoformat(d["valid_until"]) < today:
            expired.append(e["entity_id"])
            continue
        groups[(d["subject"], d["predicate"])].append(e)
    conflicts = []
    for (subject, predicate), claims in sorted(groups.items()):
        if len({canonical(c["data"]["value"]) for c in claims}) > 1:
            conflicts.append({"subject": subject, "predicate": predicate,
                              "claims": [{"id": c["entity_id"], "value": c["data"]["value"],
                                          "sources": c["data"].get("evidence_refs", [])} for c in claims]})
    return {"project": project, "checked_on": today.isoformat(),
            "coherent_for_checked_fields": not (conflicts or expired or missing),
            "conflicts": conflicts, "expired": expired, "missing_sources": missing,
            "hypotheses_not_promoted": hypotheses,
            "scope": "Contrôle des champs explicitement structurés ; pas vérification sémantique des sources ni preuve de qualité artistique."}


def brief(entities, project, on=None, max_words=700):
    report = audit(entities, project, on)
    selected = [e for e in entities if e["project"] == project]
    header = [f"# Reprise {project}",
              "État : " + ("cohérent pour les champs contrôlés" if report["coherent_for_checked_fields"] else "rapprochement nécessaire"),
              f"Conflits : {len(report['conflicts'])} ; faits expirés : {len(report['expired'])}."]
    mandatory, optional = [], []
    for e in selected:
        d = e["data"]
        if e["kind"] == "claim":
            if not d.get("active", True) or e["entity_id"] in report["expired"]:
                continue
            line = f"- [{d['status']}] {d['subject']} / {d['predicate']} : {canonical(d['value'])}. Source : " + ", ".join(d.get("evidence_refs", []))
            (mandatory if d.get("critical") else optional).append(line)
        else:
            optional.append(f"- Mission {d['mission_id']} ({d['owner']}) : {d['summary']} Prochaine action : {d['next_action']}")
    lines = header + mandatory
    reserve = 15
    if len(" ".join(lines).split()) + reserve > max_words:
        raise ValueError("Budget insuffisant pour conserver les informations critiques")
    omitted = 0
    for line in optional:
        if len(" ".join(lines + [line]).split()) + reserve <= max_words:
            lines.append(line)
        else:
            omitted += 1
    if omitted:
        lines.append(f"Éléments non chargés : {omitted}. Consulter le journal pour le détail.")
    return "\n\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("ingest", "brief", "export"):
        p = sub.add_parser(name)
        p.add_argument("--db", required=True)
        if name == "ingest":
            p.add_argument("--file", required=True)
        if name == "brief":
            p.add_argument("--project", required=True)
            p.add_argument("--on")
            p.add_argument("--max-words", type=int, default=700)
    p = sub.add_parser("audit")
    p.add_argument("--snapshot", required=True)
    p.add_argument("--project", required=True)
    p.add_argument("--on")
    args = parser.parse_args()
    if args.command == "audit":
        snapshot = json.loads(Path(args.snapshot).read_text(encoding="utf-8"))
        report = audit(snapshot["entities"], args.project, args.on)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["coherent_for_checked_fields"] else 2
    ledger = Ledger(args.db)
    try:
        if args.command == "ingest":
            events = json.loads(Path(args.file).read_text(encoding="utf-8"))
            print(json.dumps([ledger.ingest(e) for e in events], ensure_ascii=False, indent=2))
        elif args.command == "export":
            print(json.dumps(ledger.events(), ensure_ascii=False, indent=2))
        else:
            print(brief(ledger.snapshot(args.project), args.project, args.on, args.max_words), end="")
    finally:
        ledger.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
