"""Graphical user interface for student agent pairing and running."""

import os
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk

import httpx

from epp_agent.__main__ import ApiClient, Detector
from epp_agent.credentials import default_store
from epp_agent.execute import WindowsInstaller
from epp_agent.loop import process_once

DEFAULT_SERVER = "https://epp-api-7bhi.onrender.com"


class AgentGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Environment Provisioning Platform - Student Agent")
        self.root.geometry("560x420")
        self.root.minsize(500, 380)

        # Apply a clean modern theme
        self.style = ttk.Style()
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass

        self.store = default_store()
        self.is_running = False
        self.worker_thread = None

        self._build_ui()
        self._check_initial_state()

    def _build_ui(self) -> None:
        # Header banner
        header = ttk.Frame(self.root, padding="15 15 15 10")
        header.pack(fill="x")
        ttk.Label(
            header,
            text="Student Machine Agent",
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor="w")
        ttk.Label(
            header,
            text="Pairs your machine securely with your course environment.",
            font=("Segoe UI", 9),
            foreground="#555",
        ).pack(anchor="w", pady=(2, 0))

        # Main content
        content = ttk.Frame(self.root, padding="15 5 15 15")
        content.pack(fill="both", expand=True)

        # Server URL input
        ttk.Label(content, text="Platform Server URL:", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        self.server_var = tk.StringVar(value=self.store.load("server") or DEFAULT_SERVER)
        self.server_entry = ttk.Entry(content, textvariable=self.server_var)
        self.server_entry.pack(fill="x", pady=(2, 10))

        # Pairing frame
        self.pair_frame = ttk.LabelFrame(content, text="Pair Device", padding="12")
        self.pair_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(
            self.pair_frame,
            text="Enter the 8-character Pairing Code from your dashboard:",
            font=("Segoe UI", 9),
        ).pack(anchor="w")

        code_row = ttk.Frame(self.pair_frame)
        code_row.pack(fill="x", pady=(5, 0))

        self.code_var = tk.StringVar()
        self.code_entry = ttk.Entry(code_row, textvariable=self.code_var, font=("Consolas", 14), width=12)
        self.code_entry.pack(side="left", padx=(0, 10))

        self.pair_btn = ttk.Button(code_row, text="Pair Device", command=self._pair_device)
        self.pair_btn.pack(side="left")

        # Status & Control Frame
        self.control_frame = ttk.LabelFrame(content, text="Agent Service Status", padding="12")
        self.control_frame.pack(fill="both", expand=True)

        status_row = ttk.Frame(self.control_frame)
        status_row.pack(fill="x", pady=(0, 5))

        ttk.Label(status_row, text="Status:", font=("Segoe UI", 9, "bold")).pack(side="left")
        self.status_lbl = ttk.Label(
            status_row,
            text="Not Paired",
            foreground="#b45309",
            font=("Segoe UI", 9, "bold"),
        )
        self.status_lbl.pack(side="left", padx=(6, 0))

        self.start_btn = ttk.Button(
            self.control_frame,
            text="Start Agent Polling",
            command=self._toggle_agent,
            state="disabled",
        )
        self.start_btn.pack(fill="x", pady=(5, 5))

        # Log box
        ttk.Label(self.control_frame, text="Activity Log:", font=("Segoe UI", 8)).pack(anchor="w")
        self.log_text = tk.Text(self.control_frame, height=5, font=("Consolas", 8), bg="#f8f9fa", state="disabled")
        self.log_text.pack(fill="both", expand=True, pady=(2, 0))

    def _log(self, message: str) -> None:
        self.log_text.config(state="normal")
        self.log_text.insert("end", f"[{time.strftime('%H:%M:%S')}] {message}\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def _check_initial_state(self) -> None:
        cred = self.store.load("device_credential")
        if cred:
            self.status_lbl.config(text="Paired (Ready to start)", foreground="#15803d")
            self.start_btn.config(state="normal")
            self._log("Device credential loaded from Windows DPAPI.")
        else:
            self.status_lbl.config(text="Not Paired (Enter code above)", foreground="#b45309")
            self.start_btn.config(state="disabled")

    def _pair_device(self) -> None:
        code = self.code_var.get().strip().upper()
        server = self.server_var.get().strip().rstrip("/")
        if not code or len(code) < 6:
            messagebox.showwarning("Invalid Code", "Please enter a valid pairing code from your dashboard.")
            return

        self._log(f"Pairing with {server} using code {code}...")
        self.pair_btn.config(state="disabled")

        def task():
            try:
                display_name = os.environ.get("COMPUTERNAME", "Windows Device")
                resp = httpx.post(
                    f"{server}/api/v1/devices/pair",
                    json={"code": code, "display_name": display_name, "platform": "windows"},
                    timeout=20,
                )
                if 200 <= resp.status_code < 300:
                    token = resp.json()["device_credential"]
                    self.store.save("device_credential", token)
                    self.store.save("server", server)
                    self.root.after(0, self._on_pair_success)
                else:
                    msg = resp.json().get("error", {}).get("message", "Pairing failed")
                    self.root.after(0, lambda m=msg: self._on_pair_error(m))
            except (httpx.HTTPError, OSError, ValueError) as exc:
                err_text = str(exc)
                self.root.after(0, lambda e=err_text: self._on_pair_error(e))

        threading.Thread(target=task, daemon=True).start()

    def _on_pair_success(self) -> None:
        self.pair_btn.config(state="normal")
        self.code_var.set("")
        self._log("Device paired successfully! DPAPI credential saved.")
        messagebox.showinfo("Success", "Device paired successfully! Click 'Start Agent Polling' to begin.")
        self._check_initial_state()

    def _on_pair_error(self, message: str) -> None:
        self.pair_btn.config(state="normal")
        self._log(f"Error: {message}")
        messagebox.showerror("Pairing Error", message)

    def _toggle_agent(self) -> None:
        if self.is_running:
            self.is_running = False
            self.start_btn.config(text="Start Agent Polling")
            self.status_lbl.config(text="Stopped", foreground="#6b7280")
            self._log("Agent stopped.")
        else:
            self.is_running = True
            self.start_btn.config(text="Stop Agent")
            self.status_lbl.config(text="Active (Polling for work...)", foreground="#0284c7")
            self._log("Agent started. Polling cloud API...")
            self.worker_thread = threading.Thread(target=self._run_loop, daemon=True)
            self.worker_thread.start()

    def _run_loop(self) -> None:
        server = self.server_var.get().strip().rstrip("/")
        cred = self.store.load("device_credential")
        client = ApiClient(server, cred)
        detector = Detector()
        installer = WindowsInstaller()

        while self.is_running:
            try:
                job = process_once(client, detector, installer)
                if job:
                    status = job.get("status")
                    self.root.after(0, lambda s=status: self._log(f"Job update: Status is '{s}'"))
                time.sleep(3)
            except (httpx.HTTPError, OSError, RuntimeError, ValueError) as exc:
                err_text = str(exc)
                self.root.after(0, lambda e=err_text: self._log(f"Network polling notice: {e}"))
                time.sleep(10)


def main() -> None:
    root = tk.Tk()
    AgentGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
