// A local stand-in for standout.work, so the payload can be READ before anyone
// decides whether to send it.
//
// `STANDOUT_API_URL` templates every request the CLI makes — submit, enrich,
// wrapped, the GitHub proxy and the LLM baseURL. Pointing it here means the
// tool runs its whole flow and hands us the exact bytes it would have uploaded.
//
// WHY THIS EXISTS AT ALL: the difference between a dry run and publishing a
// real corpus is one environment variable. A gate you can inspect beats a
// promise you cannot. The container that runs this has --network none, so even
// if the variable were wrong there is nowhere for a request to go.
//
// Node, not Python, because the image is node:22-slim and has no python3.
// No dependencies on purpose: this must run with the corpus mounted read-only
// and npm unable to reach a registry.
//
//   node sink.js            # PORT=8787 CAPTURE=/capture
//
// Every request becomes one file. Nothing is ever replayed to the internet.

const http = require("http");
const fs = require("fs");
const path = require("path");

const PORT = parseInt(process.env.SINK_PORT || "8787", 10);
const CAPTURE = process.env.CAPTURE || "/capture";

fs.mkdirSync(CAPTURE, { recursive: true });

let n = 0;

// The CLI branches on what it gets back. A bare 200 makes it stop early and the
// large payload never gets built, so the reply is permissive and shaped like
// something it can keep walking: ids and urls present, everything optional.
//
// `computed` is not decoration. After POSTing the payload the CLI calls
// pollComputed(), which loops until:
//
//     isReady(computed) === computed.status === "ready" || computed.archetype != null
//
// A reply without it polls for the full POLL_TIMEOUT_MS (180 s) and then gives
// up, which looks exactly like a hang. Answering "ready" immediately lets the
// run finish in seconds and, more importantly, lets the CLI proceed to whatever
// it would send NEXT — the later requests are part of what needs auditing.
function reply(url) {
  return {
    ok: true,
    id: "local-sink",
    slug: "local-sink",
    url: "http://127.0.0.1/local-sink",
    wrapped_url: "http://127.0.0.1/local-sink",
    profile_url: "http://127.0.0.1/local-sink",
    status: "ok",
    computed: {
      status: "ready",
      archetype: "local-sink",
      summary: "captured locally",
      stats: {},
    },
    data: {},
    result: {},
    choices: [{ message: { role: "assistant", content: "{}" } }],
    _sink_note: "captured locally; nothing was uploaded",
    _sink_path: url,
  };
}

const server = http.createServer((req, res) => {
  const chunks = [];
  req.on("data", (c) => chunks.push(c));
  req.on("end", () => {
    const body = Buffer.concat(chunks);
    n += 1;

    // Authorization headers are the one thing NOT written to disk. The capture
    // is meant to be read, diffed and pasted into a report; a bearer token in
    // it would be a new leak created by the tool built to prevent leaks.
    const headers = {};
    for (const [k, v] of Object.entries(req.headers)) {
      headers[k] = /^(authorization|cookie|x-api-key)$/i.test(k) ? "[stripped]" : v;
    }

    const slug = (req.url || "/").replace(/[^A-Za-z0-9]+/g, "-").slice(0, 60);
    const file = path.join(
      CAPTURE,
      `${String(n).padStart(4, "0")}-${req.method}-${slug}.json`
    );

    let parsed = null;
    try {
      parsed = JSON.parse(body.toString("utf8"));
    } catch {
      /* not JSON; raw is kept below */
    }

    fs.writeFileSync(
      file,
      JSON.stringify(
        {
          seq: n,
          method: req.method,
          url: req.url,
          headers,
          body_bytes: body.length,
          body_is_json: parsed !== null,
          // Both forms are kept. The gate scans the DECODED strings, because
          // scanning raw bytes reports "\n@pytest.fixture" as an email address
          // and produced 613 false positives when it was first done that way.
          // The raw text is kept anyway so a human can see exactly what left.
          body: parsed,
          body_raw: parsed === null ? body.toString("utf8") : undefined,
        },
        null,
        1
      ),
      "utf8"
    );

    console.log(
      `[sink] ${String(n).padStart(3)} ${req.method} ${req.url}  ${body.length} bytes -> ${path.basename(file)}`
    );

    res.writeHead(200, { "content-type": "application/json" });
    res.end(JSON.stringify(reply(req.url)));
  });
});

// Bind to all interfaces INSIDE the container. With --network none there is no
// route off the host namespace, so this is reachable only by the CLI beside it.
server.listen(PORT, "0.0.0.0", () => {
  console.log(`[sink] listening on ${PORT}, capturing to ${CAPTURE}`);
});
