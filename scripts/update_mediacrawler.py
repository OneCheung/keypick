#!/usr/bin/env python3
"""
Update MediaCrawler submodule from remote repository

This script helps update the MediaCrawler submodule while preserving
local customizations.
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime


def run_command(cmd, cwd=None, check=True):
    """Run a shell command and return the result"""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=check
    )
    return result


def get_git_status(cwd):
    """Get git status output"""
    result = run_command(["git", "status", "--porcelain"], cwd=cwd, check=False)
    return result.stdout.strip()


def main():
    project_root = Path(__file__).parent.parent
    mediacrawler_dir = project_root / "MediaCrawler"

    print("=" * 50)
    print("Updating MediaCrawler from remote repository")
    print("=" * 50)
    print()

    # Check if MediaCrawler directory exists
    if not mediacrawler_dir.exists():
        print(f"Error: MediaCrawler directory not found at {mediacrawler_dir}")
        sys.exit(1)

    # Check current status
    print("Current MediaCrawler status:")
    status = get_git_status(mediacrawler_dir)
    if status:
        print(status)
    else:
        print("  (no changes)")
    print()

    # Check if there are local modifications
    has_changes = bool(status)
    stashed = False

    if has_changes:
        print("⚠️  Warning: MediaCrawler has local modifications")
        print()
        response = input("Do you want to stash local changes before updating? (y/n): ")
        if response.lower() in ['y', 'yes']:
            print("Stashing local changes...")
            stash_message = f"Local changes before update {datetime.now().strftime('%Y-%m-%d_%H:%M:%S')}"
            run_command(
                ["git", "stash", "push", "-m", stash_message],
                cwd=mediacrawler_dir
            )
            stashed = True
            print("✅ Changes stashed")
        else:
            print("Keeping local changes. Update may fail if there are conflicts.")
    print()

    # Fetch latest changes
    print("Fetching latest changes from remote...")
    run_command(["git", "fetch", "origin"], cwd=mediacrawler_dir)
    print()

    # Show current and remote commits
    print("Current commit:")
    result = run_command(
        ["git", "log", "--oneline", "-1"],
        cwd=mediacrawler_dir
    )
    print(result.stdout.strip())
    print()

    print("Latest commit on origin/main:")
    result = run_command(
        ["git", "log", "--oneline", "-1", "origin/main"],
        cwd=mediacrawler_dir
    )
    print(result.stdout.strip())
    print()

    # Check if update is needed
    result = run_command(
        ["git", "rev-parse", "HEAD"],
        cwd=mediacrawler_dir
    )
    current_commit = result.stdout.strip()

    result = run_command(
        ["git", "rev-parse", "origin/main"],
        cwd=mediacrawler_dir
    )
    remote_commit = result.stdout.strip()

    if current_commit == remote_commit:
        print("✅ MediaCrawler is already up to date!")
        print()

        # Restore stashed changes if any
        if stashed:
            print("Restoring stashed changes...")
            result = run_command(
                ["git", "stash", "pop"],
                cwd=mediacrawler_dir,
                check=False
            )
            if result.returncode != 0:
                print("⚠️  Warning: There may be conflicts with stashed changes")
                print("You can resolve conflicts manually and then run: git stash drop")
            else:
                print("✅ Stashed changes restored successfully")
        sys.exit(0)

    # Update to latest
    print("Updating MediaCrawler to latest version...")
    run_command(["git", "pull", "origin", "main"], cwd=mediacrawler_dir)
    print("✅ Update completed")
    print()

    # Restore stashed changes if any
    if stashed:
        print("Restoring stashed changes...")
        result = run_command(
            ["git", "stash", "pop"],
            cwd=mediacrawler_dir,
            check=False
        )
        if result.returncode != 0:
            print("⚠️  Warning: There may be conflicts with stashed changes")
            print("You can resolve conflicts manually and then run: git stash drop")
        else:
            print("✅ Stashed changes restored successfully")
        print()

    # Update parent repository's submodule reference
    print("Updating parent repository's submodule reference...")
    run_command(["git", "add", "MediaCrawler"], cwd=project_root)
    print()

    print("=" * 50)
    print("✅ MediaCrawler update completed!")
    print("=" * 50)
    print()

    # Show new commit
    print("New commit:")
    result = run_command(
        ["git", "log", "--oneline", "-1"],
        cwd=mediacrawler_dir
    )
    print(result.stdout.strip())
    print()

    print("Note: Don't forget to commit the submodule update in the parent repository:")
    print("  git commit -m 'Update MediaCrawler submodule'")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nUpdate cancelled by user")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"\n\nError: Command failed with exit code {e.returncode}")
        if e.stderr:
            print(f"Error output: {e.stderr}")
        sys.exit(1)

