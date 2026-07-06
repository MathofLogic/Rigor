"""
auditkit.detectors — the carrier's eyes.
==========================================================================
Each detector is registered through the Admission Gate with a tier, a
falsifier, and a self-test. They are kept in ONE module on purpose: seven
small detectors split into seven files would be the exact unpaid
indirection archload flags. We split when a detector grows a real internal
seam — not before. (Eating our own dogfood.)

Ported from archload:  DEAD, SINGLE_IMPL, FORWARD, SPEC_PARAM, NAME_SMELL
New, via the gate:      GOD_CLASS, CYCLE
"""
from __future__ import annotations
from .core import Finding
from .registry import detector

ROOT_NAMES = {"main", "run", "handler", "lambda_handler", "application",
              "wsgi", "app", "cli", "setup", "create_app"}
SMELL = {"Manager", "Factory", "Helper", "Util", "Utils", "Wrapper",
         "Handler", "Processor", "Coordinator", "Provider", "Engine",
         "Service", "Controller"}
GOD_METHODS, GOD_LOAD = 15, 400      # stipulated thresholds


def _reachable(symbols, sym_refs, roots):
    seen, stack = set(), [r for r in roots if r in symbols]
    while stack:
        s = stack.pop()
        if s in seen:
            continue
        seen.add(s)
        for nxt in sym_refs.get(s, ()):
            if nxt in symbols and nxt not in seen:
                stack.append(nxt)
    return seen


# ------------------------------------------------------------------ #
# DEAD — reachability from roots. Review list (non-gating) by default. #
# ------------------------------------------------------------------ #
@detector(
    name="dead", tier="CONDITIONAL", gating=False,
    falsifier="a getattr/visitor/registry/entry-point edge the AST cannot see",
    pos="def used():\n return orphan()\ndef live():\n return used()\n"
        "def __main__():\n pass\nif __name__=='__main__':\n live()\n"
        "def orphan_unreachable():\n return 1\n",
    neg="def run():\n return helper()\ndef helper():\n return 1\n")
def detect_dead(prog, ctx, explicit_roots=()):
    symbols = prog.symbols
    declared = set(explicit_roots) | prog.code_roots
    roots = set(declared)
    roots |= {n for n in symbols if n in ROOT_NAMES or n.lower() in ROOT_NAMES}
    roots |= {n for n in symbols if n.startswith("__") or n.startswith("test_")}
    live = _reachable(set(symbols), prog.sym_refs, roots)
    tier = "FORCED" if declared else "CONDITIONAL"
    out = []
    for name, s in symbols.items():
        if name in roots or name.startswith("__") or name.startswith("test_"):
            continue
        if name not in live:
            out.append(Finding("dead", "DEAD", name, s.file, s.line, s.load,
                               0.0, tier, "this name is reached only "
                               "dynamically, or is an undeclared entry point "
                               "— pass roots to settle it", gating=False))
    return out


# ------------------------------------------------------------------ #
# SINGLE_IMPL — abstract seam priced for a swap that isn't exercised   #
# ------------------------------------------------------------------ #
@detector(
    name="single_impl", tier="CONDITIONAL",
    falsifier="a second implementation exists outside the tree, or this is a "
              "published extension point for external implementers",
    pos="from abc import ABC, abstractmethod\nclass Base(ABC):\n"
        " @abstractmethod\n def go(self): ...\nclass Only(Base):\n"
        " def go(self): return 1\nx=Only()\n",
    neg="from abc import ABC, abstractmethod\nclass B(ABC):\n"
        " @abstractmethod\n def go(self): ...\nclass A1(B):\n def go(self): return 1\n"
        "class A2(B):\n def go(self): return 2\na=A1();b=A2()\n")
def detect_single_impl(prog, ctx):
    out = []
    for name, s in prog.symbols.items():
        if s.kind != "class" or not s.is_abstract:
            continue
        impls = [c for c in prog.subclasses.get(name, []) if not c.is_abstract]
        if len(impls) == 1:
            out.append(Finding("single_impl", "SINGLE_IMPL", name, s.file,
                               s.line, s.load, 0.3, "CONDITIONAL",
                               "a second impl exists outside the tree / this "
                               "is a published extension point"))
        elif len(impls) == 0:
            out.append(Finding("single_impl", "SINGLE_IMPL", name, s.file,
                               s.line, s.load, 0.5, "CONDITIONAL",
                               "external implementers exist (cannot tell from "
                               "the artifact) -> UNKNOWN, not asserted unpaid"))
    return out


# ------------------------------------------------------------------ #
# FORWARD — single-caller delegating wrapper, an unpaid indirection    #
# ------------------------------------------------------------------ #
@detector(
    name="forward", tier="CONDITIONAL",
    falsifier="the wrapper stabilizes a public API or adapts across a "
              "module boundary",
    pos="def real(x): return x+1\ndef wrap(x): return real(x)\ndef run():\n"
        " return wrap(1)\n",
    neg="def real(x): return x+1\ndef wrap(x): return real(x)\n"
        "def a():\n return wrap(1)\ndef b():\n return wrap(2)\n")
def detect_forward(prog, ctx):
    out = []
    for name, s in prog.symbols.items():
        if s.kind != "func" or not s.forwarder or name.startswith("__"):
            continue
        if prog.call_sites.get(name, 0) == 1:
            out.append(Finding("forward", "FORWARD", name, s.file, s.line,
                               s.load, 0.2, "CONDITIONAL",
                               "this wrapper stabilizes a public API or "
                               "adapts across a module boundary"))
    return out


