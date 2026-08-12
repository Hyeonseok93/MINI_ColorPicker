# -*- coding: utf-8 -*-
from __future__ import annotations
import sys
import signal
import os
from PySide6 import QtCore, QtWidgets, QtGui
from pynput import mouse, keyboard

from ColorPickerUi import MainWindow
import ColorPickerCore as Core

# ---- PyInstaller Boot Splash ----
_boot_splash = None
try:
    import pyi_splash
    _boot_splash = pyi_splash
except Exception:
    _boot_splash = None

def resource_path(rel: str) -> str:
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)

class App(QtWidgets.QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        self.setQuitOnLastWindowClosed(False)

        # ---- Load App Icon ----
        icon_path = None
        for p in ("assets/app.ico", "asset/app.ico"):
            cp = resource_path(p)
            if os.path.exists(cp):
                icon_path = cp
                break
        
        self.icon = QtGui.QIcon(icon_path) if icon_path else QtGui.QIcon()
        if icon_path:
            self.setWindowIcon(self.icon)

        # ---- Font Database Loading (Pretendard) ----
        for font_name in ("Pretendard-Medium.ttf", "Pretendard-Bold.ttf"):
            font_path = resource_path(os.path.join("assets", "fonts", font_name))
            if os.path.exists(font_path):
                QtGui.QFontDatabase.addApplicationFont(font_path)

        app_font = QtGui.QFont("Pretendard", 10)
        app_font.setStyleHint(QtGui.QFont.SansSerif)
        self.setFont(app_font)

        # ---- Instantiate Main Window ----
        self.win = MainWindow()
        self.win.closeEvent = self.on_win_close
        if icon_path:
            self.win.setWindowIcon(self.icon)
        self.win.show()
        self.win.apply_pin_state(True)
        self.processEvents()


        # ---- Close Boot Splash ----
        if _boot_splash is not None:
            QtCore.QTimer.singleShot(100, lambda: _boot_splash.close())

        # ---- System Tray Icon Setup ----
        self._setup_system_tray()

        # ---- Mouse & Keyboard Listener (pynput) ----
        self.mouse_listener = mouse.Listener(on_click=self.on_global_click)
        self.mouse_listener.start()

        self.key_listener = keyboard.Listener(on_press=self.on_global_key_press)
        self.key_listener.start()

        signal.signal(signal.SIGINT, lambda *_: QtCore.QTimer.singleShot(0, self.quit))

    def _setup_system_tray(self):
        if not QtWidgets.QSystemTrayIcon.isSystemTrayAvailable():
            return

        self.tray = QtWidgets.QSystemTrayIcon(self.icon, self)
        self.tray.setToolTip("Color Picker (Ctrl+클릭으로 캡쳐)")

        tray_menu = QtWidgets.QMenu()
        open_action = tray_menu.addAction("📂 Color Picker 열기")
        open_action.triggered.connect(self._show_main_window)

        copy_last_action = tray_menu.addAction("📋 최근 색상 복사")
        copy_last_action.triggered.connect(self._copy_latest_color)

        tray_menu.addSeparator()
        quit_action = tray_menu.addAction("❌ 종료")
        quit_action.triggered.connect(self.quit)

        self.tray.setContextMenu(tray_menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()
        self.win.tray_icon = self.tray


    def _on_tray_activated(self, reason: QtWidgets.QSystemTrayIcon.ActivationReason):
        if reason in (QtWidgets.QSystemTrayIcon.Trigger, QtWidgets.QSystemTrayIcon.DoubleClick):
            self._show_main_window()

    def _show_main_window(self):
        self.win.showNormal()
        self.win.activateWindow()
        self.win.raise_()

    def _copy_latest_color(self):
        if hasattr(self.win, "captured_hex") and self.win.captured_hex:
            QtWidgets.QApplication.clipboard().setText(self.win.captured_hex)
            self.win.show_toast(f"최근 색상 복사: {self.win.captured_hex}")

    def capture_current_position(self):
        x, y = Core.get_cursor_pos_native()
        r, g, b = Core.get_pixel_color_at(x, y)
        hexstr = Core.rgb_to_hex(r, g, b)
        QtCore.QMetaObject.invokeMethod(
            self.win, "emit_color", QtCore.Qt.QueuedConnection,
            QtCore.Q_ARG(int, r), QtCore.Q_ARG(int, g), QtCore.Q_ARG(int, b), QtCore.Q_ARG(str, hexstr)
        )
        self.win.show_toast(f"캡쳐 완료: {hexstr}")

    def on_global_key_press(self, key):
        # Global Hotkey (Ctrl + C captures current cursor pixel)
        try:
            vk = getattr(key, 'vk', None)
            char = getattr(key, 'char', None)

            is_c_key = (vk == 67) or (char and char.lower() in ('c', '\x03'))

            if is_c_key and Core.is_ctrl_pressed():
                # Avoid triggering when cursor is focused on an input text field inside window
                self.capture_current_position()
        except Exception:
            pass

    def on_global_click(self, x: int, y: int, button, pressed: bool):
        if not pressed or button != mouse.Button.left:
            return
        if not Core.is_ctrl_pressed():
            return
        if self.win.contains_native_point(x, y):
            return

        r, g, b = Core.get_pixel_color_at(x, y)
        hexstr = Core.rgb_to_hex(r, g, b)
        QtCore.QMetaObject.invokeMethod(
            self.win, "emit_color", QtCore.Qt.QueuedConnection,
            QtCore.Q_ARG(int, r), QtCore.Q_ARG(int, g), QtCore.Q_ARG(int, b), QtCore.Q_ARG(str, hexstr)
        )

    def on_win_close(self, event):
        event.accept()
        self.quit()

    def quit(self):

        try:
            if hasattr(self, "mouse_listener") and self.mouse_listener:
                self.mouse_listener.stop()
            if hasattr(self, "key_listener") and self.key_listener:
                self.key_listener.stop()
        except Exception:
            pass
        self.win.save_session_history()
        super().quit()

if __name__ == "__main__":
    if not Core.check_single_instance():
        # Close PyInstaller boot splash immediately if open
        try:
            import pyi_splash
            pyi_splash.close()
        except Exception:
            pass

        dummy_app = QtWidgets.QApplication(sys.argv)
        msg_box = QtWidgets.QMessageBox()
        msg_box.setIcon(QtWidgets.QMessageBox.Warning)
        msg_box.setWindowTitle("알림")
        msg_box.setText("Color Picker가 이미 실행 중입니다.\n작업 표시줄 트레이 영역을 확인해 주세요.")
        msg_box.setWindowFlags(msg_box.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
        msg_box.exec()
        sys.exit(0)

    app = App(sys.argv)
    sys.exit(app.exec())


