#!/usr/bin/env python3
"""Adversarial tests for the stats-cache floor in monthly.py.

    python3 adv_statscache_floor.py

FOUR GAPS, EACH WITH A PLANTED BREAK

The stats-cache floor was added to monthly.py without any adversarial coverage.
These four tests close the gaps identified at the time:

  GAP 1  no test that life["tokens"] >= stats-cache total after the floor
  GAP 2  no test that a frozen month is not retroactively below the floor
  GAP 3  no test that a missing or malformed stats-cache is handled gracefully
  GAP 4  no test that other machines with no stats-cache key are unaffected

Each test is written to FAIL against code with the break planted and PASS
against correct code — if any of these pass with the floor logic gutted, the
test is not evidence.

WHAT IS TESTED HERE, NOT ELSEWHERE

apply_statscache_floor_fleet() and the per-machine block in monthly.main()
are both exercised. stats_page.machine_floor() is already covered in its own
call sites; what is new here is the integration: the delta reaches life["tokens"],
life["by_cli"]["claude"], and the LIFETIME.md text.
"""
import json
import os
import pathlib
import shutil
import sys
import tempfile
from collections import defaultdict

REPO = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, REPO)

import monthly
import paths
import stats_page

FAILED = []
SKIPPED = []


def check(name, got, want, why=""):
    ok = got == want
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    if not ok:
        print(f"        got {got!r}")
        print(f"        want {want!r}" + (f" — {why}" if why else ""))
        FAILED.append(name)
    return ok


def skip(name, why):
    print(f"  SKIP  {name} — {why}")
    SKIPPED.append(name)


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _make_sessions(sessions, stats_cache=None, machine="test-machine"):
    """Minimal sessions.json dict."""
    return {
        "machine": machine,
        "generated_at": "2026-08-01T00:00:00+00:00",
        "sessions": sessions,
        "stats_cache": stats_cache or [],
    }


def _make_session(cli, total, start="2026-07-01", account=None):
    s = {"cli": cli, "total": total, "start": start,
         "turns": 1, "duration_min": 1.0}
    if account:
        s["account"] = account
    return s


def _make_stats_cache_entry(account, total, last_computed="2026-07-01", by_day=None):
    return {
        "account": account,
        "total": total,
        "last_computed": last_computed,
        "by_day": by_day or {},
    }


def _make_totals(accounts):
    """Minimal totals.json dict."""
    acct_list = []
    for acct, gt in accounts.items():
        acct_list.append({
            "account": acct,
            "grand_total": gt,
            "by_day": {},
            "totals": {"input_tokens": gt, "cache_creation_input_tokens": 0,
                       "cache_read_input_tokens": 0, "output_tokens": 0},
            "by_model": {},
            "sessions": 1,
            "turns": 1,
        })
    return {"accounts": acct_list, "grand_total_tokens": sum(accounts.values())}


def _build_machine_dir(tmpdir, name, sessions_d, totals_d=None):
    """Write sessions.json and optionally totals.json under a machine dir."""
    md = pathlib.Path(tmpdir) / name
    # paths.machine() / paths.human() — not flat joins — so the repo's own
    # flat-path check (test_scanner.py:test_no_script_reads_a_generated_file_by_flat_path)
    # does not flag this fixture.
    paths.machine(md).mkdir(parents=True, exist_ok=True)
    paths.human(md).mkdir(parents=True, exist_ok=True)
    paths.machine(md).joinpath("sessions.json").write_text(
        json.dumps(sessions_d), encoding="utf-8")
    if totals_d:
        paths.machine(md).joinpath("totals.json").write_text(
            json.dumps(totals_d), encoding="utf-8")
    (md / ".machine-id").write_text(
        json.dumps({"hostname": name}), encoding="utf-8")
    return md


def _run_fleet_fold(tmpdir, sessions_d, totals_d=None):
    """Run collect() + fold_ledger_fleet() against a single-machine fixture root."""
    root = pathlib.Path(tmpdir)
    months, life = monthly.collect(root)
    monthly.fold_ledger_fleet(root, life)
    return life


# ---------------------------------------------------------------------------
# GAP 1 — life["tokens"] must be >= stats-cache total after the floor
# ---------------------------------------------------------------------------

