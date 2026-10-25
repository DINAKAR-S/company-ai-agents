import pytest

from orgchart import frontmatter as fm


def test_round_trip_scalars_null_and_lists():
    text = fm.dump({"id": "a/b", "reports_to": None, "n": 3, "flag": True, "tools": ["x", "y"], "q": "has: colon"})
    data, body = fm.parse(text + "\nbody\n")
    assert data == {"id": "a/b", "reports_to": None, "n": 3, "flag": True, "tools": ["x", "y"], "q": "has: colon"}
    assert body == "body"


def test_missing_opening_fence_is_an_error():
    with pytest.raises(fm.FrontMatterError):
        fm.parse("id: x\n---\n")


def test_missing_closing_fence_is_an_error():
    with pytest.raises(fm.FrontMatterError):
        fm.parse("---\nid: x\n")


def test_nested_maps_are_rejected_not_silently_flattened():
    with pytest.raises(fm.FrontMatterError):
        fm.parse("---\ntools:\n  - a\n---\n")


def test_duplicate_keys_are_rejected():
    with pytest.raises(fm.FrontMatterError):
        fm.parse("---\nid: a\nid: b\n---\n")


def test_unclosed_flow_list_is_rejected():
    with pytest.raises(fm.FrontMatterError):
        fm.parse("---\ntools: [a, b\n---\n")


def test_empty_list_and_quoted_commas():
    data, _ = fm.parse('---\ntools: []\ntags: ["a, b", c]\n---\n')
    assert data["tools"] == []
    assert data["tags"] == ["a, b", "c"]


def test_crlf_input_parses_the_same_as_lf():
    lf, _ = fm.parse("---\nid: a/b\n---\nbody\n")
    crlf, body = fm.parse("---\r\nid: a/b\r\n---\r\nbody\r\n")
    assert lf == crlf
    assert body.strip() == "body"
