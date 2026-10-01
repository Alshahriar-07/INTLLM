#!/usr/bin/env bash
# INTLLM installer for Linux and macOS.
#
# Usage:
#   curl -fsSL https://intllm.vercel.app/install.sh | bash
#
# Environment overrides:
#   INTLLM_REPO         GitHub repo (default: Alshahriar-07/INTLLM)
#   INTLLM_VERSION      Release tag or version (default: latest)
#   INTLLM_HOME         Install root (default: ~/.intllm)
#   INTLLM_BIN_DIR      Wrapper directory (default: ~/.local/bin)
#   INTLLM_NO_PATH_EDIT Set to 1 to skip shell rc PATH edits
#
# The script downloads a release artifact, verifies its SHA256 against the
# published SHA256.txt, installs it into an isolated virtual environment and
# exposes an `intllm` command. It never installs unrelated software.
set -euo pipefail

REPO="${INTLLM_REPO:-Alshahriar-07/INTLLM}"
VERSION="${INTLLM_VERSION:-latest}"
HOME_DIR="${INTLLM_HOME:-$HOME/.intllm}"
BIN_DIR="${INTLLM_BIN_DIR:-$HOME/.local/bin}"
VENV_DIR="$HOME_DIR/venv"

C_RESET=""; C_DIM=""; C_ERR=""
if [ -t 1 ]; then
  C_RESET=$'\033[0m'; C_DIM=$'\033[2m'; C_ERR=$'\033[31m'
fi

info() { printf '%s\n' "$1"; }
dim()  { printf '%s%s%s\n' "$C_DIM" "$1" "$C_RESET"; }
fail() { printf '%sINTLLM install failed: %s%s\n' "$C_ERR" "$1" "$C_RESET" >&2; exit 1; }

need() {
  command -v "$1" >/dev/null 2>&1 || fail "required command not found: $1"
}

need curl
need uname
need python3

# --- Platform detection -----------------------------------------------------
OS="$(uname -s)"
ARCH="$(uname -m)"
case "$OS" in
  Linux|Darwin) : ;;
  *) fail "unsupported operating system: $OS (use install.ps1 on Windows)" ;;
esac
case "$ARCH" in
  x86_64|amd64|aarch64|arm64) : ;;
  *) fail "unsupported architecture: $ARCH" ;;
esac

info "INTLLM installer"
dim "  platform: $OS ($ARCH)"

# --- Python version check ---------------------------------------------------
PYTHON_VERSION="$("python3" -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
if [ "$(printf '%s\n' "3.11" "$PYTHON_VERSION" | sort -V | head -n1)" != "3.11" ]; then
  fail "Python 3.11+ is required (found $PYTHON_VERSION)"
fi
dim "  python:   $PYTHON_VERSION"

# --- Resolve release version and download base ------------------------------
if [ "$VERSION" = "latest" ]; then
  dim "  resolving latest release..."
  TAG="$(curl -fsSL "https://api.github.com/repos/$REPO/releases/latest" \
    | grep -m1 '"tag_name"' | sed -E 's/.*"tag_name"[[:space:]]*:[[:space:]]*"([^"]+)".*/\1/')"
  [ -n "${TAG:-}" ] || fail "could not resolve the latest release for $REPO"
  BASE_URL="https://github.com/$REPO/releases/latest/download"
else
  TAG="$VERSION"
  case "$TAG" in v*) : ;; *) TAG="v$TAG" ;; esac
  BASE_URL="https://github.com/$REPO/releases/download/$TAG"
fi
VERSION_NUM="${TAG#v}"
WHEEL="intllm-${VERSION_NUM}-py3-none-any.whl"
dim "  release:  $TAG"

# --- Download + verify ------------------------------------------------------
TMP_DIR="$(mktemp -d)"
cleanup() { rm -rf "$TMP_DIR"; }
trap cleanup EXIT

download() {
  local name="$1"
  curl -fsSL --retry 3 -o "$TMP_DIR/$name" "$BASE_URL/$name" \
    || fail "failed to download $name from $BASE_URL"
}

download "SHA256.txt"
download "$WHEEL"

expected="$(grep -E "[[:space:]]${WHEEL}\$" "$TMP_DIR/SHA256.txt" | awk '{print $1}' | head -n1 || true)"
[ -n "$expected" ] || fail "SHA256.txt does not list $WHEEL"

if command -v sha256sum >/dev/null 2>&1; then
  actual="$(sha256sum "$TMP_DIR/$WHEEL" | awk '{print $1}')"
else
  actual="$(shasum -a 256 "$TMP_DIR/$WHEEL" | awk '{print $1}')"
fi
[ "$expected" = "$actual" ] || fail "SHA256 mismatch for $WHEEL (expected $expected, got $actual)"
dim "  checksum: verified"

# --- Install ----------------------------------------------------------------
mkdir -p "$HOME_DIR" "$BIN_DIR"
info "Installing to $HOME_DIR ..."

if [ -d "$VENV_DIR" ]; then
  dim "  reusing existing virtual environment"
else
  python3 -m venv "$VENV_DIR" || fail "could not create a virtual environment"
fi

"$VENV_DIR/bin/python" -m pip install --quiet --upgrade pip >/dev/null 2>&1 || true
"$VENV_DIR/bin/python" -m pip install --quiet --force-reinstall "$TMP_DIR/$WHEEL" \
  || fail "pip install of $WHEEL failed"

# Wrapper so `intllm` resolves without activating the venv.
cat > "$BIN_DIR/intllm" <<EOF
#!/usr/bin/env bash
exec "$VENV_DIR/bin/python" -m app.cli "\$@"
EOF
chmod +x "$BIN_DIR/intllm"

# --- PATH -------------------------------------------------------------------
if [ "${INTLLM_NO_PATH_EDIT:-0}" != "1" ]; then
  case ":$PATH:" in
    *":$BIN_DIR:"*) : ;;
    *)
      for rc in "$HOME/.bashrc" "$HOME/.zshrc" "$HOME/.profile"; do
        if [ -f "$rc" ] && ! grep -q "$BIN_DIR" "$rc" 2>/dev/null; then
          printf '\n# INTLLM\nexport PATH="%s:$PATH"\n' "$BIN_DIR" >> "$rc"
          dim "  added $BIN_DIR to PATH in $(basename "$rc")"
        fi
      done
      ;;
  esac
fi

# --- Verify -----------------------------------------------------------------
INSTALLED_VERSION="$("$BIN_DIR/intllm" --version 2>/dev/null || true)"
[ -n "$INSTALLED_VERSION" ] || fail "installation verification failed (intllm --version produced no output)"

info ""
info "INTLLM installed successfully ($INSTALLED_VERSION)."
info ""
info "Next steps:"
info "  intllm doctor    # check PostgreSQL and Ollama readiness"
info "  intllm           # start the local runtime and open the web UI"
info ""
if ! printf '%s' ":$PATH:" | grep -q ":$BIN_DIR:"; then
  info "Add this to your shell profile if 'intllm' is not found:"
  info "  export PATH=\"$BIN_DIR:\$PATH\""
fi
