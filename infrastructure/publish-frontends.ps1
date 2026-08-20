param(
    [Parameter(Mandatory=$true)][string]$ApiUrl,
    [Parameter(Mandatory=$true)][string]$BucketName,
    [Parameter(Mandatory=$true)][string]$DistributionId
)

# REVIEW ONLY. Running this script uploads objects and requires deployment approval.
$site = Join-Path $PSScriptRoot ".site"
New-Item -ItemType Directory -Path "$site/staff" -Force | Out-Null
New-Item -ItemType Directory -Path "$site/customer" -Force | Out-Null
Copy-Item "$PSScriptRoot/../landing_index.html" "$site/index.html" -Force
Copy-Item "$PSScriptRoot/../member1_index.html" "$site/customer/index.html" -Force
Set-Content "$site/config.js" "window.APP_CONFIG = { API_BASE_URL: '$($ApiUrl.TrimEnd('/'))' };" -Encoding UTF8
$env:VITE_API_BASE_URL = $ApiUrl.TrimEnd('/')
pnpm --dir "$PSScriptRoot/../staff-dashboard" build
if ($LASTEXITCODE -ne 0) { throw "Staff build failed" }
Copy-Item "$PSScriptRoot/../staff-dashboard/dist/*" "$site/staff" -Recurse -Force
aws s3 sync $site "s3://$BucketName" --delete
if ($LASTEXITCODE -ne 0) { throw "S3 upload failed" }
aws cloudfront create-invalidation --distribution-id $DistributionId --paths "/*"
