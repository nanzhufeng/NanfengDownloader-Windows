[CmdletBinding()]
param(
    [switch]$SkipTests,
    [switch]$CheckCompilerOnly
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$isccCandidates = @(
    (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 7\ISCC.exe"),
    (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe")
)
$iscc = $isccCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1

if (-not $iscc) {
    throw "Inno Setup was not found. Install JRSoftware.InnoSetup.7 first."
}

Push-Location $projectRoot
try {
    Write-Output "Inno compiler: $iscc"
    if ($CheckCompilerOnly) {
        return
    }

    if (-not $SkipTests) {
        python -m unittest discover -s tests -v
        if ($LASTEXITCODE -ne 0) {
            throw "Automated tests failed."
        }
    }

    $spec = Get-ChildItem -LiteralPath $projectRoot -Filter "*.spec" -File |
        Where-Object { $_.Name -notlike "*_mac.spec" } |
        Select-Object -First 1
    if (-not $spec) {
        throw "No Windows PyInstaller spec was found."
    }

    python -m PyInstaller --noconfirm --clean $spec.FullName
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller build failed."
    }

    & $iscc "packaging\windows\NanfengDownloader.iss"
    if ($LASTEXITCODE -ne 0) {
        throw "Inno Setup build failed."
    }

    $installer = Join-Path $projectRoot "installer\NanfengDownloader-Windows-v2026.08.01-Setup.exe"
    if (-not (Test-Path -LiteralPath $installer)) {
        throw "Installer was not created: $installer"
    }

    $hash = Get-FileHash -LiteralPath $installer -Algorithm SHA256
    Write-Output "Installer: $installer"
    Write-Output "SHA-256: $($hash.Hash)"
}
finally {
    Pop-Location
}
