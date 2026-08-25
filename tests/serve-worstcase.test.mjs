// tests/serve-worstcase.test.mjs — the LAN server under hostile conditions.
//
// `starreckon serve` binds a port on the local network and, with --collect,
// WRITES FILES from network input. The threat model is not the internet: it is
// the other devices on the same WiFi — a housemate's laptop, a conference
// network, a compromised phone. None of them are authenticated, and none of
// them have to be well-behaved.
//
// Every test here drives makeHandler() directly with fake req/res. No sockets,
// no bind, no network — they pass on a machine with the WiFi switched off.
import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, rmSync, existsSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";

import { lanIp, makeHandler, sanitizeFolderName } from "../src/serve.mjs";

const tmp = () => mkdtempSync(join(tmpdir(), "starreckon-serve-worst-"));

// A fake request that can emit a body, so POST paths are drivable.
function fakePost(url = "/submit", chunks = []) {
  const listeners = {};
  const req = {
    method: "POST",
    url,
    socket: { remoteAddress: "192.168.1.99", once() {} },
    destroyed: false,
    on(ev, fn) { (listeners[ev] ??= []).push(fn); return req; },
    destroy() { req.destroyed = true; },
    _emit(ev, arg) { for (const fn of listeners[ev] ?? []) fn(arg); },
    _send() {
      for (const c of chunks) {
        if (req.destroyed) return;      // a destroyed request stops delivering
        req._emit("data", c);
      }
      if (!req.destroyed) req._emit("end");
    },
  };
  return req;
}

function fakeRes() {
  const calls = { writeHead: null, ended: null, headers: {} };
  return {
    _calls: calls,
    writeHead(s, h) { calls.writeHead = s; Object.assign(calls.headers, h ?? {}); },
    end(b) { calls.ended = b ?? ""; },
  };
}

const withDir = (fn) => {
  const d = tmp();
  try { return fn(d); } finally { rmSync(d, { recursive: true, force: true }); }
};

// ── WiFi absent / hostile network shape ──────────────────────────────────────

test("lanIp never throws and never advertises a link-local address", () => {
  // Worst case is WiFi off: no external interface at all. lanIp must still
  // return something bindable rather than undefined, and must never hand out a
  // 169.254.x.x autoconfiguration address — printing that in a QR code sends
  // the user to an address that cannot route.
  const ip = lanIp();
  assert.equal(typeof ip, "string");
  assert.ok(ip.length > 0, "lanIp must always return a bindable address");
  assert.ok(!ip.startsWith("169.254."), "link-local is never a usable LAN address");
  assert.match(ip, /^\d{1,3}(\.\d{1,3}){3}$/);
});

// ── unauthenticated writes: POST /submit ─────────────────────────────────────

test("POST /submit is 404 when collection was not enabled", () => {
  const { handler } = makeHandler("<h1>hi</h1>", 3, null);
  const req = fakePost();
  const res = fakeRes();
  handler(req, res);
  req._send();
  assert.equal(res._calls.writeHead, 404, "no --collect means no write endpoint");
});

test("an oversized body is refused instead of being buffered without limit", () => {
  // THE DENIAL OF SERVICE. `body += chunk` with no cap means any device on the
  // same WiFi can hold the process open and grow a string until it dies. The
  // server must stop reading and answer 413 rather than accumulate whatever it
  // is handed.
  withDir((dir) => {
    const { handler } = makeHandler("<h1>hi</h1>", 3, dir);
    // 12 MB in 1 MB chunks — well past any legitimate machine folder.
    const chunks = Array.from({ length: 12 }, () => "x".repeat(1024 * 1024));
    const req = fakePost("/submit", chunks);
    const res = fakeRes();
    handler(req, res);
    req._send();
    assert.equal(
      res._calls.writeHead,
      413,
      "an unbounded POST body is a denial of service on the LAN endpoint",
    );
  });
});

test("a legitimate-sized submission is still accepted", () => {
  // The cap must not break the feature it protects.
  withDir((dir) => {
    const { handler } = makeHandler("<h1>hi</h1>", 3, dir);
    const body = JSON.stringify({ folderName: "laptop", sessions: [] });
    const req = fakePost("/submit", [body]);
    const res = fakeRes();
    handler(req, res);
    req._send();
    assert.notEqual(res._calls.writeHead, 413, "a small valid body must not be rejected");
  });
});

