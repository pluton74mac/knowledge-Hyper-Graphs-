#!/usr/bin/env bash
# Start the three servers of P1 outside the repository (research 01 §2, §4, §5; ruling 10 on D10).
#
#   P1_ROOT=/a/scratch/directory ./start-servers.sh [postgres] [neo4j] [typedb]     # default: all three
#
# Engines and data live under P1_ROOT, never in the repository. Each download is pinned by version and checked
# against the sha256 it had when research 01 fetched it (2026-09-25). The script is idempotent: a checked file is
# not fetched again, an unpacked engine is not unpacked again, an initialised cluster is not initialised again, and a
# server whose port answers is left running. Then:
#
#   export KHG_BAKEOFF_POSTGRES="host=127.0.0.1 port=5418 user=postgres"
#   export KHG_BAKEOFF_NEO4J=bolt://127.0.0.1:7687
#   export KHG_BAKEOFF_TYPEDB=127.0.0.1:1729
#
# The clients are pinned in khg-bakeoff/pyproject.toml (pip install "./khg-bakeoff[all,dev]"): psycopg 3.3.6,
# neo4j 6.3.1, typedb-driver 3.13.6, pyoxigraph 0.5.11. SQLite is the Python standard library's (3.45.1 here).
# Neo4j needs Java 21 on PATH; about 1.3 GB of RAM at the heap and page cache below.
set -euo pipefail

ROOT=${P1_ROOT:?set P1_ROOT to a directory outside the repository}
mkdir -p "$ROOT"

PG_VERSION=18.6.0
PG_URL=https://repo1.maven.org/maven2/io/zonky/test/postgres/embedded-postgres-binaries-linux-amd64/$PG_VERSION/embedded-postgres-binaries-linux-amd64-$PG_VERSION.jar
PG_SHA256=008ee189eaa7ca2b58bd01dd950291e638b998392cf982297acd4779ec898ac1
PG_PORT=5418

NEO4J_VERSION=2026.09.0
NEO4J_URL=https://dist.neo4j.org/neo4j-community-$NEO4J_VERSION-unix.tar.gz
NEO4J_SHA256=cdaa0905d9a533bbbc474d239c268f69978982eb5ca3177666c04c9792d1c399
NEO4J_PORT=7687

TYPEDB_VERSION=3.13.6
TYPEDB_URL=https://repo.typedb.com/public/public-release/raw/names/typedb-all-linux-x86_64/versions/$TYPEDB_VERSION/typedb-all-linux-x86_64-$TYPEDB_VERSION.tar.gz
TYPEDB_SHA256=3411c72ad5e38d85dd4663b8620d3198bbd38e69e83fdcc0a08cbee57fea8913
TYPEDB_PORT=1729

# fetch URL FILE SHA256: download unless FILE already has SHA256 (Maven Central answered 429 once: retry)
fetch() {
  local url=$1 file=$2 sum=$3
  if [ -f "$file" ] && echo "$sum  $file" | sha256sum -c --status; then
    return 0
  fi
  curl -sSL --retry 5 --retry-delay 4 -o "$file" "$url"
  echo "$sum  $file" | sha256sum -c
}

