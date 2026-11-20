"""Settings page: firm profile, security, default folders, backup."""
from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication, QComboBox, QDialog, QFileDialog, QFrame, QLabel, QLineEdit, QListWidget,
    QScrollArea, QWidget,
)

from .. import paths, security, storage
from ..context import AppContext, AuthError
from . import icons, theme
from .brand import BrandMark
from .widgets import (
    BaseDialog, Field, PageHeader, PasswordEdit, button, card, confirm, divider, hbox, label,
    prompt_text, vbox,
)

AUTOLOCK = [("Never", 0), ("After 5 minutes", 5), ("After 10 minutes", 10),
            ("After 15 minutes", 15), ("After 30 minutes", 30), ("After 1 hour", 60)]


class PasswordConfirmDialog(BaseDialog):
    """Requires the owner's current password before executing a destructive reset."""

    def __init__(self, parent, title: str, message: str, confirm_text: str):
        super().__init__(parent, title, 470)
        lay = vbox(self, (26, 24, 26, 22), 14)
        top = hbox(spacing=14)
        badge = QLabel()
        badge.setFixedSize(46, 46)
        badge.setAlignment(Qt.AlignCenter)
        badge.setStyleSheet(f"background:{theme.DANGER_SOFT}; border-radius:14px;")
        badge.setPixmap(icons.pixmap("alert", theme.DANGER, 22))
        top.addWidget(badge, 0, Qt.AlignTop)
        col = vbox(spacing=4)
        col.addWidget(label(title, "h2"))
        col.addWidget(label(message, "sub", wrap=True))
        top.addLayout(col, 1)
        lay.addLayout(top)

        self.pw = PasswordEdit("Enter owner password to confirm")
        self.f_pw = Field("Owner password", self.pw, True)
        lay.addWidget(self.f_pw)

        row = hbox(spacing=10)
        row.addStretch(1)
        c = button("Cancel")
        c.clicked.connect(self.reject)
        ok = button(confirm_text, "trash", "solidDanger")
        ok.setDefault(True)
        ok.clicked.connect(self._ok)
        row.addWidget(c)
        row.addWidget(ok)
        lay.addLayout(row)

    def _ok(self) -> None:
        if not self.pw.text():
            self.f_pw.set_error("Enter your current owner password")
            return
        self.accept()

    def password(self) -> str:
        return self.pw.text()


