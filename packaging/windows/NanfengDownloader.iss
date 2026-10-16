#define MyAppName "南枫下载"
#ifndef MyAppVersion
  #error "MyAppVersion is required. Use scripts\\build_windows_installer.ps1 -Version YYYY.MM.DD."
#endif
#ifndef MyVersionInfo
  #error "MyVersionInfo is required."
#endif
#ifndef MyOutputVersion
  #error "MyOutputVersion is required."
#endif
#define MyAppPublisher "南烛枫"
#define MyAppExeName "南枫下载.exe"
#define MyAppSourceDir "..\..\dist\南枫下载"
#ifndef MyAppOutputDir
  #define MyAppOutputDir "..\..\installer\releases"
#endif

[Setup]
AppId={{D89A65BA-5F2E-4B16-A594-0DBE777162DB}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir={#MyAppOutputDir}
OutputBaseFilename=NanfengDownloader-Windows-v{#MyOutputVersion}-Setup
SetupIconFile=..\..\app\assets\nanzhufeng-icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
UsePreviousTasks=no
ShowLanguageDialog=no
UsePreviousLanguage=no
VersionInfoVersion={#MyVersionInfo}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName} Windows 安装程序
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}

[Languages]
Name: "chinesesimp"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加任务："

[Files]
Source: "close_running_app.ps1"; Flags: dontcopy
Source: "{#MyAppSourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[InstallDelete]
; Older builds accidentally bundled Poppler ICU, shadowing the Windows ICU API.
Type: files; Name: "{app}\_internal\icuuc.dll"
Type: files; Name: "{app}\_internal\icudt78.dll"

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "启动 {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Code]
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ExitCode: Integer;
  Arguments: String;
begin
  Result := '';
  WizardForm.StatusLabel.Caption := '正在关闭旧版程序及后台组件，请稍候……';
  ExtractTemporaryFile('close_running_app.ps1');
  Arguments := '-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "' +
    ExpandConstant('{tmp}\close_running_app.ps1') + '" -InstallDirectory "' +
    ExpandConstant('{app}') + '" -Apply';
  if not Exec(ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe'),
    Arguments, '', SW_HIDE, ewWaitUntilTerminated, ExitCode) then
    Result := '无法启动旧版程序清理，请关闭南枫下载后重试。'
  else if ExitCode <> 0 then
    Result := '旧版程序仍在占用文件，请关闭南枫下载后重试；不会强制覆盖正在使用的文件。';
end;