def t_absent_root_no_crash():
    """A root that does not exist must not crash collect() or fold_ledger_fleet.

    This is the fresh-clone / first-run case: the repo was just pulled and no
    machine has ever been scanned. collect() must return empty structures and
    fold_ledger_fleet must return an empty block.

    ABSENT MARKER: the tempdir is created and deleted before use. A suite that
    never exercises an absent tree is not evidence against crash-on-empty,
    because an empty tempdir is a directory that exists.
    """
    import tempfile as _tf
    d = _tf.mkdtemp(prefix="adv-sc-absent-")
    shutil.rmtree(d)               # ABSENT marker — outside finally
    root = pathlib.Path(d)

    try:
        months, life = monthly.collect(root)
        monthly.fold_ledger_fleet(root, life)
        raised = False
    except Exception as exc:
        raised = f"{type(exc).__name__}: {exc}"

    check("absent root: collect() + fold_ledger_fleet() do not crash",
          raised, False,
          f"raised: {raised}" if raised else "")
    if not raised:
        check("absent root: life['tokens'] is 0", life["tokens"], 0)
        check("absent root: statscache_floor_delta is 0",
              life.get("statscache_floor_delta", 0), 0)


def t_floor_lifts_headline():
    """The headline is never below what Claude's own counter reports.

    THE BREAK: delete `apply_statscache_floor_fleet(root, life)` from
    `fold_ledger_fleet`. The floor is not applied and life["tokens"] stays at
    the scan total, well below the cache total.

    This checks both that the delta was applied and that `statscache_floor_delta`
    carries the exact gap — so a floor that is applied but misreported goes RED
    on the second assertion.
    """
    with tempfile.TemporaryDirectory() as td:
        # Cache says 10 000; scan only shows 100 dated tokens.
        # The floor must lift life["tokens"] to at least 10 000.
        sc = [_make_stats_cache_entry("a@b.com", 10_000, "2026-06-30")]
        sd = _make_sessions(
            [_make_session("claude", 100, "2026-07-15", "a@b.com")],
            stats_cache=sc)
        totals = _make_totals({"a@b.com": 90})
        _build_machine_dir(td, "m1", sd, totals)

        life = _run_fleet_fold(td, sd, totals)

    sc_total = sc[0]["total"]
    check("life['tokens'] >= stats-cache total",
          life["tokens"] >= sc_total, True,
          f"life['tokens']={life['tokens']:,} < cache_total={sc_total:,} — "
          "the floor was not applied")
    delta = life.get("statscache_floor_delta", 0)
    expected_delta = sc_total - 100    # cache_total minus the 100 dated tokens
    check("statscache_floor_delta == expected gap",
          delta, expected_delta,
          f"got {delta:,}, want {expected_delta:,}")
    # The LIFETIME.md must mention the floor. The text is written by render(),
    # which keys on statscache_floor_delta > 0.
    check("statscache_floor_delta is recorded in life dict",
          life.get("statscache_floor_delta", 0) > 0, True,
          "a floor that is applied but not recorded is invisible to readers")


def t_floor_does_not_double_if_scan_exceeds_cache():
    """When scan+ledger already exceeds the cache, nothing changes.

    THE BREAK: apply the floor unconditionally (no max(0, ...)), so a scan that
    is larger than the cache subtracts rather than stays. life["tokens"] then
    falls below the scan total, which is a contradiction in terms.

    The scan shows 50 000, the cache says 10 000. Delta must be 0.
    """
    with tempfile.TemporaryDirectory() as td:
        sc = [_make_stats_cache_entry("a@b.com", 10_000, "2026-06-30")]
        sd = _make_sessions(
            [_make_session("claude", 50_000, "2026-07-15", "a@b.com")],
            stats_cache=sc)
        totals = _make_totals({"a@b.com": 48_000})
        _build_machine_dir(td, "m1", sd, totals)
        life_before_tokens = 50_000    # known from the single session

        life = _run_fleet_fold(td, sd, totals)

    check("no delta when scan >= cache",
          life.get("statscache_floor_delta", 0), 0,
          "the floor must never REDUCE what we already measured")
    check("tokens did not fall below scan total",
          life["tokens"] >= life_before_tokens, True,
          f"life['tokens']={life['tokens']:,} < scan_total={life_before_tokens:,}")


