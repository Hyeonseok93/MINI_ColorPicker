# -*- coding: utf-8 -*-
from __future__ import annotations
from datetime import datetime
from typing import Tuple, Optional, List

from PySide6 import QtCore, QtGui, QtWidgets

import ColorPickerCore as Core

# ---- Toast Notification Widget ----
class ToastNotification(QtWidgets.QFrame):
    """Floating Glassmorphism Toast Notification Alert."""
    def __init__(self, message: str, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self.setWindowFlags(QtCore.Qt.SubWindow | QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_ShowWithoutActivating)

        self.setStyleSheet("""
            QFrame#ToastFrame {
                background-color: rgba(24, 26, 32, 235);
                border: 1px solid rgba(88, 208, 130, 0.5);
                border-radius: 12px;
            }
            QLabel {
                color: #EDEFF5;
                font-size: 13px;
                font-weight: 600;
                border: none;
                background: transparent;
            }
        """)
        self.setObjectName("ToastFrame")

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 18, 10)
        layout.setSpacing(10)

        icon_lbl = QtWidgets.QLabel("📋")
        icon_lbl.setStyleSheet("font-size: 16px; border:none; background:transparent;")

        msg_lbl = QtWidgets.QLabel(message)
        msg_lbl.setStyleSheet("border:none; background:transparent;")

        layout.addWidget(icon_lbl)
        layout.addWidget(msg_lbl)

        self.opacity_effect = QtWidgets.QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)

        self.anim = QtCore.QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim.setDuration(200)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)

    def show_toast(self, parent_widget: QtWidgets.QWidget, duration_ms: int = 2000):
        self.adjustSize()
        if parent_widget:
            p_rect = parent_widget.geometry()
            x = p_rect.x() + (p_rect.width() - self.width()) // 2
            y = p_rect.y() + p_rect.height() - self.height() - 28
            self.move(x, y)
        self.show()
        self.anim.start()
        QtCore.QTimer.singleShot(duration_ms, self._fade_out)

    def _fade_out(self):
        self.anim_out = QtCore.QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim_out.setDuration(250)
        self.anim_out.setStartValue(1.0)
        self.anim_out.setEndValue(0.0)
        self.anim_out.finished.connect(self.close)
        self.anim_out.start()


# ---- Square Pixel Magnifier Widget (Fixed 8x Zoom) ----
class PixelMagnifier(QtWidgets.QFrame):
    """Square 200x200 Pixel Magnifier Canvas with Fixed 8x Zoom."""

    def __init__(self, side_size: int = 200, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self.setFixedSize(side_size, side_size)
        self.setObjectName("MagnifierFrame")
        self.setStyleSheet("""
            QFrame#MagnifierFrame {
                background: #14161B;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 12px;
            }
        """)

        self.grid_size = 21
        self.show_grid = True

        self.crop_image: Optional[QtGui.QImage] = None

    def update_magnifier(self, center_x: int, center_y: int):
        # Use Win32 virtual-desktop capture (same coords as GetPixel) so any
        # monitor layout works. Qt grabWindow expects screen-local coords and
        # goes black on non-primary displays.
        half = self.grid_size // 2
        w = h = self.grid_size
        raw = Core.capture_screen_region(center_x - half, center_y - half, w, h)
        if not raw:
            self.crop_image = None
            self.update()
            return

        img = QtGui.QImage(raw, w, h, w * 4, QtGui.QImage.Format.Format_RGB32)
        self.crop_image = img.copy()  # detach from temporary buffer
        self.update()

    def paintEvent(self, event: QtGui.QPaintEvent):
        super().paintEvent(event)
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing, False)

        w, h = self.width(), self.height()

        if self.crop_image and not self.crop_image.isNull():
            cell_w = w / self.grid_size
            cell_h = h / self.grid_size

            for gy in range(self.grid_size):
                for gx in range(self.grid_size):
                    col = QtGui.QColor(self.crop_image.pixel(gx, gy)) if (gx < self.crop_image.width() and gy < self.crop_image.height()) else QtGui.QColor(0,0,0)
                    rect = QtCore.QRectF(gx * cell_w, gy * cell_h, cell_w, cell_h)
                    painter.fillRect(rect, col)

                    if self.show_grid:
                        painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 25), 1))
                        painter.drawRect(rect)

            center_idx = self.grid_size // 2
            center_rect = QtCore.QRectF(center_idx * cell_w, center_idx * cell_h, cell_w, cell_h)
            
            painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 240), 2))
            painter.drawRect(center_rect)
            painter.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0, 200), 1))
            painter.drawRect(center_rect.adjusted(1, 1, -1, -1))

            painter.setPen(QtGui.QPen(QtGui.QColor(88, 208, 130, 180), 1, QtCore.Qt.DashLine))
            painter.drawLine(QtCore.QPointF(w / 2, 0), QtCore.QPointF(w / 2, h))
            painter.drawLine(QtCore.QPointF(0, h / 2), QtCore.QPointF(w, h / 2))

        # Fixed Badge Text
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        badge_rect = QtCore.QRectF(8, 8, 52, 22)
        painter.setBrush(QtGui.QColor(0, 0, 0, 180))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRoundedRect(badge_rect, 5, 5)

        painter.setPen(QtGui.QColor("#58D082"))
        font = painter.font()
        font.setPointSize(9)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(badge_rect, QtCore.Qt.AlignCenter, "🔍 8x")
        painter.end()


