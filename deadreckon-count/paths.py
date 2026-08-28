#!/usr/bin/env python3
"""Where every generated file lives. One definition, imported by everything.

    root/
      README.md                  entry point, GitHub renders it from here
      machines.json              AUTHORED — the fleet roster, you edit this
      accounts.json              AUTHORED — labels for emailless profiles
      human-readable/            every .md the tools generate
      machine-readable/          every .json and .csv the tools generate

    <machine>/
      .machine-id                which computer owns this folder
      human-readable/            REPORT, STATS, BY-COMPANY, BY-ACCOUNT for it
      machine-readable/          totals, sessions, hardware, and the same
                                 reports as data

WHY SPLIT THEM

A directory holding `totals.json` next to `BY-COMPANY.md` reads as one pile of
files with no indication which is the source and which is the rendering. They
are not peers: the JSON is what a program reads and rewrites, the Markdown is
generated from it and is never an input. Putting them in separate folders makes
that impossible to get backwards — anything under machine-readable/ can be
regenerated from a scan, and anything under human-readable/ can be regenerated
from machine-readable/.

The two authored files stay at the root because they are neither: they are
inputs a person maintains, and burying them in machine-readable/ would invite
a script to overwrite them.

MIGRATION

`migrate()` moves an old flat layout into this one, with `git mv` when the file
is tracked so history follows it. It is idempotent — running it on an already
migrated tree does nothing.
"""

import pathlib
import shutil
import subprocess

HUMAN = "human-readable"
MACHINE = "machine-readable"

# Files a person edits. Never moved, never generated.
AUTHORED = {"machines.json", "accounts.json", "README.md", ".gitignore",
            ".gitattributes", ".fleet-reset.json"}

# Old flat name -> which folder it belongs in now.
ROOT_MOVES = {
    "BY-COMPUTER.md": HUMAN, "BY-ACCOUNT.md": HUMAN,
    "BY-COMPANY.md": HUMAN, "STATS.md": HUMAN,
    "ALL-COMPUTERS.json": MACHINE,
}
MACHINE_MOVES = {
    "REPORT.md": HUMAN,
    # The corpus wrote this loose at the machine root while every other
    # generated artifact obeyed the split. It is machine-readable data — the
    # project mapping, the file counts, the redaction totals — so it belongs
    # with the rest of it. Readers go through find(), which checks the new
    # location, the old one, then flat, so a corpus exported before this still
    # reads. The per-machine README.md deliberately stays at the machine root:
    # it is the entry point for that folder, the same role README.md plays at
    # the root of a repository.
    "MANIFEST.json": MACHINE,
    "totals.json": MACHINE, "sessions.json": MACHINE, "hardware.json": MACHINE,
    "by_account.csv": MACHINE, "by_day.csv": MACHINE,
    "by_model.csv": MACHINE, "by_project.csv": MACHINE,
}


def human(base):
    p = pathlib.Path(base) / HUMAN
    p.mkdir(parents=True, exist_ok=True)
    return p


def machine(base):
    p = pathlib.Path(base) / MACHINE
    p.mkdir(parents=True, exist_ok=True)
    return p


def find(base, name):
    """A generated file, wherever it currently is.

    Checks the new location first, then the old flat one. Readers use this so a
    machine that has not re-run yet — or a folder pulled from a computer still
    on the previous layout — is read rather than reported as missing. Absent and
    "moved" must not look the same; that mistake has been made in this repo four
    times already, in four different readers.
    """
    base = pathlib.Path(base)
    for c in (base / MACHINE / name, base / HUMAN / name, base / name):
        if c.is_file():
            return c
    return None


def iter_machine_files(root, name):
    """Yield (machine_folder, path) for every machine that has `name`.

    Call sites used `root.glob("*/totals.json")` and then took `f.parent.name`
    as the machine. After the split that parent is `machine-readable/`, so the
    machine name would silently become the folder name — every report would
    have relabelled itself. Returning both removes the guess.
    """
    for d in machine_folders(root):
        p = find(d, name)
        if p:
            yield d, p


# Directories at a repository or corpus root that are never a computer.
NOT_A_MACHINE = (HUMAN, MACHINE, "archive", "testing-archive", "corpus",
                 "merged", "digests", "dist", "docker", "capture",
                 "submission", "out", "__pycache__")


def corpus_machine_folders(corpus):
    """Every machine folder in a CORPUS — present, empty, or half-exported.

    `machine_folders` asks for totals.json, which a corpus never holds, so the
    corpus side had no definition and each caller invented one:

        corpus_reports  (d / ".claude" / "projects").is_dir()
        count_corpus    paths.find(d, "MANIFEST.json")

    Both are tests of CONTENT being used as tests of EXISTENCE, and both
    therefore answer "absent" for a folder that is sitting right there — the
    first for an export that came out empty or holds only tools/, the second
    for an export interrupted before it wrote its manifest. Neither printed a
    row, so on a five-machine corpus each reported four and called it every.

    This asks whether the directory IS a machine folder, and leaves what is
    inside it to the caller, which is the only way the two can differ visibly.
    """
    corpus = pathlib.Path(corpus)
    out = []
    for d in sorted(p for p in corpus.iterdir() if p.is_dir()):
        if d.name in NOT_A_MACHINE or d.name.startswith("."):
            continue
        if ((d / ".claude").is_dir() or (d / "tools").is_dir()
                or (d / MACHINE).is_dir() or find(d, "MANIFEST.json")):
            out.append(d)
    return out


def machine_folders(root):
    """Every machine folder, old layout or new."""
    root = pathlib.Path(root)
    out = []
    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        if d.name in (HUMAN, MACHINE, "archive", "corpus", "merged",
                      "digests", "dist", "docker", "__pycache__"):
            continue
        if find(d, "totals.json"):
            out.append(d)
    return out


def _move(src, dst, tracked):
    dst.parent.mkdir(parents=True, exist_ok=True)
    rel = str(src)
    if rel in tracked:
        r = subprocess.run(["git", "mv", str(src), str(dst)],
                           cwd=src.parents[len(src.parts) - 2] if False else None,
                           capture_output=True, text=True)
        if r.returncode == 0:
            return "git mv"
    shutil.move(str(src), str(dst))
    return "mv"


def migrate(root, dry=True):
    """Move a flat layout into human-readable/ and machine-readable/."""
    root = pathlib.Path(root)
    tracked = set()
    r = subprocess.run(["git", "-C", str(root), "ls-files"],
                       capture_output=True, text=True)
    if r.returncode == 0:
        tracked = {str(root / line) for line in r.stdout.splitlines()}

    moves = []
    for name, where in ROOT_MOVES.items():
        src = root / name
        if src.is_file():
            moves.append((src, root / where / name))
    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        if d.name in (HUMAN, MACHINE, "archive", "corpus", "merged", "digests",
                      "dist", "docker", "__pycache__", ".git"):
            continue
        for name, where in MACHINE_MOVES.items():
            src = d / name
            if src.is_file():
                moves.append((src, d / where / name))

    for src, dst in moves:
        print(f"  {'would move' if dry else 'moved'}  "
              f"{src.relative_to(root)}  ->  {dst.relative_to(root)}")
        if not dry:
            _move(src, dst, tracked)
    if not moves:
        print("  already migrated — nothing to move")
    return len(moves)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(pathlib.Path(__file__).parent))
    ap.add_argument("--yes", action="store_true")
    a = ap.parse_args()
    n = migrate(a.root, dry=not a.yes)
    if n and not a.yes:
        print("\n  re-run with --yes to move them.")