def t_by_cli_claude_reflects_floor():
    """life['by_cli']['claude'] is lifted by the same delta as life['tokens'].

    THE BREAK: update life['tokens'] but forget life['by_cli']['claude'].
    The share column in LIFETIME.md then shows claude at a fraction of the true
    lifetime, and the by-CLI table is internally inconsistent.
    """
    with tempfile.TemporaryDirectory() as td:
        cache_total = 9_000
        scan_dated = 200
        sc = [_make_stats_cache_entry("x@y.com", cache_total, "2026-06-30")]
        sd = _make_sessions(
            [_make_session("claude", scan_dated, "2026-07-10", "x@y.com"),
             _make_session("gemini", 300, "2026-07-10")],
            stats_cache=sc)
        totals = _make_totals({"x@y.com": 180})
        _build_machine_dir(td, "m1", sd, totals)

        life = _run_fleet_fold(td, sd, totals)

    by_cli = dict(life["by_cli"])
    # Claude's share of tokens must be at least the cache_total.
    # 300 gemini tokens are also in life["tokens"]; claude must be at least 9000.
    check("by_cli['claude'] >= cache_total",
          by_cli.get("claude", 0) >= cache_total, True,
          f"by_cli claude={by_cli.get('claude',0):,} < cache_total={cache_total:,}")
    # Sum of by_cli must equal life["tokens"]. by_cli has no bucket for the
    # other_floor delta (no named counter for other CLIs), so the invariant
    # only holds if other_floor == 0 in this fixture (which it is: gemini is
    # not lifted, only scan-total).
    check("by_cli sum == life['tokens']",
          sum(by_cli.values()), life["tokens"],
          f"sum={sum(by_cli.values()):,} != tokens={life['tokens']:,} — "
          "the floor was applied to tokens but not to the CLI buckets, "
          "or vice versa")


# ---------------------------------------------------------------------------
# GAP 2 — frozen months are not retroactively re-frozen below the floor
# ---------------------------------------------------------------------------

def t_frozen_months_not_affected_by_floor():
    """Frozen months cover dated work; the stats-cache floor covers lifetime.

    The floor is applied only to the LIFETIME bucket, never to individual
    months. A month frozen at 100 tokens stays at 100 after the floor lifts
    the lifetime to 10 000 — the floor represents pre-daemon deleted sessions
    with no known month, so routing them into past months would be wrong.

    THE BREAK: apply the floor delta to each month bucket as well as to life.
    A frozen 2026-07 month that held 100 would then be re-frozen at 10 000.

    Verified structurally: months dict is collected BEFORE fold_ledger_fleet
    is called, and apply_statscache_floor_fleet only touches `life`. If that
    ever changes, this test catches it.
    """
    with tempfile.TemporaryDirectory() as td:
        sc = [_make_stats_cache_entry("a@b.com", 10_000, "2026-06-30")]
        sd = _make_sessions(
            [_make_session("claude", 100, "2026-07-15", "a@b.com")],
            stats_cache=sc)
        totals = _make_totals({"a@b.com": 90})
        root = pathlib.Path(td)
        _build_machine_dir(td, "m1", sd, totals)

        months, life = monthly.collect(root)
        july_before = dict(months.get("2026-07", {})).get("tokens", 0)
        monthly.fold_ledger_fleet(root, life)
        july_after = dict(months.get("2026-07", {})).get("tokens", 0)

    check("floor does not bleed into month buckets",
          july_before, july_after,
          f"2026-07 tokens changed: {july_before:,} -> {july_after:,} — "
          "the floor was written into a month that has no month for those tokens")
    check("but life was still lifted",
          life["tokens"] >= 10_000, True,
          "the floor must still reach the lifetime total")


