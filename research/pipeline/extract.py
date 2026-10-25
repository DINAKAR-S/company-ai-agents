"""Extract skills, tools and daily tasks from postings with the Message Batches API.

Requires: pip install anthropic, and ANTHROPIC_API_KEY (or `ant auth login`).
Batches run asynchronously at half price; this script submits, waits, and writes
one JSON object per posting keyed by the posting's index.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

SCHEMA = {
    "type": "object",
    "properties": {
        "skills": {"type": "array", "items": {"type": "string"}},
        "tools": {"type": "array", "items": {"type": "string"}},
        "daily_tasks": {"type": "array", "items": {"type": "string"}},
        "seniority": {"type": "string", "enum": ["junior", "mid", "senior", "lead", "unknown"]},
    },
    "required": ["skills", "tools", "daily_tasks", "seniority"],
    "additionalProperties": False,
}
SYSTEM = (
    "You extract structured facts from one job posting. Skills are capabilities the posting asks for, "
    "short noun phrases, lowercase, deduplicated. Tools are named products. Daily tasks are verb-first "
    "sentences describing what the person does. Only use what the posting says."
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default="claude-sonnet-5-5")
    ap.add_argument("--poll", type=int, default=30, help="seconds between status checks")
    a = ap.parse_args()

    try:
        import anthropic
    except ImportError:
        sys.exit("pip install anthropic")

    postings = [json.loads(ln) for ln in Path(a.inp).read_text(encoding="utf-8").splitlines() if ln.strip()]
    if not postings:
        sys.exit("no postings in input")

    client = anthropic.Anthropic()
    requests = []
    for i, p in enumerate(postings):
        requests.append({
            "custom_id": f"p{i}",
            "params": {
                "model": a.model,
                "max_tokens": 2000,
                "system": SYSTEM,
                "output_config": {"format": {"type": "json_schema", "schema": SCHEMA}},
                "messages": [{"role": "user", "content": f"Title: {p.get('title','')}\n\n{p['text'][:12000]}"}],
            },
        })
    batch = client.messages.batches.create(requests=requests)
    print(f"batch {batch.id} submitted with {len(requests)} requests")
    while True:
        b = client.messages.batches.retrieve(batch.id)
        if b.processing_status == "ended":
            break
        print(f"  {b.processing_status}: {b.request_counts}")
        time.sleep(a.poll)

    results, in_tok, out_tok = {}, 0, 0
    for r in client.messages.batches.results(batch.id):
        idx = int(r.custom_id[1:])
        if r.result.type != "succeeded":
            results[idx] = {"error": r.result.type}
            continue
        msg = r.result.message
        in_tok += msg.usage.input_tokens
        out_tok += msg.usage.output_tokens
        text = "".join(block.text for block in msg.content if block.type == "text")
        try:
            results[idx] = json.loads(text)
        except json.JSONDecodeError:
            results[idx] = {"error": "bad_json"}
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"model": a.model, "batch_id": batch.id, "input_tokens": in_tok,
                               "output_tokens": out_tok, "results": results}, indent=2), encoding="utf-8")
    print(f"{len(results)} results, {in_tok} input tokens, {out_tok} output tokens -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
