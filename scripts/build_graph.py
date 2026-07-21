"""AST-based static code graph generator for the etsy_pipeline codebase.

Walks all Python source files under configured roots and produces a JSON
dependency/call graph at .repo-graph/graph.json. The graph is the primary
structural prior for agent sessions — read it first, open source files second.

Usage:
    python scripts/build_graph.py               # generate graph
    python scripts/build_graph.py --check       # fail if graph would change (CI mode)
    python scripts/build_graph.py --out PATH    # write to custom path

Limitations:
    - Static analysis only. Dynamic dispatch, getattr(), and runtime-constructed
      calls are not captured. All edges carry "static_only": true.
    - Call edges are detected by name matching within function bodies. Indirect
      calls through aliases are not resolved.
"""

from __future__ import annotations

import ast
import hashlib
import json
import sys
from argparse import ArgumentParser
from datetime import datetime

try:
    from datetime import UTC
except ImportError:
    import datetime as dt

    UTC = dt.UTC
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
SCAN_ROOTS: list[Path] = [
    REPO_ROOT / "etsy_pipeline",
    REPO_ROOT / "scripts",
    REPO_ROOT / "tests",
]
OUTPUT_PATH = REPO_ROOT / ".repo-graph" / "graph.json"
SCHEMA_VERSION = "1.0"

# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------


def _get_docstring_summary(node: ast.AST) -> str:
    """Return the first line of a node's docstring, or empty string.

    Args:
        node: An AST node that may have a docstring (Module, ClassDef, FunctionDef).

    Returns:
        First line of the docstring, stripped, or empty string if absent.
    """
    raw = ast.get_docstring(node)
    if not raw:
        return ""
    return raw.strip().splitlines()[0].strip()


def _is_public(name: str) -> bool:
    """Return True if a name is considered part of the public interface.

    Args:
        name: Function or method name.

    Returns:
        True if the name does not start with an underscore.
    """
    return not name.startswith("_")


