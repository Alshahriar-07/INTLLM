# INTLLM installer for Windows (x64).
#
# Usage:
#   irm https://intllm.vercel.app/install.ps1 | iex
#
# Environment overrides:
#   INTLLM_REPO       GitHub repo (default: Alshahriar-07/INTLLM)
#   INTLLM_VERSION    Release tag or version (default: latest)
#   INTLLM_USE_SETUP  Set to 1 to prefer INTLLM-Setup.exe when published
#
# The script downloads a release artifact, verifies its SHA256 against the
# published SHA256.txt, installs INTLLM for the current user and verifies the
# installation. It never installs unrelated software.
[CmdletBinding()]
param(
  [string]$Repo = $(if ($env:INTLLM_REPO) { $env:INTLLM_REPO } else { 'Alshahriar-07/INTLLM' }),
  [string]$Version = $(if ($env:INTLLM_VERSION) { $env:INTLLM_VERSION } else { 'latest' })
)

$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

function Fail([string]$Message) {
  Write-Host "INTLLM install failed: $Message" -ForegroundColor Red
  exit 1
}

Write-Host "INTLLM installer"

# --- Platform detection -----------------------------------------------------
if (-not [Environment]::Is64BitOperatingSystem) {
  Fail "64-bit Windows is required"
}
$arch = $env:PROCESSOR_ARCHITECTURE
if ($arch -ne 'AMD64') {
  Fail "unsupported architecture: $arch (Windows x64/AMD64 is required)"
}
Write-Host "  platform: Windows ($arch)"

# --- Resolve release --------------------------------------------------------
if (-not $Version -or $Version -eq 'latest') {
  Write-Host "  resolving latest release..."
  $release = Invoke-RestMethod -Uri "https://api.github.com/repos/$Repo/releases/latest" -UseBasicParsing
  $tag = $release.tag_name
  $baseUrl = "https://github.com/$Repo/releases/latest/download"
} else {
  $tag = $Version
  if ($tag -notmatch '^v') { $tag = "v$tag" }
  $baseUrl = "https://github.com/$Repo/releases/download/$tag"
}
if (-not $tag) { Fail "could not resolve a release version for $Repo" }
Write-Host "  release:  $tag"

$tmp = Join-Path $env:TEMP ("intllm-" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $tmp | Out-Null

try {
  $shaPath = Join-Path $tmp 'SHA256.txt'
  Invoke-WebRequest -Uri "$baseUrl/SHA256.txt" -OutFile $shaPath -UseBasicParsing
  $shaLines = Get-Content $shaPath

  function Get-ExpectedHash([string]$FileName) {
    foreach ($line in $shaLines) {
      $parts = $line -split '\s+', 2
      if ($parts.Count -eq 2 -and $parts[1].Trim() -eq $FileName) { return $parts[0].Trim() }
    }
    return $null
  }

  function Get-FileHashHex([string]$Path) {
    return (Get-FileHash -Path $Path -Algorithm SHA256).Hash.ToLower()
  }

  function Download-Verified([string]$FileName) {
    $target = Join-Path $tmp $FileName
    Invoke-WebRequest -Uri "$baseUrl/$FileName" -OutFile $target -UseBasicParsing
    $expected = Get-ExpectedHash $FileName
    if (-not $expected) { Fail "SHA256.txt does not list $FileName" }
    $actual = Get-FileHashHex $target
    if ($actual -ne $expected.ToLower()) {
      Fail "SHA256 mismatch for $FileName (expected $expected, got $actual)"
    }
    Write-Host "  checksum: verified ($FileName)"
    return $target
  }

  # Program files live in ...\Programs\INTLLM; INTLLM runtime data is stored
  # separately under %LOCALAPPDATA%\INTLLM by the app and is preserved.
  $installDir = Join-Path $env:LOCALAPPDATA 'Programs\INTLLM'
  $exeName = 'INTLLM.exe'
  $exePath = Join-Path $installDir $exeName

  $setupExpected = Get-ExpectedHash 'INTLLM-Setup.exe'
  $useSetup = ($env:INTLLM_USE_SETUP -eq '1') -and $setupExpected

  if ($useSetup) {
    $setup = Download-Verified 'INTLLM-Setup.exe'
    Write-Host "Installing with INTLLM-Setup.exe ..."
    $proc = Start-Process -FilePath $setup `
      -ArgumentList '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART' -Wait -PassThru
    if ($proc.ExitCode -ne 0) { Fail "INTLLM-Setup.exe exited with code $($proc.ExitCode)" }
    if (-not (Test-Path $exePath)) {
      $candidate = Join-Path $env:LOCALAPPDATA 'Programs\INTLLM\INTLLM.exe'
      if (Test-Path $candidate) { $exePath = $candidate } else { Fail "installer did not place INTLLM.exe where expected" }
    }
  } else {
    $portable = Download-Verified 'INTLLM-windows-x64.exe'
    New-Item -ItemType Directory -Force -Path $installDir | Out-Null
    Copy-Item -Path $portable -Destination $exePath -Force
    Write-Host "Installing to $installDir ..."

    # Add to the per-user PATH (never the machine PATH).
    $userPath = [Environment]::GetEnvironmentVariable('PATH', 'User')
    if (-not $userPath) { $userPath = '' }
    $entries = $userPath -split ';' | Where-Object { $_ -ne '' }
    if ($entries -notcontains $installDir) {
      $newPath = (@($entries) + $installDir) -join ';'
      [Environment]::SetEnvironmentVariable('PATH', $newPath, 'User')
      Write-Host "  added $installDir to the user PATH"
    }

    # Start Menu shortcut.
    try {
      $startMenu = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs'
      $shortcutPath = Join-Path $startMenu 'INTLLM.lnk'
      $shell = New-Object -ComObject WScript.Shell
      $shortcut = $shell.CreateShortcut($shortcutPath)
      $shortcut.TargetPath = $exePath
      $shortcut.WorkingDirectory = $installDir
      $shortcut.Save()
      Write-Host "  created Start Menu shortcut"
    } catch {
      Write-Host "  (could not create Start Menu shortcut: $_)" -ForegroundColor DarkGray
    }
  }

  # --- Verify ---------------------------------------------------------------
  if (-not (Test-Path $exePath)) { Fail "INTLLM.exe was not installed" }
  $installed = & $exePath --version 2>$null
  if (-not $installed) {
    # Console apps may buffer; retry once.
    Start-Sleep -Milliseconds 500
    $installed = & $exePath --version 2>$null
  }
  if (-not $installed) { Fail "installation verification failed (INTLLM.exe --version produced no output)" }

  Write-Host ""
  Write-Host "INTLLM installed successfully ($installed)." -ForegroundColor Green
  Write-Host ""
  Write-Host "Next steps:"
  Write-Host "  INTLLM                # start the local runtime and open the web UI"
  Write-Host "  INTLLM --version      # print the installed version"
  Write-Host ""
  Write-Host "PostgreSQL and Ollama are external local dependencies. Install them"
  Write-Host "separately; INTLLM detects and reports their state at startup."
  Write-Host "Restart your terminal (or sign out/in) so the updated PATH is picked up."
} finally {
  Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
}
