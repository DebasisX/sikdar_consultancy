"""Main application window: login <-> shell with sidebar navigation."""
from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QEvent, QObject, QPropertyAnimation, Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication, QButtonGroup, QFrame, QGraphicsOpacityEffect, QHBoxLayout, QMainWindow,
    QMessageBox, QPushButton, QSplitter, QStackedWidget, QWidget,
)

from .. import paths, storage
from ..context import AppContext
from . import icons, theme
from .brand import BrandMark, app_icon
from .client_detail import ClientDetailPage
from .clients import ClientsPage
from .dashboard import Dashboard
from .deadlines_page import DeadlinesPage
from .fees import FeesPage
from .login import LoginPage
from .settings import SettingsPage
from .widgets import Toast, button, hbox, label, vbox

NAV = [
    ("dashboard", "Dashboard", "dashboard"),
    ("clients", "Clients", "users"),
    ("deadlines", "Deadlines & Tasks", "calendar"),
    ("fees", "Fees & Payments", "rupee"),
    ("settings", "Settings", "settings"),
]


class Sidebar(QFrame):
    def __init__(self, on_nav, on_logout):
        super().__init__()
        self.setObjectName("sidebar")
        self.setMinimumWidth(190)
        self.setMaximumWidth(380)
        lay = vbox(self, (16, 22, 16, 18), 0)
        brand = hbox(spacing=12)
        brand.setContentsMargins(6, 0, 0, 0)
        brand.addWidget(BrandMark(40, radius_ratio=0.22))
        col = vbox(spacing=1)
        col.addWidget(label("Sikdar Consultancy", "brandName"))
        col.addWidget(label("Tax Consultancy · Estd 2000", "brandTag"))
        brand.addLayout(col)
        brand.addStretch(1)
        lay.addLayout(brand)
        lay.addSpacing(30)
        sec = label("MENU", "navSection")
        sec.setContentsMargins(14, 0, 0, 8)
        lay.addWidget(sec)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.buttons: dict[str, QPushButton] = {}
        for key, text, ic in NAV:
            b = QPushButton("  " + text.replace("&", "&&"))
            b.setObjectName("nav")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setIcon(icons.icon(ic, "#AAB6CE", 20))
            b.setIconSize(b.iconSize().expandedTo(b.iconSize()))
            b.clicked.connect(lambda _=False, k=key: on_nav(k))
            self.group.addButton(b)
            self.buttons[key] = b
            lay.addWidget(b)
            lay.addSpacing(4)
        lay.addStretch(1)

        chip = QFrame()
        chip.setObjectName("userChip")
        cl = hbox(chip, (12, 10, 8, 10), 10)
        self.avatar = label("", "")
        self.avatar.setFixedSize(34, 34)
        self.avatar.setAlignment(Qt.AlignCenter)
        self.avatar.setStyleSheet("background:#E5E7EB; color:#0B0C0E; border-radius:17px; font-weight:700;")
        cl.addWidget(self.avatar)
        col = vbox(spacing=0)
        self.owner = label("owner", "chipName")
        col.addWidget(self.owner)
        col.addWidget(label("Owner · Administrator", "chipRole"))
        cl.addLayout(col, 1)
        out = QPushButton()
        out.setObjectName("chipBtn")
        out.setCursor(Qt.PointingHandCursor)
        out.setIcon(icons.icon("logout", "#B4BAC4", 20))
        out.setToolTip("Sign out (Ctrl+L)")
        out.clicked.connect(on_logout)
        cl.addWidget(out)
        lay.addWidget(chip)

    def set_owner(self, owner_id: str) -> None:
        self.owner.setText(owner_id)
        self.avatar.setText(owner_id[:1].upper())

    def check(self, key: str) -> None:
        b = self.buttons.get(key)
        if b:
            b.setChecked(True)
        for k, bt in self.buttons.items():
            ic = {"dashboard": "dashboard", "clients": "users", "deadlines": "calendar",
                  "fees": "rupee", "settings": "settings"}[k]
            bt.setIcon(icons.icon(ic, theme.NAVY if bt.isChecked() else "#B4BAC4", 20))


