#!/usr/bin/env python3
"""Adapter des sources documentaires explicites au journal Marwin.

Une passation rédigée et une projection de rapport gardent des origines distinctes.
Cet importeur travaille sur des fichiers fournis ; il ne lit pas les conversations.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from pilote import Conflict, Ledger, canonical


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def capsules_from_sources(continuity, audit_report, continuity_ref, audit_ref):
    h = continuity["reference_learning"]["handoff"]
    a = continuity["global_audit"]
    next_brief = continuity["next_creative_brief"]
    test = audit_report["next_test"]
    if next_brief["title"] != test["title"]:
        raise Conflict("Le rapport et le brief courant ne désignent pas le même essai")
    if not h.get("changed") or not h.get("next_action"):
        raise ValueError("Passation de recherche incomplète")
    research = {
        "owner": h["responsible"], "mission_id": "MAR-01",
        "summary": h["changed"], "next_action": h["next_action"],
        "observed_on": h["date"][:10],
        "evidence_refs": [continuity_ref + " / reference_learning.handoff"]
            + [e["url"] for e in h.get("evidence", []) if e.get("url")],
        "origin": "authored_documentary_handoff",
        "open_questions": h.get("open"),
        "provenance": {"source_pointer": "/reference_learning/handoff",
                       "payload_sha256": digest(h), "source_payload": h},
    }
    selected = {"audit_summary": a, "next_test": test}
    context = {
        "owner": "Session Contexte et scénario", "mission_id": "MAR-02",
        "summary": a["scope"] + " Priorités : " + "; ".join(a["priorities"]),
        "next_action": "Préparer l’essai " + next_brief["id"] + " : " + test["title"]
            + ". Critère : " + test["pass_condition"],
        "observed_on": audit_report["date"][:10],
        "evidence_refs": [continuity_ref + " / global_audit", audit_ref + " / next_test"],
        "origin": "structured_report_projection",
        "normalization_note": "Capsule produite par le pilotage depuis le rapport ; pas une passation rédigée ou un message émis par ce fil.",
        "active_test_id": next_brief["id"],
        "provenance": {"source_pointer": "/global_audit + audit:/next_test",
                       "payload_sha256": digest(selected), "source_payload": selected},
    }
    return [{"entity_id": "research-latest", "data": research},
            {"entity_id": "context-latest", "data": context}]


def event_for_capsule(ledger, capsule, project="marwin"):
    # Le contenu et le périmètre déterminent l'identifiant ; une répétition
    # réutilise la requête initiale, y compris sa révision attendue.
    key = {"project": project, **capsule}
    event_id = "documentary-" + digest(key)
    existing = next((e for e in ledger.events() if e["event_id"] == event_id), None)
    if existing:
        return existing
    current = next((e for e in ledger.snapshot(project)
                    if e["kind"] == "handoff" and e["entity_id"] == capsule["entity_id"]), None)
    return {"event_id": event_id, "project": project, "kind": "handoff",
            "entity_id": capsule["entity_id"],
            "expected_revision": current["revision"] if current else 0,
            "data": capsule["data"]}


def import_sources(ledger, continuity, audit_report, continuity_ref, audit_ref, project="marwin"):
    # Rapprocher les deux documents avant d'enregistrer la première capsule.
    capsules = capsules_from_sources(continuity, audit_report, continuity_ref, audit_ref)
    return [ledger.ingest(event_for_capsule(ledger, c, project)) for c in capsules]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--db", required=True)
    p.add_argument("--continuity", required=True)
    p.add_argument("--audit", required=True)
    p.add_argument("--continuity-ref", required=True)
    p.add_argument("--audit-ref", required=True)
    args = p.parse_args()
    continuity = json.loads(Path(args.continuity).read_text(encoding="utf-8"))
    report = json.loads(Path(args.audit).read_text(encoding="utf-8"))
    ledger = Ledger(args.db)
    try:
        result = import_sources(ledger, continuity, report, args.continuity_ref, args.audit_ref)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        ledger.close()


if __name__ == "__main__":
    main()
