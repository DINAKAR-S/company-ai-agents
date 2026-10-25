from orgchart import compose
from orgchart.compose import PAINS, ROUTER, Answers, Team


def test_every_rule_points_at_a_real_role(catalog):
    from orgchart.compose import TOOL_IMPLIES
    for pain, ids in PAINS.items():
        for rid in ids:
            assert rid in catalog.roles, f"pain {pain} -> {rid}"
    for tool, ids in TOOL_IMPLIES.items():
        for rid in ids:
            assert rid in catalog.roles, f"tool {tool} -> {rid}"
    assert ROUTER in catalog.roles


def test_empty_answers_give_router_plus_default_motion_and_a_warning_free_team(catalog):
    team = compose(catalog, {})
    ids = team.ids()
    assert ids[0] == ROUTER
    assert "sales/sdr" in ids  # default motion is sales-led
    assert len(ids) <= 12


def test_nothing_at_all_warns_instead_of_silently_returning_one_role(catalog):
    team = compose(catalog, {"motion": "none", "pains": [], "tools": []})
    assert team.ids() == [ROUTER]
    assert any("Answer at least one question" in w for w in team.warnings)


def test_unknown_pain_is_reported_not_crashed(catalog):
    team = compose(catalog, {"pains": ["vibes"]})
    assert any("unknown pain 'vibes'" in w for w in team.warnings)


def test_pains_map_to_roles_and_reasons_say_why(catalog):
    team = compose(catalog, {"pains": ["support"], "motion": "none"})
    ids = team.ids()
    assert "customer/support-tier1" in ids
    reason = next(r["reason"] for r in team.roles if r["id"] == "customer/support-tier1")
    assert "support" in reason


def test_max_roles_is_respected_and_router_survives_the_cut(catalog):
    team = compose(catalog, {"pains": list(PAINS), "max_roles": 3})
    assert len(team.roles) == 3
    assert team.roles[0]["id"] == ROUTER
    assert any("keeping the first 3" in w for w in team.warnings)


def test_growth_stage_adds_managers_for_picked_ics(catalog):
    small = compose(catalog, {"pains": ["leads"], "stage": "early", "motion": "none"})
    big = compose(catalog, {"pains": ["leads"], "stage": "growth", "motion": "none", "max_roles": 20})
    assert "sales/sales-manager" not in small.ids()
    assert "sales/sales-manager" in big.ids()


def test_hostile_inputs_are_normalised(catalog):
    a = Answers.from_dict({"stage": "DROP TABLE", "motion": 42, "headcount": -5, "tools": [" Attio "], "pains": None, "max_roles": 0})
    assert a.stage == "early" and a.motion == "sales-led" and a.headcount == 0
    assert a.tools == ["attio"] and a.pains == [] and a.max_roles == 1
    team = compose(catalog, a)
    assert team.roles


def test_team_json_round_trip(catalog, tmp_path):
    team = compose(catalog, {"company": "Acme", "pains": ["finance"]})
    p = team.save(tmp_path / "team.json")
    back = Team.from_json(p.read_text(encoding="utf-8"))
    assert back.ids() == team.ids() and back.company == "Acme"


def test_same_answers_same_team(catalog):
    a = {"pains": ["leads", "support"], "tools": ["attio"], "stage": "growth", "max_roles": 20}
    assert compose(catalog, a).ids() == compose(catalog, dict(a)).ids()
