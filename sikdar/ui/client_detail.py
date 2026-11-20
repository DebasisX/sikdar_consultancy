"""Client profile page with folder & document management."""
from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QSize, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QGuiApplication
from PySide6.QtWidgets import (
    QAbstractItemView, QDialog, QFileDialog, QFrame, QHeaderView, QLabel, QListWidget,
    QListWidgetItem, QMenu, QScrollArea, QSplitter, QTableWidget, QTableWidgetItem, QWidget,
)

from .. import storage, validators
from ..context import AppContext
from . import icons, theme
from .clients import ClientDialog
from .widgets import (
    AvatarLabel, button, card, chip, confirm, divider, empty_state, hbox, label, left_headers,
    prompt_text, vbox,
)


def copy_text(text: str, secret: bool = False) -> None:
    cb = QGuiApplication.clipboard()
    cb.setText(text)
    if secret:
        def clear() -> None:
            if cb.text() == text:
                cb.clear()
        QTimer.singleShot(30_000, clear)


class DropTable(QTableWidget):
    files_dropped = Signal(list)

    def __init__(self, *a):
        super().__init__(*a)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dragMoveEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        paths = [u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()]
        if paths:
            self.files_dropped.emit(paths)
            e.acceptProposedAction()


class FolderRow(QWidget):
    def __init__(self, name: str, count: int):
        super().__init__()
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        lay = hbox(self, (4, 0, 4, 0), 10)
        ic = QLabel()
        ic.setPixmap(icons.pixmap("folder", "#D97706", 20))
        lay.addWidget(ic)
        lay.addWidget(label(name))
        lay.addStretch(1)
        self.count = label(str(count))
        self.count.setStyleSheet(f"color:{theme.TEXT_2}; background:#EEF1F6; border-radius:9px; "
                                 "padding:1px 8px; font-size:11.5px; font-weight:700;")
        lay.addWidget(self.count)

    def set_count(self, n: int) -> None:
        self.count.setText(str(n))


