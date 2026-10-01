; INTLLM Windows installer (Inno Setup 6.3+).
;
; Build (from this directory):
;   ISCC.exe /DAppVersion=0.4.2 /DSourceExe=..\build\release\INTLLM-windows-x64.exe INTLLM-Setup.iss
;
; Or from the repository root:
;   python scripts/build_release.py
;
; Produces: build\release\INTLLM-Setup.exe
;
; Behaviour:
;   * per-user install to %LOCALAPPDATA%\Programs\INTLLM (no admin prompt)
;   * application files live in ...\Programs\INTLLM; INTLLM runtime data
;     (%LOCALAPPDATA%\INTLLM) is separate and is NOT touched by install or
;     uninstall, so user conversations/memory survive upgrades and removal
;   * adds the install dir to the per-user PATH (notified via ChangesEnvironment)
;   * Start Menu shortcut + optional desktop icon
;   * detects an existing install and upgrades in place

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#ifndef SourceExe
  #define SourceExe "..\build\release\INTLLM-windows-x64.exe"
#endif
#ifndef OutputDir
  #define OutputDir "..\build\release"
#endif
#ifndef AppIcon
  #define AppIcon "..\assets\ico\INTLLM.ico"
#endif

[Setup]
AppId={{8F3A1C2D-5B6E-4F70-9A11-2C3D4E5F6A7B}
AppName=INTLLM
AppVersion={#AppVersion}
AppVerName=INTLLM {#AppVersion}
AppPublisher=INTLLM
DefaultDirName={localappdata}\Programs\INTLLM
DefaultGroupName=INTLLM
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir={#OutputDir}
OutputBaseFilename=INTLLM-Setup
SetupIconFile={#AppIcon}
UninstallDisplayIcon={app}\INTLLM.exe
UninstallDisplayName=INTLLM
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; Notify running processes (Explorer/shells) after the PATH change.
ChangesEnvironment=yes
; Close a running INTLLM so the exe can be replaced during an upgrade.
CloseApplications=yes
RestartApplications=no

[Files]
Source: "{#SourceExe}"; DestDir: "{app}"; DestName: "INTLLM.exe"; Flags: ignoreversion

[Icons]
Name: "{group}\INTLLM"; Filename: "{app}\INTLLM.exe"; WorkingDir: "{app}"; IconFilename: "{app}\INTLLM.exe"
Name: "{group}\Uninstall INTLLM"; Filename: "{uninstallexe}"
Name: "{userdesktop}\INTLLM"; Filename: "{app}\INTLLM.exe"; WorkingDir: "{app}"; IconFilename: "{app}\INTLLM.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Run]
; Smoke-check the installed binary. It prints the version and exits.
Filename: "{app}\INTLLM.exe"; Parameters: "--version"; Flags: runhidden; StatusMsg: "Verifying installation..."

[Registry]
; Canonical Inno Setup pattern: append {app} to the per-user PATH only when it
; is not already present. Uninstall removes it again in [Code] below.
Root: HKCU; Subkey: "Environment"; ValueType: expandsz; ValueName: "Path"; \
  ValueData: "{olddata};{app}"; Check: NeedsAddPath('{app}')

[UninstallDelete]
; Only the program directory. Runtime data under %LOCALAPPDATA%\INTLLM is
; intentionally preserved (see the comment at the top of this file).
Type: filesandordirs; Name: "{app}"

[Code]
{ True when Param is not already a PATH entry. }
function NeedsAddPath(Param: string): Boolean;
var
  OrigPath: string;
begin
  if not RegQueryStringValue(HKEY_CURRENT_USER, 'Environment', 'Path', OrigPath) then
  begin
    Result := True;
    exit;
  end;
  Result := Pos(';' + Param + ';', ';' + OrigPath + ';') = 0;
end;

{ Remove the install directory from the per-user PATH on uninstall. }
procedure RemoveFromPath(Param: string);
var
  Current, NewPath: string;
begin
  if not RegQueryStringValue(HKEY_CURRENT_USER, 'Environment', 'Path', Current) then
    exit;
  NewPath := Current;
  StringChangeEx(NewPath, ';' + Param, '', True);
  StringChangeEx(NewPath, Param + ';', '', True);
  StringChangeEx(NewPath, Param, '', True);
  RegWriteStringValue(HKEY_CURRENT_USER, 'Environment', 'Path', NewPath);
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then
    RemoveFromPath(ExpandConstant('{app}'));
end;
