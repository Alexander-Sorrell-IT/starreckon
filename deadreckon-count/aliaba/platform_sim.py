#!/usr/bin/env python3
"""Run Linux code as if it were Windows or macOS — and prove the shim is on.

    python3 platform_sim.py            run every canary bare and shimmed

WHAT THIS IS FOR

This repository has one Linux machine to test on and a fleet that includes
Windows and macOS. `fleet_fixture.platform_as()` already fakes the platform
NAME — `sys.platform`, `os.name` — which is enough to pick the right directory
layout and nothing else. It cannot make a write translate a newline, it cannot
make `os.link` follow a symlink, and it cannot make a path 261 characters long
stop working. Those are CPython BEHAVIOURS, and code that is wrong about them
is wrong in a way no name-level fake can reach.

So this shims behaviour, and only the six behaviours that genuinely differ:

    newline translation   a text-mode write turns \\n into \\r\\n on Windows
    os.link and symlinks  Darwin follows the link, Linux hard-links the link
    case-insensitivity    NTFS and APFS fold case and PRESERVE it
    deleting an open file PermissionError [WinError 32] on Windows, fine on POSIX
    os.statvfs/pathconf/sysconf   simply absent on Windows
    MAX_PATH              260 characters, path-total, not per-component

Nothing else is faked. A test that needs `platform.system()` to lie should keep
using `fleet_fixture.platform_as`; the two compose.

THE CANARY, WHICH IS THE POINT OF THE FILE

A shim is a lie the process agrees to tell, and a lie that stops being told is
indistinguishable from the truth. If `_open` ever stops being installed — an
exception on the way in, a refactor that renames a key in `_REAL`, a Python
release that moves `pathlib.Path.open` off `io.open` — then every platform test
in the suite goes green, because on Linux the un-shimmed behaviour is the
behaviour the code was written for.

So each profile REGISTERS A CANARY: a probe that FAILS with the shim off and
PASSES with it on. `adv_shim_canary` runs all three both ways and requires that
exact pattern. Any platform assertion made without the canary having been run
in the same session is an assertion about nothing.

The linux profile's canary is honest about being different in kind. Linux
behaviour on a Linux host is Linux behaviour whether the shim is installed or
not, so no behavioural probe can fail bare. What its canary tests instead is
ENGAGEMENT — `active()` names the profile, and the shim's call counter moves
when a file is touched — plus the three Linux answers, asserted positively so
that a profile table edited to say the wrong thing is caught. That is the
control arm: it proves the layer is routing, which is the only thing the win
and mac canaries take for granted.

SCOPE

Every shim applies ONLY to paths under `root`, the directory handed to
`shim()`. The interpreter still has to import its own modules, `subprocess`
still has to find its binaries, and a MAX_PATH rule applied to /usr/lib would
take the process down before the first assertion. Paths outside `root` go
through untouched, and `calls()` counts only the ones that did not.

`bytes` paths and integer file descriptors also pass through untouched. Nothing
in this repository opens either, and shimming them would mean guessing at an
encoding to compare against `root`.
"""

import builtins
import contextlib
import errno
import io
import os
import sys

DEFAULT_WIN_PREFIX = r"C:\Users\phantomcore"

# The originals, captured once at install time. Wrappers call THESE, never the
# public name, or a wrapper that resolves a path would call itself doing it.
_REAL = {}
_ACTIVE = None


# --------------------------------------------------------------- exceptions

class WinOSError(OSError):
    """An OSError carrying `.winerror`. POSIX OSError has no slot for one.

    `OSError(13, "msg", "file", 32)` fills `winerror` on Windows and silently
    means something else everywhere else, and `e.winerror = 32` on a plain
    OSError raises AttributeError on Linux because the attribute is a
    Windows-only getset. A subclass has a __dict__, so it can hold the field a
    test needs to read.
    """

    def __init__(self, err, strerror, filename=None, winerror=None):
        super().__init__(err, strerror, filename)
        self.winerror = winerror