class Shell(QWidget):
    def __init__(self, ctx: AppContext, on_logout):
        super().__init__()
        self.ctx = ctx
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setObjectName("mainSplit")
        self.splitter.setChildrenCollapsible(False)
        self.sidebar = Sidebar(self.navigate, on_logout)
        self.stack = QStackedWidget()
        self.splitter.addWidget(self.sidebar)
        self.splitter.addWidget(self.stack)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setSizes([260, 1100])
        lay.addWidget(self.splitter)

        self.dashboard = Dashboard(ctx)
        self.clients = ClientsPage(ctx)
        self.detail = ClientDetailPage(ctx)
        self.deadlines = DeadlinesPage(ctx)
        self.fees = FeesPage(ctx)
        self.settings = SettingsPage(ctx)
        self.pages = {"dashboard": self.dashboard, "clients": self.clients, "detail": self.detail,
                      "deadlines": self.deadlines, "fees": self.fees, "settings": self.settings}
        for p in self.pages.values():
            self.stack.addWidget(p)

        self._fade_anim: QPropertyAnimation | None = None
        self._fade_page: QWidget | None = None

        self.dashboard.goto.connect(self.navigate)
        self.dashboard.open_client.connect(self.open_client)
        self.dashboard.open_documents.connect(self._open_user_documents)
        self.dashboard.goto_pending_fees.connect(self._open_pending_fees)
        self.dashboard.add_client.connect(self._register)
        self.clients.open_client.connect(self.open_client)
        self.detail.back.connect(lambda: self.navigate("clients"))
        self.detail.go_fees.connect(self._detail_fees)
        self.settings.firm_changed.connect(self.dashboard.refresh)

    def _transition_to(self, page: QWidget) -> None:
        """Smoothly fade in the target page, then clear the effect so card shadows stay sharp."""
        if self.stack.currentWidget() is page:
            return
        if self._fade_anim is not None:
            self._fade_anim.stop()
            if self._fade_page is not None:
                self._fade_page.setGraphicsEffect(None)
        self.stack.setCurrentWidget(page)
        fx = QGraphicsOpacityEffect(page)
        fx.setOpacity(0.15)
        page.setGraphicsEffect(fx)
        anim = QPropertyAnimation(fx, b"opacity", self)
        anim.setDuration(160)
        anim.setStartValue(0.15)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.finished.connect(lambda p=page: p.setGraphicsEffect(None))
        self._fade_page = page
        self._fade_anim = anim
        anim.start()

    def _register(self) -> None:
        self.navigate("clients")
        self.clients.add_client()

    def _open_pending_fees(self) -> None:
        self.fees.show_pending()
        self._transition_to(self.fees)
        self.sidebar.check("fees")

    def _open_user_documents(self) -> None:
        """Open the most recent client with documents directly, or Clients directory if none."""
        clients = self.ctx.db.list_clients()
        if not clients:
            self.navigate("clients")
            return
        # Prefer the most recent client that has uploaded documents, else most recent client
        ordered = sorted(clients, key=lambda c: c["id"], reverse=True)
        pick = next(
            (c for c in ordered if any(n > 0 for _, n in storage.list_folders(c["folder_name"]))),
            ordered[0],
        )
        self.open_client(pick["id"])

    def _detail_fees(self, cid: int) -> None:
        self.fees.show_client(cid) if cid else self.fees.refresh()
        self._transition_to(self.fees)
        self.sidebar.check("fees")

    def navigate(self, key: str) -> None:
        page = self.pages[key]
        if hasattr(page, "refresh"):
            page.refresh()
        self._transition_to(page)
        self.sidebar.check("clients" if key == "detail" else key)

    def open_client(self, cid: int) -> None:
        self.detail.load(cid)
        self._transition_to(self.detail)
        self.sidebar.check("clients")

    def start(self) -> None:
        self.sidebar.set_owner(self.ctx.owner_id())
        self.navigate("dashboard")