def _module_id(path: Path) -> str:
    """Convert a file path to a dotted module identifier.

    Args:
        path: Absolute path to a Python file.

    Returns:
        Dotted module string relative to the repo root (e.g. 'etsy_pipeline.models.job').
    """
    relative = path.relative_to(REPO_ROOT)
    parts = list(relative.with_suffix("").parts)
    # Drop __init__ — the package itself is the module
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _collect_calls(func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    """Extract called names from a function body (best-effort, static only).

    Args:
        func_node: A function definition AST node.

    Returns:
        List of called name strings (may include method names without class context).
    """
    calls: list[str] = []
    for node in ast.walk(func_node):
        if isinstance(node, ast.Call):
            # Direct call: foo()
            if isinstance(node.func, ast.Name):
                calls.append(node.func.id)
            # Attribute call: self.foo() or module.foo()
            elif isinstance(node.func, ast.Attribute):
                calls.append(node.func.attr)
    return calls


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------


class GraphBuilder:
    """Builds a JSON code graph by walking Python source files via the AST.

    The graph has two top-level lists: nodes (modules, classes, functions)
    and edges (import and call relationships).

    Usage:
        builder = GraphBuilder()
        builder.scan()
        graph = builder.to_dict()
    """

    def __init__(self) -> None:
        """Initialize an empty graph builder."""
        self._nodes: list[dict[str, Any]] = []
        self._edges: list[dict[str, Any]] = []
        # Map: file path → module_id, for resolving local imports
        self._path_to_module: dict[Path, str] = {}

    def scan(self) -> None:
        """Walk all configured scan roots and build the graph.

        Collects all .py files, parses them, and extracts nodes + edges.
        """
        py_files: list[Path] = []
        for root in SCAN_ROOTS:
            if root.exists():
                py_files.extend(sorted(root.rglob("*.py")))

        # First pass: register all module IDs so import resolution works
        for path in py_files:
            self._path_to_module[path] = _module_id(path)

        # Second pass: extract nodes and edges from each file
        for path in py_files:
            self._process_file(path)

    def _process_file(self, path: Path) -> None:
        """Parse a single Python file and extract its graph contributions.

        Args:
            path: Absolute path to the Python source file.
        """
        source = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError:
            return

        mod_id = _module_id(path)
        rel_path = str(path.relative_to(REPO_ROOT)).replace("\\", "/")

        # Collect top-level class and function IDs for the module node
        child_ids: list[str] = []
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                child_ids.append(f"{mod_id}.{node.name}")

        # Module node
        self._nodes.append(
            {
                "id": mod_id,
                "kind": "module",
                "path": rel_path,
                "docstring_summary": _get_docstring_summary(tree),
                "children": child_ids,
            }
        )

        # Import edges from this module
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self._edges.append(
                        {
                            "from": mod_id,
                            "to": alias.name,
                            "kind": "import",
                            "static_only": True,
                        }
                    )
            elif isinstance(node, ast.ImportFrom):
                base = node.module or ""
                # Resolve relative imports
                if node.level and node.level > 0:
                    parts = mod_id.split(".")
                    base_parts = parts[: -(node.level)]
                    if base:
                        base = ".".join(base_parts) + "." + base
                    else:
                        base = ".".join(base_parts)
                for alias in node.names:
                    target = f"{base}.{alias.name}" if base else alias.name
                    self._edges.append(
                        {
                            "from": mod_id,
                            "to": target,
                            "kind": "import",
                            "static_only": True,
                        }
                    )

        # Class and function nodes
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                self._process_class(node, mod_id)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._process_function(node, mod_id, parent_class=None)

    def _process_class(self, class_node: ast.ClassDef, mod_id: str) -> None:
        """Extract a class node and all its method nodes.

        Args:
            class_node: The AST ClassDef node.
            mod_id: The dotted module identifier this class belongs to.
        """
        class_id = f"{mod_id}.{class_node.name}"
        method_names: list[str] = []

        for node in ast.iter_child_nodes(class_node):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                method_names.append(node.name)

        self._nodes.append(
            {
                "id": class_id,
                "kind": "class",
                "module": mod_id,
                "docstring_summary": _get_docstring_summary(class_node),
                "methods": method_names,
                "public_methods": [m for m in method_names if _is_public(m)],
            }
        )

        # Process each method
        for node in ast.iter_child_nodes(class_node):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._process_function(node, mod_id, parent_class=class_node.name)

    def _process_function(
        self,
        func_node: ast.FunctionDef | ast.AsyncFunctionDef,
        mod_id: str,
        parent_class: str | None,
    ) -> None:
        """Extract a function/method node and its outbound call edges.

        Args:
            func_node: The AST function definition node.
            mod_id: The dotted module identifier.
            parent_class: Class name if this is a method, else None.
        """
        prefix = f"{mod_id}.{parent_class}" if parent_class else mod_id
        func_id = f"{prefix}.{func_node.name}"

        # Build signature string from arguments
        args = func_node.args
        arg_names = [a.arg for a in args.args]
        sig = f"({', '.join(arg_names)})"

        node_entry: dict[str, Any] = {
            "id": func_id,
            "kind": "function",
            "module": mod_id,
            "docstring_summary": _get_docstring_summary(func_node),
            "signature": sig,
            "is_public": _is_public(func_node.name),
            "is_async": isinstance(func_node, ast.AsyncFunctionDef),
        }
        if parent_class:
            node_entry["class"] = parent_class

        self._nodes.append(node_entry)

        # Call edges from this function — sort for determinism
        called_names = _collect_calls(func_node)
        for called in sorted(set(called_names)):  # sorted+dedup for stable output
            self._edges.append(
                {
                    "from": func_id,
                    "to": called,
                    "kind": "call",
                    "static_only": True,
                    "note": "name-only; may not resolve to correct module without runtime context",
                }
            )

    def to_dict(self) -> dict[str, Any]:
        """Serialize the graph to a JSON-compatible dictionary.

        Returns:
            Dictionary with schema_version, generated_at, nodes, and edges.
        """
        sorted_nodes = sorted(self._nodes, key=lambda n: n["id"])
        sorted_edges = sorted(
            self._edges, key=lambda e: (e["from"], e.get("to", ""), e["kind"])
        )
        return {
            "schema_version": SCHEMA_VERSION,
            "generated_at": datetime.now(UTC).isoformat(),
            "generator": "scripts/build_graph.py",
            "static_only": True,
            "scan_roots": [
                str(r.relative_to(REPO_ROOT)).replace("\\", "/") for r in SCAN_ROOTS
            ],
            "node_count": len(sorted_nodes),
            "edge_count": len(sorted_edges),
            "nodes": sorted_nodes,
            "edges": sorted_edges,
        }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _graph_hash(graph: dict[str, Any]) -> str:
    """Compute a stable hash of graph content, excluding the timestamp.

    Args:
        graph: The graph dictionary.

    Returns:
        SHA-256 hex digest of the sorted JSON representation.
    """
    stable = {k: v for k, v in graph.items() if k != "generated_at"}
    canonical = json.dumps(stable, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode()).hexdigest()


def main() -> None:
    """CLI entry point for the graph generator.

    Supports --check mode for CI validation and --out for custom output paths.
    """
    parser = ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail with exit code 1 if the graph would change (CI mode).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=OUTPUT_PATH,
        help=f"Output path for graph.json (default: {OUTPUT_PATH})",
    )
    args = parser.parse_args()

    # Build the graph
    builder = GraphBuilder()
    builder.scan()
    graph = builder.to_dict()

    output_path: Path = args.out
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if args.check:
        # CI mode: compare hash of new graph against existing
        if output_path.exists():
            existing = json.loads(output_path.read_text(encoding="utf-8"))
            if _graph_hash(existing) == _graph_hash(graph):
                print("[OK] graph.json is up to date")
                sys.exit(0)
            else:
                print(
                    "[FAIL] graph.json is stale. Run 'python scripts/build_graph.py' and commit the result.",
                    file=sys.stderr,
                )
                sys.exit(1)
        else:
            print(
                "[FAIL] graph.json does not exist. Run 'python scripts/build_graph.py'.",
                file=sys.stderr,
            )
            sys.exit(1)

    # Write the graph
    graph_json = json.dumps(graph, indent=2, ensure_ascii=False)
    output_path.write_text(graph_json, encoding="utf-8")
    print(
        f"[OK] Graph written to {output_path} "
        f"({graph['node_count']} nodes, {graph['edge_count']} edges)"
    )


if __name__ == "__main__":
    main()
