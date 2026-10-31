#!/bin/sh
cd "$(dirname "$0")/.." || exit 1
DIR="${1:-examples/test}"
for f in "$DIR"/*.toml; do
    repo=$(sed -n 's/^repository = "\(.*\)"/\1/p' "$f")
    printf '$ cat %s\n' "$repo"
    cat "$repo"
    printf '$ ./run.sh --no-color -c %s\n' "$f"
    ./run.sh --no-color -c "$f" 2>&1
    printf '(код выхода %s)\n\n' "$?"
done
