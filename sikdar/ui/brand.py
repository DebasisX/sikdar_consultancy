"""Brand logo and application icon loaded from assets/logo.png."""
from __future__ import annotations

from functools import lru_cache

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QWidget

from .. import paths


@lru_cache(maxsize=1)
def _raw_logo() -> QPixmap:
    p = paths.resource_path("assets/logo.png")
    if p.exists():
        pm = QPixmap(str(p))
        if not pm.isNull():
            return pm
    return QPixmap()


def draw_mark(p: QPainter, size: float, radius_ratio: float = 0.22, border: bool = True) -> None:
    p.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform | QPainter.TextAntialiasing)
    r = QRectF(0, 0, size, size)
    path = QPainterPath()
    path.addRoundedRect(r, size * radius_ratio, size * radius_ratio)
    p.save()
    p.setClipPath(path)

    logo = _raw_logo()
    if not logo.isNull():
        scaled = logo.scaled(int(size * 2), int(size * 2),
                             Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        p.drawPixmap(r, scaled, QRectF(0, 0, scaled.width(), scaled.height()))
    else:
        g = QLinearGradient(0, 0, size, size)
        g.setColorAt(0, QColor("#C4C8D0"))
        g.setColorAt(1, QColor("#FFFFFF"))
        p.fillPath(path, g)
        p.setPen(QColor("#111214"))
        f = QFont("Segoe UI")
        f.setPixelSize(int(size * 0.56))
        f.setWeight(QFont.Bold)
        p.setFont(f)
        p.drawText(r, Qt.AlignCenter, "S")

    p.restore()
    if border:
        pen = QPen(QColor(200, 205, 214, 140))
        pen.setWidthF(max(1.0, size * 0.015))
        p.setPen(pen)
        p.drawRoundedRect(r.adjusted(0.5, 0.5, -0.5, -0.5), size * radius_ratio, size * radius_ratio)


class BrandMark(QWidget):
    """Square rounded brand emblem (used in sidebar, login hero, about card)."""

    def __init__(self, size: int = 40, radius_ratio: float = 0.22, border: bool = True, parent=None):
        super().__init__(parent)
        self._s = size
        self._rr = radius_ratio
        self._border = border
        self.setFixedSize(size, size)

    def paintEvent(self, _):
        p = QPainter(self)
        draw_mark(p, self._s, self._rr, self._border)


def app_icon() -> QIcon:
    ic = QIcon()
    for s in (16, 24, 32, 48, 64, 128, 256):
        pm = QPixmap(s, s)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        draw_mark(p, s, radius_ratio=0.18, border=False)
        p.end()
        ic.addPixmap(pm)
    return ic
