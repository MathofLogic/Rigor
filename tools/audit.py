#!/usr/bin/env python3
"""
audit — one CLI for the toolbox.
==========================================================================
    audit arch <path> [--context dev|prod] [--json] [--roots a,b] [--gate-dead]

`arch` runs the architecture-load carrier (overengineering). It is the
first tool on the shared spine; `test` (vctest) and `deps` (bedrock) join
as subcommands once ported. Every tool prints a tiered, itemized verdict,
never a bare boolean, and seals to one hash-chain.
"""
import sys, json, argparse, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import auditkit
from auditkit import config as cfg_mod
from auditkit.core import BASE_NONCLAIMS

ARCH_NONCLAIMS = BASE_NONCLAIMS + [
    "NOT claimed: that DEAD is gating or settled. It is a review list; "
    "static reachability cannot see getattr/visitor/registry dispatch.",
    "PROVENANCE: structural budget (prod 8 / dev 18 per kAST) is EMPIRICAL "
    "n=6, calibrated on more_itertools/toolz/tqdm/click/jinja2/flask.",
    "SCOPE: the v1 IR models top-level symbols; method-level forwarders are "
    "a declared roadmap gap (ROADMAP: IR grows method nodes).",
]


def report(path, v):
    print(f"\n  audit arch — {path}   context={v.context}   "
          f"[{v.extra.get('admission','')}]")
    print("  " + "-" * 70)
    by = {}
    for f in v.findings:
        by.setdefault(f.file, []).append(f)
    if not by:
        print("   no findings (no flags != proof of minimality)")
    for fname, items in sorted(by.items()):
        print(f"   {fname}")
        for f in sorted(items, key=lambda x: x.line):
            tag = ("UNKNOWN" if f.v == 0.5 else "unpaid" if f.v < 0.5 else "paid")
            gate = "" if f.gating else "  (review)"
            print(f"      L{f.line:<4d} {f.kind:11s} {f.name:26.26s} "
                  f"v={f.v} [{tag}/{f.tier}]{gate}")
    print("  " + "-" * 70)
    print(f"   unpaid={v.unpaid}  unknown={v.unknown}  "
          f"structural={v.s_density}/kAST  total={v.total_load} AST")
    print(f"   VERDICT: {'SHIP' if v.ship else 'BLOCK'}/{v.tier}"
          " — composite capped at the instrument's weakest stipulation"
          + (("; " + "; ".join(v.reasons)) if v.reasons else ""))
    for n in v.notes:
        print(f"   note: {n}")
    print(f"   sealed: {v.sha} (prev {v.sha_prev})")
    print("  " + "-" * 70)
    for nc in ARCH_NONCLAIMS:
        print(f"   · {nc}")
    print()


def cmd_arch(a):
    cfg = cfg_mod.load(a.path)
    if a.roots:
        cfg.roots += [r.strip() for r in a.roots.split(",") if r.strip()]
    if a.gate_dead:
        cfg.gate_dead = True
    v = auditkit.analyze(a.path, a.context, cfg=cfg)
    d = v.to_dict()
    d["root"] = a.path
    auditkit.seal(d, a.chain)
    v.sha, v.sha_prev = d["sha"], d["sha_prev"]
    if a.json:
        print(json.dumps(d))
    else:
        report(a.path, v)
    return 0 if v.ship else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(prog="audit")
    sub = ap.add_subparsers(dest="cmd", required=True)
    pa = sub.add_parser("arch", help="architecture-load (overengineering)")
    pa.add_argument("path")
    pa.add_argument("--context", default="prod", choices=["dev", "prod"])
    pa.add_argument("--roots", default="")
    pa.add_argument("--gate-dead", action="store_true")
    pa.add_argument("--chain", default="audit_chain.json")
    pa.add_argument("--json", action="store_true")
    pa.set_defaults(fn=cmd_arch)
    a = ap.parse_args()
    sys.exit(a.fn(a))