# ------------------------------------------------------------------ #
# SPEC_PARAM — a defaulted knob no in-tree caller ever turns           #
# ------------------------------------------------------------------ #
@detector(
    name="spec_param", tier="CONDITIONAL",
    falsifier="a caller outside the tree (public API) sets this parameter",
    pos="def f(a, flag=False, mode='x'):\n return a\ndef run():\n return f(1)\n",
    neg="def f(a, flag=False):\n return a\ndef run():\n return f(1, flag=True)\n")
def detect_spec_param(prog, ctx):
    out = []
    for name, s in prog.symbols.items():
        if s.kind != "func" or prog.call_sites.get(name, 0) == 0:
            continue
        ever = prog.kw_used.get(name, set())
        max_pos = max(prog.pos_arity.get(name, {0}))
        n_pos = getattr(s, "extra_pos", 0)
        # positional defaults never passed beyond observed arity
        for i, pname in enumerate(s.defaulted):
            idx = n_pos - len(s.defaulted) + i
            if pname not in ever and idx >= max_pos:
                out.append(Finding("spec_param", "SPEC_PARAM",
                                   f"{name}({pname})", s.file, s.line, 3, 0.3,
                                   "CONDITIONAL", "a public-API caller outside "
                                   "the tree sets this"))
        for pname in s.kwonly:
            if pname not in ever:
                out.append(Finding("spec_param", "SPEC_PARAM",
                                   f"{name}({pname}=)", s.file, s.line, 3, 0.3,
                                   "CONDITIONAL", "a public-API caller outside "
                                   "the tree sets this"))
    return out


# ------------------------------------------------------------------ #
# NAME_SMELL — a Manager/Factory/... that is also thin (stipulated)    #
# ------------------------------------------------------------------ #
@detector(
    name="name_smell", tier="STIPULATED",
    falsifier="the name is a convention, not evidence; this class may carry "
              "real coordination logic the heuristic misses",
    pos="class ThingManager:\n def __init__(self, t): self._t=t\n"
        " def go(self): return self._t.go()\n",
    neg="class Order:\n def total(self): return sum(self.items)\n")
def detect_name_smell(prog, ctx):
    out = []
    for name, s in prog.symbols.items():
        if s.kind != "class":
            continue
        if any(name.endswith(x) or name == x for x in SMELL) and s.methods_forwarder:
            out.append(Finding("name_smell", "NAME_SMELL", name, s.file,
                               s.line, s.load, 0.5, "STIPULATED",
                               "the name is convention, not evidence; may "
                               "carry real coordination logic"))
    return out


# ================================================================== #
# NEW DETECTORS — admitted through the same gate                       #
# ================================================================== #

# GOD_CLASS — a class concentrating load that should be distributed.
# Carrier framing: it makes many distinctions but they do not cohere;
# the load belongs to several carriers fused into one. Thresholds are
# stipulated, so the tier is STIPULATED and it does not hard-gate.
@detector(
    name="god_class", tier="STIPULATED", gating=False,
    falsifier="a cohesive large class (state machine, generated client, "
              "parser table) whose parts genuinely share state — split would "
              "raise load, not lower it",
    pos="class God:\n" + "".join(
        f" def m{i}(self, x):\n  y=x+{i}\n  z=y*2\n  return z-{i}\n"
        for i in range(16)),
    neg="class Small:\n def a(self): return 1\n def b(self): return 2\n")
def detect_god_class(prog, ctx):
    out = []
    for name, s in prog.symbols.items():
        if s.kind != "class":
            continue
        if s.n_methods >= GOD_METHODS and s.load >= GOD_LOAD:
            out.append(Finding("god_class", "GOD_CLASS", name, s.file, s.line,
                               s.load, 0.3, "STIPULATED",
                               f"cohesive by design ({s.n_methods} methods, "
                               f"load {s.load}); declare it or measure "
                               "cohesion (LCOM) before splitting", gating=False))
    return out


# CYCLE — modules that import each other: two mirrors, no acyclic seam.
# Echoes vctest's Mode 4. The cycle's EXISTENCE is forced by enumeration;
# whether it is harmful is CONDITIONAL (some cycles are intentional facades).
@detector(
    name="cycle", tier="CONDITIONAL",
    falsifier="the cycle is intentional/contained (TYPE_CHECKING-only import, "
              "a package facade, or runtime-guarded)",
    pos={"a.py": "from b import beta\ndef alpha(): return beta()\n",
         "b.py": "from a import alpha\ndef beta(): return alpha()\n"},
    neg={"a.py": "from b import beta\ndef alpha(): return beta()\n",
         "b.py": "def beta(): return 1\n"})
def detect_cycle(prog, ctx):
    names = set(prog.modules)
    graph = {m: (prog.modules[m].imports & names) - {m} for m in names}
    # Tarjan SCC
    idx = {}
    low = {}
    onstack = {}
    stack = []
    counter = [0]
    sccs = []

    def strong(v):
        idx[v] = low[v] = counter[0]
        counter[0] += 1
        stack.append(v)
        onstack[v] = True
        for w in graph.get(v, ()):
            if w not in idx:
                strong(w)
                low[v] = min(low[v], low[w])
            elif onstack.get(w):
                low[v] = min(low[v], idx[w])
        if low[v] == idx[v]:
            comp = []
            while True:
                w = stack.pop()
                onstack[w] = False
                comp.append(w)
                if w == v:
                    break
            sccs.append(comp)

    for v in names:
        if v not in idx:
            strong(v)

    out = []
    for comp in sccs:
        if len(comp) > 1:
            cyc = " <-> ".join(sorted(comp))
            mod0 = prog.modules[sorted(comp)[0]]
            out.append(Finding("cycle", "CYCLE", cyc, mod0.file, 1,
                               12 * len(comp), 0.2, "CONDITIONAL",
                               "the cycle is intentional/contained "
                               "(TYPE_CHECKING-only, facade, runtime-guarded)"))
    return out
