$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = (Resolve-Path (Join-Path $ScriptDir "..\..")).Path
$FrontendDir = Join-Path $Root "frontend"

if (-not (Test-Path -LiteralPath $FrontendDir)) {
  throw "Missing frontend directory: $FrontendDir"
}

Set-Location $FrontendDir

if (-not $env:VITE_API_PROXY_TARGET) {
  $env:VITE_API_PROXY_TARGET = "http://127.0.0.1:8000"
}

$npm = Get-Command npm.cmd -ErrorAction SilentlyContinue
if (-not $npm) {
  throw "npm not found. Install Node.js 20+ and run npm ci in $FrontendDir."
}

& $npm.Source run dev -- --host 127.0.0.1 --port 5173
