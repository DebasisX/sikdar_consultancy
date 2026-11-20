"""Design tokens and the global stylesheet — Layered Silver, White & Charcoal monochrome theme."""
from __future__ import annotations

# Layered Monochrome Palette (Charcoal, Titanium, Silver, Platinum, Pearl White)
NAVY = "#131519"         # Deep charcoal (sidebar / hero)
NAVY_2 = "#1B1E24"       # Graphite surface
NAVY_3 = "#282C34"       # Titanium hover / dark border
BRAND = "#1A1D22"        # Soft charcoal primary accent
BRAND_DARK = "#2D313A"   # Brushed graphite hover
BRAND_SOFT = "#EAEDF2"   # Soft platinum tint
SILVER = "#A4ABB6"       # Metallic silver
SILVER_LIGHT = "#D5D9E1" # Light brushed silver
SILVER_DEEP = "#6C7380"  # Pewter silver
BG = "#EEF0F4"           # Soft pearl-silver canvas
CARD = "#FFFFFF"         # Pure white cards
BORDER = "#E1E4EB"       # Hairline silver border
BORDER_STRONG = "#C9CED8"
TEXT = "#16181D"         # Soft obsidian text (easier on eyes than #000)
TEXT_2 = "#4E5460"       # Graphite secondary text
MUTED = "#7D8491"        # Silver-slate muted text

# Tasteful muted semantic tones
SUCCESS = "#047857"
SUCCESS_SOFT = "#ECFDF5"
WARN = "#B45309"
WARN_SOFT = "#FEF3C7"
DANGER = "#B91C1C"
DANGER_SOFT = "#FEF2F2"
INFO_SOFT = "#E7EAF0"

FONT = "'Segoe UI Variable Text', 'Segoe UI', 'Inter', sans-serif"

