"""Give each panelist a first name so a debate transcript reads like a meeting.

Names are labels for readability. The same role always gets the same name
(hash of the role id), two roles on one panel never share one, and no name
carries any claim about a real person.
"""

from __future__ import annotations

import hashlib

NAMES = [
    "Steven", "Priya", "Mateo", "Aisha", "Hiroshi", "Lena", "Omar", "Ingrid", "Kwame", "Sofia",
    "Dmitri", "Mei", "Rafael", "Zanele", "Tomasz", "Amara", "Luca", "Fatima", "Noah", "Yuki",
    "Elena", "Arjun", "Hanna", "Diego", "Nadia", "Kenji", "Chloe", "Tariq", "Greta", "Samuel",
    "Leila", "Mikael", "Ruth", "Idris", "Beatriz", "Jonas", "Anika", "Felix", "Imani", "Oscar",
]


def name_for(role_id: str, taken: set[str] | None = None) -> str:
    h = int(hashlib.sha1(role_id.encode("utf-8")).hexdigest(), 16)
    taken = taken or set()
    for i in range(len(NAMES)):
        candidate = NAMES[(h + i) % len(NAMES)]
        if candidate not in taken:
            return candidate
    return f"Panelist-{h % 1000}"  # more than 40 panelists; keep going rather than fail


def assign(role_ids: list[str]) -> dict[str, str]:
    taken: set[str] = set()
    out: dict[str, str] = {}
    for rid in role_ids:
        n = name_for(rid, taken)
        taken.add(n)
        out[rid] = n
    return out
