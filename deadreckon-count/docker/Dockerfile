# One computer, assembled from all of them.
#
# `merge_corpus.py` collapses every machine's redacted transcripts into a single
# .claude/projects tree. This mounts that tree as a home directory and runs a
# profile tool against it, so a tool that reads one home sees the whole fleet.
#
# Two reasons it is a container rather than a directory on the host:
#
#   1. Tools of this kind read more than the transcripts. The one this was built
#      for also reaches for browser cookies and honours an env var that
#      redirects every request it makes. In here there is no browser profile, no
#      ssh key, no host filesystem beyond the single mount, and the network can
#      be switched off entirely with --network none.
#   2. HOME is the whole interface. Setting it on the host risks a tool writing
#      into a real profile; here the only writable thing is the mount.
#
# Build:  docker build -t deadreckon-record-runner docker/
# Run:    see run.sh

FROM node:22-slim

# git and ca-certificates only — npx fetches over https, and some tools shell
# out to git for repo context. Nothing else is installed on purpose.
RUN apt-get update \
 && apt-get install -y --no-install-recommends git ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# A non-root user whose home is the mount point. Running as root would let a
# tool write anywhere in the image and would leave root-owned files in the
# bind-mounted corpus on the host.
#
# The base image already ships uid 1000 as `node`, which is the same uid most
# hosts hand out. RENAME that account rather than adding a second one: the first
# attempt here ran `useradd || true`, which swallowed the collision and produced
# an image with no `runner` at all — `docker run` then failed with "unable to
# find user runner: no matching entries in passwd file". `|| true` on a command
# whose success is load-bearing turns a build error into a run error.
#
# THE GID MUST BE ALLOWED TO ALREADY EXIST.
#
# run.sh and submit_gate.sh pass --build-arg GID="$(id -g)". On macOS the
# default primary group is `staff`, gid 20 — and gid 20 in this Debian base is
# `dialout`. The old else-branch ran a bare `groupadd -g 20 runner`, which
# fails with "GID '20' already exists", exit 4, aborting the whole RUN. Since
# both scripts are `set -euo pipefail`, the build failure aborted them too:
# on a Mac the container could not be built at all, so neither the runner nor
# the pre-submission gate would start. `macbook-air-m1` is a real machine in
# this fleet and its first ./docker/run.sh died here.
#
# gid 100 (`users`) does the same thing to Linux hosts that use it as a primary
# group. The whole range below 1000 is Debian system groups, so "the host's gid
# is free in the image" was never a safe assumption.
#
# Reusing a taken gid is harmless here: the group only decides who owns files,
# the corpus mounts read-only, and the container is disposable. Failing to
# build is not harmless.
#
# The cosmetic `groupmod -n runner` is gone with it — renaming the image's
# `dialout` group to `runner` to make one label prettier is worse than leaving
# a gid with an unexpected name.
ARG UID=1000
ARG GID=1000
RUN if getent passwd "${UID}" >/dev/null; then \
        old="$(getent passwd "${UID}" | cut -d: -f1)"; \
        [ "$old" = runner ] || usermod -l runner -d /home/runner -m "$old"; \
    else \
        getent group "${GID}" >/dev/null 2>&1 || groupadd -g "${GID}" runner; \
        useradd -m -u "${UID}" -g "${GID}" -s /bin/bash runner; \
    fi \
 && id runner \
 && mkdir -p /home/runner && chown "${UID}:${GID}" /home/runner

USER runner
ENV HOME=/home/runner
WORKDIR /home/runner

# The corpus is bind-mounted read-only at /home/runner/.claude. A tool that
# insists on writing gets a writable overlay elsewhere, never the records.
ENV npm_config_cache=/tmp/npm
ENV NPM_CONFIG_UPDATE_NOTIFIER=false

ENTRYPOINT ["/bin/bash", "-lc"]
CMD ["ls -la ~/.claude/projects | head; echo; echo 'projects:'; ls ~/.claude/projects | wc -l"]
