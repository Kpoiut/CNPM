param(
  [string]$ExpectedHost = "127.0.0.1",
  [int]$ExpectedPort = 5433,
  [string]$ExpectedDatabase = "real_estate_avm",
  [string]$ExpectedMajorVersion = "18"
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = (Resolve-Path (Join-Path $ScriptDir "..\..")).Path
Set-Location $Root

function Read-EnvFile {
  param([string]$Path)
  $values = @{}
  if (-not (Test-Path -LiteralPath $Path)) {
    throw "Missing .env at $Path"
  }
  Get-Content -LiteralPath $Path | ForEach-Object {
    $line = $_.Trim()
    if (-not $line -or $line.StartsWith("#") -or -not $line.Contains("=")) { return }
    $parts = $line.Split("=", 2)
    $values[$parts[0].Trim()] = $parts[1].Trim().Trim('"').Trim("'")
  }
  return $values
}

function Resolve-Psql {
  $postgres18 = "C:\Program Files\PostgreSQL\18\bin\psql.exe"
  if (Test-Path -LiteralPath $postgres18) { return $postgres18 }
  $cmd = Get-Command psql -ErrorAction SilentlyContinue
  if ($cmd) { return $cmd.Source }
  throw "psql.exe not found. Install PostgreSQL 18 client tools or add psql to PATH."
}

$envValues = Read-EnvFile (Join-Path $Root ".env")
$databaseUrl = $envValues["DATABASE_URL"]
if (-not $databaseUrl) {
  throw "DATABASE_URL is missing in .env"
}
if ($databaseUrl -notmatch "^postgresql\+psycopg://([^:]+):([^@]+)@([^:/]+):(\d+)/([^?]+)") {
  throw "DATABASE_URL must be postgresql+psycopg://user:password@host:port/database"
}

$dbUser = $Matches[1]
$dbPassword = $Matches[2]
$dbHostName = $Matches[3]
$dbPort = [int]$Matches[4]
$dbName = $Matches[5]

if ($dbHostName -ne $ExpectedHost -or $dbPort -ne $ExpectedPort -or $dbName -ne $ExpectedDatabase) {
  throw "DATABASE_URL points to $dbHostName`:$dbPort/$dbName, expected $ExpectedHost`:$ExpectedPort/$ExpectedDatabase"
}

$psql = Resolve-Psql
$oldPassword = $env:PGPASSWORD
$env:PGPASSWORD = $dbPassword

try {
  Write-Host "Checking PostgreSQL 18 realtime connection from .env..."
  $identitySql = "SELECT current_setting('server_version') AS server_version, current_database() AS database, current_user AS app_user, current_setting('port') AS port;"
  & $psql -h $dbHostName -p $dbPort -U $dbUser -d $dbName -v ON_ERROR_STOP=1 -c $identitySql

  $major = & $psql -h $dbHostName -p $dbPort -U $dbUser -d $dbName -t -A -v ON_ERROR_STOP=1 -c "SELECT split_part(current_setting('server_version'), '.', 1);"
  if ($major.Trim() -ne $ExpectedMajorVersion) {
    throw "Connected PostgreSQL major version is $($major.Trim()), expected $ExpectedMajorVersion"
  }

  $head = & $psql -h $dbHostName -p $dbPort -U $dbUser -d $dbName -t -A -v ON_ERROR_STOP=1 -c "SELECT version_num FROM public.alembic_version;"
  if ($head.Trim() -ne "20260622_0014") {
    throw "Alembic head is $($head.Trim()), expected 20260622_0014"
  }

  $countSql = @"
SELECT 'public.accounts' AS object_name, COUNT(*)::int AS row_count FROM public.accounts
UNION ALL SELECT 'auth.auth_accounts', COUNT(*)::int FROM auth.auth_accounts
UNION ALL SELECT 'public.properties', COUNT(*)::int FROM public.properties
UNION ALL SELECT 'public.valuation_runs', COUNT(*)::int FROM public.valuation_runs
UNION ALL SELECT 'public.matched_pairs', COUNT(*)::int FROM public.matched_pairs
UNION ALL SELECT 'public.buyer_requirements', COUNT(*)::int FROM public.buyer_requirements
ORDER BY object_name;
"@
  & $psql -h $dbHostName -p $dbPort -U $dbUser -d $dbName -v ON_ERROR_STOP=1 -c $countSql

  $dbProperties = & $psql -h $dbHostName -p $dbPort -U $dbUser -d $dbName -t -A -v ON_ERROR_STOP=1 -c "SELECT COUNT(*)::int FROM public.properties;"
  $dbProperties = [int]$dbProperties.Trim()

  $health = $null
  foreach ($url in @("http://127.0.0.1:4173/api/health", "http://127.0.0.1:8000/api/health")) {
    try {
      $health = Invoke-RestMethod -Uri $url -TimeoutSec 8
      Write-Host "API health reached: $url"
      break
    } catch {
      $health = $null
    }
  }
  if (-not $health) {
    throw "Backend/frontend proxy health is not reachable on 4173 or 8000. Start the app, then run this script again."
  }
  if ($health.database.dialect -ne "postgresql") {
    throw "API health dialect is $($health.database.dialect), expected postgresql"
  }
  if ([int]$health.database.total_properties -ne $dbProperties) {
    throw "API properties count $($health.database.total_properties) does not match PostgreSQL count $dbProperties"
  }

  Write-Host "OK: API is reading PostgreSQL $ExpectedMajorVersion on $ExpectedHost`:$ExpectedPort in realtime."
} finally {
  $env:PGPASSWORD = $oldPassword
}
