
# Agentic AI Midterm Exam — Offline Windows Desktop MVP

A starter desktop examination system for **Agentic AI Systems Engineering, Weeks 1–7**.
It runs locally on each Windows computer and does not need the internet or a local server.

## Included
- Student desktop app with timer, navigation, autosave, image questions, and multiple question formats.
- Instructor desktop app to create an exam package from JSON, generate RSA keys, collect encrypted submissions, grade them, adjust marks, and export PDF results.
- Offline exam package format with images bundled into a ZIP.
- Student submissions encrypted with the instructor's public key; the private key remains with the instructor.
- Example exam question bank focused on Weeks 1–7, including an image-based question.

## Important security limitation
This is an MVP, not a high-stakes locked-down exam browser. Students with local administrator access or technical skills may inspect files, process memory, or modify the application. Keep the instructor private key secure, supervise the exam, and pilot the application before relying on it for official grading. A password on its own cannot make a local Windows application tamper-proof.

## Requirements
- Windows 10/11
- Python 3.11+ for running from source
- Internet is needed only to install build dependencies beforehand; the exam itself runs offline.

## Run from source (Windows PowerShell)
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python instructor_app.py
```

In the instructor app:
1. Click **Generate instructor keys** and keep `instructor_private.pem` somewhere private and backed up.
2. Click **Create exam package** and select `examples\weeks1_7_exam.json`.
3. Enter the exam title, duration and exam password when prompted. The example JSON includes sample questions; replace/edit it before the actual examination.
4. Copy the `.exam` package and `student_app.py` (or the complete packaged student-app folder) to the university common folder.

On each student PC:
```powershell
python student_app.py
```
Select the `.exam` file, enter the exam password, and begin. Submissions are written to a `submissions` folder next to the app unless another location is selected.

Back on the instructor PC:
1. Copy all student `.submission` files to one folder.
2. Open the instructor app and choose **Grade submissions**.
3. Select the instructor private key and submission folder.
4. Review marks, make adjustments if necessary, and export a PDF report.

## Build the Windows student app
Build on Windows after installing the requirements and PyInstaller:
```powershell
python -m pip install pyinstaller
pyinstaller --clean --noconfirm AgenticExamStudent.spec
```
This produces `dist\AgenticExamStudent\AgenticExamStudent.exe` and its required support files. Distribute the **entire** `dist\AgenticExamStudent` folder (for example, as a ZIP), not the EXE by itself. The folder build avoids PyInstaller's one-file runtime extraction, and the spec disables UPX compression. These choices can reduce false positives, but cannot override antivirus or school application-control policies.

Before classroom distribution, test the exact ZIP on a representative student PC. If endpoint protection or application control still blocks a file, ask school IT to review the detection and approve the application through its normal process. For managed deployments, have the EXE and bundled DLLs code-signed with a certificate trusted by the school and request publisher-based allowlisting; do not ask students to disable or bypass security controls. A code-signing certificate must be obtained separately and is not included in this project.

The instructor app can still be run from source using the earlier instructions. To build its EXE separately:
```powershell
pyinstaller --noconfirm --onefile --windowed --name AgenticExamInstructor instructor_app.py
```

## Question format
See `examples\weeks1_7_exam.json`. Supported types:
- `mcq`: one correct option; options may include text and/or images.
- `image_mcq`: reference image plus answer options; options can themselves be images.
- `true_false`
- `fill_blank`: exact or case-insensitive answer matching.
- `matching`: match labels to values using a compact `key=value; key=value` response format.
- `short_answer`: manual grading by instructor.

Question fields:
- `id`, `week`, `type`, `prompt`, `marks`
- optional `image` (relative to the JSON file)
- `options` for `mcq` / `image_mcq`; each option has `id`, `text`, optional `image`
- `answer` for auto-graded question types
- optional `explanation` (not shown to students during the exam)

The instructor package creator copies referenced images into the exam package. Use relative paths such as `images/agent_loop.png`.

## Current MVP limitations
- Questions are imported from JSON rather than authored with a full rich-text visual editor.
- Short answers require instructor grading.
- Matching uses a concise typed response, not drag-and-drop.
- PDF report layout is basic and should be validated before official use.
- This project is a starting implementation; conduct a supervised pilot and security review before an official exam.


## Automatic grading plus instructor adjustment
Objective questions are graded automatically against the answer key. Matching awards proportional partial credit per correctly matched pair. Short answers can use instructor-authored rubric keyword rules to calculate a *suggested* score; this is not semantic AI grading and can miss paraphrases, so the instructor should review those answers. In the instructor results window, select a student and choose **Review / adjust individual questions** to inspect each response and change its mark. The total is recalculated from question-level marks. PDF export includes class totals and question-level rows.


## Fix: student submission says `No such file or directory`
The student app now checks the extracted temporary directory and a nearby key file for `instructor_public.pem`. If it still reports the key is missing:
1. Open the instructor app and generate instructor keys.
2. Recreate the `.exam` package *after* generating keys.
3. Confirm the `.exam` ZIP contains `instructor_public.pem` (you can inspect a copy with 7-Zip).
4. Distribute the newly generated `.exam` package and rebuild/re-distribute `AgenticExamStudent.exe` from this updated source.
Do not distribute `instructor_private.pem`.

## Modern student interface (HTML/CSS embedded in Windows desktop)

The student client uses `pywebview` to display a responsive navy-and-blue examination interface. It includes a clickable question palette, local autosave during the session, review flags, a final review screen, and click-to-zoom question images. The instructor application remains Tkinter-based and retains the existing package, encrypted submission, grading, and PDF workflow.

On Windows PowerShell, from the project directory:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python student_app.py
```

