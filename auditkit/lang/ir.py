"""
auditkit.lang.ir — the language-agnostic intermediate representation.
==========================================================================
Detectors consume THIS, never raw `ast`. That is the whole point of the
seam: a Python frontend (ast) fills it today; a Tree-sitter frontend fills
the same shapes tomorrow for JS/Go/Rust, and every detector keeps working
unchanged. Multi-language is a frontend problem, not a detector problem.
"""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class Symbol:
    name: str
    kind: str                       # 'class' | 'func'
    file: str
    line: int
    load: int                       # structural size (frontend-defined)
    refs: set = field(default_factory=set)      # names referenced in body
    bases: list = field(default_factory=list)   # base names (classes)
    is_abstract: bool = False
    n_methods: int = 0
    forwarder: bool = False         # body is a single delegating return
    methods_forwarder: bool = False # all methods forward/dunder (thin class)
    defaulted: list = field(default_factory=list)   # param names w/ defaults
    kwonly: list = field(default_factory=list)
    decorators: list = field(default_factory=list)
    body_hash: str = ""             # sha256[:16] of the symbol's AST dump
                                    # (change detection for the testimpact
                                    # carrier; "" = frontend didn't fill it)


@dataclass
class Module:
    name: str                       # importable stem
    file: str
    symbols: dict = field(default_factory=dict)   # name -> Symbol
    imports: set = field(default_factory=set)     # imported module stems
    from_names: set = field(default_factory=set)  # names imported (roots)
    exported: set = field(default_factory=set)    # __all__
    main_refs: set = field(default_factory=set)   # names under __main__ guard


@dataclass
class Program:
    modules: dict = field(default_factory=dict)   # name -> Module
    # global indexes (filled by the frontend)
    call_sites: dict = field(default_factory=dict)
    kw_used: dict = field(default_factory=dict)
    pos_arity: dict = field(default_factory=dict)
    subclasses: dict = field(default_factory=dict)  # base name -> [Symbol]
    sym_refs: dict = field(default_factory=dict)    # name -> {referenced names}
    code_roots: set = field(default_factory=set)
    total_load: int = 0

    @property
    def symbols(self):
        out = {}
        for m in self.modules.values():
            out.update(m.symbols)
        return out
