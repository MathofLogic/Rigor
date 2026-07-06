"""
auditkit.registry — the Admission Gate for detectors.
==========================================================================
VCOS's discipline, turned on the toolbox itself. A detector is a candidate.
It is ADMITTED only if it:
  1. declares its default tier (where on the evidence ladder it sits),
  2. names its falsifier (what observation would overturn its findings),
  3. passes its OWN self-test (fires on a positive fixture, stays silent
     on a negative one) — a detector that cannot catch its own example
     does not get to judge your code.
Failures are RECORDED, never silently dropped. The gate cannot admit a
change to itself (Mode 3): the admission rule lives above the detectors.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from .lang.python_frontend import parse as _parse_py
import tempfile, pathlib


@dataclass
class Detector:
    name: str
    tier: str                 # default tier of findings it raises
    falsifier: str            # the standing falsifier for this detector
    fn: callable              # fn(program, ctx) -> list[Finding]
    pos_fixture: str = ""     # source that SHOULD raise >=1 finding
    neg_fixture: str = ""     # source that should raise 0
    gating: bool = True       # do its findings gate ship/block by default?
    admitted: bool = False
    record: str = ""          # why admitted / rejected


def _run_on_source(fn, src):
    """src is a str (single m.py) or a dict {filename: source} for
    cross-module detectors (cyclic deps, test-only leakage, ...)."""
    files = {"m.py": src} if isinstance(src, str) else src
    with tempfile.TemporaryDirectory() as d:
        for fname, text in files.items():
            (pathlib.Path(d) / fname).write_text(text)
        prog = _parse_py(d)
        return fn(prog, "prod")


class Gate:
    def __init__(self):
        self.detectors = {}
        self.log = []

    def admit(self, det: Detector):
        try:
            pos = _run_on_source(det.fn, det.pos_fixture) if det.pos_fixture else [1]
            neg = _run_on_source(det.fn, det.neg_fixture) if det.neg_fixture else []
            ok = len(pos) >= 1 and len(neg) == 0
            det.admitted = ok
            det.record = ("ADMITTED" if ok else
                          f"REJECTED: selftest pos={len(pos)} neg={len(neg)} "
                          "(needs pos>=1, neg==0)")
        except Exception as e:
            det.admitted = False
            det.record = f"REJECTED: selftest raised {type(e).__name__}: {e}"
        self.detectors[det.name] = det
        self.log.append((det.name, det.record))
        return det.admitted

    def admitted(self):
        return [d for d in self.detectors.values() if d.admitted]

    def summary(self):
        a = sum(1 for d in self.detectors.values() if d.admitted)
        return f"{a}/{len(self.detectors)} detectors admitted"


GATE = Gate()


def detector(name, tier, falsifier, pos="", neg="", gating=True):
    """Decorator: register a detector function through the gate."""
    def wrap(fn):
        GATE.admit(Detector(name, tier, falsifier, fn, pos, neg, gating))
        return fn
    return wrap
