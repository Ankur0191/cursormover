from __future__ import annotations

import math
import random
import threading
import time
import tkinter as tk
from dataclasses import dataclass
from tkinter import messagebox

import customtkinter as ctk
import pyautogui
from pynput import keyboard, mouse


APP_NAME = "CursorMover"
MIN_INTERVAL = 1
MAX_INTERVAL = 60
MIN_RADIUS = 5
MAX_RADIUS = 250
USER_INPUT_PAUSE_SECONDS = 3.0


@dataclass
class Settings:
    interval: float = 5.0
    radius: int = 35
    smooth: bool = True


class CursorMoverApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_NAME)
        self.geometry("460x540")
        self.minsize(420, 500)
        self.resizable(False, False)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.settings = Settings()
        self.running = threading.Event()
        self.shutdown = threading.Event()
        self.last_user_input = 0.0
        self.last_programmatic_move = 0.0
        self.worker: threading.Thread | None = None
        self.mouse_listener: mouse.Listener | None = None
        self.keyboard_listener: keyboard.Listener | None = None

        self.interval_var = tk.DoubleVar(value=self.settings.interval)
        self.radius_var = tk.IntVar(value=self.settings.radius)
        self.smooth_var = tk.BooleanVar(value=True)

        self._build_ui()
        self._start_input_listeners()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(self, corner_radius=16)
        header.grid(row=0, column=0, padx=22, pady=(22, 12), sticky="ew")
        ctk.CTkLabel(
            header, text="CursorMover", font=ctk.CTkFont(size=26, weight="bold")
        ).pack(anchor="w", padx=20, pady=(18, 2))
        ctk.CTkLabel(
            header,
            text="Gentle, random cursor movement for Windows",
            text_color="gray",
            font=ctk.CTkFont(size=12),
        ).pack(anchor="w", padx=20, pady=(0, 18))

        controls = ctk.CTkFrame(self, corner_radius=16)
        controls.grid(row=1, column=0, padx=22, pady=10, sticky="ew")
        controls.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            controls, text="MOVEMENT INTERVAL", font=ctk.CTkFont(size=11, weight="bold")
        ).grid(row=0, column=0, padx=18, pady=(18, 4), sticky="w")
        self.interval_value = ctk.CTkLabel(
            controls, text="5 seconds", font=ctk.CTkFont(size=22, weight="bold")
        )
        self.interval_value.grid(row=1, column=0, padx=18, sticky="w")
        ctk.CTkSlider(
            controls,
            from_=MIN_INTERVAL,
            to=MAX_INTERVAL,
            number_of_steps=59,
            variable=self.interval_var,
            command=self._update_interval_label,
        ).grid(row=2, column=0, padx=18, pady=(8, 16), sticky="ew")

        ctk.CTkLabel(
            controls, text="MOVEMENT RADIUS", font=ctk.CTkFont(size=11, weight="bold")
        ).grid(row=3, column=0, padx=18, pady=(6, 4), sticky="w")
        self.radius_value = ctk.CTkLabel(
            controls, text="35 pixels", font=ctk.CTkFont(size=18, weight="bold")
        )
        self.radius_value.grid(row=4, column=0, padx=18, sticky="w")
        ctk.CTkSlider(
            controls,
            from_=MIN_RADIUS,
            to=MAX_RADIUS,
            number_of_steps=49,
            variable=self.radius_var,
            command=self._update_radius_label,
        ).grid(row=5, column=0, padx=18, pady=(8, 15), sticky="ew")

        ctk.CTkSwitch(
            controls,
            text="Smooth curved movement",
            variable=self.smooth_var,
            onvalue=True,
            offvalue=False,
        ).grid(row=6, column=0, padx=18, pady=(4, 18), sticky="w")

        status = ctk.CTkFrame(self, corner_radius=14)
        status.grid(row=2, column=0, padx=22, pady=10, sticky="ew")
        self.status_dot = ctk.CTkLabel(
            status, text="●", text_color="#9CA3AF", font=ctk.CTkFont(size=18)
        )
        self.status_dot.pack(side="left", padx=(16, 8), pady=12)
        self.status_label = ctk.CTkLabel(
            status, text="Stopped", font=ctk.CTkFont(size=13, weight="bold")
        )
        self.status_label.pack(side="left", pady=12)
        self.count_label = ctk.CTkLabel(status, text="0 movements", text_color="gray")
        self.count_label.pack(side="right", padx=16, pady=12)
        self.movement_count = 0

        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.grid(row=3, column=0, padx=22, pady=(8, 4), sticky="ew")
        buttons.grid_columnconfigure((0, 1), weight=1)
        self.start_button = ctk.CTkButton(
            buttons, text="Start", height=44, command=self.start
        )
        self.start_button.grid(row=0, column=0, padx=(0, 6), sticky="ew")
        self.stop_button = ctk.CTkButton(
            buttons,
            text="Stop",
            height=44,
            fg_color="#374151",
            hover_color="#4B5563",
            command=self.stop,
            state="disabled",
        )
        self.stop_button.grid(row=0, column=1, padx=(6, 0), sticky="ew")

        ctk.CTkLabel(
            self,
            text="Moves within a small radius. Pauses briefly after real mouse or keyboard input.",
            text_color="gray",
            wraplength=400,
            justify="center",
            font=ctk.CTkFont(size=11),
        ).grid(row=4, column=0, padx=24, pady=(12, 4))
        ctk.CTkLabel(
            self,
            text="CursorMover • Runs locally on this PC",
            text_color="#6B7280",
            font=ctk.CTkFont(size=10),
        ).grid(row=5, column=0, padx=20, pady=(2, 14))

    def _update_interval_label(self, value: float) -> None:
        self.interval_value.configure(text=f"{int(round(value))} seconds")

    def _update_radius_label(self, value: float) -> None:
        self.radius_value.configure(text=f"{int(round(value))} pixels")

    def _start_input_listeners(self) -> None:
        def note_input(*_args: object) -> None:
            # Ignore events occurring immediately after our own pointer move.
            if time.monotonic() - self.last_programmatic_move > 0.12:
                self.last_user_input = time.monotonic()

        self.mouse_listener = mouse.Listener(
            on_move=note_input,
            on_click=note_input,
            on_scroll=note_input,
        )
        self.keyboard_listener = keyboard.Listener(on_press=note_input)
        self.mouse_listener.daemon = True
        self.keyboard_listener.daemon = True
        self.mouse_listener.start()
        self.keyboard_listener.start()

    def start(self) -> None:
        if self.running.is_set():
            return
        self.settings.interval = float(self.interval_var.get())
        self.settings.radius = int(self.radius_var.get())
        self.settings.smooth = bool(self.smooth_var.get())
        self.running.set()
        self.status_label.configure(text="Running")
        self.status_dot.configure(text_color="#22C55E")
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.worker = threading.Thread(target=self._movement_loop, daemon=True)
        self.worker.start()

    def stop(self) -> None:
        self.running.clear()
        self.status_label.configure(text="Stopped")
        self.status_dot.configure(text_color="#9CA3AF")
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")

    def _movement_loop(self) -> None:
        while self.running.is_set() and not self.shutdown.is_set():
            deadline = time.monotonic() + self.settings.interval
            while self.running.is_set() and time.monotonic() < deadline:
                time.sleep(0.05)
            if not self.running.is_set():
                break

            # Do not compete with genuine user interaction.
            if time.monotonic() - self.last_user_input < USER_INPUT_PAUSE_SECONDS:
                continue

            try:
                x, y = pyautogui.position()
                screen_w, screen_h = pyautogui.size()
                radius = self.settings.radius
                target_x = max(2, min(screen_w - 3, x + random.randint(-radius, radius)))
                target_y = max(2, min(screen_h - 3, y + random.randint(-radius, radius)))
                self.last_programmatic_move = time.monotonic()

                if self.settings.smooth:
                    self._move_curved(x, y, target_x, target_y)
                else:
                    pyautogui.moveTo(target_x, target_y, duration=0.12)

                self.movement_count += 1
                self.after(0, self._update_count)
            except Exception as exc:
                self.after(0, lambda error=str(exc): self._movement_error(error))
                break

        self.after(0, self._sync_stopped_state)

    def _move_curved(self, x1: int, y1: int, x2: int, y2: int) -> None:
        dx, dy = x2 - x1, y2 - y1
        distance = math.hypot(dx, dy)
        if distance < 1:
            return
        # A perpendicular control point gives the path a gentle, non-linear arc.
        bend = random.uniform(-0.25, 0.25) * distance
        perp_x, perp_y = -dy / distance, dx / distance
        cx = (x1 + x2) / 2 + perp_x * bend
        cy = (y1 + y2) / 2 + perp_y * bend
        steps = max(8, min(24, int(distance / 5)))
        for i in range(1, steps + 1):
            if not self.running.is_set():
                return
            t = i / steps
            inv = 1 - t
            px = inv * inv * x1 + 2 * inv * t * cx + t * t * x2
            py = inv * inv * y1 + 2 * inv * t * cy + t * t * y2
            pyautogui.moveTo(round(px), round(py), duration=0)
            time.sleep(0.008)

    def _update_count(self) -> None:
        self.count_label.configure(text=f"{self.movement_count} movements")

    def _movement_error(self, error: str) -> None:
        self.stop()
        messagebox.showerror("CursorMover error", error)

    def _sync_stopped_state(self) -> None:
        if not self.running.is_set():
            self.status_label.configure(text="Stopped")
            self.status_dot.configure(text_color="#9CA3AF")
            self.start_button.configure(state="normal")
            self.stop_button.configure(state="disabled")

    def _on_close(self) -> None:
        self.shutdown.set()
        self.running.clear()
        for listener in (self.mouse_listener, self.keyboard_listener):
            if listener is not None:
                try:
                    listener.stop()
                except Exception:
                    pass
        self.destroy()


if __name__ == "__main__":
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0
    app = CursorMoverApp()
    app.mainloop()
