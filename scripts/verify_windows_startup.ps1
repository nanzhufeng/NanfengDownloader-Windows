[CmdletBinding()]
param(
    [string]$Executable,
    [string]$PreviewDirectory
)
$ErrorActionPreference = 'Stop'
if (-not $Executable) { $Executable = Join-Path (Split-Path -Parent $PSScriptRoot) 'dist\南枫下载\南枫下载.exe' }
$qaRoot = Join-Path ([IO.Path]::GetTempPath()) ('NanfengDownloader-QA-' + [guid]::NewGuid().ToString('N'))
if (-not ('NanfengStartupProbe' -as [type])) {
    Add-Type @"
using System;
using System.Text;
using System.Runtime.InteropServices;
public static class NanfengStartupProbe {
    public delegate bool Callback(IntPtr handle, IntPtr state);
    [DllImport("user32.dll")] static extern bool EnumWindows(Callback callback, IntPtr state);
    [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr handle, out uint processId);
    [DllImport("user32.dll", CharSet=CharSet.Unicode)] static extern int GetWindowText(IntPtr handle, StringBuilder text, int count);
    [DllImport("user32.dll")] static extern IntPtr SendMessageTimeout(IntPtr handle, uint msg, IntPtr wp, IntPtr lp, uint flags, uint timeout, out IntPtr result);
    public static bool Responsive(int processId, string title) {
        bool found = false;
        EnumWindows(delegate(IntPtr h, IntPtr state) {
            uint owner; GetWindowThreadProcessId(h, out owner);
            if (owner != processId) return true;
            var text = new StringBuilder(256); GetWindowText(h, text, text.Capacity);
            if (text.ToString() != title) return true;
            IntPtr result; found = SendMessageTimeout(h, 0, IntPtr.Zero, IntPtr.Zero, 2, 500, out result) != IntPtr.Zero;
            return !found;
        }, IntPtr.Zero);
        return found;
    }
}
"@
}
$originalEnvironment = @{}
$process = $null
try {
    New-Item -ItemType Directory -Path $qaRoot -Force | Out-Null
    foreach ($name in @('NANFENG_DOWNLOADER_QA_ROOT','NANFENG_DOWNLOADER_QA_PREVIEW','LOCALAPPDATA','APPDATA')) {
        $originalEnvironment[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
    }
    $env:NANFENG_DOWNLOADER_QA_ROOT = $qaRoot
    $env:NANFENG_DOWNLOADER_QA_PREVIEW = if ($PreviewDirectory) { '1' } else { '0' }
    $env:LOCALAPPDATA = Join-Path $qaRoot 'Local'
    $env:APPDATA = Join-Path $qaRoot 'Roaming'
    $process = Start-Process -FilePath $Executable -WindowStyle Hidden -PassThru
    $deadline = [DateTime]::UtcNow.AddSeconds(30)
    do {
        Start-Sleep -Milliseconds 250
        $process.Refresh()
        if ($process.HasExited) { throw 'Application exited before opening its main window.' }
        if ($process.MainWindowTitle -like '*Unhandled exception*') {
            throw 'Frozen application startup failed: unhandled exception.'
        }
        if ([NanfengStartupProbe]::Responsive($process.Id, '南枫下载')) {
            if ($PreviewDirectory) {
                $previewReceipt = Join-Path $qaRoot 'preview.json'
                if (-not (Test-Path -LiteralPath $previewReceipt)) { continue }
                New-Item -ItemType Directory -Path $PreviewDirectory -Force | Out-Null
                foreach ($file in @('workbench.png','history.png','settings.png','popup.png','preview.json')) {
                    Copy-Item -LiteralPath (Join-Path $qaRoot $file) -Destination $PreviewDirectory -Force
                }
            }
            Write-Output 'Startup verified: 南枫下载; responsive main window.'
            return
        }
    } while ([DateTime]::UtcNow -lt $deadline)
    throw ('Application startup verification timed out; preview ready: ' + (Test-Path -LiteralPath (Join-Path $qaRoot 'preview.json')))
}
finally {
    if ($process -and -not $process.HasExited) {
        $null = $process.CloseMainWindow()
        if (-not $process.WaitForExit(5000)) { $process.Kill() }
    }
    if ($process) { $process.Dispose() }
    foreach ($name in $originalEnvironment.Keys) { [Environment]::SetEnvironmentVariable($name, $originalEnvironment[$name], 'Process') }
    $tempRoot = [IO.Path]::GetFullPath([IO.Path]::GetTempPath())
    $resolvedQaRoot = [IO.Path]::GetFullPath($qaRoot)
    if ($resolvedQaRoot.StartsWith($tempRoot, [StringComparison]::OrdinalIgnoreCase) -and (Split-Path -Leaf $resolvedQaRoot) -like 'NanfengDownloader-QA-*') {
        Remove-Item -LiteralPath $resolvedQaRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}
