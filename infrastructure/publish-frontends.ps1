param(
    [Parameter(Mandatory=$true)][ValidateNotNullOrEmpty()][string]$ApiUrl,
    [Parameter(Mandatory=$true)][ValidateNotNullOrEmpty()][string]$BucketName,
    [Parameter(Mandatory=$true)][ValidateNotNullOrEmpty()][string]$DistributionId,
    [switch]$StageOnly
)

$ErrorActionPreference = "Stop"

# REVIEW ONLY. Without -StageOnly, this script uploads objects and requires deployment approval.
$landingSource = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "../landing_index.html"))
$customerSource = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "../member2_backend/index.html"))
$staffProject = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "../staff-dashboard"))
$staffPackage = Join-Path $staffProject "package.json"
$staffDist = Join-Path $staffProject "dist"

$requiredFiles = [ordered]@{
    "Landing page" = $landingSource
    "Customer page" = $customerSource
    "Staff package manifest" = $staffPackage
}

foreach ($requiredFile in $requiredFiles.GetEnumerator()) {
    if (-not (Test-Path -LiteralPath $requiredFile.Value -PathType Leaf)) {
        throw "$($requiredFile.Key) is missing: $($requiredFile.Value)"
    }
}

$infrastructureRoot = [System.IO.Path]::GetFullPath($PSScriptRoot)
$site = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".site"))
if ([System.IO.Path]::GetDirectoryName($site) -ne $infrastructureRoot) {
    throw "Refusing to clear an unexpected staging path: $site"
}

if (Test-Path -LiteralPath $site) {
    Remove-Item -LiteralPath $site -Recurse -Force
}
New-Item -ItemType Directory -Path $site -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $site "staff") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $site "customer") -Force | Out-Null

$stagedLanding = Join-Path $site "index.html"
$stagedCustomer = Join-Path $site "customer/index.html"
$stagedConfig = Join-Path $site "config.js"

Copy-Item -LiteralPath $landingSource -Destination $stagedLanding -Force
Copy-Item -LiteralPath $customerSource -Destination $stagedCustomer -Force
Set-Content -LiteralPath $stagedConfig -Value "window.APP_CONFIG = { API_BASE_URL: '$($ApiUrl.TrimEnd('/'))' };" -Encoding UTF8

$env:VITE_API_BASE_URL = $ApiUrl.TrimEnd('/')
pnpm --dir $staffProject build
if ($LASTEXITCODE -ne 0) { throw "Staff build failed" }

if (-not (Test-Path -LiteralPath $staffDist -PathType Container)) {
    throw "Staff build output is missing: $staffDist"
}
$staffBuildFiles = Get-ChildItem -LiteralPath $staffDist -File -Recurse
if (-not $staffBuildFiles) {
    throw "Staff build output is empty: $staffDist"
}
Copy-Item -Path (Join-Path $staffDist "*") -Destination (Join-Path $site "staff") -Recurse -Force

if (-not (Test-Path -LiteralPath $stagedCustomer -PathType Leaf)) {
    throw "Customer staging failed; refusing to run S3 sync: $stagedCustomer"
}
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $customerSource).Hash -ne
    (Get-FileHash -Algorithm SHA256 -LiteralPath $stagedCustomer).Hash) {
    throw "Staged customer page does not match its source; refusing to run S3 sync"
}

if ($StageOnly) {
    Write-Host "Frontend staging verified at $site. No AWS commands were run."
    return
}

aws s3 sync $site "s3://$BucketName" --delete
if ($LASTEXITCODE -ne 0) { throw "S3 upload failed" }
aws cloudfront create-invalidation --distribution-id $DistributionId --paths "/*"
if ($LASTEXITCODE -ne 0) { throw "CloudFront invalidation failed" }
