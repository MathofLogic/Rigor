"""
auditkit.config — .archaudit.toml, the declared theta.
==========================================================================
Config is where a team DECLARES the theta the auditor cannot see: which
names are roots, which paths to ignore, what budget the context tolerates,
which detectors are live, and which structures are paid-by-declaration.
A declared root turns a CONDITIONAL dead-finding FORCED; a declared
extension point clears a SINGLE_IMPL. Declaration is how you pay theta.

[archaudit]
budgets = { prod = 8.0, dev = 18.0 }
roots   = ["serve", "worker_main"]        # extra entry points
ignore  = ["migrations", "generated"]     # path fragments to skip
disable = ["name_smell"]                   # detectors to turn off
gate_dead = false                          # block on DEAD findings
"""
from __future__ import annotations
import tomllib, pathlib
from dataclasses import dataclass, field

DEFAULTS = {"budgets": {"prod": 8.0, "dev": 18.0}, "roots": [],
            "ignore": [], "disable": [], "gate_dead": False,
            "extension_points": []}


@dataclass
class Config:
    budgets: dict = field(default_factory=lambda: dict(DEFAULTS["budgets"]))
    roots: list = field(default_factory=list)
    ignore: list = field(default_factory=list)
    disable: list = field(default_factory=list)
    gate_dead: bool = False
    extension_points: list = field(default_factory=list)
    source: str = "defaults"


def load(root) -> Config:
    p = pathlib.Path(root)
    f = p / ".archaudit.toml" if p.is_dir() else p.parent / ".archaudit.toml"
    if not f.exists():
        return Config()
    data = tomllib.loads(f.read_text()).get("archaudit", {})
    merged = {**DEFAULTS, **data}
    return Config(budgets={**DEFAULTS["budgets"], **merged.get("budgets", {})},
                  roots=list(merged["roots"]), ignore=list(merged["ignore"]),
                  disable=list(merged["disable"]),
                  gate_dead=bool(merged["gate_dead"]),
                  extension_points=list(merged["extension_points"]),
                  source=str(f))
