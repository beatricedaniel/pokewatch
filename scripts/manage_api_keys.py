#!/usr/bin/env python3
"""
API Key Management Script

Manage API keys for PokeWatch API authentication.
Supports generating, listing, and revoking API keys.
"""

import argparse
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from pokewatch.api.auth import generate_api_key, mask_api_key


def load_api_keys(env_file: Path = None) -> list[str]:
    """Load API keys from .env file."""
    if env_file is None:
        env_file = Path(__file__).parent.parent / ".env"

    if not env_file.exists():
        return []

    api_keys = []
    with open(env_file, "r") as f:
        for line in f:
            line = line.strip()
            if line.startswith("API_KEYS="):
                keys_str = line.split("=", 1)[1].strip('"').strip("'")
                api_keys = [k.strip() for k in keys_str.split(",") if k.strip()]
                break

    return api_keys


def save_api_keys(api_keys: list[str], env_file: Path = None):
    """Save API keys to .env file."""
    if env_file is None:
        env_file = Path(__file__).parent.parent / ".env"

    # Read existing .env content
    lines = []
    api_keys_line_idx = None

    if env_file.exists():
        with open(env_file, "r") as f:
            lines = f.readlines()

        # Find API_KEYS line
        for i, line in enumerate(lines):
            if line.strip().startswith("API_KEYS="):
                api_keys_line_idx = i
                break

    # Format API keys line
    keys_str = ",".join(api_keys)
    new_line = f"API_KEYS={keys_str}\n"

    # Update or append
    if api_keys_line_idx is not None:
        lines[api_keys_line_idx] = new_line
    else:
        # Add at the end with a comment
        if lines and not lines[-1].endswith("\n"):
            lines.append("\n")
        lines.append("# API Keys for authentication\n")
        lines.append(new_line)

    # Write back
    with open(env_file, "w") as f:
        f.writelines(lines)


def cmd_generate(args):
    """Generate a new API key."""
    api_key = generate_api_key(prefix=args.prefix, length=args.length)

    if args.add:
        # Add to .env file
        api_keys = load_api_keys(args.env_file)
        api_keys.append(api_key)
        save_api_keys(api_keys, args.env_file)
        print(f"✓ Generated and added new API key: {api_key}")
        print(f"  Total keys: {len(api_keys)}")
    else:
        # Just generate and print
        print(f"Generated API key: {api_key}")
        print("\nTo add this key to your .env file, run:")
        print(f"  python scripts/manage_api_keys.py add {api_key}")


def cmd_list(args):
    """List all API keys."""
    api_keys = load_api_keys(args.env_file)

    if not api_keys:
        print("No API keys configured.")
        print("\nTo generate a new key, run:")
        print("  python scripts/manage_api_keys.py generate --add")
        return

    print(f"API Keys ({len(api_keys)}):")
    print("-" * 60)

    for i, key in enumerate(api_keys, 1):
        if args.masked:
            display_key = mask_api_key(key)
        else:
            display_key = key

        print(f"{i}. {display_key}")

    if args.masked:
        print("\nUse --show-full to display complete keys")


def cmd_add(args):
    """Add an existing API key."""
    api_keys = load_api_keys(args.env_file)

    if args.key in api_keys:
        print(f"⚠ Key already exists: {mask_api_key(args.key)}")
        return

    api_keys.append(args.key)
    save_api_keys(api_keys, args.env_file)

    print(f"✓ Added API key: {mask_api_key(args.key)}")
    print(f"  Total keys: {len(api_keys)}")


def cmd_revoke(args):
    """Revoke (remove) an API key."""
    api_keys = load_api_keys(args.env_file)

    # Try to find by full key or masked key
    removed = False

    if args.key in api_keys:
        api_keys.remove(args.key)
        removed = True
    else:
        # Try to match by last characters
        for key in api_keys:
            if key.endswith(args.key) or mask_api_key(key).endswith(args.key):
                api_keys.remove(key)
                removed = True
                print(f"✓ Revoked API key: {mask_api_key(key)}")
                break

    if removed:
        save_api_keys(api_keys, args.env_file)
        print(f"  Remaining keys: {len(api_keys)}")
    else:
        print(f"✗ Key not found: {args.key}")
        print("\nAvailable keys:")
        cmd_list(argparse.Namespace(env_file=args.env_file, masked=True))


