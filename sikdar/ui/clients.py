"""Client registration dialog and the Clients list page."""
from __future__ import annotations

from PySide6.QtCore import QDate, QSize, Qt, Signal
from PySide6.QtGui import QAction, QColor
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QDateEdit, QDialog, QFileDialog, QFrame, QGridLayout,
    QHeaderView, QLabel, QLineEdit, QMenu, QScrollArea, QTableWidget, QTableWidgetItem,
    QTextEdit, QVBoxLayout, QWidget,
)

from .. import storage, validators
from ..context import AppContext
from . import icons, theme
from .widgets import (
    AvatarLabel, BaseDialog, Field, PageHeader, PasswordEdit, button, card, chip, clean_date_edit,
    confirm, empty_state, hbox, label, left_headers, search_box, vbox,
)


class ClientDialog(BaseDialog):
    """Register a new client or edit an existing one."""

    def __init__(self, parent, ctx: AppContext, client=None):
        super().__init__(parent, "Edit client" if client else "Register new client", 760)
        self.ctx = ctx
        self.client = client
        self.photo_src: str | None = None
        self.remove_photo = False
        self.result_data: dict | None = None
        self.setMinimumHeight(640)
        self.resize(820, 720)

        outer = vbox(self)
        # header
        head = QWidget()
        hl = vbox(head, (28, 22, 28, 18), 3)
        hl.addWidget(label("Edit client" if client else "Register new client", "h1"))
        hl.addWidget(label("Personal details, identity numbers and Income Tax portal login.", "sub"))
        outer.addWidget(head)
        outer.addWidget(self._divider())

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.viewport().setAutoFillBackground(False)
        body = QWidget()
        body.setObjectName("page")
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)
        bl = hbox(body, (28, 22, 28, 22), 28)

        # ---- photo column
        pc = vbox(spacing=10)
        self.avatar = AvatarLabel(132)
        pc.addWidget(self.avatar, 0, Qt.AlignHCenter)
        self.btn_photo = button("Upload photo", "camera", small=True)
        self.btn_photo.clicked.connect(self._pick_photo)
        self.btn_rm_photo = button("Remove", kind="ghost", small=True)
        self.btn_rm_photo.clicked.connect(self._clear_photo)
        pc.addWidget(self.btn_photo)
        pc.addWidget(self.btn_rm_photo)
        pc.addWidget(label("JPG or PNG.\nAuto-cropped to a square.", "muted"), 0, Qt.AlignHCenter)
        pc.addStretch(1)
        bl.addLayout(pc)

        # ---- form column
        form = vbox(spacing=18)
        bl.addLayout(form, 1)

        form.addWidget(label("Personal details", "h3"))
        g = QGridLayout()
        g.setHorizontalSpacing(16)
        g.setVerticalSpacing(14)
        self.name = QLineEdit()
        self.name.setPlaceholderText("As per PAN card")
        self.dob = clean_date_edit()
        self.dob.setMinimumDate(QDate(1900, 1, 1))
        self.dob.setMaximumDate(QDate.currentDate())
        self.dob.setSpecialValueText("Not set")
        self.dob.setDate(self.dob.minimumDate())
        self.phone = QLineEdit()
        self.phone.setPlaceholderText("10-digit mobile number")
        self.phone.setMaxLength(17)
        self.email = QLineEdit()
        self.email.setPlaceholderText("name@example.com")
        self.address = QTextEdit()
        self.address.setFixedHeight(70)
        self.address.setAcceptRichText(False)
        self.address.setPlaceholderText("Residential address")
        self.f_name = Field("Full name", self.name, True)
        self.f_dob = Field("Date of birth", self.dob)
        self.f_phone = Field("Phone number", self.phone, True)
        self.f_email = Field("Email ID", self.email)
        self.f_addr = Field("Address", self.address)
        g.addWidget(self.f_name, 0, 0, 1, 2)
        g.addWidget(self.f_phone, 1, 0)
        g.addWidget(self.f_email, 1, 1)
        g.addWidget(self.f_dob, 2, 0)
        g.addWidget(self.f_addr, 3, 0, 1, 2)
        form.addLayout(g)

        form.addWidget(self._divider())
        form.addWidget(label("Identity numbers", "h3"))
        g2 = QGridLayout()
        g2.setHorizontalSpacing(16)
        self.pan = QLineEdit()
        self.pan.setPlaceholderText("ABCDE1234F")
        self.pan.setMaxLength(10)
        self.aadhar = QLineEdit()
        self.aadhar.setPlaceholderText("XXXX XXXX XXXX")
        self.aadhar.setMaxLength(14)
        self.f_pan = Field("PAN", self.pan)
        self.f_aadhar = Field("Aadhaar number", self.aadhar)
        g2.addWidget(self.f_pan, 0, 0)
        g2.addWidget(self.f_aadhar, 0, 1)
        form.addLayout(g2)

        form.addWidget(self._divider())
        form.addWidget(label("Portal logins (optional — ITR, GST, or both)", "h3"))
        gp = QGridLayout()
        gp.setHorizontalSpacing(16)
        gp.setVerticalSpacing(12)
        self.itr_id_preview = QLineEdit()
        self.itr_id_preview.setReadOnly(True)
        self.itr_id_preview.setPlaceholderText("Auto-filled from PAN above")
        self.portal_pw = PasswordEdit("ITR portal password (optional)")
        self.gst_id = QLineEdit()
        self.gst_id.setPlaceholderText("GST username / GSTIN (optional)")
        self.gst_pw = PasswordEdit("GST portal password (optional)")

        self.f_itr_id = Field("Income Tax (ITR) User ID", self.itr_id_preview)
        self.f_portal = Field("Income Tax (ITR) password", self.portal_pw)
        self.f_gst_id = Field("GST (GSTR) User ID", self.gst_id)
        self.f_gst_pw = Field("GST (GSTR) password", self.gst_pw)

        gp.addWidget(self.f_itr_id, 0, 0, Qt.AlignTop)
        gp.addWidget(self.f_gst_id, 0, 1, Qt.AlignTop)
        gp.addWidget(self.f_portal, 1, 0, Qt.AlignTop)
        gp.addWidget(self.f_gst_pw, 1, 1, Qt.AlignTop)
        gp.setColumnStretch(0, 1)
        gp.setColumnStretch(1, 1)
        form.addLayout(gp)
        form.addWidget(label(
            "ITR User ID automatically uses the client's PAN. Both passwords are stored encrypted on this PC.",
            "muted", wrap=True,
        ))

        form.addWidget(self._divider())
        g3 = QGridLayout()
        g3.setHorizontalSpacing(16)
        self.status = QComboBox()
        self.status.addItems(["Active", "Inactive"])
        self.notes = QTextEdit()
        self.notes.setFixedHeight(70)
        self.notes.setAcceptRichText(False)
        self.notes.setPlaceholderText("Internal notes (not shared)")
        g3.addWidget(Field("Status", self.status), 0, 0)
        g3.addWidget(Field("Notes", self.notes), 0, 1)
        g3.setColumnStretch(1, 2)
        g3.setColumnStretch(0, 1)
        form.addLayout(g3)
        form.addStretch(1)

        # ---- footer
        outer.addWidget(self._divider())
        foot = QWidget()
        fl = hbox(foot, (28, 14, 28, 16), 10)
        self.err = label("", "error")
        fl.addWidget(self.err, 1)
        c = button("Cancel")
        c.clicked.connect(self.reject)
        self.ok = button("Save changes" if client else "Register client", "check", "primary")
        self.ok.clicked.connect(self._save)
        fl.addWidget(c)
        fl.addWidget(self.ok)
        outer.addWidget(foot)

        self.pan.textEdited.connect(lambda t: self._set_upper(self.pan, t))
        self.pan.textChanged.connect(lambda t: self.itr_id_preview.setText(t.strip().upper()))
        self.aadhar.textEdited.connect(self._fmt_aadhar)

        if client:
            self._load(client)
        else:
            self.avatar.set_client(None, "New Client")
        self.name.textChanged.connect(self._refresh_avatar)

    @staticmethod
    def _divider() -> QFrame:
        d = QFrame()
        d.setObjectName("divider")
        return d

    # -- helpers
    def _set_upper(self, edit: QLineEdit, text: str) -> None:
        edit.setText(text.upper().replace(" ", ""))

    def _fmt_aadhar(self, text: str) -> None:
        self.aadhar.setText(validators.format_aadhar(text))

    def _refresh_avatar(self) -> None:
        if self.photo_src:
            return
        existing = None
        if self.client and not self.remove_photo:
            existing = self.ctx.photo_path(self.client["photo"])
        self.avatar.set_client(existing, self.name.text() or "New Client")

    def _pick_photo(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose client photo", "", "Images (*.png *.jpg *.jpeg *.bmp *.webp)")
        if path:
            from PySide6.QtGui import QPixmap
            if QPixmap(path).isNull():
                self.err.setText("That file could not be read as an image.")
                return
            self.photo_src = path
            self.remove_photo = False
            self.avatar.set_client(path, self.name.text())  # type: ignore[arg-type]
            self.err.setText("")

    def _clear_photo(self) -> None:
        self.photo_src = None
        self.remove_photo = True
        self.avatar.set_client(None, self.name.text() or "New Client")

    def _load(self, c) -> None:
        self.name.setText(c["name"])
        self.phone.setText(validators.format_phone(c["phone"]))
        self.email.setText(c["email"])
        self.pan.setText(c["pan"])
        self.aadhar.setText(validators.format_aadhar(c["aadhar"]))
        self.address.setPlainText(c["address"])
        self.notes.setPlainText(c["notes"])
        self.status.setCurrentText(c["status"])
        if c["dob"]:
            d = QDate.fromString(c["dob"], Qt.ISODate)
            if d.isValid():
                self.dob.setDate(d)
        self.portal_pw.setText(self.ctx.portal_password(c))
        self.gst_id.setText(c["gst_id"] if "gst_id" in c.keys() else "")
        self.gst_pw.setText(self.ctx.gst_password(c))
        self.avatar.set_client(self.ctx.photo_path(c["photo"]), c["name"])

    # -- save
    def _save(self) -> None:
        name = " ".join(self.name.text().split())
        phone = validators.normalize_phone(self.phone.text())
        email = self.email.text().strip()
        pan = validators.normalize_pan(self.pan.text())
        aadhar = validators.normalize_aadhar(self.aadhar.text())
        errors = 0

        def check(field: Field, bad: bool, msg: str) -> None:
            nonlocal errors
            field.set_error(msg if bad else "")
            errors += bad

        check(self.f_name, not name, "Full name is required")
        check(self.f_phone, not phone or not validators.valid_phone(phone),
              "Enter a valid 10-digit mobile number")
        check(self.f_email, bool(email) and not validators.valid_email(email), "Enter a valid email address")
        pan_bad = bool(pan) and not validators.valid_pan(pan)
        pan_msg = "Format: 5 letters, 4 digits, 1 letter"
        if pan and not pan_bad and self.ctx.db.pan_exists(pan, self.client["id"] if self.client else None):
            pan_bad, pan_msg = True, "A client with this PAN already exists"
        check(self.f_pan, pan_bad, pan_msg)
        check(self.f_aadhar, bool(aadhar) and not validators.valid_aadhar(aadhar),
              "Aadhaar must be 12 digits")
        if errors:
            self.err.setText("Please fix the highlighted fields.")
            return
        self.err.setText("")
        dob = ""
        if self.dob.date() != self.dob.minimumDate():
            dob = self.dob.date().toString(Qt.ISODate)
        self.result_data = {
            "name": name, "phone": phone, "email": email, "pan": pan, "aadhar": aadhar,
            "dob": dob, "address": self.address.toPlainText().strip(),
            "portal_password": self.portal_pw.text(),
            "gst_id": self.gst_id.text().strip(),
            "gst_password": self.gst_pw.text(),
            "status": self.status.currentText(),
            "notes": self.notes.toPlainText().strip(),
        }
        self.accept()


class ClientsPage(QWidget):
    open_client = Signal(int)
    data_changed = Signal()
    toast = Signal(str, str)

    COLS = ["Client", "PAN", "Phone", "Email", "Aadhaar", "Status", "Documents", ""]

    def __init__(self, ctx: AppContext):
        super().__init__()
        self.setObjectName("page")
        self.ctx = ctx
        lay = vbox(self, (36, 30, 36, 28), 20)
        self.header = PageHeader("Clients", "Register and manage everyone you file for.")
        self.btn_export = button("Export CSV", "download")
        self.btn_export.clicked.connect(self._export)
        self.btn_add = button("Register client", "user-plus", "primary")
        self.btn_add.clicked.connect(self.add_client)
        self.header.add_action(self.btn_export)
        self.header.add_action(self.btn_add)
        lay.addWidget(self.header)

        bar = hbox(spacing=12)
        self.search = search_box("Search by name, PAN, phone, email or Aadhaar")
        self.search.setMinimumWidth(380)
        self.search.textChanged.connect(self.refresh)
        self.filter = QComboBox()
        self.filter.addItems(["All", "Active", "Inactive"])
        self.filter.setFixedWidth(130)
        self.filter.currentTextChanged.connect(self.refresh)
        self.count = label("", "sub")
        bar.addWidget(self.search)
        bar.addWidget(self.filter)
        bar.addStretch(1)
        bar.addWidget(self.count)
        lay.addLayout(bar)

        self.panel = card()
        pl = vbox(self.panel, (10, 6, 10, 10))
        self.table = QTableWidget(0, len(self.COLS))
        self.table.setHorizontalHeaderLabels(self.COLS)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(60)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.setIconSize(QSize(38, 38))
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        hh = self.table.horizontalHeader()
        left_headers(self.table)
        hh.setStretchLastSection(False)
        hh.setSectionResizeMode(0, QHeaderView.Stretch)
        for i, w in ((1, 118), (2, 138), (3, 172), (4, 138), (5, 96), (6, 106), (7, 52)):
            hh.setSectionResizeMode(i, QHeaderView.Fixed)
            self.table.setColumnWidth(i, w)
        self.table.cellClicked.connect(lambda r, c: self._open_row(r) if c == 7 else None)
        self.table.cellDoubleClicked.connect(lambda r, _c: self._open_row(r))
        self.table.customContextMenuRequested.connect(self._menu)
        pl.addWidget(self.table, 1)
        self.empty = empty_state("users", "No clients yet",
                                 "Register your first client to start organising their documents.")
        pl.addWidget(self.empty, 1)
        lay.addWidget(self.panel, 1)
        lay.addWidget(label("Tip: double-click a client to open their profile and documents.", "muted"))

    # -- data
    def refresh(self) -> None:
        rows = self.ctx.db.list_clients(self.search.text(), self.filter.currentText())
        total = self.ctx.db.count_clients()
        self.table.setRowCount(len(rows))
        for r, c in enumerate(rows):
            folders = storage.list_folders(c["folder_name"])
            docs = sum(n for _, n in folders)
            name = QTableWidgetItem(c["name"])
            name.setData(Qt.UserRole, c["id"])
            name.setIcon(self._avatar_icon(c))
            f = name.font()
            f.setWeight(f.Weight.DemiBold)
            name.setFont(f)
            self.table.setItem(r, 0, name)
            self.table.setItem(r, 1, QTableWidgetItem(c["pan"] or "-"))
            self.table.setItem(r, 2, QTableWidgetItem(validators.format_phone(c["phone"]) or "-"))
            self.table.setItem(r, 3, QTableWidgetItem(c["email"] or "-"))
            self.table.setItem(r, 4, QTableWidgetItem(validators.mask_aadhar(c["aadhar"]) or "-"))
            # Soft rounded Active/Inactive pill matching Dashboard
            st_wrap = QWidget()
            st_wrap.setAttribute(Qt.WA_TransparentForMouseEvents)
            sl = hbox(st_wrap, (8, 0, 8, 0), 0)
            sl.addWidget(chip(c["status"], "success" if c["status"] == "Active" else "neutral"), 0, Qt.AlignVCenter)
            sl.addStretch(1)
            self.table.setCellWidget(r, 5, st_wrap)
            self.table.setItem(r, 6, QTableWidgetItem(f"{docs} file{'s' if docs != 1 else ''}"))
            # Arrow inset from the right edge so it isn't flush against the border
            arr_wrap = QWidget()
            arr_wrap.setAttribute(Qt.WA_TransparentForMouseEvents)
            al = hbox(arr_wrap, (0, 0, 16, 0), 0)
            arr_ic = QLabel()
            arr_ic.setPixmap(icons.pixmap("chevron-right", theme.MUTED, 16))
            al.addWidget(arr_ic, 0, Qt.AlignCenter)
            self.table.setCellWidget(r, 7, arr_wrap)
        has = bool(rows)
        self.table.setVisible(has)
        self.empty.setVisible(not has)
        self.count.setText(f"{len(rows)} of {total} client{'s' if total != 1 else ''}")

    def _avatar_icon(self, c):
        from PySide6.QtGui import QIcon
        from .widgets import avatar_pixmap
        return QIcon(avatar_pixmap(self.ctx.photo_path(c["photo"]), c["name"], 38))

    def _selected_id(self) -> int | None:
        r = self.table.currentRow()
        if r < 0:
            return None
        return self.table.item(r, 0).data(Qt.UserRole)

    def _open_row(self, row: int) -> None:
        self.open_client.emit(self.table.item(row, 0).data(Qt.UserRole))

    def _menu(self, pos) -> None:
        idx = self.table.indexAt(pos)
        if not idx.isValid():
            return
        self.table.selectRow(idx.row())
        cid = self.table.item(idx.row(), 0).data(Qt.UserRole)
        m = QMenu(self)
        a_open = m.addAction(icons.icon("folder-open", theme.TEXT_2, 16), "Open profile && documents")
        a_edit = m.addAction(icons.icon("edit", theme.TEXT_2, 16), "Edit details")
        m.addSeparator()
        a_del = m.addAction(icons.icon("trash", theme.DANGER, 16), "Delete client")
        act = m.exec(self.table.viewport().mapToGlobal(pos))
        if act == a_open:
            self.open_client.emit(cid)
        elif act == a_edit:
            self.edit_client(cid)
        elif act == a_del:
            self.delete_client(cid)

    # -- actions
    def add_client(self) -> None:
        d = ClientDialog(self.window(), self.ctx)
        if d.exec() == QDialog.Accepted and d.result_data:
            try:
                cid = self.ctx.add_client(d.result_data, d.photo_src)
            except (OSError, ValueError) as e:
                self.toast.emit(f"Could not register client: {e}", "error")
                return
            self.refresh()
            self.data_changed.emit()
            self.toast.emit(f"{d.result_data['name']} registered with default folders", "success")
            self.open_client.emit(cid)

    def edit_client(self, cid: int) -> None:
        c = self.ctx.db.get_client(cid)
        if not c:
            return
        d = ClientDialog(self.window(), self.ctx, c)
        if d.exec() == QDialog.Accepted and d.result_data:
            try:
                self.ctx.update_client(cid, d.result_data, d.photo_src, d.remove_photo)
            except (OSError, storage.StorageError, ValueError) as e:
                self.toast.emit(f"Could not update client: {e}", "error")
                return
            self.refresh()
            self.data_changed.emit()
            self.toast.emit("Client details updated", "success")

    def delete_client(self, cid: int) -> bool:
        c = self.ctx.db.get_client(cid)
        if not c:
            return False
        if not confirm(self.window(), f"Delete {c['name']}?",
                       "This removes the client, their fees and tasks, and moves their document "
                       "folders to the Recycle Bin.", "Delete client", danger=True):
            return False
        self.ctx.delete_client(cid)
        self.refresh()
        self.data_changed.emit()
        self.toast.emit("Client deleted", "success")
        return True

    def _export(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export clients", "clients.csv", "CSV (*.csv)")
        if not path:
            return
        inc = confirm(self.window(), "Include portal passwords?",
                      "The CSV will be a plain-text file. Include Income Tax portal passwords only "
                      "if you will store the file securely.", "Include passwords",
                      danger=True, icon_name="lock")
        try:
            n = self.ctx.export_clients_csv(path, inc)
        except OSError as e:
            self.toast.emit(f"Export failed: {e}", "error")
            return
        self.toast.emit(f"Exported {n} clients", "success")
