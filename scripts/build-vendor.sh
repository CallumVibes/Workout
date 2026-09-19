#!/usr/bin/env bash
# Rebuilds the two generated files in www/. Everything else in this repo is
# hand-edited and stays that way.
#
#   www/nostr.js   nostr-tools, for bunker (NIP-46) sign-in     ~100 KB
#   www/spark.js   the Spark SDK, for the zapping wallet        ~6 MB
#
# Neither is loaded at startup. nostr.js is fetched when somebody signs in
# with a bunker, spark.js when somebody opens the wallet; anyone who does
# neither downloads neither.
#
#   ./scripts/build-vendor.sh              # both
#   ./scripts/build-vendor.sh nostr        # just one
#   SPARK_VERSION=0.13.0 ./scripts/build-vendor.sh spark
#
# Needs node and npm. A minute or two, most of it npm install.
set -euo pipefail

SPARK_VERSION="${SPARK_VERSION:-0.12.0}"
NOSTR_VERSION="${NOSTR_VERSION:-2.25.2}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WHICH="${1:-both}"

build() {
  local name="$1" pkg="$2" entry="$3" out="$ROOT/www/$name.js"
  local work; work="$(mktemp -d)"
  echo "Building $pkg -> www/$name.js"
  (
    cd "$work"
    npm init -y >/dev/null
    npm install --no-audit --no-fund --silent "$pkg" esbuild >/dev/null
    printf '%s\n' "$entry" > entry.mjs
    # A classic script rather than a module: Capacitor and GitHub Pages would
    # both serve a module fine, but a plain script also works from file://,
    # which is how the app is opened in development and by the tests.
    npx esbuild entry.mjs \
      --bundle --format=iife --minify --target=es2020 \
      --outfile="$out" --log-level=warning
  )
  rm -rf "$work"
  echo "  www/$name.js  $(( $(wc -c < "$out") / 1024 )) KiB"
}

NOSTR_ENTRY="import { BunkerSigner, parseBunkerInput } from 'nostr-tools/nip46';
import { SimplePool } from 'nostr-tools/pool';
import { generateSecretKey, getPublicKey } from 'nostr-tools/pure';
import { npubEncode, decode as nip19decode } from 'nostr-tools/nip19';
globalThis.NostrTools = { BunkerSigner, parseBunkerInput, SimplePool,
  generateSecretKey, getPublicKey, npubEncode, nip19decode, ready: true };"

# Only the wallet surface the app calls; the rest of the SDK is tree-shaken.
SPARK_ENTRY="import { SparkWallet } from '@buildonspark/spark-sdk';
globalThis.Spark = { SparkWallet, ready: true };"

case "$WHICH" in
  nostr) build nostr "nostr-tools@$NOSTR_VERSION" "$NOSTR_ENTRY" ;;
  spark) build spark "@buildonspark/spark-sdk@$SPARK_VERSION" "$SPARK_ENTRY" ;;
  both)
    build nostr "nostr-tools@$NOSTR_VERSION" "$NOSTR_ENTRY"
    build spark "@buildonspark/spark-sdk@$SPARK_VERSION" "$SPARK_ENTRY"
    ;;
  *) echo "usage: $0 [nostr|spark|both]" >&2; exit 1 ;;
esac

echo
echo "Remember to bump CACHE in www/sw.js so installed copies pick it up."