class _ActivityFilter(QObject):
    def __init__(self, on_activity):
        super().__init__()
        self._cb = on_activity

    def eventFilter(self, obj, ev):
        if ev.type() in (QEvent.MouseMove, QEvent.MouseButtonPress, QEvent.KeyPress, QEvent.Wheel):
            self._cb()
        return False


class MainWindow(QMainWindow):
    def __init__(self, ctx: AppContext):
        super().__init__()
        self.ctx = ctx
        self.setWindowTitle(paths.APP_NAME)
        self.setWindowIcon(app_icon())
        self.resize(1360, 840)
        self.setMinimumSize(1120, 700)

        self.root = QStackedWidget()
        self.setCentralWidget(self.root)
        self.login = LoginPage(ctx)
        self.shell = Shell(ctx, self.logout)
        self.root.addWidget(self.login)
        self.root.addWidget(self.shell)
        self.login.authenticated.connect(self._signed_in)

        self.toast = Toast(self.root)
        for page in (self.shell.dashboard, self.shell.clients, self.shell.detail,
                     self.shell.deadlines, self.shell.fees, self.shell.settings):
            page.toast.connect(self.toast.show_message)
        for page in (self.shell.detail, self.shell.clients, self.shell.deadlines, self.shell.fees):
            page.data_changed.connect(lambda: None)
        self.shell.settings.autolock_changed.connect(self._setup_autolock)
        self.shell.settings.restored.connect(self._after_restore)
        self.shell.settings.data_cleared.connect(self._after_user_clear)
        self.shell.settings.admin_cleared.connect(self._after_admin_clear)

        self._idle = QTimer(self, singleShot=True)
        self._idle.timeout.connect(self._idle_lock)
        self._filter = _ActivityFilter(self._poke)
        QApplication.instance().installEventFilter(self._filter)

        QShortcut(QKeySequence("Ctrl+L"), self, activated=self.logout)
        QShortcut(QKeySequence("Ctrl+N"), self, activated=self._shortcut_new)
        QShortcut(QKeySequence("Ctrl+F"), self, activated=self._shortcut_find)

        self.show_login()

    # -- navigation between login and app
    def show_login(self) -> None:
        self._idle.stop()
        self.root.setCurrentWidget(self.login)
        self.login.show_for_state()

    def _signed_in(self) -> None:
        self.shell.start()
        self.root.setCurrentWidget(self.shell)
        self._setup_autolock()

    def logout(self) -> None:
        if self.root.currentWidget() is not self.shell:
            return
        self.ctx.logout()
        self.shell.detail.client = None
        self.show_login()

    # -- idle auto-lock
    def _setup_autolock(self) -> None:
        mins = self.ctx.autolock_minutes()
        if mins and self.root.currentWidget() is self.shell:
            self._idle.start(mins * 60_000)
        else:
            self._idle.stop()

    def _poke(self) -> None:
        if self._idle.isActive():
            self._idle.start()

    def _idle_lock(self) -> None:
        if self.root.currentWidget() is self.shell:
            self.logout()
            self.login.l_err.setText("You were signed out after a period of inactivity.")
            self.login.l_err.show()

    # -- shortcuts
    def _shortcut_new(self) -> None:
        if self.root.currentWidget() is self.shell:
            self.shell._register()

    def _shortcut_find(self) -> None:
        if self.root.currentWidget() is self.shell:
            self.shell.navigate("clients")
            self.shell.clients.search.setFocus()
            self.shell.clients.search.selectAll()

    def _after_restore(self) -> None:
        self.shell.detail.client = None
        self.show_login()
        self.toast.show_message("Backup restored — sign in with the backup's owner account", "success", 4500)

    def _after_user_clear(self) -> None:
        self.shell.detail.client = None
        self.shell.dashboard.refresh()
        self.shell.clients.refresh()
        self.shell.deadlines.refresh()
        self.shell.fees.refresh()

    def _after_admin_clear(self) -> None:
        self.shell.detail.client = None
        self.login.l_id.clear()
        self.show_login()
        self.toast.show_message("All data & admin account cleared — set up a new office", "info", 4500)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.toast.reposition()

    def closeEvent(self, e):
        self.ctx.db.close()
        super().closeEvent(e)
