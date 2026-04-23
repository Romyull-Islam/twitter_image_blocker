"""
X.com Profile Photo Blocker — Desktop App
Run: python app.py
"""

import asyncio
import os
import queue
import shutil
import threading
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image

import config
from runner import run_scan
from browser_utils import find_system_chrome, any_browser_available, install_playwright_chromium

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

ACCENT   = "#1d9bf0"
DANGER   = "#e0245e"
BG_CARD  = "#1e1e2e"
FG_DIM   = "#8b9ab0"


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("X.com Profile Photo Blocker")
        self.geometry("960x720")
        self.minsize(820, 620)

        # Set window icon
        _icon = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
        if os.path.exists(_icon):
            self.iconbitmap(_icon)

        self._log_queue   = queue.Queue()
        self._stop_event  = threading.Event()
        self._scan_thread = None
        self._img_refs    = []   # keep CTkImage objects alive

        self._build_ui()
        self._refresh_images()
        self._poll_queue()
        self.after(200, self._check_chromium)

    # ── First-run browser setup ───────────────────────────────────────────────

    def _check_chromium(self):
        sys_chrome = find_system_chrome()
        if sys_chrome:
            self._append_log(f"[setup] Using system browser: {sys_chrome}")
            return
        if any_browser_available():
            self._append_log("[setup] Playwright Chromium is ready.")
            return
        self._show_chromium_setup()

    def _show_chromium_setup(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("First-time Setup")
        dialog.geometry("440x230")
        dialog.resizable(False, False)
        dialog.grab_set()
        dialog.lift()

        ctk.CTkLabel(
            dialog,
            text="Downloading Browser (one-time setup)",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(pady=(28, 6))

        ctk.CTkLabel(
            dialog,
            text="No browser found on this PC.\n"
                 "The app will download Chromium once (~170 MB) and never again.",
            font=ctk.CTkFont(size=11),
            text_color=FG_DIM,
            justify="center",
        ).pack(pady=(0, 16))

        bar = ctk.CTkProgressBar(dialog, width=360, mode="indeterminate")
        bar.pack(pady=(0, 10))
        bar.start()

        ctk.CTkLabel(
            dialog, text="Downloading...", font=ctk.CTkFont(size=11), text_color=FG_DIM
        ).pack()

        def _do_install():
            try:
                install_playwright_chromium()
                self.after(0, lambda: (bar.stop(), dialog.destroy(),
                                       self._append_log("[setup] Chromium downloaded and ready.")))
            except Exception as e:
                self.after(0, lambda: (bar.stop(), dialog.destroy(),
                                       messagebox.showerror(
                                           "Setup Failed",
                                           f"Could not download Chromium:\n{e}\n\n"
                                           "Check your internet connection and restart the app."
                                       )))

        threading.Thread(target=_do_install, daemon=True).start()

    # ── UI build ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        # ── header ───────────────────────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=0)
        hdr.pack(fill="x")

        ctk.CTkLabel(
            hdr,
            text="  X.com Profile Photo Blocker",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=ACCENT,
        ).pack(side="left", pady=14, padx=18)

        self._status_lbl = ctk.CTkLabel(
            hdr, text="Ready", font=ctk.CTkFont(size=12), text_color=FG_DIM
        )
        self._status_lbl.pack(side="right", padx=18)

        # ── two-column middle area ────────────────────────────────────────────
        mid = ctk.CTkFrame(self, fg_color="transparent")
        mid.pack(fill="both", expand=True, padx=16, pady=12)
        mid.columnconfigure(0, weight=3)
        mid.columnconfigure(1, weight=2)
        mid.rowconfigure(0, weight=1)

        self._build_left_panel(mid)
        self._build_right_panel(mid)

        # ── action bar ───────────────────────────────────────────────────────
        bar = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=0)
        bar.pack(fill="x", side="bottom")

        self._start_btn = ctk.CTkButton(
            bar, text="▶  Start Scan",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=ACCENT, hover_color="#1a8cd8",
            width=160, height=40,
            command=self._start_scan,
        )
        self._start_btn.pack(side="left", padx=14, pady=10)

        self._stop_btn = ctk.CTkButton(
            bar, text="■  Stop",
            fg_color=DANGER, hover_color="#b01c4b",
            width=100, height=40,
            state="disabled",
            command=self._stop_scan,
        )
        self._stop_btn.pack(side="left", padx=(0, 14))

        self._stats_lbl = ctk.CTkLabel(
            bar, text="Scanned: 0  |  Blocked: 0",
            font=ctk.CTkFont(size=12), text_color=FG_DIM,
        )
        self._stats_lbl.pack(side="right", padx=18)

    def _build_left_panel(self, parent):
        frame = ctk.CTkFrame(parent, fg_color=BG_CARD)
        frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        frame.rowconfigure(1, weight=1)
        frame.rowconfigure(3, weight=2)

        # Reference images section
        ctk.CTkLabel(
            frame, text="Reference Images",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=14, pady=(14, 2))

        ctk.CTkLabel(
            frame,
            text="Accounts whose profile photo matches any of these will be blocked.",
            font=ctk.CTkFont(size=11), text_color=FG_DIM, wraplength=380, justify="left",
        ).grid(row=0, column=0, sticky="sw", padx=14, pady=(36, 0))

        self._img_scroll = ctk.CTkScrollableFrame(frame, label_text="", fg_color="transparent")
        self._img_scroll.grid(row=1, column=0, sticky="nsew", padx=10, pady=6)

        ctk.CTkButton(
            frame, text="+ Add Images", width=140,
            command=self._add_images,
        ).grid(row=2, column=0, sticky="w", padx=14, pady=(2, 10))

        # Progress log section
        ctk.CTkLabel(
            frame, text="Progress Log",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=3, column=0, sticky="nw", padx=14, pady=(6, 2))

        self._log_box = ctk.CTkTextbox(
            frame,
            font=ctk.CTkFont(family="Courier", size=11),
            wrap="word",
            state="disabled",
        )
        self._log_box.grid(row=3, column=0, sticky="nsew", padx=10, pady=(28, 10))

    def _build_right_panel(self, parent):
        frame = ctk.CTkFrame(parent, fg_color=BG_CARD)
        frame.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        ctk.CTkLabel(
            frame, text="Settings",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=16, pady=(16, 12))

        # ── Sensitivity ───────────────────────────────────────────────────────
        ctk.CTkLabel(
            frame, text="Matching Sensitivity",
            font=ctk.CTkFont(size=12, weight="bold"),
        ).pack(anchor="w", padx=16)

        ctk.CTkLabel(
            frame,
            text="Move left for strict (fewer false positives).\nMove right for loose (catches more variations).",
            font=ctk.CTkFont(size=10), text_color=FG_DIM, justify="left",
        ).pack(anchor="w", padx=16, pady=(2, 4))

        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=(0, 4))

        self._thresh_val = ctk.CTkLabel(row, text=str(config.HASH_THRESHOLD), width=28)
        self._thresh_val.pack(side="right")

        self._thresh_slider = ctk.CTkSlider(
            row, from_=0, to=20, number_of_steps=20,
            command=lambda v: self._thresh_val.configure(text=str(int(float(v)))),
        )
        self._thresh_slider.set(config.HASH_THRESHOLD)
        self._thresh_slider.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(
            frame, text="← Strict          Loose →",
            font=ctk.CTkFont(size=10), text_color=FG_DIM,
        ).pack(anchor="w", padx=16, pady=(0, 14))

        ctk.CTkFrame(frame, height=1, fg_color="#333344").pack(fill="x", padx=16, pady=4)

        # ── Numeric settings ──────────────────────────────────────────────────
        fields = [
            ("Max Followers to Scan",  "max_followers",  config.MAX_FOLLOWERS_SCAN),
            ("Max Following to Scan",  "max_following",  config.MAX_FOLLOWING_SCAN),
            ("2nd-Level Accounts",     "second_level",   config.MAX_SECOND_LEVEL_USERS),
            ("Per 2nd-Level Account",  "second_per",     config.MAX_SECOND_LEVEL_PER_USER),
        ]

        self._vars = {}
        for label, key, default in fields:
            ctk.CTkLabel(
                frame, text=label, font=ctk.CTkFont(size=12, weight="bold"),
            ).pack(anchor="w", padx=16, pady=(12, 2))
            var = ctk.StringVar(value=str(default))
            self._vars[key] = var
            ctk.CTkEntry(frame, textvariable=var, width=100).pack(anchor="w", padx=16)

        ctk.CTkFrame(frame, height=1, fg_color="#333344").pack(fill="x", padx=16, pady=16)

        # ── Reset scan history ────────────────────────────────────────────────
        ctk.CTkLabel(
            frame, text="Reset",
            font=ctk.CTkFont(size=12, weight="bold"),
        ).pack(anchor="w", padx=16)

        ctk.CTkLabel(
            frame,
            text="Clear history so previously scanned\naccounts are checked again.",
            font=ctk.CTkFont(size=10), text_color=FG_DIM, justify="left",
        ).pack(anchor="w", padx=16, pady=(2, 6))

        ctk.CTkButton(
            frame, text="Clear Scan History",
            fg_color="#333344", hover_color="#444466",
            command=self._clear_history,
        ).pack(anchor="w", padx=16)

    # ── Reference images ──────────────────────────────────────────────────────

    def _refresh_images(self):
        for w in self._img_scroll.winfo_children():
            w.destroy()
        self._img_refs.clear()

        os.makedirs(config.REFERENCE_IMAGES_DIR, exist_ok=True)
        supported = ('.png', '.jpg', '.jpeg', '.webp', '.bmp')
        files = [f for f in sorted(os.listdir(config.REFERENCE_IMAGES_DIR))
                 if f.lower().endswith(supported)]

        if not files:
            ctk.CTkLabel(
                self._img_scroll,
                text="No images yet.\nClick '+ Add Images' to add reference photos.",
                text_color=FG_DIM, justify="center",
            ).pack(pady=20)
            return

        for filename in files:
            path = os.path.join(config.REFERENCE_IMAGES_DIR, filename)
            row = ctk.CTkFrame(self._img_scroll, fg_color="#2a2a3e", corner_radius=8)
            row.pack(fill="x", pady=3, padx=2)

            try:
                pil = Image.open(path)
                pil.thumbnail((44, 44))
                ctkimg = ctk.CTkImage(pil, size=(44, 44))
                self._img_refs.append(ctkimg)
                ctk.CTkLabel(row, image=ctkimg, text="").pack(side="left", padx=8, pady=6)
            except Exception:
                ctk.CTkLabel(row, text="?", width=44).pack(side="left", padx=8, pady=6)

            ctk.CTkLabel(
                row, text=filename, anchor="w",
                font=ctk.CTkFont(size=11),
            ).pack(side="left", fill="x", expand=True)

            ctk.CTkButton(
                row, text="✕", width=30, height=28,
                fg_color=DANGER, hover_color="#b01c4b",
                command=lambda f=filename: self._remove_image(f),
            ).pack(side="right", padx=6, pady=6)

    def _add_images(self):
        paths = filedialog.askopenfilenames(
            title="Select reference profile photos",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.webp *.bmp")],
        )
        for src in paths:
            dst = os.path.join(config.REFERENCE_IMAGES_DIR, os.path.basename(src))
            shutil.copy2(src, dst)
        self._refresh_images()

    def _remove_image(self, filename):
        path = os.path.join(config.REFERENCE_IMAGES_DIR, filename)
        if os.path.exists(path):
            os.remove(path)
        self._refresh_images()

    # ── Scan control ──────────────────────────────────────────────────────────

    def _start_scan(self):
        supported = ('.png', '.jpg', '.jpeg', '.webp', '.bmp')
        imgs = [f for f in os.listdir(config.REFERENCE_IMAGES_DIR)
                if f.lower().endswith(supported)]
        if not imgs:
            messagebox.showwarning(
                "No Reference Images",
                "Please add at least one reference profile photo before scanning."
            )
            return

        # Apply settings
        try:
            config.HASH_THRESHOLD          = int(float(self._thresh_slider.get()))
            config.MAX_FOLLOWERS_SCAN      = int(self._vars['max_followers'].get())
            config.MAX_FOLLOWING_SCAN      = int(self._vars['max_following'].get())
            config.MAX_SECOND_LEVEL_USERS  = int(self._vars['second_level'].get())
            config.MAX_SECOND_LEVEL_PER_USER = int(self._vars['second_per'].get())
        except ValueError:
            messagebox.showerror("Invalid Settings", "All settings must be whole numbers.")
            return

        self._stop_event.clear()
        self._start_btn.configure(state="disabled")
        self._stop_btn.configure(state="normal")
        self._set_status("Running...")

        self._scan_thread = threading.Thread(target=self._thread_target, daemon=True)
        self._scan_thread.start()

    def _thread_target(self):
        try:
            asyncio.run(run_scan(self._log_queue, self._stop_event))
        except Exception as e:
            self._log_queue.put({'type': 'error', 'message': str(e)})

    def _stop_scan(self):
        self._stop_event.set()
        self._stop_btn.configure(state="disabled")
        self._set_status("Stopping...")

    # ── Queue polling ─────────────────────────────────────────────────────────

    def _poll_queue(self):
        try:
            while True:
                item = self._log_queue.get_nowait()
                t = item['type']
                if t == 'log':
                    self._append_log(item['message'])
                elif t == 'status':
                    self._set_status(item['message'])
                elif t == 'stats':
                    self._stats_lbl.configure(
                        text=f"Scanned: {item['scanned']}  |  Blocked: {item['blocked']}"
                    )
                elif t == 'done':
                    self._append_log("\n" + item['message'])
                    self._on_done()
                elif t == 'error':
                    self._on_done()
                    messagebox.showerror("Error", item['message'])
        except Exception:
            pass
        self.after(150, self._poll_queue)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _append_log(self, msg):
        self._log_box.configure(state="normal")
        self._log_box.insert("end", msg + "\n")
        self._log_box.see("end")
        self._log_box.configure(state="disabled")

    def _set_status(self, msg):
        self._status_lbl.configure(text=msg)

    def _on_done(self):
        self._start_btn.configure(state="normal")
        self._stop_btn.configure(state="disabled")
        self._set_status("Done")

    def _clear_history(self):
        if messagebox.askyesno(
            "Clear Scan History",
            "This will make the app re-scan all accounts it has already seen.\nContinue?"
        ):
            if os.path.exists(config.SCANNED_USERS_FILE):
                os.remove(config.SCANNED_USERS_FILE)
            self._append_log("[info] Scan history cleared.")


if __name__ == "__main__":
    app = App()
    app.mainloop()
