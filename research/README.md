# Research pipeline: skills from real job postings

Every agent's **Skills** section is meant to carry counts like `Pipeline forecasting (37 of 50 postings)` so a reader knows the skill came from the market and not from one author's head. The pipeline that produces those counts is scaffolded here and has **not yet been run** across the catalog; today the Skills sections are editorial, and no file shows counts it did not earn.

## How it works when run

```
python research/pipeline/collect.py --role sales/sdr --n 50 --out research/sources/sales-sdr.jsonl
python research/pipeline/extract.py --in research/sources/sales-sdr.jsonl --out research/extracted/sales-sdr.json
python research/pipeline/merge.py --role sales/sdr --in research/extracted/sales-sdr.json
```

1. **collect.py** pulls postings for the role title from a job board API or an Apify actor you run yourself. It stores the raw text, source URL and date. It does not scrape LinkedIn profiles.
2. **extract.py** sends each posting to Claude through the Message Batches API (half price, no latency need) with a strict JSON schema: `skills[]`, `tools[]`, `daily_tasks[]`, `seniority`. One batch per role.
3. **merge.py** counts how many postings mention each skill, writes the counts back into the role's Skills section, and records the run in `research/runs.md` with date, source and sample size.

## What a run costs

Roughly 50 postings per role at a few thousand tokens each. At current Message Batches pricing for a mid-tier model that is well under a dollar per role; the collection step depends on the source you use. Both scripts print their token counts so the figure can be checked rather than quoted.

## Rules

- Sources are public job postings only.
- Raw postings stay out of the repo (`research/sources/` is gitignored); only counts and dated summaries are committed.
- A count is never edited by hand. If a skill is obviously missing, add it without a count and let the next run confirm it.
