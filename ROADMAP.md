# Roadmap — gated candidates

Each item enters through the same Admission Gate it asks others to pass:
it must resolve a named failure, pass a closure/self-audit, and name its
falsifier. Status reflects where it sits on that path.

## ADMITTED (on the spine)
- Shared carrier core: tiers, Finding/Verdict, weakest-link, STIPULATED cap.
- Admission Gate for detectors (this file's own rule).
- IR + Python frontend; `audit arch` with 7 detectors.
- `.archaudit.toml` config (roots, budgets, ignores, extension points).
- Hash-chained seal/replay.
- **Delta audits** (`tools/audit_delta.py` + CI workflow): gate the change,
  not the snapshot. Head-ref snapshot bug found and fixed (SOURCE_AUDIT #2).
- **Testimpact carrier**: selective test runs with tiered skip-soundness;
  dynamic-dispatch tests kept unconditionally. IR gained `Symbol.body_hash`
  to support it (SOURCE_AUDIT #1).

## PENDING

1. **IR grows method/nested nodes** — prerequisite for full FORWARD/DEAD
   fidelity. Failure it resolves: v1 IR is top-level-only, so method-level
   forwarders are missed. Closure audit: re-check the library panel for
   parity. Falsifier: a method graph that changes a top-level verdict it
   shouldn't.

2. **New detectors** — `OVER_ABSTRACTION` (depth of indirection per call
   path), `TEST_ONLY_LEAKAGE` (prod symbols reachable only from test roots),
   richer `GOD_CLASS` via real LCOM cohesion. Each: tier + falsifier +
   pos/neg fixtures, admitted individually.

3. **Tree-sitter frontend** — multi-language. Seam declared
   (`auditkit/lang/treesitter_frontend.py`). Admission: fill `ir.Program`
   for a JS or Go fixture and pass a parity check against hand-built IR.
   Cross-language claims start CONDITIONAL until calibrated per language.

4. **Re-cut the demo_tangled fixture** so the calibration chart in the
   codebase paper and the pinned density in `tests/run.py` describe the
   same artifact (the original 164.47 fixture variant was lost; see
   SOURCE_AUDIT #3).

5. **Fill the benchmark comparison column** — run the declared-stub
   comparison against an LLM reviewer on the same repos/PRs. No
   "outperforms" claim before that column is EMPIRICAL.

## The bottleneck map (why this toolbox exists)
- review burnout → tiered itemized verdicts + delta audits (ADMITTED)
- poisoned architecture → `audit arch` (here)
- CI time → testimpact carrier (ADMITTED)
- vibe coding / context gap → declared θ in config
- junior talent → the verdict explains itself; tiers teach what evidence is
