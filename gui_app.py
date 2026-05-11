#!/usr/bin/env python3
"""Tkinter GUI for Downie → Stash conversion.

- Lets user pick:
  - Downie JSON folder
  - one or more media roots
  - output folder
- Exposes knobs for score threshold, ambiguity gap, date/URL behavior
- Runs the conversion in a worker thread and streams logs into a text box
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Optional

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from core import ConversionConfig, run_conversion


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Downie → Stash Import Helper")
        self.geometry("800x600")

        self.json_root_var = tk.StringVar()
        self.output_root_var = tk.StringVar()
        self.details_var = tk.StringVar(value="Imported from Downie metadata")
        self.min_score_var = tk.DoubleVar(value=60.0)
        self.ambiguity_gap_var = tk.DoubleVar(value=7.5)
        self.include_date_var = tk.BooleanVar(value=True)
        self.allow_stream_url_var = tk.BooleanVar(value=False)
        self.dry_run_var = tk.BooleanVar(value=False)

        self.media_roots: list[str] = []

        self._build_ui()
        self.worker_thread: Optional[threading.Thread] = None

    # ---------- UI building ----------

    def _build_ui(self) -> None:
        main = ttk.Frame(self, padding=10)
        main.pack(fill=tk.BOTH, expand=True)

        # JSON root
        json_frame = ttk.LabelFrame(main, text="Downie JSON")
        json_frame.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(json_frame, text="JSON folder:").grid(row=0, column=0, sticky="w")
        json_entry = ttk.Entry(json_frame, textvariable=self.json_root_var, width=60)
        json_entry.grid(row=0, column=1, sticky="we", padx=4)
        ttk.Button(json_frame, text="Browse…", command=self._choose_json_root).grid(
            row=0, column=2, padx=4
        )
        json_frame.columnconfigure(1, weight=1)

        # Media roots
        media_frame = ttk.LabelFrame(main, text="Media roots")
        media_frame.pack(fill=tk.BOTH, pady=(0, 8))
        self.media_list = tk.Listbox(media_frame, height=4)
        self.media_list.grid(row=0, column=0, rowspan=3, sticky="nsew", padx=(0, 4))
        media_frame.columnconfigure(0, weight=1)
        media_frame.rowconfigure(0, weight=1)
        ttk.Button(media_frame, text="Add root…", command=self._add_media_root).grid(
            row=0, column=1, sticky="ew", pady=2
        )
        ttk.Button(
            media_frame,
            text="Remove selected",
            command=self._remove_media_root,
        ).grid(row=1, column=1, sticky="ew", pady=2)

        # Output
        out_frame = ttk.LabelFrame(main, text="Output")
        out_frame.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(out_frame, text="Output folder:").grid(row=0, column=0, sticky="w")
        out_entry = ttk.Entry(out_frame, textvariable=self.output_root_var, width=60)
        out_entry.grid(row=0, column=1, sticky="we", padx=4)
        ttk.Button(out_frame, text="Browse…", command=self._choose_output_root).grid(
            row=0, column=2, padx=4
        )
        out_frame.columnconfigure(1, weight=1)
        ttk.Label(
            out_frame,
            text="Will create scenes/, report.json, unmatched.json, ambiguous.json",
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(4, 0))

        # Options
        opt_frame = ttk.LabelFrame(main, text="Options")
        opt_frame.pack(fill=tk.X, pady=(0, 8))

        ttk.Checkbutton(
            opt_frame,
            text="Include date from Downie",
            variable=self.include_date_var,
        ).grid(row=0, column=0, sticky="w")
        ttk.Checkbutton(
            opt_frame,
            text="Allow stream URL when no referer",
            variable=self.allow_stream_url_var,
        ).grid(row=1, column=0, sticky="w")
        ttk.Checkbutton(
            opt_frame,
            text="Dry run (no scene JSON files)",
            variable=self.dry_run_var,
        ).grid(row=2, column=0, sticky="w")

        ttk.Label(opt_frame, text="Details text:").grid(
            row=0, column=1, sticky="e", padx=(20, 4)
        )
        ttk.Entry(opt_frame, textvariable=self.details_var, width=40).grid(
            row=0, column=2, sticky="we", padx=(0, 4)
        )

        ttk.Label(opt_frame, text="Min score:").grid(
            row=1, column=1, sticky="e", padx=(20, 4)
        )
        ttk.Spinbox(
            opt_frame,
            from_=0,
            to=200,
            increment=1,
            textvariable=self.min_score_var,
            width=6,
        ).grid(row=1, column=2, sticky="w")

        ttk.Label(opt_frame, text="Ambiguity gap:").grid(
            row=2, column=1, sticky="e", padx=(20, 4)
        )
        ttk.Spinbox(
            opt_frame,
            from_=0,
            to=50,
            increment=0.5,
            textvariable=self.ambiguity_gap_var,
            width=6,
        ).grid(row=2, column=2, sticky="w")

        opt_frame.columnconfigure(2, weight=1)

        # Log + run
        run_frame = ttk.Frame(main)
        run_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = tk.Text(run_frame, height=15, wrap="word")
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll = ttk.Scrollbar(
            run_frame, orient="vertical", command=self.log_text.yview
        )
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.configure(yscrollcommand=scroll.set)

        bottom = ttk.Frame(main)
        bottom.pack(fill=tk.X, pady=(8, 0))
        self.run_button = ttk.Button(bottom, text="Run", command=self._on_run_clicked)
        self.run_button.pack(side=tk.RIGHT)
        self.status_var = tk.StringVar(value="Idle")
        ttk.Label(bottom, textvariable=self.status_var).pack(side=tk.LEFT)

    # ---------- Helper methods ----------

    def _append_log(self, msg: str) -> None:
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)
        self.log_text.update_idletasks()

    def _choose_json_root(self) -> None:
        path = filedialog.askdirectory(title="Select Downie JSON folder")
        if path:
            self.json_root_var.set(path)

    def _choose_output_root(self) -> None:
        path = filedialog.askdirectory(
            title="Select output folder (Stash import bundle)"
        )
        if path:
            self.output_root_var.set(path)

    def _add_media_root(self) -> None:
        path = filedialog.askdirectory(title="Select media root")
        if not path:
            return
        if path not in self.media_roots:
            self.media_roots.append(path)
            self.media_list.insert(tk.END, path)

    def _remove_media_root(self) -> None:
        sel = list(self.media_list.curselection())
        if not sel:
            return
        for index in reversed(sel):
            path = self.media_list.get(index)
            self.media_roots.remove(path)
            self.media_list.delete(index)

    def _collect_config(self) -> Optional[ConversionConfig]:
        json_root = self.json_root_var.get().strip()
        if not json_root:
            messagebox.showerror("Error", "Please select a JSON folder.")
            return None

        if not self.media_roots:
            messagebox.showerror("Error", "Please add at least one media root.")
            return None

        output_root = self.output_root_var.get().strip()
        if not output_root:
            messagebox.showerror("Error", "Please select an output folder.")
            return None

        try:
            min_score = float(self.min_score_var.get())
            ambiguity_gap = float(self.ambiguity_gap_var.get())
        except ValueError:
            messagebox.showerror(
                "Error", "Min score and ambiguity gap must be numbers."
            )
            return None

        return ConversionConfig(
            json_root=Path(json_root),
            media_roots=[Path(p) for p in self.media_roots],
            output_root=Path(output_root),
            details_text=self.details_var.get(),
            min_score=min_score,
            ambiguity_gap=ambiguity_gap,
            allow_stream_url=self.allow_stream_url_var.get(),
            include_date=self.include_date_var.get(),
            dry_run=self.dry_run_var.get(),
        )

    # ---------- Run handling ----------

    def _on_run_clicked(self) -> None:
        config = self._collect_config()
        if not config:
            return

        if self.worker_thread and self.worker_thread.is_alive():
            messagebox.showwarning("Running", "A conversion is already in progress.")
            return

        self.log_text.delete("1.0", tk.END)
        self.status_var.set("Running…")
        self.run_button.config(state=tk.DISABLED)

        def worker() -> None:
            try:
                run_conversion(
                    config,
                    log=lambda m: self.after(0, self._append_log, m),
                )
                self.after(0, self._on_run_done, None)
            except Exception as e:  # noqa: BLE001
                self.after(0, self._on_run_done, e)

        self.worker_thread = threading.Thread(target=worker, daemon=True)
        self.worker_thread.start()

    def _on_run_done(self, error: Optional[Exception]) -> None:
        self.run_button.config(state=tk.NORMAL)
        if error:
            self.status_var.set("Error")
            messagebox.showerror("Error", str(error))
        else:
            self.status_var.set("Completed")
            messagebox.showinfo(
                "Done",
                "Conversion complete. Check the log and output folder.",
            )


def main() -> None:
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
