"""
auditkit.core — the shared carrier spine.
==========================================================================
Every tool in the toolbox (archload, vctest, bedrock, ...) draws its
verdict vocabulary from here, so the discipline is defined ONCE:

  TIER          the evidence ladder, identical across tools.
  Finding       one priced observation: load, value v in [0,1], tier,
                and a NAMED FALSIFIER (no finding without one).
  Verdict       a composed result: weakest-link tier, AND-summed load,
                and a composite tier that CANNOT outrank the instrument's
                own weakest stipulation (the VCOS K1 self-grade).
  seal/replay   one hash-chain, shared. Loaded history, tamper-evident.

v = 0.5 is reserved: the artifact cannot tell whether theta demands the
structure. It is never counted as half-unpaid; it lives in its own pile.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
import json, hashlib, pathlib

TIER = {"UNPAID": 0, "STIPULATED": 1, "CONDITIONAL": 2,
        "EMPIRICAL": 3, "FORCED": 4}
TNAME = {v: k for k, v in TIER.items()}


@dataclass
class Finding:
    detector: str          # which detector raised it
    kind: str              # finding subtype (DEAD, GOD_CLASS, CYCLE, ...)
    name: str              # the symbol/edge in question
    file: str
    line: int
    load: float            # countable structural cost
    v: float               # paid fraction in [0,1]; 0.5 == UNKNOWN
    tier: str              # evidence tier of THIS finding
    falsifier: str         # what would overturn it (required, never empty)
    gating: bool = True    # does this finding participate in ship/block?

    def __post_init__(self):
        assert self.falsifier, f"{self.kind}:{self.name} has no falsifier"
        assert self.tier in TIER, f"unknown tier {self.tier}"

    @property
    def unpaid(self) -> float:
        return self.load * (1 - self.v) if self.v < 0.5 else 0.0

    @property
    def unknown(self) -> float:
        return self.load if self.v == 0.5 else 0.0


def compose(findings, total_load, budgets, gate_kinds=()):
    """Price a set of findings into a Verdict.

    - structural unpaid density (excl. non-gating kinds) is the GATE.
    - composite tier = weakest finding tier, CAPPED AT STIPULATED, because
      the instrument is stipulation-bottomed (tier order, v-values, budgets,
      thresholds). A clean scan is absence of evidence, not FORCED minimality.
    """
    gating = [f for f in findings if f.gating and f.kind not in NON_GATING]
    gate_unpaid = sum(f.unpaid for f in gating)
    all_unpaid = round(sum(f.unpaid for f in findings), 1)
    unknown = round(sum(f.unknown for f in findings), 1)
    s_density = round(1000.0 * gate_unpaid / total_load, 2) if total_load else 0.0
    weakest = min((TIER[f.tier] for f in findings), default=TIER["FORCED"])
    composite = min(weakest, TIER["STIPULATED"])
    return Verdict(all_unpaid, unknown, s_density, round(total_load), TNAME[composite],
                   list(findings), budgets)


NON_GATING = set()   # kinds the runner marks informational (e.g. DEAD review)


@dataclass
class Verdict:
    unpaid: float
    unknown: float
    s_density: float
    total_load: float
    tier: str               # composite, capped at STIPULATED
    findings: list
    budgets: dict
    context: str = "prod"
    reasons: list = field(default_factory=list)
    notes: list = field(default_factory=list)
    extra: dict = field(default_factory=dict)
    sha_prev: str = ""
    sha: str = ""

    def decide(self, context):
        self.context = context
        budget = self.budgets.get(context, self.budgets.get("prod", 8.0))
        self.reasons, self.notes = [], []
        if self.s_density > budget:
            self.reasons.append(
                f"structural overengineering density {self.s_density}/kAST "
                f"over {context} budget {budget}")
        for f in self.findings:
            if not f.gating and f.kind in REVIEW_NOTE:
                pass
        return self

    @property
    def ship(self):
        return not self.reasons

    def to_dict(self):
        d = {k: getattr(self, k) for k in
             ("context", "unpaid", "unknown", "s_density", "total_load",
              "tier", "reasons", "notes", "extra")}
        d["n_findings"] = len(self.findings)
        d["ship"] = self.ship
        return d


REVIEW_NOTE = set()


# ------------------------------------------------------------------ #
# seal — one hash-chain, shared by every tool                         #
# ------------------------------------------------------------------ #
def seal(verdict_dict, chain_path):
    p = pathlib.Path(chain_path)
    chain = json.loads(p.read_text()) if p.exists() else []
    # THE HISTORY HEARING: appending onto a chain that does not replay
    # extends a lie. Verify the shipped history by seal arithmetic
    # before minting anything onto it; a broken file is evidence and
    # must not be written over.
    if chain and replay_list(chain) is not True:
        raise ValueError(f"existing chain at {chain_path} does not "
                         f"replay — possible tampering; file preserved, "
                         f"sealing refused")
    prev = chain[-1]["sha"] if chain else "GENESIS"
    body = json.dumps(verdict_dict, sort_keys=True)
    verdict_dict["sha_prev"] = prev
    verdict_dict["sha"] = hashlib.sha256((prev + body).encode()).hexdigest()[:16]
    chain.append(verdict_dict)
    p.write_text(json.dumps(chain, indent=1))
    return verdict_dict


def replay_list(chain):
    """Replay an in-memory chain; True/False/None (not a chain)."""
    if not isinstance(chain, list) or not all(
            isinstance(g, dict) and "sha" in g and "sha_prev" in g
            for g in chain):
        return None
    prev = "GENESIS"
    for g in chain:
        body = json.dumps({k: v for k, v in g.items()
                           if k not in ("sha", "sha_prev")},
                          sort_keys=True)
        want = hashlib.sha256((prev + body).encode()).hexdigest()[:16]
        if g["sha_prev"] != prev or g["sha"] != want:
            return False
        prev = g["sha"]
    return True


def replay(chain_path):
    chain = json.loads(pathlib.Path(chain_path).read_text())
    prev = "GENESIS"
    for g in chain:
        body = {k: v for k, v in g.items() if k not in ("sha", "sha_prev")}
        want = hashlib.sha256(
            (prev + json.dumps(body, sort_keys=True)).encode()).hexdigest()[:16]
        if g["sha_prev"] != prev or g["sha"] != want:
            return False
        prev = g["sha"]
    return True


BASE_NONCLAIMS = [
    "NOT claimed: that flagged load is wrong to have. theta may demand it; "
    "the auditor cannot see all of theta. Every 'unpaid' tops out CONDITIONAL.",
    "NOT claimed: that a clean scan proves minimality. No flags raised is "
    "absence of evidence; the composite verdict caps at STIPULATED because "
    "the instrument is built of stipulations.",
    "NOT claimed: that low load == good code. Correctness, performance, and "
    "security are other carriers, other tools in this box.",
]
