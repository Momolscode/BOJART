import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from bojart_ops.orchestration import markdown, plan
from tools import orchestrate

ROOT = Path(__file__).resolve().parents[1]
SHA = "a" * 40


def entry(path, content="x"):
    raw = content.encode()
    return {"path": path, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


class OrchestrationTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((ROOT / "ops/orchestration.json").read_text(encoding="utf-8"))
        paths = {p for t in self.config["tasks"] for p in t["evidence"]}
        self.audit = {"revision": SHA, "ok": True, "scope": "fixture",
                      "files": [entry(p, p) for p in sorted(paths)]}

    def checkpoint(self, **changes):
        pr = dict(head_sha=SHA, status="partial", pending_paths=["context/CURRENT.md"])
        pr.update(changes)
        return {"repository": "Momolscode/BOJART", "pull_requests": {"1": pr}}

    def test_all_paths_preserved_and_no_action_executed(self):
        report = plan(self.audit, self.config)
        self.assertEqual({x["path"] for x in report["files"]}, {x["path"] for x in self.audit["files"]})
        self.assertEqual(report["tasks_executed"], 0)
        self.assertFalse(report["classification_is_semantic_review"])
        self.assertEqual(report["summary"]["review_paths"], len(self.audit["files"]))

    def test_current_checkpoint_only_uses_explicit_pending_paths(self):
        report = plan(self.audit, self.config, self.checkpoint())
        self.assertTrue(report["context_audit"]["coverage_usable"])
        self.assertEqual(report["summary"]["review_paths"], 1)
        self.assertEqual(report["files"][0]["review_status"], "not_listed_pending")
        self.assertNotIn("reviewed", {f["review_status"] for f in report["files"]})

    def test_stale_checkpoint_cannot_approve_current_revision(self):
        report = plan(self.audit, self.config, self.checkpoint(head_sha="b" * 40, status="complete", pending_paths=[]))
        self.assertFalse(report["context_audit"]["same_revision"])
        self.assertEqual(report["summary"]["review_paths"], len(self.audit["files"]))

    def test_invalid_checkpoint_does_not_remove_work(self):
        for cp in ({}, {"repository": "another/repo"}, self.checkpoint(pending_paths=["../secret"]),
                   self.checkpoint(status="complete")):
            with self.subTest(cp=cp):
                report = plan(self.audit, self.config, cp)
                self.assertEqual(report["context_audit"]["state"], "invalid")
                self.assertEqual(report["summary"]["review_paths"], len(self.audit["files"]))

    def test_checkpoint_missing_paths_or_blocked_status_cannot_claim_coverage(self):
        for cp in (self.checkpoint(pending_paths=["absent.txt"]),
                   self.checkpoint(status="blocked", pending_paths=[])):
            report = plan(self.audit, self.config, cp)
            self.assertTrue(report["context_audit"]["same_revision"])
            self.assertFalse(report["context_audit"]["coverage_usable"])
            self.assertEqual(report["summary"]["review_paths"], len(self.audit["files"]))

    def test_duplicates_share_reading_unit_without_losing_provenance(self):
        self.audit["files"] += [entry("bojart_memory/a.py"), entry("bojart_memory/b.py"),
                                entry("sites/c.py")]
        report = plan(self.audit, self.config)
        units = [u for b in report["review_batches"] for u in b["units"] if u["sha256"] == entry("x")["sha256"]]
        self.assertEqual(len(units), 2)
        self.assertEqual(next(u for u in units if u["domain"] == "memory")["paths"],
                         ["bojart_memory/a.py", "bojart_memory/b.py"])

    def test_specific_historical_and_creative_routes_precede_runtime(self):
        self.audit["files"] += [entry("jarvis/apps/jarvis/heritage/old.md"),
                                entry("jarvis/knowledge/growth/topics.json")]
        mapping = {f["path"]: f for f in plan(self.audit, self.config)["files"]}
        self.assertEqual(mapping["jarvis/apps/jarvis/heritage/old.md"]["domain"], "history")
        self.assertIsNone(mapping["jarvis/apps/jarvis/heritage/old.md"]["project"])
        self.assertEqual(mapping["jarvis/knowledge/growth/topics.json"]["project"], "bojart.creative")

    def test_unknown_path_visible_at_priority_zero(self):
        self.audit["files"].append(entry("new-component/source.rs"))
        report = plan(self.audit, self.config)
        unknown = next(f for f in report["files"] if f["domain"] == "unclassified")
        self.assertEqual(unknown["priority"], 0)
        self.assertEqual(report["summary"]["unclassified"], 1)

    def test_preinstallation_proposals_do_not_become_decisions_or_approval(self):
        paths = {
            "docs/preinstallation/knowledge/01-recherche-citee.txt": "research",
            "data/preinstallation/knowledge-cards.json": "research",
            "data/preinstallation/sources-curated.json": "research",
            "data/preinstallation/tool-registry.json": "research",
            "data/preinstallation/requirements.json": "continuity",
            "data/preinstallation/target-profile.json": "continuity",
            "data/preinstallation/retrieval-cases.json": "memory",
            "data/preinstallation/target-inventory.template.json": "operations",
            "skills/bojart-context-reconstruction/SKILL.md": "operations",
            "skills/bojart-evidence-audit/SKILL.md": "operations",
            "skills/bojart-evidence-audit/references/acceptance.md": "operations",
            "skills/bojart-tool-qualification/SKILL.md": "operations",
            "data/preinstallation/unreviewed-category.json": "unclassified",
        }
        self.audit["files"] += [entry(path) for path in paths]
        report = plan(self.audit, self.config)
        mapping = {f["path"]: f for f in report["files"]}
        for path, domain in paths.items():
            with self.subTest(path=path):
                self.assertEqual(mapping[path]["domain"], domain)
                self.assertEqual(mapping[path]["review_status"], "not_assessed_for_revision")
                if domain == "research":
                    self.assertIsNone(mapping[path]["project"])
        self.assertFalse(report["classification_is_semantic_review"])
        self.assertEqual(report["tasks_executed"], 0)

    def test_dependencies_block_installation_and_master(self):
        tasks = {t["id"]: t for t in plan(self.audit, self.config)["tasks"]}
        self.assertEqual(tasks["target-install"]["effective_status"], "blocked")
        self.assertIn("target-inventory", tasks["target-install"]["waiting_for"])
        self.assertEqual(tasks["master-review"]["waiting_for"], ["g2-source"])
        self.assertEqual(tasks["sites-contract"]["effective_status"], "planned")

    def test_cycle_and_unknown_dependency_refused(self):
        for dependency in ("target-install", "missing-task"):
            config = copy.deepcopy(self.config)
            next(t for t in config["tasks"] if t["id"] == "target-inventory")["depends_on"] = [dependency]
            with self.assertRaises(ValueError):
                plan(self.audit, config)

    def test_done_with_unfinished_parent_refused(self):
        task = next(t for t in self.config["tasks"] if t["id"] == "target-install")
        task["status"] = "done"
        with self.assertRaises(ValueError):
            plan(self.audit, self.config)

    def test_missing_task_evidence_refused(self):
        self.audit["files"] = [f for f in self.audit["files"] if f["path"] != "context/CURRENT.md"]
        with self.assertRaises(ValueError):
            plan(self.audit, self.config)

    def test_unsafe_duplicate_and_invalid_inventory_refused(self):
        for item in (entry("../escape"), entry("/absolute"), entry("C:/escape"), entry("a\\b"),
                     entry("a\nb"), self.audit["files"][0],
                     dict(entry("bad"), sha256="invalid"), dict(entry("bad"), bytes=-1)):
            with self.subTest(item=item):
                audit = copy.deepcopy(self.audit)
                audit["files"].append(item)
                with self.assertRaises(ValueError):
                    plan(audit, self.config)

    def test_bounded_batches_deterministic_and_no_mutation(self):
        self.config["batch_size"] = 2
        before = copy.deepcopy((self.audit, self.config))
        report = plan(self.audit, self.config)
        self.assertTrue(all(1 <= len(b["units"]) <= 2 for b in report["review_batches"]))
        reverse = copy.deepcopy(self.audit)
        reverse["files"].reverse()
        self.assertEqual(report, plan(reverse, self.config))
        self.assertEqual((self.audit, self.config), before)

    def test_failed_structural_audit_remains_failed(self):
        self.audit["ok"] = False
        self.assertFalse(plan(self.audit, self.config)["structural_audit_ok"])

    def test_markdown_escapes_untrusted_labels(self):
        self.config["tasks"][0]["title"] = "<script>run()</script>|bad\nrow"
        text = markdown(plan(self.audit, self.config))
        self.assertNotIn("<script>", text)
        self.assertIn("&lt;script&gt;", text)
        self.assertIn("&#124;bad row", text)

    def test_repository_registry_resolves_against_manifest(self):
        source = ROOT / "data/catalog/repository_manifest.json"
        inventory = json.loads(source.read_text(encoding="utf-8"))["files"]
        raw = source.read_bytes()
        inventory.append({"path": source.relative_to(ROOT).as_posix(), "bytes": len(raw),
                          "sha256": hashlib.sha256(raw).hexdigest()})
        report = plan({"revision": SHA, "ok": True, "files": inventory}, self.config)
        self.assertEqual(report["summary"]["unclassified"], 0)


class CommandTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.config = {"schema_version": 1, "repository": "Momolscode/BOJART", "batch_size": 20,
                       "domains": [{"id": "unclassified", "label": "Unknown", "project": None, "priority": 0}],
                       "rules": [], "tasks": [], "context_audit": {"relay_pull_request": 1, "url": "https://github.com/Momolscode/BOJART"}}
        self.audit = {"revision": SHA, "ok": True, "files": [entry("readme.txt")]}
        for name, value in (("config.json", self.config), ("audit.json", self.audit)):
            (self.root / name).write_text(json.dumps(value), encoding="utf-8")

    def run_cli(self, *extra, revision=SHA):
        argv = ["orchestrate", "--audit", str(self.root / "audit.json"),
                "--config", str(self.root / "config.json"), *extra]
        with patch.object(orchestrate, "ROOT", self.root), patch("sys.argv", argv), \
                patch.object(orchestrate.subprocess, "check_output", return_value=revision):
            return orchestrate.main()

    def test_missing_checkpoint_reports_unknown_and_writes_only_reports(self):
        self.assertEqual(self.run_cli("--checkpoint", str(self.root / "missing.json")), 0)
        result = json.loads((self.root / ".bojart-audit/orchestration.json").read_text(encoding="utf-8"))
        self.assertEqual(result["context_audit"]["state"], "unavailable")
        self.assertEqual(result["summary"]["review_paths"], 1)
        self.assertEqual(result["tasks_executed"], 0)
        self.assertIsNone(result["input_sha256"]["checkpoint"])

    def test_stale_audit_refused_before_writing(self):
        with self.assertRaises(ValueError):
            self.run_cli(revision="b" * 40)
        self.assertFalse((self.root / ".bojart-audit").exists())

    def test_output_cannot_replace_source_tree(self):
        with self.assertRaises(ValueError):
            self.run_cli("--output", str(self.root))
        self.assertFalse((self.root / "orchestration.json").exists())

    def test_duplicate_json_keys_refused(self):
        (self.root / "audit.json").write_text('{"revision":"x","revision":"y"}')
        with self.assertRaises(ValueError):
            self.run_cli()


if __name__ == "__main__":
    unittest.main()
