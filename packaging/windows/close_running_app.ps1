[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$InstallDirectory,
    [ValidateRange(0,30)][int]$GraceSeconds=6,
    [switch]$Apply
)
$ErrorActionPreference='Stop'
[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false)
$root=[IO.Path]::GetFullPath($InstallDirectory).TrimEnd('\')
if (-not (Split-Path -Parent $root)) { throw 'Refusing a drive-root target.' }
$relativePaths=@(
    '南枫下载.exe',
    '_internal\playwright\driver\node.exe',
    '_internal\tools\node\node.exe',
    '_internal\tools\ffmpeg\ffmpeg.exe',
    '_internal\tools\ffmpeg\ffprobe.exe',
    '_internal\tools\aria2\aria2c.exe'
)
$allowedPaths=@($relativePaths | ForEach-Object { Join-Path $root $_ })
function Get-OwnedProcesses {
    @(Get-CimInstance Win32_Process -Filter "Name='南枫下载.exe' OR Name='node.exe' OR Name='ffmpeg.exe' OR Name='ffprobe.exe' OR Name='aria2c.exe'" |
        Where-Object { $_.ExecutablePath -and $allowedPaths -contains [IO.Path]::GetFullPath($_.ExecutablePath) })
}
$candidates=@(Get-OwnedProcesses)
if (-not $Apply) {
    [pscustomobject]@{CandidateCount=$candidates.Count;ClosedCount=0;Applied=$false} | ConvertTo-Json -Compress
    exit 0
}
# Give owned GUI processes a chance to persist their queue before escalation.
foreach ($candidate in $candidates) {
    $process=Get-Process -Id $candidate.ProcessId -ErrorAction SilentlyContinue
    if ($process) { $null=$process.CloseMainWindow() }
}
$deadline=[DateTime]::UtcNow.AddSeconds($GraceSeconds)
while ([DateTime]::UtcNow -lt $deadline -and @(Get-OwnedProcesses).Count -gt 0) {
    Start-Sleep -Milliseconds 200
}
$closed=0
# Stop parent app first so it cannot respawn helpers; never use name-based kills
# or /T, which could include a user's external browser.
foreach ($candidate in @(Get-OwnedProcesses | Sort-Object @{Expression={if ($_.Name -eq '南枫下载.exe') {0} else {1}}})) {
    $current=Get-CimInstance Win32_Process -Filter "ProcessId=$($candidate.ProcessId)"
    if ($current -and $current.CreationDate -eq $candidate.CreationDate -and
        $current.ExecutablePath -eq $candidate.ExecutablePath -and $allowedPaths -contains [IO.Path]::GetFullPath($current.ExecutablePath)) {
        try {
            Stop-Process -Id $current.ProcessId -Force -ErrorAction Stop
            $closed++
        } catch {
            # Playwright helpers often exit when their parent closes. A process
            # disappearing between the ownership check and Stop-Process is success.
            $stillRunning=Get-CimInstance Win32_Process -Filter "ProcessId=$($candidate.ProcessId)"
            if ($stillRunning -and $stillRunning.CreationDate -eq $candidate.CreationDate) { throw }
        }
    }
}
$remaining=@(Get-OwnedProcesses)
[pscustomobject]@{CandidateCount=$candidates.Count;ClosedCount=($candidates.Count-$remaining.Count);ForcedCount=$closed;RemainingCount=$remaining.Count;Applied=$true} | ConvertTo-Json -Compress
if ($remaining.Count -gt 0) { exit 1 }
