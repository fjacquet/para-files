"""Stage 4 exit: every module of the package is reachable from the CLI (no dead modules)."""

from __future__ import annotations

import ast
from pathlib import Path


SRC = Path(__file__).parent.parent / "src"
PACKAGE = SRC / "para_files"


def _name(path: Path) -> str:
    parts = list(path.relative_to(SRC).with_suffix("").parts)
    return ".".join(parts[:-1] if parts[-1] == "__init__" else parts)


MODULES = {_name(path): path for path in PACKAGE.rglob("*.py")}


def _imports(name: str) -> set[str]:
    path = MODULES[name]
    package = name if path.name == "__init__.py" else name.rpartition(".")[0]
    found: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            found |= {alias.name for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                head = ".".join(package.split(".")[: len(package.split(".")) - node.level + 1])
                base = f"{head}.{base}" if base else head
            found |= {base} | {f"{base}.{alias.name}" for alias in node.names}
    reached: set[str] = set()
    for dotted in found:
        module = dotted
        while module and module not in MODULES:
            module = module.rpartition(".")[0]
        if module:
            parts = module.split(".")
            reached |= {".".join(parts[:i]) for i in range(1, len(parts) + 1)}
    return reached & MODULES.keys()


def test_every_module_is_reachable_from_the_cli():
    seen: set[str] = set()
    todo = ["para_files.cli.app", "para_files.cli"]
    while todo:
        name = todo.pop()
        if name not in seen:
            seen.add(name)
            todo += sorted(_imports(name))
    assert sorted(MODULES.keys() - seen) == []
