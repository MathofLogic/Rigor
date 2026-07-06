#!/usr/bin/env python3
"""
audit_delta — gate a change against its base. Usage:
    audit_delta.py [resistance|arch|all] --repo . --base <ref> [--head <ref>]
                   [--summary <file>]   # GitHub step-summary markdown

Exit code 0 = SHIP, 1 = BLOCK — so CI fails the check when a change adds a
theta-cliff crossing or pushes added load past the delta budget.
"""
import sys, argparse, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from auditkit import delta


def md_summary(deltas):
    lines = ["## audit delta — did this change make it worse?\n"]
    worst = False
    for d in deltas:
        verdict = "✅ SHIP" if d.ship else "🛑 BLOCK"
        worst = worst or not d.ship
        lines.append(f"### `{d.carrier}` — {verdict} (net {d.net:+})")
        if d.crossings:
            lines.append("**θ-cliff crossings (a symbol became a hub):**\n")
            for k, (b, h) in sorted(d.crossings.items(), key=lambda x: -x[1][1]):
                lines.append(f"- `{k}` blast radius {b} → **{h}** (cliff {d.cliff})")
        if d.added:
            top = sorted(d.added.items(), key=lambda x: -x[1])[:5]
            lines.append("\n**load added to existing symbols:** "
                         + ", ".join(f"`{k}` +{v}" for k, v in top))
        if d.reasons:
            lines.append("\n> " + "; ".join(d.reasons))
        lines.append("\n_tier: per-symbol counts are FORCED; the delta budget is "
                     "STIPULATED, so the composite verdict caps at STIPULATED._\n")
    return "\n".join(lines), worst


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("carrier", nargs="?", default="all",
                    choices=["resistance", "arch", "all"])
    ap.add_argument("--repo", default=".")
    ap.add_argument("--base", required=True)
    ap.add_argument("--head", default=None)
    ap.add_argument("--summary", default=None)
    ap.add_argument("--chain", default="delta_chain.json")
    a = ap.parse_args()

    carriers = ["resistance", "arch"] if a.carrier == "all" else [a.carrier]
    deltas = []
    for c in carriers:
        d = delta.run_delta(a.repo, c, a.base, a.head, a.chain)
        delta.report(d)
        deltas.append(d)

    md, blocked = md_summary(deltas)
    if a.summary:
        pathlib.Path(a.summary).write_text(md)
    sys.exit(1 if blocked else 0)
