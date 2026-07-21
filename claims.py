"""
claims.py — the /rigor ledger, priced by the Atlas LEDGER plate.
==========================================================================
Checked claims name entries in rigor_checks:CHECKS, run by the gate.
Claims about the usefulness of findings are cited and priced as the
presumptions they are — the harness forces its own behavior, never the
value of what it finds.
"""

SECTIONS = [
    ("The seal discipline", [
        {"claim": "sealing replays the shipped chain first: a history "
                  "that does not replay refuses the mint and is "
                  "preserved as evidence, never written over",
         "check": "seal_refuses_broken_history", "tier": "FORCED"},
        {"claim": "an intact chain accepts the next seal and still "
                  "replays end to end",
         "check": "seal_appends_on_intact_history", "tier": "FORCED"},
    ]),
    ("The apparatus under its own gate", [
        {"claim": "the benchmark apparatus runs under the build gate "
                  "on bundled fixtures — its coverage is earned by "
                  "execution, not implied by shipping",
         "check": "benchmark_runs_on_fixtures", "tier": "FORCED"},
        {"claim": "zero measurements is a red: the apparatus refuses "
                  "to print a determinism verdict over an empty or "
                  "nonexistent measurement set",
         "check": "benchmark_refuses_vacuity", "tier": "FORCED"},
        {"claim": "the deterministic core is byte-identical across "
                  "re-runs on the same tree",
         "check": "benchmark_is_deterministic", "tier": "EMPIRICAL"},
    ]),
    ("The evidence ladder", [
        {"claim": "the tier order is total and weakest-link governs: "
                  "one weak finding caps a stack of strong ones",
         "check": "weakest_link_governs", "tier": "FORCED"},
    ]),
    ("Standing stipulations", [
        {"claim": "a verdict here prices structure, cost, and blast "
                  "radius; whether a finding MATTERS for a given "
                  "codebase is the caller's judgment",
         "cite": "README: the evidence ladder", "tier": "STIPULATED"},
        {"claim": "no comparison with any other reviewer is claimed "
                  "until the declared-stub column is filled with that "
                  "reviewer's actual runs",
         "cite": "benchmark.py: DECLARED STUB", "tier": "STIPULATED"},
        {"claim": "the detector set is a finite probe of code health, "
                  "not its definition",
         "cite": "ROADMAP.md", "tier": "PRESUMED"},
    ]),
]
