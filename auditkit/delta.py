"""
auditkit.delta — gate the change, not the snapshot.
==========================================================================
A snapshot audit answers "is this codebase stiff / overengineered?". The
governance question that actually attacks review burnout is the DELTA:
"did THIS change make it worse?" The seal/chain was built for exactly this.

The engine is carrier-agnostic. A carrier exposes
    signature(root) -> {key: scalar}
(resistance: {symbol -> R}; archload: {finding -> unpaid load}). The delta
diffs two signatures (a base ref and the working tree) and reports:

  - added       keys whose value rose  (stiffness / load added)
  - born        keys absent at base, present now (new structure)
  - crossings   keys that crossed a threshold  (a leaf became a hub:
                the theta-cliff, the single most important governance signal)
  - net         total change

Tiers, honestly: a per-key value's tier is the carrier's (resistance count
= FORCED). The DELTA inherits it for the count, but the GATE budget is
STIPULATED and the composite verdict caps at STIPULATED, like every tool
in this box.
"""
from __future__ import annotations
import subprocess, tempfile, tarfile, io, pathlib
from dataclasses import dataclass, field
from .core import seal as _seal, TIER, TNAME


def git_snapshot(repo, ref):
    """Materialise a git ref into a temp dir via `git archive` (offline)."""
    out = subprocess.run(["git", "-C", str(repo), "archive", "--format=tar", ref],
                         capture_output=True, check=True).stdout
    d = tempfile.mkdtemp(prefix=f"snap_{ref}_")
    with tarfile.open(fileobj=io.BytesIO(out)) as t:
        t.extractall(d)
    return d


def merge_base(repo, a, b):
    return subprocess.run(["git", "-C", str(repo), "merge-base", a, b],
                          capture_output=True, text=True, check=True).stdout.strip()


@dataclass
class Delta:
    carrier: str
    cliff: float                       # threshold a key "crosses" to become bad
    added: dict = field(default_factory=dict)     # key -> +increase
    dropped: dict = field(default_factory=dict)   # key -> -decrease
    born: dict = field(default_factory=dict)      # new key -> value
    gone: list = field(default_factory=list)      # removed keys
    crossings: dict = field(default_factory=dict) # key -> (base, head) over cliff
    net: float = 0.0
    budget: float = 0.0
    tier: str = "STIPULATED"
    reasons: list = field(default_factory=list)
    sha_prev: str = ""
    sha: str = ""

    @property
    def ship(self):
        return not self.reasons


def diff(base_sig, head_sig, carrier, cliff, budget):
    d = Delta(carrier=carrier, cliff=cliff, budget=budget)
    keys = set(base_sig) | set(head_sig)
    for k in keys:
        b, h = base_sig.get(k), head_sig.get(k)
        if b is None and h is not None:
            d.born[k] = h
            if h >= cliff:                       # born stiff
                d.crossings[k] = (0, h)
        elif h is None:
            d.gone.append(k)
        else:
            if h > b:
                d.added[k] = round(h - b, 2)
                if b < cliff <= h:               # the theta-cliff crossing
                    d.crossings[k] = (b, h)
            elif h < b:
                d.dropped[k] = round(h - b, 2)
    d.net = round(sum(head_sig.values()) - sum(base_sig.values()), 2)
    added_total = round(sum(d.added.values()) + sum(d.born.values()), 2)
    # GATE: block on any theta-cliff crossing, or on net added beyond budget.
    if d.crossings:
        d.reasons.append(f"{len(d.crossings)} theta-cliff crossing(s): "
                         "a symbol crossed into STIFF/hub territory")
    if added_total > budget:
        d.reasons.append(f"added {carrier} load {added_total} over delta "
                         f"budget {budget}")
    # composite caps at STIPULATED (the budget is a stipulation)
    d.tier = TNAME[min(TIER["FORCED"], TIER["STIPULATED"])]
    return d


# --- carrier registry for delta ------------------------------------------
def _sig_resistance(root):
    from .resistance import signature
    return signature(root)

def _sig_archload(root):
    from .runner import analyze
    v = analyze(root, "prod")
    sig = {}
    for f in v.findings:
        if f.gating and f.v < 0.5:
            sig[f"{f.file}:{f.kind}:{f.name}"] = round(f.load * (1 - f.v), 2)
    return sig

CARRIERS = {
    "resistance": (_sig_resistance, 8.0, 12.0),   # (sig_fn, cliff, delta budget)
    "arch":       (_sig_archload,  10.0, 20.0),
}


def run_delta(repo, carrier, base_ref, head_root=None, chain="delta_chain.json"):
    sig_fn, cliff, budget = CARRIERS[carrier]
    base_dir = git_snapshot(repo, base_ref)
    base_sig = sig_fn(base_dir)
    if head_root is None:
        head_dir = repo                          # working tree by default
    else:
        p = pathlib.Path(head_root)
        # a head that names a directory is used as-is; anything else is a
        # git ref and must be materialised like base. Passing a ref string
        # straight to the frontend silently parses zero files — an empty
        # signature that fakes a SHIP. Refuse that failure mode.
        head_dir = str(p) if p.is_dir() else git_snapshot(repo, head_root)
    head_sig = sig_fn(head_dir)
    d = diff(base_sig, head_sig, carrier, cliff, budget)
    sealed = _seal({"carrier": carrier, "base": base_ref, "net": d.net,
                    "n_crossings": len(d.crossings), "ship": d.ship,
                    "reasons": d.reasons}, chain)
    d.sha, d.sha_prev = sealed["sha"], sealed["sha_prev"]
    return d


def report(d):
    print(f"\n  delta [{d.carrier}]  net change: {d.net:+}")
    print("  " + "-" * 60)
    if d.crossings:
        print("  THETA-CLIFF CROSSINGS (leaf -> hub) — the headline signal:")
        for k, (b, h) in sorted(d.crossings.items(), key=lambda x: -x[1][1]):
            print(f"     {k:28.28}  {b} -> {h}   (cliff {d.cliff})")
    if d.added:
        print("  stiffness/load ADDED to existing symbols:")
        for k, v in sorted(d.added.items(), key=lambda x: -x[1])[:6]:
            print(f"     {k:28.28}  +{v}")
    if d.born:
        print(f"  {len(d.born)} new symbol(s); {sum(1 for v in d.born.values() if v>=d.cliff)} born stiff")
    print("  " + "-" * 60)
    print(f"  VERDICT: {'SHIP' if d.ship else 'BLOCK'}/{d.tier}"
          + (("  — " + "; ".join(d.reasons)) if d.reasons else ""))
    print(f"  sealed: {d.sha} (prev {d.sha_prev})")
    print("  tier: per-symbol counts FORCED; the delta budget is STIPULATED,")
    print("        so the composite verdict caps at STIPULATED.\n")