def cmd_rotate(args):
    """Rotate an API key (revoke old, generate new)."""
    api_keys = load_api_keys(args.env_file)

    # Find old key
    old_key = None
    for key in api_keys:
        if key == args.old_key or key.endswith(args.old_key):
            old_key = key
            break

    if not old_key:
        print(f"✗ Old key not found: {args.old_key}")
        return

    # Generate new key
    new_key = generate_api_key(prefix=args.prefix, length=32)

    # Replace
    api_keys = [new_key if k == old_key else k for k in api_keys]
    save_api_keys(api_keys, args.env_file)

    print(f"✓ Rotated API key")
    print(f"  Old key: {mask_api_key(old_key)} (revoked)")
    print(f"  New key: {new_key}")
    print(f"\nUpdate your clients with the new key!")


def cmd_clear(args):
    """Clear all API keys."""
    if not args.force:
        response = input("Are you sure you want to remove ALL API keys? (yes/no): ")
        if response.lower() != "yes":
            print("Cancelled.")
            return

    save_api_keys([], args.env_file)
    print("✓ All API keys removed")


def main():
    parser = argparse.ArgumentParser(
        description="Manage API keys for PokeWatch API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate and add a new key
  python scripts/manage_api_keys.py generate --add

  # List all keys (masked)
  python scripts/manage_api_keys.py list

  # List all keys (full)
  python scripts/manage_api_keys.py list --show-full

  # Add an existing key
  python scripts/manage_api_keys.py add pk_abc123def456

  # Revoke a key
  python scripts/manage_api_keys.py revoke pk_abc123def456

  # Rotate a key
  python scripts/manage_api_keys.py rotate pk_old_key
        """
    )

    parser.add_argument(
        "--env-file",
        type=Path,
        help="Path to .env file (default: pokewatch/.env)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Generate command
    gen_parser = subparsers.add_parser("generate", aliases=["gen"], help="Generate a new API key")
    gen_parser.add_argument("--prefix", default="pk", help="Key prefix (default: pk)")
    gen_parser.add_argument("--length", type=int, default=32, help="Key length (default: 32)")
    gen_parser.add_argument("--add", action="store_true", help="Add to .env file")
    gen_parser.set_defaults(func=cmd_generate)

    # List command
    list_parser = subparsers.add_parser("list", aliases=["ls"], help="List all API keys")
    list_parser.add_argument("--show-full", dest="masked", action="store_false", help="Show full keys")
    list_parser.set_defaults(func=cmd_list, masked=True)

    # Add command
    add_parser = subparsers.add_parser("add", help="Add an API key")
    add_parser.add_argument("key", help="API key to add")
    add_parser.set_defaults(func=cmd_add)

    # Revoke command
    revoke_parser = subparsers.add_parser("revoke", aliases=["rm"], help="Revoke an API key")
    revoke_parser.add_argument("key", help="API key (full or last characters)")
    revoke_parser.set_defaults(func=cmd_revoke)

    # Rotate command
    rotate_parser = subparsers.add_parser("rotate", help="Rotate an API key")
    rotate_parser.add_argument("old_key", help="Old API key to replace")
    rotate_parser.add_argument("--prefix", default="pk", help="Prefix for new key")
    rotate_parser.set_defaults(func=cmd_rotate)

    # Clear command
    clear_parser = subparsers.add_parser("clear", help="Remove all API keys")
    clear_parser.add_argument("--force", action="store_true", help="Skip confirmation")
    clear_parser.set_defaults(func=cmd_clear)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Run command
    args.func(args)


if __name__ == "__main__":
    main()
