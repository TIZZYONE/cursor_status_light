#!/usr/bin/env python3
"""Cursor 红绿灯：读状态、窗口、托盘。视觉见 cursor_light_ui.py。"""

from __future__ import annotations

import json
import os
import re
import sys
import threading
import time
import tkinter as tk
from pathlib import Path

# 保证同目录可 import ui（仓库或 %USERPROFILE%\.cursor）
_APP_DIR = Path(__file__).resolve().parent
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

import cursor_light_ui as ui
from PIL import Image, ImageTk

if sys.platform == "win32":
    import ctypes

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass
    user32 = ctypes.windll.user32
    HWND_TOPMOST, HWND_NOTOPMOST = -1, -2
    SWP_NOMOVE, SWP_NOSIZE, SWP_NOACTIVATE, SWP_SHOWWINDOW = 0x0002, 0x0001, 0x0010, 0x0040
else:
    user32 = None

STATUS_DIR = Path.home() / ".cursor" / "status"
PID_FILE = Path.home() / ".cursor" / "cursor_light.pid"
CONFIG_FILE = Path.home() / ".cursor" / "cursor_light_config.json"

POLL_MS = 300
STALE_SECONDS = 600
SESSION_EXPIRE_SEC = 900
# 最近一次 busy/thinking 后保持黄灯的秒数（避免工具间隔间隙误变绿）
HEARTBEAT_HOLD_SEC = 30

BUSY_MODES = frozenset({"busy", "working", "thinking", "ai", "demo"})
SUCCESS_MODES = frozenset({"success", "done", "idle", "off", "traffic"})
ERROR_MODES = frozenset({"error", "alarm"})
SKIP_STATUS_FILES = frozenset({"hook.log", "_heartbeat.json"})
HEARTBEAT_FILE = STATUS_DIR / "_heartbeat.json"

OPACITY_PRESETS = (1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3)


def display_scale() -> int:
    if sys.platform != "win32" or user32 is None:
        return ui.RENDER_SCALE
    try:
        hdc = user32.GetDC(0)
        dpi = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)
        user32.ReleaseDC(0, hdc)
        return max(ui.RENDER_SCALE, round(dpi / 96) + 1)
    except Exception:
        return ui.RENDER_SCALE


def win_hwnd(root: tk.Tk) -> int:
    root.update_idletasks()
    return root.winfo_id()


def set_win_topmost(root: tk.Tk, on: bool) -> None:
    if user32 is None:
        return
    user32.SetWindowPos(
        win_hwnd(root),
        HWND_TOPMOST if on else HWND_NOTOPMOST,
        0, 0, 0, 0,
        SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW,
    )


def load_config() -> dict:
    default = {"always_on_top": True, "opacity": 1.0}
    if not CONFIG_FILE.exists():
        return default
    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8-sig"))
        if "opacity" in data:
            data["opacity"] = max(0.2, min(1.0, float(data["opacity"])))
        return {**default, **data}
    except Exception:
        return default


