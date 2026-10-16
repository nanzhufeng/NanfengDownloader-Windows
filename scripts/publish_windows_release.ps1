[CmdletBinding()]
param([switch]$Publish,[switch]$Plan)
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
    $metadata=python scripts/release_metadata.py --from-source app/main.py --format json | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) { throw 'Source version is invalid.' }
    $head=git rev-parse HEAD
    if ($LASTEXITCODE -ne 0) { throw 'Not a Git checkout.' }
    $dirty=@(git status --porcelain).Count -gt 0
    $notes=Join-Path $root "docs/release-$($metadata.output_version).md"
    if ($Publish -and -not (Test-Path -LiteralPath $notes)) { throw 'Version-specific release notes are required.' }
    if ($Plan) {
        [ordered]@{tag=$metadata.tag;source=$head;dirty=$dirty;publish=[bool]$Publish;
            route='GitHub Actions Windows build and upload';external_mutations=$false} | ConvertTo-Json
        return
    }
    if ($dirty) { throw 'Commit the intended changes before dispatch; cloud builds must use the exact reviewed source.' }
    $branch=git branch --show-current
    if (-not $branch) { throw 'Use a named, pushed branch before dispatch.' }
    $remote=git ls-remote origin "refs/heads/$branch"
    if ($LASTEXITCODE -ne 0 -or ($remote -split '\s+')[0] -ne $head) { throw 'Push the exact local commit before dispatch.' }
    gh auth status
    if ($LASTEXITCODE -ne 0) { throw 'GitHub CLI authentication is required.' }
    $active=gh run list --workflow release-windows.yml --branch $branch --limit 10 --json databaseId,headSha,status --repo nanzhufeng/NanfengDownloader-Windows | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) { throw 'Cannot inspect existing workflow runs.' }
    if (@($active | Where-Object { $_.headSha -eq $head -and $_.status -ne 'completed' }).Count) {
        throw 'A run for this source is already active; inspect it instead of dispatching another build.'
    }
    $publishValue=([bool]$Publish).ToString().ToLowerInvariant()
    gh workflow run release-windows.yml --repo nanzhufeng/NanfengDownloader-Windows --ref $branch -f "tag=$($metadata.tag)" -F "publish=$publishValue"
    if ($LASTEXITCODE -ne 0) { throw 'Workflow dispatch failed.' }
    Write-Output "Dispatched $($metadata.tag), publish=$publishValue, source=$head"
    Write-Output 'Inspect progress: gh run list --workflow release-windows.yml --limit 3'
} finally { Pop-Location }
