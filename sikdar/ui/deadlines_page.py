"""Deadlines & tasks page with editable statutory due dates."""
from __future__ import annotations

from datetime import date

from PySide6.QtCore import QDate, Qt, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QDateEdit, QDialog, QHeaderView, QLineEdit, QMenu,
    QSplitter, QTableWidget, QTableWidgetItem, QWidget,
)

from .. import deadlines
from ..context import AppContext
from . import icons, theme
from .dashboard import when_chip
from .widgets import (
    BaseDialog, Field, PageHeader, button, card, clean_date_edit, confirm, divider, empty_state,
    hbox, label, left_headers, vbox,
)


class TaskDialog(BaseDialog):
    def __init__(self, parent, ctx: AppContext, task=None, client_id: int | None = None):
        super().__init__(parent, "Edit task" if task else "New task", 460)
        lay = vbox(self, (26, 24, 26, 22), 14)
        lay.addWidget(label("Edit task" if task else "New task", "h2"))
        self.title = QLineEdit(task["title"] if task else "")
        self.title.setPlaceholderText("e.g. File ITR-1 for FY 2024-25")
        self.client = QComboBox()
        self.client.addItem("No client (general)", None)
        for c in ctx.db.list_clients():
            self.client.addItem(f"{c['name']}  ·  {c['pan']}" if c["pan"] else c["name"], c["id"])
        want = task["client_id"] if task else client_id
        if want:
            i = self.client.findData(want)
            if i >= 0:
                self.client.setCurrentIndex(i)
        self.due = clean_date_edit()
        self.due.setDate(QDate.fromString(task["due_date"], Qt.ISODate) if task else QDate.currentDate().addDays(7))
        self.prio = QComboBox()
        self.prio.addItems(["Normal", "High", "Low"])
        if task:
            self.prio.setCurrentText(task["priority"])
        self.f_title = Field("Task", self.title, True)
        lay.addWidget(self.f_title)
        lay.addWidget(Field("Client", self.client))
        row = hbox(spacing=14)
        row.addWidget(Field("Due date", self.due))
        row.addWidget(Field("Priority", self.prio))
        lay.addLayout(row)
        lay.addSpacing(6)
        foot = hbox(spacing=10)
        foot.addStretch(1)
        c = button("Cancel")
        c.clicked.connect(self.reject)
        ok = button("Save task", kind="primary")
        ok.setDefault(True)
        ok.clicked.connect(self._ok)
        foot.addWidget(c)
        foot.addWidget(ok)
        lay.addLayout(foot)

    def _ok(self) -> None:
        if not self.title.text().strip():
            self.f_title.set_error("Describe the task")
            return
        self.accept()

    def values(self):
        return (self.title.text().strip(), self.due.date().toString(Qt.ISODate),
                self.client.currentData(), self.prio.currentText())


