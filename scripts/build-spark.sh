#!/usr/bin/env bash
# Rebuilds www/spark.js — the only generated file in the repo.
#
# The app has no build step and does not want one. This is the exception:
# @buildonspark/spark-sdk is a 23-dependency npm package whose browser entry
# imports sibling chunks, so it cannot simply be copied in. Run this when you
# want a newer SDK, commit the result, and go back to editing index.html by
# hand.
#
#   ./scripts/build-spark.sh            # current pinned version
#   SPARK_VERSION=0.13.0 ./scripts/build-spark.sh
#
# Needs node and npm. Takes about a minute, most of it npm install.
set -euo pipefail

SPARK_VERSION="${SPARK_VERSION:-0.12.0}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/www/spark.js"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

echo "Building Spark SDK $SPARK_VERSION -> www/spark.js"
cd "$WORK"
npm init -y >/dev/null
npm install --no-audit --no-fund --silent \
  "@buildonspark/spark-sdk@$SPARK_VERSION" esbuild >/dev/null

# Only the wallet surface the app actually calls. Everything else the SDK
# exports — token operations, on-chain exits, attestation — is tree-shaken.
cat > entry.mjs <<'EOF'
import { SparkWallet } from "@buildonspark/spark-sdk";
globalThis.Spark = { SparkWallet, ready: true };
EOF

# A classic script rather than a module: Capacitor and GitHub Pages would both
# serve a module fine, but a plain script also works from file://, which is how
# the app is opened during development and by the test harness.
npx esbuild entry.mjs \
  --bundle --format=iife --minify --target=es2020 \
  --outfile="$OUT" --log-level=warning

SIZE=$(wc -c < "$OUT")
echo "www/spark.js  $(( SIZE / 1024 )) KiB"
echo
echo "Remember to bump CACHE in www/sw.js so installed copies pick it up."
