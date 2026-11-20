"""Owner login / first-run setup screen."""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QStackedWidget, QVBoxLayout, QWidget,
)

from .. import security
from ..context import AppContext, AuthError
from . import icons, theme
from .brand import BrandMark
from .widgets import BaseDialog, Field, PasswordEdit, button, card, hbox, label, repolish, vbox


class ForgotPasswordDialog(BaseDialog):
    """Reset the owner password using the configured recovery code & hint."""

    def __init__(self, parent, ctx: AppContext):
        super().__init__(parent, "Reset owner password", 480)
        self.ctx = ctx
        lay = vbox(self, (26, 24, 26, 22), 14)
        top = hbox(spacing=14)
        badge = QLabel()
        badge.setFixedSize(46, 46)
        badge.setAlignment(Qt.AlignCenter)
        badge.setStyleSheet("background:#EAF1FF; border-radius:14px;")
        badge.setPixmap(icons.pixmap("shield", "#2563EB", 22))
        top.addWidget(badge, 0, Qt.AlignTop)
        col = vbox(spacing=3)
        col.addWidget(label("Forgot password?", "h2"))
        col.addWidget(label(
            f"Reset password for owner ID '{ctx.owner_id()}' using your recovery code. "
            "All client portal passwords stay safe.", "sub", wrap=True))
        top.addLayout(col, 1)
        lay.addLayout(top)

        hint_text = ctx.recovery_hint()
        hint_box = QFrame()
        hint_box.setObjectName("hintBox")
        hint_box.setStyleSheet("QFrame#hintBox { background:#F3F5F8; border:1px solid #DFE3EA; border-radius:12px; }")
        hl = vbox(hint_box, (14, 10, 14, 10), 2)
        hl.addWidget(label("RECOVERY CODE HINT", "muted"))
        hl.addWidget(label(hint_text if hint_text else "No hint was saved for your recovery code.", "h3", wrap=True))
        lay.addWidget(hint_box)

        self.code = PasswordEdit("Enter your recovery code")
        self.pw = PasswordEdit("At least 8 characters")
        self.pw2 = PasswordEdit("Re-enter new password")
        self.f_code = Field("Recovery code", self.code, True)
        self.f_pw = Field("New password", self.pw, True)
        self.f_pw2 = Field("Confirm new password", self.pw2, True)
        lay.addWidget(self.f_code)
        lay.addWidget(self.f_pw)
        self.strength = label("", "muted")
        lay.addWidget(self.strength)
        lay.addWidget(self.f_pw2)
        self.pw.textChanged.connect(self._strength)

        row = hbox(spacing=10)
        row.addStretch(1)
        c = button("Cancel")
        c.clicked.connect(self.reject)
        ok = button("Reset password", "check", "primary")
        ok.setDefault(True)
        ok.clicked.connect(self._submit)
        row.addWidget(c)
        row.addWidget(ok)
        lay.addSpacing(4)
        lay.addLayout(row)

    def _strength(self, text: str) -> None:
        score, lbl = security.password_strength(text)
        colors = [theme.DANGER, theme.DANGER, theme.WARN, theme.SUCCESS, theme.SUCCESS]
        self.strength.setText(f"Password strength: {lbl}" if text else "")
        self.strength.setStyleSheet(f"color:{colors[score]}; font-size:12px; font-weight:600;")

    def _submit(self) -> None:
        code = self.code.text().strip()
        pw, pw2 = self.pw.text(), self.pw2.text()
        ok = True
        self.f_code.set_error("" if code else "Enter your recovery code")
        ok &= bool(code)
        self.f_pw.set_error("Use at least 8 characters" if len(pw) < 8 else "")
        ok &= len(pw) >= 8
        self.f_pw2.set_error("Passwords do not match" if pw != pw2 else "")
        ok &= (pw == pw2)
        if not ok:
            return
        try:
            self.ctx.reset_password_with_recovery(code, pw)
        except AuthError as e:
            self.f_code.set_error(str(e))
            return
        self.accept()


