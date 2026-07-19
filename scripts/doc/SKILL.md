# Coding Skills & Rules — `scripts`

When adding or modifying runnable scripts:

## 1. Path Resolution
All CLI scripts must resolve the project root and add it to `sys.path` to allow imports from `etsy_pipeline` to resolve correctly when run as standalone scripts.
```python
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
```

## 2. Command Formatting
*   Always use `argparse` for CLI commands to ensure arguments are self-documenting.
*   Document `--help` commands clearly.

## 3. Exit Code Integrity
*   Build verification tools (like `build_graph.py --check`) must return `sys.exit(0)` on success and non-zero on failure so they integrate correctly with pre-commit hooks and CI systems.
