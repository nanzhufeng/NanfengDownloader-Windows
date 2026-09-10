[CmdletBinding()]
param(
    [string]$Version,
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
$originalPath = $env:PATH
try {
    Write-Output "Inno compiler: $iscc"
    if ($CheckCompilerOnly) {
        return
    }

    # Keep unrelated native DLLs (for example Poppler ICU) out of dependency discovery.
    $pythonExecutable = (Get-Command python -CommandType Application | Select-Object -First 1).Source
    $pythonDirectory = Split-Path -Parent $pythonExecutable
    $env:PATH = @($pythonDirectory, (Join-Path $pythonDirectory 'Scripts'),
        (Join-Path $env:SystemRoot 'System32'), $env:SystemRoot) -join ';'

    if ([string]::IsNullOrWhiteSpace($Version)) {
        throw "Version is required. Example: -Version 2026.08.21"
    }
    $metadata = python scripts\release_metadata.py --version $Version --format json | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) {
        throw "Release version is invalid."
    }

    $releaseDirectory = 'D:\ReleaseUpload\NanfengDownloader'
    $releaseInstaller = Join-Path $releaseDirectory $metadata.installer_name
    if (Test-Path -LiteralPath $releaseInstaller) {
        throw "Refusing to overwrite an existing release artifact: $releaseInstaller"
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

    & (Join-Path $PSScriptRoot 'verify_windows_startup.ps1')

    $buildOutputDirectory = Join-Path $releaseDirectory ("work\{0}-{1}" -f $metadata.output_version, [guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Path $buildOutputDirectory -Force | Out-Null
    & $iscc "/DMyAppVersion=$($metadata.app_version)" "/DMyVersionInfo=$($metadata.version_info)" "/DMyOutputVersion=$($metadata.output_version)" "/DMyAppOutputDir=$buildOutputDirectory" "packaging\windows\NanfengDownloader.iss"
    if ($LASTEXITCODE -ne 0) {
        throw "Inno Setup build failed."
    }

    $installer = Join-Path $buildOutputDirectory $metadata.installer_name
    if (-not (Test-Path -LiteralPath $installer)) {
        throw "Installer was not created in the isolated build directory: $installer"
    }

    New-Item -ItemType Directory -Path $releaseDirectory -Force | Out-Null
    Move-Item -LiteralPath $installer -Destination $releaseInstaller -ErrorAction Stop

    $hash = Get-FileHash -LiteralPath $releaseInstaller -Algorithm SHA256
    Write-Output "Installer: $releaseInstaller"
    Write-Output "SHA-256: $($hash.Hash)"
}
finally {
    $env:PATH = $originalPath
    Pop-Location
}
