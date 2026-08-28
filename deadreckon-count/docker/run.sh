#!/usr/bin/env bash
# Run a profile tool against the whole fleet as if it were one computer.
#
#   ./docker/run.sh                      # what the tool would see, offline
#   ./docker/run.sh --net -- npx standout # network ON, uploads INTERCEPTED
#   ./docker/run.sh --live -- npx standout # network ON, uploads REAL
#
# To audit what a tool would upload, use ../submit_gate.sh instead. It vendors
# the CLI with the corpus unmounted, then runs it under --network none, so
# nothing can escape even if a variable is wrong.
#
# WHY --net IS NOT ENOUGH ON ITS OWN
#
# This script forwarded no environment into the container at all, so a host
# `STANDOUT_API_URL=...` arrived UNSET and every documented --net invocation was
# a real upload of a private corpus. That was invisible while the argument
# handling was also broken (the tool never actually ran). Fixing one exposed the
# other.
#
# So --net now defaults to INTERCEPTED: an unreachable API url is injected
# unless you pass one yourself. Sending real data requires --live, which is a
# word you have to type.
#
# The corpus mounts READ-ONLY. Everything else about the container is disposable.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(dirname "$HERE")"
MERGED="${MERGED:-$REPO/merged}"
NET="none"
LIVE=0
IMAGE="deadreckon-record-runner"

usage() {
  sed -n '2,20p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
  cat <<'EOF'

  --merged DIR     corpus to mount (default ../merged)
  -e KEY=VALUE     forward one environment variable
  --net            network on, uploads intercepted (safe default)
  --live           network on, uploads REAL — requires typing it
  -- CMD...        command to run inside the container
EOF
  exit 0
}

envs=()
user_set_api=0
args=()
while [ $# -gt 0 ]; do
  case "$1" in
    --net)      NET="bridge"; shift ;;
    --live)     NET="bridge"; LIVE=1; shift ;;
    --merged)   [ $# -ge 2 ] || { echo "--merged needs a directory" >&2; exit 2; }
                MERGED="$2"; shift 2 ;;
    -e)         [ $# -ge 2 ] || { echo "-e needs KEY=VALUE" >&2; exit 2; }
                case "$2" in STANDOUT_API_URL=*) user_set_api=1 ;; esac
                envs+=(-e "$2"); shift 2 ;;
    -h|--help)  usage ;;
    --)         shift; args=("$@"); break ;;
    *)          args+=("$1"); shift ;;
  esac
done

# Relative paths become docker VOLUME NAMES rather than bind mounts, which
# fails with an obscure error after the corpus line has already printed a
# convincing count. Resolve before anything is reported.
MERGED="$(cd "$MERGED" 2>/dev/null && pwd || echo "$MERGED")"

if [ ! -d "$MERGED/.claude/projects" ]; then
  echo "no merged corpus at $MERGED/.claude/projects" >&2
  echo "run:  python3 merge_corpus.py" >&2
  exit 1
fi

n=$(find "$MERGED/.claude/projects" -maxdepth 1 -mindepth 1 -type d | wc -l)
f=$(find "$MERGED/.claude/projects" -name '*.jsonl' | wc -l)
echo "corpus : $MERGED  ($n projects, $f transcripts)"

# WHEN the tree was merged, always — never silently.
#
# Both runners default to $REPO/merged, and that default was a day-old tree
# with 18,037 transcripts while the corpus that had actually been rebuilt held
# 20,217. Everything downstream — the capture, the gate's verdict on it — then
# described the wrong input, and nothing said so. A stale tree is legitimate;
# a stale tree you cannot see is not.
if [ -f "$MERGED/MERGE.json" ]; then
  gen=$(sed -n 's/.*"generated_at"[: ]*"\([^"]*\)".*/\1/p' "$MERGED/MERGE.json" | head -1)
  age=$(( ( $(date +%s) - $(stat -c %Y "$MERGED/MERGE.json" 2>/dev/null || echo 0) ) / 3600 ))
  if [ "$age" -gt 24 ]; then
    echo "merged : ${gen:-unknown}   <- ${age}h old; rebuild with merge_corpus.py if machines have scanned since"
  else
    echo "merged : ${gen:-unknown}"
  fi
fi

