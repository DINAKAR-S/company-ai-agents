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
    "Aditi", "Bruno", "Carmen", "Dae-jung", "Esme", "Farid", "Gabriela", "Hamza", "Ines", "Jamal",
    "Kaori", "Lorenzo", "Maya", "Nikolai", "Olumide", "Paulina", "Quentin", "Rania", "Sven", "Thandiwe",
    "Umar", "Valentina", "Wei", "Ximena", "Yara", "Zoltan", "Abebe", "Bianca", "Cyrus", "Dalia",
    "Emeka", "Freya", "Gustavo", "Halima", "Ivan", "Jiro", "Katarina", "Liam", "Marisol", "Naveen",
    "Oona", "Pedro", "Qi", "Rosa", "Sanjay", "Tamar", "Ulrich", "Vera", "Wanjiru", "Xavier",
    "Yusuf", "Zara", "Ayla", "Bastien", "Celine", "Dev", "Eitan", "Fola", "Giulia", "Hugo",
    "Isla", "Joon", "Kofi", "Lucia", "Milo", "Nour", "Otto", "Petra", "Rohan", "Saoirse",
    "Teo", "Uma", "Viktor", "Willa", "Yasmin", "Zeynep", "Anders", "Bao", "Clara", "Dara",
    "Elif", "Finn", "Grace", "Hassan", "Ida", "Javier", "Kira", "Leon", "Mira", "Nils",
    "Oriol", "Pia", "Ravi", "Sara", "Tobias", "Una", "Vikram", "Wren", "Yael", "Zia",
]


# The faces on the README hero image. Pinned so the picture, the docs and a real panel agree.
PINNED = {
    "data-ai/data-ai-solutions-architect": "Steven",
    "sales/sdr": "Priya",
    "customer/support-escalation": "Mateo",
    "sales/revops": "Aisha",
    "customer/customer-success-manager": "Hiroshi",
    "c-suite/chief-of-staff": "Lena",
}
POOL = [n for n in NAMES if n not in PINNED.values()]


def name_for(role_id: str, taken: set[str] | None = None) -> str:
    taken = taken or set()
    if role_id in PINNED:
        return PINNED[role_id]
    h = int(hashlib.sha1(role_id.encode("utf-8")).hexdigest(), 16)
    for i in range(len(POOL)):
        candidate = POOL[(h + i) % len(POOL)]
        if candidate not in taken:
            return candidate
    return f"Panelist-{h % 1000}"  # more panelists than names; keep going rather than fail


def global_names(role_ids) -> dict[str, str]:
    """One name per role across the whole catalog, deterministic: pinned first, then sorted ids.
    Adding a role can shift a hash collision's resolution; names are labels, so that is acceptable."""
    ordered = sorted(role_ids, key=lambda r: (r not in PINNED, r))
    return assign(list(ordered))


def assign(role_ids: list[str]) -> dict[str, str]:
    taken: set[str] = set()
    out: dict[str, str] = {}
    for rid in sorted(role_ids, key=lambda r: r not in PINNED):  # pinned first so they always keep their name
        n = name_for(rid, taken)
        taken.add(n)
        out[rid] = n
    return {rid: out[rid] for rid in role_ids}