QSS = f"""
* {{ font-family: {FONT}; font-size: 13px; color: {TEXT}; outline: 0; }}
QMainWindow, QDialog {{ background: {BG}; }}
QWidget#page {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #F3F4F7, stop:1 #EAECEF);
}}
QToolTip {{
    background: {NAVY_2}; color: #F8F9FA; border: 1px solid {NAVY_3};
    padding: 7px 10px; border-radius: 9px;
}}

/* ---------- typography ---------- */
QLabel {{ background: transparent; }}
QLabel#h1 {{ font-size: 24px; font-weight: 700; color: {TEXT}; }}
QLabel#h2 {{ font-size: 16px; font-weight: 650; color: {TEXT}; }}
QLabel#h3 {{ font-size: 14px; font-weight: 600; color: {TEXT}; }}
QLabel#sub {{ color: {TEXT_2}; font-size: 13px; }}
QLabel#muted {{ color: {MUTED}; font-size: 12px; }}
QLabel#fieldLabel {{ color: {TEXT_2}; font-size: 12px; font-weight: 600; }}
QLabel#error {{ color: {DANGER}; font-size: 12px; }}

/* ---------- cards ---------- */
QFrame#card {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #FFFFFF, stop:1 #FAFBFD);
    border: 1px solid {BORDER};
    border-radius: 18px;
}}
QFrame#card[clickable="true"]:hover {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #FFFFFF, stop:1 #F1F3F7);
    border: 1px solid #B5BCC8;
}}
QFrame#dashRow {{ background: transparent; border-radius: 12px; border: 1px solid transparent; }}
QFrame#dashRow:hover {{ background: #F3F5F8; border: 1px solid #E4E7EE; }}
QFrame#cardFlat {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 16px;
}}
QFrame#divider {{ background: {BORDER}; border: none; max-height: 1px; min-height: 1px; }}
QFrame#vdivider {{ background: {BORDER}; border: none; max-width: 1px; min-width: 1px; }}
QSplitter::handle {{ background: transparent; }}
QSplitter::handle:horizontal {{ width: 8px; margin: 12px 2px; border-radius: 2px; }}
QSplitter::handle:horizontal:hover {{ background: #C8CDD7; }}
QSplitter#mainSplit::handle:horizontal {{ width: 5px; margin: 0px; background: #1E2128; }}
QSplitter#mainSplit::handle:horizontal:hover {{ background: #6C7380; }}

/* ---------- sidebar ---------- */
QFrame#sidebar {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #111317, stop:0.55 #181B21, stop:1 #111317);
    border-right: 1px solid {NAVY_3};
}}
QLabel#brandName {{ color: #F9FAFB; font-size: 15px; font-weight: 700; letter-spacing: 0.4px; }}
QLabel#brandTag {{ color: #9097A4; font-size: 11px; letter-spacing: 0.5px; }}
QLabel#navSection {{ color: #6B7280; font-size: 11px; font-weight: 700; letter-spacing: 1.3px; }}
QPushButton#nav {{
    background: transparent; color: #B8BFC9; border: none; border-radius: 13px;
    padding: 11px 15px; text-align: left; font-size: 13.5px; font-weight: 500;
}}
QPushButton#nav:hover {{ background: {NAVY_3}; color: #FFFFFF; }}
QPushButton#nav:checked {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FFFFFF, stop:1 #E8EBF0);
    color: {NAVY}; font-weight: 700;
}}
QFrame#userChip {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1D2027, stop:1 #16181E);
    border-radius: 14px; border: 1px solid #2A2E37;
}}
QLabel#chipName {{ color: #F9FAFB; font-weight: 600; font-size: 13px; }}
QLabel#chipRole {{ color: #8E95A3; font-size: 11px; }}
QPushButton#chipBtn {{ background: transparent; border: none; border-radius: 10px; padding: 6px; }}
QPushButton#chipBtn:hover {{ background: {NAVY_3}; }}

/* ---------- buttons ---------- */
QPushButton {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #FFFFFF, stop:1 #F3F5F8);
    color: {TEXT}; border: 1px solid {BORDER_STRONG};
    border-radius: 12px; padding: 9px 17px; font-weight: 600;
}}
QPushButton:hover {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #F8F9FB, stop:1 #E7EBF0);
    border-color: #A5ACB8;
}}
QPushButton:pressed {{ background: #DFE3EA; }}
QPushButton:disabled {{ color: #A6ACB6; background: #F4F5F8; border-color: {BORDER}; }}
QPushButton[kind="primary"] {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #262A32, stop:1 #131519);
    color: #FFFFFF; border: 1px solid #131519;
}}
QPushButton[kind="primary"]:hover {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #353A45, stop:1 #1E2128);
    border-color: #2B2F38;
}}
QPushButton[kind="primary"]:pressed {{ background: #0B0C0E; }}
QPushButton[kind="primary"]:disabled {{ background: #9CA3AF; border-color: #9CA3AF; color: #FFFFFF; }}
QPushButton[kind="danger"] {{ background: {CARD}; color: {DANGER}; border: 1px solid #ECCACA; }}
QPushButton[kind="danger"]:hover {{ background: {DANGER_SOFT}; border-color: #DDA4A4; }}
QPushButton[kind="solidDanger"] {{ background: {DANGER}; color: #FFFFFF; border: 1px solid {DANGER}; }}
QPushButton[kind="solidDanger"]:hover {{ background: #991B1B; }}
QPushButton[kind="done"] {{
    background: #ECFDF5; color: #047857; border: 1px solid #A7F3D0;
    border-radius: 10px; padding: 5px 11px; font-size: 12px; font-weight: 700;
}}
QPushButton[kind="done"]:hover {{ background: #059669; color: #FFFFFF; border-color: #059669; }}
QPushButton[kind="done"]:pressed {{ background: #047857; color: #FFFFFF; }}
QPushButton[kind="undo"] {{
    background: #F1F3F6; color: {TEXT_2}; border: 1px solid {BORDER_STRONG};
    border-radius: 10px; padding: 5px 11px; font-size: 12px; font-weight: 600;
}}
QPushButton[kind="undo"]:hover {{ background: #E4E7EE; color: {TEXT}; }}
QPushButton[kind="ghost"] {{ background: transparent; border: 1px solid transparent; color: {TEXT_2}; }}
QPushButton[kind="ghost"]:hover {{ background: #E5E8EE; color: {TEXT}; }}
QPushButton[kind="link"] {{ background: transparent; border: none; color: {TEXT_2}; padding: 4px 8px; font-weight: 600; }}
QPushButton[kind="link"]:hover {{ color: {TEXT}; background: transparent; text-decoration: underline; }}
QPushButton[size="sm"] {{ padding: 6px 12px; border-radius: 10px; font-size: 12px; }}
QToolButton {{ background: transparent; border: none; border-radius: 10px; padding: 6px; }}
QToolButton:hover {{ background: #E5E8EE; }}

/* ---------- quick link tiles ---------- */
QPushButton#quickLink {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #FFFFFF, stop:1 #F2F4F8);
    color: {TEXT}; border: 1px solid #DDE1E8; border-radius: 15px;
    padding: 0px; text-align: left; font-weight: 600;
}}
QPushButton#quickLink:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #F9FAFC, stop:1 #E6E9F0);
    border-color: #AEB5C2;
}}
QPushButton#quickLink:pressed {{
    background: #DFE3EB;
    border-color: #98A0AE;
}}

/* ---------- inputs ---------- */
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QDateEdit, QSpinBox, QDoubleSpinBox {{
    background: #FBFCFE; border: 1px solid {BORDER_STRONG}; border-radius: 12px;
    padding: 9px 13px; selection-background-color: {BRAND}; selection-color: #FFFFFF;
}}
QLineEdit:hover, QTextEdit:hover, QComboBox:hover, QDateEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover {{
    border-color: #979EAA; background: #FFFFFF;
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus, QDateEdit:focus,
QSpinBox:focus, QDoubleSpinBox:focus {{
    background: #FFFFFF; border: 1.5px solid {BRAND}; padding: 8.5px 12.5px;
}}
/* Strip inner child QLineEdit borders so QDateEdit / editable QComboBox / QSpinBox have NO boxed edges inside rounded borders */
QDateEdit QLineEdit, QComboBox QLineEdit, QSpinBox QLineEdit, QDoubleSpinBox QLineEdit {{
    border: none; background: transparent; padding: 0px; border-radius: 0px;
}}
QDateEdit QLineEdit:hover, QDateEdit QLineEdit:focus,
QComboBox QLineEdit:hover, QComboBox QLineEdit:focus,
QSpinBox QLineEdit:hover, QSpinBox QLineEdit:focus {{
    border: none; background: transparent; padding: 0px;
}}
QDateEdit {{ min-width: 154px; }}
QLineEdit[invalid="true"], QTextEdit[invalid="true"], QComboBox[invalid="true"] {{ border: 1.5px solid {DANGER}; }}
QLineEdit:read-only {{ background: #F2F4F7; }}
QLineEdit#search {{ background: #FFFFFF; padding: 10px 14px 10px 38px; border-radius: 13px; }}
QComboBox::drop-down {{ background: transparent; border: none; width: 30px; }}
QComboBox::down-arrow {{ image: url(@@CHEVRON@@); width: 14px; height: 14px; }}
QComboBox QAbstractItemView {{
    background: #FFFFFF; border: 1px solid {BORDER_STRONG}; border-radius: 10px; padding: 4px;
    selection-background-color: {BRAND_SOFT}; selection-color: {TEXT}; outline: 0;
}}
QDateEdit::drop-down {{ background: transparent; border: none; width: 30px; }}
QDateEdit::down-arrow {{ image: url(@@CHEVRON@@); width: 14px; height: 14px; }}

/* Spacious, clean Calendar Popup (fixes congested year spinbox & boxed edges) */
QCalendarWidget {{
    background: #FFFFFF; border: 1px solid {BORDER_STRONG}; border-radius: 12px;
    min-width: 340px; min-height: 290px;
}}
QCalendarWidget QWidget {{ background: #FFFFFF; alternate-background-color: #F6F7FA; }}
QCalendarWidget QWidget#qt_calendar_navigationbar {{
    background: #F4F5F8; border-bottom: 1px solid {BORDER};
    min-height: 46px; padding: 4px 8px;
}}
QCalendarWidget QToolButton {{
    background: transparent; color: {TEXT}; border: none; border-radius: 8px;
    padding: 5px 10px; font-weight: 650; font-size: 13px;
}}
QCalendarWidget QToolButton:hover {{ background: #E4E7EE; }}
QCalendarWidget QToolButton#qt_calendar_monthbutton {{ min-width: 96px; padding-right: 18px; }}
QCalendarWidget QToolButton#qt_calendar_yearbutton {{ min-width: 74px; padding: 5px 12px; }}
QCalendarWidget QToolButton::menu-indicator {{ image: none; }}
QCalendarWidget QSpinBox#qt_calendar_yearedit {{
    background: #FFFFFF; color: {TEXT}; border: 1px solid {BORDER_STRONG};
    border-radius: 8px; min-width: 84px; max-width: 96px; min-height: 28px; max-height: 32px;
    padding: 2px 6px; font-size: 13px; font-weight: 700;
}}
QCalendarWidget QSpinBox#qt_calendar_yearedit:focus {{
    border: 1.5px solid {BRAND}; padding: 1.5px 5.5px;
}}
QCalendarWidget QSpinBox#qt_calendar_yearedit::up-button,
QCalendarWidget QSpinBox#qt_calendar_yearedit::down-button {{ width: 18px; border: none; background: transparent; }}
QCalendarWidget QAbstractItemView:enabled {{
    background: #FFFFFF; color: {TEXT};
    selection-background-color: {BRAND}; selection-color: #FFFFFF;
    border: none; outline: 0; font-size: 12.5px;
}}
QCalendarWidget QAbstractItemView:disabled {{ color: #B4BAC6; }}

QCheckBox {{ spacing: 8px; }}
QCheckBox::indicator {{ width: 18px; height: 18px; border-radius: 6px; border: 1.5px solid {BORDER_STRONG}; background: #FFFFFF; }}
QCheckBox::indicator:hover {{ border-color: {BRAND}; }}
QCheckBox::indicator:checked {{ background: {BRAND}; border-color: {BRAND}; }}

/* ---------- tables ---------- */
QTableWidget, QTableView {{
    background: transparent; border: none; gridline-color: transparent;
    alternate-background-color: #F9FAFC; selection-background-color: {BRAND_SOFT};
    selection-color: {TEXT};
}}
QTableWidget::item {{ padding: 0 12px; border-bottom: 1px solid #ECEFF4; }}
QTableWidget::item:selected {{ background: {BRAND_SOFT}; color: {TEXT}; }}
QHeaderView {{ background: transparent; border: none; }}
QHeaderView::section {{
    background: transparent; color: {TEXT_2}; border: none; border-bottom: 1px solid {BORDER};
    padding: 11px 12px; font-size: 11.5px; font-weight: 700; text-transform: uppercase;
}}
QTableCornerButton::section {{ background: transparent; border: none; }}

QListWidget {{ background: transparent; border: none; }}
QListWidget#folders::item {{
    padding: 11px 12px; border-radius: 12px; margin: 2px 0; color: {TEXT};
}}
QListWidget#folders::item:hover {{ background: #EFF1F5; }}
QListWidget#folders::item:selected {{ background: #E5E8EE; color: {TEXT}; font-weight: 600; }}

/* ---------- scrollbars ---------- */
QScrollArea {{ background: transparent; border: none; }}
QScrollBar:vertical {{ background: transparent; width: 12px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #C5CBD5; border-radius: 5px; min-height: 36px; margin: 0 2px; }}
QScrollBar::handle:vertical:hover {{ background: #9EA6B4; }}
QScrollBar:horizontal {{ background: transparent; height: 12px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: #C5CBD5; border-radius: 5px; min-width: 36px; margin: 2px 0; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

/* ---------- menus & dialogs ---------- */
QMenu {{ background: #FFFFFF; border: 1px solid {BORDER_STRONG}; border-radius: 12px; padding: 6px; }}
QMenu::item {{ padding: 8px 22px 8px 12px; border-radius: 8px; }}
QMenu::item:selected {{ background: {BRAND_SOFT}; }}
QMenu::separator {{ height: 1px; background: {BORDER}; margin: 5px 8px; }}
QMessageBox {{ background: #FFFFFF; }}
QProgressBar {{ background: #E4E7EE; border: none; border-radius: 4px; max-height: 6px; }}
QProgressBar::chunk {{ background: {BRAND}; border-radius: 4px; }}

/* ---------- chips ---------- */
QLabel[chip="success"] {{ background: {SUCCESS_SOFT}; color: {SUCCESS}; border-radius: 12px; padding: 4px 11px; font-size: 11.5px; font-weight: 700; }}
QLabel[chip="warn"] {{ background: {WARN_SOFT}; color: {WARN}; border-radius: 12px; padding: 4px 11px; font-size: 11.5px; font-weight: 700; }}
QLabel[chip="danger"] {{ background: {DANGER_SOFT}; color: {DANGER}; border-radius: 12px; padding: 4px 11px; font-size: 11.5px; font-weight: 700; }}
QLabel[chip="info"] {{ background: #E6E9F0; color: {TEXT}; border-radius: 12px; padding: 4px 11px; font-size: 11.5px; font-weight: 700; }}
QLabel[chip="neutral"] {{ background: #EFF1F5; color: {TEXT_2}; border-radius: 12px; padding: 4px 11px; font-size: 11.5px; font-weight: 700; }}

/* ---------- login ---------- */
QFrame#brandPanel {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #101216, stop:0.55 #1A1D24, stop:1 #262A33);
    border: none;
}}
QLabel#heroTitle {{ color: #FFFFFF; font-size: 32px; font-weight: 700; }}
QLabel#heroSub {{ color: #B8BFC9; font-size: 13.5px; }}
QLabel#heroBullet {{ color: #DDE1E8; font-size: 13px; }}
QFrame#loginPanel {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #F6F7FA, stop:1 #ECEEF3);
    border: none;
}}
QLabel#toast {{ background: {NAVY}; color: #FFFFFF; border-radius: 12px; padding: 12px 18px; font-weight: 600; }}
QLabel#toast[kind="success"] {{ background: #14532D; }}
QLabel#toast[kind="error"] {{ background: #991B1B; }}
QFrame#dropZone {{ border: 2px dashed {BORDER_STRONG}; border-radius: 16px; background: #F8F9FC; }}
QFrame#dropZone[active="true"] {{ border-color: {BRAND}; background: {BRAND_SOFT}; }}
"""
