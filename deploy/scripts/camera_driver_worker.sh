#!/usr/bin/env bash
set -euo pipefail
root="$(cd -- "$(dirname -- "$0")/../.." && pwd)"
exec bash "$root/deploy/scripts/start_gemini2.sh"
