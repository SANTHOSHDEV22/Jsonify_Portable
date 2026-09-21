; ============================================================
; Jsonify - Windows Installer
; Inno Setup Script
; ============================================================

#define MyAppName "Jsonify"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Jsonify"
#define MyAppExeName "Jsonify.exe"


[Setup]

; IMPORTANT:
; Generate your own GUID once and keep it permanently.
AppId={{8F74009B-54B2-4DF4-BC36-BED26B835879}

AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}

AppPublisher={#MyAppPublisher}

DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}

DisableProgramGroupPage=yes

OutputDir=..\installer-output
OutputBaseFilename=Jsonify-Setup-{#MyAppVersion}

Compression=lzma2
SolidCompression=yes

WizardStyle=modern

PrivilegesRequired=admin

ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}

SetupLogging=yes


[Languages]

Name: "english"; MessagesFile: "compiler:Default.isl"


[Tasks]

Name: "desktopicon"; \
    Description: "Create a desktop shortcut"; \
    GroupDescription: "Additional shortcuts:"; \
    Flags: unchecked


[Files]

; Copy the complete PyInstaller onedir build.
Source: "..\dist\Jsonify\*"; \
    DestDir: "{app}"; \
    Flags: ignoreversion recursesubdirs createallsubdirs


[Icons]

; Start Menu shortcut
Name: "{group}\Jsonify"; \
    Filename: "{app}\{#MyAppExeName}"

; Optional Desktop shortcut
Name: "{autodesktop}\Jsonify"; \
    Filename: "{app}\{#MyAppExeName}"; \
    Tasks: desktopicon

; Uninstall shortcut
Name: "{group}\Uninstall Jsonify"; \
    Filename: "{uninstallexe}"


[Run]

; Offer to launch Jsonify after installation.
Filename: "{app}\{#MyAppExeName}"; \
    Description: "Launch Jsonify"; \
    Flags: nowait postinstall skipifsilent