#!/usr/bin/env python3
"""
Migration script for ORG-001 Phase 4: Extract System Prefixes as Tags

This script analyzes existing agents and automatically adds tags based on their
naming prefixes. For example, an agent named "research-team-analyst" will get
the tag "research-team" added.

Usage:
    python scripts/management/migrate_prefixes_to_tags.py [--dry-run]

Options:
    --dry-run    Show what would be done without making changes
"""

import sys
import os
import sqlite3
import argparse
from datetime import datetime
from collections import defaultdict

# Add the backend to the path for database access
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src/backend'))


def get_db_path():
    """Get the database path from environment or default location."""
    # Check environment variable first
    db_path = os.environ.get('TRINITY_DB_PATH')
    if db_path:
        return db_path

    # Default local development path
    home = os.path.expanduser('~')
    return os.path.join(home, 'trinity-data', 'trinity.db')


def extract_prefix(agent_name: str) -> str | None:
    """
    Extract the system prefix from an agent name.

    The prefix is everything before the last '-'.
    Example: "research-team-analyst" -> "research-team"

    Returns None if no prefix can be extracted (no hyphens).
    """
    if '-' not in agent_name:
        return None

    parts = agent_name.split('-')
    if len(parts) < 2:
        return None

    # Join all parts except the last one
    prefix = '-'.join(parts[:-1])
    return prefix if prefix else None


def get_all_agents(conn) -> list[dict]:
    """Get all agents from the database."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name, template, created_at
        FROM agents
        ORDER BY name
    """)

    return [
        {'name': row[0], 'template': row[1], 'created_at': row[2]}
        for row in cursor.fetchall()
    ]


def get_agent_tags(conn, agent_name: str) -> list[str]:
    """Get existing tags for an agent."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT tag FROM agent_tags WHERE agent_name = ? ORDER BY tag",
        (agent_name,)
    )
    return [row[0] for row in cursor.fetchall()]


def add_tag(conn, agent_name: str, tag: str, dry_run: bool = False) -> bool:
    """
    Add a tag to an agent if it doesn't already exist.

    Returns True if tag was added (or would be added in dry-run mode).
    """
    normalized_tag = tag.lower().strip()

    # Check if tag already exists
    existing_tags = get_agent_tags(conn, agent_name)
    if normalized_tag in existing_tags:
        return False

    if not dry_run:
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat() + "Z"
        cursor.execute(
            "INSERT OR IGNORE INTO agent_tags (agent_name, tag, created_at) VALUES (?, ?, ?)",
            (agent_name, normalized_tag, now)
        )
        conn.commit()

    return True


def migrate_prefixes_to_tags(dry_run: bool = False):
    """
    Main migration function.

    Extracts system prefixes from agent names and adds them as tags.
    """
    db_path = get_db_path()

    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        print("Set TRINITY_DB_PATH environment variable or ensure Trinity is running.")
        sys.exit(1)

    print(f"Database: {db_path}")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print("-" * 60)

    conn = sqlite3.connect(db_path)

    try:
        agents = get_all_agents(conn)

        if not agents:
            print("No agents found in database.")
            return

        print(f"Found {len(agents)} agents")
        print()

        # Group agents by their extracted prefixes
        prefix_groups = defaultdict(list)
        no_prefix_agents = []

        for agent in agents:
            prefix = extract_prefix(agent['name'])
            if prefix:
                prefix_groups[prefix].append(agent['name'])
            else:
                no_prefix_agents.append(agent['name'])

        # Display prefix analysis
        print("System Prefix Analysis:")
        print("-" * 40)

        for prefix in sorted(prefix_groups.keys()):
            agent_names = prefix_groups[prefix]
            print(f"  {prefix}: {len(agent_names)} agent(s)")
            for name in agent_names:
                print(f"    - {name}")

        if no_prefix_agents:
            print(f"\n  (no prefix): {len(no_prefix_agents)} agent(s)")
            for name in no_prefix_agents:
                print(f"    - {name}")

        print()
        print("-" * 60)

        # Apply tags
        tags_added = 0
        tags_skipped = 0

        print("\nApplying Tags:")
        for agent in agents:
            prefix = extract_prefix(agent['name'])
            if not prefix:
                continue

            existing_tags = get_agent_tags(conn, agent['name'])
            normalized_prefix = prefix.lower()

            if normalized_prefix in existing_tags:
                print(f"  {agent['name']}: tag '{normalized_prefix}' already exists (skipped)")
                tags_skipped += 1
            else:
                if add_tag(conn, agent['name'], prefix, dry_run):
                    action = "would add" if dry_run else "added"
                    print(f"  {agent['name']}: {action} tag '{normalized_prefix}'")
                    tags_added += 1

        print()
        print("-" * 60)
        print(f"\nSummary:")
        print(f"  Tags {'to add' if dry_run else 'added'}: {tags_added}")
        print(f"  Tags skipped (already exist): {tags_skipped}")
        print(f"  Agents without prefix: {len(no_prefix_agents)}")

        if dry_run and tags_added > 0:
            print("\nRun without --dry-run to apply these changes.")

    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(
        description='Migrate agent prefixes to tags (ORG-001 Phase 4)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without making changes'
    )

    args = parser.parse_args()

    print("=" * 60)
    print("ORG-001 Phase 4: Migrate System Prefixes to Tags")
    print("=" * 60)
    print()

    migrate_prefixes_to_tags(dry_run=args.dry_run)


if __name__ == '__main__':
    main()