# ---- Color Harmony Widget ----
class ColorHarmonyWidget(QtWidgets.QFrame):
    """Displays Complementary and Analogous color palette chips."""
    color_clicked = QtCore.Signal(str)

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self.setObjectName("HarmonyFrame")
        self.setStyleSheet("""
            QFrame#HarmonyFrame {
                background: #23262F;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
            }
            QLabel {
                border: none;
                background: transparent;
            }
        """)
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(6)

        title = QtWidgets.QLabel("🎨 선택 색상 조화 팔레트 (클릭 시 복사)")
        title.setStyleSheet("color:#A8ACB4; font-size:11px; font-weight:700; border:none;")
        lay.addWidget(title)

        self.chips_layout = QtWidgets.QHBoxLayout()
        self.chips_layout.setSpacing(8)
        lay.addLayout(self.chips_layout)

        self.chips: List[QtWidgets.QPushButton] = []
        for _ in range(4):
            btn = QtWidgets.QPushButton()
            btn.setFixedHeight(30)
            btn.setCursor(QtCore.Qt.PointingHandCursor)
            btn.clicked.connect(lambda _, b=btn: self.on_chip_clicked(b))
            self.chips_layout.addWidget(btn, 1)
            self.chips.append(btn)

    def update_harmony(self, r: int, g: int, b: int):
        comp = Core.get_complementary_color(r, g, b)
        ana = Core.get_analogous_colors(r, g, b)

        colors = [(r, g, b), comp, ana[0], ana[1]]
        labels = ["Main", "Comp", "Ana-1", "Ana-2"]

        for btn, (cr, cg, cb), label in zip(self.chips, colors, labels):
            hexstr = Core.rgb_to_hex(cr, cg, cb)
            btn.setText(f"{label}\n{hexstr}")
            luma = 0.299 * cr + 0.587 * cg + 0.114 * cb
            text_col = "#000000" if luma > 160 else "#FFFFFF"
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {hexstr};
                    color: {text_col};
                    border: 1px solid rgba(255,255,255,0.2);
                    border-radius: 6px;
                    font-weight: 700;
                    font-size: 10px;
                }}
                QPushButton:hover {{
                    border: 2px solid #58D082;
                }}
            """)
            btn.setProperty("hexstr", hexstr)

    def on_chip_clicked(self, btn: QtWidgets.QPushButton):
        hexstr = btn.property("hexstr")
        if hexstr:
            self.color_clicked.emit(hexstr)


# ---- Expanded Format Row Widget ----
class FormatRow(QtWidgets.QFrame):
    """Card row displaying label, format value and copy button."""
    copied = QtCore.Signal(str)

    def __init__(self, label: str, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self.setFixedHeight(34)
        self.setObjectName("FormatRowFrame")
        self.setStyleSheet("""
            QFrame#FormatRowFrame {
                background: #282C37;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
            }
            QLabel {
                border: none;
                background: transparent;
            }
        """)
        h = QtWidgets.QHBoxLayout(self)
        h.setContentsMargins(6, 3, 6, 3)
        h.setSpacing(6)

        self.tag = QtWidgets.QLabel(label)
        self.tag.setFixedWidth(48)
        self.tag.setAlignment(QtCore.Qt.AlignCenter)
        self.tag.setStyleSheet("""
            QLabel {
                background: #363B49;
                color: #58D082;
                border-radius: 4px;
                font-weight: 800;
                font-size: 11px;
                border: none;
            }
        """)

        self.val_lbl = QtWidgets.QLabel("—")
        self.val_lbl.setStyleSheet("""
            QLabel {
                color: #EDEFF5;
                font-size: 12px;
                font-weight: 600;
                font-family: "Cascadia Code", "Consolas", monospace;
                border: none;
            }
        """)

        self.copy_btn = QtWidgets.QPushButton("복사")
        self.copy_btn.setFixedSize(50, 24)
        self.copy_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.copy_btn.setStyleSheet("""
            QPushButton {
                background: #3A3F4B;
                color: #E6E6EB;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 5px;
                font-size: 11px;
                font-weight: 700;
            }
            QPushButton:hover { background: #58D082; color: #12141A; }
            QPushButton:pressed { background: #46AC67; }
        """)
        self.copy_btn.clicked.connect(self._on_copy)

        h.addWidget(self.tag)
        h.addWidget(self.val_lbl, 1)
        h.addWidget(self.copy_btn)

    def set_value(self, val: str):
        self.val_lbl.setText(val)

    def _on_copy(self):
        text = self.val_lbl.text()
        if text and text != "—":
            QtWidgets.QApplication.clipboard().setText(text)
            self.copied.emit(f"{self.tag.text()}: {text}")


# ---- Help Dialog Modal ----
class HelpDialog(QtWidgets.QDialog):
    """Badge-styled Help & Shortcut Guide Modal."""
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("도움말 가이드")
        self.setFixedSize(480, 360)
        self.setStyleSheet("""
            QDialog {
                background: #1E2129;
                color: #EDEFF5;
            }
            QLabel {
                color: #EDEFF5;
                border: none;
                background: transparent;
            }
        """)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        title = QtWidgets.QLabel("🎯 Color Picker 사용 가이드")
        title.setStyleSheet("font-size: 18px; font-weight: 800; color: #58D082; border: none;")
        layout.addWidget(title)

        guides = [
            ("🖱️ 화면 색상 캡쳐", "Ctrl + 클릭", "화면 위 원하는 마우스 위치의 색상을 즉시 캡쳐"),
            ("⌨️ 커서 단축키 캡쳐", "Ctrl + C", "현재 마우스 커서 지점 색상을 바로 캡쳐"),
            ("📌 최상단 고정", "📌 버튼", "다른 프로그램 위로 항상 최상단 윈도우 고정 유지"),
            ("📥 트레이 백그라운드", "창 최소화 (_)", "최소화 시 시스템 트레이 백그라운드 상주")
        ]

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        container = QtWidgets.QWidget()
        c_lay = QtWidgets.QVBoxLayout(container)
        c_lay.setSpacing(10)
        c_lay.setContentsMargins(0, 0, 0, 0)

        for icon_title, badge_txt, desc in guides:
            row = QtWidgets.QFrame()
            row.setObjectName("GuideRow")
            row.setStyleSheet("""
                QFrame#GuideRow {
                    background: #252833;
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 8px;
                }
                QLabel {
                    border: none;
                    background: transparent;
                }
            """)
            r_lay = QtWidgets.QVBoxLayout(row)
            r_lay.setContentsMargins(12, 10, 12, 10)
            r_lay.setSpacing(4)

            top_h = QtWidgets.QHBoxLayout()
            lbl_title = QtWidgets.QLabel(icon_title)
            lbl_title.setStyleSheet("font-weight: 700; font-size: 13px; color: #EDEFF5; border: none;")

            badge = QtWidgets.QLabel(badge_txt)
            badge.setStyleSheet("""
                QLabel {
                    background: #343947;
                    color: #58D082;
                    font-weight: 800;
                    font-size: 11px;
                    padding: 3px 8px;
                    border-radius: 5px;
                    border: none;
                }
            """)

            top_h.addWidget(lbl_title)
            top_h.addStretch()
            top_h.addWidget(badge)

            lbl_desc = QtWidgets.QLabel(desc)
            lbl_desc.setStyleSheet("font-size: 11px; color: #A8ACB4; border: none;")

            r_lay.addLayout(top_h)
            r_lay.addWidget(lbl_desc)
            c_lay.addWidget(row)

        scroll.setWidget(container)
        layout.addWidget(scroll, 1)

        close_btn = QtWidgets.QPushButton("닫기")
        close_btn.setFixedHeight(36)
        close_btn.setCursor(QtCore.Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background: #58D082;
                color: #12141A;
                font-weight: 800;
                font-size: 13px;
                border-radius: 8px;
            }
            QPushButton:hover { background: #6CE095; }
        """)
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)