test("malformed JSON is rejected without touching the filesystem", () => {
  withDir((dir) => {
    const { handler } = makeHandler("<h1>hi</h1>", 3, dir);
    const req = fakePost("/submit", ["{not json at all"]);
    const res = fakeRes();
    handler(req, res);
    req._send();
    assert.equal(res._calls.writeHead, 400);
    assert.equal(existsSync(dir) ? readdirSync(dir).length : 0, 0, "nothing was written");
  });
});

// ── path traversal via the one attacker-controlled name ──────────────────────

test("sanitizeFolderName refuses every traversal and absolute-path shape", () => {
  // folderName is the ONLY attacker-controlled value that reaches a filesystem
  // path. If it can escape collectDir, an unauthenticated device on the WiFi
  // can write anywhere the process can.
  for (const evil of [
    "../../etc/passwd",
    "..",
    ".",
    "/etc/passwd",
    "....//....//etc",
    ".ssh",
    ".bashrc",
    "\\..\\..\\windows",
    "foo/../../bar",
    "con:/../x",
  ]) {
    const out = sanitizeFolderName(evil);
    if (out !== null) {
      assert.ok(!out.includes("/"), `"${evil}" -> "${out}" still contains a separator`);
      assert.ok(!out.includes("\\"), `"${evil}" -> "${out}" still contains a separator`);
      assert.ok(!out.startsWith("."), `"${evil}" -> "${out}" is a dotfile`);
      assert.notEqual(out, "..");
    }
  }
});

test("a traversing folderName never creates anything outside collectDir", () => {
  withDir((dir) => {
    const { handler } = makeHandler("<h1>hi</h1>", 3, join(dir, "collect"));
    const req = fakePost("/submit", [
      JSON.stringify({ folderName: "../../escaped", sessions: [] }),
    ]);
    const res = fakeRes();
    handler(req, res);
    req._send();
    assert.ok(!existsSync(join(dir, "escaped")), "wrote outside the collect directory");
  });
});

test("an absurdly long folderName is truncated, not passed through", () => {
  const out = sanitizeFolderName("a".repeat(5000));
  assert.ok(out.length <= 64, "a 5000-char path component can break the filesystem");
});

// ── request shapes a hostile client can send ─────────────────────────────────

test("GET with a traversing path is 404, never a file read", () => {
  const { handler } = makeHandler("<h1>secret</h1>", 3, null);
  for (const url of [
    "/../../etc/passwd",
    "/..%2f..%2fetc%2fpasswd",
    "//etc/passwd",
    "/index.html/../../../etc/shadow",
  ]) {
    const res = fakeRes();
    handler({ method: "GET", url, socket: { remoteAddress: "1.2.3.4", once() {} } }, res);
    assert.equal(res._calls.writeHead, 404, `${url} must not be served`);
  }
});

test("a request with no socket at all does not crash the server", () => {
  // A half-open or immediately-reset connection can reach the handler with no
  // usable socket. One hostile client must not be able to take the process down.
  const { handler } = makeHandler("<h1>hi</h1>", 3, null);
  const res = fakeRes();
  assert.doesNotThrow(() => handler({ method: "GET", url: "/", socket: null }, res));
  assert.equal(res._calls.writeHead, 200);
});

test("visits past the shutdown limit neither throw nor keep counting up", () => {
  // maxVisits is the only thing bounding how long the server stays exposed.
  const { handler, onShutdown, getVisits } = makeHandler("<h1>hi</h1>", 2, null);
  let fired = 0;
  onShutdown(() => { fired += 1; });
  for (let i = 0; i < 10; i++) {
    handler({ method: "GET", url: "/", socket: { remoteAddress: "1.2.3.4", once() {} } }, fakeRes());
  }
  assert.equal(fired, 1, "shutdown must fire exactly once, not once per extra visit");
  if (typeof getVisits === "function") assert.ok(getVisits() >= 2);
});
