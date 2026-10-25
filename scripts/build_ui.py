"""Build docs/index.html: a single-file browser for the catalog.

No server, no dependencies, no framework. The catalog is embedded as JSON so the
page works from a file:// URL and from GitHub Pages. Rebuild after changing any
agent file:  python scripts/build_ui.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from orgchart import load_catalog
from orgchart.finder import ALIASES, STOPWORDS
from orgchart.names import name_for

# Small companies ask for these first; the page lists departments in this order.
DEPT_ORDER = ["marketing", "sales", "customer", "people", "finance", "operations", "data-ai",
              "product-design", "engineering", "legal", "strategy", "executive-support", "c-suite"]

TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>company-ai-agents</title>
<style>
  :root { --bg:#f7f6f2; --ink:#1d1d1b; --mute:#6b6a65; --line:#dedcd5; --card:#fff; --acc:#0f6b4f; --acc2:#e8f3ee; }
  @media (prefers-color-scheme: dark) { :root { --bg:#161614; --ink:#ecebe6; --mute:#9d9c95; --line:#2d2d2a; --card:#1f1f1c; --acc:#5fc39a; --acc2:#1f2f28; } }
  * { box-sizing:border-box }
  body { margin:0; background:var(--bg); color:var(--ink); font:15px/1.5 ui-sans-serif,system-ui,Segoe UI,Roboto,sans-serif }
  header { padding:20px 16px 8px; max-width:1200px; margin:0 auto }
  h1 { margin:0 0 4px; font-size:22px } h1 span { color:var(--mute); font-weight:400; font-size:15px; margin-left:8px }
  .bar { display:flex; gap:8px; flex-wrap:wrap; align-items:center; margin:10px 0 }
  input[type=search] { flex:1; min-width:240px; padding:10px 12px; border:1px solid var(--line); border-radius:8px; background:var(--card); color:var(--ink); font-size:15px }
  .chip { border:1px solid var(--line); background:var(--card); color:var(--ink); border-radius:999px; padding:5px 11px; cursor:pointer; font-size:13px }
  .chip.on { background:var(--acc); color:#fff; border-color:var(--acc) }
  main { display:grid; grid-template-columns: 360px 1fr; gap:16px; max-width:1200px; margin:0 auto; padding:0 16px 40px }
  @media (max-width:860px) { main { grid-template-columns:1fr } }
  .list { display:flex; flex-direction:column; gap:6px; max-height:calc(100vh - 170px); overflow:auto; padding-right:4px }
  .role { background:var(--card); border:1px solid var(--line); border-radius:10px; padding:10px 12px; cursor:pointer }
  .role:hover, .role.on { border-color:var(--acc); background:var(--acc2) }
  .role .t { font-weight:600 } .role .m { color:var(--mute); font-size:12.5px }
  .role .why { color:var(--acc); font-size:12px; margin-top:2px }
  .face { display:inline-block; width:26px; height:26px; border-radius:50%; background:var(--acc); color:#fff; font-size:12px; line-height:26px; text-align:center; margin-right:8px; vertical-align:middle }
  article { background:var(--card); border:1px solid var(--line); border-radius:12px; padding:18px 22px; min-height:300px }
  article h2 { margin:0 0 2px; font-size:20px } article .meta { color:var(--mute); font-size:13px; margin-bottom:10px }
  article h3 { margin:18px 0 6px; font-size:15px; border-top:1px solid var(--line); padding-top:12px }
  article ul { padding-left:20px; margin:4px 0 } article li { margin:2px 0 }
  .btn { background:var(--acc); color:#fff; border:0; border-radius:8px; padding:8px 12px; cursor:pointer; font-size:14px; margin-right:6px }
  .btn.alt { background:transparent; color:var(--acc); border:1px solid var(--acc) }
  pre { white-space:pre-wrap; background:var(--bg); border:1px solid var(--line); border-radius:8px; padding:10px; font-size:12.5px; max-height:40vh; overflow:auto }
  .empty { color:var(--mute); padding:40px 10px; text-align:center }
  .tag { display:inline-block; background:var(--acc2); color:var(--acc); border-radius:6px; padding:1px 7px; font-size:12px; margin:2px 4px 2px 0 }
  footer { max-width:1200px; margin:0 auto; padding:0 16px 30px; color:var(--mute); font-size:13px }
</style>
</head>
<body>
<header>
  <h1>company-ai-agents <span>__COUNT__ roles, every department, each one a ready prompt</span></h1>
  <div class="bar">
    <input id="q" type="search" placeholder="Describe the problem: leads not followed up, tickets pile up, hiring takes months, invoices unpaid...">
    <button class="btn alt" id="clear">Clear</button>
  </div>
  <div class="bar" id="depts"></div>
</header>
<main>
  <div class="list" id="list"></div>
  <article id="detail"><div class="empty">Type a problem above, or pick a department, then click a role. The prompt is yours to copy.</div></article>
</main>
<footer>Every prompt refuses to send, post or change records without a human yes. Names are labels for readability. Built from the repo files by <code>scripts/build_ui.py</code>.</footer>
<script>
const DATA = __DATA__;
const STOP = new Set(__STOP__);
const ALIASES = __ALIASES__;
const W = {title:3, tags:3, triggers:1.5, skills:2, tasks:1, integrations:1.5};
const DEPT_ORDER = __DEPT_ORDER__;
const list = document.getElementById('list'), detail = document.getElementById('detail'), q = document.getElementById('q'), deptsEl = document.getElementById('depts');
let dept = null, selected = null;
function tokens(t){ const out=new Set(); for (const w of (t.toLowerCase().match(/[a-z][a-z0-9+-]{2,}/g)||[])) if(!STOP.has(w)) out.add(w); return out; }
function expand(s){ const o=new Set(s); for (const t of s) for (const a of (ALIASES[t]||[])) o.add(a); return o; }
function score(role, qs){ let sc=0, hits=new Set(); for (const f in W){ for (const t of role.terms[f]) if (qs.has(t)){ sc+=W[f]; hits.add(t);} } return [sc, [...hits]]; }
function section(body, h){ const i=body.indexOf(h); if(i<0) return ''; const rest=body.slice(i+h.length); const j=rest.indexOf('\n## '); return (j<0?rest:rest.slice(0,j)).trim(); }
function render(){
  const text = q.value.trim(); const qs = text ? expand(tokens(text)) : null;
  let rows = DATA.roles.filter(r => !dept || r.department===dept);
  rows = rows.map(r => { const [sc, hits] = qs ? score(r, qs) : [0, []]; return {r, sc, hits}; });
  if (qs) rows = rows.filter(x => x.sc>0).sort((a,b)=> b.sc-a.sc || a.r.id.localeCompare(b.r.id));
  else rows.sort((a,b)=> DEPT_ORDER.indexOf(a.r.department)-DEPT_ORDER.indexOf(b.r.department) || a.r.id.localeCompare(b.r.id));
  list.innerHTML = rows.length ? rows.map(({r, hits}) => `<div class="role ${selected===r.id?'on':''}" data-id="${r.id}">
      <span class="face">${r.name[0]}</span><span class="t">${r.name}</span> <span class="m">${r.title}</span>
      <div class="m">${r.id} · reports to ${r.reports_to||'human owner'}</div>
      ${hits.length?`<div class="why">matched: ${hits.slice(0,6).join(', ')}</div>`:''}</div>`).join('')
    : `<div class="empty">No role matches those words. Try the words a practitioner would use: tickets, leads, invoices, candidates, churn, dashboard.</div>`;
}
function show(id){
  selected = id; const r = DATA.roles.find(x=>x.id===id); if(!r) return; render();
  const li = s => s.split('\n').filter(l=>l.startsWith('- ')).map(l=>`<li>${l.slice(2)}</li>`).join('');
  detail.innerHTML = `<h2>${r.name}, ${r.title}</h2>
    <div class="meta">${r.id} · ${r.department} · ${r.level} · model ${r.model_hint} · reports to ${r.reports_to||'human owner'} · escalates to ${r.escalates_to||'human owner'}</div>
    <div>${r.tags.map(t=>`<span class="tag">${t}</span>`).join('')}</div>
    <p>${r.summary}</p>
    <button class="btn" id="copy">Copy the prompt</button>
    <button class="btn alt" id="copycc">Copy as Claude Code subagent</button>
    <span class="m" id="copied"></span>
    <h3>What this role does</h3><ul>${li(section(r.body,'## What you do'))}</ul>
    <h3>Working rules</h3><ul>${li(section(r.body,'## Working rules'))}</ul>
    <h3>Escalates when</h3><ul>${li(section(r.body,'## Escalate when'))}</ul>
    <h3>Example</h3><pre>${section(r.body,'## Example').replace(/</g,'&lt;')}</pre>
    <h3>Full prompt</h3><pre>${r.body.replace(/</g,'&lt;')}\n\n${DATA.style.replace(/</g,'&lt;')}</pre>`;
  const say = m => { document.getElementById('copied').textContent = m; setTimeout(()=>document.getElementById('copied').textContent='', 2000); };
  document.getElementById('copy').onclick = () => navigator.clipboard.writeText(r.body + '\n\n' + DATA.style).then(()=>say('copied'), ()=>say('select the text below and copy'));
  document.getElementById('copycc').onclick = () => navigator.clipboard.writeText(`---\nname: ${r.id.replace('/','-')}\ndescription: ${r.title}. ${r.summary}\nmodel: ${({fast:'haiku',balanced:'sonnet',deep:'opus'})[r.model_hint]}\n---\n\n${r.body}\n\n${DATA.style}`).then(()=>say('copied, save as .claude/agents/'+r.id.replace('/','-')+'.md'), ()=>say('copy failed'));
}
deptsEl.innerHTML = `<button class="chip on" data-d="">All</button>` + DEPT_ORDER.filter(d=>DATA.departments[d]).map(d=>`<button class="chip" data-d="${d}" title="${DATA.departments[d]}">${d}</button>`).join('');
deptsEl.onclick = e => { const b=e.target.closest('.chip'); if(!b) return; dept=b.dataset.d||null; [...deptsEl.children].forEach(c=>c.classList.toggle('on', c===b)); render(); };
list.onclick = e => { const el=e.target.closest('.role'); if(el) show(el.dataset.id); };
q.oninput = render; document.getElementById('clear').onclick = () => { q.value=''; render(); };
render();
</script>
</body>
</html>
"""


def terms(role):
    from orgchart.finder import role_terms
    return {k: sorted(v) for k, v in role_terms(role).items()}


def main() -> int:
    cat = load_catalog(ROOT)
    roles = []
    for r in cat.roles.values():
        roles.append({
            "id": r.id, "title": r.title, "department": r.department, "reports_to": r.reports_to,
            "escalates_to": r.escalates_to, "level": r.level, "model_hint": r.model_hint, "tags": r.tags,
            "summary": r.summary, "body": r.body, "name": name_for(r.id), "terms": terms(r),
        })
    data = {"departments": cat.departments, "roles": roles, "style": cat.style}
    html = (TEMPLATE.replace("__COUNT__", str(len(roles)))
            .replace("__DATA__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
            .replace("__STOP__", json.dumps(sorted(STOPWORDS)))
            .replace("__ALIASES__", json.dumps(ALIASES))
            .replace("__DEPT_ORDER__", json.dumps(DEPT_ORDER)))
    out = ROOT / "docs" / "index.html"
    out.write_text(html, encoding="utf-8", newline="\n")
    print(f"{out} ({out.stat().st_size // 1024} KB, {len(roles)} roles)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
