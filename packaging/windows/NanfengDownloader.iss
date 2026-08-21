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
#define MyAppOutputDir "..\..\installer\releases"

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
CloseApplications=no
RestartApplications=no
VersionInfoVersion={#MyVersionInfo}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName} Windows 安装程序
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加任务："; Flags: unchecked

[Files]
Source: "{#MyAppSourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "启动 {#MyAppName}"; Flags: nowait postinstall skipifsilent