class SettingsPage(QWidget):
    firm_changed = Signal()
    autolock_changed = Signal()
    restored = Signal()
    data_cleared = Signal()
    admin_cleared = Signal()
    toast = Signal(str, str)

    def __init__(self, ctx: AppContext):
        super().__init__()
        self.setObjectName("page")
        self.ctx = ctx
        self._cards: list[QWidget] = []
        outer = vbox(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        host = QWidget()
        host.setObjectName("page")
        scroll.setWidget(host)
        outer.addWidget(scroll)
        lay = vbox(host, (36, 30, 36, 30), 20)
        lay.addWidget(PageHeader("Settings", "Firm profile, security, folder templates and backups."))

        grid = hbox(spacing=20)
        lay.addLayout(grid)
        col1, col2 = vbox(spacing=20), vbox(spacing=20)
        grid.addLayout(col1, 1)
        grid.addLayout(col2, 1)

        # ---- firm
        c = self._section("Firm profile & signature", "Shown on your dashboard and PDF bills/receipts.")
        self.firm = QLineEdit()
        c.addWidget(Field("Firm name", self.firm))
        b = button("Save firm name", kind="primary", small=True)
        b.clicked.connect(self._save_firm)
        c.addWidget(b, 0, Qt.AlignLeft)
        c.addWidget(divider())
        c.addWidget(label("Authorised signature (for PDF Bills & Receipts)", "fieldLabel"))
        self.sig_preview = QLabel("No signature uploaded")
        self.sig_preview.setAlignment(Qt.AlignCenter)
        self.sig_preview.setFixedHeight(84)
        self.sig_preview.setStyleSheet(
            "background:#F5F6F9; border:1px dashed #C9CED8; border-radius:12px; color:#7D8491;"
        )
        c.addWidget(self.sig_preview)
        srow = hbox(spacing=8)
        b_sig = button("Upload signature", "upload", small=True)
        b_sig.clicked.connect(self._upload_signature)
        self.btn_rm_sig = button("Remove", "trash", "danger", small=True)
        self.btn_rm_sig.clicked.connect(self._remove_signature)
        srow.addWidget(b_sig)
        srow.addWidget(self.btn_rm_sig)
        srow.addStretch(1)
        c.addLayout(srow)
        c.addWidget(label("Tip: use a PNG with transparent or white background for the cleanest PDF look.", "muted", wrap=True))
        col1.addWidget(c.parentWidget())

        # ---- security
        c = self._section("Owner login & security", "Change your ID or password. Portal passwords stay readable.")
        self.new_id = QLineEdit()
        self.cur_pw = PasswordEdit("Current password")
        self.new_pw = PasswordEdit("Leave blank to keep current")
        self.new_pw2 = PasswordEdit("Repeat new password")
        self.f_id = Field("Owner ID", self.new_id)
        self.f_cur = Field("Current password", self.cur_pw, True)
        self.f_new = Field("New password", self.new_pw)
        self.f_new2 = Field("Confirm new password", self.new_pw2)
        for f in (self.f_id, self.f_cur, self.f_new, self.f_new2):
            c.addWidget(f)
        b = button("Update credentials", kind="primary", small=True)
        b.clicked.connect(self._save_security)
        c.addWidget(b, 0, Qt.AlignLeft)
        c.addWidget(divider())
        self.autolock = QComboBox()
        for t, v in AUTOLOCK:
            self.autolock.addItem(t, v)
        self.autolock.currentIndexChanged.connect(self._save_autolock)
        c.addWidget(Field("Auto-lock when idle", self.autolock,
                          hint="Signs you out automatically if the app is left unattended."))
        c.addWidget(divider())
        c.addWidget(label("Password recovery code & hint", "h3"))
        self.rec_status = label("", "sub", wrap=True)
        c.addWidget(self.rec_status)
        self.rec_code = PasswordEdit("Min 4 characters (e.g. secret PIN / phrase)")
        self.rec_hint = QLineEdit()
        self.rec_hint.setPlaceholderText("Hint shown on Forgot Password screen")
        self.rec_cur_pw = PasswordEdit("Current owner password to save")
        self.f_rec_code = Field("Recovery code", self.rec_code)
        self.f_rec_hint = Field("Hint (visible when resetting password)", self.rec_hint)
        self.f_rec_pw = Field("Current owner password", self.rec_cur_pw, True)
        c.addWidget(self.f_rec_code)
        c.addWidget(self.f_rec_hint)
        c.addWidget(self.f_rec_pw)
        rrow = hbox(spacing=8)
        b_rec = button("Save recovery code", "shield", "primary", small=True)
        b_rec.clicked.connect(self._save_recovery)
        self.btn_rm_rec = button("Remove", "trash", "danger", small=True)
        self.btn_rm_rec.clicked.connect(self._remove_recovery)
        rrow.addWidget(b_rec)
        rrow.addWidget(self.btn_rm_rec)
        rrow.addStretch(1)
        c.addLayout(rrow)
        col1.addWidget(c.parentWidget())
        col1.addStretch(1)

        # ---- default folders
        c = self._section("Default client folders",
                          "Created automatically for every newly registered client. "
                          "Existing clients are not changed.")
        self.folders = QListWidget()
        self.folders.setObjectName("folders")
        self.folders.setFixedHeight(150)
        self.folders.setStyleSheet(f"QListWidget {{ border:1px solid {theme.BORDER}; border-radius:10px; padding:4px; }}")
        c.addWidget(self.folders)
        row = hbox(spacing=8)
        for text, icon, fn, kind in (("Add", "folder-plus", self._f_add, "secondary"),
                                     ("Rename", "edit", self._f_rename, "secondary"),
                                     ("Remove", "trash", self._f_remove, "danger")):
            bt = button(text, icon, kind, small=True)
            bt.clicked.connect(fn)
            row.addWidget(bt)
        row.addStretch(1)
        c.addLayout(row)
        col2.addWidget(c.parentWidget())

        # ---- data
        c = self._section("Data & backup",
                          "Full .zip backup includes all clients, portal credentials, fees, "
                          "payment transactions, tasks, documents, photos, signature & PDFs.")
        self.loc = label("", "sub", wrap=True)
        self.loc.setTextInteractionFlags(Qt.TextSelectableByMouse)
        c.addWidget(self.loc)
        self.last = label("", "muted")
        c.addWidget(self.last)
        row = hbox(spacing=8)
        b1 = button("Back up all data (.zip)", "download", "primary", small=True)
        b1.clicked.connect(self._backup)
        b2 = button("Restore from .zip", "upload", small=True)
        b2.clicked.connect(self._restore)
        b3 = button("Open data folder", "folder-open", small=True)
        b3.clicked.connect(lambda: storage.reveal(paths.home_dir()))
        for b in (b1, b2, b3):
            row.addWidget(b)
        row.addStretch(1)
        c.addLayout(row)
        c.addWidget(divider())
        c.addWidget(label("Clear data", "h3"))
        c.addWidget(label(
            "Both options ask for your owner password and send removed files to the Recycle Bin.",
            "muted", wrap=True))
        drow = hbox(spacing=8)
        b_cu = button("Clear all client data", "trash", "danger", small=True)
        b_cu.setToolTip("Removes all clients, folders, documents, fees, transactions & tasks. Keeps admin login.")
        b_cu.clicked.connect(self._clear_user_data)
        b_ca = button("Clear all data (incl. admin)", "alert", "solidDanger", small=True)
        b_ca.setToolTip("Factory reset: removes all client data AND resets owner login & settings.")
        b_ca.clicked.connect(self._clear_all_data)
        drow.addWidget(b_cu)
        drow.addWidget(b_ca)
        drow.addStretch(1)
        c.addLayout(drow)
        col2.addWidget(c.parentWidget())

        # ---- about
        c = self._section("About", "")
        ab = hbox(spacing=14)
        ab.addWidget(BrandMark(56, radius_ratio=0.18))
        acol = vbox(spacing=2)
        acol.addWidget(label(f"The Sikdar Tax Consultancy  ·  v{paths.APP_VERSION}", "h3"))
        acol.addWidget(label("Estd 2000 · Built for Indian income-tax practice. Keep regular backups — "
                             "your client records exist only on this PC.", "muted", wrap=True))
        ab.addLayout(acol, 1)
        c.addLayout(ab)
        col2.addWidget(c.parentWidget())
        col2.addStretch(1)

    def _section(self, title: str, sub: str):
        f = card()
        self._cards.append(f)
        l = vbox(f, (24, 22, 24, 22), 14)
        l.addWidget(label(title, "h2"))
        if sub:
            l.addWidget(label(sub, "sub", wrap=True))
        return l

    # ------------------------------------------------------------ refresh
    def refresh(self) -> None:
        self.firm.setText(self.ctx.firm_name())
        self.new_id.setText(self.ctx.owner_id())
        self.cur_pw.clear()
        self.new_pw.clear()
        self.new_pw2.clear()
        i = self.autolock.findData(self.ctx.autolock_minutes())
        self.autolock.blockSignals(True)
        self.autolock.setCurrentIndex(max(i, 0))
        self.autolock.blockSignals(False)
        self._load_folders()
        self._load_signature()
        self._load_recovery()
        self.loc.setText(f"Location:  {paths.home_dir()}")
        lb = self.ctx.db.get_meta("last_backup")
        self.last.setText(f"Last backup: {lb}" if lb else "No backup made yet - create one now.")

    def _save_firm(self) -> None:
        name = self.firm.text().strip()
        if not name:
            self.toast.emit("Firm name cannot be empty", "error")
            return
        self.ctx.db.set_meta("firm_name", name)
        self.firm_changed.emit()
        self.toast.emit("Firm name saved", "success")

    def _load_signature(self) -> None:
        sp = self.ctx.signature_path()
        if sp:
            pm = QPixmap(str(sp))
            if not pm.isNull():
                self.sig_preview.setText("")
                self.sig_preview.setPixmap(pm.scaled(260, 72, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                self.btn_rm_sig.setEnabled(True)
                return
        self.sig_preview.setPixmap(QPixmap())
        self.sig_preview.setText("No signature uploaded")
        self.btn_rm_sig.setEnabled(False)

    def _upload_signature(self) -> None:
        src, _ = QFileDialog.getOpenFileName(
            self, "Upload signature image", "", "Images (*.png *.jpg *.jpeg *.webp *.bmp)")
        if not src:
            return
        try:
            self.ctx.save_signature(src)
        except (ValueError, OSError) as e:
            self.toast.emit(str(e), "error")
            return
        self._load_signature()
        self.ctx.db.log("Updated authorised signature image")
        self.toast.emit("Signature uploaded — will appear on all new PDF bills & receipts", "success")

    def _remove_signature(self) -> None:
        self.ctx.remove_signature()
        self._load_signature()
        self.ctx.db.log("Removed authorised signature image")
        self.toast.emit("Signature removed", "success")

    def _save_security(self) -> None:
        oid = self.new_id.text().strip()
        pw, pw2 = self.new_pw.text(), self.new_pw2.text()
        ok = True
        bad_id = len(oid) < 3 or " " in oid
        self.f_id.set_error("At least 3 characters, no spaces" if bad_id else "")
        ok &= not bad_id
        self.f_cur.set_error("" if self.cur_pw.text() else "Enter your current password")
        ok &= bool(self.cur_pw.text())
        short = bool(pw) and len(pw) < 8
        self.f_new.set_error("Use at least 8 characters" if short else "")
        ok &= not short
        mis = pw != pw2
        self.f_new2.set_error("Passwords do not match" if mis else "")
        ok &= not mis
        if not ok:
            return
        try:
            self.ctx.change_credentials(self.cur_pw.text(), oid, pw or None)
        except AuthError as e:
            self.f_cur.set_error(str(e))
            return
        self.cur_pw.clear()
        self.new_pw.clear()
        self.new_pw2.clear()
        self.toast.emit("Credentials updated", "success")

    def _save_autolock(self) -> None:
        self.ctx.db.set_meta("autolock_minutes", str(self.autolock.currentData()))
        self.autolock_changed.emit()
        self.toast.emit("Auto-lock updated", "success")

    def _load_recovery(self) -> None:
        has = self.ctx.has_recovery_code()
        hint = self.ctx.recovery_hint()
        if has:
            self.rec_status.setText(f"Active  ·  Hint: \"{hint}\"" if hint else "Active  ·  No hint set")
            self.rec_hint.setText(hint)
        else:
            self.rec_status.setText("Not set yet — add a recovery code so you can reset your password if forgotten.")
            self.rec_hint.clear()
        self.rec_code.clear()
        self.rec_cur_pw.clear()
        self.btn_rm_rec.setEnabled(has)

    def _save_recovery(self) -> None:
        code = self.rec_code.text().strip()
        hint = self.rec_hint.text().strip()
        pw = self.rec_cur_pw.text()
        ok = True
        self.f_rec_code.set_error("Use at least 4 characters" if len(code) < 4 else "")
        ok &= len(code) >= 4
        self.f_rec_pw.set_error("" if pw else "Enter your current owner password")
        ok &= bool(pw)
        if not ok:
            return
        try:
            self.ctx.set_recovery_code(pw, code, hint)
        except AuthError as e:
            self.f_rec_pw.set_error(str(e))
            return
        self._load_recovery()
        self.toast.emit("Recovery code & hint saved", "success")

    def _remove_recovery(self) -> None:
        pw = self.rec_cur_pw.text()
        if not pw:
            self.f_rec_pw.set_error("Enter your current owner password to remove")
            return
        self.f_rec_pw.set_error("")
        try:
            self.ctx.remove_recovery_code(pw)
        except AuthError as e:
            self.f_rec_pw.set_error(str(e))
            return
        self._load_recovery()
        self.toast.emit("Recovery code removed", "success")

    # ------------------------------------------------------------ folders
    def _load_folders(self) -> None:
        self.folders.clear()
        for f in self.ctx.default_folders():
            self.folders.addItem(f)
        if self.folders.count():
            self.folders.setCurrentRow(0)

    def _store_folders(self) -> None:
        self.ctx.set_default_folders([self.folders.item(i).text() for i in range(self.folders.count())])

    def _f_add(self) -> None:
        name = prompt_text(self.window(), "Add default folder", "Folder name", ok_text="Add")
        if name is None:
            return
        try:
            name = storage.clean_name(name, "Folder name")
        except storage.StorageError as e:
            self.toast.emit(str(e), "error")
            return
        if name.lower() in [self.folders.item(i).text().lower() for i in range(self.folders.count())]:
            self.toast.emit("That folder is already in the list", "error")
            return
        self.folders.addItem(name)
        self._store_folders()

    def _f_rename(self) -> None:
        it = self.folders.currentItem()
        if not it:
            return
        name = prompt_text(self.window(), "Rename default folder", "New name", it.text(), "Rename")
        if name is None:
            return
        try:
            name = storage.clean_name(name, "Folder name")
        except storage.StorageError as e:
            self.toast.emit(str(e), "error")
            return
        it.setText(name)
        self._store_folders()

    def _f_remove(self) -> None:
        r = self.folders.currentRow()
        if r >= 0:
            self.folders.takeItem(r)
            self._store_folders()

    # -------------------------------------------------------------- backup
    def _backup(self) -> None:
        default = str(paths.backups_dir() / f"SikdarBackup-{datetime.now():%Y%m%d-%H%M}.zip")
        dest, _ = QFileDialog.getSaveFileName(self, "Save full backup", default, "Backup (*.zip)")
        if not dest:
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            counts = self.ctx.backup(dest)
        except OSError as e:
            QApplication.restoreOverrideCursor()
            self.toast.emit(f"Backup failed: {e}", "error")
            return
        QApplication.restoreOverrideCursor()
        self.refresh()
        self.toast.emit(
            f"Backup saved ({counts['clients']} clients, {counts['payments']} transactions, {counts['files']} files)",
            "success",
        )

    def _restore(self) -> None:
        src, _ = QFileDialog.getOpenFileName(self, "Choose backup", str(paths.backups_dir()), "Backup (*.zip)")
        if not src:
            return
        if not confirm(self.window(), "Restore this backup?",
                       "Current data (clients, transactions, documents & settings) will be replaced "
                       "by the backup (a copy of current data is kept beside it). You'll be returned "
                       "to the login screen to sign in with the backup's owner credentials.",
                       "Restore backup", danger=True, icon_name="upload"):
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            self.ctx.restore(src)
        except Exception as e:  # noqa: BLE001
            QApplication.restoreOverrideCursor()
            self.toast.emit(f"Restore failed: {e}", "error")
            return
        QApplication.restoreOverrideCursor()
        self.restored.emit()

    # ---------------------------------------------------------- clear data
    def _clear_user_data(self) -> None:
        d = PasswordConfirmDialog(
            self.window(),
            "Clear all client & user data?",
            "This permanently clears all clients, portal passwords, client folders/documents, "
            "fees, payment transactions, generated PDFs, tasks, and statutory date overrides.\n\n"
            "Your owner login, firm name, signature, and default folder template will be kept.",
            "Clear client data",
        )
        if d.exec() != QDialog.Accepted:
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            self.ctx.clear_user_data(d.password())
        except AuthError as e:
            QApplication.restoreOverrideCursor()
            self.toast.emit(str(e), "error")
            return
        except OSError as e:
            QApplication.restoreOverrideCursor()
            self.toast.emit(f"Could not clear data: {e}", "error")
            return
        QApplication.restoreOverrideCursor()
        self.refresh()
        self.data_cleared.emit()
        self.toast.emit("All client & transaction data cleared", "success")

    def _clear_all_data(self) -> None:
        d = PasswordConfirmDialog(
            self.window(),
            "Factory reset — clear ALL data including admin?",
            "This wipes EVERYTHING: all clients, documents, fees, payment transactions, PDFs, "
            "signature, settings, AND your owner ID & password.\n\n"
            "You will be taken back to the first-time setup screen. Make a backup first if needed!",
            "Reset everything",
        )
        if d.exec() != QDialog.Accepted:
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            self.ctx.clear_all_data(d.password())
        except AuthError as e:
            QApplication.restoreOverrideCursor()
            self.toast.emit(str(e), "error")
            return
        except OSError as e:
            QApplication.restoreOverrideCursor()
            self.toast.emit(f"Could not reset app: {e}", "error")
            return
        QApplication.restoreOverrideCursor()
        self.admin_cleared.emit()
