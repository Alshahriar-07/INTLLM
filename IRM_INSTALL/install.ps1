# INTLLM installer for Windows (x64).
#
# Usage:
#   irm https://intllm.vercel.app/install.ps1 | iex
#
# Environment overrides:
#   INTLLM_REPO         GitHub repo (default: Alshahriar-07/INTLLM)
#   INTLLM_VERSION      Release tag or version (default: latest)
#   INTLLM_USE_SETUP    Set to 1 to prefer INTLLM-Setup.exe when published
#   INTLLM_NO_PATH_EDIT Set to 1 to skip the per-user PATH update
#   INTLLM_NO_ANIMATION Set to 1 for plain output (CI / non-interactive)
#
# The script downloads a release artifact, verifies its SHA256 against the
# published SHA256.txt, installs INTLLM for the current user, creates the
# `intllm` command + shortcuts, and verifies the installation. Progress shown is
# driven by the real operation in flight; it never simulates work.
[CmdletBinding()]
param(
  [string]$Repo = $(if ($env:INTLLM_REPO) { $env:INTLLM_REPO } else { 'Alshahriar-07/INTLLM' }),
  [string]$Version = $(if ($env:INTLLM_VERSION) { $env:INTLLM_VERSION } else { 'latest' })
)

$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

# --- Presentation -----------------------------------------------------------
$script:Animate = -not ($env:INTLLM_NO_ANIMATION -eq '1') -and $Host.Name -ne 'ServerRemoteHost'
$script:UseColor = $true
try { $null = $Host.UI.RawUI.WindowSize } catch { $script:UseColor = $false }

function C([string]$Text, [string]$Color) {
  if ($script:UseColor) { Write-Host $Text -ForegroundColor $Color } else { Write-Host $Text }
}

function Banner {
  C '' 'Gray'
  C '  +----------------------------------------------+' 'DarkGray'
  C '  |   I N T L L M                                |' 'Cyan'
  C '  |   Local Intelligence Runtime                 |' 'DarkGray'
  C '  +----------------------------------------------+' 'DarkGray'
  C '' 'Gray'
}

function Step([string]$Message) {
  Write-Host ('  ' + [char]0x203A + ' ' + $Message) -NoNewline -ForegroundColor Gray
  C ' ...' 'DarkGray'
}

function Done([string]$Message, [string]$Detail = '') {
  if ($Detail) {
    C ('    ' + [char]0x2713 + ' ' + $Message + ' ' + $Detail) 'Green'
  } else {
    C ('    ' + [char]0x2713 + ' ' + $Message) 'Green'
  }
}

function Info([string]$Message) { C ('      ' + $Message) 'DarkGray' }
function Warn([string]$Message) { C ('    ! ' + $Message) 'Yellow' }
function Fail([string]$Message) {
  C '' 'Gray'
  C ('  ' + [char]0x2717 + ' INTLLM install failed: ' + $Message) 'Red'
  exit 1
}

# --- Platform detection -----------------------------------------------------
Banner

Step 'Detecting system'
if (-not [Environment]::Is64BitOperatingSystem) { Fail '64-bit Windows is required' }
$arch = $env:PROCESSOR_ARCHITECTURE
if ($arch -ne 'AMD64') { Fail "unsupported architecture: $arch (Windows x64/AMD64 is required)" }
Done 'System' "Windows x64 ($arch)"

# --- Resolve release --------------------------------------------------------
Step 'Preparing installation'
$headers = @{ 'User-Agent' = 'INTLLM-Installer' }
if ($Version -eq 'latest' -or -not $Version) {
  try {
    $release = Invoke-RestMethod -Uri "https://api.github.com/repos/$Repo/releases/latest" -Headers $headers -UseBasicParsing
    $tag = $release.tag_name
  } catch {
    Fail "could not resolve the latest release for $Repo ($($_.Exception.Message))"
  }
  $baseUrl = "https://github.com/$Repo/releases/latest/download"
} else {
  $tag = $Version
  if ($tag -notmatch '^v') { $tag = "v$tag" }
  $baseUrl = "https://github.com/$Repo/releases/download/$tag"
}
if (-not $tag) { Fail "could not resolve a release version for $Repo" }
# Release asset names carry the version, e.g. INTLLM-v1.1.0-win64x.exe.
$versionNum = $tag -replace '^v', ''
$portableName = "INTLLM-v$versionNum-win64x.exe"
$setupName = "INTLLM-v$versionNum-Setup.exe"
Done 'Release' $tag

