#!/usr/bin/env bash
# Build the two optional external hypertree-decomposition solvers of khg-width (P6 DESIGN §4.5) from pinned commits.
#
# Usage:  scripts/build-solvers.sh [DEST]
#
#   DEST defaults to ${XDG_CACHE_HOME:-~/.cache}/khg-width/solvers. A DEST inside a git working tree is refused:
#   binaries and sources never enter the repository.
#
# Needs git and Go (1.24.7 probed). GOTOOLCHAIN=local, so Go never downloads another toolchain. The module and build
# caches live under DEST/go unless GOMODCACHE / GOCACHE are set.
#
# Result:
#   DEST/src/<tool>/          the checkouts (BalancedGo 872c662c…, log-k-decomp 5e021dd4…)
#   DEST/bin/BalancedGo, DEST/bin/log-k-decomp
#   DEST/solvers.json         commit, describe, Go version, binary sha256 and licence per tool
#
# khg-width finds the binaries through KHG_WIDTH_BALANCEDGO / KHG_WIDTH_LOGK, then KHG_WIDTH_SOLVERS=DEST, then the
# default DEST, then PATH.
set -euo pipefail

BALANCEDGO_URL="https://github.com/cem-okulmus/BalancedGo"
BALANCEDGO_COMMIT="872c662c9f409aeb7386f963d2f16b88523ff4bf"   # v1.7.2-2-g872c662, MIT
LOGK_URL="https://github.com/cem-okulmus/log-k-decomp"
LOGK_COMMIT="5e021dd442b028099c30deecc316a906a49a8cb3"         # v1.1.0, MIT

die() { echo "build-solvers: $*" >&2; exit 1; }

DEST="${1:-${XDG_CACHE_HOME:-$HOME/.cache}/khg-width/solvers}"
command -v git >/dev/null || die "git is required"

# refuse a DEST inside a git working tree (the repository, or any other), before anything is created: test the
# nearest existing ancestor
probe="$DEST"
while [ ! -d "$probe" ]; do probe="$(dirname "$probe")"; done
if git -C "$probe" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  die "DEST $DEST is inside a git working tree ($(git -C "$probe" rev-parse --show-toplevel)); choose a directory outside it"
fi
mkdir -p "$DEST"
DEST="$(cd "$DEST" && pwd -P)"

command -v go >/dev/null || die "Go is required (1.24.7 was probed); without it khg-width runs Python-only"
export GOTOOLCHAIN=local
export GOFLAGS="${GOFLAGS:-}"
export GOMODCACHE="${GOMODCACHE:-$DEST/go/mod}"
export GOCACHE="${GOCACHE:-$DEST/go/cache}"
export GOPATH="${GOPATH:-$DEST/go/path}"
GOVERSION="$(go env GOVERSION)"

sha256() { if command -v sha256sum >/dev/null; then sha256sum "$1" | cut -d' ' -f1; else shasum -a 256 "$1" | cut -d' ' -f1; fi; }

checkout() {  # checkout <name> <url> <commit>
  local name="$1" url="$2" commit="$3" dir="$DEST/src/$1"
  if [ ! -d "$dir/.git" ]; then
    rm -rf "$dir"
    git clone --quiet "$url" "$dir"
  fi
  git -C "$dir" fetch --quiet --tags origin || true
  git -C "$dir" -c advice.detachedHead=false checkout --quiet --force "$commit"
  git -C "$dir" clean -fdxq
  [ "$(git -C "$dir" rev-parse HEAD)" = "$commit" ] || die "$name: HEAD is not $commit"
}

build() {  # build <name> <binary>
  local name="$1" bin="$2" dir="$DEST/src/$1"
  mkdir -p "$DEST/bin"
  (cd "$dir" && go build -trimpath -mod=readonly -o "$DEST/bin/$bin" .)
}

smoke() {  # smoke <binary> [flags]: the triangle has hypertree width 2
  local bin="$1"; shift
  local tri="$DEST/b_triangle.hg"
  printf 'E1 (a, b),\nE2 (b, c),\nE3 (a, c).\n' > "$tri"
  local out
  out="$("$DEST/bin/$bin" -graph "$tri" -exact "$@" 2>&1)" || die "$bin: smoke test failed to run"
  echo "$out" | grep -q '^Width:  2$' || die "$bin: smoke test did not report width 2 on b_triangle:
$out"
  echo "$out" | grep -q '^Correct:  true$' || die "$bin: smoke test decomposition not correct"
}

checkout BalancedGo "$BALANCEDGO_URL" "$BALANCEDGO_COMMIT"
checkout log-k-decomp "$LOGK_URL" "$LOGK_COMMIT"
build BalancedGo BalancedGo
build log-k-decomp log-k-decomp
smoke BalancedGo -det
smoke log-k-decomp

entry() {  # entry <name> <binary> <url> <commit> <licence> <source dir>
  local dir="$DEST/src/$6"
  printf '  "%s": {"binary": "bin/%s", "repository": "%s", "commit": "%s", "describe": "%s", "go_version": "%s", "sha256": "%s", "licence": "%s", "smoke_test": "b_triangle width 2"}' \
    "$1" "$2" "$3" "$4" "$(git -C "$dir" describe --tags --always 2>/dev/null || echo unknown)" "$GOVERSION" \
    "$(sha256 "$DEST/bin/$2")" "$5"
}
{
  echo "{"
  echo "  \"format\": \"khg-width-solvers/1\","
  echo "  \"built\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\","
  entry balancedgo BalancedGo "$BALANCEDGO_URL" "$BALANCEDGO_COMMIT" "MIT" BalancedGo; echo ","
  entry logk log-k-decomp "$LOGK_URL" "$LOGK_COMMIT" "MIT" log-k-decomp; echo
  echo "}"
} > "$DEST/solvers.json"

echo "build-solvers: built into $DEST/bin (see $DEST/solvers.json)"
echo "build-solvers: export KHG_WIDTH_SOLVERS=$DEST  (not needed for the default location)"
