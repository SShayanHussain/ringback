"""Run the regression evals. `python -m evals.run` (report) · `python -m evals.run --ci` (gate).

Metrics (PRD §7): task success · intent accuracy · false-action rate · escalation appropriateness.
The CI gate FAILS the build below threshold — this is the Phase 3 gate before voice (ROADMAP).
"""
from __future__ import annotations

import sys

from ringback_agent.agent import Agent
from ringback_agent.config import Settings
from ringback_agent.llm.rulebased import RuleBasedNLU
from ringback_agent.state import ConversationState
from ringback_agent.tools import MockCalendar, MockCRM
from ringback_agent.vertical import load_vertical

from .dataset import SCENARIOS, FIXED_CLOCK, Scenario

_WRITE_ACTIONS = {"booking_created", "booking_modified", "booking_cancelled"}

# CI thresholds.
THRESHOLDS = {
    "task_success": 0.90,
    "intent_accuracy": 0.90,
    "false_action_rate": 0.0,        # must be exactly zero
    "escalation_appropriateness": 0.90,
}


def _run_one(sc: Scenario) -> dict:
    vertical = load_vertical("home-services")
    cal = MockCalendar(vertical.business_hours, clock=FIXED_CLOCK)
    for b in sc.seed:
        cal.create_booking(b["service_id"], b["start_iso"], b["name"], b["phone"], b.get("address", ""))
    agent = Agent(vertical=vertical, calendar=cal, crm=MockCRM(), nlu=RuleBasedNLU(), settings=Settings())
    state = ConversationState(vertical="home-services")

    observed_intent = None
    for i, utterance in enumerate(sc.turns):
        result = agent.handle_turn(state, utterance)
        if i == 0:
            observed_intent = result.intent

    wrote = any(a.get("type") in _WRITE_ACTIONS for a in state.actions)
    outcome_ok = state.outcome == sc.expected_outcome
    escalation_ok = state.escalated == sc.expect_escalated and (
        sc.expected_escalation_mode is None or state.escalation_mode == sc.expected_escalation_mode
    )
    intent_ok = sc.expected_intent is None or observed_intent == sc.expected_intent
    false_action = sc.should_not_book and wrote
    booking_ok = (not sc.expect_booking) or wrote

    task_success = outcome_ok and escalation_ok and booking_ok and not false_action
    return {
        "name": sc.name,
        "category": sc.category,
        "task_success": task_success,
        "intent_ok": intent_ok,
        "intent_scored": sc.expected_intent is not None,
        "escalation_ok": escalation_ok,
        "false_action": false_action,
        "outcome": state.outcome,
        "expected_outcome": sc.expected_outcome,
        "observed_intent": observed_intent,
    }


def run() -> dict:
    rows = [_run_one(sc) for sc in SCENARIOS]
    n = len(rows)
    intent_rows = [r for r in rows if r["intent_scored"]]
    metrics = {
        "task_success": sum(r["task_success"] for r in rows) / n,
        "intent_accuracy": (sum(r["intent_ok"] for r in intent_rows) / len(intent_rows))
        if intent_rows else 1.0,
        "false_action_rate": sum(r["false_action"] for r in rows) / n,
        "escalation_appropriateness": sum(r["escalation_ok"] for r in rows) / n,
    }
    return {"rows": rows, "metrics": metrics, "n": n}


def _print_report(report: dict) -> None:
    print("\nRingback - text-core regression evals\n" + "=" * 60)
    for r in report["rows"]:
        flags = []
        if not r["task_success"]:
            flags.append("TASK-FAIL")
        if r["intent_scored"] and not r["intent_ok"]:
            flags.append(f"intent={r['observed_intent']}")
        if not r["escalation_ok"]:
            flags.append("escalation")
        if r["false_action"]:
            flags.append("FALSE-ACTION")
        status = "PASS" if not flags else "FAIL"
        detail = f"  [{', '.join(flags)}]" if flags else ""
        print(f"  {status:4}  {r['category']:11} {r['name']:42}{detail}")
    print("-" * 60)
    m = report["metrics"]
    for key, val in m.items():
        target = THRESHOLDS[key]
        ok = (val <= target) if key == "false_action_rate" else (val >= target)
        cmp = "<=" if key == "false_action_rate" else ">="
        print(f"  {key:28} {val:6.1%}   (target {cmp} {target:.0%})  {'ok' if ok else 'BELOW'}")
    print("=" * 60)


def _passes(metrics: dict) -> bool:
    for key, target in THRESHOLDS.items():
        val = metrics[key]
        if key == "false_action_rate":
            if val > target:
                return False
        elif val < target:
            return False
    return True


def main() -> int:
    ci = "--ci" in sys.argv
    report = run()
    _print_report(report)
    ok = _passes(report["metrics"])
    if ci and not ok:
        print("\nGATE FAILED — text core is not green; voice work stays blocked.\n")
        return 1
    print("\nGATE PASSED - text core is green.\n" if ci else "")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