$tmp = Join-Path $env:TEMP ('intllm-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $tmp | Out-Null

function Get-HashHex([string]$Path) {
  return (Get-FileHash -Path $Path -Algorithm SHA256).Hash.ToLower()
}

# Real, chunked download with byte-accurate progress.
function Get-RemoteFile([string]$Uri, [string]$OutFile, [string]$Label) {
  Add-Type -AssemblyName System.Net.Http -ErrorAction SilentlyContinue
  $client = New-Object System.Net.Http.HttpClient
  $client.Timeout = [TimeSpan]::FromMinutes(15)
  $client.DefaultRequestHeaders.Add('User-Agent', 'INTLLM-Installer')
  try {
    $resp = $client.GetAsync($Uri, [System.Net.Http.HttpCompletionOption]::ResponseHeadersRead).GetAwaiter().GetResult()
    if (-not $resp.IsSuccessStatusCode) { throw ('HTTP ' + [int]$resp.StatusCode) }
    $total = $resp.Content.Headers.ContentLength
    $inStream = $resp.Content.ReadAsStreamAsync().GetAwaiter().GetResult()
    $outStream = [System.IO.File]::Create($OutFile)
    $buffer = New-Object byte[] 1048576
    $done = 0
    $lastDraw = [DateTime]::MinValue
    while ($true) {
      $read = $inStream.Read($buffer, 0, $buffer.Length)
      if ($read -le 0) { break }
      $outStream.Write($buffer, 0, $read)
      $done += $read
      if ($script:Animate -and ((Get-Date) - $lastDraw).TotalMilliseconds -ge 80) {
        $lastDraw = Get-Date
        if ($total -and $total -gt 0) {
          $pct = [int](($done / $total) * 100)
          $barW = 28
          $filled = [int]($pct * $barW / 100)
          $bar = ('#' * $filled).PadRight($barW, '.')
          Write-Host ("`r      $Label [$bar] $pct% ") -NoNewline -ForegroundColor DarkGray
        } else {
          $mb = [math]::Round($done / 1MB, 1)
          Write-Host ("`r      $Label ${mb} MB ") -NoNewline -ForegroundColor DarkGray
        }
      }
    }
    $outStream.Close(); $inStream.Close()
    if ($script:Animate) { Write-Host ("`r" + (' ' * 70) + "`r") -NoNewline }
  } finally {
    $client.Dispose()
  }
}

try {
  # --- Download SHA256 manifest (small) ------------------------------------
  Step 'Downloading release manifest'
  Get-RemoteFile "$baseUrl/SHA256.txt" (Join-Path $tmp 'SHA256.txt') 'manifest'
  $shaLines = Get-Content (Join-Path $tmp 'SHA256.txt')
  Done 'Manifest' 'SHA256.txt'

  function Get-ExpectedHash([string]$FileName) {
    foreach ($line in $shaLines) {
      $parts = $line -split '\s+', 2
      if ($parts.Count -eq 2 -and $parts[1].Trim() -eq $FileName) { return $parts[0].Trim().ToLower() }
    }
    return $null
  }

  function Get-Verified([string]$FileName) {
    $target = Join-Path $tmp $FileName
    Step "Downloading $FileName"
    try {
      Get-RemoteFile "$baseUrl/$FileName" $target $FileName
    } catch {
      Fail "failed to download $FileName from $baseUrl ($($_.Exception.Message))"
    }
    $expected = Get-ExpectedHash $FileName
    if (-not $expected) { Fail "SHA256.txt does not list $FileName" }
    Step "Verifying $FileName"
    $actual = Get-HashHex $target
    if ($actual -ne $expected) {
      Fail "SHA256 mismatch for $FileName (expected $expected, got $actual)"
    }
    Done "Verified $FileName" "(SHA256)"
    return $target
  }

  # --- Install -------------------------------------------------------------
  $installDir = Join-Path $env:LOCALAPPDATA 'Programs\INTLLM'
  $exeName = 'INTLLM.exe'
  $exePath = Join-Path $installDir $exeName
  $existing = Test-Path $exePath

  $setupExpected = Get-ExpectedHash $setupName
  $useSetup = ($env:INTLLM_USE_SETUP -eq '1') -and $setupExpected

  if ($useSetup) {
    $setup = Get-Verified $setupName
    Step "Installing runtime ($setupName)"
    $proc = Start-Process -FilePath $setup -ArgumentList '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART' -Wait -PassThru
    if ($proc.ExitCode -ne 0) { Fail "$setupName exited with code $($proc.ExitCode)" }
    if (-not (Test-Path $exePath)) { Fail 'installer did not place INTLLM.exe where expected' }
    Done 'Runtime installed'
  } else {
    $portable = Get-Verified $portableName
    Step $(if ($existing) { 'Updating runtime' } else { 'Installing runtime' })
    New-Item -ItemType Directory -Force -Path $installDir | Out-Null
    Copy-Item -Path $portable -Destination $exePath -Force
    Done $(if ($existing) { 'Runtime updated' } else { 'Runtime installed' }) $installDir

    # `intllm` command shim so a fresh terminal can launch the app by name.
    Step 'Installing intllm command'
    $shimPath = Join-Path $installDir 'intllm.cmd'
    $shimBody = "@echo off`r`nsetlocal`r`n`"%~dp0INTLLM.exe`" %*`r`nexit /b %ERRORLEVEL%`r`n"
    Set-Content -Path $shimPath -Value $shimBody -Encoding ASCII
    Done 'intllm command installed'
  }

  # --- PATH ----------------------------------------------------------------
  if ($env:INTLLM_NO_PATH_EDIT -ne '1') {
    Step 'Configuring PATH'
    $userPath = [Environment]::GetEnvironmentVariable('PATH', 'User')
    if (-not $userPath) { $userPath = '' }
    $entries = $userPath -split ';' | Where-Object { $_ -ne '' }
    if ($entries -contains $installDir) {
      Done 'PATH already configured'
    } else {
      $newPath = (@($entries) + $installDir) -join ';'
      [Environment]::SetEnvironmentVariable('PATH', $newPath, 'User')
      $env:PATH = "$env:PATH;$installDir"
      Done 'PATH configured' $installDir
    }
  } else {
    Step 'Configuring PATH'
    Info 'skipped (INTLLM_NO_PATH_EDIT=1)'
  }

  # --- Shortcuts -----------------------------------------------------------
  Step 'Creating shortcuts'
  try {
    $shell = New-Object -ComObject WScript.Shell
    $startMenu = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs'
    $startShortcut = $shell.CreateShortcut((Join-Path $startMenu 'INTLLM.lnk'))
    $startShortcut.TargetPath = $exePath
    $startShortcut.WorkingDirectory = $installDir
    $startShortcut.Description = 'INTLLM - Local Intelligence Runtime'
    $startShortcut.Save()
    $desktop = [Environment]::GetFolderPath('Desktop')
    $desktopShortcut = $shell.CreateShortcut((Join-Path $desktop 'INTLLM.lnk'))
    $desktopShortcut.TargetPath = $exePath
    $desktopShortcut.WorkingDirectory = $installDir
    $desktopShortcut.IconLocation = $exePath
    $desktopShortcut.Description = 'INTLLM - Local Intelligence Runtime'
    $desktopShortcut.Save()
    Done 'Start Menu + desktop shortcuts'
  } catch {
    Warn "could not create one or more shortcuts: $($_.Exception.Message)"
  }

  # --- Verify --------------------------------------------------------------
  Step 'Finalizing'
  if (-not (Test-Path $exePath)) { Fail 'INTLLM.exe was not installed' }
  $installed = & $exePath --version 2>$null
  if (-not $installed) {
    Start-Sleep -Milliseconds 600
    $installed = & $exePath --version 2>$null
  }
  if (-not $installed) { Fail 'installation verification failed (INTLLM.exe --version produced no output)' }
  Done 'Verified' "$installed"

  C '' 'Gray'
  C ('  ' + [char]0x2713 + ' INTLLM installed successfully.') 'Green'
  C '' 'Gray'
  C '  Run:' 'Gray'
  C '      intllm                # start the runtime and open the web UI' 'White'
  C '      intllm doctor         # check PostgreSQL and Ollama readiness' 'White'
  C '      intllm --version      # print the installed version' 'White'
  C '' 'Gray'
  C '  PostgreSQL and Ollama are external local dependencies that INTLLM detects' 'DarkGray'
  C '  and reports. A new terminal (or sign out/in) is needed to pick up PATH.' 'DarkGray'
  C '' 'Gray'
} catch {
  Fail $_.Exception.Message
} finally {
  Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
}
