#!/bin/sh
cd "$(dirname "$0")/.." || exit 1
for f in "${1:-examples/npm}"/*.toml; do
    printf '$ ./run.sh --no-color -c %s\n' "$f"
    ./run.sh --no-color -c "$f" 2>&1
    printf '(код выхода %s)\n\n' "$?"
done
