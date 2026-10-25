import json
import subprocess
import sys


def run(*args, cwd):
    return subprocess.run([sys.executable, "-m", "orgchart", *args], check=False, cwd=cwd, capture_output=True, text=True)


def test_validate_exits_zero_on_clean_repo(root):
    r = run("validate", cwd=root)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "no problems" in r.stdout


def test_validate_exits_nonzero_on_broken_copy(root, tmp_path):
    import shutil
    copy = tmp_path / "repo"
    shutil.copytree(root / "agents", copy / "agents")
    shutil.copy(root / "catalog.json", copy / "catalog.json")
    (copy / "agents" / "sales" / "sdr" / "AGENT.md").unlink()
    r = run("--root", str(copy), "validate", cwd=root)
    assert r.returncode == 1
    assert "sales/sdr: missing" in r.stdout


def test_tree_prints_every_role_once(root, catalog):
    r = run("tree", cwd=root)
    assert r.returncode == 0
    for rid in catalog.roles:
        assert r.stdout.count(f"({rid},") == 1, rid


def test_hire_from_answers_file_then_export(root, tmp_path):
    answers = tmp_path / "answers.json"
    answers.write_text(json.dumps({"company": "Acme", "pains": ["leads"], "max_roles": 4}), encoding="utf-8")
    team = tmp_path / "team.json"
    r = run("hire", "--answers", str(answers), "--out", str(team), cwd=root)
    assert r.returncode == 0, r.stderr
    assert team.exists()
    out = tmp_path / "acme"
    r = run("export", "--team", str(team), "--to", "claude-code", "--out", str(out), cwd=root)
    assert r.returncode == 0, r.stderr
    assert (out / "TEAM.md").exists()
    assert len(list((out / ".claude" / "agents").glob("*.md"))) == 4


def test_show_unknown_role_is_a_clean_error(root):
    r = run("show", "sales/nobody", cwd=root)
    assert r.returncode == 1
    assert "no role" in r.stderr


def test_hire_without_a_terminal_says_what_to_do(root):
    r = subprocess.run([sys.executable, "-m", "orgchart", "hire", "--out", "nope.json"], check=False,
                       cwd=root, capture_output=True, text=True, stdin=subprocess.DEVNULL)
    assert r.returncode != 0
    assert "--answers" in r.stderr
    assert "Traceback" not in r.stderr


def test_malformed_answers_file_is_a_clean_error(root, tmp_path):
    bad = tmp_path / "a.json"
    bad.write_text("{not json", encoding="utf-8")
    r = run("hire", "--answers", str(bad), "--out", str(tmp_path / "t.json"), cwd=root)
    assert r.returncode == 2
    assert "not valid JSON" in r.stderr and "Traceback" not in r.stderr


def test_answers_with_wrong_types_still_produce_a_team(root, tmp_path):
    a = tmp_path / "a.json"
    a.write_text(json.dumps({"company": "Acme\n# injected", "headcount": "abc", "max_roles": "9999999999",
                             "pains": ["../../etc"], "tools": [123, None], "stage": None}), encoding="utf-8")
    out = tmp_path / "t.json"
    r = run("hire", "--answers", str(a), "--out", str(out), cwd=root)
    assert r.returncode == 0, r.stderr
    team = json.loads(out.read_text(encoding="utf-8"))
    assert "\n" not in team["company"] and "injected" in team["company"]
    assert team["answers"]["max_roles"] == 500 and team["answers"]["headcount"] == 0


def test_traversal_id_in_catalog_never_reaches_the_filesystem(root, tmp_path):
    import shutil
    copy = tmp_path / "repo"
    shutil.copytree(root / "agents", copy / "agents")
    bad = {"version": 1, "departments": {"x": "x"}, "levels": [],
           "roles": [{"id": "x/../../evil", "title": "t", "department": "x", "reports_to": None, "level": "ic"}]}
    (copy / "catalog.json").write_text(json.dumps(bad), encoding="utf-8")
    r = run("--root", str(copy), "tree", cwd=root)
    assert r.returncode == 2
    assert "not a valid role id" in r.stderr and "Traceback" not in r.stderr


def test_export_with_a_garbage_team_file_is_a_clean_error(root, tmp_path):
    bad = tmp_path / "team.json"
    bad.write_text("[1, 2, 3]", encoding="utf-8")
    r = run("export", "--team", str(bad), "--to", "n8n", "--out", str(tmp_path / "o"), cwd=root)
    assert r.returncode == 2 and "Traceback" not in r.stderr


def test_find_ranks_roles_without_a_model(root):
    r = run("find", "support tickets pile up after releases", "--limit", "3", cwd=root)
    assert r.returncode == 0, r.stderr
    assert "customer/" in r.stdout


def test_find_with_nonsense_is_a_clean_non_zero(root):
    r = run("find", "zzzz qqqq", cwd=root)
    assert r.returncode == 1 and "no role matched" in r.stdout


def test_solve_dry_run_needs_no_credentials(root, tmp_path):
    ctx = tmp_path / "ctx.md"
    ctx.write_text("A 20-person clinic scheduling SaaS using Zendesk and Slack.", encoding="utf-8")
    r = run("solve", "--problem", "support tickets pile up after every release", "--context", f"@{ctx}",
            "--dry-run", "--size", "4", "--out", str(tmp_path / "sol"), "--no-memory", cwd=root)
    assert r.returncode == 0, r.stderr
    text = (tmp_path / "sol" / "panel.md").read_text(encoding="utf-8")
    assert "Steven" in text or "moderator" in text
    assert "Round 1 prompts" in text


def test_solve_without_credentials_explains_dry_run(root, tmp_path, monkeypatch):
    import os
    env = {k: v for k, v in os.environ.items() if k not in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")}
    env["HOME"] = str(tmp_path)
    env["USERPROFILE"] = str(tmp_path)
    r = subprocess.run([sys.executable, "-m", "orgchart", "solve", "--problem", "x y z", "--no-memory",
                        "--out", str(tmp_path / "o")], check=False, cwd=root, capture_output=True, text=True, env=env)
    assert r.returncode == 2 and "--dry-run" in r.stderr


def test_lesson_add_and_list(root, tmp_path):
    mem = tmp_path / "l.jsonl"
    r = run("lesson", "add", "check the opt-out list", "--memory", str(mem), "--role", "sales/sdr", cwd=root)
    assert r.returncode == 0 and "sales/sdr" in r.stdout
    r = run("lesson", "list", "--memory", str(mem), cwd=root)
    assert "check the opt-out list" in r.stdout
    r = run("lesson", "list", "--memory", str(tmp_path / "none.jsonl"), cwd=root)
    assert r.returncode == 0 and "no lessons" in r.stdout