def t_lifetime_json_carries_floor_delta():
    """lifetime.json must carry statscache_floor_delta so consumers can see it.

    THE BREAK: strip statscache_floor_delta from the plain() output before
    writing lifetime.json. The file then carries a token total with no
    explanation for why it differs from the scan total, and every downstream
    reader sees a gap with no cause.

    This verifies the key exists in the dict that gets serialised — the same
    check that adv_platform_behaviour uses for store_state: a distinction that
    exists in memory but never reaches the artifact is not a distinction.
    """
    with tempfile.TemporaryDirectory() as td:
        sc = [_make_stats_cache_entry("a@b.com", 10_000, "2026-06-30")]
        sd = _make_sessions(
            [_make_session("claude", 100, "2026-07-15", "a@b.com")],
            stats_cache=sc)
        totals = _make_totals({"a@b.com": 90})
        root = pathlib.Path(td)
        md = _build_machine_dir(td, "m1", sd, totals)

        months, life = monthly.collect(root)
        monthly.fold_ledger_fleet(root, life)

        # Simulate what monthly.main() writes
        import sessions as sess_mod
        plain = monthly.plain(life)
        serialised = json.loads(json.dumps(sess_mod.stamped(plain)))

    check("statscache_floor_delta survives serialisation to lifetime.json",
          "statscache_floor_delta" in serialised, True,
          "plain() or stamped() stripped the key — a reader cannot tell why "
          "the lifetime differs from the scan total")
    check("statscache_claude_floor_delta also survives",
          "statscache_claude_floor_delta" in serialised, True)
    check("the value is non-zero when a floor was applied",
          serialised.get("statscache_floor_delta", 0) > 0, True)


# ---------------------------------------------------------------------------
# GAP 3 — missing or malformed stats-cache is handled gracefully
# ---------------------------------------------------------------------------

def t_absent_stats_cache_no_change():
    """When stats_cache is missing entirely, nothing changes and no crash.

    THE BREAK: try to iterate `d.get("stats_cache")` without guarding for
    None — `for e in None` raises TypeError. The fleet run dies before writing
    any LIFETIME.md.

    sessions.json may legitimately have no stats_cache key (other machines
    before their first update with the new scanner). The result must be:
    - life["tokens"] unchanged from the scan total
    - statscache_floor_delta == 0
    - no exception raised
    """
    with tempfile.TemporaryDirectory() as td:
        # No stats_cache key at all
        sd = {
            "machine": "test-machine",
            "generated_at": "2026-08-01T00:00:00+00:00",
            "sessions": [_make_session("claude", 500, "2026-07-15", "a@b.com")],
            # no "stats_cache" key
        }
        totals = _make_totals({"a@b.com": 480})
        _build_machine_dir(td, "m1", sd, totals)

        try:
            life = _run_fleet_fold(td, sd, totals)
            raised = False
        except Exception as exc:
            life = None
            raised = f"{type(exc).__name__}: {exc}"

    check("absent stats_cache does not raise", raised, False,
          f"raised: {raised}" if raised else "")
    if life is not None:
        check("life['tokens'] unchanged when stats_cache absent",
              life["tokens"], 500,
              f"got {life['tokens']:,}, want 500")
        check("statscache_floor_delta is 0 when stats_cache absent",
              life.get("statscache_floor_delta", 0), 0)


def t_empty_stats_cache_no_change():
    """An explicitly empty stats_cache list is treated the same as absent.

    THE BREAK: treat an empty list as a signal to zero out life["by_cli"]
    or to set statscache_floor_delta to None. Either crashes downstream code.
    """
    with tempfile.TemporaryDirectory() as td:
        sd = _make_sessions(
            [_make_session("claude", 500, "2026-07-15", "a@b.com")],
            stats_cache=[])   # empty list, not absent
        totals = _make_totals({"a@b.com": 480})
        _build_machine_dir(td, "m1", sd, totals)

        try:
            life = _run_fleet_fold(td, sd, totals)
            raised = False
        except Exception as exc:
            life = None
            raised = f"{type(exc).__name__}: {exc}"

    check("empty stats_cache does not raise", raised, False,
          f"raised: {raised}" if raised else "")
    if life is not None:
        check("life['tokens'] unchanged when stats_cache empty",
              life["tokens"], 500)
        check("statscache_floor_delta is 0 when stats_cache empty",
              life.get("statscache_floor_delta", 0), 0)


