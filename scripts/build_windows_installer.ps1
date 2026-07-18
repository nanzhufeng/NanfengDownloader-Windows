[CmdletBinding()]
param(
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$iscc = Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"

if (-not (Test-Path -LiteralPath $iscc)) {
    throw "Inno Setup 6 was not found. Install JRSoftware.InnoSetup first."
}

Push-Location $projectRoot
try {
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

    $installer = Join-Path $projectRoot "installer\NanfengDownloader-Windows-v2026.07.19-Setup.exe"
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
