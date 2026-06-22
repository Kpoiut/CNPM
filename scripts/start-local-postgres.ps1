param(
    [string]$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [int]$ApiPort = 8000,
    [int]$FrontendPort = 5173
)

$ErrorActionPreference = "Stop"

$envFile = Join-Path $Root ".env.postgres.local"
if (-not (Test-Path -LiteralPath $envFile)) {
    throw "Missing $envFile. Create it from .env.example or run the PostgreSQL local setup first."
}

Get-Content -LiteralPath $envFile | ForEach-Object {
    if ($_ -match '^([^#=]+)=(.*)$') {
        [Environment]::SetEnvironmentVariable($matches[1], $matches[2], "Process")
    }
}

$venvPython = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $venvPython)) {
    throw "Missing backend venv at $venvPython"
}

$frontendDir = Join-Path $Root "frontend"
$viteBin = Join-Path $frontendDir "node_modules\.bin\vite.cmd"
if (-not (Test-Path -LiteralPath $viteBin)) {
    throw "Missing frontend node_modules. Run npm ci in $frontendDir first."
}

$logDir = Join-Path $Root "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

$backendCmd = @"
Set-Location '$Root'
Get-Content -LiteralPath '$envFile' | ForEach-Object { if (`$_ -match '^([^#=]+)=(.*)$') { [Environment]::SetEnvironmentVariable(`$matches[1], `$matches[2], 'Process') } }
`$env:PYTHONPATH='$Root'
& '$venvPython' -m uvicorn src.backend.main:app --host 127.0.0.1 --port $ApiPort
"@

$frontendCmd = @"
Set-Location '$frontendDir'
Get-Content -LiteralPath '$envFile' | ForEach-Object { if (`$_ -match '^([^#=]+)=(.*)$') { [Environment]::SetEnvironmentVariable(`$matches[1], `$matches[2], 'Process') } }
& npm.cmd run dev -- --host 127.0.0.1 --port $FrontendPort
"@

$backend = Start-Process -FilePath "powershell.exe" `
    -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $backendCmd `
    -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $logDir "backend.out.log") `
    -RedirectStandardError (Join-Path $logDir "backend.err.log") `
    -PassThru

$frontend = Start-Process -FilePath "powershell.exe" `
    -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $frontendCmd `
    -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $logDir "frontend.out.log") `
    -RedirectStandardError (Join-Path $logDir "frontend.err.log") `
    -PassThru

[pscustomobject]@{
    ApiUrl = "http://127.0.0.1:$ApiPort"
    FrontendUrl = "http://127.0.0.1:$FrontendPort"
    BackendPid = $backend.Id
    FrontendPid = $frontend.Id
    Logs = $logDir
}