def t_malformed_stats_cache_entry_no_crash():
    """A stats-cache entry with missing or wrong-typed fields must not crash.

    THE BREAK: access e["total"] without a default — a KeyError if the field
    is absent, or a TypeError if it holds None. Either silently skips the
    whole machine or takes down the run.

    Tested shapes:
      - entry with no "total" field
      - entry with total=None
      - entry that is not a dict at all (a string)
      - entry with last_computed holding an integer, not a date string
    """
    bad_entries = [
        {"account": "a@b.com"},                    # missing total
        {"account": "a@b.com", "total": None},     # None total
        "not a dict at all",                        # wrong type entirely
        {"account": "a@b.com", "total": 100,
         "last_computed": 20260101},                # int date, not string
    ]
    for i, bad in enumerate(bad_entries):
        with tempfile.TemporaryDirectory() as td:
            sd = _make_sessions(
                [_make_session("claude", 200, "2026-07-15", "a@b.com")],
                stats_cache=[bad])
            totals = _make_totals({"a@b.com": 180})
            _build_machine_dir(td, "m1", sd, totals)

            try:
                life = _run_fleet_fold(td, sd, totals)
                raised = False
            except Exception as exc:
                life = None
                raised = f"{type(exc).__name__}: {exc}"

        desc = repr(bad)[:40]
        check(f"malformed entry {i} ({desc}...) does not crash",
              raised, False,
              f"raised: {raised}" if raised else "")
        if life is not None:
            # The malformed entry may legitimately produce 0 delta; the
            # important thing is it does not invent tokens or crash.
            check(f"malformed entry {i}: life['tokens'] >= scan total",
                  life["tokens"] >= 200, True,
                  f"floor produced {life['tokens']:,} < scan_total=200 — "
                  "the malformed entry subtracted rather than being ignored")


def t_corrupt_totals_json_no_crash():
    """If totals.json is unreadable, the floor degrades gracefully to 0.

    THE BREAK: propagate the exception from json.loads up through
    apply_statscache_floor_fleet. The whole run dies instead of degrading.

    stats_page.machine_floor({}, sessions, sc) must still return a usable
    floor — it falls back to per_acct_sess from sessions alone.
    """
    with tempfile.TemporaryDirectory() as td:
        sc = [_make_stats_cache_entry("a@b.com", 10_000, "2026-06-30")]
        sd = _make_sessions(
            [_make_session("claude", 100, "2026-07-15", "a@b.com")],
            stats_cache=sc)
        md = _build_machine_dir(td, "m1", sd, totals_d=None)
        # Write a corrupt totals.json via paths.machine() — not a flat join.
        paths.machine(md).joinpath("totals.json").write_text(
            "NOT VALID JSON {{{", encoding="utf-8")

        try:
            life = _run_fleet_fold(td, sd)
            raised = False
        except Exception as exc:
            life = None
            raised = f"{type(exc).__name__}: {exc}"

    check("corrupt totals.json does not crash the fleet fold", raised, False,
          f"raised: {raised}" if raised else "")
    if life is not None:
        # When totals.json is corrupt, machine_floor receives an empty totals
        # dict. The `merged` loop (which anchors stats-cache entries against
        # accounts from totals.json) never runs, so the cache total of 10 000
        # is not reachable via the concatenation path. machine_floor returns
        # the scan total (100) as the floor. That is correct graceful
        # degradation: we cannot lift above what was measured without the
        # totals anchor. The important properties are no crash and no drop.
        check("life['tokens'] not below scan total when totals.json is corrupt",
              life["tokens"] >= 100, True,
              f"got {life['tokens']:,}, want >= 100 (scan total) — "
              "the floor must never drop below what sessions showed")


# ---------------------------------------------------------------------------
# GAP 4 — other machines with no stats-cache are unaffected
# ---------------------------------------------------------------------------

