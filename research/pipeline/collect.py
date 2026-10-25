"""Collect job postings for one role title into a JSONL file.

Pluggable by design: pass --source apify to run an Apify actor you own, or
--source file to import postings you gathered another way. No source is run by
default, because every source has its own terms and pricing.

Each output line: {"role": "...", "title": "...", "company": "...", "url": "...",
                   "posted": "YYYY-MM-DD", "text": "..."}
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path


def from_file(path: str):
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def from_apify(actor: str, query: str, n: int):
    token = os.environ.get("APIFY_TOKEN")
    if not token:
        sys.exit("APIFY_TOKEN is not set")
    url = f"https://api.apify.com/v2/acts/{actor}/run-sync-get-dataset-items?token={token}"
    body = json.dumps({"query": query, "maxItems": n}).encode()
    req = urllib.request.Request(url, data=body, headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as resp:
        for item in json.load(resp):
            yield {
                "title": item.get("title", ""), "company": item.get("companyName", ""),
                "url": item.get("url", ""), "posted": item.get("postedAt", "")[:10],
                "text": item.get("description", ""),
            }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--role", required=True, help="catalog role id, e.g. sales/sdr")
    ap.add_argument("--title", help="search title; defaults to the role title from catalog.json")
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--source", choices=["file", "apify"], default="file")
    ap.add_argument("--file", help="JSONL input when --source file")
    ap.add_argument("--actor", default="apify/linkedin-jobs-scraper", help="Apify actor id when --source apify")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    root = Path(__file__).resolve().parents[2]
    with open(root / "catalog.json", encoding="utf-8") as f:
        titles = {r["id"]: r["title"] for r in json.load(f)["roles"]}
    if a.role not in titles:
        sys.exit(f"unknown role {a.role}")
    title = a.title or titles[a.role]

    if a.source == "file":
        if not a.file:
            sys.exit("--file is required with --source file")
        rows = from_file(a.file)
    else:
        rows = from_apify(a.actor, title, a.n)

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with open(out, "w", encoding="utf-8") as f:
        for row in rows:
            if not row.get("text"):
                continue
            row["role"] = a.role
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1
            if count >= a.n:
                break
    print(f"{count} postings for {a.role} ({title!r}) -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