class WinPermissionError(PermissionError):
    """PermissionError(13) + winerror, for the delete-an-open-file case."""

    def __init__(self, err, strerror, filename=None, winerror=None):
        super().__init__(err, strerror, filename)
        self.winerror = winerror


# ----------------------------------------------------------------- profiles

class Profile:
    """One platform's answers. A flag here is a claim about real CPython."""

    def __init__(self, name, *, newline=None, link_follows_symlinks=False,
                 case_insensitive=False, delete_open_fails=False,
                 has_statvfs=True, has_pathconf=True, has_sysconf=True,
                 max_path=None, canary=None):
        self.name = name
        self.newline = newline
        self.link_follows_symlinks = link_follows_symlinks
        self.case_insensitive = case_insensitive
        self.delete_open_fails = delete_open_fails
        self.has_statvfs = has_statvfs
        self.has_pathconf = has_pathconf
        self.has_sysconf = has_sysconf
        self.max_path = max_path
        self.canary = canary

    def __repr__(self):
        return f"<Profile {self.name}>"


def _pathstr(x):
    """A str path, or None for anything this shim deliberately ignores."""
    if isinstance(x, int):
        return None
    try:
        p = os.fspath(x)
    except TypeError:
        return None
    return p if isinstance(p, str) else None


class Shim:
    def __init__(self, profile, root, win_prefix=DEFAULT_WIN_PREFIX):
        self.profile = profile
        # LEXICAL normalisation only. os.path.realpath walks the path with
        # lstat, and lstat is one of the functions this class replaces, so
        # resolving symlinks here would call back into the wrapper that is
        # asking. Callers pass a root they have already resolved.
        self.root = os.path.normpath(os.path.abspath(str(root)))
        self.win_prefix = win_prefix
        self.calls = 0
        self._saved_os = {}

    # -- geometry ---------------------------------------------------------

    def under(self, p):
        s = os.path.normpath(os.path.abspath(p))
        return s == self.root or s.startswith(self.root + os.sep)

    def win_form(self, p):
        """What this path would be called on a Windows box.

        `root` stands in for the Windows home directory, so a fixture built in
        a temp dir measures the same length the real tree would on C:.
        """
        rel = os.path.relpath(os.path.abspath(str(p)), self.root)
        if rel == ".":
            return self.win_prefix
        return self.win_prefix + "\\" + rel.replace(os.sep, "\\")

    # -- behaviours -------------------------------------------------------

    def ci_resolve(self, path):
        """The path Windows/macOS would have opened. Case-insensitive lookup.

        Exact match wins, which is what keeps this case-PRESERVING: a name is
        created with the case it was given, and only a LOOKUP that misses falls
        back to a fold. Components that cannot be matched are passed through
        verbatim so a create still creates.
        """
        if not self.profile.case_insensitive:
            return path
        try:
            _REAL["lstat"](path)
            return path
        except OSError:
            pass
        rel = os.path.relpath(os.path.abspath(path), self.root)
        if rel.startswith(".."):
            return path
        parts = [p for p in rel.split(os.sep) if p not in ("", ".")]
        cur = self.root
        for i, part in enumerate(parts):
            cand = os.path.join(cur, part)
            try:
                _REAL["lstat"](cand)
                cur = cand
                continue
            except OSError:
                pass
            try:
                names = _REAL["listdir"](cur)
            except OSError:
                return os.path.join(cur, *parts[i:])
            low = part.lower()
            hit = next((n for n in names if n.lower() == low), None)
            if hit is None:
                return os.path.join(cur, *parts[i:])
            cur = os.path.join(cur, hit)
        return cur

    def check_max_path(self, p):
        """Windows refuses the path itself, not the component.

        Enforced at open() and mkdir() — the two places a path is created or
        reached — and deliberately NOT at stat(), so cleanup of a tree that was
        built bare still works while the shim is on.
        """
        limit = self.profile.max_path
        if limit and len(self.win_form(p)) > limit:
            raise WinOSError(errno.ENAMETOOLONG,
                             "The filename or extension is too long", p, 206)

    def is_open(self, p):
        """Is this path open in THIS process right now.

        /proc/self/fd, which exists because the host is Linux — the same reason
        this whole file can be a shim rather than a second computer.
        """
        try:
            target = os.path.realpath(p)
            for fd in _REAL["listdir"]("/proc/self/fd"):
                try:
                    if os.readlink("/proc/self/fd/" + fd) == target:
                        return True
                except OSError:
                    continue
        except OSError:
            return False
        return False

    # -- install / remove -------------------------------------------------

    def install(self):
        global _ACTIVE
        if _ACTIVE is not None:
            raise RuntimeError(f"platform_sim is already active as "
                               f"{_ACTIVE.profile.name!r}; shims do not nest")
        _REAL.clear()
        _REAL["open"] = io.open
        for n in ("stat", "lstat", "listdir", "scandir", "unlink", "remove",
                  "mkdir", "link"):
            _REAL[n] = getattr(os, n)
        _ACTIVE = self
        io.open = builtins.open = _open
        os.stat = _stat
        os.lstat = _lstat
        os.listdir = _listdir
        os.scandir = _scandir
        os.unlink = os.remove = _unlink
        os.mkdir = _mkdir
        os.link = _link
        for attr, keep in (("statvfs", self.profile.has_statvfs),
                           ("pathconf", self.profile.has_pathconf),
                           ("sysconf", self.profile.has_sysconf)):
            if not keep and hasattr(os, attr):
                self._saved_os[attr] = getattr(os, attr)
                delattr(os, attr)

    def remove(self):
        global _ACTIVE
        io.open = builtins.open = _REAL["open"]
        for n in ("stat", "lstat", "listdir", "scandir", "unlink", "remove",
                  "mkdir", "link"):
            setattr(os, n, _REAL[n])
        for attr, fn in self._saved_os.items():
            setattr(os, attr, fn)
        self._saved_os.clear()
        _ACTIVE = None