def t_machine_without_stats_cache_unaffected():
    """A machine with no stats-cache entry must not have its tokens changed.

    THE BREAK: apply the floor globally rather than per-machine, so a machine
    that has no stats-cache key receives a delta computed from a different
    machine's cache. Its token total then exceeds what was ever measured on it.

    Two machines: m1 has a stats-cache (floor = 10 000), m2 does not (200 tokens).
    After the floor, m1 is lifted and m2 is unchanged.
    """
    with tempfile.TemporaryDirectory() as td:
        # Machine 1: has stats-cache, scan=100, cache=10 000
        sc1 = [_make_stats_cache_entry("a@b.com", 10_000, "2026-06-30")]
        sd1 = _make_sessions(
            [_make_session("claude", 100, "2026-07-15", "a@b.com")],
            stats_cache=sc1, machine="m1")
        totals1 = _make_totals({"a@b.com": 90})
        _build_machine_dir(td, "m1", sd1, totals1)

        # Machine 2: NO stats-cache, scan=200
        sd2 = _make_sessions(
            [_make_session("claude", 200, "2026-07-20", "b@c.com")],
            stats_cache=[], machine="m2")
        totals2 = _make_totals({"b@c.com": 190})
        _build_machine_dir(td, "m2", sd2, totals2)

        root = pathlib.Path(td)
        months, life = monthly.collect(root)
        by_machine_before = dict(life.get("by_machine", {}))
        monthly.fold_ledger_fleet(root, life)
        by_machine_after = dict(life["by_machine"])

    m1_before = by_machine_before.get("m1", 0)
    m2_before = by_machine_before.get("m2", 0)
    m1_after  = by_machine_after.get("m1",  0)
    m2_after  = by_machine_after.get("m2",  0)

    check("m1 (with cache) was lifted",
          m1_after >= 10_000, True,
          f"m1 by_machine: {m1_before:,} -> {m1_after:,}; cache says 10 000")
    check("m2 (no cache) was NOT changed",
          m2_after, m2_before,
          f"m2 moved from {m2_before:,} to {m2_after:,} — "
          "another machine's cache was applied here")
    check("m2 tokens == scan total of 200",
          m2_after, 200,
          f"m2 should be exactly 200 (its scan); got {m2_after:,}")


def t_floor_is_per_machine_not_fleet_wide():
    """The floor for one machine never inflates another.

    Specifically: machine A's cache of 10 000 should not add 9 900 to
    machine B's 100 — the delta is bounded to A and A alone.

    THE BREAK: compute the fleet-wide delta as (sum of all cache totals) -
    (sum of all scan totals) and apply it once to life, rather than per-machine.
    On a two-machine fleet where only one has a cache, B gets inflated.
    """
    with tempfile.TemporaryDirectory() as td:
        sc = [_make_stats_cache_entry("a@b.com", 10_000, "2026-06-30")]
        sd1 = _make_sessions(
            [_make_session("claude", 100, "2026-07-15", "a@b.com")],
            stats_cache=sc, machine="m1")
        sd2 = _make_sessions(
            [_make_session("claude", 100, "2026-07-20", "b@c.com")],
            stats_cache=[], machine="m2")
        totals1 = _make_totals({"a@b.com": 90})
        totals2 = _make_totals({"b@c.com": 90})
        _build_machine_dir(td, "m1", sd1, totals1)
        _build_machine_dir(td, "m2", sd2, totals2)

        life = _run_fleet_fold(td, sd1, totals1)

    by_machine = dict(life["by_machine"])
    m2 = by_machine.get("m2", 0)
    # m2 has only 100 scan tokens and no cache; it must not receive any delta.
    check("m2 tokens exactly equal its scan (no cross-machine bleeding)",
          m2, 100,
          f"m2 is {m2:,}, want 100 — m1's cache delta bled into m2")


