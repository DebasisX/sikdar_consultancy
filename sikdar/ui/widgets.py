"""Reusable UI building blocks."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import (
    QCalendarWidget, QComboBox, QDateEdit, QDialog, QFrame, QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect, QHBoxLayout, QLabel, QLineEdit, QPushButton, QSizePolicy, QSpinBox,
    QToolButton, QVBoxLayout, QWidget,
)

from . import icons, theme

_AVATAR_COLORS = ["#181A1F", "#2D3138", "#3F4550", "#525866", "#23262C", "#474D59", "#343942", "#5D6472"]


# ------------------------------------------------------------ basic factories
def repolish(w: QWidget) -> None:
    w.style().unpolish(w)
    w.style().polish(w)


def left_headers(table) -> None:
    table.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    table.horizontalHeader().setHighlightSections(False)


class CleanCalendar(QCalendarWidget):
    """Spacious calendar popup with a wide Month dropdown and wide Year spinbox."""

    _MONTHS = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setNavigationBarVisible(False)
        self.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        self.setGridVisible(False)
        self.setMinimumSize(368, 304)

        nav = QFrame()
        nav.setObjectName("calNav")
        nav.setStyleSheet(
            "QFrame#calNav { background:#F4F5F8; border-bottom:1px solid #E1E4EB; "
            "border-top-left-radius:11px; border-top-right-radius:11px; }"
        )
        nl = hbox(nav, (10, 8, 10, 8), 8)

        b_prev = QToolButton()
        b_prev.setCursor(Qt.PointingHandCursor)
        b_prev.setIcon(icons.icon("chevron-left", theme.TEXT_2, 16))
        b_prev.setToolTip("Previous month")
        b_prev.clicked.connect(self.showPreviousMonth)

        self._month = QComboBox()
        self._month.addItems(self._MONTHS)
        self._month.setMinimumWidth(128)
        self._month.setStyleSheet("padding: 5px 10px; border-radius: 9px; font-weight: 600;")
        self._month.currentIndexChanged.connect(self._on_month)

        self._year = QComboBox()
        self._year.setEditable(True)
        self._year.setInsertPolicy(QComboBox.NoInsert)
        self._year.addItems([str(y) for y in range(2040, 1919, -1)])
        self._year.setMinimumWidth(96)
        self._year.setStyleSheet("padding: 5px 10px; border-radius: 9px; font-weight: 700;")
        self._year.currentTextChanged.connect(self._on_year)

        b_next = QToolButton()
        b_next.setCursor(Qt.PointingHandCursor)
        b_next.setIcon(icons.icon("chevron-right", theme.TEXT_2, 16))
        b_next.setToolTip("Next month")
        b_next.clicked.connect(self.showNextMonth)

        nl.addWidget(b_prev)
        nl.addWidget(self._month, 1)
        nl.addWidget(self._year)
        nl.addWidget(b_next)

        lay = self.layout()
        if lay is not None:
            lay.insertWidget(0, nav)

        self.currentPageChanged.connect(self._sync_nav)
        self._sync_nav(self.yearShown(), self.monthShown())

    def _sync_nav(self, year: int, month: int) -> None:
        self._month.blockSignals(True)
        self._year.blockSignals(True)
        self._month.setCurrentIndex(max(0, min(11, month - 1)))
        self._year.setCurrentText(str(year))
        self._month.blockSignals(False)
        self._year.blockSignals(False)

    def _on_month(self, idx: int) -> None:
        try:
            yr = int(self._year.currentText().strip())
        except ValueError:
            yr = self.yearShown()
        self.setCurrentPage(yr, idx + 1)

    def _on_year(self, text: str) -> None:
        t = text.strip()
        if len(t) == 4 and t.isdigit():
            yr = int(t)
            if 1900 <= yr <= 2100:
                self.setCurrentPage(yr, self._month.currentIndex() + 1)


def clean_date_edit(display_fmt: str = "dd MMM yyyy") -> QDateEdit:
    """Create a QDateEdit with a spacious calendar popup and wide, uncongested year selector."""
    de = QDateEdit()
    de.setCalendarPopup(True)
    de.setCalendarWidget(CleanCalendar(de))
    de.setDisplayFormat(display_fmt)
    de.setMinimumHeight(40)
    return de


def button(text: str = "", icon: str | None = None, kind: str = "secondary",
           small: bool = False, icon_color: str | None = None) -> QPushButton:
    b = QPushButton(text)
    b.setCursor(Qt.PointingHandCursor)
    b.setProperty("kind", kind)
    if small:
        b.setProperty("size", "sm")
    if icon:
        color = icon_color or {"primary": "#FFFFFF", "danger": theme.DANGER,
                               "solidDanger": "#FFFFFF"}.get(kind, theme.TEXT_2)
        b.setIcon(icons.icon(icon, color, 18))
    return b


def label(text: str = "", name: str = "", wrap: bool = False) -> QLabel:
    lb = QLabel(text)
    if name:
        lb.setObjectName(name)
    lb.setWordWrap(wrap)
    return lb


def chip(text: str, kind: str = "neutral") -> QLabel:
    lb = QLabel(text)
    lb.setProperty("chip", kind)
    lb.setAlignment(Qt.AlignCenter)
    lb.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
    return lb


def shadow(w: QWidget, blur: int = 28, dy: int = 6, alpha: int = 22) -> None:
    eff = QGraphicsDropShadowEffect(w)
    eff.setBlurRadius(blur)
    eff.setOffset(0, dy)
    eff.setColor(QColor(15, 23, 42, alpha))
    w.setGraphicsEffect(eff)


def card(shadowed: bool = True, flat: bool = False) -> QFrame:
    f = QFrame()
    f.setObjectName("cardFlat" if flat else "card")
    if shadowed:
        shadow(f, 32, 6, 15)
    return f


def divider(vertical: bool = False) -> QFrame:
    f = QFrame()
    f.setObjectName("vdivider" if vertical else "divider")
    return f


def vbox(parent: QWidget | None = None, margins=(0, 0, 0, 0), spacing: int = 0) -> QVBoxLayout:
    lay = QVBoxLayout(parent) if parent is not None else QVBoxLayout()
    lay.setContentsMargins(*margins)
    lay.setSpacing(spacing)
    return lay


def hbox(parent: QWidget | None = None, margins=(0, 0, 0, 0), spacing: int = 0) -> QHBoxLayout:
    lay = QHBoxLayout(parent) if parent is not None else QHBoxLayout()
    lay.setContentsMargins(*margins)
    lay.setSpacing(spacing)
    return lay


# --------------------------------------------------------------- avatars
def initials(name: str) -> str:
    parts = [p for p in (name or "?").split() if p]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def avatar_pixmap(photo: Path | None, name: str, size: int = 40) -> QPixmap:
    scale = 2
    px = size * scale
    out = QPixmap(px, px)
    out.fill(Qt.transparent)
    p = QPainter(out)
    p.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
    path = QPainterPath()
    path.addEllipse(QRectF(0, 0, px, px))
    p.setClipPath(path)
    src = QPixmap(str(photo)) if photo else QPixmap()
    if not src.isNull():
        src = src.scaled(px, px, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        p.drawPixmap((px - src.width()) // 2, (px - src.height()) // 2, src)
    else:
        base = QColor(_AVATAR_COLORS[sum(map(ord, name or "?")) % len(_AVATAR_COLORS)])
        g = QLinearGradient(0, 0, px, px)
        g.setColorAt(0, base.lighter(118))
        g.setColorAt(1, base.darker(112))
        p.fillRect(0, 0, px, px, g)
        p.setPen(QColor("white"))
        f = QFont(theme.FONT.split(",")[1].strip(" '"))
        f.setPixelSize(int(px * 0.38))
        f.setWeight(QFont.DemiBold)
        p.setFont(f)
        p.drawText(QRectF(0, 0, px, px), Qt.AlignCenter, initials(name))
    p.end()
    out.setDevicePixelRatio(scale)
    return out


class AvatarLabel(QLabel):
    def __init__(self, size: int = 40, parent=None):
        super().__init__(parent)
        self._size = size
        self.setFixedSize(size, size)

    def set_client(self, photo: Path | None, name: str) -> None:
        self.setPixmap(avatar_pixmap(photo, name, self._size))


# --------------------------------------------------------------- inputs
class PasswordEdit(QLineEdit):
    def __init__(self, placeholder: str = "", parent=None):
        super().__init__(parent)
        self.setEchoMode(QLineEdit.Password)
        self.setPlaceholderText(placeholder)
        self._shown = False
        self._act = self.addAction(icons.icon("eye", theme.MUTED, 18), QLineEdit.TrailingPosition)
        self._act.setToolTip("Show / hide")
        self._act.triggered.connect(self.toggle)

    def toggle(self) -> None:
        self._shown = not self._shown
        self.setEchoMode(QLineEdit.Normal if self._shown else QLineEdit.Password)
        self._act.setIcon(icons.icon("eye-off" if self._shown else "eye", theme.MUTED, 18))


def search_box(placeholder: str) -> QLineEdit:
    e = QLineEdit()
    e.setObjectName("search")
    e.setPlaceholderText(placeholder)
    e.setClearButtonEnabled(True)
    e.addAction(icons.icon("search", theme.MUTED, 18), QLineEdit.LeadingPosition)
    return e


class Field(QWidget):
    """Label + input + inline error message."""

    def __init__(self, text: str, widget: QWidget, required: bool = False, hint: str = ""):
        super().__init__()
        self.widget = widget
        lay = vbox(self, spacing=6)
        lb = label(text + (" *" if required else ""), "fieldLabel")
        lay.addWidget(lb)
        lay.addWidget(widget)
        self._err = label("", "error")
        self._err.setVisible(False)
        lay.addWidget(self._err)
        if hint:
            lay.addWidget(label(hint, "muted"))

    def set_error(self, msg: str = "") -> None:
        self._err.setText(msg)
        self._err.setVisible(bool(msg))
        self.widget.setProperty("invalid", bool(msg))
        repolish(self.widget)


# ---------------------------------------------------------------- header
class PageHeader(QWidget):
    def __init__(self, title: str, subtitle: str = ""):
        super().__init__()
        lay = hbox(self, spacing=12)
        col = vbox(spacing=3)
        self.title = label(title, "h1")
        self.subtitle = label(subtitle, "sub")
        col.addWidget(self.title)
        col.addWidget(self.subtitle)
        lay.addLayout(col)
        lay.addStretch(1)
        self.actions = hbox(spacing=10)
        lay.addLayout(self.actions)

    def add_action(self, w: QWidget) -> None:
        self.actions.addWidget(w)


class StatCard(QFrame):
    clicked = Signal()

    def __init__(self, title: str, icon_name: str, color: str, soft: str, clickable: bool = False):
        super().__init__()
        self.setObjectName("card")
        self._clickable = clickable
        if clickable:
            self.setProperty("clickable", True)
            self.setCursor(Qt.PointingHandCursor)
        shadow(self, 32, 6, 15)
        lay = hbox(self, (22, 20, 22, 20), 14)
        col = vbox(spacing=4)
        self.title = label(title, "sub")
        self.value = label("0", "h1")
        self.note = label("", "muted")
        col.addWidget(self.title)
        col.addWidget(self.value)
        col.addWidget(self.note)
        lay.addLayout(col, 1)
        badge = QLabel()
        badge.setFixedSize(48, 48)
        badge.setAlignment(Qt.AlignCenter)
        badge.setStyleSheet(f"background:{soft}; border-radius: 15px;")
        badge.setPixmap(icons.pixmap(icon_name, color, 22))
        lay.addWidget(badge, 0, Qt.AlignTop)

    def set_clickable(self, enabled: bool = True, tooltip: str = "") -> None:
        self._clickable = enabled
        self.setProperty("clickable", enabled)
        self.setCursor(Qt.PointingHandCursor if enabled else Qt.ArrowCursor)
        if tooltip:
            self.setToolTip(tooltip)
        repolish(self)

    def mousePressEvent(self, event) -> None:
        if self._clickable and event.button() == Qt.LeftButton:
            self.clicked.emit()
            event.accept()
            return
        super().mousePressEvent(event)

    def set(self, value: str, note: str = "") -> None:
        self.value.setText(value)
        self.note.setText(note)


def empty_state(icon_name: str, title: str, text: str) -> QWidget:
    w = QWidget()
    lay = vbox(w, (20, 40, 20, 40), 8)
    lay.setAlignment(Qt.AlignCenter)
    badge = QLabel()
    badge.setFixedSize(64, 64)
    badge.setAlignment(Qt.AlignCenter)
    badge.setStyleSheet(f"background:{theme.BRAND_SOFT}; border-radius: 32px;")
    badge.setPixmap(icons.pixmap(icon_name, theme.BRAND, 28))
    lay.addWidget(badge, 0, Qt.AlignHCenter)
    t = label(title, "h3")
    t.setAlignment(Qt.AlignCenter)
    s = label(text, "sub", wrap=True)
    s.setAlignment(Qt.AlignCenter)
    s.setMaximumWidth(380)
    lay.addSpacing(6)
    lay.addWidget(t)
    lay.addWidget(s, 0, Qt.AlignHCenter)
    return w


# ----------------------------------------------------------------- toast
class Toast(QLabel):
    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setObjectName("toast")
        self.hide()
        self._fx = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._fx)
        self._anim = QPropertyAnimation(self._fx, b"opacity", self)
        self._timer = QTimer(self, singleShot=True)
        self._timer.timeout.connect(self._fade_out)

    def show_message(self, text: str, kind: str = "info", ms: int = 2800) -> None:
        self.setProperty("kind", kind)
        repolish(self)
        self.setText(text)
        self.adjustSize()
        self.reposition()
        self.show()
        self.raise_()
        self._anim.stop()
        self._anim.setDuration(180)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        try:
            self._anim.finished.disconnect()
        except RuntimeError:
            pass
        self._anim.start()
        self._timer.start(ms)

    def reposition(self) -> None:
        p = self.parentWidget()
        if p:
            self.move(p.width() - self.width() - 28, p.height() - self.height() - 28)

    def _fade_out(self) -> None:
        self._anim.stop()
        self._anim.setDuration(260)
        self._anim.setStartValue(1.0)
        self._anim.setEndValue(0.0)
        self._anim.finished.connect(self.hide)
        self._anim.start()


# ---------------------------------------------------------------- dialogs
class BaseDialog(QDialog):
    def __init__(self, parent, title: str, width: int = 460):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(width)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)


class ConfirmDialog(BaseDialog):
    def __init__(self, parent, title: str, message: str, confirm_text: str = "Confirm",
                 danger: bool = False, icon_name: str | None = None):
        super().__init__(parent, title, 440)
        lay = vbox(self, (26, 26, 26, 22), 16)
        top = hbox(spacing=16)
        badge = QLabel()
        badge.setFixedSize(46, 46)
        badge.setAlignment(Qt.AlignCenter)
        color, soft = (theme.DANGER, theme.DANGER_SOFT) if danger else (theme.BRAND, theme.BRAND_SOFT)
        badge.setStyleSheet(f"background:{soft}; border-radius: 23px;")
        badge.setPixmap(icons.pixmap(icon_name or ("alert" if danger else "check-circle"), color, 22))
        top.addWidget(badge, 0, Qt.AlignTop)
        col = vbox(spacing=6)
        col.addWidget(label(title, "h2"))
        col.addWidget(label(message, "sub", wrap=True))
        top.addLayout(col, 1)
        lay.addLayout(top)
        row = hbox(spacing=10)
        row.addStretch(1)
        cancel = button("Cancel")
        ok = button(confirm_text, kind="solidDanger" if danger else "primary")
        cancel.clicked.connect(self.reject)
        ok.clicked.connect(self.accept)
        ok.setDefault(True)
        row.addWidget(cancel)
        row.addWidget(ok)
        lay.addLayout(row)


def confirm(parent, title: str, message: str, confirm_text: str = "Confirm",
            danger: bool = False, icon_name: str | None = None) -> bool:
    return ConfirmDialog(parent, title, message, confirm_text, danger, icon_name).exec() == QDialog.Accepted


class TextPrompt(BaseDialog):
    def __init__(self, parent, title: str, field_label: str, value: str = "",
                 ok_text: str = "Save", placeholder: str = ""):
        super().__init__(parent, title, 420)
        lay = vbox(self, (26, 24, 26, 22), 14)
        lay.addWidget(label(title, "h2"))
        self.edit = QLineEdit(value)
        self.edit.setPlaceholderText(placeholder)
        lay.addWidget(Field(field_label, self.edit))
        self.edit.selectAll()
        row = hbox(spacing=10)
        row.addStretch(1)
        cancel = button("Cancel")
        ok = button(ok_text, kind="primary")
        cancel.clicked.connect(self.reject)
        ok.clicked.connect(self.accept)
        ok.setDefault(True)
        row.addWidget(cancel)
        row.addWidget(ok)
        lay.addLayout(row)

    def value(self) -> str:
        return self.edit.text().strip()


def prompt_text(parent, title: str, field_label: str, value: str = "",
                ok_text: str = "Save", placeholder: str = "") -> str | None:
    d = TextPrompt(parent, title, field_label, value, ok_text, placeholder)
    return d.value() if d.exec() == QDialog.Accepted else None
