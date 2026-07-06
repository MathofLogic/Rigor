"""
auditkit.runner — wire the spine together.
==========================================================================
parse(root) -> Program
  -> run every ADMITTED detector (gated through the registry)
  -> compose into a Verdict (weakest-link, STIPULATED self-cap)
  -> decide ship/block against the context budget
Config supplies the theta: roots, ignores, budgets, extension points,
disabled detectors, and whether DEAD gates.
"""
from __future__ import annotations
from .lang.python_frontend import parse
from .registry import GATE
from . import detectors  # noqa: F401  (import registers detectors via the gate)
from .core import compose, Finding
from . import config as cfg_mod


def analyze(root, context="prod", cfg=None):
    cfg = cfg or cfg_mod.load(root)
    prog = parse(root)
    findings = []
    for det in GATE.admitted():
        if det.name in cfg.disable:
            continue
        # detectors that accept explicit roots get them from config
        if det.name == "dead":
            fs = det.fn(prog, context, explicit_roots=tuple(cfg.roots))
        else:
            fs = det.fn(prog, context)
        # extension points declared in config clear matching SINGLE_IMPL
        if det.name == "single_impl" and cfg.extension_points:
            fs = [f for f in fs if f.name not in cfg.extension_points]
        for f in fs:
            if det.name == "dead" and cfg.gate_dead:
                f.gating = True
            findings.append(f)

    v = compose(findings, prog.total_load, cfg.budgets)
    v.decide(context)
    # DEAD review note (non-gating unless config opts in)
    n_dead = sum(1 for f in findings if f.kind == "DEAD")
    if n_dead and not cfg.gate_dead:
        v.notes.append(f"{n_dead} DEAD candidate(s) — review list, not gating "
                       "(dynamic dispatch evades static reachability; set "
                       "gate_dead=true for reflection-free apps)")
    elif n_dead and cfg.gate_dead:
        v.reasons.append(f"{n_dead} DEAD construct(s) gating (gate_dead=true)")
    v.extra = {"admission": GATE.summary(),
               "detectors": [d.name for d in GATE.admitted()
                             if d.name not in cfg.disable],
               "config": cfg.source}
    return v
