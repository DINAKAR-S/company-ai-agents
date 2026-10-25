import json

import pytest

from orgchart.solve import (
    CRITIQUE_SCHEMA,
    DECISION_SCHEMA,
    MAX_CONTEXT_CHARS,
    MODERATOR,
    POSITION_SCHEMA,
    build_panel,
    solve,
    write_dry_run,
    write_outputs,
)

PROBLEM = "Support tickets pile up after every release and customers wait days; we want an AI triage step."
CONTEXT = "A 30-person B2B SaaS company selling scheduling software to clinics. Uses Zendesk, Linear, Slack."


def fake_call_factory(fail_for: set[str] | None = None, log: list | None = None):
    fail_for = fail_for or set()

    def call(model, system, user, schema):
        if log is not None:
            log.append((model, schema is POSITION_SCHEMA, schema is CRITIQUE_SCHEMA, schema is DECISION_SCHEMA))
        name = system.split("Your name on this panel is ")[1].split(".")[0] if "Your name on this panel is " in system else "mod"
        if name in fail_for:
            raise RuntimeError("simulated 500")
        if schema is POSITION_SCHEMA:
            return {"approach": f"{name}'s approach", "steps": ["a", "b"], "risks": ["r"], "edge_cases": ["empty ticket"],
                    "requirements": ["must log"], "what_breaks_in_the_current_setup": ["helpdesk API rate limit"],
                    "mitigations": ["queue and batch"], "questions_for_the_company": ["volume?"]}
        if schema is CRITIQUE_SCHEMA:
            return {"best_approach_from": "Steven", "why": "simplest", "disagreements": [], "missed_edge_cases": ["unicode subject"],
                    "changes_to_my_position": []}
        assert schema is DECISION_SCHEMA
        return {"decision": "go with the triage step", "plan_md": "# Plan\n\n1. do it", "edge_cases_md": "# Edge cases\n\n| case | expected | test |\n|---|---|---|",
                "requirements_md": "# Requirements\n\n- must log", "open_questions": ["budget?"]}
    return call


def test_panel_has_lead_first_moderator_separate_and_unique_names(catalog):
    panel, moderator, _warnings = build_panel(catalog, PROBLEM, CONTEXT, size=6)
    assert panel[0].role.id == "data-ai/data-ai-solutions-architect"
    assert moderator.role.id == MODERATOR
    names = [p.name for p in panel] + [moderator.name]
    assert len(names) == len(set(names))
    assert len(panel) == 6
    assert any(p.role.id.startswith("customer/") for p in panel)


def test_unknown_lead_and_extra_are_warned_not_fatal(catalog):
    panel, _, warnings = build_panel(catalog, PROBLEM, "", size=4, lead="nope/nope", extra=["also/nope", "legal/privacy-officer"])
    assert panel[0].role.id == "data-ai/data-ai-solutions-architect"
    assert any(p.role.id == "legal/privacy-officer" for p in panel)
    assert len(warnings) == 2


def test_full_session_writes_all_files(catalog, tmp_path):
    log = []
    s = solve(catalog, PROBLEM, CONTEXT, size=4, call=fake_call_factory(log=log))
    assert not s.errors
    assert len(s.positions) == 4 and len(s.critiques) == 4 and s.decision
    written = write_outputs(s, tmp_path)
    names = sorted(p.name for p in written)
    assert names == ["debate.md", "edge-cases.md", "panel.json", "plan.md", "requirements.md"]
    debate = (tmp_path / "debate.md").read_text(encoding="utf-8")
    assert "## Round 3: decision" in debate and "go with the triage step" in debate
    # moderator decides on the deep model regardless of its own hint
    assert log[-1][0] == "claude-opus-5-5" and log[-1][3]


def test_one_panelist_failing_does_not_end_the_session(catalog, tmp_path):
    first = build_panel(catalog, PROBLEM, CONTEXT, size=4)[0][0].name
    s = solve(catalog, PROBLEM, CONTEXT, size=4, call=fake_call_factory(fail_for={first}))
    failed = [e for e in s.errors if first in e]
    assert failed and len(s.positions) == 3
    assert s.decision is not None
    write_outputs(s, tmp_path)
    panel = json.loads((tmp_path / "panel.json").read_text(encoding="utf-8"))
    assert panel["errors"] and panel["rounds_completed"]["positions"] == 3


