#!/usr/bin/env bash
# Run the profile tool over the whole fleet and CAPTURE what it would upload,
# without letting it upload anything.
#
#   ./submit_gate.sh                       # vendor, capture, verify
#   ./submit_gate.sh --merged /path/to/merged
#   ./submit_gate.sh --skip-vendor         # reuse an existing vendor/ tree
#
# Three phases, and the split is the whole point:
#
#   1 VENDOR   network ON, corpus NOT mounted. npm downloads standout and its
#              entire dependency tree into vendor/. This is the only phase that
#              reaches the internet, and it cannot see the transcripts.
#
#   2 CAPTURE  --network none, corpus mounted READ-ONLY. The CLI runs against a
#              local sink that records every request. With no network there is
#              nowhere for a request to go even if STANDOUT_API_URL were wrong,
#              so interception is no longer something to trust — it is
#              something the kernel enforces.
#
#   3 VERIFY   verify_payload.py reads the captured bytes on the host.
#
# The previous design ran with the network UP and relied on STANDOUT_API_URL
# being set correctly. That is one typo away from publishing a private corpus.
# Splitting the phases removes the typo from the threat model.
#
# This never submits. Submitting is a separate, deliberate act by a human.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MERGED="${MERGED:-$HERE/merged}"
VENDOR="$HERE/vendor"
CAPTURE="$HERE/capture"
IMAGE="deadreckon-record-runner"
PKG="${PKG:-standout}"
SKIP_VENDOR=0

# Arguments handed to the CLI itself. These are NOT cosmetic: a positional
# token is parsed as a jobId, which FORCES mode="full" (no mode prompt, no
# local option), sets STANDOUT_JOB_ID, and tags the wrapped with
# `group: <jobId>`. Auditing a bare `standout` and then running
# `standout <job-id>` would audit a different payload than the one sent.
CLI_ARGS=()

while [ $# -gt 0 ]; do
  case "$1" in
    --merged)       MERGED="$2"; shift 2 ;;
    --capture)      CAPTURE="$2"; shift 2 ;;
    --skip-vendor)  SKIP_VENDOR=1; shift ;;
    --package)      PKG="$2"; shift 2 ;;
    --)             shift; CLI_ARGS=("$@"); break ;;
    *) echo "unknown option: $1" >&2
       echo "  (pass CLI arguments after --, e.g. -- standout-founding-eng)" >&2
       exit 2 ;;
  esac
done

[ -d "$MERGED/.claude/projects" ] || {
  echo "no merged corpus at $MERGED/.claude/projects" >&2
  echo "run:  python3 merge_corpus.py --corpus <dir> --out $MERGED" >&2
  exit 1
}

docker image inspect "$IMAGE" >/dev/null 2>&1 || {
  [ "$(id -u)" != 0 ] || { echo "do not run this as root (or under sudo):" >&2
                           echo "  the container deliberately runs as a non-root user" >&2
                           exit 1; }
  echo "building $IMAGE ..."
  docker build -q -t "$IMAGE" --build-arg UID="$(id -u)" --build-arg GID="$(id -g)" "$HERE/docker"
}

echo "corpus  : $MERGED ($(find "$MERGED/.claude/projects" -name '*.jsonl' | wc -l) transcripts)"
# Auditing the wrong tree is worse than not auditing: it produces a verdict.
# The default here was a day-stale merge, 2,180 transcripts short, and said so
# to nobody.
if [ -f "$MERGED/MERGE.json" ]; then
  gen=$(sed -n 's/.*"generated_at"[: ]*"\([^"]*\)".*/\1/p' "$MERGED/MERGE.json" | head -1)
  age=$(( ( $(date +%s) - $(stat -c %Y "$MERGED/MERGE.json" 2>/dev/null || echo 0) ) / 3600 ))
  echo "merged  : ${gen:-unknown}$([ "$age" -gt 24 ] && echo "   <- ${age}h old" || true)"
fi
echo "vendor  : $VENDOR"
echo "capture : $CAPTURE"

# ---------------------------------------------------------------- 1 VENDOR
if [ "$SKIP_VENDOR" = 0 ]; then
  echo
  echo "[1/3] vendoring $PKG (network ON, corpus NOT mounted)"
  rm -rf "$VENDOR"; mkdir -p "$VENDOR"
  # No corpus mount here on purpose: the one phase with a route to the
  # internet is also the one phase with nothing worth sending.
  docker run --rm \
    --network bridge \
    -v "$VENDOR:/vendor" \
    -e npm_config_cache=/tmp/npm \
    "$IMAGE" \
    "npm install --prefix /vendor --no-audit --no-fund --loglevel=error $PKG >/dev/null && \
     node -e 'const p=require(\"/vendor/node_modules/$PKG/package.json\");
              const b=p.bin; const rel=typeof b===\"string\"?b:Object.values(b)[0];
              console.log(rel)' > /vendor/.binpath && \
     echo vendored \$(node -e 'console.log(require(\"/vendor/node_modules/$PKG/package.json\").version)')"
else
  echo
  echo "[1/3] skipping vendor, reusing $VENDOR"
  [ -d "$VENDOR/node_modules/$PKG" ] || { echo "no vendored $PKG in $VENDOR" >&2; exit 1; }
fi

BIN_REL="$(cat "$VENDOR/.binpath" 2>/dev/null || echo "dist/cli.js")"
echo "        entry: node_modules/$PKG/$BIN_REL"

# ---------------------------------------------------------------- 2 CAPTURE
echo
echo "[2/3] capturing (--network none, corpus READ-ONLY)"
rm -rf "$CAPTURE"; mkdir -p "$CAPTURE"

# --network none is the guarantee. STANDOUT_API_URL is still set, but now as a
# convenience so the CLI reaches the sink quickly rather than waiting on DNS
# that cannot resolve — not as the thing standing between a private corpus and
# the internet.
docker run --rm \
  --network none \
  --read-only --tmpfs /tmp:exec,size=2g \
  -v "$MERGED/.claude:/home/runner/.claude:ro" \
  -v "$VENDOR:/vendor:ro" \
  -v "$CAPTURE:/capture" \
  -v "$HERE/docker/sink.js:/sink.js:ro" \
  -e CAPTURE=/capture \
  -e SINK_PORT=8787 \
  -e STANDOUT_API_URL=http://127.0.0.1:8787 \
  -e CI=1 \
  "$IMAGE" \
  "node /sink.js & sink=\$!;
   for i in \$(seq 1 50); do
     node -e 'require(\"net\").connect(8787,\"127.0.0.1\").on(\"connect\",()=>process.exit(0)).on(\"error\",()=>process.exit(1))' 2>/dev/null && break
     sleep 0.2
   done
   echo '[gate] sink up, running $PKG ${CLI_ARGS[*]} with no network';
   node /vendor/node_modules/$PKG/$BIN_REL ${CLI_ARGS[*]} </dev/null 2>&1 | tail -40 || true;
   sleep 2; kill \$sink 2>/dev/null || true; wait \$sink 2>/dev/null || true" \
  || echo "  (CLI exited non-zero — expected; it could not reach a real server)"

echo
echo "        captured $(ls -1 "$CAPTURE" 2>/dev/null | wc -l) request(s)"

# ---------------------------------------------------------------- 3 VERIFY
echo
echo "[3/3] verifying the captured payload"
python3 "$HERE/verify_payload.py" --capture "$CAPTURE"
