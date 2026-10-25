#!/usr/bin/env python3
"""ListClean Local desktop shell (tkinter). Pick a list file -> clean & re-check."""
import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from list_clean import run_listclean


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ListClean Local — Email List Cleaning (Private)")
        self.geometry("680x520")
        self.src = tk.StringVar()
        tk.Label(self, text="Email list file (.csv with an email column, or .txt one per line):").pack(anchor="w", padx=12, pady=(12, 2))
        row = tk.Frame(self)
        row.pack(fill="x", padx=12)
        tk.Entry(row, textvariable=self.src).pack(side="left", fill="x", expand=True)
        tk.Button(row, text="Browse…", command=self.pick).pack(side="left", padx=6)
        self.btn = tk.Button(self, text="Clean & Re-Check", command=self.run, height=2)
        self.btn.pack(pady=12)
        self.log = scrolledtext.ScrolledText(self, wrap="word")
        self.log.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.write("ListClean validates, de-duplicates and sorts your email list into\n"
                   "clean / rejected / flagged files, then re-validates the result.\n"
                   "Everything runs locally — your subscriber list is never uploaded.\n")

    def write(self, s):
        self.log.insert("end", s)
        self.log.see("end")

    def pick(self):
        p = filedialog.askopenfilename(filetypes=[("List files", "*.csv *.txt"), ("All files", "*.*")])
        if p:
            self.src.set(p)

    def run(self):
        src = self.src.get().strip()
        if not src or not os.path.isfile(src):
            messagebox.showerror("ListClean Local", "Choose a list file first.")
            return
        self.btn.config(state="disabled")
        threading.Thread(target=self._work, args=(src,), daemon=True).start()

    def _work(self, src):
        try:
            outdir = os.path.join(os.path.dirname(src), "listclean_output")
            s = run_listclean(src, outdir)
            self.write(f"\nDone. Rows read: {s['total']} · clean: {s['cleaned']} · "
                       f"duplicates removed: {s['duplicates']} · invalid: {s['rejects']} · "
                       f"disposable flagged: {s['flagged']}\n"
                       f"Cleaned list: {s['clean_path']}\nRejects/flagged: {s['reject_path']}\n"
                       f"Report: {s['report_path']}\nVerdict: {s['verdict']}\n")
        except Exception as e:
            self.write(f"\nError: {e}\n")
        finally:
            self.btn.config(state="normal")


if __name__ == "__main__":
    App().mainloop()