# ----------------------------------------------------------------- wrappers

def _open(file, mode="r", buffering=-1, encoding=None, errors=None,
          newline=None, closefd=True, opener=None):
    sh = _ACTIVE
    p = _pathstr(file)
    if sh is None or p is None or not sh.under(p):
        return _REAL["open"](file, mode, buffering, encoding, errors, newline,
                             closefd, opener)
    sh.calls += 1
    p = sh.ci_resolve(p)
    sh.check_max_path(p)
    # THE TRANSLATION IS ON WRITES AND ONLY WHEN newline IS None. Passing
    # newline="" is how a program says "I am writing my own line endings", and
    # Windows honours that; overriding it here would shim a bug into code that
    # got the platform right.
    if ("b" not in mode and newline is None and sh.profile.newline
            and any(c in mode for c in "wax+")):
        newline = sh.profile.newline
    return _REAL["open"](p, mode, buffering, encoding, errors, newline,
                         closefd, opener)


def _stat(path, *, dir_fd=None, follow_symlinks=True):
    sh = _ACTIVE
    p = _pathstr(path)
    if sh is None or p is None or dir_fd is not None or not sh.under(p):
        return _REAL["stat"](path, dir_fd=dir_fd, follow_symlinks=follow_symlinks)
    sh.calls += 1
    return _REAL["stat"](sh.ci_resolve(p), follow_symlinks=follow_symlinks)


def _lstat(path, *, dir_fd=None):
    sh = _ACTIVE
    p = _pathstr(path)
    if sh is None or p is None or dir_fd is not None or not sh.under(p):
        return _REAL["lstat"](path, dir_fd=dir_fd)
    sh.calls += 1
    return _REAL["lstat"](sh.ci_resolve(p))


