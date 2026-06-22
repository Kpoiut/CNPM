$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$env:PYTHONPATH = $PSScriptRoot

if (-not (Test-Path -LiteralPath ".env")) {
  Copy-Item -LiteralPath ".env.example" -Destination ".env"
  Write-Host "Created .env from .env.example. Edit JWT_SECRET_KEY and optional AI keys if needed."
}

Get-Content -LiteralPath ".env" | ForEach-Object {
  $line = $_.Trim()
  if (-not $line -or $line.StartsWith("#") -or -not $line.Contains("=")) { return }
  $parts = $line.Split("=", 2)
  [Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1].Trim().Trim('"').Trim("'"), "Process")
}

$claudeSettings = Join-Path $env:USERPROFILE ".claude\settings.json"
if (Test-Path -LiteralPath $claudeSettings) {
  try {
    $claude = Get-Content -Raw -LiteralPath $claudeSettings | ConvertFrom-Json
    if ($claude.env) {
      foreach ($name in @("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL", "ANTHROPIC_DEFAULT_OPUS_MODEL", "ANTHROPIC_DEFAULT_SONNET_MODEL")) {
        $current = [Environment]::GetEnvironmentVariable($name, "Process")
        $hasClaudeValue = $claude.env.PSObject.Properties.Name -contains $name
        $shouldOverrideDefaultBase = (
          $name -eq "ANTHROPIC_BASE_URL" -and
          $hasClaudeValue -and
          -not [Environment]::GetEnvironmentVariable("ANTHROPIC_API_KEY", "Process") -and
          [Environment]::GetEnvironmentVariable("ANTHROPIC_AUTH_TOKEN", "Process") -and
          ($current -eq "https://api.anthropic.com" -or -not $current)
        )
        if (($hasClaudeValue -and -not $current) -or $shouldOverrideDefaultBase) {
          [Environment]::SetEnvironmentVariable($name, [string]$claude.env.$name, "Process")
        }
      }
      if (-not $env:NOVA_MODEL -and $claude.env.ANTHROPIC_DEFAULT_OPUS_MODEL) {
        $env:NOVA_MODEL = [string]$claude.env.ANTHROPIC_DEFAULT_OPUS_MODEL
      } elseif (-not $env:NOVA_MODEL -and $claude.env.ANTHROPIC_DEFAULT_SONNET_MODEL) {
        $env:NOVA_MODEL = [string]$claude.env.ANTHROPIC_DEFAULT_SONNET_MODEL
      }
    }
  } catch {
    Write-Host "Claude local settings found but could not be loaded. Continuing without printing secrets."
  }
}

if (-not $env:JWT_SECRET_KEY -or $env:JWT_SECRET_KEY -eq "replace-with-a-random-64-char-secret") {
  $env:JWT_SECRET_KEY = [System.Guid]::NewGuid().ToString("N") + [System.Guid]::NewGuid().ToString("N")
  Write-Host "Generated temporary JWT_SECRET_KEY for this run. Put a permanent value in .env for submission/demo machines."
}

$pythonCmd = $null
$pythonArgs = @()
if (Get-Command py -ErrorAction SilentlyContinue) {
  $pythonCmd = "py"
  $pythonArgs = @("-m", "uvicorn", "src.backend.main:app", "--reload", "--app-dir", $PSScriptRoot, "--host", "0.0.0.0", "--port", "8000")
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
  $pythonCmd = "python"
  $pythonArgs = @("-m", "uvicorn", "src.backend.main:app", "--reload", "--app-dir", $PSScriptRoot, "--host", "0.0.0.0", "--port", "8000")
} else {
  throw "Python launcher not found. Install Python 3.12+ or add python/py to PATH, then run INSTALL_DEPENDENCIES.bat."
}

& $pythonCmd @pythonArgs
