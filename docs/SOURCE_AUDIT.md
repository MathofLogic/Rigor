# Source audit — what came in, what was broken, what changed

The /rigor repo was refined out of a flat dump of the MathofLogic project
sources on 2026-07-06. Everything below was verified by running the code,
not by reading it. Per the project's own standard: findings, not verdicts,
and every claim names how it was checked.

## Duplicates removed (byte-identical, md5-confirmed)

| kept | dropped | evidence |
|---|---|---|
| `auditkit/delta.py` | `delta_engine.py` | `diff` empty; identical md5 `18be4d69…` |
| `auditkit/resistance.py` | `resistance_carrier.py` | `diff` empty; identical md5 `3dc2ab37…` |

Canonical names follow the import graph (`from auditkit import resistance, delta`).

## Broken and fixed

1. **`testimpact_carrier.selftest()` crashed** —
   `AttributeError: 'Symbol' object has no attribute 'body_hash'`.
   The carrier was written against a newer IR than the one shipped.
   Fix (additive): `Symbol.body_hash` added to `auditkit/lang/ir.py`;
   the Python frontend fills it with `sha256(ast.dump(node))[:16]`.
   Selftest now passes and is wired into `tests/run.py`.

2. **`audit_delta.py --head <ref>` silently produced empty head signatures.**
   `run_delta` passed the ref string to the frontend as a *directory path*;
   parsing a non-existent path yields zero files, an empty signature, and a
   fake `SHIP`. Fix: a head that is not an existing directory is now
   materialised via `git archive` exactly like base. Verified end-to-end on
   a scratch git repo: a ceremony-adding commit now reports `arch net +18.7`
   instead of `+0`.

3. **`tests/run.py` pinned `demo_tangled` density at `164.47` — unreproducible.**
   No combination of the shipped fixture files reproduces it
   (`payments.py` alone = 174.77; `payments.py + orphans.py` = 128.97;
   exhaustively searched all 1–4 file combinations). The original fixture
   evidently contained a file variant that was not in the dump. The pin is
   STIPULATED either way; it is re-pinned to `128.97` against the fixtures
   actually in this repo, with the drift noted inline.

4. **`benchmark.py` had the wrong `sys.path` for a `tools/` placement** —
   it inserts `parent`, not `parent.parent`, so it belongs at the repo
   root. It lives there now and runs (library panel reports "not run"
   until the six calibration repos are checked out beside it).

## Reconstructed from the flat dump

The dump had no directory structure. The layout was rebuilt from the
import graph (`from .lang.python_frontend import …`, `import auditkit`,
`ROOT/"tests/fixtures/demo_tangled"`):

- `auditkit/` — core, registry, runner, detectors, config, delta,
  resistance, testimpact_carrier
- `auditkit/lang/` — ir, python_frontend, treesitter_frontend
  (`lang/__init__.py` was missing entirely; created empty)
- `tools/` — audit.py, audit_delta.py
- `tests/fixtures/` — assignment inferred and confirmed by the gate's own
  expectations: `demo_godcycle` = orders+inventory (GOD_CLASS + CYCLE fire),
  `demo_lean` = app+shapes (clean, ships), `demo_tangled` = payments+orphans
  (blocks; see re-pin above).

## Verified working, unchanged

- `tests/run.py` build gate: **BUILD PASSED** (admission 7/7, parity,
  new detectors, self-audit STIPULATED, resistance, delta, testimpact, seal).
- `tools/audit.py` CLI: verdicts, non-claims, sealing all behave as documented.
- Determinism: two `--json` runs produce byte-identical findings; only the
  seal differs, by design — each seal commits to the previous chain link.
- `suite/rigor-suite-instrument.html`: the Rigor Suite reference instrument
  (calls the Anthropic API from the artifact environment; runs L0–L7 in
  three staged passes and saves sealed audits).

## Left for sibling repos (not /rigor's load)

Per the one-repo-one-carrier split, these ran clean here and were **not**
included: `pl.py` (kernel, PASS/STIPULATED, chain sha `bfddc7d82986ba9b`
matching `pl_manifest.json` exactly), `atlas3.py` (`ab59172abd6618cb`,
matching), `pl_guide_audit.py` (`318db3aa0606a917`, matching),
`workbook_verified.py` (51 claims PASS), `carrier_verify.py` (all
enumerations match), `pl_dras.py` (all demos complete). Their manifests
regenerate bit-for-bit — the sealed history is intact and they are ready
to be lifted into the kernel repo unchanged.