class BrandPanel(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("brandPanel")
        lay = vbox(self, (56, 48, 56, 48), 0)
        row = hbox(spacing=14)
        row.addWidget(BrandMark(46, radius_ratio=0.22))
        col = vbox(spacing=1)
        n = label("Sikdar Consultancy", "brandName")
        n.setStyleSheet("font-size:17px;")
        col.addWidget(n)
        col.addWidget(label("TAX CONSULTANCY  ·  ESTD 2000", "brandTag"))
        row.addLayout(col)
        row.addStretch(1)
        lay.addLayout(row)
        lay.addStretch(2)
        logo_card = BrandMark(156, radius_ratio=0.16)
        lay.addWidget(logo_card)
        lay.addSpacing(24)
        lay.addWidget(label("Your clients.\nYour returns.\nOne secure place.", "heroTitle"))
        lay.addSpacing(12)
        sub = label("A private workspace to manage client records, income-tax portal "
                    "credentials and every return, computation and document.", "heroSub", wrap=True)
        sub.setMaximumWidth(460)
        lay.addWidget(sub)
        lay.addSpacing(24)
        for ic, text in (("shield", "Portal passwords stored encrypted on this PC"),
                         ("folder", "Returns, Computation & Other folders for every client"),
                         ("calendar", "Editable statutory due dates & quick portal links"),
                         ("rupee", "Fee billing and outstanding tracker")):
            r = hbox(spacing=12)
            badge = QLabel()
            badge.setFixedSize(30, 30)
            badge.setAlignment(Qt.AlignCenter)
            badge.setStyleSheet("background:#1F2228; border:1px solid #2E323B; border-radius:9px;")
            badge.setPixmap(icons.pixmap(ic, "#D1D5DB", 15))
            r.addWidget(badge)
            r.addWidget(label(text, "heroBullet"))
            r.addStretch(1)
            lay.addLayout(r)
            lay.addSpacing(10)
        lay.addStretch(3)
        lay.addWidget(label("© The Sikdar Tax Consultancy  ·  Data stays on this computer", "brandTag"))


class LoginPage(QWidget):
    authenticated = Signal()

    def __init__(self, ctx: AppContext):
        super().__init__()
        self.ctx = ctx
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(BrandPanel(), 11)

        right = QFrame()
        right.setObjectName("loginPanel")
        rl = vbox(right)
        rl.setAlignment(Qt.AlignCenter)
        self.stack = QStackedWidget()
        self.stack.setFixedWidth(420)
        self.stack.addWidget(self._build_login())
        self.stack.addWidget(self._build_setup())
        rl.addWidget(self.stack, 0, Qt.AlignCenter)
        root.addWidget(right, 9)

        self._timer = QTimer(self, interval=500)
        self._timer.timeout.connect(self._tick_lock)

    # -- login form
    def _build_login(self) -> QWidget:
        w = QWidget()
        lay = vbox(w, spacing=0)
        lay.addWidget(label("Welcome back", "h1"))
        lay.addSpacing(4)
        lay.addWidget(label("Sign in to the owner dashboard", "sub"))
        lay.addSpacing(26)
        self.l_id = QLineEdit()
        self.l_id.setPlaceholderText("Owner ID")
        self.l_id.addAction(icons.icon("user", theme.MUTED, 18), QLineEdit.LeadingPosition)
        self.l_pw = PasswordEdit("Password")
        self.l_pw.addAction(icons.icon("lock", theme.MUTED, 18), QLineEdit.LeadingPosition)
        self.f_id = Field("Owner ID", self.l_id)
        self.f_pw = Field("Password", self.l_pw)
        lay.addWidget(self.f_id)
        lay.addSpacing(14)
        lay.addWidget(self.f_pw)
        forgot_row = hbox()
        forgot_row.addStretch(1)
        self.btn_forgot = button("Forgot password?", kind="link", small=True)
        self.btn_forgot.clicked.connect(self._forgot)
        forgot_row.addWidget(self.btn_forgot)
        lay.addLayout(forgot_row)
        lay.addSpacing(4)
        self.l_err = label("", "error", wrap=True)
        self.l_err.hide()
        lay.addWidget(self.l_err)
        lay.addSpacing(12)
        self.btn_login = button("Sign in", kind="primary")
        self.btn_login.setMinimumHeight(44)
        self.btn_login.setDefault(True)
        self.btn_login.clicked.connect(self._do_login)
        lay.addWidget(self.btn_login)
        self.l_id.returnPressed.connect(self.l_pw.setFocus)
        self.l_pw.returnPressed.connect(self._do_login)
        lay.addSpacing(22)
        lay.addWidget(label("Protected: after 5 wrong attempts sign-in locks for 30 seconds.", "muted", wrap=True))
        return w

    # -- first-run setup
    def _build_setup(self) -> QWidget:
        w = QWidget()
        lay = vbox(w, spacing=0)
        lay.addWidget(label("Set up your office", "h1"))
        lay.addSpacing(4)
        lay.addWidget(label("Create the owner account. You'll use this ID and password to sign in.", "sub", wrap=True))
        lay.addSpacing(18)
        self.s_firm = QLineEdit("Sikdar Consultancy")
        self.s_id = QLineEdit()
        self.s_id.setPlaceholderText("e.g. owner")
        self.s_pw = PasswordEdit("At least 8 characters")
        self.s_pw2 = PasswordEdit("Re-enter password")
        self.s_rec = PasswordEdit("Optional (e.g. secret PIN)")
        self.s_hint = QLineEdit()
        self.s_hint.setPlaceholderText("e.g. Birth city / office PIN")
        self.sf_firm = Field("Firm name", self.s_firm)
        self.sf_id = Field("Owner ID", self.s_id)
        self.sf_pw = Field("Password", self.s_pw)
        self.sf_pw2 = Field("Confirm password", self.s_pw2)
        self.sf_rec = Field("Recovery code", self.s_rec)
        self.sf_hint = Field("Recovery hint", self.s_hint)
        for f in (self.sf_firm, self.sf_id, self.sf_pw):
            lay.addWidget(f)
            lay.addSpacing(10)
        self.strength = label("", "muted")
        lay.addWidget(self.strength)
        lay.addSpacing(6)
        lay.addWidget(self.sf_pw2)
        lay.addSpacing(10)
        rec_row = hbox(spacing=10)
        rec_row.addWidget(self.sf_rec, 1)
        rec_row.addWidget(self.sf_hint, 1)
        lay.addLayout(rec_row)
        lay.addWidget(label("Optional: lets you reset your password if forgotten (also editable in Settings).", "muted", wrap=True))
        lay.addSpacing(16)
        b = button("Create account && continue", kind="primary")
        b.setMinimumHeight(44)
        b.setDefault(True)
        b.clicked.connect(self._do_setup)
        lay.addWidget(b)
        self.s_pw.textChanged.connect(self._strength)
        return w

    # -- logic
    def show_for_state(self) -> None:
        from PySide6.QtWidgets import QSizePolicy
        self.stack.setCurrentIndex(0 if self.ctx.is_setup() else 1)
        for i in range(self.stack.count()):
            vp = QSizePolicy.Preferred if i == self.stack.currentIndex() else QSizePolicy.Ignored
            self.stack.widget(i).setSizePolicy(QSizePolicy.Preferred, vp)
        self.stack.updateGeometry()
        self.l_pw.clear()
        self.l_err.hide()
        self.f_pw.set_error("")
        if self.ctx.is_setup():
            self.l_id.setText(self.l_id.text())
            (self.l_pw if self.l_id.text() else self.l_id).setFocus()
            self._tick_lock()
        else:
            self.s_id.setFocus()

    def _strength(self, text: str) -> None:
        score, lbl = security.password_strength(text)
        colors = [theme.DANGER, theme.DANGER, theme.WARN, theme.SUCCESS, theme.SUCCESS]
        self.strength.setText(f"Password strength: {lbl}" if text else "")
        self.strength.setStyleSheet(f"color:{colors[score]}; font-size:12px; font-weight:600;")

    def _show_err(self, msg: str) -> None:
        self.l_err.setText(msg)
        self.l_err.setVisible(bool(msg))

    def _tick_lock(self) -> None:
        rem = self.ctx.lock_remaining()
        if rem:
            self.btn_login.setEnabled(False)
            self.btn_login.setText(f"Locked - try again in {rem}s")
            if not self._timer.isActive():
                self._timer.start()
        else:
            self._timer.stop()
            self.btn_login.setEnabled(True)
            self.btn_login.setText("Sign in")

    def _do_login(self) -> None:
        if not self.btn_login.isEnabled():
            return
        oid, pw = self.l_id.text(), self.l_pw.text()
        self.f_id.set_error("" if oid.strip() else "Enter your owner ID")
        self.f_pw.set_error("" if pw else "Enter your password")
        if not oid.strip() or not pw:
            return
        self.btn_login.setEnabled(False)
        self.btn_login.setText("Signing in...")
        self.repaint()
        try:
            self.ctx.login(oid, pw)
        except AuthError as e:
            self._show_err(str(e))
            self.l_pw.clear()
            self.l_pw.setFocus()
            self._tick_lock()
            return
        self._show_err("")
        self._tick_lock()
        self.l_pw.clear()
        self.authenticated.emit()

    def _forgot(self) -> None:
        if not self.ctx.has_recovery_code():
            self._show_err(
                "No recovery code is set yet. Sign in and configure one under "
                "Settings → Owner login & security."
            )
            return
        d = ForgotPasswordDialog(self.window(), self.ctx)
        if d.exec() == QDialog.Accepted:
            self._show_err("")
            self._tick_lock()
            self.l_pw.clear()
            self.authenticated.emit()

    def _do_setup(self) -> None:
        firm, oid = self.s_firm.text().strip(), self.s_id.text().strip()
        pw, pw2 = self.s_pw.text(), self.s_pw2.text()
        rec_code = self.s_rec.text().strip()
        rec_hint = self.s_hint.text().strip()
        ok = True
        self.sf_firm.set_error("" if firm else "Enter the firm name")
        ok &= bool(firm)
        bad_id = len(oid) < 3 or " " in oid
        self.sf_id.set_error("At least 3 characters, no spaces" if bad_id else "")
        ok &= not bad_id
        short = len(pw) < 8
        self.sf_pw.set_error("Use at least 8 characters" if short else "")
        ok &= not short
        mismatch = pw != pw2
        self.sf_pw2.set_error("Passwords do not match" if mismatch else "")
        ok &= not mismatch
        bad_rec = bool(rec_code) and len(rec_code) < 4
        self.sf_rec.set_error("At least 4 characters" if bad_rec else "")
        ok &= not bad_rec
        if not ok:
            return
        self.ctx.setup_owner(oid, pw, firm, rec_code, rec_hint)
        self.authenticated.emit()