If `pywebview` reports that its WebView2 runtime is unavailable, install the Microsoft Edge WebView2 Runtime on that PC, then launch the student app again. For classroom deployment, test on a representative student PC before the exam.

The local draft is saved in the application's temporary session directory. It is intended as in-session autosave, not as a guaranteed recovery store after Windows restarts or the temporary directory is cleaned. Student submissions are encrypted using the instructor public key embedded in the exam package; keep `instructor_private.pem` instructor-only.


## Windows WebView troubleshooting

The student interface uses pywebview. The exam-file and submission-folder dialogs use pywebview native dialogs; do not call Tkinter dialogs from the JavaScript API bridge. If WebView2 reports `E_NOINTERFACE` or controller UI-thread errors, update pywebview in the active virtual environment and install/update the Microsoft Edge WebView2 Runtime, then restart the app:

```powershell
python -m pip install --upgrade pywebview
python -m pip show pywebview
python student_app.py
```

The app requires the Microsoft Edge WebView2 Runtime on Windows. Download it from Microsoft's official WebView2 page if it is missing.


## Multiple-select questions

The student application now supports `multiple_select` questions. Students can select
several options using checkboxes; selections are saved in the normal local draft and
included in the encrypted submission. The instructor grading engine supports partial
credit with a penalty for incorrect selections.

For each multiple-select question, the score is calculated proportionally:

`score = question_marks * max(0, correct_selections - incorrect_selections) / number_of_correct_options`

The score is capped at the question's maximum marks. A fully correct selection earns
all available marks. Missing correct selections earn no points, while incorrect
selections reduce the score.

An example instructor JSON file for questions Q36-Q40 is included under `examples/`.
It contains the answer key and must not be distributed to students. The exam package
creation process removes the answer key before creating the student package.


## Staged and parallel agent workflow questions

The student app supports `visual_workflow` questions with staged execution. Agents are arranged in stages from top to bottom. Agents in the same stage are treated as parallel; the next stage starts after the preceding stage has completed.

Example question structure:

```json
{
  "id": "Q51",
  "week": 7,
  "type": "visual_workflow",
  "marks": 2,
  "prompt": "Arrange the agents for the described scenario.",
  "workflow_data": {
    "components": [
      {"id": "intake", "label": "Intake Agent"},
      {"id": "eligibility", "label": "Eligibility Agent"},
      {"id": "documents", "label": "Document Agent"},
      {"id": "notify", "label": "Communication Agent"}
    ],
    "allow_connections": false,
    "execution_model": "staged_parallel"
  }
}
```

The instructor answer key defines the expected stages:

```json
{
  "Q51": {
    "accepted_stages": [
      ["intake"],
      ["eligibility", "documents"],
      ["notify"]
    ]
  }
}
```

Students can reorder agents with the up/down controls, merge a stage with the previous stage to mark parallel execution, or split an agent out of a parallel stage into a sequential stage. Grading evaluates pairwise execution relationships: which agents must run before others and which agents must run in parallel. The answer key is excluded from the encrypted student package by `create_exam_package`.


## Student installer (Windows)

The project now includes an Inno Setup installer definition under `installer/`.

### Build on the instructor/build computer

1. Use Windows 10/11 x64.
2. Install Python 3.11 and Inno Setup 6.
3. Open PowerShell in the project root.
4. Run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\installer\Build_Student_Installer.ps1
```

The script builds the student client as a PyInstaller ONEDIR application and compiles `installer/AgenticAI_Student_Exam.iss`. The resulting installer is written to `installer_output/AgenticAI_Student_Exam_Setup.exe`.

Distribute that installer to students. They run it once; it installs the complete application folder under their own LocalAppData, creates Start Menu shortcuts, optionally creates a desktop shortcut, and runs an installation-time `Unblock-File` pass over the installed app files.

### Important Windows runtime and trust notes

- The student app uses pywebview and requires the Microsoft Edge WebView2 Runtime. The installer script does not silently download or install it. Verify that the university lab image already includes the Evergreen WebView2 Runtime, or arrange an approved offline deployment of Microsoft's runtime.
- The installer does not disable Defender, bypass SmartScreen, or override antivirus policy. `Unblock-File` only removes the Mark-of-the-Web alternate data stream where present.
- If Windows blocks the installer itself, an installation action cannot run until the installer is allowed to start. For institution-wide distribution, sign the installer with a trusted code-signing certificate and have IT deploy/trust the publisher. Do not ask students to disable security controls.
- Test the generated installer on a clean Windows 10/11 x64 machine without Python installed before the examination.
- The current installer is per-user (`PrivilegesRequired=lowest`) and does not require administrator rights. It does not install WebView2.
