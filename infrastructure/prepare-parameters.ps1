param(
    [Parameter(Mandatory=$true)][string]$Region,
    [Parameter(Mandatory=$true)][string]$Prefix,
    [Parameter(Mandatory=$true)][string]$DbHost,
    [string]$DbName = "postgres",
    [string]$DbUser = "postgres",
    [Parameter(Mandatory=$true)][SecureString]$JwtSecret
)

# REVIEW ONLY. Running this script creates SSM resources and therefore requires
# the explicit deployment approval that has not yet been given.
$jwt = [System.Net.NetworkCredential]::new("", $JwtSecret).Password
$values = @{
    DB_IAM_AUTH = "true"
    DB_HOST = $DbHost
    DB_PORT = "5432"
    DB_NAME = $DbName
    DB_USER = $DbUser
    # Aurora express uses the AWS internet access gateway certificate chain.
    DB_SSL_ROOT_CERT = "/etc/pki/tls/certs/ca-bundle.crt"
    JWT_SECRET = $jwt
    JWT_EXPIRE_MINUTES = "1440"
}

foreach ($entry in $values.GetEnumerator()) {
    $type = if ($entry.Key -eq "JWT_SECRET") { "SecureString" } else { "String" }
    aws ssm put-parameter --region $Region --name "$Prefix/$($entry.Key)" --type $type --value $entry.Value --overwrite
    if ($LASTEXITCODE -ne 0) { throw "Failed to create $Prefix/$($entry.Key)" }
}