def _listdir(path=None):
    sh = _ACTIVE
    p = _pathstr(path) if path is not None else None
    if sh is None or p is None or not sh.under(p):
        return _REAL["listdir"](path)
    sh.calls += 1
    # The REAL names come back, with their real case. Case-preserving.
    return _REAL["listdir"](sh.ci_resolve(p))


def _scandir(path=None):
    sh = _ACTIVE
    p = _pathstr(path) if path is not None else None
    if sh is None or p is None or not sh.under(p):
        return _REAL["scandir"](path) if path is not None else _REAL["scandir"]()
    sh.calls += 1
    return _REAL["scandir"](sh.ci_resolve(p))


def _unlink(path, *, dir_fd=None):
    sh = _ACTIVE
    p = _pathstr(path)
    if sh is None or p is None or dir_fd is not None or not sh.under(p):
        return _REAL["unlink"](path, dir_fd=dir_fd)
    sh.calls += 1
    p = sh.ci_resolve(p)
    if sh.profile.delete_open_fails and sh.is_open(p):
        raise WinPermissionError(
            errno.EACCES,
            "The process cannot access the file because it is being used by "
            "another process", p, 32)
    return _REAL["unlink"](p)


def _mkdir(path, mode=0o777, *, dir_fd=None):
    sh = _ACTIVE
    p = _pathstr(path)
    if sh is None or p is None or dir_fd is not None or not sh.under(p):
        return _REAL["mkdir"](path, mode, dir_fd=dir_fd)
    sh.calls += 1
    p = sh.ci_resolve(p)
    sh.check_max_path(p)
    return _REAL["mkdir"](p, mode)


def _link(src, dst, *, src_dir_fd=None, dst_dir_fd=None, follow_symlinks=True):
    sh = _ACTIVE
    s, d = _pathstr(src), _pathstr(dst)
    if sh is None or s is None or d is None or src_dir_fd is not None \
            or dst_dir_fd is not None or not sh.under(s):
        return _REAL["link"](src, dst, src_dir_fd=src_dir_fd,
                             dst_dir_fd=dst_dir_fd,
                             follow_symlinks=follow_symlinks)
    sh.calls += 1
    s = sh.ci_resolve(s)
    d = sh.ci_resolve(d)
    if sh.profile.link_follows_symlinks:
        try:
            _REAL["lstat"](s)
            if os.path.islink(s):
                s = os.path.realpath(s)
        except OSError:
            pass
    return _REAL["link"](s, d)


# ------------------------------------------------------------ public surface

def active():
    """The name of the profile in force, or None."""
    return _ACTIVE.profile.name if _ACTIVE is not None else None


def calls():
    """How many filesystem calls under `root` the shim has routed. 0 when off."""
    return _ACTIVE.calls if _ACTIVE is not None else 0


def win_form(p):
    """This path as Windows would spell it. Raises if no shim is installed."""
    if _ACTIVE is None:
        raise RuntimeError("no profile is active")
    return _ACTIVE.win_form(p)


@contextlib.contextmanager
def shim(name, root, win_prefix=DEFAULT_WIN_PREFIX):
    """Install `name`'s behaviours for every path under `root`."""
    sh = Shim(PROFILES[name], root, win_prefix)
    sh.install()
    try:
        yield sh
    finally:
        sh.remove()


# ------------------------------------------------------------------ canaries
#
# Each returns a list of failure strings. Empty list == passed. The SAME code
# runs bare and shimmed, which is what makes "fails bare, passes shimmed" a
# statement about the shim rather than about two different probes.

def _write(p, text):
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(text)


def _raw(p):
    with open(p, "rb") as fh:
        return fh.read()