# ---- History Item Widget ----
class HistoryItem(QtWidgets.QWidget):
    item_selected = QtCore.Signal(tuple, str)  # (r,g,b), hex

    def __init__(self, rgb: Tuple[int, int, int], hexstr: str, timestamp: str = None, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        if timestamp is None:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        r, g, b = rgb

        lay = QtWidgets.QHBoxLayout(self)
        lay.setContentsMargins(8, 6, 8, 6)
        lay.setSpacing(10)

        sw = QtWidgets.QLabel()
        sw.setFixedSize(24, 24)
        sw.setStyleSheet(f"border-radius:6px; background:{hexstr}; border:1px solid rgba(255,255,255,0.25);")

        info = QtWidgets.QVBoxLayout()
        h, s, l = Core.rgb_to_hsl(r, g, b)
        l1 = QtWidgets.QLabel(f"{hexstr}   RGB({r},{g},{b})")
        l2 = QtWidgets.QLabel(f"{timestamp}  •  HSL({h}°, {s}%, {l}%)")
        l1.setStyleSheet("color:#ECECF1; font-weight:700; font-family:'Cascadia Code', monospace; font-size:12px; border:none;")
        l2.setStyleSheet("color:#A8ACB4; font-size:11px; border:none;")
        info.addWidget(l1)
        info.addWidget(l2)

        btns = QtWidgets.QHBoxLayout()
        select_btn = QtWidgets.QPushButton("선택")
        copy_btn = QtWidgets.QPushButton("복사")
        del_btn = QtWidgets.QPushButton("삭제")

        for btt in (select_btn, copy_btn, del_btn):
            btt.setFixedHeight(24)
            btt.setCursor(QtCore.Qt.PointingHandCursor)
            btt.setStyleSheet("""
                QPushButton { color:#E6E6EB; background:#3A3F4B; border:1px solid rgba(255,255,255,0.08);
                              border-radius:5px; padding:2px 8px; font-size:11px; font-weight:600; }
                QPushButton:hover  { background:#4A5060; color:#FFF; }
                QPushButton:pressed{ background:#343947; }
            """)

        select_btn.setStyleSheet("""
            QPushButton { color:#12141A; background:#58D082; border-radius:5px; padding:2px 8px; font-size:11px; font-weight:800; }
            QPushButton:hover { background:#6CE095; }
        """)

        select_btn.clicked.connect(lambda: self.item_selected.emit(rgb, hexstr))
        copy_btn.clicked.connect(lambda: self._copy_color(r, g, b, hexstr))
        del_btn.clicked.connect(lambda: self.window().remove_me(self))

        btns.addWidget(select_btn)
        btns.addWidget(copy_btn)
        btns.addWidget(del_btn)

        lay.addWidget(sw)
        lay.addLayout(info, 1)
        lay.addLayout(btns)

        self.rgb, self.hex, self.timestamp = rgb, hexstr, timestamp

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        super().mousePressEvent(event)
        self.item_selected.emit(self.rgb, self.hex)

    def _copy_color(self, r, g, b, hexstr):
        QtWidgets.QApplication.clipboard().setText(hexstr)
        if hasattr(self.window(), "show_toast"):
            self.window().show_toast(f"복사 완료: {hexstr}")


class HistoryList(QtWidgets.QListWidget):
    def sizeHint(self):
        return QtCore.QSize(480, 240)


# ---- Main Window UI ----
class MainWindow(QtWidgets.QWidget):
    color_captured = QtCore.Signal(tuple, str)  # (r,g,b), hex

    @QtCore.Slot(int, int, int, str)
    def emit_color(self, r, g, b, hexstr):
        self.color_captured.emit((r, g, b), hexstr)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Color Picker")
        self.setMinimumSize(660, 700)
        self.setStyleSheet("""
            QWidget {
                background: #1E2129;
                color: #EDEFF5;
                font-family: 'Pretendard', 'Malgun Gothic', sans-serif;
            }
            QLabel {
                border: none;
                background: transparent;
            }
        """)

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        # ---- Clean Header ----
        header = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel("🎯 Color Picker")
        title.setStyleSheet("font-size:18px; font-weight:800; color:#58D082; border:none;")
        header.addWidget(title)
        header.addStretch()

        self.help_btn = QtWidgets.QPushButton("❓ 도움말")
        self.help_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.help_btn.setStyleSheet("""
            QPushButton { color:#E6E6EB; background:#3A3F4B; border:1px solid rgba(255,255,255,0.08);
                          border-radius:8px; padding:6px 12px; font-weight:700; }
            QPushButton:hover { background:#4A5060; }
        """)
        self.help_btn.clicked.connect(self.show_help_dialog)
        header.addWidget(self.help_btn)

        self.pin_btn = QtWidgets.QPushButton("📌 항상 위 켜짐")
        self.pin_btn.setCheckable(True)
        self.pin_btn.setChecked(True)
        self.pin_btn.clicked.connect(self.toggle_pin)
        self.pin_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.pin_btn.setStyleSheet("""
            QPushButton { color:#E6E6EB; background:#3A3F4B; border:1px solid rgba(255,255,255,0.08);
                          border-radius:8px; padding:6px 12px; font-weight:700; }
            QPushButton:hover { background:#4A5060; }
            QPushButton:checked { background:#58607A; color:#58D082; border:1px solid #58D082; }
        """)
        header.addWidget(self.pin_btn)
        root.addLayout(header)

        # ---- 1. Main Top Content Card: Left Square Magnifier (200x200) + Right Format Cards Panel ----
        top_card = QtWidgets.QFrame()
        top_card.setObjectName("TopCard")
        top_card.setStyleSheet("QFrame#TopCard { background:#23262F; border:1px solid rgba(88,208,130,0.3); border-radius:12px; }")
        root.addWidget(top_card)

        top_layout = QtWidgets.QHBoxLayout(top_card)
        top_layout.setContentsMargins(14, 14, 14, 14)
        top_layout.setSpacing(14)

        # Left: Square Magnifier (200x200 Fixed 8x)
        self.magnifier = PixelMagnifier(side_size=200)
        top_layout.addWidget(self.magnifier, 0)

        # Right: Captured Color Format Cards Panel
        format_panel = QtWidgets.QWidget()
        f_lay = QtWidgets.QVBoxLayout(format_panel)
        f_lay.setContentsMargins(0, 0, 0, 0)
        f_lay.setSpacing(6)

        cap_header = QtWidgets.QHBoxLayout()
        self.cap_title = QtWidgets.QLabel("📌 캡쳐 색상 상세 포맷 (원하는 포맷 선택 복사)")
        self.cap_title.setStyleSheet("font-size:12px; font-weight:800; color:#58D082; border:none;")
        cap_header.addWidget(self.cap_title)
        cap_header.addStretch()

        self.selected_swatch = QtWidgets.QLabel()
        self.selected_swatch.setFixedSize(20, 20)
        self.selected_swatch.setStyleSheet("border-radius:4px; background:#000000; border:1px solid rgba(255,255,255,0.3);")
        cap_header.addWidget(self.selected_swatch)
        f_lay.addLayout(cap_header)

        # Format Rows (HEX, RGB, HSL, CMYK)
        self.row_hex = FormatRow("HEX")
        self.row_rgb = FormatRow("RGB")
        self.row_hsl = FormatRow("HSL")
        self.row_cmyk = FormatRow("CMYK")

        for r_row in (self.row_hex, self.row_rgb, self.row_hsl, self.row_cmyk):
            r_row.copied.connect(self.show_toast)
            f_lay.addWidget(r_row)

        top_layout.addWidget(format_panel, 1)

        # ---- 2. Standalone Live Color Card (Middle Row, Full Width) ----
        live_card = QtWidgets.QFrame()
        live_card.setObjectName("LiveCard")
        live_card.setFixedHeight(42)
        live_card.setStyleSheet("QFrame#LiveCard { background:#23262F; border:1px solid rgba(255,255,255,0.08); border-radius:8px; }")

        live_lay = QtWidgets.QHBoxLayout(live_card)
        live_lay.setContentsMargins(14, 4, 14, 4)
        live_lay.setSpacing(12)

        # 200px Wide Live Color Swatch Box (Matching 200px Magnifier Width, keeping original 24px height)
        self.live_swatch = QtWidgets.QLabel("#000000")
        self.live_swatch.setFixedSize(200, 24)
        self.live_swatch.setAlignment(QtCore.Qt.AlignCenter)

        self.live_swatch.setStyleSheet("""
            QLabel {
                border-radius: 6px;
                background: #000000;
                color: #FFFFFF;
                font-weight: 800;
                font-size: 12px;
                font-family: 'Cascadia Code', 'Consolas', monospace;
                border: 1px solid rgba(255, 255, 255, 0.3);
            }
        """)

        self.live_text_lbl = QtWidgets.QLabel("🔍 실시간 마우스 색상   RGB(0, 0, 0)")
        self.live_text_lbl.setStyleSheet("""
            QLabel {
                color: #EDEFF5;
                font-size: 13px;
                font-weight: 700;
                font-family: 'Cascadia Code', 'Consolas', monospace;
                border: none;
            }
        """)

        live_lay.addWidget(self.live_swatch)
        live_lay.addWidget(self.live_text_lbl, 1)
        root.addWidget(live_card)

        # ---- 3. Color Harmony Widget ----
        self.harmony_widget = ColorHarmonyWidget()
        self.harmony_widget.color_clicked.connect(self._on_harmony_copied)
        root.addWidget(self.harmony_widget)

        # ---- 4. History Section Header & List ----
        h_head = QtWidgets.QHBoxLayout()
        h_title = QtWidgets.QLabel("📜 세션 히스토리 목록 (클릭 시 상단 포맷 고정)")
        h_title.setStyleSheet("font-size:13px; font-weight:800; border:none;")
        h_head.addWidget(h_title)
        h_head.addStretch()

        self.export_btn = QtWidgets.QPushButton("CSV 내보내기")
        self.clear_btn = QtWidgets.QPushButton("전체 지우기")
        for b in (self.export_btn, self.clear_btn):
            b.setCursor(QtCore.Qt.PointingHandCursor)
            b.setStyleSheet("""
                QPushButton { color:#E6E6EB; background:#3A3F4B; border:1px solid rgba(255,255,255,0.08);
                              border-radius:6px; padding:4px 10px; font-weight:700; font-size:11px; }
                QPushButton:hover { background:#4A5060; }
                QPushButton:pressed{ background:#343947; }
            """)
        self.export_btn.clicked.connect(self.export_csv)
        self.clear_btn.clicked.connect(self.clear_history)

        h_head.addWidget(self.export_btn)
        h_head.addWidget(self.clear_btn)
        root.addLayout(h_head)

        # History List Widget
        self.list = HistoryList()
        self.list.setStyleSheet("""
            QListWidget { background:#23262F; border:1px solid rgba(255,255,255,0.08); border-radius:10px; }
            QScrollBar:vertical { background:#1E2028; width:10px; margin:2px; }
            QScrollBar::handle:vertical { background:#4A5060; border-radius:5px; }
        """)
        root.addWidget(self.list, 1)

        # Color States
        self.live_hex = "#000000"
        self.captured_hex = "#000000"

        # Live Update Timer
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(33)
        self.timer.timeout.connect(self.update_live_preview)
        self.timer.start()

        self.color_captured.connect(self.add_history_item)
        self.load_session_history()

    def show_help_dialog(self):
        dlg = HelpDialog(self)
        dlg.exec()

    def show_toast(self, msg: str):
        toast = ToastNotification(msg, self)
        toast.show_toast(self)

    def _on_harmony_copied(self, hexstr: str):
        QtWidgets.QApplication.clipboard().setText(hexstr)
        self.show_toast(f"조화 색상 복사: {hexstr}")

    def apply_pin_state(self, enabled: bool):
        rect = self.geometry()
        # Toggle only this bit. Rewriting all flags via setWindowFlags() can
        # drop WindowCloseButtonHint and gray out the title-bar close button.
        self.setWindowFlag(QtCore.Qt.WindowType.WindowStaysOnTopHint, enabled)
        self.setGeometry(rect)
        self.show()
        if enabled:
            self.raise_()
        self.pin_btn.setChecked(enabled)
        self.pin_btn.setText("📌 항상 위 켜짐" if enabled else "📌 항상 위 끄기")

    def toggle_pin(self, checked):
        self.apply_pin_state(checked)

    # ---- 실시간 마우스 색상 및 돋보기 업데이트 ----
    def update_live_preview(self):
        x, y = Core.get_cursor_pos_native()
        r, g, b = Core.get_pixel_color_at(x, y)
        self.live_hex = Core.rgb_to_hex(r, g, b)
        self.magnifier.update_magnifier(x, y)

        # 실시간 마우스 색상 박스 갱신 (상단 돋보기 200px 폭과 1:1 수직 라인 맞춤)
        luma = 0.299 * r + 0.587 * g + 0.114 * b
        text_col = "#000000" if luma > 160 else "#FFFFFF"
        self.live_swatch.setText(self.live_hex)
        self.live_swatch.setStyleSheet(f"""
            QLabel {{
                border-radius: 6px;
                background: {self.live_hex};
                color: {text_col};
                font-weight: 800;
                font-size: 12px;
                font-family: 'Cascadia Code', 'Consolas', monospace;
                border: 1px solid rgba(255,255,255,0.3);
            }}
        """)
        self.live_text_lbl.setText(f"🔍 실시간 마우스 색상   RGB({r}, {g}, {b})")

    # ---- 가장 최근 캡쳐 / 선택된 색상 포맷 카드 세팅 ----
    def set_captured_color(self, rgb: Tuple[int, int, int], hexstr: str):
        self.captured_hex = hexstr
        r, g, b = rgb

        h, s, l = Core.rgb_to_hsl(r, g, b)
        c, m, y_c, k = Core.rgb_to_cmyk(r, g, b)

        self.selected_swatch.setStyleSheet(f"border-radius:4px; background:{hexstr}; border:1px solid rgba(255,255,255,0.3);")
        self.cap_title.setText(f"📌 캡쳐 색상 포맷 ({hexstr})")

        self.row_hex.set_value(hexstr)
        self.row_rgb.set_value(f"rgb({r}, {g}, {b})")
        self.row_hsl.set_value(f"hsl({h}°, {s}%, {l}%)")
        self.row_cmyk.set_value(f"cmyk({c}%, {m}%, {y_c}%, {k}%)")

        self.harmony_widget.update_harmony(r, g, b)

    # ---- 히스토리 관리 ----
    def add_history_item(self, rgb: Tuple[int, int, int], hexstr: str, timestamp: str = None):
        it = QtWidgets.QListWidgetItem(self.list)
        w = HistoryItem(rgb, hexstr, timestamp=timestamp, parent=self)
        w.item_selected.connect(self.set_captured_color)
        it.setSizeHint(w.sizeHint())
        self.list.addItem(it)
        self.list.setItemWidget(it, w)

        self.set_captured_color(rgb, hexstr)
        self.save_session_history()

    def load_session_history(self):
        history_data = Core.load_session_history()
        for item in history_data:
            rgb = tuple(item.get("rgb", (0, 0, 0)))
            hexstr = item.get("hex", "#000000")
            ts = item.get("timestamp", None)
            self.add_history_item(rgb, hexstr, timestamp=ts)

        if self.list.count() > 0:
            last_it = self.list.item(self.list.count() - 1)
            w = self.list.itemWidget(last_it)
            if isinstance(w, HistoryItem):
                self.set_captured_color(w.rgb, w.hex)

    def save_session_history(self):
        data = []
        for i in range(self.list.count()):
            it = self.list.item(i)
            w = self.list.itemWidget(it)
            if isinstance(w, HistoryItem):
                data.append({
                    "rgb": list(w.rgb),
                    "hex": w.hex,
                    "timestamp": w.timestamp
                })
        Core.save_session_history(data)

    def remove_me(self, widget: QtWidgets.QWidget):
        for i in range(self.list.count()):
            it = self.list.item(i)
            if self.list.itemWidget(it) is widget:
                self.list.removeItemWidget(it)
                widget.deleteLater()
                self.list.takeItem(i)
                break
        self.save_session_history()

    def clear_history(self):
        for i in reversed(range(self.list.count())):
            it = self.list.item(i)
            w = self.list.itemWidget(it)
            if w is not None:
                self.list.removeItemWidget(it)
                w.deleteLater()
            self.list.takeItem(i)
        self.save_session_history()

    def export_csv(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "CSV로 저장", "color_history.csv", "CSV files (*.csv)"
        )
        if not path:
            return
        rows = []
        for i in range(self.list.count()):
            it = self.list.item(i)
            w = self.list.itemWidget(it)
            if isinstance(w, HistoryItem):
                r, g, b = w.rgb
                h, s, l = Core.rgb_to_hsl(r, g, b)
                rows.append(f"{w.timestamp},{r},{g},{b},{w.hex},hsl({h}° {s}% {l}%)")
        with open(path, "w", encoding="utf-8-sig") as f:
            f.write("Timestamp,R,G,B,HEX,HSL\n")
            f.write("\n".join(rows))
        QtWidgets.QMessageBox.information(self, "완료", f"CSV 저장 성공:\n{path}")

    def contains_native_point(self, nx: int, ny: int) -> bool:
        hwnd = int(self.winId())
        rc = Core.get_window_rect_native(hwnd)
        return (rc.left <= nx < rc.right) and (rc.top <= ny < rc.bottom)

    def changeEvent(self, event: QtCore.QEvent):
        if event.type() == QtCore.QEvent.WindowStateChange:
            if self.isMinimized():
                QtCore.QTimer.singleShot(100, self.hide)
                if hasattr(self, "tray_icon") and self.tray_icon:
                    self.tray_icon.showMessage(
                        "Color Picker",
                        "시스템 트레이로 최소화되었습니다.",
                        QtWidgets.QSystemTrayIcon.Information, 1500
                    )
                elif hasattr(self, "show_toast"):
                    self.show_toast("시스템 트레이로 최소화되었습니다.")
        super().changeEvent(event)