def test_everything_failing_still_writes_debate_and_panel(catalog, tmp_path):
    def dead(model, system, user, schema):
        raise RuntimeError("API down")
    s = solve(catalog, PROBLEM, CONTEXT, size=3, call=dead)
    assert s.decision is None and not s.positions
    written = write_outputs(s, tmp_path)
    assert sorted(p.name for p in written) == ["debate.md", "panel.json"]
    assert "no decision" in (tmp_path / "debate.md").read_text(encoding="utf-8")


def test_empty_problem_rejected_and_huge_context_truncated(catalog):
    with pytest.raises(ValueError):
        solve(catalog, "  ", call=fake_call_factory())
    s = solve(catalog, PROBLEM, "x" * (MAX_CONTEXT_CHARS + 10), size=2, call=fake_call_factory())
    assert any("truncated" in w for w in s.warnings)
    assert len(s.context) == MAX_CONTEXT_CHARS


def test_dry_run_writes_prompts_and_calls_nothing(catalog, tmp_path):
    panel, moderator, warnings = build_panel(catalog, PROBLEM, CONTEXT, size=3)
    from orgchart.solve import Session
    s = Session(problem=PROBLEM, context=CONTEXT, panel=panel, moderator=moderator, warnings=warnings)
    written = write_dry_run(s, tmp_path)
    text = written[0].read_text(encoding="utf-8")
    assert "Round 1 prompts" in text and "Your name on this panel is" in text
    assert PROBLEM in text


def test_second_run_overwrites_cleanly(catalog, tmp_path):
    s = solve(catalog, PROBLEM, CONTEXT, size=3, call=fake_call_factory())
    first = write_outputs(s, tmp_path)
    second = write_outputs(s, tmp_path)
    assert sorted(first) == sorted(second)


def test_lessons_round_trip_into_the_next_panel(catalog, tmp_path):
    from orgchart.solve import record_lessons
    mem = tmp_path / "lessons.jsonl"
    s1 = solve(catalog, PROBLEM, CONTEXT, size=3, call=fake_call_factory(), memory=mem)
    n = record_lessons(s1, mem)
    assert n > 0 and mem.exists()
    seen = []

    def spy(model, system, user, schema):
        seen.append(system)
        return fake_call_factory()(model, system, user, schema)

    s2 = solve(catalog, PROBLEM, CONTEXT, size=3, call=spy, memory=mem)
    assert s2.lessons
    assert any("Lessons from earlier panels" in sys_ and "unicode subject" in sys_ for sys_ in seen)


def test_lessons_are_deduplicated_and_bad_lines_are_skipped(tmp_path):
    from orgchart.solve import add_lesson, load_lessons
    mem = tmp_path / "lessons.jsonl"
    add_lesson(mem, "panel", "check the rate limit")
    add_lesson(mem, "panel", "check   the rate limit")
    mem.write_text(mem.read_text(encoding="utf-8") + "{not json\n", encoding="utf-8")
    lessons, warnings = load_lessons(mem)
    assert len(lessons) == 1 and len(warnings) == 1
    with pytest.raises(ValueError):
        add_lesson(mem, "panel", "   ")


def test_missing_memory_file_is_an_empty_memory(catalog, tmp_path):
    s = solve(catalog, PROBLEM, CONTEXT, size=2, call=fake_call_factory(), memory=tmp_path / "none.jsonl")
    assert s.lessons == [] and not s.warnings


def test_debate_shows_what_breaks_and_mitigations(catalog, tmp_path):
    s = solve(catalog, PROBLEM, CONTEXT, size=2, call=fake_call_factory())
    write_outputs(s, tmp_path)
    text = (tmp_path / "debate.md").read_text(encoding="utf-8")
    assert "What breaks in the present setup" in text and "helpdesk API rate limit" in text


def test_house_style_reaches_every_panelist_and_the_moderator(catalog):
    seen = []

    def spy(model, system, user, schema):
        seen.append(system)
        return fake_call_factory()(model, system, user, schema)

    solve(catalog, PROBLEM, CONTEXT, size=3, call=spy)
    assert seen and all("## How you talk" in s_ for s_ in seen)
