"""Generate assets/app.ico from assets/logo.png (used by the PyInstaller build)."""
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QApplication

from sikdar.ui.brand import draw_mark

app = QApplication(sys.argv)
out = Path(__file__).parent / "assets"
out.mkdir(exist_ok=True)
img = QImage(256, 256, QImage.Format_ARGB32)
img.fill(Qt.transparent)
p = QPainter(img)
draw_mark(p, 256, radius_ratio=0.16, border=False)
p.end()
ok = img.save(str(out / "app.ico"), "ICO")
print("ico written:", ok, out / "app.ico")
