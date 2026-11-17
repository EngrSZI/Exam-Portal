
import json, os, tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from pathlib import Path
from agentic_exam.crypto_utils import generate_rsa_keys, load_private_key, decrypt_submission
from agentic_exam.exam_package import create_exam_package
from agentic_exam.grading import grade_answers

class InstructorApp:
    def __init__(self, root):
        self.root = root
        root.title("Agentic AI Midterm — Instructor Console")
        root.geometry("900x650")
        self.private_key_path = ""
        self.public_key_path = ""
        self.results = []
        self.exam_spec = None
        self._build()

    def _build(self):
        frm = ttk.Frame(self.root, padding=22); frm.pack(fill="both", expand=True)
        ttk.Label(frm, text="Agentic AI Midterm — Instructor Console", font=("Segoe UI", 20, "bold")).pack(anchor="w")
        ttk.Label(frm, text="Offline tools for exam packaging, encrypted submissions, grading and PDF export.").pack(anchor="w", pady=(4, 20))
        ttk.Button(frm, text="Generate instructor keys", command=self._keys).pack(anchor="w", pady=5)
        ttk.Button(frm, text="Create exam package from JSON", command=self._package).pack(anchor="w", pady=5)
        ttk.Button(frm, text="Grade submissions", command=self._grade).pack(anchor="w", pady=5)
        ttk.Button(frm, text="Adjust marks and export PDF", command=self._export).pack(anchor="w", pady=5)
        self.status = tk.StringVar(value="Ready.")
        ttk.Label(frm, textvariable=self.status, wraplength=820).pack(anchor="w", pady=18)
        ttk.Label(frm, text="Keep instructor_private.pem private. Distribute only instructor_public.pem and the exam package.", foreground="#9b2226").pack(anchor="w", pady=8)

    def _keys(self):
        out = filedialog.askdirectory(title="Choose secure folder for instructor keys")
        if not out: return
        pw = simpledialog.askstring("Private-key password", "Set a strong password for the instructor private key:", show="*")
        if not pw: return
        try:
            self.private_key_path = str(Path(out) / "instructor_private.pem")
            self.public_key_path = str(Path(out) / "instructor_public.pem")
            generate_rsa_keys(self.private_key_path, self.public_key_path, pw)
            self.status.set(f"Keys generated. Private key: {self.private_key_path}\nPublic key: {self.public_key_path}")
            messagebox.showinfo("Keys generated", "Store instructor_private.pem securely and back it up. The student package needs only instructor_public.pem.")
        except Exception as e: messagebox.showerror("Key generation failed", str(e))

    def _package(self):
        source = filedialog.askopenfilename(title="Select exam question JSON", filetypes=[("JSON", "*.json")])
        if not source: return
        out = filedialog.asksaveasfilename(title="Save exam package", defaultextension=".exam", filetypes=[("Exam package", "*.exam")])
        if not out: return
        pw = simpledialog.askstring("Exam password", "Set exam password to share with students at exam start:", show="*")
        if not pw: return
        try:
            create_exam_package(source, out, pw)
            self.exam_spec = json.loads(Path(source).read_text(encoding="utf-8"))
            # Copy public key beside the package; include it in exam ZIP for student encryption.
            if not self.public_key_path or not Path(self.public_key_path).exists():
                messagebox.showwarning("Public key missing", "Exam package created, but submissions need an instructor public key. Generate keys first, then create the package again.")
            else:
                import zipfile
                tmp = out + ".tmp"
                with zipfile.ZipFile(out, "r") as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
                    for item in zin.infolist(): zout.writestr(item, zin.read(item.filename))
                    zout.write(self.public_key_path, "instructor_public.pem")
                os.replace(tmp, out)
            self.status.set(f"Exam package created: {out}")
            messagebox.showinfo("Package created", f"Created exam package:\n{out}\n\nDistribute this file and the student application.")
        except Exception as e: messagebox.showerror("Package creation failed", str(e))

    def _grade(self):
        folder = filedialog.askdirectory(title="Select folder containing .submission files")
        if not folder: return
        private = filedialog.askopenfilename(title="Select instructor_private.pem", filetypes=[("PEM", "*.pem")])
        if not private: return
        pw = simpledialog.askstring("Private-key password", "Enter private-key password:", show="*")
        if pw is None: return
        spec_path = filedialog.askopenfilename(title="Select original instructor exam JSON (answer key)", filetypes=[("JSON", "*.json")])
        if not spec_path: return
        try:
            key = load_private_key(private, pw)
            spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))
            self.exam_spec = spec
            self.results = []
            for p in Path(folder).glob("*.submission"):
                try:
                    payload = json.loads(decrypt_submission(p.read_bytes(), key).decode("utf-8"))
                    result = grade_answers(spec["questions"], spec.get("answer_key", {}), payload.get("answers", {}))
                    for q in spec["questions"]:
                        if q["type"] == "short_answer":
                            for row in result["rows"]:
                                if row["id"] == q["id"]:
                                    row["marks"] = 0.0
                    result["earned"] = sum(float(r["marks"]) for r in result["rows"])
                    result.update({"student_id": payload.get("student_id", "UNKNOWN"),
                                   "attempt_id": payload.get("attempt_id", ""),
                                   "exam_title": payload.get("exam_title", ""),
                                   "file": p.name})
                    self.results.append(result)
                except Exception as e:
                    self.results.append({"student_id": p.stem, "error": str(e), "file": p.name, "rows": [], "earned": 0, "total": 0})
            self.status.set(f"Processed {len(self.results)} submission(s). Short answers initially receive zero and require instructor review.")
            messagebox.showinfo("Grading complete", f"Processed {len(self.results)} submission(s).\nUse Adjust marks and export PDF to review and save results.")
        except Exception as e: messagebox.showerror("Grading failed", f"{e}")

    def _export(self):
        if not self.results:
            messagebox.showwarning("No results", "Grade submissions first.")
            return
        win = tk.Toplevel(self.root); win.title("Review and adjust marks"); win.geometry("950x600")
        cols = ("student", "earned", "total", "file")
        tree = ttk.Treeview(win, columns=cols, show="headings", height=14)
        for c, label, width in [("student","Student ID",180),("earned","Marks",100),("total","Total",100),("file","Submission",450)]:
            tree.heading(c, text=label); tree.column(c, width=width)
        tree.pack(fill="both", expand=True, padx=10, pady=10)
        for i, r in enumerate(self.results):
            tree.insert("", "end", iid=str(i), values=(r.get("student_id"), f"{r.get('earned',0):.2f}", f"{r.get('total',0):.2f}", r.get("file","")))
        ttk.Label(win, text="Select a student to review individual questions, adjust marks, and recalculate the total.").pack(anchor="w", padx=10)
        row = ttk.Frame(win, padding=10); row.pack(fill="x")
        def review_questions():
            sel = tree.selection()
            if not sel: return
            idx = int(sel[0]); result = self.results[idx]
            qwin = tk.Toplevel(win); qwin.title(f"Question review — {result.get('student_id')}"); qwin.geometry("1000x620")
            qcols = ("qid", "type", "response", "awarded", "max", "note")
            qt = ttk.Treeview(qwin, columns=qcols, show="headings", height=15)
            for c, label, width in [("qid","Question",90),("type","Type",110),("response","Student answer",260),("awarded","Marks",80),("max","Max",70),("note","Auto-grading note",300)]:
                qt.heading(c, text=label); qt.column(c, width=width)
            qt.pack(fill="both", expand=True, padx=10, pady=10)
            for j, rr in enumerate(result.get("rows", [])):
                qt.insert("", "end", iid=str(j), values=(rr.get("id"), rr.get("type"), str(rr.get("response",""))[:180], rr.get("marks",0), rr.get("max_marks",0), rr.get("grading_note","")))
            edit = ttk.Frame(qwin, padding=10); edit.pack(fill="x")
            ttk.Label(edit, text="Selected question's revised mark:").pack(side="left")
            markvar = tk.StringVar()
            ttk.Entry(edit, textvariable=markvar, width=10).pack(side="left", padx=8)
            def set_question_mark():
                qsel = qt.selection()
                if not qsel: return
                j = int(qsel[0]); rr = result["rows"][j]
                try: m = float(markvar.get())
                except ValueError: messagebox.showerror("Invalid mark", "Enter a numeric mark."); return
                mx = float(rr.get("max_marks", 0))
                if m < 0 or m > mx:
                    messagebox.showerror("Out of range", f"Enter a mark between 0 and {mx}."); return
                rr["marks"] = m; rr["adjusted"] = True; rr["grading_note"] = (rr.get("grading_note","") + " | Instructor adjusted").strip(" |")
                qt.set(str(j), "awarded", f"{m:g}")
                qt.set(str(j), "note", rr["grading_note"])
                result["earned"] = sum(float(x.get("marks",0)) for x in result.get("rows",[]))
                result["adjusted"] = True
                tree.set(str(idx), "earned", f"{result['earned']:.2f}")
            ttk.Button(edit, text="Apply mark to selected question", command=set_question_mark).pack(side="left", padx=8)
            ttk.Label(qwin, text="Auto-grading is a recommendation for rubric-based short answers; review uncertain answers before finalizing.", foreground="#9b2226").pack(anchor="w", padx=10, pady=5)
        ttk.Button(row, text="Review / adjust individual questions", command=review_questions).pack(side="left", padx=5)
        def pdf():
            out = filedialog.asksaveasfilename(title="Export PDF results", defaultextension=".pdf", filetypes=[("PDF", "*.pdf")])
            if not out: return
            try:
                from reportlab.lib.pagesizes import A4, landscape
                from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
                from reportlab.lib import colors
                from reportlab.lib.styles import getSampleStyleSheet
                styles = getSampleStyleSheet()
                doc = SimpleDocTemplate(out, pagesize=landscape(A4))
                story = [Paragraph("Agentic AI Systems Engineering — Midterm Results", styles["Title"]), Spacer(1, 14)]
                data = [["Student ID", "Marks", "Total", "Percentage", "Adjusted"]]
                for r in self.results:
                    total = float(r.get("total", 0)); earned = float(r.get("earned", 0))
                    pct = (earned / total * 100) if total else 0
                    data.append([str(r.get("student_id","")), f"{earned:.2f}", f"{total:.2f}", f"{pct:.1f}%", "Yes" if r.get("adjusted") else "No"])
                table = Table(data, repeatRows=1)
                table.setStyle(TableStyle([
                    ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#203864")),
                    ("TEXTCOLOR", (0,0), (-1,0), colors.white),
                    ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
                    ("ALIGN", (1,1), (-1,-1), "CENTER"),
                    ("PADDING", (0,0), (-1,-1), 7),
                ]))
                story.append(table)
                story.append(Spacer(1, 18))
                story.append(Paragraph("Question-level grading and adjustments", styles["Heading2"]))
                detail = [["Student ID", "Question", "Type", "Response", "Marks", "Maximum", "Review note"]]
                for r in self.results:
                    for rr in r.get("rows", []):
                        detail.append([
                            str(r.get("student_id","")), str(rr.get("id","")), str(rr.get("type","")),
                            str(rr.get("response",""))[:100], f"{float(rr.get('marks',0)):.2f}",
                            f"{float(rr.get('max_marks',0)):.2f}", str(rr.get("grading_note",""))[:90]
                        ])
                if len(detail) > 1:
                    dt = Table(detail, repeatRows=1, colWidths=[75,55,65,190,45,45,190])
                    dt.setStyle(TableStyle([
                        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#203864")),
                        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
                        ("GRID", (0,0), (-1,-1), 0.35, colors.grey),
                        ("FONTSIZE", (0,0), (-1,-1), 7),
                        ("VALIGN", (0,0), (-1,-1), "TOP"),
                        ("PADDING", (0,0), (-1,-1), 4),
                    ]))
                    story.append(dt)
                doc.build(story)
                messagebox.showinfo("PDF exported", f"Saved: {out}")
            except Exception as e: messagebox.showerror("PDF export failed", str(e))
        ttk.Button(row, text="Export PDF", command=pdf).pack(side="right", padx=5)

if __name__ == "__main__":
    root = tk.Tk()
    InstructorApp(root)
    root.mainloop()
