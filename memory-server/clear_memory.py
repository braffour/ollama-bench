#!/usr/bin/env python3
"""
Memory Clearing Utility for Vector Store

This utility provides functions to clear memory from the vector store
used by the multi-agent system.
"""

import argparse
import sys
import os
from pathlib import Path

# Add parent directory to path for imports
parent_dir = Path(__file__).parent
sys.path.insert(0, str(parent_dir))

from storage.simple_vector_store import SimpleVectorStore
from config.settings import CHROMA_PERSIST_DIR


def clear_vector_store(confirm: bool = True) -> bool:
    """
    Clear the vector store by resetting it to empty state.

    Args:
        confirm: Whether to ask for confirmation before clearing

    Returns:
        True if successful, False otherwise
    """
    try:
        persist_file = os.path.join(CHROMA_PERSIST_DIR, "vector_store.json")

        # Initialize store to check current state
        store = SimpleVectorStore(persist_file=persist_file)
        count = store.count()

        if count == 0:
            print("ℹ️  Vector store is already empty")
            return True

        if confirm:
            print(f"⚠️  About to clear {count} entries from vector store")
            response = input("Are you sure? (type 'yes' to confirm): ")
            if response.lower() != 'yes':
                print("❌ Operation cancelled by user")
                return False

        # Clear the store by resetting all its data
        store.vectors = []
        store.documents = []
        store.metadatas = []
        store.ids = []

        # Save empty state
        store._save_to_file()
        print(f"✅ Cleared vector store: {count} entries removed")
        return True

    except Exception as e:
        print(f"❌ Error clearing vector store: {str(e)}")
        return False


def clear_simple_vector_store(confirm: bool = True) -> bool:
    """
    Clear the simple vector store persistence file.

    Args:
        confirm: Whether to ask for confirmation before clearing

    Returns:
        True if successful, False otherwise
    """
    try:
        persist_file = os.path.join(CHROMA_PERSIST_DIR, "vector_store.json")

        if not os.path.exists(persist_file):
            print(f"ℹ️  Simple vector store file does not exist: {persist_file}")
            return True

        # Get file size for info
        file_size = os.path.getsize(persist_file)
        file_size_kb = file_size / 1024

        if confirm:
            print(f"⚠️  About to delete simple vector store file ({file_size_kb:.1f} KB)")
            response = input("Are you sure? (type 'yes' to confirm): ")
            if response.lower() != 'yes':
                print("❌ Operation cancelled by user")
                return False

        # Delete the file
        os.remove(persist_file)
        print(f"✅ Deleted simple vector store file: {persist_file}")
        return True

    except Exception as e:
        print(f"❌ Error clearing simple vector store: {str(e)}")
        return False


def get_memory_stats() -> dict:
    """
    Get current memory statistics.

    Returns:
        Dict with memory statistics
    """
    stats = {
        "vector_store": {"exists": False, "count": 0}
    }

    try:
        # Check vector store
        persist_file = os.path.join(CHROMA_PERSIST_DIR, "vector_store.json")
        if os.path.exists(persist_file):
            try:
                store = SimpleVectorStore(persist_file=persist_file)
                stats["vector_store"]["exists"] = True
                stats["vector_store"]["count"] = store.count()
            except Exception:
                pass

    except Exception as e:
        print(f"⚠️  Error getting stats: {str(e)}")

    return stats


def show_stats():
    """Display current memory statistics."""
    print("📊 Memory Statistics:")
    print("=" * 50)

    stats = get_memory_stats()

    # Vector store stats
    vector_store = stats["vector_store"]
    if vector_store["exists"]:
        print(f"Vector Store: {vector_store['count']} entries")
    else:
        print("Vector Store: Not found")

    persist_file = os.path.join(CHROMA_PERSIST_DIR, "vector_store.json")
    if os.path.exists(persist_file):
        file_size = os.path.getsize(persist_file)
        file_size_kb = file_size / 1024
        print(f"Vector Store File: {file_size_kb:.1f} KB")
    else:
        print("Vector Store File: Not found")

    print(f"\nTotal Memory Entries: {vector_store['count']}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Clear memory from vector store",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python clear_memory.py --stats                    # Show memory statistics
  python clear_memory.py --clear-store              # Clear vector store entries
  python clear_memory.py --clear-file               # Clear vector store file
  python clear_memory.py --clear-all --yes          # Clear everything without confirmation
  python clear_memory.py --clear-all                # Clear everything with confirmation
        """
    )

    parser.add_argument(
        '--stats',
        action='store_true',
        help='Show memory statistics'
    )

    parser.add_argument(
        '--clear-store',
        action='store_true',
        help='Clear vector store entries'
    )

    parser.add_argument(
        '--clear-file',
        action='store_true',
        help='Clear vector store persistence file'
    )

    parser.add_argument(
        '--clear-all',
        action='store_true',
        help='Clear both vector store and persistence file'
    )

    parser.add_argument(
        '--yes', '-y',
        action='store_true',
        help='Skip confirmation prompts'
    )

    args = parser.parse_args()

    # Show stats if requested or no action specified
    if args.stats or (not args.clear_store and not args.clear_file and not args.clear_all):
        show_stats()
        if not args.stats:
            print("\nUse --help for available options")
        return

    # Handle clear operations
    success_count = 0
    total_operations = 0

    if args.clear_store or args.clear_all:
        total_operations += 1
        if clear_vector_store(confirm=not args.yes):
            success_count += 1

    if args.clear_file or args.clear_all:
        total_operations += 1
        if clear_simple_vector_store(confirm=not args.yes):
            success_count += 1

    print(f"\n📊 Operation Summary: {success_count}/{total_operations} operations successful")

    if success_count == total_operations:
        print("✅ All memory clearing operations completed successfully")
    else:
        print("⚠️  Some operations failed - check output above")
        sys.exit(1)


if __name__ == "__main__":
    main()
