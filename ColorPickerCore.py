# -*- coding: utf-8 -*-
from __future__ import annotations
import ctypes
from ctypes import wintypes
import colorsys
import json
import os
from typing import List, Tuple, Dict, Any, Optional

_single_instance_mutex = None

def check_single_instance(mutex_name: str = "Global\\MINI_ColorPicker_SingleInstance_Mutex") -> bool:
    """Check if another instance is already running using Win32 Named Mutex."""
    global _single_instance_mutex
    try:
        ERROR_ALREADY_EXISTS = 183
        kernel32 = ctypes.windll.kernel32
        mutex = kernel32.CreateMutexW(None, False, mutex_name)
        if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
            return False
        _single_instance_mutex = mutex
        return True
    except Exception:
        return True

# ---- Win32 API Definitions ----

user32 = ctypes.windll.user32
gdi32  = ctypes.windll.gdi32

class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]

SRCCOPY = 0x00CC0020
BI_RGB = 0
DIB_RGB_COLORS = 0

def get_cursor_pos_native() -> Tuple[int, int]:
    """Get global cursor position (X, Y)."""
    pt = POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y

def get_pixel_color_at(x: int, y: int) -> Tuple[int, int, int]:
    """Get RGB pixel color at screen coordinate (x, y)."""
    hdc = user32.GetDC(0)
    pixel = gdi32.GetPixel(hdc, x, y)  # COLORREF: 0x00BBGGRR
    user32.ReleaseDC(0, hdc)
    if pixel == -1 or pixel == 0xFFFFFFFF:
        return 0, 0, 0
    r = pixel & 0xFF
    g = (pixel >> 8) & 0xFF
    b = (pixel >> 16) & 0xFF
    return r, g, b

def capture_screen_region(x: int, y: int, width: int, height: int) -> Optional[bytes]:
    """Capture a w×h region from the virtual desktop (same coords as GetCursorPos/GetPixel).

    Returns top-down BGRA bytes (width * height * 4), or None on failure.
    Works across any multi-monitor layout.
    """
    if width <= 0 or height <= 0:
        return None

    hdc = user32.GetDC(0)
    if not hdc:
        return None

    memdc = gdi32.CreateCompatibleDC(hdc)
    hbmp = gdi32.CreateCompatibleBitmap(hdc, width, height) if memdc else None
    if not memdc or not hbmp:
        if hbmp:
            gdi32.DeleteObject(hbmp)
        if memdc:
            gdi32.DeleteDC(memdc)
        user32.ReleaseDC(0, hdc)
        return None

    old = gdi32.SelectObject(memdc, hbmp)
    ok = gdi32.BitBlt(memdc, 0, 0, width, height, hdc, x, y, SRCCOPY)

    buf: Optional[bytes] = None
    if ok:
        bmi = BITMAPINFOHEADER()
        bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.biWidth = width
        bmi.biHeight = -height  # top-down
        bmi.biPlanes = 1
        bmi.biBitCount = 32
        bmi.biCompression = BI_RGB

        buf_size = width * height * 4
        raw = (ctypes.c_char * buf_size)()
        got = gdi32.GetDIBits(memdc, hbmp, 0, height, raw, ctypes.byref(bmi), DIB_RGB_COLORS)
        if got:
            buf = bytes(raw)

    gdi32.SelectObject(memdc, old)
    gdi32.DeleteObject(hbmp)
    gdi32.DeleteDC(memdc)
    user32.ReleaseDC(0, hdc)
    return buf

def get_window_rect_native(hwnd: int) -> RECT:
    rc = RECT()
    user32.GetWindowRect(wintypes.HWND(hwnd), ctypes.byref(rc))
    return rc

# ---- Keyboard State Helpers (Windows) ----
VK_CONTROL = 0x11
VK_LCONTROL = 0xA2
VK_RCONTROL = 0xA3

def is_ctrl_pressed() -> bool:
    try:
        return bool(user32.GetAsyncKeyState(VK_CONTROL) & 0x8000) or \
               bool(user32.GetAsyncKeyState(VK_LCONTROL) & 0x8000) or \
               bool(user32.GetAsyncKeyState(VK_RCONTROL) & 0x8000)
    except Exception:
        return False

# ---- Color Conversion Functions ----
def rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{r:02X}{g:02X}{b:02X}"

def rgb_to_hsl(r: int, g: int, b: int) -> Tuple[int, int, int]:
    r_n, g_n, b_n = r / 255.0, g / 255.0, b / 255.0
    h, l, s = colorsys.rgb_to_hls(r_n, g_n, b_n)
    return round(h * 360), round(s * 100), round(l * 100)

def rgb_to_cmyk(r: int, g: int, b: int) -> Tuple[int, int, int, int]:
    if (r, g, b) == (0, 0, 0):
        return 0, 0, 0, 100
    c = 1 - (r / 255.0)
    m = 1 - (g / 255.0)
    y = 1 - (b / 255.0)
    k = min(c, m, y)
    c = (c - k) / (1 - k) if (1 - k) > 0 else 0
    m = (m - k) / (1 - k) if (1 - k) > 0 else 0
    y = (y - k) / (1 - k) if (1 - k) > 0 else 0
    return round(c * 100), round(m * 100), round(y * 100), round(k * 100)

def hsl_to_rgb(h: float, s: float, l: float) -> Tuple[int, int, int]:
    h_n, s_n, l_n = (h % 360) / 360.0, s / 100.0, l / 100.0
    r, g, b = colorsys.hls_to_rgb(h_n, l_n, s_n)
    return round(r * 255), round(g * 255), round(b * 255)

# ---- Color Harmony Helpers ----
def get_complementary_color(r: int, g: int, b: int) -> Tuple[int, int, int]:
    h, s, l = rgb_to_hsl(r, g, b)
    return hsl_to_rgb(h + 180, s, l)

def get_analogous_colors(r: int, g: int, b: int) -> List[Tuple[int, int, int]]:
    h, s, l = rgb_to_hsl(r, g, b)
    c1 = hsl_to_rgb(h - 30, s, l)
    c2 = hsl_to_rgb(h + 30, s, l)
    return [c1, c2]

# ---- Session Persistence Helpers ----
SESSION_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "session_history.json")

def load_session_history() -> List[Dict[str, Any]]:
    if not os.path.exists(SESSION_FILE_PATH):
        return []
    try:
        with open(SESSION_FILE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
    except Exception as e:
        print(f"[Core Warning] Failed to load session history: {e}")
    return []

def save_session_history(items: List[Dict[str, Any]]) -> bool:
    try:
        os.makedirs(os.path.dirname(SESSION_FILE_PATH), exist_ok=True)
        with open(SESSION_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[Core Error] Failed to save session history: {e}")
        return False