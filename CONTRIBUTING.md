# Contributing — the Admission Gate

This repo evolves the way VCOS evolves: a contribution is a **candidate**,
and the gate admits it only if it earns its place. The gate cannot amend
itself (Mode 3): the admission rule lives above the detectors.

## A new detector must

1. **Declare its tier.** Where on the evidence ladder do its findings sit?
   If its thresholds are stipulations (most heuristics), the tier is
   `STIPULATED` and it should not hard-gate.
2. **Name its falsifier.** One sentence: what observation would overturn a
   finding? A detector with no falsifier is not admitted.
3. **Ship a positive and a negative fixture.** Source that *should* fire it,
   and source that should stay silent. The gate runs both; it admits only
   on `pos ≥ 1 and neg == 0`. A detector that can't catch its own example
   does not get to judge anyone's code.

```python
@detector(
    name="my_rule", tier="STIPULATED",
    falsifier="the structure is paid by a θ the artifact can't show",
    pos="...source that should raise...",
    neg="...source that should stay clean...")
def detect_my_rule(prog, ctx):
    return [Finding(...)]   # every Finding carries a falsifier
```

Run `python tests/run.py` — it prints the admission log and fails the build
if any detector is REJECTED or any parity/self-audit check breaks.

## Non-negotiables

- **No finding without a falsifier** (enforced in `Finding.__post_init__`).
- **The composite verdict caps at STIPULATED.** Don't add a path that lets
  the tool grade itself FORCED-clean.
- **Detectors speak IR, never `ast`.** Language specifics live in a frontend.
- **Declare scope honestly** in the non-claims when a detector is partial.