# Default-deny. With the network on and no api url of your own, point every
# request the tool makes at a closed port so it cannot reach anyone.
if [ "$NET" != "none" ] && [ "$LIVE" = 0 ] && [ "$user_set_api" = 0 ]; then
  envs+=(-e STANDOUT_API_URL=http://127.0.0.1:9)
  echo "network: $NET  (uploads INTERCEPTED — pass --live to send for real)"
elif [ "$LIVE" = 1 ]; then
  # The tool's own consent step is not a backstop. With no tty it prints
  # "(non-interactive, proceeding)" and POSTs the payload before showing a
  # single card — so --live from a pipe, a script or CI uploads the private
  # corpus with nobody having seen it. Typing --live is a good gate for a human
  # at a keyboard and no gate at all for anything else, so require the keyboard.
  if [ ! -t 0 ]; then
    echo "refusing --live without a terminal." >&2
    echo "  standout skips its own review step when stdin is not a tty:" >&2
    echo "  it would POST ~4 MB of the corpus before showing you anything." >&2
    echo "  Run it from an interactive shell, or audit with ./submit_gate.sh." >&2
    exit 1
  fi
  echo "network: $NET  *** LIVE — uploads will be REAL ***"
  echo "         corpus: $f transcripts from $n projects"
  echo "         audit first with:  ./submit_gate.sh"
else
  echo "network: $NET"
fi

docker image inspect "$IMAGE" >/dev/null 2>&1 || {
  # Root cannot be the container user — the image renames the uid to `runner`
  # and you cannot rename root. Say so here, because the alternative is a
  # usermod error from inside a build log.
  [ "$(id -u)" != 0 ] || { echo "do not run this as root (or under sudo):" >&2
                           echo "  the container deliberately runs as a non-root user" >&2
                           exit 1; }
  echo "building $IMAGE ..."
  docker build -q -t "$IMAGE" --build-arg UID="$(id -u)" --build-arg GID="$(id -g)" "$HERE"
}

# --network none by default. A tool that only reads local records needs no
# network, and anything that phones home should be an explicit choice rather
# than a side effect of running this.
#
# The mount is :ro. These are the only copies of transcripts already deleted
# from the machines that produced them; nothing run in here gets to alter them.
# The image's ENTRYPOINT is `bash -lc`, which takes ONE command string — any
# further arguments become $0, $1 ... and are never executed. Passing
# "${args[@]:-}" therefore broke both documented invocations:
#
#   --net -- npx standout   ran bare `npx`; the word `standout` became $0
#   (no arguments)          expanded to a single EMPTY string, which overrode
#                           the Dockerfile CMD, so the offline mode printed
#                           nothing instead of showing what the tool would see
#
# Join into one string, and pass nothing at all when there is nothing to pass
# so CMD survives.
TTY=(); [ -t 0 ] && TTY=(-it)
#
# The entrypoint is `bash -lc`, which runs ONE string, so several arguments have
# to become one. There are two intents and they want opposite handling:
#
#   ONE argument   is a shell snippet and must pass through untouched, or
#                    -- 'echo one; echo two'
#                  becomes a single literal command name.
#
#   MANY arguments are an argv and must be escaped individually, or
#                    -- printf '[%s]\n' 'a b'
#                  gave [a]n[b]n — 'a b' re-split into two and \n lost its
#                  backslash. %q makes the inner shell rebuild exactly what
#                  was typed.
#
# Joining everything on spaces broke the first case's siblings; escaping
# everything broke the second. Dispatching on the count is what serves both.
#
case "${#args[@]}" in
  0) set -- ;;
  1) set -- "${args[0]}" ;;
  *) set -- "$(printf '%q ' "${args[@]}")" ;;
esac

# Mount the vendored CLI when submit_gate.sh has already fetched it, so a live
# run uses the EXACT build that was audited rather than whatever `npx` resolves
# today. Without this, `-- node /vendor/...` died with MODULE_NOT_FOUND because
# only submit_gate.sh mounted it — the audit and the submission would have run
# different code.
VOL=()
if [ -d "$REPO/vendor/node_modules" ]; then
  VOL=(-v "$REPO/vendor:/vendor:ro")
fi

exec docker run --rm "${TTY[@]}" \
  --network "$NET" \
  --read-only --tmpfs /tmp:exec,size=2g \
  -v "$MERGED/.claude:/home/runner/.claude:ro" \
  ${VOL[@]+"${VOL[@]}"} \
  ${envs[@]+"${envs[@]}"} \
  "$IMAGE" "$@"
