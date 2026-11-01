"""Derive a review plan from the existing audit; never execute a task or source."""
from __future__ import annotations

from collections import Counter, defaultdict
from fnmatch import fnmatchcase
import html
from pathlib import PurePosixPath
import re


def require(condition, message):
    if not condition:
        raise ValueError(message)


def safe_path(value):
    require(isinstance(value, str) and bool(value), "invalid path")
    p = PurePosixPath(value)
    require(not p.is_absolute() and ".." not in p.parts
            and "\\" not in value and ":" not in value
            and not any(ord(c) < 32 or ord(c) == 127 for c in value)
            and p.as_posix() == value and value != ".", "unsafe path")
    return value


def plan(audit, config, checkpoint=None, checkpoint_error=None):
    require(isinstance(audit, dict) and isinstance(config, dict), "invalid inputs")
    require(config.get("schema_version") == 1
            and config.get("repository") == "Momolscode/BOJART", "invalid configuration")
    revision = audit.get("revision")
    require(isinstance(revision, str) and re.fullmatch("[0-9a-f]{40}", revision),
            "audit requires an exact Git revision")
    require(type(audit.get("ok")) is bool, "audit result missing")
    batch_size = config.get("batch_size")
    require(type(batch_size) is int and 1 <= batch_size <= 50, "invalid batch size")

    domains = {}
    for d in config["domains"]:
        require(d["id"] not in domains and isinstance(d["label"], str), "duplicate domain")
        require(type(d["priority"]) is int and 0 <= d["priority"] <= 3, "invalid priority")
        require(d["project"] in (None, "bojart.jarvis", "bojart.creative", "bojart.sites"),
                "invalid project")
        domains[d["id"]] = d
    require("unclassified" in domains, "unclassified fallback missing")
    for rule in config["rules"]:
        require(rule["domain"] in domains and bool(rule["patterns"]), "invalid rule")
        require(all(isinstance(p, str) and p for p in rule["patterns"]), "invalid pattern")

    inventory = {}
    for item in audit["files"]:
        name = safe_path(item["path"])
        require(name not in inventory, "duplicate inventory path")
        require(type(item["bytes"]) is int and item["bytes"] >= 0, "invalid byte count")
        require(isinstance(item["sha256"], str)
                and re.fullmatch("[0-9a-f]{64}", item["sha256"]), "invalid digest")
        inventory[name] = item

    # A checkpoint for a different SHA never approves current bytes.
    observation = {"state": "unavailable", "head_sha": None, "pending_paths": [],
                   "diagnostic": checkpoint_error, "same_revision": False}
    if checkpoint is not None:
        try:
            require(checkpoint.get("repository") == config["repository"], "wrong repository")
            pr = checkpoint["pull_requests"].get(str(config["context_audit"]["relay_pull_request"]))
            require(isinstance(pr, dict), "relay entry missing")
            require(re.fullmatch("[0-9a-f]{40}", pr["head_sha"]), "invalid checkpoint revision")
            require(pr["status"] in ("partial", "complete", "blocked"), "invalid checkpoint status")
            require(isinstance(pr["pending_paths"], list), "invalid pending list")
            pending = sorted({safe_path(p) for p in pr["pending_paths"]})
            require(pr["status"] != "complete" or not pending, "complete checkpoint has pending paths")
            observation = {"state": pr["status"], "head_sha": pr["head_sha"],
                           "pending_paths": pending, "diagnostic": None,
                           "same_revision": pr["head_sha"] == revision}
        except (KeyError, TypeError, ValueError, AttributeError):
            observation["state"] = "invalid"
            observation["diagnostic"] = "Checkpoint rejected; no review coverage inferred."
    pending = set(observation["pending_paths"])
    observation["pending_absent_from_inventory"] = sorted(pending - inventory.keys())
    observation["url"] = config["context_audit"]["url"]
    observation["coverage_usable"] = (observation["same_revision"]
                                      and observation["state"] in ("partial", "complete")
                                      and not observation["pending_absent_from_inventory"])
    if observation["same_revision"] and observation["pending_absent_from_inventory"]:
        observation["diagnostic"] = "Checkpoint inventory mismatch; current coverage is unknown."

    classified = []
    for name, item in sorted(inventory.items()):
        match = next((r for r in config["rules"]
                      if any(fnmatchcase(name, p) for p in r["patterns"])), None)
        domain = domains[match["domain"] if match else "unclassified"]
        status = ("pending" if name in pending else "not_listed_pending") \
            if observation["coverage_usable"] else "not_assessed_for_revision"
        classified.append({
            "path": name, "bytes": item["bytes"], "sha256": item["sha256"],
            "domain": domain["id"], "project": domain["project"], "priority": domain["priority"],
            "routing_reason": match["reason"] if match else "No routing rule; review classification.",
            "review_status": status,
        })

    # Equal bytes share a reading unit only within a domain; all paths survive.
    groups = defaultdict(list)
    for item in classified:
        if item["review_status"] != "not_listed_pending":
            groups[(item["domain"], item["sha256"])].append(item)
    units = []
    for (domain, sha), items in groups.items():
        units.append({"domain": domain, "priority": domains[domain]["priority"], "sha256": sha,
                      "paths": sorted(x["path"] for x in items),
                      "review_status": sorted({x["review_status"] for x in items})})
    units.sort(key=lambda u: (u["priority"], u["domain"], u["paths"][0]))
    batches = []
    for domain in sorted(domains, key=lambda d: (domains[d]["priority"], d)):
        selected = [u for u in units if u["domain"] == domain]
        for offset in range(0, len(selected), batch_size):
            batch = selected[offset:offset + batch_size]
            batches.append({"id": f"{domain}-{offset // batch_size + 1:03d}",
                            "domain": domain, "priority": domains[domain]["priority"],
                            "paths_count": sum(len(u["paths"]) for u in batch), "units": batch})

    tasks = {}
    for task in config["tasks"]:
        require(task["id"] not in tasks and task["domain"] in domains, "invalid task")
        require(task["status"] in ("planned", "in_progress", "blocked", "done"), "invalid task status")
        require(type(task["priority"]) is int and 0 <= task["priority"] <= 3, "invalid task priority")
        require(isinstance(task["depends_on"], list) and isinstance(task["blockers"], list),
                "invalid dependencies")
        require(bool(task["evidence"]), "task requires evidence references")
        for path in task["evidence"]:
            require(safe_path(path) in inventory, "task evidence absent from audited inventory")
        require(task["status"] != "done" or not task["blockers"], "done task has blockers")
        require(task["status"] != "blocked" or bool(task["blockers"] or task["depends_on"]),
                "blocked task requires a reason")
        tasks[task["id"]] = dict(task)
    visited, visiting, ordered = set(), set(), []

    def visit(task_id):
        require(task_id in tasks, "unknown task dependency")
        require(task_id not in visiting, "dependency cycle")
        if task_id in visited:
            return
        visiting.add(task_id)
        for parent in sorted(tasks[task_id]["depends_on"]):
            visit(parent)
        visiting.remove(task_id)
        visited.add(task_id)
        ordered.append(task_id)

    for task_id in sorted(tasks, key=lambda t: (tasks[t]["priority"], t)):
        visit(task_id)
    for task in tasks.values():
        waiting = [p for p in task["depends_on"] if tasks[p]["status"] != "done"]
        require(task["status"] != "done" or not waiting, "done task depends on unfinished work")
        task["waiting_for"] = waiting
        task["effective_status"] = "blocked" if waiting or task["blockers"] else task["status"]
        task["status_basis"] = "declared_with_references; not executed by this planner"

    counts = Counter(x["domain"] for x in classified)
    return {
        "schema": "bojart.orchestration.v1", "revision": revision,
        "scope": audit.get("scope", "tracked working-tree files"),
        "structural_audit_ok": audit["ok"], "classification_is_semantic_review": False,
        "tasks_executed": 0, "context_audit": observation,
        "summary": {"files": len(classified), "unique_contents": len({x["sha256"] for x in classified}),
                    "unclassified": counts.get("unclassified", 0), "review_units": len(units),
                    "review_paths": sum(len(u["paths"]) for u in units), "batches": len(batches)},
        "domains": [dict(d, files=counts.get(d["id"], 0)) for d in domains.values()],
        "tasks": [tasks[t] for t in ordered], "review_batches": batches, "files": classified,
        "limits": [
            "Path routing and equal hashes do not prove semantic correctness or artistic approval.",
            "Task completion is declared in the versioned registry, not inferred from green CI.",
            "A different checkpoint SHA leaves every current path unassessed.",
            "Not listed pending is not an independent proof of review.",
            "No source moved or deleted; no machine, model, paid generation or publishing action.",
        ],
    }