listening() { (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null; }

wait_for() {
  local port=$1 name=$2 i
  for i in $(seq 1 120); do
    if listening "$port"; then echo "$name: listening on 127.0.0.1:$port"; return 0; fi
    sleep 1
  done
  echo "$name: not listening on 127.0.0.1:$port after 120 s" >&2
  return 1
}

# initdb refuses to run as root; as root, a user namespace maps root to uid 1000 (research 01 §2.1)
as_user() {
  if [ "$(id -u)" = 0 ]; then unshare --user --map-user=1000 --map-group=1000 "$@"; else "$@"; fi
}

postgres() {
  local dir=$ROOT/pg18
  mkdir -p "$dir"
  fetch "$PG_URL" "$dir/pg.jar" "$PG_SHA256"
  if [ ! -x "$dir/dist/bin/postgres" ]; then
    (cd "$dir" && unzip -oq pg.jar && mkdir -p dist && tar xJf postgres-linux-x86_64.txz -C dist)
  fi
  if [ ! -f "$dir/data/PG_VERSION" ]; then
    as_user "$dir/dist/bin/initdb" -D "$dir/data" --locale=C --encoding=UTF8 -U postgres --auth=trust > "$dir/initdb.out"
  fi
  if listening "$PG_PORT"; then echo "postgres: already listening on $PG_PORT"; return 0; fi
  # TCP only: a Unix socket under a long scratch path exceeds the 107-byte limit
  as_user "$dir/dist/bin/pg_ctl" -D "$dir/data" -l "$dir/server.log" \
    -o "-p $PG_PORT -c unix_socket_directories='' -c listen_addresses=127.0.0.1 -c shared_buffers=256MB" start
  wait_for "$PG_PORT" postgres
}

neo4j() {
  local dir=$ROOT/neo4j home
  home=$dir/neo4j-community-$NEO4J_VERSION
  mkdir -p "$dir"
  fetch "$NEO4J_URL" "$dir/neo4j-community-$NEO4J_VERSION-unix.tar.gz" "$NEO4J_SHA256"
  if [ ! -d "$home" ]; then
    tar xzf "$dir/neo4j-community-$NEO4J_VERSION-unix.tar.gz" -C "$dir"
  fi
  # appended once: a repeated key makes the configuration validation fail (research 01 §4.1)
  if ! grep -q '^# P1 probe settings' "$home/conf/neo4j.conf"; then
    cat >> "$home/conf/neo4j.conf" <<'EOF'
# P1 probe settings
dbms.security.auth_enabled=false
server.default_listen_address=127.0.0.1
server.bolt.listen_address=127.0.0.1:7687
server.http.listen_address=127.0.0.1:7474
server.memory.heap.initial_size=512m
server.memory.heap.max_size=1g
server.memory.pagecache.size=256m
dbms.usage_report.enabled=false
EOF
  fi
  if listening "$NEO4J_PORT"; then echo "neo4j: already listening on $NEO4J_PORT"; return 0; fi
  (cd "$home" && nohup ./bin/neo4j console > "$dir/console.out" 2>&1 &)
  wait_for "$NEO4J_PORT" neo4j
}

typedb() {
  local dir=$ROOT/typedb home
  home=$dir/typedb-all-linux-x86_64-$TYPEDB_VERSION
  mkdir -p "$dir/data" "$dir/logs"
  fetch "$TYPEDB_URL" "$dir/typedb-all-linux-x86_64.tar.gz" "$TYPEDB_SHA256"
  if [ ! -d "$home" ]; then
    tar xzf "$dir/typedb-all-linux-x86_64.tar.gz" -C "$dir"
  fi
  # server/config.yml with: listen on 127.0.0.1, data and logs under $dir, diagnostics reporting off
  cat > "$dir/config.yml" <<EOF
server:
    listen-address: 127.0.0.1:$TYPEDB_PORT
    advertise-address:
    http:
        enabled: true
        listen-address: 127.0.0.1:8000
        advertise-address:
    admin:
        enabled: false
        socket-path:

    authentication:
        token-expiration-seconds: 5000

    encryption:
        enabled: false
        certificate:
        certificate-key:
        ca-certificate:

storage:
    data-directory: "$dir/data"
    rocksdb:
        cache-size: 1gb
        write-buffers-limit: 512mb
    mvcc:
        cleanup:
            enabled: false
            strategy: eager

logging:
    directory: "$dir/logs"

diagnostics:
    monitoring:
        enabled: true
        port: 4104
    reporting:
        metrics: false
        errors: false
EOF
  if listening "$TYPEDB_PORT"; then echo "typedb: already listening on $TYPEDB_PORT"; return 0; fi
  (nohup "$home/typedb" server --config "$dir/config.yml" > "$dir/server.out" 2>&1 &)
  wait_for "$TYPEDB_PORT" typedb
}

servers=("$@")
[ ${#servers[@]} -eq 0 ] && servers=(postgres neo4j typedb)
for s in "${servers[@]}"; do
  case $s in
    postgres|neo4j|typedb) "$s" ;;
    *) echo "unknown server: $s (postgres, neo4j, typedb)" >&2; exit 2 ;;
  esac
done