class ClientDetailPage(QWidget):
    back = Signal()
    data_changed = Signal()
    toast = Signal(str, str)
    go_fees = Signal(int)

    def __init__(self, ctx: AppContext):
        super().__init__()
        self.setObjectName("page")
        self.ctx = ctx
        self.cid: int | None = None
        self.client = None
        self.current_folder: str | None = None
        self._pw_shown = False
        self._aadhar_shown = False

        outer = vbox(self, (36, 30, 36, 28), 18)
        top = hbox(spacing=12)
        self.btn_back = button("Clients", "arrow-left", "ghost")
        self.btn_back.clicked.connect(self.back.emit)
        top.addWidget(self.btn_back)
        top.addStretch(1)
        self.btn_edit = button("Edit details", "edit")
        self.btn_edit.clicked.connect(self._edit)
        self.btn_delete = button("Delete client", "trash", "danger")
        self.btn_delete.clicked.connect(self._delete)
        top.addWidget(self.btn_edit)
        top.addWidget(self.btn_delete)
        outer.addLayout(top)

        body = QSplitter(Qt.Horizontal)
        body.setChildrenCollapsible(False)
        outer.addWidget(body, 1)

        # ---------------- left: profile
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setMinimumWidth(275)
        left_scroll.setMaximumWidth(520)
        left_scroll.setFrameShape(QFrame.NoFrame)
        left_host = QWidget()
        left_host.setObjectName("page")
        left_scroll.setWidget(left_host)
        ll = vbox(left_host, (0, 0, 8, 12), 16)

        self.profile = card()
        pl = vbox(self.profile, (24, 26, 24, 22), 0)
        self.avatar = AvatarLabel(96)
        pl.addWidget(self.avatar, 0, Qt.AlignHCenter)
        pl.addSpacing(12)
        self.name = label("", "h2")
        self.name.setAlignment(Qt.AlignCenter)
        self.name.setWordWrap(True)
        pl.addWidget(self.name)
        self.status = chip("Active", "success")
        pl.addSpacing(6)
        pl.addWidget(self.status, 0, Qt.AlignHCenter)
        pl.addSpacing(10)
        self.since = label("", "muted")
        self.since.setAlignment(Qt.AlignCenter)
        pl.addWidget(self.since)
        pl.addSpacing(16)
        pl.addWidget(divider())
        pl.addSpacing(10)
        self.info_host = vbox(spacing=0)
        pl.addLayout(self.info_host)
        ll.addWidget(self.profile)

        # portal credentials
        self.portal = card()
        cl = vbox(self.portal, (22, 20, 22, 20), 10)
        hd = hbox(spacing=8)
        ic = QLabel()
        ic.setPixmap(icons.pixmap("shield", theme.BRAND, 18))
        hd.addWidget(ic)
        hd.addWidget(label("Income Tax portal login", "h3"))
        hd.addStretch(1)
        cl.addLayout(hd)
        cl.addWidget(label("incometax.gov.in e-filing", "muted"))
        cl.addSpacing(4)
        cl.addWidget(label("User ID (PAN)", "fieldLabel"))
        r1 = hbox(spacing=8)
        self.portal_id = label("", "h3")
        self.portal_id.setTextInteractionFlags(Qt.TextSelectableByMouse)
        r1.addWidget(self.portal_id, 1)
        b = button("", "copy", "ghost", small=True)
        b.setToolTip("Copy PAN")
        b.clicked.connect(lambda: self._copy(self.client["pan"], "PAN copied"))
        r1.addWidget(b)
        cl.addLayout(r1)
        cl.addWidget(label("Password", "fieldLabel"))
        r2 = hbox(spacing=8)
        self.portal_pw = label("", "h3")
        self.portal_pw.setTextInteractionFlags(Qt.TextSelectableByMouse)
        r2.addWidget(self.portal_pw, 1)
        self.btn_reveal = button("", "eye", "ghost", small=True)
        self.btn_reveal.setToolTip("Show / hide password")
        self.btn_reveal.clicked.connect(self._toggle_pw)
        r2.addWidget(self.btn_reveal)
        b2 = button("", "copy", "ghost", small=True)
        b2.setToolTip("Copy password (clipboard clears after 30 s)")
        b2.clicked.connect(self._copy_pw)
        r2.addWidget(b2)
        cl.addLayout(r2)
        cl.addSpacing(4)
        b_portal = button("Open e-Filing Portal", "external-link", small=True)
        b_portal.clicked.connect(lambda: QDesktopServices.openUrl(
            QUrl("https://www.incometax.gov.in/iec/foportal/")))
        cl.addWidget(b_portal, 0, Qt.AlignLeft)
        ll.addWidget(self.portal)

        # quick stats
        self.quick = card()
        ql = vbox(self.quick, (22, 18, 22, 18), 10)
        ql.addWidget(label("At a glance", "h3"))
        self.q_fees = label("", "sub")
        self.q_tasks = label("", "sub")
        ql.addWidget(self.q_fees)
        ql.addWidget(self.q_tasks)
        bfees = button("View fees", "rupee", small=True)
        bfees.clicked.connect(lambda: self.go_fees.emit(self.cid or 0))
        ql.addWidget(bfees, 0, Qt.AlignLeft)
        ll.addWidget(self.quick)
        ll.addStretch(1)
        body.addWidget(left_scroll)

        # ---------------- right: documents
        docs = card()
        dl = vbox(docs)
        head = hbox(spacing=10)
        head_w = QWidget()
        head_w.setLayout(head)
        head.setContentsMargins(24, 20, 24, 16)
        col = vbox(spacing=2)
        col.addWidget(label("Documents", "h2"))
        self.docs_sub = label("", "sub")
        col.addWidget(self.docs_sub)
        head.addLayout(col)
        head.addStretch(1)
        self.btn_open_root = button("Open in Explorer", "folder-open", small=True)
        self.btn_open_root.clicked.connect(self._open_root)
        head.addWidget(self.btn_open_root)
        dl.addWidget(head_w)
        dl.addWidget(divider())

        split = QSplitter(Qt.Horizontal)
        split.setChildrenCollapsible(False)
        dl.addWidget(split, 1)

        # folder column
        fcol = QWidget()
        fcol.setMinimumWidth(185)
        fcol.setMaximumWidth(380)
        fl = vbox(fcol, (14, 14, 14, 14), 10)
        fl.addWidget(label("FOLDERS", "navSection"))
        fcol.findChild(QLabel).setStyleSheet(f"color:{theme.MUTED}; font-size:11px; font-weight:700; letter-spacing:1px;")
        self.folder_list = QListWidget()
        self.folder_list.setObjectName("folders")
        self.folder_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.folder_list.currentRowChanged.connect(self._folder_selected)
        self.folder_list.customContextMenuRequested.connect(self._folder_menu)
        fl.addWidget(self.folder_list, 1)
        row = hbox(spacing=6)
        self.btn_new_folder = button("New folder", "folder-plus", small=True)
        self.btn_new_folder.setToolTip("Create new folder")
        self.btn_new_folder.clicked.connect(self._new_folder)
        self.btn_ren_folder = button("", "edit", small=True)
        self.btn_ren_folder.setFixedWidth(34)
        self.btn_ren_folder.setToolTip("Rename selected folder")
        self.btn_ren_folder.clicked.connect(self._rename_folder)
        self.btn_del_folder = button("", "trash", "danger", small=True)
        self.btn_del_folder.setFixedWidth(34)
        self.btn_del_folder.setToolTip("Delete selected folder")
        self.btn_del_folder.clicked.connect(self._delete_folder)
        row.addWidget(self.btn_new_folder, 1)
        row.addWidget(self.btn_ren_folder)
        row.addWidget(self.btn_del_folder)
        fl.addLayout(row)
        split.addWidget(fcol)

        # files column
        fc = QWidget()
        fcl = vbox(fc, (20, 14, 20, 14), 12)
        bar = hbox(spacing=10)
        self.folder_title = label("", "h3")
        self.folder_count = label("", "muted")
        bar.addWidget(self.folder_title)
        bar.addWidget(self.folder_count)
        bar.addStretch(1)
        self.btn_upload = button("Upload files", "upload", "primary", small=True)
        self.btn_upload.clicked.connect(self._upload)
        bar.addWidget(self.btn_upload)
        fcl.addLayout(bar)

        self.files = DropTable(0, 4)
        self.files.setHorizontalHeaderLabels(["Name", "Size", "Modified", ""])
        self.files.verticalHeader().setVisible(False)
        self.files.verticalHeader().setDefaultSectionSize(46)
        self.files.setShowGrid(False)
        self.files.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.files.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.files.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.files.setFocusPolicy(Qt.NoFocus)
        self.files.setIconSize(QSize(20, 20))
        self.files.setContextMenuPolicy(Qt.CustomContextMenu)
        hh = self.files.horizontalHeader()
        left_headers(self.files)
        hh.setSectionResizeMode(0, QHeaderView.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.Fixed)
        hh.setSectionResizeMode(2, QHeaderView.Fixed)
        hh.setSectionResizeMode(3, QHeaderView.Fixed)
        self.files.setColumnWidth(1, 80)
        self.files.setColumnWidth(2, 112)
        self.files.setColumnWidth(3, 4)
        self.files.cellDoubleClicked.connect(lambda r, _c: self._open_file(r))
        self.files.customContextMenuRequested.connect(self._file_menu)
        self.files.files_dropped.connect(self._add_dropped)
        fcl.addWidget(self.files, 1)
        self.drop_hint = empty_state("upload", "This folder is empty",
                                     "Drag & drop files here, or click Upload files.")
        fcl.addWidget(self.drop_hint, 1)
        split.addWidget(fc)
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)
        split.setSizes([230, 560])
        body.addWidget(docs)
        body.setStretchFactor(0, 0)
        body.setStretchFactor(1, 1)
        body.setSizes([355, 760])

    # ------------------------------------------------------------ loading
    def load(self, cid: int, folder: str | None = None) -> None:
        self.cid = cid
        self._pw_shown = False
        self._aadhar_shown = False
        self.reload_client()
        self.reload_folders(select=folder)

    def reload_client(self) -> None:
        c = self.ctx.db.get_client(self.cid) if self.cid else None
        if c is None:
            return
        self.client = c
        self.avatar.set_client(self.ctx.photo_path(c["photo"]), c["name"])
        self.name.setText(c["name"])
        self.status.setText(c["status"])
        self.status.setProperty("chip", "success" if c["status"] == "Active" else "neutral")
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)
        try:
            self.since.setText("Client since " + datetime.fromisoformat(c["created_at"]).strftime("%d %b %Y"))
        except ValueError:
            self.since.setText("")
        self._fill_info()
        self.portal_id.setText(c["pan"] or "-")
        self._paint_pw()
        billed = recv = 0.0
        for f in self.ctx.db.list_fees(c["id"]):
            billed += f["billed"]
            recv += f["received"]
        bal = billed - recv
        self.q_fees.setText(f"Outstanding fees:  {validators.inr(bal)}" if billed else "No fees recorded yet")
        pending = [t for t in self.ctx.db.list_tasks(False, c["id"])]
        self.q_tasks.setText(f"Pending tasks:  {len(pending)}")

    def _fill_info(self) -> None:
        while self.info_host.count():
            it = self.info_host.takeAt(0)
            w = it.widget()
            if w:
                w.hide()
                w.setParent(None)
                w.deleteLater()
        c = self.client
        dob = ""
        if c["dob"]:
            try:
                dob = datetime.fromisoformat(c["dob"]).strftime("%d %b %Y")
            except ValueError:
                dob = c["dob"]
        aad = validators.format_aadhar(c["aadhar"]) if self._aadhar_shown else validators.mask_aadhar(c["aadhar"])
        rows = [
            ("phone", "Phone", validators.format_phone(c["phone"]), c["phone"], "#059669", "#E6F7F0"),
            ("mail", "Email", c["email"], c["email"], "#2563EB", "#EAF1FF"),
            ("id-card", "PAN", c["pan"], c["pan"], "#7C3AED", "#F3E8FF"),
            ("shield", "Aadhaar", aad, c["aadhar"], "#D97706", "#FEF3C7"),
            ("calendar", "Date of birth", dob, "", "#0D9488", "#CCFBF1"),
            ("map-pin", "Address", c["address"], "", "#DC2626", "#FEE2E2"),
        ]
        for ic, key, val, copy_val, fg_c, bg_c in rows:
            w = QWidget()
            lay = hbox(w, (0, 8, 0, 8), 12)
            badge = QLabel()
            badge.setFixedSize(32, 32)
            badge.setAlignment(Qt.AlignCenter)
            badge.setStyleSheet(f"background:{bg_c}; border-radius:10px;")
            badge.setPixmap(icons.pixmap(ic, fg_c, 16))
            lay.addWidget(badge, 0, Qt.AlignTop)
            col = vbox(spacing=1)
            col.addWidget(label(key, "muted"))
            v = label(val or "-", wrap=True)
            v.setTextInteractionFlags(Qt.TextSelectableByMouse)
            col.addWidget(v)
            lay.addLayout(col, 1)
            if key == "Aadhaar" and c["aadhar"]:
                eb = button("", "eye-off" if self._aadhar_shown else "eye", "ghost", small=True)
                eb.setToolTip("Show / hide Aadhaar")
                eb.clicked.connect(self._toggle_aadhar)
                lay.addWidget(eb, 0, Qt.AlignTop)
            if copy_val:
                cb = button("", "copy", "ghost", small=True)
                cb.setToolTip(f"Copy {key.lower()}")
                cb.clicked.connect(lambda _=False, t=copy_val, k=key: self._copy(t, f"{k} copied"))
                lay.addWidget(cb, 0, Qt.AlignTop)
            self.info_host.addWidget(w)

    def _toggle_aadhar(self) -> None:
        self._aadhar_shown = not self._aadhar_shown
        self._fill_info()

    def _paint_pw(self) -> None:
        pw = self.ctx.portal_password(self.client)
        if not pw:
            self.portal_pw.setText("Not saved")
            self.portal_pw.setStyleSheet(f"color:{theme.MUTED}; font-weight:500;")
            self.btn_reveal.setEnabled(False)
            return
        self.btn_reveal.setEnabled(True)
        self.portal_pw.setStyleSheet("")
        self.portal_pw.setText(pw if self._pw_shown else "•" * min(len(pw), 14))
        self.btn_reveal.setIcon(icons.icon("eye-off" if self._pw_shown else "eye", theme.TEXT_2, 18))

    def _toggle_pw(self) -> None:
        self._pw_shown = not self._pw_shown
        self._paint_pw()

    def _copy(self, text: str, msg: str) -> None:
        copy_text(text)
        self.toast.emit(msg, "success")

    def _copy_pw(self) -> None:
        pw = self.ctx.portal_password(self.client)
        if not pw:
            self.toast.emit("No portal password saved for this client", "error")
            return
        copy_text(pw, secret=True)
        self.toast.emit("Password copied - clipboard clears in 30 s", "success")

    # ---------------------------------------------------------- client actions
    def _edit(self) -> None:
        d = ClientDialog(self.window(), self.ctx, self.client)
        if d.exec() == QDialog.Accepted and d.result_data:
            try:
                self.ctx.update_client(self.cid, d.result_data, d.photo_src, d.remove_photo)
            except (OSError, storage.StorageError, ValueError) as e:
                self.toast.emit(f"Could not update client: {e}", "error")
                return
            self.reload_client()
            self.reload_folders(select=self.current_folder)
            self.data_changed.emit()
            self.toast.emit("Client details updated", "success")

    def _delete(self) -> None:
        if confirm(self.window(), f"Delete {self.client['name']}?",
                   "This removes the client, their fees and tasks, and moves all their document "
                   "folders to the Recycle Bin.", "Delete client", danger=True):
            self.ctx.delete_client(self.cid)
            self.data_changed.emit()
            self.toast.emit("Client deleted", "success")
            self.back.emit()

    # --------------------------------------------------------------- folders
    def reload_folders(self, select: str | None = None) -> None:
        fn = self.client["folder_name"]
        storage.ensure_client(fn, [])  # make sure the root exists
        folders = storage.list_folders(fn)
        self.folder_list.blockSignals(True)
        self.folder_list.clear()
        target = 0
        for i, (name, count) in enumerate(folders):
            it = QListWidgetItem()
            it.setData(Qt.UserRole, name)
            it.setSizeHint(QSize(0, 44))
            self.folder_list.addItem(it)
            self.folder_list.setItemWidget(it, FolderRow(name, count))
            if select and name == select:
                target = i
        self.folder_list.blockSignals(False)
        total = sum(c for _, c in folders)
        self.docs_sub.setText(f"{len(folders)} folder{'s' if len(folders) != 1 else ''}  ·  "
                              f"{total} file{'s' if total != 1 else ''}")
        has = bool(folders)
        for b in (self.btn_ren_folder, self.btn_del_folder):
            b.setEnabled(has)
        if has:
            self.folder_list.setCurrentRow(target)
            self._folder_selected(target)
        else:
            self.current_folder = None
            self._folder_selected(-1)

    def _folder_selected(self, row: int) -> None:
        it = self.folder_list.item(row) if row >= 0 else None
        self.current_folder = it.data(Qt.UserRole) if it else None
        self.reload_files()

    def _new_folder(self) -> None:
        name = prompt_text(self.window(), "New folder", "Folder name", ok_text="Create folder",
                           placeholder="e.g. GST, Notices, FY 2024-25")
        if name is None:
            return
        try:
            created = storage.add_folder(self.client["folder_name"], name)
        except (storage.StorageError, OSError) as e:
            self.toast.emit(str(e), "error")
            return
        self.ctx.db.log(f"Added folder '{created}' for {self.client['name']}")
        self.reload_folders(select=created)
        self.toast.emit(f"Folder '{created}' created", "success")

    def _rename_folder(self) -> None:
        old = self.current_folder
        if not old:
            return
        new = prompt_text(self.window(), "Rename folder", "New name", old, "Rename")
        if new is None or new == old:
            return
        try:
            new = storage.rename_folder(self.client["folder_name"], old, new)
        except (storage.StorageError, OSError) as e:
            self.toast.emit(str(e), "error")
            return
        self.ctx.db.log(f"Renamed folder '{old}' to '{new}' for {self.client['name']}")
        self.reload_folders(select=new)
        self.toast.emit(f"Renamed to '{new}'", "success")

    def _delete_folder(self) -> None:
        name = self.current_folder
        if not name:
            return
        n = len(storage.list_files(self.client["folder_name"], name))
        extra = (f" It contains {n} file{'s' if n != 1 else ''}, which will be moved to the Recycle Bin."
                 if n else " The folder is empty.")
        if not confirm(self.window(), f"Delete folder '{name}'?", extra.strip(),
                       "Delete folder", danger=True):
            return
        try:
            storage.delete_folder(self.client["folder_name"], name)
        except OSError as e:
            self.toast.emit(f"Could not delete: {e}", "error")
            return
        self.ctx.db.log(f"Deleted folder '{name}' for {self.client['name']}")
        self.reload_folders()
        self.data_changed.emit()
        self.toast.emit(f"Folder '{name}' deleted", "success")

    def _folder_menu(self, pos) -> None:
        it = self.folder_list.itemAt(pos)
        m = QMenu(self)
        a_new = m.addAction(icons.icon("folder-plus", theme.TEXT_2, 16), "New folder")
        a_ren = a_del = a_open = None
        if it:
            self.folder_list.setCurrentItem(it)
            m.addSeparator()
            a_open = m.addAction(icons.icon("folder-open", theme.TEXT_2, 16), "Open in Explorer")
            a_ren = m.addAction(icons.icon("edit", theme.TEXT_2, 16), "Rename")
            a_del = m.addAction(icons.icon("trash", theme.DANGER, 16), "Delete")
        act = m.exec(self.folder_list.viewport().mapToGlobal(pos))
        if act is None:
            return
        if act == a_new:
            self._new_folder()
        elif act == a_ren:
            self._rename_folder()
        elif act == a_del:
            self._delete_folder()
        elif act == a_open:
            storage.reveal(storage.client_root(self.client["folder_name"]) / self.current_folder)

    def _open_root(self) -> None:
        storage.reveal(storage.client_root(self.client["folder_name"]))

    # ----------------------------------------------------------------- files
    def reload_files(self) -> None:
        self.files.setRowCount(0)
        if not self.current_folder:
            self.folder_title.setText("No folders")
            self.folder_count.setText("")
            self.files.hide()
            self.btn_upload.setEnabled(False)
            self.drop_hint.show()
            return
        self.btn_upload.setEnabled(True)
        items = storage.list_files(self.client["folder_name"], self.current_folder)
        self.folder_title.setText(self.current_folder)
        self.folder_count.setText(f"{len(items)} file{'s' if len(items) != 1 else ''}")
        self.files.setRowCount(len(items))
        for r, f in enumerate(items):
            it = QTableWidgetItem(f.name)
            it.setData(Qt.UserRole, str(f.path))
            it.setIcon(icons.icon("file-text", theme.BRAND if f.name.lower().endswith(".pdf") else theme.MUTED, 20))
            self.files.setItem(r, 0, it)
            self.files.setItem(r, 1, QTableWidgetItem(storage.human_size(f.size)))
            self.files.setItem(r, 2, QTableWidgetItem(f.modified.strftime("%d %b %Y")))
            self.files.setItem(r, 3, QTableWidgetItem(""))
        self.files.setVisible(bool(items))
        self.drop_hint.setVisible(not items)
        # refresh count badge for this folder
        self._refresh_folder_badges()

    def _refresh_folder_badges(self) -> None:
        counts = dict(storage.list_folders(self.client["folder_name"]))
        for i in range(self.folder_list.count()):
            it = self.folder_list.item(i)
            row = self.folder_list.itemWidget(it)
            if isinstance(row, FolderRow):
                row.set_count(counts.get(it.data(Qt.UserRole), 0))
        total = sum(counts.values())
        self.docs_sub.setText(f"{len(counts)} folder{'s' if len(counts) != 1 else ''}  ·  "
                              f"{total} file{'s' if total != 1 else ''}")

    def _selected_files(self) -> list[str]:
        rows = sorted({i.row() for i in self.files.selectedIndexes()})
        return [self.files.item(r, 0).data(Qt.UserRole) for r in rows]

    def _upload(self) -> None:
        if not self.current_folder:
            return
        paths, _ = QFileDialog.getOpenFileNames(self, f"Upload to {self.current_folder}")
        if paths:
            self._add_dropped(paths)

    def _add_dropped(self, paths: list) -> None:
        if not self.current_folder:
            self.toast.emit("Create a folder first", "error")
            return
        try:
            n = storage.add_files(self.client["folder_name"], self.current_folder, paths)
        except OSError as e:
            self.toast.emit(f"Upload failed: {e}", "error")
            return
        if n:
            self.ctx.db.log(f"Added {n} file(s) to {self.client['name']} / {self.current_folder}")
            self.toast.emit(f"{n} file{'s' if n != 1 else ''} added to {self.current_folder}", "success")
        else:
            self.toast.emit("Folders can't be dropped here - add files only", "error")
        self.reload_files()
        self.data_changed.emit()

    def _open_file(self, row: int) -> None:
        from pathlib import Path
        try:
            storage.open_path(Path(self.files.item(row, 0).data(Qt.UserRole)))
        except OSError as e:
            self.toast.emit(f"Could not open file: {e}", "error")

    def _file_menu(self, pos) -> None:
        idx = self.files.indexAt(pos)
        if not idx.isValid():
            return
        if not self.files.item(idx.row(), 0).isSelected():
            self.files.selectRow(idx.row())
        sel = self._selected_files()
        m = QMenu(self)
        a_open = m.addAction(icons.icon("file", theme.TEXT_2, 16), "Open")
        a_show = m.addAction(icons.icon("folder-open", theme.TEXT_2, 16), "Show in Explorer")
        a_ren = m.addAction(icons.icon("edit", theme.TEXT_2, 16), "Rename")
        a_ren.setEnabled(len(sel) == 1)
        m.addSeparator()
        a_del = m.addAction(icons.icon("trash", theme.DANGER, 16),
                            f"Delete {len(sel)} files" if len(sel) > 1 else "Delete")
        act = m.exec(self.files.viewport().mapToGlobal(pos))
        from pathlib import Path
        if act == a_open:
            self._open_file(idx.row())
        elif act == a_show:
            storage.reveal(Path(sel[0]))
        elif act == a_ren:
            self._rename_file(Path(sel[0]))
        elif act == a_del:
            self._delete_files(sel)

    def _rename_file(self, path) -> None:
        new = prompt_text(self.window(), "Rename file", "File name", path.name, "Rename")
        if new is None or new == path.name:
            return
        try:
            storage.rename_file(self.client["folder_name"], self.current_folder, path.name, new)
        except (storage.StorageError, OSError) as e:
            self.toast.emit(str(e), "error")
            return
        self.reload_files()
        self.toast.emit("File renamed", "success")

    def _delete_files(self, sel: list[str]) -> None:
        from pathlib import Path
        what = Path(sel[0]).name if len(sel) == 1 else f"{len(sel)} files"
        if not confirm(self.window(), f"Delete {what}?", "The file(s) will be moved to the Recycle Bin.",
                       "Delete", danger=True):
            return
        for s in sel:
            storage.delete_file(Path(s))
        self.ctx.db.log(f"Deleted {len(sel)} file(s) from {self.client['name']} / {self.current_folder}")
        self.reload_files()
        self.data_changed.emit()
        self.toast.emit("Deleted", "success")
