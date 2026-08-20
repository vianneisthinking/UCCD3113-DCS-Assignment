param([string]$Python = "python")

$artifact = Join-Path $PSScriptRoot "../member2_backend/lambda_backend.zip"
$staging = Join-Path $PSScriptRoot ".build/backend"
if (Test-Path $staging) { Remove-Item -LiteralPath $staging -Recurse -Force }
New-Item -ItemType Directory -Path $staging -Force | Out-Null

# Docker/SAM on Linux is preferred. This cross-platform pip mode explicitly
# downloads CPython 3.12 manylinux x86_64 wheels for Lambda.
& $Python -m pip install --platform manylinux2014_x86_64 --python-version 3.12 --implementation cp --only-binary=:all: --target $staging -r "$PSScriptRoot/../member2_backend/requirements.txt"
if ($LASTEXITCODE -ne 0) { throw "Dependency build failed" }
Copy-Item "$PSScriptRoot/../member2_backend/api" "$staging/api" -Recurse -Force
Copy-Item "$PSScriptRoot/../member2_backend/lambda_handler.py" "$staging/lambda_handler.py" -Force
Copy-Item "$PSScriptRoot/../member2_backend/migration_handler.py" "$staging/migration_handler.py" -Force
Copy-Item "$PSScriptRoot/../member2_backend/alembic.ini" "$staging/alembic.ini" -Force
Copy-Item "$PSScriptRoot/../member2_backend/migrations" "$staging/migrations" -Recurse -Force
Invoke-WebRequest "https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem" -OutFile "$staging/global-bundle.pem"
if (Test-Path $artifact) { Remove-Item -LiteralPath $artifact -Force }
Compress-Archive -Path "$staging/*" -DestinationPath $artifact -CompressionLevel Optimal

$zip = Get-Item $artifact
$files = Get-ChildItem $staging -Recurse -File
[pscustomobject]@{
    ZipMiB = [math]::Round($zip.Length / 1MB, 2)
    UnzippedMiB = [math]::Round((($files | Measure-Object Length -Sum).Sum) / 1MB, 2)
    Files = $files.Count
}
