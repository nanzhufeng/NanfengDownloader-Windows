[CmdletBinding()]
param([string]$Executable = (Join-Path (Split-Path -Parent $PSScriptRoot) 'dist\南枫下载\南枫下载.exe'))
$ErrorActionPreference = 'Stop'
$process = Start-Process -FilePath $Executable -PassThru
try {
    $deadline = [DateTime]::UtcNow.AddSeconds(30)
    do {
        Start-Sleep -Milliseconds 250
        $process.Refresh()
        if ($process.HasExited) { throw 'Application exited before opening its main window.' }
        if ($process.MainWindowTitle -like '*Unhandled exception*') {
            throw 'Frozen application startup failed: unhandled exception.'
        }
        if ($process.MainWindowTitle -eq '南枫下载' -and $process.Responding) {
            Write-Output 'Startup verified: 南枫下载; responsive main window.'
            return
        }
    } while ([DateTime]::UtcNow -lt $deadline)
    throw 'Application did not show a responsive main window within 30 seconds.'
}
finally {
    if (-not $process.HasExited) {
        $null = $process.CloseMainWindow()
        if (-not $process.WaitForExit(5000)) { $process.Kill() }
    }
    $process.Dispose()
}
