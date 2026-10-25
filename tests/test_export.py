import json

import pytest

from orgchart import compose, export_team
from orgchart import frontmatter as fm
from orgchart.export import TARGETS


@pytest.fixture
def team(catalog):
    return compose(catalog, {"company": "Acme", "pains": ["leads", "support"], "tools": ["attio"], "max_roles": 6})


@pytest.mark.parametrize("target", TARGETS)
def test_export_writes_one_file_per_role_plus_chart(catalog, team, tmp_path, target):
    written = export_team(catalog, team, target, tmp_path)
    assert len(written) == len(team.roles) + 1
    assert (tmp_path / "TEAM.md").exists()
    for p in written:
        assert p.exists() and p.stat().st_size > 500


def test_claude_code_files_have_valid_frontmatter_and_known_models(catalog, team, tmp_path):
    export_team(catalog, team, "claude-code", tmp_path)
    for p in (tmp_path / ".claude" / "agents").glob("*.md"):
        data, body = fm.parse(p.read_text(encoding="utf-8"))
        assert set(data) == {"name", "description", "tools", "model"}
        assert data["model"] in {"haiku", "sonnet", "opus"}
        assert data["name"] == p.stem
        assert "## Your team" in body
        assert "ESCALATE:" in body


def test_managed_agents_export_has_prompt_body_and_environment(catalog, team, tmp_path):
    export_team(catalog, team, "managed-agents", tmp_path)
    env = tmp_path / "environments" / "cloud.yaml"
    assert env.exists()
    for p in (tmp_path / "agents").glob("*.md"):
        text = p.read_text(encoding="utf-8")
        assert text.startswith("---\nname: ")
        assert "model: claude-" in text
        assert "agent_toolset_20260401" in text
        assert "## What you do" in text


def test_web_tools_off_unless_role_lists_web_search(catalog, team, tmp_path):
    export_team(catalog, team, "managed-agents", tmp_path)
    for rid in team.ids():
        role = catalog.roles[rid]
        text = (tmp_path / "agents" / f"{role.slug}.md").read_text(encoding="utf-8")
        expected = "true" if "web_search" in role.tools else "false"
        assert f"{{name: web_search, enabled: {expected}}}" in text, rid


def test_n8n_export_is_valid_json_with_system_message(catalog, team, tmp_path):
    export_team(catalog, team, "n8n", tmp_path)
    for p in (tmp_path / "n8n").glob("*.json"):
        d = json.loads(p.read_text(encoding="utf-8"))
        assert d["systemMessage"].startswith("You are")
        assert d["model"].startswith("claude-")
        assert "escalate_to" in d["systemMessage"]


def test_second_export_overwrites_without_duplicates(catalog, team, tmp_path):
    first = export_team(catalog, team, "claude-code", tmp_path)
    second = export_team(catalog, team, "claude-code", tmp_path)
    assert sorted(first) == sorted(second)
    assert len(list((tmp_path / ".claude" / "agents").glob("*.md"))) == len(team.roles)


def test_unknown_target_is_rejected(catalog, team, tmp_path):
    with pytest.raises(ValueError):
        export_team(catalog, team, "crewai", tmp_path)


def test_team_with_a_role_no_longer_in_catalog_skips_it(catalog, team, tmp_path):
    team.roles.append({"id": "sales/unicorn", "reason": "stale team file"})
    written = export_team(catalog, team, "n8n", tmp_path)
    assert not any("unicorn" in str(p) for p in written)
