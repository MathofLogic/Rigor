"""
auditkit.resistance — the resistance carrier.
==========================================================================
Grounded in PL: R(x) = L(reconfigure x) - L(maintain x) = the blast radius
of changing x (the transitive set of symbols that break). Directional
(reverse-reachability), threshold-dependent (the theta-cliff). The COUNT is
FORCED (enumeration over the graph); "will hurt to change" is CONDITIONAL
(whether you must change x is theta, not in the AST).
"""
from __future__ import annotations
from collections import defaultdict, deque
from .lang.python_frontend import parse

STIFF_BUDGET = 8
FRAGILE_RATIO = 2.0


def _reverse_graph(prog):
    symbols = set(prog.symbols)
    dependents = defaultdict(set)
    for a, refs in prog.sym_refs.items():
        if a not in symbols:
            continue
        for b in refs:
            if b in symbols and b != a:
                dependents[b].add(a)
    return dependents


def _blast(sym, dependents):
    seen, q = set(), deque([sym])
    while q:
        x = q.popleft()
        for d in dependents.get(x, ()):
            if d not in seen and d != sym:
                seen.add(d)
                q.append(d)
    return seen


def analyze(root):
    prog = parse(root)
    dependents = _reverse_graph(prog)
    rows = []
    for name, s in prog.symbols.items():
        if name.startswith("__"):
            continue
        radius = len(_blast(name, dependents))
        rows.append({"name": name, "file": s.file, "line": s.line,
                     "own": s.load, "R": radius,
                     "fragility": round(radius / max(s.load, 1), 3),
                     "stiff": radius >= STIFF_BUDGET})
    rows.sort(key=lambda r: (-r["R"], -r["fragility"]))
    n = len(rows) or 1
    return {"root": str(root), "rows": rows,
            "total_R": sum(r["R"] for r in rows),
            "mean_R": round(sum(r["R"] for r in rows) / n, 2),
            "max_R": rows[0]["R"] if rows else 0,
            "n_stiff": sum(1 for r in rows if r["stiff"])}


def signature(root):
    """{symbol -> R}: the per-key scalar the delta engine diffs."""
    return {r["name"]: r["R"] for r in analyze(root)["rows"]}
