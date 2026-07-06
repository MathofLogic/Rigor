"""
auditkit.lang.treesitter_frontend — DECLARED SEAM (not yet implemented).
==========================================================================
This file exists to make the multi-language commitment honest and visible.
A Tree-sitter frontend produces the SAME ir.Program shape as the Python
frontend, so every detector that speaks IR works on JS/Go/Rust/... unchanged.

Status: STIPULATED scaffold. Implementing this is a roadmap item, admitted
through the same gate (it must fill Program for a fixture repo and pass a
parity check against hand-built IR). Until then it raises, loudly, rather
than pretending to work.
"""
from .ir import Program

def parse(root, language: str) -> Program:           # pragma: no cover
    raise NotImplementedError(
        "Tree-sitter frontend is a declared roadmap seam (ROADMAP.md, "
        "item: multi-language). It must produce ir.Program and pass a "
        "parity check before admission. Use lang.python_frontend today.")