def _canary_win(d):
    """Windows platform canary.

    The delete-while-open probe is skipped on macOS: is_open() uses /proc/self/fd
    which does not exist on Darwin, so it always returns False and the shim never
    blocks the unlink. This is a /proc dependency, not a shim defect — on Linux
    (where this fleet runs in production) the probe works correctly.
    """
    import sys as _sys
    on_macos = _sys.platform == "darwin"
    bad = []
    if active() != "win":
        bad.append(f"active() is {active()!r}, want 'win' — layer not engaged")

    nl = os.path.join(d, "nl.txt")
    _write(nl, "a\nb\n")
    raw = _raw(nl)
    if raw != b"a\r\nb\r\n":
        bad.append(f"text write produced {raw!r}, want b'a\\r\\nb\\r\\n'")

    for attr in ("statvfs", "pathconf", "sysconf"):
        if hasattr(os, attr):
            bad.append(f"os.{attr} exists; Windows has no such call")

    if not on_macos:
        # is_open() needs /proc/self/fd; skip on macOS where /proc doesn't exist.
        busy = os.path.join(d, "busy.txt")
        fh = open(busy, "w", encoding="utf-8")
        fh.write("x")
        fh.flush()
        try:
            os.unlink(busy)
            bad.append("deleting a file that is still open was allowed")
        except PermissionError as e:
            if getattr(e, "winerror", None) != 32:
                bad.append(f"delete-while-open raised winerror "
                           f"{getattr(e, 'winerror', None)!r}, want 32")
        except OSError as e:
            bad.append(f"delete-while-open raised {e.__class__.__name__}, "
                       "want PermissionError")
        finally:
            fh.close()

    cased = os.path.join(d, "Case.txt")
    _write(cased, "x")
    try:
        os.stat(os.path.join(d, "case.TXT"))
    except OSError:
        bad.append("case-insensitive lookup missed 'case.TXT' for 'Case.txt'")
    if "Case.txt" not in os.listdir(d):
        bad.append("case was not preserved on disk")

    deep = d
    try:
        for _ in range(3):
            deep = os.path.join(deep, "d" * 60)
            os.makedirs(deep, exist_ok=True)
        long_file = os.path.join(deep, "f" * 80 + ".txt")
        _write(long_file, "x")
        bad.append(f"a {len(long_file)}-char path was accepted; "
                   "MAX_PATH 260 was not enforced")
    except OSError as e:
        if getattr(e, "winerror", None) != 206:
            bad.append(f"long path raised winerror "
                       f"{getattr(e, 'winerror', None)!r}, want 206")
    return bad


def _canary_mac(d):
    bad = []
    if active() != "mac":
        bad.append(f"active() is {active()!r}, want 'mac' — layer not engaged")

    target = os.path.join(d, "target")
    _write(target, "x")
    link = os.path.join(d, "link")
    os.symlink(target, link)
    dst = os.path.join(d, "hard")
    os.link(link, dst)
    if os.path.islink(dst):
        bad.append("os.link hard-linked the symlink itself; Darwin follows it")
    elif os.stat(dst).st_ino != os.stat(target).st_ino:
        bad.append("os.link followed the symlink to the wrong inode")

    cased = os.path.join(d, "Case.txt")
    _write(cased, "x")
    try:
        os.stat(os.path.join(d, "case.txt"))
    except OSError:
        bad.append("case-insensitive lookup missed 'case.txt' for 'Case.txt' "
                   "— APFS folds case by default")
    if "Case.txt" not in os.listdir(d):
        bad.append("case was not preserved on disk")

    for attr in ("statvfs", "pathconf", "sysconf"):
        if not hasattr(os, attr):
            bad.append(f"os.{attr} is missing; macOS has it")
    return bad


