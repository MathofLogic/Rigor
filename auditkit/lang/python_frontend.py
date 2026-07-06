"""
auditkit.lang.python_frontend — fills the IR from Python `ast`.
==========================================================================
This is the ONE place that knows about `ast`. Everything downstream speaks
IR. A Tree-sitter frontend would live beside this file and produce the same
Program shape; see lang/treesitter_frontend.py (declared seam).
"""
from __future__ import annotations
import ast, pathlib, hashlib
from collections import defaultdict
from .ir import Symbol, Module, Program

DYNAMIC_DECOS = ("route", "fixture", "register", "command", "task",
                 "app.", "cli.", "bp.", "celery", "rpc")
SKIP_DIRS = {".venv", "venv", "site-packages", "__pycache__",
             "build", "dist", ".git"}


def _size(node):
    return sum(1 for _ in ast.walk(node))


def _names_in(node):
    out = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Name):
            out.add(n.id)
        elif isinstance(n, ast.Attribute):
            out.add(n.attr)
    return out


def _is_abstract(cls):
    bases = {ast.unparse(b) for b in cls.bases}
    if any("ABC" in b or "Protocol" in b for b in bases):
        return True
    for n in cls.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if any("abstractmethod" in ast.unparse(d) for d in n.decorator_list):
                return True
            body = [s for s in n.body if not (isinstance(s, ast.Expr)
                    and isinstance(s.value, ast.Constant))]
            if body and all(
                (isinstance(s, ast.Raise) and "NotImplementedError" in ast.unparse(s))
                or isinstance(s, ast.Pass)
                or (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant)
                    and s.value.value is Ellipsis)
                for s in body):
                return True
    return False


def _is_forwarder(fn):
    body = [s for s in fn.body if not (isinstance(s, ast.Expr)
            and isinstance(s.value, ast.Constant))]
    if len(body) != 1:
        return False
    s = body[0]
    call = None
    if isinstance(s, ast.Return) and isinstance(s.value, ast.Call):
        call = s.value
    elif isinstance(s, ast.Return) and isinstance(s.value, ast.Await) \
            and isinstance(s.value.value, ast.Call):
        call = s.value.value
    elif isinstance(s, ast.Expr) and isinstance(s.value, ast.Call):
        call = s.value
    if call is None:
        return False
    for a in list(call.args) + [k.value for k in call.keywords]:
        if not isinstance(a, (ast.Name, ast.Attribute, ast.Starred, ast.Constant)):
            return False
    return True


def parse(root) -> Program:
    files = {}
    for p in sorted(pathlib.Path(root).rglob("*.py")):
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        try:
            files[p] = ast.parse(p.read_text(), filename=str(p))
        except (SyntaxError, UnicodeDecodeError):
            continue

    prog = Program()
    call_sites = defaultdict(int)
    kw_used = defaultdict(set)
    pos_arity = defaultdict(set)
    subclasses = defaultdict(list)
    sym_refs = defaultdict(set)

    for path, tree in files.items():
        mod = Module(name=path.stem, file=path.name)
        for n in tree.body:
            if isinstance(n, ast.ClassDef):
                methods = [m for m in n.body
                           if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))]
                thin = bool(methods) and all(
                    _is_forwarder(m) or m.name.startswith("__") for m in methods)
                sym = Symbol(n.name, "class", path.name, n.lineno, _size(n),
                             refs=_names_in(n) - {n.name},
                             bases=[ast.unparse(b).split(".")[-1] for b in n.bases],
                             is_abstract=_is_abstract(n), n_methods=len(methods),
                             methods_forwarder=thin,
                             decorators=[ast.unparse(d) for d in n.decorator_list])
                sym.body_hash = hashlib.sha256(ast.dump(n).encode()).hexdigest()[:16]
                mod.symbols[n.name] = sym
                prog.total_load += sym.load
                for b in sym.bases:
                    subclasses[b].append(sym)
                sym_refs[n.name] |= sym.refs
                if any(any(t in d for t in DYNAMIC_DECOS) for d in sym.decorators):
                    prog.code_roots.add(n.name)
            elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                defaulted = ([a.arg for a in n.args.args[-len(n.args.defaults):]]
                             if n.args.defaults else [])
                sym = Symbol(n.name, "func", path.name, n.lineno, _size(n),
                             refs=_names_in(n) - {n.name},
                             forwarder=_is_forwarder(n),
                             defaulted=defaulted,
                             kwonly=[a.arg for a in n.args.kwonlyargs],
                             decorators=[ast.unparse(d) for d in n.decorator_list])
                sym.extra_pos = len(n.args.args)
                sym.body_hash = hashlib.sha256(ast.dump(n).encode()).hexdigest()[:16]
                mod.symbols[n.name] = sym
                prog.total_load += sym.load
                sym_refs[n.name] |= sym.refs
                if any(any(t in d for t in DYNAMIC_DECOS) for d in sym.decorators):
                    prog.code_roots.add(n.name)
            elif isinstance(n, ast.If) and "__main__" in ast.unparse(n.test):
                mod.main_refs |= _names_in(n)
                prog.code_roots |= _names_in(n)
            elif isinstance(n, ast.Assign) and any(
                    isinstance(t, ast.Name) and t.id == "__all__" for t in n.targets):
                if isinstance(n.value, (ast.List, ast.Tuple)):
                    mod.exported |= {e.value for e in n.value.elts
                                     if isinstance(e, ast.Constant)}
        # imports (module-level + nested) for roots and the dep graph
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                mod.imports |= {a.name.split(".")[0] for a in n.names}
            elif isinstance(n, ast.ImportFrom):
                if n.module:
                    mod.imports.add(n.module.split(".")[0])
                mod.from_names |= {a.asname or a.name for a in n.names}
        prog.code_roots |= mod.exported | mod.from_names
        prog.modules[path.stem] = mod

    # call-site indexes
    for path, tree in files.items():
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                f = node.func
                name = (f.id if isinstance(f, ast.Name)
                        else f.attr if isinstance(f, ast.Attribute) else None)
                if name:
                    call_sites[name] += 1
                    pos_arity[name].add(len(node.args))
                    kw_used[name] |= {k.arg for k in node.keywords if k.arg}

    prog.call_sites = dict(call_sites)
    prog.kw_used = dict(kw_used)
    prog.pos_arity = dict(pos_arity)
    prog.subclasses = dict(subclasses)
    prog.sym_refs = dict(sym_refs)
    return prog
