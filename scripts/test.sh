#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
source .venv/bin/activate
pytest
politybench benchmark-smoke --fidelity F0 --seeds 2
politybench calibrate-smoke
