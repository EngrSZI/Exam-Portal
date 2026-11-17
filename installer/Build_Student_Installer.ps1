$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    py -3.11 -m venv .venv
}
& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip setuptools wheel
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
& ".\.venv\Scripts\python.exe" -m pip install --upgrade pyinstaller

# Build the student application as ONEDIR. Do not distribute only the EXE.
& ".\.venv\Scripts\python.exe" -m PyInstaller --clean --noconfirm AgenticExamStudent.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller student build failed." }

# Compile the installer. Install Inno Setup 6 on the build computer first.
$iscc = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
if (-not (Test-Path $iscc)) {
    $iscc = "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
}
if (-not (Test-Path $iscc)) {
    throw "Inno Setup 6 compiler (ISCC.exe) not found. Install Inno Setup 6, then rerun this script."
}
& $iscc ".\installer\AgenticAI_Student_Exam.iss"
if ($LASTEXITCODE -ne 0) { throw "Inno Setup compilation failed." }

Write-Host "Installer created in installer_output." -ForegroundColor Green