class EditStatutoryDialog(BaseDialog):
    """Add a manual statutory date, edit/delete a manual one, or edit/reset a standard date."""

    def __init__(self, parent, item: deadlines.Statutory | None = None):
        is_new = item is None
        is_custom = (item is None) or (item.custom_id is not None)
        title_str = (
            "Add manual statutory date" if is_new
            else ("Edit manual statutory date" if is_custom else "Edit statutory due date")
        )
        super().__init__(parent, title_str, 490)
        self.item = item
        self.is_custom = is_custom
        self.reset_requested = False
        self.delete_requested = False

        lay = vbox(self, (26, 24, 26, 22), 14)
        lay.addWidget(label(title_str, "h2"))
        if is_new:
            lay.addWidget(label(
                "Add a custom statutory deadline (e.g. GSTR-1, GSTR-3B, GST Annual Return, or CBDT notification).",
                "sub", wrap=True))
        elif is_custom:
            lay.addWidget(label("Update or remove this manual statutory deadline.", "sub", wrap=True))
        else:
            lay.addWidget(label(
                f"Standard date: {item.default_due.strftime('%d %b %Y')}. "
                "Update when CBDT announces an extension.", "sub", wrap=True))

        self.title = QLineEdit(item.title if item else "")
        self.title.setPlaceholderText("e.g. GSTR-3B Monthly Return / Form 10B Audit")
        self.due = clean_date_edit()
        if item:
            self.due.setDate(QDate(item.due.year, item.due.month, item.due.day))
        else:
            self.due.setDate(QDate.currentDate().addDays(15))
        self.kind = QComboBox()
        self.kind.addItems(deadlines.STATUTORY_KINDS)
        if item and item.kind in deadlines.STATUTORY_KINDS:
            self.kind.setCurrentText(item.kind)
        self.note = QLineEdit(item.note if item else "")
        self.note.setPlaceholderText("e.g. Extended via CBDT Circular / GST Notification")

        self.f_title = Field("Obligation", self.title, True)
        lay.addWidget(self.f_title)
        if is_custom:
            r1 = hbox(spacing=14)
            r1.addWidget(Field("Due date", self.due, True), 1)
            r1.addWidget(Field("Category", self.kind), 1)
            lay.addLayout(r1)
        else:
            lay.addWidget(Field("Due date", self.due, True))
        lay.addWidget(Field("Note / Circular reference (optional)", self.note))

        lay.addSpacing(6)
        foot = hbox(spacing=10)
        if item and item.custom_id is not None:
            b_del = button("Delete", "trash", "danger", small=True)
            b_del.clicked.connect(self._delete)
            foot.addWidget(b_del)
        elif item and item.edited:
            b_reset = button("Reset to standard", "rotate-ccw", "ghost", small=True)
            b_reset.clicked.connect(self._reset)
            foot.addWidget(b_reset)
        foot.addStretch(1)
        c = button("Cancel")
        c.clicked.connect(self.reject)
        ok = button("Add date" if is_new else "Save date", "check", "primary")
        ok.setDefault(True)
        ok.clicked.connect(self._ok)
        foot.addWidget(c)
        foot.addWidget(ok)
        lay.addLayout(foot)

    def _reset(self) -> None:
        self.reset_requested = True
        self.accept()

    def _delete(self) -> None:
        self.delete_requested = True
        self.accept()

    def _ok(self) -> None:
        if not self.title.text().strip():
            self.f_title.set_error("Obligation title cannot be empty")
            return
        self.accept()

    def values(self) -> tuple[str, str, str, str]:
        return (
            self.due.date().toString(Qt.ISODate),
            self.title.text().strip(),
            self.kind.currentText(),
            self.note.text().strip(),
        )


