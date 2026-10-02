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
#   INTLLM_NO_ANIMATION Set to 1 for plain output (CI / non-interactive)
#
# The script downloads a release artifact, verifies its SHA256 against the
# published SHA256.txt, installs it into an isolated virtual environment and
# exposes an `intllm` command. Progress reflects the real operation in flight.
set -euo pipefail

REPO="${INTLLM_REPO:-Alshahriar-07/INTLLM}"
VERSION="${INTLLM_VERSION:-latest}"
HOME_DIR="${INTLLM_HOME:-$HOME/.intllm}"
BIN_DIR="${INTLLM_BIN_DIR:-$HOME/.local/bin}"
VENV_DIR="$HOME_DIR/venv"

# --- Presentation -----------------------------------------------------------
if [ -t 1 ] && [ "${INTLLM_NO_ANIMATION:-0}" != "1" ]; then
  INTERACTIVE=1
else
  INTERACTIVE=0
fi

C_RESET=""; C_DIM=""; C_GRAY=""; C_CYAN=""; C_GREEN=""; C_YELLOW=""; C_ERR=""; C_WHITE=""
if [ "$INTERACTIVE" = "1" ]; then
  C_RESET=$'\033[0m'; C_DIM=$'\033[2m'; C_GRAY=$'\033[90m'
  C_CYAN=$'\033[36m'; C_GREEN=$'\033[32m'; C_YELLOW=$'\033[33m'; C_ERR=$'\033[31m'
  C_WHITE=$'\033[97m'
fi

CHECK="${C_GREEN}$(printf '\u2713')${C_RESET}"
CROSS="${C_ERR}$(printf '\u2717')${C_RESET}"
ARROW="${C_GRAY}>${C_RESET}"

banner() {
  printf '\n'
  printf '%s\n' "${C_CYAN}  ██╗███╗   ██╗████████╗██╗     ██╗     ███╗   ███╗${C_RESET}"
  printf '%s\n' "${C_CYAN}  ██║████╗  ██║╚══██╔══╝██║     ██║     ████╗ ████║${C_RESET}"
  printf '%s\n' "${C_CYAN}  ██║██╔██╗ ██║   ██║   ██║     ██║     ██╔████╔██║${C_RESET}"
  printf '%s\n' "${C_CYAN}  ██║██║╚██╗██║   ██║   ██║     ██║     ██║╚██╔╝██║${C_RESET}"
  printf '%s\n' "${C_CYAN}  ██║██║ ╚████║   ██║   ███████╗███████╗██║ ╚═╝ ██║${C_RESET}"
  printf '%s\n' "${C_CYAN}  ╚═╝╚═╝  ╚═══╝   ╚═╝   ╚══════╝╚══════╝╚═╝     ╚═╝${C_RESET}"
  printf '%s\n\n' "${C_GRAY}  Local Intelligence Runtime${C_RESET}"
}

step()  { printf '  %s %s …\n' "$ARROW" "$1"; }
done_() { printf '    %s %s %s\n' "$CHECK" "$1" "${C_DIM}${2:-}${C_RESET}"; }
info()  { printf '      %s\n' "${C_GRAY}$1${C_RESET}"; }
warn()  { printf '    %s %s\n' "${C_YELLOW}!${C_RESET}" "$1"; }
fail()  {
  printf '\n  %s INTLLM install failed: %s\n' "$CROSS" "$1" >&2
  exit 1
}

need() { command -v "$1" >/dev/null 2>&1 || fail "required command not found: $1"; }

# --- Platform detection -----------------------------------------------------
banner
step "Detecting system"
need curl
need uname
need python3

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
PYTHON_VERSION="$("python3" -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
if [ "$(printf '%s\n' "3.11" "$PYTHON_VERSION" | sort -V | head -n1)" != "3.11" ]; then
  fail "Python 3.11+ is required (found $PYTHON_VERSION)"
fi
done_ "System" "$OS ($ARCH), Python $PYTHON_VERSION"

# --- Resolve release --------------------------------------------------------
step "Preparing installation"
if [ "$VERSION" = "latest" ]; then
  TAG="$(curl -fsSL -H 'User-Agent: INTLLM-Installer' \
    "https://api.github.com/repos/$REPO/releases/latest" \
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
done_ "Release" "$TAG"

