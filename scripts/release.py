#!/usr/bin/env python3
"""
Release utility: stamps VERSION and CHANGELOG.md.

Examples:
  python scripts/release.py --version 0.2.0 --notes "Units normalization; provenance export."
  python scripts/release.py --bump patch --notes-file NOTES.txt --tag
"""
from __future__ import annotations
import argparse, os, re, sys, subprocess
from datetime import date

VERSION_FILE = "VERSION"
CHANGELOG = "CHANGELOG.md"

def read_version() -> tuple[int,int,int]:
    if not os.path.exists(VERSION_FILE):
        return (0, 1, 0)  # default initial version
    txt = open(VERSION_FILE, "r", encoding="utf-8").read().strip()
    m = re.match(r"^(\d+)\.(\d+)\.(\d+)$", txt)
    if not m:
        raise SystemExit(f"Invalid {VERSION_FILE} content: '{txt}'")
    return tuple(map(int, m.groups()))  # type: ignore[return-value]

def write_version(major:int, minor:int, patch:int) -> str:
    v = f"{major}.{minor}.{patch}"
    with open(VERSION_FILE, "w", encoding="utf-8") as f:
        f.write(v + "\n")
    return v

def bump(major:int, minor:int, patch:int, which:str) -> tuple[int,int,int]:
    if which == "major":
        return (major+1, 0, 0)
    if which == "minor":
        return (major, minor+1, 0)
    if which == "patch":
        return (major, minor, patch+1)
    raise ValueError(which)

def prepend_changelog(version:str, notes:str) -> None:
    today = date.today().isoformat()
    entry = f"## v{version} — {today}\n\n"
    lines = [ln.strip() for ln in notes.splitlines() if ln.strip()]
    if lines:
        for ln in lines:
            if ln.startswith("- "):
                entry += f"{ln}\n"
            else:
                entry += f"- {ln}\n"
    else:
        entry += "- (no notes provided)\n"
    entry += "\n"

    prev = ""
    if os.path.exists(CHANGELOG):
        prev = open(CHANGELOG, "r", encoding="utf-8").read()
    with open(CHANGELOG, "w", encoding="utf-8") as f:
        f.write(entry + prev)

def git_available() -> bool:
    try:
        subprocess.check_output(["git", "--version"], stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False

def git_commit_and_tag(version:str) -> None:
    try:
        subprocess.check_call(["git", "add", VERSION_FILE, CHANGELOG])
        subprocess.check_call(["git", "commit", "-m", f"Release v{version}"])
        subprocess.check_call(["git", "tag", "-a", f"v{version}", "-m", f"Release v{version}"])
        print(f"Created tag v{version}")
    except Exception as e:
        print(f"[WARN] Git commit/tag failed: {e}")

def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--version", help="Explicit semantic version X.Y.Z")
    g.add_argument("--bump", choices=["major","minor","patch"], help="Bump from current VERSION")
    ap.add_argument("--notes", help="Release notes string")
    ap.add_argument("--notes-file", help="Path to a file with notes")
    ap.add_argument("--tag", action="store_true", help="Create a git commit and annotated tag")
    args = ap.parse_args()

    M,m,p = read_version()
    if args.version:
        mobj = re.match(r"^(\d+)\.(\d+)\.(\d+)$", args.version)
        if not mobj:
            raise SystemExit("Provide --version as X.Y.Z")
        M,m,p = map(int, mobj.groups())
    elif args.bump:
        M,m,p = bump(M,m,p,args.bump)

    if args.notes_file:
        with open(args.notes_file, "r", encoding="utf-8") as fh:
            notes = fh.read()
    else:
        notes = args.notes or ""

    version = write_version(M,m,p)
    prepend_changelog(version, notes)
    print(f"Wrote {VERSION_FILE} = {version}")
    print(f"Updated {CHANGELOG}")

    if args.tag:
        if git_available():
            git_commit_and_tag(version)
        else:
            print("[WARN] git is not available; skipping commit/tag.")

if __name__ == "__main__":
    main()