def save_config(always_on_top: bool, opacity: float) -> None:
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(
        json.dumps({"always_on_top": always_on_top, "opacity": round(opacity, 2)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def parse_timestamp(ts_str: str):
    from datetime import datetime

    s = str(ts_str).strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return datetime.fromisoformat(re.sub(r"(\.\d{6})\d+", r"\1", s))


def normalize_mode(raw: str) -> str:
    s = (raw or "").lower().strip()
    if s in ERROR_MODES:
        return "error"
    if s in BUSY_MODES:
        return "busy"
    if s in SUCCESS_MODES:
        return "success"
    return "success"


def _session_file_age(path: Path, now: float) -> float | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        ts = data.get("ts")
        if not ts:
            return None
        return now - parse_timestamp(ts).timestamp()
    except Exception:
        return None


def _cleanup_stale_sessions(now: float) -> None:
    if not STATUS_DIR.is_dir():
        return
    for path in STATUS_DIR.glob("*.json"):
        if path.name in SKIP_STATUS_FILES:
            continue
        age = _session_file_age(path, now)
        if age is not None and age > SESSION_EXPIRE_SEC:
            try:
                path.unlink(missing_ok=True)
            except Exception:
                pass


def _heartbeat_active(now: float) -> bool:
    """最近一次 busy/thinking 类事件是否在保持期内。"""
    if not HEARTBEAT_FILE.exists():
        return False
    try:
        data = json.loads(HEARTBEAT_FILE.read_text(encoding="utf-8-sig"))
        ts = data.get("ts")
        if not ts:
            return False
        return (now - parse_timestamp(ts).timestamp()) < HEARTBEAT_HOLD_SEC
    except Exception:
        return False


def read_aggregate() -> tuple[str, int]:
    """
    多 Cursor 窗口 / 多会话聚合：
    - 每个会话独立 json
    - 优先级：error > busy > success
    - 有心跳（30s 内有过 busy/thinking）则强制黄灯，避免工具间隙闪绿
    """
    if not STATUS_DIR.is_dir():
        return "success", 0

    now = time.time()
    _cleanup_stale_sessions(now)

    modes: list[str] = []
    active = 0

    for path in sorted(STATUS_DIR.glob("*.json")):
        if path.name in SKIP_STATUS_FILES:
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
            status = str(data.get("status", "")).lower()
            if not status:
                continue

            age = _session_file_age(path, now)
            if age is None:
                continue
            if age > STALE_SECONDS:
                continue

            mode = normalize_mode(status)
            active += 1
            modes.append(mode)
        except Exception:
            continue

    if not modes:
        agg = "success"
    elif "error" in modes:
        agg = "error"
    elif "busy" in modes:
        agg = "busy"
    else:
        agg = "success"

    if agg != "error" and _heartbeat_active(now):
        agg = "busy"

    return agg, active


def kill_previous_instance() -> None:
    if not PID_FILE.exists():
        return
    try:
        old = int(PID_FILE.read_text(encoding="utf-8").strip())
        if old != os.getpid():
            os.kill(old, 9)
    except Exception:
        pass
    try:
        PID_FILE.unlink(missing_ok=True)
    except Exception:
        pass


class TrafficLightApp:
    def __init__(self) -> None:
        kill_previous_instance()
        PID_FILE.write_text(str(os.getpid()), encoding="utf-8")

        cfg = load_config()
        self.scale = display_scale()
        self.always_on_top = bool(cfg.get("always_on_top", True))
        self.opacity = float(cfg.get("opacity", 1.0))
        self._drag_x = self._drag_y = 0
        self._photo: ImageTk.PhotoImage | None = None
        self._last_key = ""
        self._tray_icon = None
        chroma_hex = "#%02x%02x%02x" % ui.CHROMA
        self.root = tk.Tk()
        self.root.title("Cursor Status Light")
        self.root.overrideredirect(True)
        self.root.configure(bg=chroma_hex)
        self.root.wm_attributes("-transparentcolor", chroma_hex)
        self.root.resizable(False, False)

        sw = self.root.winfo_screenwidth()
        self.root.geometry(f"{ui.BASE_W}x{ui.BASE_H}+{sw - ui.BASE_W - 28}+20")

        self.canvas = tk.Label(self.root, bd=0, highlightthickness=0, bg=chroma_hex)
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self._drag_start)
        self.canvas.bind("<B1-Motion>", self._drag_motion)
        self.root.bind("<Escape>", lambda _e: self.quit())

        self.apply_topmost(self.always_on_top)
        self.apply_opacity(self.opacity)
        self._start_tray()
        self.poll_status()
        self.root.protocol("WM_DELETE_WINDOW", self.quit)

    def _persist(self) -> None:
        save_config(self.always_on_top, self.opacity)

    def apply_opacity(self, value: float) -> None:
        self.opacity = max(0.2, min(1.0, value))
        try:
            self.root.attributes("-alpha", self.opacity)
        except tk.TclError:
            pass
        self._persist()

    def apply_topmost(self, on: bool) -> None:
        self.always_on_top = on
        self.root.wm_attributes("-topmost", on)
        set_win_topmost(self.root, on)
        self._persist()

    def toggle_topmost(self) -> None:
        self.apply_topmost(not self.always_on_top)
        self._rebuild_tray_menu()

    def _set_image(self, agg: str) -> None:
        if agg == self._last_key and self._photo is not None:
            return
        self._last_key = agg

        raw = ui.render_traffic_light(agg, self.scale)
        display = raw.resize((ui.BASE_W, ui.BASE_H), Image.Resampling.LANCZOS)
        self._photo = ImageTk.PhotoImage(display)
        self.canvas.configure(image=self._photo)

    def _drag_start(self, event) -> None:
        self._drag_x = event.x_root - self.root.winfo_x()
        self._drag_y = event.y_root - self.root.winfo_y()

    def _drag_motion(self, event) -> None:
        self.root.geometry(f"+{event.x_root - self._drag_x}+{event.y_root - self._drag_y}")

    def poll_status(self) -> None:
        agg, active = read_aggregate()
        self._set_image(agg)
        if self._tray_icon is not None:
            tip = {"error": "失败", "busy": "执行中", "success": "完成"}.get(agg, agg)
            self._tray_icon.icon = ui.make_tray_icon_image(agg)
            self._tray_icon.title = f"Cursor 红绿灯 — {tip}（{active} 个会话）"
        self.root.after(POLL_MS, self.poll_status)

    def _build_tray_menu(self):
        import pystray

        def on_toggle(_i, _it):
            self.root.after(0, self.toggle_topmost)

        def on_exit(_i, _it):
            self.root.after(0, self.quit)

        def make_opacity_item(alpha: float):
            def handler(_i, _it):
                self.root.after(0, lambda: (self.apply_opacity(alpha), self._rebuild_tray_menu()))

            return pystray.MenuItem(
                f"{int(alpha * 100)}%",
                handler,
                checked=lambda item, a=alpha: abs(self.opacity - a) < 0.01,
            )

        return pystray.Menu(
            pystray.MenuItem("切换置顶", on_toggle, checked=lambda _: self.always_on_top),
            pystray.MenuItem("窗口透明度", pystray.Menu(*[make_opacity_item(a) for a in OPACITY_PRESETS])),
            pystray.MenuItem("退出", on_exit),
        )

    def _rebuild_tray_menu(self) -> None:
        if self._tray_icon:
            try:
                self._tray_icon.menu = self._build_tray_menu()
            except Exception:
                pass

    def _start_tray(self) -> None:
        try:
            import pystray
        except ImportError:
            return
        self._tray_icon = pystray.Icon(
            "cursor_status_light",
            ui.make_tray_icon_image(),
            "Cursor 红绿灯",
            self._build_tray_menu(),
        )
        threading.Thread(target=self._tray_icon.run, daemon=True).start()

    def quit(self) -> None:
        if self._tray_icon:
            try:
                self._tray_icon.stop()
            except Exception:
                pass
        try:
            PID_FILE.unlink(missing_ok=True)
        except Exception:
            pass
        self.root.destroy()
        sys.exit(0)

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    TrafficLightApp().run()
