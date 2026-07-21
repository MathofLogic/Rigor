"""
rigor_checks.py — the /rigor check registry.
==========================================================================
Named, executable checks backing the root claims.py ledger; the gate
runs every one. Checks exercise the spine (tiers, weakest-link, seal/
replay discipline) and the apparatus (benchmark runs, and refuses to
be vacuously green). They force the harness's own behavior, never the
usefulness of its findings — that rider stands.
"""
from __future__ import annotations
import json, pathlib, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parent
FIX = ROOT / "tests" / "fixtures"


def chk_seal_refuses_broken_history():
    """seal() replays the shipped chain before appending; a chain that
    does not replay refuses the mint and preserves the file."""
    from auditkit.core import seal
    with tempfile.TemporaryDirectory() as td:
        cp = pathlib.Path(td) / "chain.json"
        seal({"n": 1}, cp)
        d = json.loads(cp.read_text())
        s = d[0]["sha"]
        d[0]["sha"] = ("0" if s[0] != "0" else "1") + s[1:]
        cp.write_text(json.dumps(d, indent=1))
        before = cp.read_bytes()
        try:
            seal({"n": 2}, cp)
        except ValueError:
            return cp.read_bytes() == before
        return False


def chk_seal_appends_on_intact_history():
    """An intact chain accepts the next seal and still replays."""
    from auditkit.core import seal, replay_list
    with tempfile.TemporaryDirectory() as td:
        cp = pathlib.Path(td) / "chain.json"
        seal({"n": 1}, cp)
        seal({"n": 2}, cp)
        chain = json.loads(cp.read_text())
        return len(chain) == 2 and replay_list(chain) is True


def chk_benchmark_runs_on_fixtures():
    """The benchmark apparatus is under the gate: pointed at the
    bundled fixtures it profiles them, reports determinism, and
    exits by its measurements."""
    r = subprocess.run(
        [sys.executable, str(ROOT / "benchmark.py"),
         str(FIX / "demo_lean"), str(FIX / "demo_tangled")],
        capture_output=True, text=True, timeout=300)
    return (r.returncode == 0 and "ALL PASS" in r.stdout
            and "DECLARED STUB" in r.stdout)


def chk_benchmark_refuses_vacuity():
    """Zero profiled repos is a red, not a green: the determinism line
    is never printed over an empty measurement set."""
    r = subprocess.run(
        [sys.executable, str(ROOT / "benchmark.py"),
         "/nonexistent/nowhere"],
        capture_output=True, text=True, timeout=120)
    return r.returncode != 0 and "NOT MEASURED" in r.stdout


def chk_benchmark_is_deterministic():
    """Two benchmark runs on the same fixture are byte-identical —
    the FORCED property the apparatus advertises, held on itself."""
    def run():
        return subprocess.run(
            [sys.executable, str(ROOT / "benchmark.py"),
             str(FIX / "demo_lean")],
            capture_output=True, text=True, timeout=300).stdout
    return run() == run()


def chk_weakest_link_governs():
    """The evidence ladder orders FORCED above PRESUMED-like floors,
    and a mixed set of findings is governed by its weakest member —
    min over TIER values, exercised, not assumed."""
    from auditkit.core import TIER
    tiers = ["FORCED", "EMPIRICAL", "STIPULATED"]
    weakest = min(tiers, key=lambda t: TIER[t])
    return (TIER["FORCED"] > TIER["EMPIRICAL"] > TIER["STIPULATED"]
            > TIER["UNPAID"] and weakest == "STIPULATED")


CHECKS = {
    "seal_refuses_broken_history": chk_seal_refuses_broken_history,
    "seal_appends_on_intact_history": chk_seal_appends_on_intact_history,
    "benchmark_runs_on_fixtures": chk_benchmark_runs_on_fixtures,
    "benchmark_refuses_vacuity": chk_benchmark_refuses_vacuity,
    "benchmark_is_deterministic": chk_benchmark_is_deterministic,
    "weakest_link_governs": chk_weakest_link_governs,
}
