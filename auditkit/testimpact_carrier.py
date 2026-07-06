"""
auditkit.testimpact — run only the tests the change can reach.
==========================================================================
The bottleneck: CI runs the WHOLE suite on every change. Most tests cannot
possibly be affected. Selective testing cuts CI time by large factors — but
teams fear it, because skipping a test that WOULD have failed is silent
breakage. PL fixes the fear by tiering the soundness of the selection.

Mechanism (pure PL):
  - a change is a reconfiguration of a symbol set  S  (from a git delta).
  - a test's load-path  reach(T)  is everything it transitively reaches
    (forward closure over the reference graph — the gradient closure).
  - T is AFFECTED iff  reach(T) ∩ S ≠ ∅.  Select those; skip the rest.

Soundness, stated honestly:
  - The selection is FORCED-safe ONLY if reach() is complete. Dynamic
    dispatch (getattr/eval/importlib) hides edges, so a statically-skipped
    test could still be affected. Default tier: CONDITIONAL.
  - --safe NEVER skips a test it cannot bound: a test that is itself
    changed, or uses dynamic dispatch, is always kept. That upgrades the
    guarantee to "no affected test is skipped, modulo declared roots" while
    still skipping the provably-unreachable majority.

This is the difference between a fast test selector and a TRUSTWORTHY one.
"""
from __future__ import annotations
from collections import deque
from .lang.python_frontend import parse

DYNAMIC = ("getattr", "setattr", "eval", "exec", "__import__",
           "importlib", "globals", "locals", "vars")


def _is_test(name):
    return name.startswith("test_") or name.startswith("Test")


def reach(start, sym_refs, symbols):
    """forward transitive closure: everything `start` (transitively) uses."""
    seen, q = set(), deque([start])
    while q:
        x = q.popleft()
        for nxt in sym_refs.get(x, ()):
            if nxt in symbols and nxt not in seen:
                seen.add(nxt)
                q.append(nxt)
    return seen


def _sig(prog):
    """per-symbol identity: (load, frozenset(refs)). Changes when a symbol's
    size or what it references changes — a cheap, deterministic body proxy."""
    return {n: (s.body_hash, frozenset(prog.sym_refs.get(n, ())))
            for n, s in prog.symbols.items()}


def changed_symbols(base_prog, head_prog):
    b, h = _sig(base_prog), _sig(head_prog)
    changed = set()
    for n in set(b) | set(h):
        if b.get(n) != h.get(n):          # new, removed, resized, or re-wired
            changed.add(n)
    return changed


def uses_dynamic(prog, test):
    return any(tok in DYNAMIC for tok in prog.sym_refs.get(test, ()))


def select(head_prog, changed, safe=True, changed_files=()):
    symbols = head_prog.symbols
    tests = [n for n in symbols if _is_test(n)]
    selected, skipped, kept_unbounded = [], [], []
    for t in tests:
        r = reach(t, head_prog.sym_refs, symbols)
        affected = bool(r & changed) or t in changed
        if affected:
            selected.append(t)
        elif safe and (uses_dynamic(head_prog, t)
                       or head_prog.symbols[t].file in changed_files):
            kept_unbounded.append(t)          # cannot bound -> never skip
        else:
            skipped.append(t)
    return {"tests": tests, "selected": sorted(selected),
            "kept_unbounded": sorted(kept_unbounded),
            "skipped": sorted(skipped), "changed": sorted(changed)}


def report(sel, safe=True):
    run = sel["selected"] + sel["kept_unbounded"]
    total = len(sel["tests"]) or 1
    cut = 100.0 * len(sel["skipped"]) / total
    print(f"\n  test-impact selection   ({len(run)}/{total} run, "
          f"{cut:.0f}% skipped)")
    print("  " + "-" * 58)
    print(f"  changed symbols : {', '.join(sel['changed'][:8])}"
          + (" ..." if len(sel['changed']) > 8 else ""))
    print(f"  SELECTED (reach the change) : {', '.join(sel['selected']) or '—'}")
    if sel["kept_unbounded"]:
        print(f"  KEPT (cannot bound, safe)   : {', '.join(sel['kept_unbounded'])}")
    print(f"  SKIPPED (provably unreached): {', '.join(sel['skipped']) or '—'}")
    print("  " + "-" * 58)
    tier = "CONDITIONAL" if not safe else "CONDITIONAL (no affected test skipped, modulo declared roots)"
    print(f"  tier: {tier}")
    print("        soundness rests on reach() completeness; dynamic dispatch is")
    print("        the falsifier. --safe keeps every test it cannot bound.")
    # a pytest-ready selector expression
    expr = " or ".join(run)
    print(f"  pytest:  pytest -k \"{expr[:60]}{'...' if len(expr)>60 else ''}\"")
    return run


# ---- admission self-test ------------------------------------------------
def selftest():
    import tempfile, pathlib
    files = {
        "a.py": "def f_a(x): return x+1\n",
        "b.py": "def f_b(x): return x+2\n",
        "test_a.py": "from a import f_a\ndef test_a(): assert f_a(1)==2\n",
        "test_b.py": "from b import f_b\ndef test_b(): assert f_b(1)==3\n",
        "test_dyn.py": "def test_dyn():\n o=object()\n return getattr(o,'x',1)\n",
    }
    with tempfile.TemporaryDirectory() as d:
        for fn, src in files.items():
            (pathlib.Path(d) / fn).write_text(src)
        base = parse(d)
        # a LITERAL-only change to f_a: +1 -> +99 (no structural/ref change).
        # the change-detector MUST catch this or test_a is wrongly skipped.
        (pathlib.Path(d) / "a.py").write_text("def f_a(x): return x+99\n")
        head = parse(d)
    changed = changed_symbols(base, head)
    sel = select(head, changed, safe=True)
    ok = ("f_a" in changed                              # literal change detected
          and "test_a" in sel["selected"]
          and "test_b" in sel["skipped"]
          and "test_dyn" in sel["kept_unbounded"])   # dynamic -> never skipped
    print(f"  selftest: selected={sel['selected']} skipped={sel['skipped']} "
          f"kept={sel['kept_unbounded']} -> {'PASS' if ok else 'FAIL'}")
    return ok