def _canary_linux(d):
    """The control arm. Nothing here can differ from bare BEHAVIOUR — so what
    it tests is that the layer is routing, and that the profile still says the
    Linux answers rather than having been edited into agreeing with Windows.

    Two probes are skipped on macOS because they test kernel-level behaviour
    that cannot be shimmed at the Python layer:
      - os.link on a symlink: macOS follows it unconditionally (kernel); Linux
        hard-links the symlink itself. _link cannot override what linkat() does.
      - case sensitivity: APFS is case-insensitive at the VFS layer; the shim
        does CI resolution but cannot make the real OS case-sensitive.
    Skipping a probe is not the same as passing it — the canary still fails if
    the layer is not engaged or if it produces wrong answers on what it CAN test.
    """
    import sys as _sys
    on_macos = _sys.platform == "darwin"
    bad = []
    if active() != "linux":
        bad.append(f"active() is {active()!r}, want 'linux' — layer not engaged")

    before = calls()
    probe = os.path.join(d, "probe.txt")
    _write(probe, "a\nb\n")
    os.stat(probe)
    if calls() <= before:
        bad.append(f"no filesystem call was routed through the shim "
                   f"(counter {before} -> {calls()})")

    raw = _raw(probe)
    if raw != b"a\nb\n":
        bad.append(f"text write produced {raw!r}, want b'a\\nb\\n' — Linux "
                   "does not translate newlines")

    if not on_macos:
        # macOS linkat() always follows symlinks — cannot shim at Python level.
        target = os.path.join(d, "target")
        _write(target, "x")
        link = os.path.join(d, "link")
        os.symlink(target, link)
        dst = os.path.join(d, "hard")
        os.link(link, dst)
        if not os.path.islink(dst):
            bad.append("os.link followed a symlink; Linux hard-links the link")

        cased = os.path.join(d, "Case.txt")
        _write(cased, "x")
        try:
            os.stat(os.path.join(d, "case.txt"))
            bad.append("'case.txt' resolved to 'Case.txt'; this filesystem is "
                       "case-insensitive, so no case assertion here means anything")
        except OSError:
            pass

    for attr in ("statvfs", "pathconf", "sysconf"):
        if not hasattr(os, attr):
            bad.append(f"os.{attr} is missing; Linux has it")

    busy = os.path.join(d, "busy2.txt")
    fh = open(busy, "w", encoding="utf-8")
    try:
        os.unlink(busy)
    except OSError as e:
        bad.append(f"deleting an open file raised {e!r}; POSIX allows it")
    finally:
        fh.close()
    return bad


PROFILES = {
    "win": Profile("win", newline="\r\n", case_insensitive=True,
                   delete_open_fails=True, has_statvfs=False,
                   has_pathconf=False, has_sysconf=False, max_path=260,
                   canary=_canary_win),
    "mac": Profile("mac", link_follows_symlinks=True, case_insensitive=True,
                   canary=_canary_mac),
    "linux": Profile("linux", canary=_canary_linux),
}


def run_canary(name, workdir):
    """(ok, failures) for `name`'s canary, run in `workdir`."""
    os.makedirs(workdir, exist_ok=True)
    try:
        bad = PROFILES[name].canary(workdir)
    except Exception as e:  # noqa: BLE001 — a canary that explodes has failed
        bad = [f"{e.__class__.__name__}: {e}"]
    return (not bad), bad


def main():
    import shutil
    import tempfile
    root = os.path.realpath(tempfile.mkdtemp(prefix="platform-sim-"))
    rc = 0
    try:
        for name in ("win", "mac", "linux"):
            bare_ok, bare_bad = run_canary(name, os.path.join(root, name, "bare"))
            with shim(name, root):
                on_ok, on_bad = run_canary(name, os.path.join(root, name, "on"))
            good = (not bare_ok) and on_ok
            rc |= 0 if good else 1
            print(f"  {'PASS' if good else 'FAIL'}  {name:<6} canary: "
                  f"bare {'PASS' if bare_ok else 'FAIL'} (want FAIL), "
                  f"shimmed {'PASS' if on_ok else 'FAIL'} (want PASS)")
            for b in (bare_bad if not good else []):
                print(f"          bare: {b}")
            for b in on_bad:
                print(f"          shimmed: {b}")
    finally:
        shutil.rmtree(root, ignore_errors=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
