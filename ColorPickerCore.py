# -*- coding: utf-8 -*-
from __future__ import annotations
import ctypes
from ctypes import wintypes
import colorsys
import json
import os
from typing import List, Tuple, Dict, Any

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

def get_window_rect_native(hwnd: int) -> RECT:
    rc = RECT()
    user32.GetWindowRect(wintypes.HWND(hwnd), ctypes.byref(rc))
    return rc

# ---- Keyboard State Helpers (Windows) ----
VK_CONTROL = 0x11
VK_LCONTROL = 0xA2
VK_RCONTROL = 0xA3
VK_SHIFT   = 0x10
VK_MENU    = 0x12  # Alt key

def is_ctrl_pressed() -> bool:
    try:
        return bool(user32.GetAsyncKeyState(VK_CONTROL) & 0x8000) or \
               bool(user32.GetAsyncKeyState(VK_LCONTROL) & 0x8000) or \
               bool(user32.GetAsyncKeyState(VK_RCONTROL) & 0x8000)
    except Exception:
        return False

def is_shift_pressed() -> bool:
    try:
        return bool(user32.GetAsyncKeyState(VK_SHIFT) & 0x8000)
    except Exception:
        return False

def is_alt_pressed() -> bool:
    try:
        return bool(user32.GetAsyncKeyState(VK_MENU) & 0x8000)
    except Exception:
        return False

# ---- Color Conversion Functions ----
def rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{r:02X}{g:02X}{b:02X}"

def rgb_to_hsl(r: int, g: int, b: int) -> Tuple[int, int, int]:
    r_n, g_n, b_n = r / 255.0, g / 255.0, b / 255.0
    h, l, s = colorsys.rgb_to_hls(r_n, g_n, b_n)
    return round(h * 360), round(s * 100), round(l * 100)

def rgb_to_hsv(r: int, g: int, b: int) -> Tuple[int, int, int]:
    r_n, g_n, b_n = r / 255.0, g / 255.0, b / 255.0
    h, s, v = colorsys.rgb_to_hsv(r_n, g_n, b_n)
    return round(h * 360), round(s * 100), round(v * 100)

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

def get_triadic_colors(r: int, g: int, b: int) -> List[Tuple[int, int, int]]:
    h, s, l = rgb_to_hsl(r, g, b)
    c1 = hsl_to_rgb(h + 120, s, l)
    c2 = hsl_to_rgb(h + 240, s, l)
    return [c1, c2]

# ---- Approximate Color Naming ----
COLOR_NAMES = {
    "#000000": "Black", "#FFFFFF": "White", "#FF0000": "Red", "#00FF00": "Lime",
    "#0000FF": "Blue", "#FFFF00": "Yellow", "#00FFFF": "Cyan", "#FF00FF": "Magenta",
    "#C0C0C0": "Silver", "#808080": "Gray", "#800000": "Maroon", "#808000": "Olive",
    "#008000": "Green", "#800080": "Purple", "#008080": "Teal", "#000080": "Navy",
    "#FF7F50": "Coral", "#FF4500": "OrangeRed", "#FF8C00": "DarkOrange", "#FFD700": "Gold",
    "#4B0082": "Indigo", "#EE82EE": "Violet", "#F0E68C": "Khaki", "#E6E6FA": "Lavender",
    "#1E2129": "Dark Charcoal", "#2A2E39": "Dark Slate"
}

def get_closest_color_name(r: int, g: int, b: int) -> str:
    min_dist = float("inf")
    closest_name = "Custom Color"
    for hex_code, name in COLOR_NAMES.items():
        cr = int(hex_code[1:3], 16)
        cg = int(hex_code[3:5], 16)
        cb = int(hex_code[5:7], 16)
        dist = (r - cr) ** 2 + (g - cg) ** 2 + (b - cb) ** 2
        if dist < min_dist:
            min_dist = dist
            closest_name = name
    return closest_name

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