def markdown(report):
    def safe(value):
        return html.escape(str(value), quote=False).replace("|", "&#124;").replace("\n", " ").replace(chr(96), "&#96;")
    s, c = report["summary"], report["context_audit"]
    lines = ["# BOJ.ART — plan d'orchestration", "",
             f"Révision effectivement auditée : {safe(report['revision'])}.",
             "Classement par chemins et empreintes ; aucune tâche exécutée.", "",
             f"{s['files']} chemins, {s['unique_contents']} contenus distincts, "
             f"{s['unclassified']} chemins à classer explicitement.",
             f"Revue proposée : {s['review_paths']} chemins / {s['review_units']} unités / {s['batches']} lots.",
             f"Checkpoint : {safe(c['state'])} ; même révision : {str(c['same_revision']).lower()}.", ""]
    if not c["coverage_usable"]:
        lines += ["La couverture contextuelle de cette révision est inconnue ; aucune validation héritée.", ""]
    lines += ["| Domaine | Priorité | Chemins |", "|---|---|---|"]
    for domain in report["domains"]:
        lines.append(f"| {safe(domain['label'])} | P{domain['priority']} | {domain['files']} |")
    lines += ["", "## Tâches et dépendances", "",
              "Les états sont déclarés avec leurs références, sans validation automatique du résultat.", "",
              "| Tâche | État effectif | Attente | Preuve à obtenir |", "|---|---|---|---|"]
    for t in report["tasks"]:
        wait = "; ".join(t["waiting_for"] + t["blockers"]) or "—"
        lines.append("| " + " | ".join(safe(x) for x in
                     (t["title"], t["effective_status"], wait, t["acceptance"])) + " |")
    qualification = report.get("qualification")
    if qualification:
        q = qualification["summary"]
        lines += ["", "## Données à réunir pour les essais", "",
                  f"{q['tool_records']} fiches d'outils, {q['data_requirements']} jeux de données, {q['runtime_gates']} critères reliés au runtime.",
                  "Ce rapport ne qualifie aucune fonction sur la tour. Les dépendances ordonnent la collecte ; les prérequis des tâches restent applicables.", "",
                  "| Donnée | Critères concernés | Outils P0 actifs | Outils actifs | État déclaré |",
                  "|---|---|---|---|---|"]
        for row in qualification["datasets"]:
            lines.append("| " + " | ".join(safe(x) for x in
                         (row["id"], row["gate_count"], row["p0_tool_count"], row["active_tool_count"], row["declared_status"])) + " |")
        lines += ["", "Outils différés ou exclus conservés dans le JSON, sans augmenter la priorité de collecte.", "",
                  "| Critère du runtime | Tâches | Données requises | État |", "|---|---|---|---|"]
        for gate in qualification["gates"]:
            lines.append("| " + " | ".join(safe(x) for x in
                         (gate["label"], ", ".join(gate["task_ids"]), ", ".join(gate["required_datasets"]), gate["status"])) + " |")
    lines += ["", "## Premiers lots de lecture", "",
              "Tous les lots, chemins conservés et empreintes sont dans orchestration.json.", "",
              "| Lot | Unités | Chemins | Premier chemin |", "|---|---|---|---|"]
    for b in report["review_batches"][:12]:
        lines.append("| " + " | ".join(safe(x) for x in
                     (b["id"], len(b["units"]), b["paths_count"], b["units"][0]["paths"][0])) + " |")
    lines += ["", "## Limites", ""] + ["- " + safe(x) for x in report["limits"]]
    return "\n".join(lines) + "\n"
