#define MyAppName "Agentic AI Student Examination"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Mohammad Ali Jinnah University"
#define StudentFolderName "AgenticExamStudent"

[Setup]
AppId={{9B1C0A6E-5C87-4F7A-9A41-7D5C2B6E1034}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\MAJU\Agentic AI Student Examination
DefaultGroupName=MAJU\Agentic AI Student Examination
DisableProgramGroupPage=yes
OutputDir=installer_output
OutputBaseFilename=AgenticAI_Student_Exam_Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64
UninstallDisplayIcon={app}\{#StudentFolderName}\AgenticExamStudent.exe
; Do not request administrator rights: install per-user in LocalAppData.

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
; Build the student app first. This copies the complete PyInstaller ONEDIR folder,
; including _internal and all bundled DLLs.
Source: "..\dist\{#StudentFolderName}\*"; DestDir: "{app}\{#StudentFolderName}"; \
    Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Agentic AI Student Examination"; \
    Filename: "{app}\{#StudentFolderName}\AgenticExamStudent.exe"; \
    WorkingDir: "{app}\{#StudentFolderName}"
Name: "{autodesktop}\Agentic AI Student Examination"; \
    Filename: "{app}\{#StudentFolderName}\AgenticExamStudent.exe"; \
    WorkingDir: "{app}\{#StudentFolderName}"; Tasks: desktopicon

[Run]
; Clear Mark-of-the-Web from the installed application files, where Windows permits.
; This is not an antivirus bypass and does not override SmartScreen or Defender.
Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; \
    Parameters: "-NoProfile -NonInteractive -ExecutionPolicy Bypass -Command ""$p = '{app}\{#StudentFolderName}'; if (Test-Path -LiteralPath $p) {{ Get-ChildItem -LiteralPath $p -Recurse -File | Unblock-File -ErrorAction SilentlyContinue }}"""; \
    StatusMsg: "Finalizing application files..."; Flags: runhidden waituntilterminated

Filename: "{app}\{#StudentFolderName}\AgenticExamStudent.exe"; \
    WorkingDir: "{app}\{#StudentFolderName}"; Description: "Launch Agentic AI Student Examination"; Flags: postinstall nowait skipifsilent