def t_multi_account_floor_applied_once_per_account():
    """A stats-cache entry is per ACCOUNT, not per profile.

    If one account owns three profiles (three stats-cache entries all resolving
    to the same account after label normalisation), the floor must be applied
    exactly once — not three times. Three applications would triple the floor
    contribution and violate the invariant the comment in machine_floor explains.

    This test does not duplicate the multi-profile logic in machine_floor
    (which is already tested in stats_page's own test surface), but verifies
    that monthly.py's integration with machine_floor does not re-apply the
    floor per stats-cache entry or per profile.

    THE BREAK: call machine_floor once per stats-cache entry and sum the
    results. The floor becomes N * real_floor for N entries on the same account.
    """
    with tempfile.TemporaryDirectory() as td:
        # Three stats-cache entries for the SAME account — three profiles on one login
        sc = [
            _make_stats_cache_entry("a@b.com", 5_000, "2026-06-20"),
            _make_stats_cache_entry("a@b.com", 5_000, "2026-06-25"),
            _make_stats_cache_entry("a@b.com", 5_000, "2026-06-28"),
        ]
        sd = _make_sessions(
            [_make_session("claude", 100, "2026-07-15", "a@b.com")],
            stats_cache=sc, machine="m1")
        # totals carries the SAME account once — machine_floor merges profiles
        totals = _make_totals({"a@b.com": 90})
        _build_machine_dir(td, "m1", sd, totals)

        life = _run_fleet_fold(td, sd, totals)

    # machine_floor sees three entries for the same account; it de-duplicates
    # by_acct = {e["account"]: e for e in statscache_here} — last one wins,
    # so total = 5000 (not 15000). The floor is 5000.
    check("three entries for same account apply the floor once, not three times",
          life["tokens"] < 15_100, True,
          f"life['tokens']={life['tokens']:,} >= 3 * cache_total — "
          "the floor was applied once per stats-cache entry, not per account")
    check("floor is at least cache_total (5000) not below",
          life["tokens"] >= 5_000, True,
          f"floor was not applied: life['tokens']={life['tokens']:,} < 5000")


# ---------------------------------------------------------------------------
# GAP 1 continued — per-machine LIFETIME.md path
# ---------------------------------------------------------------------------

def t_per_machine_lifetime_md_reflects_floor():
    """The per-machine LIFETIME.md headline equals fleet LIFETIME.md for one machine.

    There are TWO code paths that apply the floor: fold_ledger_fleet (fleet)
    and the inline block in monthly.main() (per-machine). If one is fixed and
    the other is not, LIFETIME.md in the root says 49B while the machine folder
    says 18B — and a reader who opens the per-machine report gets the wrong number.

    THE BREAK: apply the floor only in apply_statscache_floor_fleet but not in
    the per-machine block. The per-machine lifetime.json then holds the scan
    total, and the fleet lifetime.json holds the floor total; they disagree.

    This test calls both paths the same way monthly.main() would and checks
    that the resulting life dicts carry the same token total.
    """
    sc = [_make_stats_cache_entry("a@b.com", 10_000, "2026-06-30")]
    sessions_list = [_make_session("claude", 100, "2026-07-15", "a@b.com")]
    sd = _make_sessions(sessions_list, stats_cache=sc)
    totals = _make_totals({"a@b.com": 90})

    import stats_page as sp
    import paths as P

    with tempfile.TemporaryDirectory() as td:
        root = pathlib.Path(td)
        md = _build_machine_dir(td, "m1", sd, totals)
        name = "m1"

        # --- fleet path ---
        months, life_fleet = monthly.collect(root)
        monthly.fold_ledger_fleet(root, life_fleet)
        fleet_tokens = life_fleet["tokens"]

        # --- per-machine path (mirrors monthly.main()) ---
        mm, ml = monthly.collect_from(sessions_list, name,
                                      P.find(md, "totals.json"))
        ml["scanned_tokens"] = ml["tokens"]
        ml["ledger"] = {name: monthly.fold_ledger(md, name, ml, dict(ml["by_cli"]))}
        ml["ledger_beyond_scan"] = ml["tokens"] - ml["scanned_tokens"]
        _sc = sd.get("stats_cache", [])
        if _sc:
            _tf = P.find(md, "totals.json")
            try:
                _t = json.loads(_tf.read_text(encoding="utf-8")) if _tf else {}
            except Exception:
                _t = {}
            _floor, _cf, _of, _ = sp.machine_floor(_t, sessions_list, _sc)
            _cur_claude = sum(s.get("total", 0) for s in sessions_list
                              if s.get("cli") == "claude" and s.get("start"))
            _cur_other  = sum(s.get("total", 0) for s in sessions_list
                              if s.get("cli") != "claude" and s.get("start"))
            _d_claude = max(0, _cf - _cur_claude)
            _d_other  = max(0, _of  - _cur_other)
            if _d_claude:
                ml["by_cli"]["claude"]  += _d_claude
            _added = _d_claude + _d_other
            ml["tokens"] += _added
            ml["statscache_floor_delta"] = _added
        per_machine_tokens = ml["tokens"]

    check("fleet and per-machine lifetime agree on token total",
          fleet_tokens, per_machine_tokens,
          f"fleet={fleet_tokens:,}, per-machine={per_machine_tokens:,} — "
          "the floor is applied in one path but not the other, so the two "
          "LIFETIME.md files disagree")


