#!/usr/bin/env python3
"""Semantische Konsistenzprüfung der kanonischen Workflow-Regeln.

Prüft Beziehungen, die JSON Schema allein nicht ausdrücken kann:
Statusgraph, Projekt-KI-Defaults, Kostenquellen, Freigabeschranken,
Strukturänderungen und GitHub-Issue-Policy.
"""
import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent.parent
SECTION_STATES = {"planned", "research", "brainstorming", "ready_to_write", "writing",
                  "revision", "fact_check", "ready_for_approval", "approved"}
CHAPTER_STATES = {"planned", "in_progress", "ready_for_assembly", "assembly",
                  "review", "ready_for_approval", "approved"}


def main():
    errors = []
    workflow = yaml.safe_load((ROOT / "workflow.yml").read_text(encoding="utf-8"))
    workflow_schema = json.loads((ROOT / "schemas/workflow.schema.json").read_text(encoding="utf-8"))
    schema_errors = list(Draft202012Validator(workflow_schema).iter_errors(workflow))
    errors.extend(f"workflow.yml: JSON-Schema: {'/'.join(map(str, e.absolute_path))}: {e.message}"
                  for e in schema_errors)

    config = yaml.safe_load((ROOT / "ghostwriter.yml").read_text(encoding="utf-8"))
    policy = workflow.get("global_ai_policy") or {}
    project_policy = config.get("ai_settings") or {}
    strictness = {
        "hallucination_policy": {"off": 0, "standard": 1, "strict": 2},
        "source_policy": {"optional": 0, "recommended": 1, "required": 2},
        "uncertainty_policy": {"off": 0, "normal": 1, "explicit": 2},
        "creativity": {"creative": 0, "balanced": 1, "conservative": 2},
        "web_research": {"none": 0, "research": 1, "mandatory": 2},
    }
    for key, levels in strictness.items():
        base, chosen = policy.get(key), project_policy.get(key)
        if base not in levels or chosen not in levels:
            errors.append(f"KI-Regel {key}: unbekannter Wert workflow.yml={base!r}, ghostwriter.yml={chosen!r}")
        elif levels[chosen] < levels[base]:
            errors.append(f"KI-Regel {key}: ghostwriter.yml lockert die globale Vorgabe {base!r} auf {chosen!r}")

    section_schema = json.loads((ROOT / "schemas/section.schema.json").read_text(encoding="utf-8"))
    section_enum = set(section_schema["properties"]["status"]["enum"])
    if section_enum != SECTION_STATES:
        errors.append("schemas/section.schema.json: Statusliste weicht von der kanonischen Abschnitts-Statusliste ab")
    if set(workflow["entities"]["section"]["statuses"]) != section_enum:
        errors.append("workflow.yml: entities.section.statuses weicht vom Abschnittsschema ab")
    if set(workflow["entities"]["chapter"]["statuses"]) != CHAPTER_STATES:
        errors.append("workflow.yml: entities.chapter.statuses ist unvollständig oder enthält unbekannte Werte")

    for name, allowed in (("section_workflow", SECTION_STATES), ("chapter_workflow", CHAPTER_STATES)):
        model = workflow[name]
        if model.get("initial_status") not in allowed:
            errors.append(f"workflow.yml: {name}.initial_status ist kein definierter Status")
        seen = set()
        for edge in model.get("transitions", []):
            pair = (edge.get("from"), edge.get("to"))
            identity = (*pair, edge.get("trigger"))
            if identity in seen:
                errors.append(f"workflow.yml: doppelter Übergang in {name}: {pair[0]} -> {pair[1]} ({identity[2]})")
            seen.add(identity)
            if pair[0] not in allowed or pair[1] not in allowed:
                errors.append(f"workflow.yml: unbekannter Status in {name}: {pair[0]} -> {pair[1]}")
        if not any(edge.get("from") == "approved" for edge in model.get("transitions", [])):
            errors.append(f"workflow.yml: {name} definiert keinen Rückweg aus approved")

    changes = workflow.get("structure_changes") or {}
    for operation in ("add_section", "rename_or_reorder", "move_section", "split_or_delete"):
        rule = changes.get(operation) or {}
        if rule.get("reset_affected_chapter_status") != "in_progress" and rule.get("always_reset_chapter_status") != "in_progress" and rule.get("reset_source_and_target_chapters_to") != "in_progress":
            errors.append(f"workflow.yml: structure_changes.{operation} setzt betroffene Kapitel nicht auf in_progress zurück")
        if not (rule.get("invalidate_chapter_approval") or rule.get("invalidate_affected_chapter_approval")):
            errors.append(f"workflow.yml: structure_changes.{operation} invalidiert Kapitel-Freigaben nicht")

    approvals = workflow.get("github_automation", {}).get("approval_policy", {})
    for key in ("github_issue_closure_is_not_user_approval", "milestone_completion_is_not_user_approval", "only_explicit_chat_confirmation_counts"):
        if approvals.get(key) is not True:
            errors.append(f"workflow.yml: github_automation.approval_policy.{key} muss true sein")
    if workflow.get("github_automation", {}).get("issue_per_unit_of_work") is not False:
        errors.append("workflow.yml: Issues pro Arbeitseinheit müssen optional bleiben (keine automatische Pflicht)")
    if workflow.get("github_automation", {}).get("issue_creation") != "optional_or_explicitly_requested":
        errors.append("workflow.yml: Issue-Erstellung muss ausdrücklich optional sein")

    costs_schema = json.loads((ROOT / "schemas/costs.schema.json").read_text(encoding="utf-8"))
    allowed_sources = set(costs_schema["properties"]["entries"]["items"]["properties"]["source"]["enum"])
    configured_sources = set(workflow["cost_tracking"]["activity_record"]["source_values"])
    if not configured_sources <= allowed_sources:
        errors.append(f"workflow.yml: Kostenquellen nicht im Kostenschema: {sorted(configured_sources - allowed_sources)}")
    if "action_api" not in configured_sources:
        errors.append("workflow.yml: action_api-Kosten aus GitHub Actions fehlen")
    required = workflow["cost_tracking"]["activity_record"]["required_fields"]
    if "section_id" in required:
        errors.append("workflow.yml: section_id darf für projektweite Kosteneinträge nicht global verpflichtend sein")
    if workflow["cost_tracking"]["attribution"].get("project_level_activity_may_omit_section_id") is not True:
        errors.append("workflow.yml: projektweite Kosteneinträge müssen ohne section_id möglich sein")

    if errors:
        for error in errors:
            print("✗ " + error)
        return 1
    print("✓ Workflow-Semantik konsistent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
