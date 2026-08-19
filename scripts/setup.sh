#!/usr/bin/env bash
# RootCause MCP - Linux / macOS / WSL Setup & Installation Script
# Usage: ./scripts/setup.sh [--profile all|clinical|rca|condensed] [--target vscode|copilot|claude|cline|all]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo "==========================================================================="
echo "🏥 RootCause MCP Server - One-Click Setup & Installer (Linux/macOS)"
echo "==========================================================================="

PROFILE="all"
RESPONSE_MODE="compact"
TARGET="all"
EXTRA_ARGS=()

while [[ $# -gt 0 ]]; do
  case $1 in
    --profile)
      PROFILE="$2"
      shift 2
      ;;
    --response-mode)
      RESPONSE_MODE="$2"
      shift 2
      ;;
    --target)
      TARGET="$2"
      shift 2
      ;;
    --skip-tests)
      EXTRA_ARGS+=("--skip-tests")
      shift
      ;;
    --skip-trial)
      EXTRA_ARGS+=("--skip-trial")
      shift
      ;;
    *)
      EXTRA_ARGS+=("$1")
      shift
      ;;
  esac
done

# 1. Check / Install uv
echo ""
echo "[1/5] Checking uv package manager..."
if ! command -v uv &> /dev/null; then
    if [ -f "$HOME/.local/bin/uv" ]; then
        UV_PATH="$HOME/.local/bin/uv"
    elif [ -f "$HOME/.cargo/bin/uv" ]; then
        UV_PATH="$HOME/.cargo/bin/uv"
    else
        echo " -> uv not found. Installing uv via official installer..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
        UV_PATH="$HOME/.local/bin/uv"
    fi
else
    UV_PATH="$(command -v uv)"
fi

if [ ! -x "$UV_PATH" ]; then
    echo "ERROR: uv executable was not found after installation: $UV_PATH" >&2
    exit 1
fi
export PATH="$(dirname "$UV_PATH"):$PATH"

echo " -> Using uv: $UV_PATH"

# 2. Sync Python virtual environment
echo ""
echo "[2/5] Initializing virtual environment & syncing dependencies..."
"$UV_PATH" sync --locked --all-extras
echo " -> Dependencies synchronized successfully."

# 3. Run Universal Installer Script
echo ""
echo "[3/5] Configuring MCP client harness & host registrations..."
"$UV_PATH" run --locked python scripts/install.py \
    --profile "$PROFILE" \
    --response-mode "$RESPONSE_MODE" \
    --target "$TARGET" \
    "${EXTRA_ARGS[@]:+${EXTRA_ARGS[@]}}"

# 4. Validate the generated config and production stdio handshake
echo ""
echo "[4/5] Validating MCP config and stdio discovery..."
case "$TARGET" in
  vscode|copilot)
    DOCTOR_CONFIG="$TARGET"
    ;;
  *)
    DOCTOR_CONFIG="all"
    ;;
esac
"$UV_PATH" run --locked python scripts/mcp_doctor.py --config "$DOCTOR_CONFIG"

# 5. Summary
echo ""
echo "==========================================================================="
echo "🎉 Setup completed successfully!"
echo "   Server command: uv run --locked rootcause-mcp"
echo "   Profile:        $PROFILE"
echo "   Response Mode:  $RESPONSE_MODE"
echo "   Reload the remote VS Code window so its extension host inherits PATH."
echo "   For WSL/SSH/containers, run this setup inside that remote environment."
echo "==========================================================================="