# --- Download helpers -------------------------------------------------------
TMP_DIR="$(mktemp -d)"
cleanup() { rm -rf "$TMP_DIR"; }
trap cleanup EXIT INT TERM

download() {
  local name="$1"
  local url="$BASE_URL/$name"
  local target="$TMP_DIR/$name"
  if [ "$INTERACTIVE" = "1" ]; then
    info "downloading $name"
    curl -fL -# --retry 3 --retry-delay 1 -o "$target" "$url" \
      || fail "failed to download $name from $BASE_URL"
    printf '\033[1A\033[2K'
  else
    curl -fsSL --retry 3 --retry-delay 1 -o "$target" "$url" \
      || fail "failed to download $name from $BASE_URL"
  fi
}

sha256_of() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
  else
    shasum -a 256 "$1" | awk '{print $1}'
  fi
}

verify() {
  local name="$1"
  local expected actual
  expected="$(grep -E "[[:space:]]${name}\$" "$TMP_DIR/SHA256.txt" | awk '{print $1}' | head -n1 || true)"
  [ -n "$expected" ] || fail "SHA256.txt does not list $name"
  actual="$(sha256_of "$TMP_DIR/$name")"
  [ "$expected" = "$actual" ] || fail "SHA256 mismatch for $name (expected $expected, got $actual)"
}

# --- Download + verify ------------------------------------------------------
step "Downloading release manifest"
download "SHA256.txt"
done_ "Manifest" "SHA256.txt"

step "Downloading package"
download "$WHEEL"
step "Verifying package"
verify "$WHEEL"
done_ "Verified" "$WHEEL (SHA256)"

# --- Install ----------------------------------------------------------------
step "Installing runtime"
mkdir -p "$HOME_DIR" "$BIN_DIR"
if [ -d "$VENV_DIR" ]; then
  info "reusing existing virtual environment"
else
  python3 -m venv "$VENV_DIR" || fail "could not create a virtual environment"
fi
"$VENV_DIR/bin/python" -m pip install --quiet --upgrade pip >/dev/null 2>&1 || true
"$VENV_DIR/bin/python" -m pip install --quiet --force-reinstall "$TMP_DIR/$WHEEL" \
  || fail "pip install of $WHEEL failed"
done_ "Runtime installed" "$HOME_DIR"

step "Installing intllm command"
cat > "$BIN_DIR/intllm" <<EOF
#!/usr/bin/env bash
exec "$VENV_DIR/bin/python" -m app.cli "\$@"
EOF
chmod +x "$BIN_DIR/intllm"
done_ "intllm command installed" "$BIN_DIR/intllm"

# --- PATH -------------------------------------------------------------------
step "Configuring PATH"
if [ "${INTLLM_NO_PATH_EDIT:-0}" = "1" ]; then
  info "skipped (INTLLM_NO_PATH_EDIT=1)"
elif printf '%s' ":$PATH:" | grep -q ":$BIN_DIR:"; then
  done_ "PATH already configured"
else
  for rc in "$HOME/.bashrc" "$HOME/.zshrc" "$HOME/.profile"; do
    if [ -f "$rc" ] && ! grep -qF "$BIN_DIR" "$rc" 2>/dev/null; then
      printf '\n# INTLLM\nexport PATH="%s:$PATH"\n' "$BIN_DIR" >> "$rc"
    fi
  done
  done_ "PATH configured in shell profile"
fi

# --- Verify -----------------------------------------------------------------
step "Finalizing"
INSTALLED_VERSION="$("$BIN_DIR/intllm" --version 2>/dev/null || true)"
[ -n "$INSTALLED_VERSION" ] || fail "installation verification failed (intllm --version produced no output)"
done_ "Verified" "$INSTALLED_VERSION"

printf '\n  %s INTLLM installed successfully.\n\n' "$CHECK"
printf '%s\n' "  Run:"
printf '      %s\n' "intllm                # start the runtime and open the web UI"
printf '      %s\n' "intllm doctor         # check PostgreSQL and Ollama readiness"
printf '      %s\n' "intllm --version      # print the installed version"
printf '\n'
if ! printf '%s' ":$PATH:" | grep -q ":$BIN_DIR:"; then
  warn "'intllm' may not be on PATH yet. Add this to your shell profile:"
  printf '      export PATH="%s:$PATH"\n' "$BIN_DIR"
fi
printf '\n'
