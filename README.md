# rigor

**The MathofLogic rigor harness. One carrier, many audit tools — every verdict priced, tiered, and sealed.**

Most tools that judge code (or papers) hand you a green checkmark. A
checkmark hides three things: *what kind of evidence* is behind it, *what it
cost* to earn, and *what would prove it wrong*. This repo replaces the
checkmark with a **verdict** that carries all three: an evidence **tier**, an
itemized **bill**, and a named **falsifier** for every finding.

The whole harness is one idea from Propagation Logic, applied repeatedly:

```
P / G → Q        a pattern P propagates through a gradient G to Q,
                 over a value space V, under a coherence threshold θ —
                 and the propagation has a cost, which goes on the books.
```

Every tool in the box is a different *carrier* of that same mechanism. The
spine is shared; the tools are thin.

```
            ┌──────────────────────────────────────────────┐
            │  auditkit  (the spine)                        │
            │  tiers · Finding/Verdict · weakest-link ·     │
            │  STIPULATED self-cap · seal/chain · IR ·      │
            │  Admission Gate (detectors plug in here)      │
            └──────┬──────────┬───────────┬────────┬───────┘
             audit arch   resistance    delta    testimpact
             (structure   (blast        (did the (run only the
              you pay      radius of     PR make  tests the
              for but      changing x)   it       change can
              don't need)                worse?)  reach)
```

## The evidence ladder

Every claim any tool makes sits on one rung. This is the vocabulary the
whole repo shares:

| tier | meaning |
|------|---------|
| **FORCED** | proved by complete enumeration on the artifact itself |
| **EMPIRICAL** | measured, or corroborated by independent observation |
| **CONDITIONAL** | holds *given* assumptions the artifact can't fully verify |
| **STIPULATED** | rests on a declared convention — a threshold, an ordering |
| **UNPAID** | asserted with no evidence; priced at zero |

Two composition rules do all the work:

- **Weakest link.** A system is an AND of its parts, so a composite verdict
  is never stronger than its weakest component.
- **The self-cap.** The instrument is built of stipulations (budgets, tier
  order, thresholds), so **no composite verdict ever exceeds STIPULATED**.
  A map that graded itself FORCED would be lying.

## Quick start

Python ≥ 3.11, stdlib only. No install step.

```bash
# audit a repo's architecture load
python tools/audit.py arch path/to/repo --context prod

# machine-readable, with declared roots
python tools/audit.py arch path/to/repo --roots serve,worker --json

# audit the CHANGE, not the snapshot: did this PR make it worse?
python tools/audit_delta.py all --repo . --base origin/main --summary pr.md

# run the whole build gate (admission + parity + self-audit + seal)
python tests/run.py

# the auditor audits its own source
python tools/audit.py arch auditkit --context dev
```

## The tools

### `audit arch` — the architecture-load carrier

Overengineering, made precise: **load added without a distinction θ needs**.
Seven detectors, each admitted through a gate that demands a declared tier,
a named falsifier, and positive/negative fixtures it must pass:

`DEAD` (reachability — a review list, never auto-gating), `SINGLE_IMPL`
(abstract seams with one implementation), `FORWARD` (functions that only
delegate), `SPEC_PARAM` (speculative parameters nobody passes),
`NAME_SMELL` (Manager/Helper/Util ceremony), `GOD_CLASS`, `CYCLE`.

Each finding prices its **paid fraction** `v ∈ [0,1]` — `v=0.5` is reserved
for "the artifact can't tell", which is itself information. Unpaid load
AND-sums, and the gate fires on **structural density**: unpaid load per
1000 AST nodes. The budget (8/kAST prod, 18 dev) is EMPIRICAL, n=6,
calibrated so that well-regarded libraries (more_itertools, toolz, tqdm,
click, jinja2) pass and tangle blocks.

**Declaring θ is how you pay it.** Config lives in `.archaudit.toml`
(see `docs/archaudit.example.toml`): a declared root turns a `DEAD` finding
FORCED; a declared extension point clears a `SINGLE_IMPL`. The auditor
can't see your whole θ — so it lets you state it, and holds you to what
you stated.

