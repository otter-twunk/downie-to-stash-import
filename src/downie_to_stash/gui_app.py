#!/usr/bin/env python3
"""Tkinter GUI for Downie to Stash conversion."""

from __future__ import annotations

import os
import subprocess
import sys
import threading
from pathlib import Path
from typing import cast

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
except ModuleNotFoundError as error:
    TK_IMPORT_ERROR: ModuleNotFoundError | None = error
else:
    TK_IMPORT_ERROR = None

from downie_to_stash.core import ConversionConfig, run_conversion


def _tk_error_message() -> str:
    return (
        "Tkinter is not available in this Python installation. "
        "Install a Python build with Tk support to use the GUI."
    )


if TK_IMPORT_ERROR is None:

    class App(tk.Tk):
        def __init__(self) -> None:
            super().__init__()
            self.title("Downie to Stash Import Helper")
            self.geometry("900x700")

            self.json_root_var = tk.StringVar()
            self.output_root_var = tk.StringVar()
            self.details_var = tk.StringVar(value="Imported from Downie metadata")
            self.min_score_var = tk.DoubleVar(value=60.0)
            self.ambiguity_gap_var = tk.DoubleVar(value=7.5)
            self.include_date_var = tk.BooleanVar(value=True)
            self.allow_stream_url_var = tk.BooleanVar(value=False)
            self.dry_run_var = tk.BooleanVar(value=False)

            self.status_var = tk.StringVar(value="Idle")
            self.summary_matched_var = tk.StringVar(value="0")
            self.summary_unmatched_var = tk.StringVar(value="0")
            self.summary_ambiguous_var = tk.StringVar(value="0")
            self.summary_media_var = tk.StringVar(value="0")
            self.summary_output_var = tk.StringVar(value="-")

            self.media_roots: list[str] = []
            self.worker_thread: threading.Thread | None = None
            self.last_output_path: Path | None = None

            self._build_ui()

        def _build_ui(self) -> None:
            main = ttk.Frame(self, padding=10)
            main.pack(fill=tk.BOTH, expand=True)

            json_frame = ttk.LabelFrame(main, text="Downie JSON")
            json_frame.pack(fill=tk.X, pady=(0, 8))
            ttk.Label(json_frame, text="JSON folder:").grid(
                row=0, column=0, sticky="w"
            )
            ttk.Entry(
                json_frame,
                textvariable=self.json_root_var,
                width=60,
            ).grid(row=0, column=1, sticky="we", padx=4)
            ttk.Button(
                json_frame,
                text="Browse...",
                command=self._choose_json_root,
            ).grid(row=0, column=2, padx=4)
            json_frame.columnconfigure(1, weight=1)

            media_frame = ttk.LabelFrame(main, text="Media roots")
            media_frame.pack(fill=tk.BOTH, pady=(0, 8))
            self.media_list = tk.Listbox(media_frame, height=4)
            self.media_list.grid(
                row=0,
                column=0,
                rowspan=3,
                sticky="nsew",
                padx=(0, 4),
            )
            media_frame.columnconfigure(0, weight=1)
            media_frame.rowconfigure(0, weight=1)
            ttk.Button(
                media_frame,
                text="Add root...",
                command=self._add_media_root,
            ).grid(row=0, column=1, sticky="ew", pady=2)
            ttk.Button(
                media_frame,
                text="Remove selected",
                command=self._remove_media_root,
            ).grid(row=1, column=1, sticky="ew", pady=2)

            out_frame = ttk.LabelFrame(main, text="Output")
            out_frame.pack(fill=tk.X, pady=(0, 8))
            ttk.Label(out_frame, text="Output folder:").grid(
                row=0, column=0, sticky="w"
            )
            ttk.Entry(
                out_frame,
                textvariable=self.output_root_var,
                width=60,
            ).grid(row=0, column=1, sticky="we", padx=4)
            ttk.Button(
                out_frame,
                text="Browse...",
                command=self._choose_output_root,
            ).grid(row=0, column=2, padx=4)
            out_frame.columnconfigure(1, weight=1)
            ttk.Label(
                out_frame,
                text="Will create scenes/, report.json, unmatched.json, ambiguous.json",
            ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(4, 0))

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
                row=0,
                column=1,
                sticky="e",
                padx=(20, 4),
            )
            ttk.Entry(
                opt_frame,
                textvariable=self.details_var,
                width=40,
            ).grid(row=0, column=2, sticky="we", padx=(0, 4))
            ttk.Label(opt_frame, text="Min score:").grid(
                row=1,
                column=1,
                sticky="e",
                padx=(20, 4),
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
                row=2,
                column=1,
                sticky="e",
                padx=(20, 4),
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

            log_frame = ttk.Frame(main)
            log_frame.pack(fill=tk.BOTH, expand=True)
            self.log_text = tk.Text(log_frame, height=14, wrap="word")
            self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scroll = ttk.Scrollbar(
                log_frame,
                orient="vertical",
                command=self.log_text.yview,
            )
            scroll.pack(side=tk.RIGHT, fill=tk.Y)
            self.log_text.configure(yscrollcommand=scroll.set)

            summary_frame = ttk.LabelFrame(main, text="Results summary")
            summary_frame.pack(fill=tk.X, pady=(8, 0))
            ttk.Label(summary_frame, text="Matched count:").grid(
                row=0, column=0, sticky="w"
            )
            ttk.Label(summary_frame, textvariable=self.summary_matched_var).grid(
                row=0,
                column=1,
                sticky="w",
                padx=(4, 20),
            )
            ttk.Label(summary_frame, text="Unmatched count:").grid(
                row=0, column=2, sticky="w"
            )
            ttk.Label(summary_frame, textvariable=self.summary_unmatched_var).grid(
                row=0,
                column=3,
                sticky="w",
                padx=(4, 20),
            )
            ttk.Label(summary_frame, text="Ambiguous count:").grid(
                row=0, column=4, sticky="w"
            )
            ttk.Label(summary_frame, textvariable=self.summary_ambiguous_var).grid(
                row=0, column=5, sticky="w"
            )
            ttk.Label(summary_frame, text="Media files indexed:").grid(
                row=1,
                column=0,
                sticky="w",
                pady=(4, 0),
            )
            ttk.Label(summary_frame, textvariable=self.summary_media_var).grid(
                row=1,
                column=1,
                sticky="w",
                padx=(4, 20),
                pady=(4, 0),
            )
            ttk.Label(summary_frame, text="Output folder:").grid(
                row=1,
                column=2,
                sticky="w",
                pady=(4, 0),
            )
            ttk.Label(summary_frame, textvariable=self.summary_output_var).grid(
                row=1,
                column=3,
                columnspan=3,
                sticky="w",
                pady=(4, 0),
            )

            controls = ttk.Frame(main)
            controls.pack(fill=tk.X, pady=(8, 0))
            ttk.Label(controls, textvariable=self.status_var).pack(side=tk.LEFT)
            self.progress = ttk.Progressbar(
                controls,
                mode="indeterminate",
                length=160,
            )
            self.progress.pack(side=tk.LEFT, padx=(12, 0))
            self.open_output_button = ttk.Button(
                controls,
                text="Open output folder",
                command=self._open_output_folder,
                state=tk.DISABLED,
            )
            self.open_output_button.pack(side=tk.RIGHT)
            self.run_button = ttk.Button(
                controls,
                text="Run",
                command=self._on_run_clicked,
            )
            self.run_button.pack(side=tk.RIGHT, padx=(0, 8))
            self.clear_log_button = ttk.Button(
                controls,
                text="Clear log",
                command=self._clear_log,
            )
            self.clear_log_button.pack(side=tk.RIGHT, padx=(0, 8))

        def _append_log(self, message: str) -> None:
            self.log_text.insert(tk.END, message + "\n")
            self.log_text.see(tk.END)
            self.log_text.update_idletasks()

        def _clear_log(self) -> None:
            self.log_text.delete("1.0", tk.END)

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
            if path and path not in self.media_roots:
                self.media_roots.append(path)
                self.media_list.insert(tk.END, path)

        def _remove_media_root(self) -> None:
            selected = list(
                cast(
                    tuple[int, ...],
                    self.media_list.curselection(),  # type: ignore[no-untyped-call]
                )
            )
            for index in reversed(selected):
                path = str(self.media_list.get(index))
                self.media_roots.remove(path)
                self.media_list.delete(index)

        def _collect_config(self) -> ConversionConfig | None:
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
            except (tk.TclError, ValueError):
                messagebox.showerror(
                    "Error",
                    "Min score and ambiguity gap must be numbers.",
                )
                return None

            return ConversionConfig(
                json_root=Path(json_root),
                media_roots=[Path(path) for path in self.media_roots],
                output_root=Path(output_root),
                details_text=self.details_var.get(),
                min_score=min_score,
                ambiguity_gap=ambiguity_gap,
                allow_stream_url=self.allow_stream_url_var.get(),
                include_date=self.include_date_var.get(),
                dry_run=self.dry_run_var.get(),
            )

        def _set_running_state(self, running: bool) -> None:
            if running:
                self.status_var.set("Running...")
                self.run_button.config(state=tk.DISABLED, text="Running...")
                self.open_output_button.config(state=tk.DISABLED)
                self.progress.start(10)
                return
            self.progress.stop()
            self.run_button.config(state=tk.NORMAL, text="Run")

        def _update_summary(self, summary: dict[str, object]) -> None:
            self.summary_matched_var.set(str(summary.get("matched_count", 0)))
            self.summary_unmatched_var.set(str(summary.get("unmatched_count", 0)))
            self.summary_ambiguous_var.set(str(summary.get("ambiguous_count", 0)))
            self.summary_media_var.set(str(summary.get("media_indexed", 0)))
            self.summary_output_var.set(
                str(summary.get("output_root", self.output_root_var.get()))
            )

        def _on_run_clicked(self) -> None:
            config = self._collect_config()
            if config is None:
                return
            if self.worker_thread and self.worker_thread.is_alive():
                messagebox.showwarning(
                    "Running",
                    "A conversion is already in progress.",
                )
                return

            self._clear_log()
            self._set_running_state(True)
            self.last_output_path = config.output_root

            def worker() -> None:
                def worker_log(message: str) -> None:
                    self.after(0, self._append_log, message)

                try:
                    summary = run_conversion(config, log=worker_log)
                    self.after(
                        0,
                        self._on_run_done,
                        None,
                        summary,
                        config.dry_run,
                    )
                except Exception as error:  # noqa: BLE001
                    self.after(0, self._on_run_done, error, None, config.dry_run)

            self.worker_thread = threading.Thread(target=worker, daemon=True)
            self.worker_thread.start()

        def _on_run_done(
            self,
            error: Exception | None,
            summary: dict[str, object] | None,
            dry_run: bool,
        ) -> None:
            self._set_running_state(False)
            if error is not None:
                self.status_var.set("Error")
                self.open_output_button.config(state=tk.DISABLED)
                messagebox.showerror("Error", str(error))
                return
            if summary is None:
                self.status_var.set("Error")
                self.open_output_button.config(state=tk.DISABLED)
                messagebox.showerror(
                    "Error",
                    "Conversion finished without a summary.",
                )
                return

            self.status_var.set("Completed")
            self._update_summary(summary)
            if not dry_run and self.last_output_path is not None:
                self.open_output_button.config(state=tk.NORMAL)
            else:
                self.open_output_button.config(state=tk.DISABLED)
            messagebox.showinfo(
                "Done",
                "Conversion complete. Check the log and output folder.",
            )

        def _open_output_folder(self) -> None:
            if self.last_output_path is None:
                return
            output_path = str(self.last_output_path.resolve())
            try:
                if sys.platform == "darwin":
                    subprocess.Popen(["open", output_path])
                elif os.name == "nt":
                    os.startfile(output_path)  # type: ignore[attr-defined]
                else:
                    subprocess.Popen(["xdg-open", output_path])
            except Exception as error:  # noqa: BLE001
                messagebox.showerror(
                    "Error",
                    f"Failed to open output folder: {error}",
                )

else:

    class _UnavailableApp:
        def __init__(self) -> None:
            raise RuntimeError(_tk_error_message()) from TK_IMPORT_ERROR

        def mainloop(self) -> None:
            raise RuntimeError(_tk_error_message()) from TK_IMPORT_ERROR

    App = _UnavailableApp  # type: ignore[misc,assignment]


def main() -> None:
    if TK_IMPORT_ERROR is not None:
        raise RuntimeError(_tk_error_message()) from TK_IMPORT_ERROR
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