class DeadlinesPage(QWidget):
    data_changed = Signal()
    toast = Signal(str, str)

    def __init__(self, ctx: AppContext):
        super().__init__()
        self.setObjectName("page")
        self.ctx = ctx
        self._stat_items: list[deadlines.Statutory] = []
        lay = vbox(self, (36, 30, 36, 28), 20)
        self.header = PageHeader("Deadlines & tasks", "Editable statutory due dates and your own to-do list.")
        b_cal = button("CBDT Calendar", "external-link")
        b_cal.setToolTip("Open official Income Tax India tax calendar in browser")
        b_cal.clicked.connect(lambda: QDesktopServices.openUrl(
            QUrl("https://www.incometaxindia.gov.in/en/tax-calendar")))
        b = button("New task", "plus", "primary")
        b.clicked.connect(self.add_task)
        self.header.add_action(b_cal)
        self.header.add_action(b)
        lay.addWidget(self.header)

        row = QSplitter(Qt.Horizontal)
        row.setChildrenCollapsible(False)
        lay.addWidget(row, 1)

        # tasks
        self.tasks_card = card()
        tl = vbox(self.tasks_card, (8, 0, 8, 10))
        head = hbox(spacing=10)
        head.setContentsMargins(24, 20, 24, 14)
        head.addWidget(label("My tasks", "h2"))
        head.addStretch(1)
        self.show_done = button("Show completed", kind="ghost", small=True)
        self.show_done.setCheckable(True)
        self.show_done.toggled.connect(self.refresh)
        head.addWidget(self.show_done)
        hw = QWidget()
        hw.setLayout(head)
        tl.addWidget(hw)
        tl.addWidget(divider())
        self.tasks = QTableWidget(0, 6)
        self.tasks.setHorizontalHeaderLabels(["", "Task", "Client", "Due", "Priority", "Action"])
        self._style(self.tasks)
        hh = self.tasks.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Fixed)
        self.tasks.setColumnWidth(0, 44)
        hh.setSectionResizeMode(1, QHeaderView.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.Interactive)
        self.tasks.setColumnWidth(2, 138)
        hh.setSectionResizeMode(3, QHeaderView.Fixed)
        self.tasks.setColumnWidth(3, 108)
        hh.setSectionResizeMode(4, QHeaderView.Fixed)
        self.tasks.setColumnWidth(4, 84)
        hh.setSectionResizeMode(5, QHeaderView.Fixed)
        self.tasks.setColumnWidth(5, 112)
        self.tasks.cellClicked.connect(self._task_clicked)
        self.tasks.cellDoubleClicked.connect(lambda r, c: self.edit_task(r) if c not in (0, 5) else None)
        self.tasks.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tasks.customContextMenuRequested.connect(self._task_menu)
        tl.addWidget(self.tasks, 1)
        self.tasks_empty = empty_state("check-circle", "No tasks", "Add a task to keep track of client work.")
        tl.addWidget(self.tasks_empty, 1)
        self.tasks_card.setMinimumWidth(320)
        row.addWidget(self.tasks_card)

        # statutory
        self.stat_card = card()
        sl = vbox(self.stat_card, (8, 0, 8, 10))
        sh = hbox(spacing=10)
        sh.setContentsMargins(16, 20, 16, 14)
        scol = vbox(spacing=2)
        scol.addWidget(label("Statutory calendar", "h2"))
        scol.addWidget(label("Double-click to edit or add your own", "muted", wrap=True))
        sh.addLayout(scol, 1)
        b_add_stat = button("Add date", "plus", small=True)
        b_add_stat.setToolTip("Add a manual statutory deadline (ITR, GST, TDS, etc.)")
        b_add_stat.clicked.connect(self.add_statutory)
        sh.addWidget(b_add_stat, 0, Qt.AlignVCenter)
        shw = QWidget()
        shw.setLayout(sh)
        sl.addWidget(shw)
        sl.addWidget(divider())
        self.stat = QTableWidget(0, 3)
        self.stat.setHorizontalHeaderLabels(["Date", "Obligation", "When"])
        self._style(self.stat)
        hh = self.stat.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Fixed)
        self.stat.setColumnWidth(0, 118)
        hh.setSectionResizeMode(1, QHeaderView.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.Fixed)
        self.stat.setColumnWidth(2, 104)
        self.stat.setWordWrap(True)
        self.stat.cellDoubleClicked.connect(lambda r, _c: self.edit_statutory(r))
        self.stat.setContextMenuPolicy(Qt.CustomContextMenu)
        self.stat.customContextMenuRequested.connect(self._stat_menu)
        sl.addWidget(self.stat, 1)
        self.stat_card.setMinimumWidth(300)
        row.addWidget(self.stat_card)
        row.setStretchFactor(0, 3)
        row.setStretchFactor(1, 2)
        row.setSizes([600, 420])

    @staticmethod
    def _style(t: QTableWidget) -> None:
        left_headers(t)
        t.verticalHeader().setVisible(False)
        t.verticalHeader().setDefaultSectionSize(52)
        t.setShowGrid(False)
        t.setSelectionBehavior(QAbstractItemView.SelectRows)
        t.setSelectionMode(QAbstractItemView.SingleSelection)
        t.setEditTriggers(QAbstractItemView.NoEditTriggers)
        t.setFocusPolicy(Qt.NoFocus)

    def refresh(self) -> None:
        rows = self.ctx.db.list_tasks(include_done=self.show_done.isChecked())
        self.tasks.setRowCount(len(rows))
        today = date.today()
        for r, t in enumerate(rows):
            done = bool(t["done"])
            overdue = False
            try:
                d_check = date.fromisoformat(t["due_date"])
                overdue = (not done) and (d_check - today).days < 0
            except ValueError:
                pass
            chk = QTableWidgetItem()
            chk.setData(Qt.UserRole, t["id"])
            ic_color = theme.SUCCESS if done else ("#DC2626" if overdue else "#D97706")
            chk.setIcon(icons.icon("check-circle" if done else "clock", ic_color, 22))
            self.tasks.setItem(r, 0, chk)
            title = QTableWidgetItem(t["title"])
            f = title.font()
            f.setStrikeOut(done)
            title.setFont(f)
            if done:
                title.setForeground(QColor(theme.MUTED))
            self.tasks.setItem(r, 1, title)
            self.tasks.setItem(r, 2, QTableWidgetItem(t["client_name"] or "-"))
            try:
                d = date.fromisoformat(t["due_date"])
                due = QTableWidgetItem(d.strftime("%d %b %Y"))
                if not done and (d - today).days < 0:
                    due.setForeground(QColor(theme.DANGER))
            except ValueError:
                due = QTableWidgetItem(t["due_date"])
            self.tasks.setItem(r, 3, due)
            p = QTableWidgetItem(t["priority"])
            if t["priority"] == "High":
                p.setForeground(QColor(theme.DANGER))
            self.tasks.setItem(r, 4, p)

            # Right-side tick-off / undo button
            act_wrap = QWidget()
            al = hbox(act_wrap, (4, 0, 8, 0), 0)
            if done:
                btn = button("Undo", "rotate-ccw", "undo", small=True)
                btn.setMinimumWidth(84)
                btn.setToolTip("Reopen this task")
            else:
                btn = button("Done", "check", "done", small=True)
                btn.setMinimumWidth(84)
                btn.setToolTip("Tick off task as completed")
            btn.clicked.connect(lambda _=False, tid=t["id"]: self._toggle_task(tid))
            al.addWidget(btn, 0, Qt.AlignVCenter | Qt.AlignRight)
            self.tasks.setCellWidget(r, 5, act_wrap)
        self.tasks.resizeRowsToContents()
        for r in range(self.tasks.rowCount()):
            self.tasks.setRowHeight(r, max(58, self.tasks.rowHeight(r) + 12))
        self.tasks.setVisible(bool(rows))
        self.tasks_empty.setVisible(not rows)

        overrides = self.ctx.db.statutory_overrides()
        custom = self.ctx.db.list_custom_statutory()
        stats = deadlines.upcoming(today, 240, overrides, custom)[:20]
        self._stat_items = stats
        self.stat.setRowCount(len(stats))
        for r, s in enumerate(stats):
            dt_text = s.due.strftime("%d %b %Y")
            tag = "\n(Manual)" if s.custom_id is not None else ("\n(Edited)" if s.edited else "")
            dt_item = QTableWidgetItem(dt_text + tag)
            if s.edited or s.custom_id is not None:
                dt_item.setForeground(QColor(theme.TEXT))
                f = dt_item.font()
                f.setWeight(f.Weight.DemiBold)
                dt_item.setFont(f)
            prefix = f"[{s.kind}] " if s.custom_id is not None else ""
            title_text = prefix + s.title + (f"\nNote: {s.note}" if s.note else "")
            title_item = QTableWidgetItem(title_text)
            if s.custom_id is not None:
                tip = f"Manual statutory deadline ({s.kind})"
                if s.note:
                    tip += f"\nNote: {s.note}"
                dt_item.setToolTip(tip)
                title_item.setToolTip(tip)
            elif s.edited:
                tip = f"Standard date: {s.default_due.strftime('%d %b %Y')}"
                if s.note:
                    tip += f"\nNote: {s.note}"
                dt_item.setToolTip(tip)
                title_item.setToolTip(tip)
            self.stat.setItem(r, 0, dt_item)
            self.stat.setItem(r, 1, title_item)
            txt, kind = when_chip(s.due, today)
            it = QTableWidgetItem(txt)
            it.setForeground(QColor({"danger": theme.DANGER, "warn": theme.WARN,
                                     "info": theme.TEXT}.get(kind, theme.TEXT_2)))
            f = it.font()
            f.setWeight(f.Weight.DemiBold)
            it.setFont(f)
            self.stat.setItem(r, 2, it)
        self.stat.resizeRowsToContents()
        for r in range(self.stat.rowCount()):
            self.stat.setRowHeight(r, max(54, self.stat.rowHeight(r) + 10))

    # ------------------------------------------------- statutory editing
    def add_statutory(self) -> None:
        d = EditStatutoryDialog(self.window(), None)
        if d.exec() == QDialog.Accepted:
            due_iso, title, kind, note = d.values()
            self.ctx.db.add_custom_statutory(title, due_iso, kind, note)
            self.ctx.db.log(f"Added manual statutory date: {title} ({due_iso})")
            self.refresh()
            self.data_changed.emit()
            self.toast.emit("Manual statutory date added", "success")

    def edit_statutory(self, row: int) -> None:
        if row < 0 or row >= len(self._stat_items):
            return
        item = self._stat_items[row]
        d = EditStatutoryDialog(self.window(), item)
        if d.exec() == QDialog.Accepted:
            if item.custom_id is not None:
                if d.delete_requested:
                    self.ctx.db.delete_custom_statutory(item.custom_id)
                    self.ctx.db.log(f"Deleted manual statutory date: {item.title}")
                    self.toast.emit("Manual statutory date deleted", "success")
                else:
                    due_iso, title, kind, note = d.values()
                    self.ctx.db.update_custom_statutory(item.custom_id, title, due_iso, kind, note)
                    self.ctx.db.log(f"Updated manual statutory date: {title} -> {due_iso}")
                    self.toast.emit("Manual statutory date updated", "success")
            else:
                if d.reset_requested:
                    self.ctx.db.clear_statutory_override(item.key)
                    self.ctx.db.log(f"Reset statutory date: {item.title}")
                    self.toast.emit("Statutory date reset to standard", "success")
                else:
                    due_iso, title, _kind, note = d.values()
                    self.ctx.db.set_statutory_override(item.key, due_iso, title, note)
                    self.ctx.db.log(f"Updated statutory date: {title} -> {due_iso}")
                    self.toast.emit("Statutory due date updated", "success")
            self.refresh()
            self.data_changed.emit()

    def _stat_menu(self, pos) -> None:
        idx = self.stat.indexAt(pos)
        if not idx.isValid():
            return
        self.stat.selectRow(idx.row())
        item = self._stat_items[idx.row()]
        m = QMenu(self)
        a_edit = m.addAction(
            icons.icon("edit", theme.TEXT_2, 16),
            "Edit manual date" if item.custom_id is not None else "Edit / extend due date",
        )
        a_del = a_reset = None
        if item.custom_id is not None:
            m.addSeparator()
            a_del = m.addAction(icons.icon("trash", theme.DANGER, 16), "Delete manual date")
        elif item.edited:
            a_reset = m.addAction(icons.icon("rotate-ccw", theme.TEXT_2, 16), "Reset to standard date")
        act = m.exec(self.stat.viewport().mapToGlobal(pos))
        if act == a_edit:
            self.edit_statutory(idx.row())
        elif a_del and act == a_del:
            if confirm(self.window(), "Delete manual statutory date?",
                       f"Remove '{item.title}' from the statutory calendar?", "Delete", danger=True):
                self.ctx.db.delete_custom_statutory(item.custom_id)
                self.ctx.db.log(f"Deleted manual statutory date: {item.title}")
                self.refresh()
                self.data_changed.emit()
                self.toast.emit("Manual statutory date deleted", "success")
        elif a_reset and act == a_reset:
            self.ctx.db.clear_statutory_override(item.key)
            self.ctx.db.log(f"Reset statutory date: {item.title}")
            self.refresh()
            self.data_changed.emit()
            self.toast.emit("Statutory date reset to standard", "success")

    # ------------------------------------------------------------ tasks
    def _tid(self, row: int) -> int:
        return self.tasks.item(row, 0).data(Qt.UserRole)

    def _toggle_task(self, tid: int) -> None:
        t = next((x for x in self.ctx.db.list_tasks() if x["id"] == tid), None)
        if not t:
            return
        new_done = not bool(t["done"])
        self.ctx.db.set_task_done(tid, new_done)
        self.ctx.db.log(f"Task {'completed' if new_done else 'reopened'}: {t['title']}")
        self.refresh()
        self.data_changed.emit()
        self.toast.emit(
            f"Completed: {t['title']}" if new_done else f"Reopened: {t['title']}",
            "success" if new_done else "info",
        )

    def _task_clicked(self, row: int, col: int) -> None:
        if col != 0:
            return
        self._toggle_task(self._tid(row))

    def add_task(self, client_id: int | None = None) -> None:
        d = TaskDialog(self.window(), self.ctx, None, client_id if isinstance(client_id, int) else None)
        if d.exec() == QDialog.Accepted:
            title, due, cid, prio = d.values()
            self.ctx.db.add_task(title, due, cid, prio)
            self.refresh()
            self.data_changed.emit()
            self.toast.emit("Task added", "success")

    def edit_task(self, row: int) -> None:
        tid = self._tid(row)
        t = next((x for x in self.ctx.db.list_tasks() if x["id"] == tid), None)
        if not t:
            return
        d = TaskDialog(self.window(), self.ctx, t)
        if d.exec() == QDialog.Accepted:
            title, due, cid, prio = d.values()
            self.ctx.db.update_task(tid, title, due, cid, prio)
            self.refresh()
            self.data_changed.emit()
            self.toast.emit("Task updated", "success")

    def _task_menu(self, pos) -> None:
        idx = self.tasks.indexAt(pos)
        if not idx.isValid():
            return
        self.tasks.selectRow(idx.row())
        m = QMenu(self)
        a_edit = m.addAction(icons.icon("edit", theme.TEXT_2, 16), "Edit")
        a_del = m.addAction(icons.icon("trash", theme.DANGER, 16), "Delete")
        act = m.exec(self.tasks.viewport().mapToGlobal(pos))
        if act == a_edit:
            self.edit_task(idx.row())
        elif act == a_del:
            if confirm(self.window(), "Delete task?", "This cannot be undone.", "Delete", danger=True):
                self.ctx.db.delete_task(self._tid(idx.row()))
                self.refresh()
                self.data_changed.emit()
