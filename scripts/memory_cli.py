"""CLI helper script for developer memory management operations.

Usage:
    python scripts/memory_cli.py health
    python scripts/memory_cli.py capture "We use MongoJobStore with find_one_and_update" --category architecture
    python scripts/memory_cli.py recall "MongoJobStore"
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Add project root to sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from etsy_pipeline.config.settings import get_settings  # noqa: E402
from etsy_pipeline.memory.base import MemoryCategory  # noqa: E402
from etsy_pipeline.memory.service import MemoryService  # noqa: E402


async def _run_cli() -> None:
    parser = argparse.ArgumentParser(description="Developer Memory CLI Utility")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Health command
    subparsers.add_parser("health", help="Check memory gateway health")

    # Capture command
    capture_parser = subparsers.add_parser("capture", help="Capture a new memory item")
    capture_parser.add_argument("content", type=str, help="Memory text content")
    capture_parser.add_argument(
        "--category",
        type=str,
        default="general_knowledge",
        choices=[c.value for c in MemoryCategory],
        help="Memory category classification",
    )
    capture_parser.add_argument(
        "--tags",
        type=str,
        nargs="*",
        default=[],
        help="Search tags for the memory",
    )

    # Recall command
    recall_parser = subparsers.add_parser("recall", help="Recall memory items matching query")
    recall_parser.add_argument("query", type=str, help="Query string")
    recall_parser.add_argument("--limit", type=int, default=5, help="Result count limit")

    args = parser.parse_args()

    # Enable memory explicitly for CLI interactions
    settings = get_settings()
    settings.memory_enabled = True
    service = MemoryService(settings=settings)

    if args.command == "health":
        status = await service.health()
        print("\n--- Memory Gateway Health ---")
        for k, v in status.items():
            print(f"  {k}: {v}")
        print()

    elif args.command == "capture":
        cat = MemoryCategory(args.category)
        success = await service.capture(
            content=args.content,
            category=cat,
            tags=args.tags,
            bypass_filter=True,  # User explicitly requested capture
        )
        if success:
            print(f"Successfully captured memory ({cat.value}): '{args.content}'")
        else:
            print("Failed to capture memory.")

    elif args.command == "recall":
        memories = await service.recall(args.query, limit=args.limit)
        print(f"\n--- Recalled Memories for '{args.query}' ({len(memories)} items) ---")
        if not memories:
            print("  (No matching memories found)")
        else:
            print(MemoryService.format_for_prompt(memories))


def main() -> None:
    """Main entry point."""
    asyncio.run(_run_cli())


if __name__ == "__main__":
    main()
