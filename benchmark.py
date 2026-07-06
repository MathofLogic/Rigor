#!/usr/bin/env python3
"""
benchmark.py — measure the signal BEFORE any claim is made about it.
==========================================================================
Grok's plan asserts "outperforms CodeRabbit" and schedules the benchmark
for later. We invert that: build the apparatus first, run the half we can,
and leave the half we cannot honestly empty rather than fabricated.

This harness reports, per repo:
  - resistance: max blast radius, # stiff hubs
  - arch:       structural unpaid density, # findings
  - determinism: re-run and assert byte-identical (a FORCED property a
                 deterministic auditor must have; an LLM reviewer does not)

It does NOT claim to beat CodeRabbit. The comparison column is a declared
stub: feed CodeRabbit's findings on the same repos/PRs to complete it.
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from auditkit import resistance
from auditkit.runner import analyze as arch_analyze
from auditkit import config as C

PORTED = C.Config(disable=["god_class", "cycle"])


def profile(root):
    r = resistance.analyze(root)
    a = arch_analyze(root, "prod", cfg=PORTED)
    return {"max_R": r["max_R"], "stiff": r["n_stiff"],
            "density": a.s_density, "findings": len(a.findings),
            "ship": a.ship}


def determinism(root, n=3):
    """re-run n times; the deterministic core MUST be byte-identical."""
    sigs = [tuple(sorted(resistance.signature(root).items())) for _ in range(n)]
    return all(s == sigs[0] for s in sigs)


if __name__ == "__main__":
    REPOS = [
        ("more_itertools", "/tmp/cal/more-itertools/more_itertools"),
        ("toolz", "/tmp/cal/toolz/toolz"),
        ("tqdm", "/tmp/cal/tqdm/tqdm"),
        ("click", "/tmp/cal/click/click"),
        ("jinja2", "/tmp/cal/jinja2/jinja2"),
        ("flask", "/tmp/cal/flask/flask"),
    ]
    print(f"  {'repo':16}{'max_R':>7}{'stiff':>7}{'density':>9}"
          f"{'finds':>7}{'determ.':>9}{'CodeRabbit':>12}")
    print("  " + "-" * 70)
    all_det = True
    for name, path in REPOS:
        try:
            p = profile(path)
            det = determinism(path)
            all_det = all_det and det
            print(f"  {name:16}{p['max_R']:>7}{p['stiff']:>7}{p['density']:>9.1f}"
                  f"{p['findings']:>7}{('yes' if det else 'NO'):>9}{'(not run)':>12}")
        except Exception as e:
            print(f"  {name:16}  ERR {type(e).__name__}: {e}")
    print("  " + "-" * 70)
    print(f"  determinism (re-run byte-identical): {'ALL PASS' if all_det else 'FAILED'} "
          "— FORCED; an LLM reviewer cannot guarantee this")
    print("  CodeRabbit column: DECLARED STUB. Not run here. To complete the")
    print("  comparison, run CodeRabbit on the same repos/PRs and populate it.")
    print("  No 'outperforms' claim is made until that column is filled.")