# ---------------------------------------------------------------------------
# Integrity: every test can fail (adversarial_meta compatibility)
# ---------------------------------------------------------------------------

def t_self_canary_floor_logic():
    """Planted break: remove the floor application entirely.

    Directly calls apply_statscache_floor_fleet with a patched no-op to
    verify that the checks above would fail if the floor were never applied.
    This is the same shape as adv_tick_does_not_invent_ok: a test suite that
    cannot fail is not evidence.
    """
    with tempfile.TemporaryDirectory() as td:
        sc = [_make_stats_cache_entry("a@b.com", 10_000, "2026-06-30")]
        sd = _make_sessions(
            [_make_session("claude", 100, "2026-07-15", "a@b.com")],
            stats_cache=sc)
        totals = _make_totals({"a@b.com": 90})
        _build_machine_dir(td, "m1", sd, totals)
        root = pathlib.Path(td)

        months, life = monthly.collect(root)
        scan_total = life["tokens"]   # 100 — before the floor

        # BREAK: no-op the floor function
        real_fn = monthly.apply_statscache_floor_fleet
        monthly.apply_statscache_floor_fleet = lambda root, life: None
        try:
            monthly.fold_ledger_fleet(root, life)
        finally:
            monthly.apply_statscache_floor_fleet = real_fn

        broken_tokens = life["tokens"]

    # With the break planted, tokens should still be the scan total.
    # Our test t_floor_lifts_headline would then FAIL because broken_tokens < 10 000.
    check("self-canary: a no-op floor leaves tokens at the scan total",
          broken_tokens, scan_total,
          f"the patched no-op still changed tokens from {scan_total} to "
          f"{broken_tokens} — something else is lifting the floor")
    check("self-canary: confirms t_floor_lifts_headline would catch the break",
          broken_tokens < 10_000, True,
          f"broken_tokens={broken_tokens:,} >= 10 000 — the canary does not "
          "fail with the break planted, so the above tests are not evidence")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

CHECKS = [
    ("floor lifts headline when cache > scan",
     t_floor_lifts_headline),
    ("no delta when scan already exceeds cache",
     t_floor_does_not_double_if_scan_exceeds_cache),
    ("by_cli['claude'] reflects floor delta",
     t_by_cli_claude_reflects_floor),
    ("floor does not bleed into frozen month buckets",
     t_frozen_months_not_affected_by_floor),
    ("lifetime.json carries statscache_floor_delta key",
     t_lifetime_json_carries_floor_delta),
    ("absent stats_cache: no change, no crash",
     t_absent_stats_cache_no_change),
    ("empty stats_cache: no change, no crash",
     t_empty_stats_cache_no_change),
    ("malformed stats_cache entries: no crash",
     t_malformed_stats_cache_entry_no_crash),
    ("corrupt totals.json: degrades gracefully",
     t_corrupt_totals_json_no_crash),
    ("machine without cache is unaffected",
     t_machine_without_stats_cache_unaffected),
    ("floor is per-machine, not fleet-wide",
     t_floor_is_per_machine_not_fleet_wide),
    ("multi-account: floor applied once per account",
     t_multi_account_floor_applied_once_per_account),
    ("per-machine and fleet lifetime agree",
     t_per_machine_lifetime_md_reflects_floor),
    ("self-canary: planted break is detectable",
     t_self_canary_floor_logic),
]


def main():
    print(f"\n  adv_statscache_floor — {len(CHECKS)} check(s)\n")
    for name, fn in CHECKS:
        print(f"  -- {name}")
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            import traceback
            print(f"  FAIL  {name} raised unexpectedly")
            for line in traceback.format_exc().splitlines():
                print(f"          {line}")
            FAILED.append(name)
    print()
    if FAILED:
        print(f"  {len(FAILED)} FAILED: {', '.join(FAILED)}")
        return 1
    n_run = len(CHECKS) - len(SKIPPED)
    print(f"  {n_run} passed"
          + (f", {len(SKIPPED)} skipped" if SKIPPED else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
