#!/bin/sh
DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHONPATH="$DIR/src" exec python3 -m depgraph "$@"
