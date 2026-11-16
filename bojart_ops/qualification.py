"""Join proposed tools, data needs and runtime gates without qualifying equipment."""
from __future__ import annotations

import ast
import hashlib
from pathlib import Path
import re

from .audit import strict_json
from .orchestration import require, safe_path

DEFERRED = {"defer", "research_only", "not_selected_current_request", "excluded_for_current_use"}


def unique(rows, key):
    require(isinstance(rows, list), "Expected a list of records")
    result = {}
    for row in rows:
        require(isinstance(row, dict), "Invalid record")
        value = row.get(key)
        require(isinstance(value, str) and re.fullmatch(r"[a-z][a-z0-9_-]*", value), "Invalid identifier")
        require(value not in result, "Duplicate identifier")
        result[value] = row
    return result


def runtime_gates(source):
    """Read only a literal declaration; never import the runtime or its dependencies."""
    declarations = [node.value for node in ast.parse(source).body
                    if isinstance(node, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == "REQUIRED_GATES" for t in node.targets)]
    require(len(declarations) == 1, "Runtime gate declaration missing or ambiguous")
    node = declarations[0]
    require(isinstance(node, ast.Dict), "Runtime gates must remain a literal dictionary")
    keys = [ast.literal_eval(key) for key in node.keys]
    require(all(isinstance(key, str) for key in keys) and len(set(keys)) == len(keys), "Invalid runtime gate IDs")
    value = ast.literal_eval(node)
    require(value and all(isinstance(v, tuple) and len(v) == 2
                         and all(isinstance(x, str) for x in v) for v in value.values()), "Invalid runtime gate descriptions")
    return value


def qualify_plan(toolchain, requirements, acceptance, gates, tasks):
    for document in (toolchain, requirements, acceptance):
        require(document.get("schema_version") == 1, "Unknown proposal schema")
    require(toolchain.get("automatic_install") is False
            and toolchain.get("target_production_qualified") is False
            and acceptance.get("production_ready") is False, "A proposal cannot certify production")
    tools = unique(toolchain["tools"], "id")
    datasets = unique(requirements["datasets"], "id")
    tests = unique(acceptance["tests"], "gate_id")
    require(set(tests) == set(gates), "Acceptance gates differ from the runtime")
    links = {key: [] for key in tests}
    direct = {key: [] for key in datasets}
    for task in tasks:
        for gate in task.get("qualification_gates", []):
            require(gate in tests, "Task references an unknown gate")
            require(task["status"] != "done", "Task claims completion while target recipe is unqualified")
            links[gate].append(task["id"])
        for dataset in task.get("required_datasets", []):
            require(dataset in datasets, "Task references unknown data")
            direct[dataset].append(task["id"])
    require(all(links.values()), "A runtime gate has no orchestration task")

    active, delayed, p0, use_gates = ({key: [] for key in datasets} for _ in range(4))
    for tool in tools.values():
        require(tool.get("priority") in ("P0", "P1", "P2", "excluded"), "Unknown tool priority")
        require(isinstance(tool.get("decision_status"), str), "Missing proposal status")
        if tool.get("repository"):
            require(isinstance(tool.get("examined_commit"), str)
                    and re.fullmatch(r"[0-9a-f]{40}", tool["examined_commit"]), "Repository revision not pinned")
        required = tool.get("required_datasets")
        require(isinstance(required, list) and len(required) == len(set(required)), "Duplicate data dependency")
        for dataset in required:
            require(dataset in datasets, "Tool references unknown data")
            deferred = tool["decision_status"] in DEFERRED or tool["priority"] == "excluded"
            (delayed if deferred else active)[dataset].append(tool["id"])
            if not deferred and tool["priority"] == "P0":
                p0[dataset].append(tool["id"])

    gate_rows = []
    for gate, test in tests.items():
        # This file is a recipe, not a receipt store. Real qualifications have a separate lifecycle.
        require(test.get("status") == "not_run_on_target" and test.get("evidence") is None,
                "Target qualification cannot be promoted by a research file")
        required = test.get("required_datasets")
        require(isinstance(required, list) and required and len(required) == len(set(required)), "Invalid gate data")
        for dataset in required:
            require(dataset in datasets, "Gate references unknown data")
            use_gates[dataset].append(gate)
        gate_rows.append({"id": gate, "label": gates[gate][0], "status": test["status"],
                          "task_ids": sorted(set(links[gate])), "required_datasets": sorted(required),
                          "pass_criteria": test["pass_criteria"]})

    rows = []
    for key, dataset in datasets.items():
        fields = dataset.get("required_fields")
        require(isinstance(fields, list) and fields and all(isinstance(f, str) and f for f in fields)
                and len(set(fields)) == len(fields), "Invalid data fields")
        require(isinstance(dataset.get("status"), str), "Missing data status")
        rows.append({"id": key, "declared_status": dataset["status"],
                     "required_field_count": len(fields), "required_fields": fields,
                     "gate_ids": sorted(use_gates[key]), "active_tool_ids": sorted(active[key]),
                     "deferred_tool_ids": sorted(delayed[key]), "p0_tool_ids": sorted(p0[key]),
                     "direct_task_ids": sorted(set(direct[key])),
                     "gate_count": len(use_gates[key]), "active_tool_count": len(active[key]),
                     "p0_tool_count": len(p0[key])})
    rows.sort(key=lambda row: (-row["gate_count"], -row["p0_tool_count"], -row["active_tool_count"], row["id"]))
    return {"schema": "bojart.qualification-dependencies.v1", "target_production_qualified": False,
            "tools_executed": 0, "tasks_executed": 0,
            "summary": {"tool_records": len(tools), "data_requirements": len(rows), "runtime_gates": len(gates),
                        "target_gates_qualified_by_this_report": 0},
            "ranking_method": "descending gate count, P0 active tool count, active tool count, stable ID",
            "ranking_limit": "Declared dependencies only; not a probability, ROI or proof that collecting data is sufficient. Task prerequisites still apply.",
            "datasets": rows, "gates": sorted(gate_rows, key=lambda row: row["id"])}


def load_qualification(root, audit, config):
    sources = config.get("qualification_sources")
    if sources is None:
        return None
    require(isinstance(sources, dict) and set(sources) == {"tools", "data", "acceptance", "runtime_gates"},
            "Incomplete qualification sources")
    root = Path(root).resolve()
    inventory = {row["path"]: row for row in audit["files"]}
    documents, provenance = {}, {}
    for role, name in sources.items():
        safe_path(name)
        path = root / name
        require(path.resolve().is_relative_to(root) and path.is_file(), "Qualification source outside repository")
        require(not any(p.is_symlink() for p in (path, *path.parents) if p != root and p.is_relative_to(root)),
                "Qualification source is a symlink")
        require(path.stat().st_size <= 1_000_000, "Qualification source too large")
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        require(name in inventory and inventory[name]["sha256"] == digest
                and inventory[name]["bytes"] == len(raw), "Qualification source changed since audit")
        documents[role] = runtime_gates(raw.decode("utf-8")) if role == "runtime_gates" else strict_json(raw.decode("utf-8"))
        provenance[role] = {"path": name, "sha256": digest, "bytes": len(raw)}
    require(documents["acceptance"].get("existing_gates_source") == sources["runtime_gates"], "Acceptance references another runtime")
    report = qualify_plan(documents["tools"], documents["data"], documents["acceptance"], documents["runtime_gates"], config["tasks"])
    report["sources"] = provenance
    return report
