#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PICO_DIR="$SCRIPT_DIR/pico"
PORT="${1:-}"

# --- helpers ---------------------------------------------------------------

red()   { printf '\033[1;31m%s\033[0m\n' "$*"; }
green() { printf '\033[1;32m%s\033[0m\n' "$*"; }
cyan()  { printf '\033[1;36m%s\033[0m\n' "$*"; }

die() { red "ERROR: $*" >&2; exit 1; }

MPREMOTE="uv run --group deploy mpremote"

# --- preflight -------------------------------------------------------------

command -v uv &>/dev/null || die "uv not found. Install: https://docs.astral.sh/uv/"

# Auto-detect port if not supplied
if [[ -z "$PORT" ]]; then
    PORT=$(ls /dev/cu.usbmodem* 2>/dev/null | head -1) \
        || die "No Pico serial port found. Is the board connected via USB?"
    [[ -n "$PORT" ]] || die "No Pico serial port found. Is the board connected via USB?"
fi

cyan "Board port: $PORT"

# Verify pico source directory exists
[[ -d "$PICO_DIR" ]] || die "pico/ directory not found at $PICO_DIR"

# --- deploy ----------------------------------------------------------------

cyan "Deploying pico/ files to board..."

for file in "$PICO_DIR"/*.py; do
    name="$(basename "$file")"
    # Skip the secrets template -- don't overwrite a real secrets.py on the board
    if [[ "$name" == "secrets_template.py" ]]; then
        continue
    fi
    printf '  %s -> :%s\n' "$name" "$name"
    $MPREMOTE connect "$PORT" cp "$file" :"$name"
done

green "All files copied."

# --- reset -----------------------------------------------------------------

cyan "Soft-resetting board..."
$MPREMOTE connect "$PORT" reset

green "Deploy complete! Board is running the new code."
