"""Dashboard overview."""
from __future__ import annotations

from datetime import date, datetime

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QPushButton, QScrollArea, QWidget

from .. import deadlines, storage, validators
from ..context import AppContext
from . import icons, theme
from .widgets import (
    AvatarLabel, PageHeader, StatCard, button, card, chip, divider, empty_state, hbox, label, vbox,
)


def when_chip(due: date, today: date | None = None) -> tuple[str, str]:
    today = today or date.today()
    d = (due - today).days
    if d < 0:
        return f"{-d}d overdue", "danger"
    if d == 0:
        return "Today", "danger"
    if d == 1:
        return "Tomorrow", "danger"
    if d <= 7:
        return f"in {d} days", "warn"
    if d <= 30:
        return f"in {d} days", "info"
    return f"in {d} days", "neutral"


def greeting() -> str:
    h = datetime.now().hour
    return "Good morning" if h < 12 else "Good afternoon" if h < 17 else "Good evening"


class Dashboard(QWidget):
    open_client = Signal(int)
    open_documents = Signal()
    goto_pending_fees = Signal()
    goto = Signal(str)
    add_client = Signal()
    toast = Signal(str, str)

    def __init__(self, ctx: AppContext):
        super().__init__()
        self.setObjectName("page")
        self.ctx = ctx
        outer = vbox(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        host = QWidget()
        host.setObjectName("page")
        scroll.setWidget(host)
        outer.addWidget(scroll)
        lay = vbox(host, (36, 30, 36, 30), 22)

        self.header = PageHeader("", "")
        b = button("Register client", "user-plus", "primary")
        b.clicked.connect(self.add_client.emit)
        self.header.add_action(b)
        lay.addWidget(self.header)

        stats = QGridLayout()
        stats.setSpacing(18)
        self.s_clients = StatCard("Total clients", "users", "#2563EB", "#EAF1FF", clickable=True)
        self.s_clients.setToolTip("Open Clients directory")
        self.s_clients.clicked.connect(lambda: self.goto.emit("clients"))

        self.s_docs = StatCard("Documents stored", "file-text", "#059669", "#E6F7F0", clickable=True)
        self.s_docs.setToolTip("Open client document folders")
        self.s_docs.clicked.connect(self.open_documents.emit)

        self.s_tasks = StatCard("Pending tasks", "clock", "#D97706", "#FEF3C7", clickable=True)
        self.s_tasks.setToolTip("Open Deadlines & Tasks")
        self.s_tasks.clicked.connect(lambda: self.goto.emit("deadlines"))

        self.s_fees = StatCard("Outstanding fees", "rupee", "#DC2626", "#FEE2E2", clickable=True)
        self.s_fees.setToolTip("View pending fee dues")
        self.s_fees.clicked.connect(self.goto_pending_fees.emit)

        for i, s in enumerate((self.s_clients, self.s_docs, self.s_tasks, self.s_fees)):
            stats.addWidget(s, 0, i)
            stats.setColumnStretch(i, 1)
        lay.addLayout(stats)

        mid = hbox(spacing=18)
        self.due_card = card()
        self.due_lay = vbox(self.due_card, (24, 22, 24, 18), 0)
        self.recent_card = card()
        self.recent_lay = vbox(self.recent_card, (24, 22, 24, 18), 0)
        mid.addWidget(self.due_card, 3)
        mid.addWidget(self.recent_card, 2)
        lay.addLayout(mid)

        # ---- Income Tax Quick Links
        self.links_card = self._build_quick_links()
        lay.addWidget(self.links_card)

        self.act_card = card()
        self.act_lay = vbox(self.act_card, (24, 22, 24, 18), 0)
        lay.addWidget(self.act_card)
        lay.addStretch(1)

    def _build_quick_links(self) -> QFrame:
        f = card()
        fl = vbox(f, (26, 24, 26, 24), 16)
        hd = hbox(spacing=10)
        ic_badge = QLabel()
        ic_badge.setFixedSize(32, 32)
        ic_badge.setAlignment(Qt.AlignCenter)
        ic_badge.setStyleSheet("background:#EAF1FF; border-radius:10px;")
        ic_badge.setPixmap(icons.pixmap("globe", "#2563EB", 16))
        hd.addWidget(ic_badge)
        hd.addWidget(label("Income Tax quick links", "h2"))
        hd.addStretch(1)
        hd.addWidget(label("Opens official government portals in your browser", "muted"))
        fl.addLayout(hd)

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(14)
        # Distinct colored icon badges (blue, yellow, green, purple, sky, teal, orange, red)
        link_styles = [
            ("globe", "#2563EB", "#EAF1FF"),        # e-Filing (blue)
            ("calendar", "#D97706", "#FEF3C7"),     # CBDT Calendar (yellow/amber)
            ("rupee", "#059669", "#E6F7F0"),        # e-Pay Tax (green)
            ("file-text", "#7C3AED", "#F3E8FF"),    # TRACES (purple)
            ("briefcase", "#0284C7", "#E0F2FE"),    # Income Tax India (sky blue)
            ("shield", "#0D9488", "#CCFBF1"),       # GST Portal (teal)
            ("id-card", "#EA580C", "#FFEDD5"),      # PAN Services (amber-orange)
            ("check-circle", "#DC2626", "#FEE2E2"), # Refund Status (red)
        ]
        for idx, ql in enumerate(deadlines.QUICK_LINKS):
            tile = QPushButton()
            tile.setObjectName("quickLink")
            tile.setCursor(Qt.PointingHandCursor)
            tile.setToolTip(ql.url)
            tile.setMinimumHeight(76)
            tl = hbox(tile, (16, 14, 14, 14), 12)
            ic_name, fg_c, bg_c = link_styles[idx % len(link_styles)]
            tag = QLabel()
            tag.setAttribute(Qt.WA_TransparentForMouseEvents)
            tag.setFixedSize(40, 40)
            tag.setAlignment(Qt.AlignCenter)
            tag.setStyleSheet(f"background:{bg_c}; border-radius:12px;")
            tag.setPixmap(icons.pixmap(ic_name, fg_c, 19))
            tl.addWidget(tag, 0, Qt.AlignVCenter)
            col = vbox(spacing=3)
            t_lbl = label(ql.title, "h3")
            t_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)
            s_lbl = label(ql.subtitle, "muted", wrap=True)
            s_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)
            col.addWidget(t_lbl)
            col.addWidget(s_lbl)
            tl.addLayout(col, 1)
            ext = QLabel()
            ext.setAttribute(Qt.WA_TransparentForMouseEvents)
            ext.setPixmap(icons.pixmap("external-link", theme.MUTED, 15))
            tl.addWidget(ext, 0, Qt.AlignTop)
            tile.clicked.connect(lambda _=False, u=ql.url: QDesktopServices.openUrl(QUrl(u)))
            grid.addWidget(tile, idx // 2, idx % 2)
        for c in range(2):
            grid.setColumnStretch(c, 1)
        fl.addLayout(grid)
        return f

    @staticmethod
    def _clear(layout) -> None:
        while layout.count():
            it = layout.takeAt(0)
            if it.widget():
                w = it.widget()
                w.hide()
                w.setParent(None)
                w.deleteLater()
            elif it.layout():
                Dashboard._clear(it.layout())

    @staticmethod
    def _title(text: str, action: str = "", slot=None) -> hbox:
        row = hbox(spacing=8)
        row.addWidget(label(text, "h2"))
        row.addStretch(1)
        if action:
            b = button(action, kind="link", small=True)
            b.clicked.connect(slot)
            row.addWidget(b)
        return row

    def refresh(self) -> None:
        db = self.ctx.db
        self.header.title.setText(f"{greeting()}, {self.ctx.firm_name()}")
        self.header.subtitle.setText(datetime.now().strftime("%A, %d %B %Y") + "  ·  Here is your practice at a glance.")

        clients = db.list_clients()
        docs = sum(n for c in clients for _, n in storage.list_folders(c["folder_name"]))
        billed, recv = db.fee_totals()
        active = sum(1 for c in clients if c["status"] == "Active")
        self.s_clients.set(str(len(clients)), f"{active} active")
        self.s_docs.set(str(docs), "across all folders")
        pend = db.pending_task_count()
        self.s_tasks.set(str(pend), "need attention" if pend else "all caught up")
        self.s_fees.set(validators.inr(max(billed - recv, 0)), f"of {validators.inr(billed)} billed")

        # --- upcoming
        self._clear(self.due_lay)
        self.due_lay.addLayout(self._title("Upcoming deadlines", "View all", lambda: self.goto.emit("deadlines")))
        self.due_lay.addSpacing(10)
        today = date.today()
        items: list[tuple[date, str, str, str, int | None]] = []
        for t in db.list_tasks(include_done=False):
            try:
                d = date.fromisoformat(t["due_date"])
            except ValueError:
                continue
            sub = t["client_name"] or "General task"
            items.append((d, t["title"], sub, "task", t["id"]))
        for s in deadlines.upcoming(today, 75, db.statutory_overrides(), db.list_custom_statutory()):
            if s.custom_id is not None:
                sub = f"Manual statutory date ({s.kind})"
            else:
                sub = "Statutory due date (edited)" if s.edited else "Statutory due date"
            items.append((s.due, s.title, sub, "stat", None))
        items.sort(key=lambda x: x[0])
        for d, title, sub, kind, tid in items[:6]:
            self.due_lay.addWidget(self._deadline_row(d, title, sub, kind, tid))
        if not items:
            self.due_lay.addWidget(empty_state("calendar", "Nothing due soon", "You're all clear."))
        self.due_lay.addStretch(1)

        # --- recent clients
        self._clear(self.recent_lay)
        self.recent_lay.addLayout(self._title("Recent clients", "All clients", lambda: self.goto.emit("clients")))
        self.recent_lay.addSpacing(10)
        recent = sorted(clients, key=lambda c: c["id"], reverse=True)[:5]
        for c in recent:
            self.recent_lay.addWidget(self._client_row(c))
        if not recent:
            self.recent_lay.addWidget(empty_state("user-plus", "No clients yet", "Register your first client."))
        self.recent_lay.addStretch(1)

        # --- activity
        self._clear(self.act_lay)
        self.act_lay.addLayout(self._title("Recent activity"))
        self.act_lay.addSpacing(8)
        acts = db.recent_activity(6)
        for a in acts:
            r = hbox(spacing=12)
            dot = QLabel()
            dot.setFixedSize(8, 8)
            dot.setStyleSheet(f"background:{theme.BRAND}; border-radius:4px;")
            r.addWidget(dot)
            r.addWidget(label(a["text"]), 1)
            try:
                ts = datetime.fromisoformat(a["ts"]).strftime("%d %b, %I:%M %p")
            except ValueError:
                ts = a["ts"]
            r.addWidget(label(ts, "muted"))
            w = QWidget()
            w.setLayout(r)
            r.setContentsMargins(0, 7, 0, 7)
            self.act_lay.addWidget(w)
        if not acts:
            self.act_lay.addWidget(label("No activity yet.", "sub"))

    def _tick_task(self, tid: int, title: str) -> None:
        self.ctx.db.set_task_done(tid, True)
        self.ctx.db.log(f"Task completed: {title}")
        self.refresh()
        self.toast.emit(f"Completed: {title}", "success")

    def _deadline_row(self, d: date, title: str, sub: str, kind: str, tid: int | None = None) -> QWidget:
        w = QFrame()
        w.setObjectName("dashRow")
        w.setCursor(Qt.PointingHandCursor)
        r = hbox(w, (8, 8, 8, 8), 14)
        cal = QLabel()
        cal.setFixedSize(46, 50)
        cal.setAlignment(Qt.AlignCenter)
        cal.setText(f"<div style='line-height:110%'><span style='font-size:17px; font-weight:700;'>{d.day}</span>"
                    f"<br><span style='font-size:10px; font-weight:700; color:{theme.MUTED}'>{d.strftime('%b').upper()}</span></div>")
        cal.setStyleSheet(
            f"background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #F8F9FB, stop:1 #EBEEF3); "
            f"border-radius:13px; border:1px solid {theme.BORDER};"
        )
        r.addWidget(cal)
        col = vbox(spacing=1)
        col.addWidget(label(title, "h3"))
        col.addWidget(label(sub, "muted"))
        r.addLayout(col, 1)
        txt, kindc = when_chip(d)
        r.addWidget(chip(txt, kindc))
        if kind == "task" and tid is not None:
            b_done = button("Done", "check", "done", small=True, icon_color="#047857")
            b_done.setToolTip("Tick off task as completed")
            b_done.clicked.connect(lambda _=False, t_id=tid, t_lbl=title: self._tick_task(t_id, t_lbl))
            r.addWidget(b_done)
        w.mousePressEvent = lambda e: self.goto.emit("deadlines") if e.button() == Qt.LeftButton else None
        return w

    def _client_row(self, c) -> QWidget:
        w = QFrame()
        w.setObjectName("dashRow")
        w.setCursor(Qt.PointingHandCursor)
        r = hbox(w, (8, 8, 8, 8), 12)
        av = AvatarLabel(40)
        av.set_client(self.ctx.photo_path(c["photo"]), c["name"])
        r.addWidget(av)
        col = vbox(spacing=1)
        col.addWidget(label(c["name"], "h3"))
        col.addWidget(label(c["pan"] or validators.format_phone(c["phone"]), "muted"))
        r.addLayout(col, 1)
        r.addWidget(chip(c["status"], "success" if c["status"] == "Active" else "neutral"))
        cid = c["id"]
        w.mousePressEvent = lambda e, cid=cid: self.open_client.emit(cid) if e.button() == Qt.LeftButton else None
        return w