### `resistance` — the change-resistance carrier

`R(x)` = the blast radius of changing `x`: the transitive set of symbols
that break, by reverse reachability. The **count is FORCED** (pure
enumeration); "this will hurt to change" is CONDITIONAL, because whether
you *must* change x lives in θ, not in the AST.

### `delta` — audit the change, not the snapshot

Diffs two sealed signatures (base ref vs working tree or head ref) and
gates on two signals: **θ-cliff crossings** (a symbol's blast radius
crossed into hub territory) and **net load added over a delta budget**.
This is the review-burnout tool: gate the PR, not the repo.
`docs/example_pr_summary.md` shows the markdown it posts to a PR.

### `testimpact` — run only the tests the change can reach

A change is a reconfiguration of a symbol set; a test's reach is its
forward closure over the reference graph. Tests outside the reach are
skipped — **with a tier on the soundness of the skip**, and any test
touching dynamic dispatch (`getattr`, registries) is kept unconditionally.
Selective CI without the silent-breakage fear.

### `benchmark.py` — measure before claiming

Profiles repos on resistance + arch + determinism. The comparison column
against LLM reviewers is a **declared stub** — it stays empty until it's
run, because a benchmark scheduled for later is an UNPAID claim now.

## The Rigor Suite (papers, not code)

`suite/rigor-suite-instrument.html` is the reference instrument for the
**Rigor Suite** — the same discipline pointed at scientific papers.
Paste an abstract and central claims; it runs eight lenses (L0–L7) in three
staged passes: claim typing (`[stipulated]` / `[forced]` / `[empirical]` /
`[presumed]`), the logic silently presumed (via the 0.5 test), hidden
ontology, the theory-dependency graph, reification, overflow exposure, and
a final **honesty delta** — the sentences the paper should add to disclose
its load. Findings are disclosures to be checked, never verdicts: a paper
resting on a hidden commitment may be entirely correct.

The full protocol, including the section where **the suite audits itself**,
is `docs/therigorsuiteprotocol.pdf`.

## Design commitments

- **The spine is the product.** Tools are thin; the carrier is shared.
- **No finding without a falsifier.** Enforced in `Finding.__post_init__`.
- **The auditor prices itself.** `tests/run.py` runs the toolbox on its own
  source; its self-verdict is STIPULATED by construction, never FORCED-clean.
- **Findings are deterministic; seals are historical.** Two runs produce
  byte-identical findings. Only the seal differs — each seal commits to the
  previous chain link (`auditkit.core.seal` / `replay`), so the audit log is
  tamper-evident: mutate one sealed verdict and replay breaks at that link.
- **Multi-language is a frontend problem.** Detectors speak IR, never `ast`.
  The Tree-sitter seam is declared in `auditkit/lang/treesitter_frontend.py`.
- **Non-claims are printed with every verdict.** What the tool does *not*
  assert (that flagged load is wrong to have, that a clean scan proves
  minimality, that low load means good code) ships in the output itself.

## Repository map

```
auditkit/            the spine + carriers (stdlib only)
  lang/              IR + Python frontend + declared Tree-sitter seam
tools/               audit.py (CLI), audit_delta.py (PR gate)
tests/run.py         the build gate; fixtures under tests/fixtures/
suite/               the Rigor Suite reference instrument (HTML)
docs/                protocol PDF, config example, PR-summary example,
                     SOURCE_AUDIT.md (what was broken in the sources
                     and exactly what was changed — read this first
                     if you knew the pre-refactor dump)
benchmark.py         the honest-benchmark harness
.github/workflows/   CI: gate + self-audit + delta on every PR
```

## Provenance and scope

This repo is one standalone piece of the MathofLogic project. The
Propagation Logic **kernel** (`pl.py`, the three-valued atlas, the DRAS
demos, the verified workbook) lives in its own repo; this harness depends
on none of it at runtime — it inherits only the vocabulary. Every source
file here was executed and verified before inclusion; the fixes and
re-pins are itemized in `docs/SOURCE_AUDIT.md`.

## License

MIT. Trust infrastructure should not be paywalled.
