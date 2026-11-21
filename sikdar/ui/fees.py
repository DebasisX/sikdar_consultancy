"""Fees & payments tracker with multi-item bill breakdown, partial-pay UX & unified PDF bills."""
from __future__ import annotations

from datetime import date
from pathlib import Path

from PySide6.QtCore import QDate, QLocale, Qt, Signal
from PySide6.QtGui import QColor, QDoubleValidator
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QDialog, QFrame, QGridLayout,
    QHeaderView, QLabel, QLineEdit, QMenu, QScrollArea, QTableWidget, QTableWidgetItem, QWidget,
)

from .. import deadlines, paths, pdf_bill, storage, validators
from ..context import AppContext
from . import icons, theme
from .widgets import (
    BaseDialog, Field, PageHeader, QuickShareDialog, StatCard, button, card, clean_date_edit,
    confirm, empty_state, hbox, label, left_headers, vbox,
)

PAY_MODES = ["UPI", "Cash", "Bank Transfer", "Cheque", "Card"]
SERVICE_OPTIONS = [
    "ITR Filing",
    "Computation",
    "GST Filing",
    "Tax Audit",
    "TDS Return",
    "Notice / Scrutiny",
    "PAN / DSC",
    "Consultation",
    "Accounting",
    "Other",
]


def summarize_items(items: list[tuple[str, str, float]]) -> str:
    """Create a concise single-line summary for the Fees table from itemized entries."""
    if not items:
        return ""
    if len(items) == 1:
        cat, desc, _ = items[0]
        if cat and desc:
            return f"{cat} — {desc}"
        return desc or cat
    parts = [cat or desc for cat, desc, _ in items]
    if len(parts) <= 3:
        return ", ".join(parts)
    return f"{', '.join(parts[:2])} +{len(parts) - 2} more"


class MoneyEdit(QLineEdit):
    """Crisp, always-visible numeric currency input."""

    def __init__(self, placeholder: str = "0", height: int = 42, parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setMinimumHeight(height)
        self.setStyleSheet("font-size: 14px; font-weight: 600;")
        v = QDoubleValidator(0.0, 99_999_999.99, 2, self)
        v.setNotation(QDoubleValidator.StandardNotation)
        v.setLocale(QLocale(QLocale.English, QLocale.India))
        self.setValidator(v)

    def amount(self) -> float:
        txt = self.text().replace(",", "").replace("₹", "").strip()
        if not txt:
            return 0.0
        try:
            return round(float(txt), 2)
        except ValueError:
            return 0.0

    def set_amount(self, val: float) -> None:
        if val <= 0:
            self.clear()
        elif float(val).is_integer():
            self.setText(str(int(val)))
        else:
            self.setText(f"{val:.2f}")


class BillItemRow(QWidget):
    """One line item inside FeeDialog: Service dropdown + Description + Amount + Remove."""

    changed = Signal()
    remove_clicked = Signal(object)

    def __init__(self, category: str = "ITR Filing", description: str = "", amount: float = 0.0):
        super().__init__()
        lay = hbox(self, (0, 2, 0, 2), 10)

        self.cat = QComboBox()
        self.cat.setEditable(True)
        self.cat.addItems(SERVICE_OPTIONS)
        self.cat.setCurrentText(category or "ITR Filing")
        self.cat.setFixedWidth(158)
        self.cat.setMinimumHeight(40)

        self.desc = QLineEdit(description)
        self.desc.setPlaceholderText("Item details (e.g. ITR-2 with Capital Gains)")
        self.desc.setMinimumHeight(40)

        self.amt = MoneyEdit("0", height=40)
        self.amt.setFixedWidth(122)
        if amount > 0:
            self.amt.set_amount(amount)

        self.btn_rm = button("", "x", "ghost", small=True)
        self.btn_rm.setFixedSize(32, 32)
        self.btn_rm.setToolTip("Remove item")
        self.btn_rm.clicked.connect(lambda: self.remove_clicked.emit(self))

        lay.addWidget(self.cat)
        lay.addWidget(self.desc, 1)
        lay.addWidget(self.amt)
        lay.addWidget(self.btn_rm)

        self.amt.textChanged.connect(self.changed.emit)
        self.cat.currentTextChanged.connect(self.changed.emit)

    def values(self) -> tuple[str, str, float]:
        return (self.cat.currentText().strip() or "Service", self.desc.text().strip(), self.amt.amount())


class PdfReadyDialog(BaseDialog):
    """Shown right after generating a PDF so the user can view or email it in one click."""

    def __init__(self, parent, title: str, pdf_path: Path, client_name: str = "",
                 client_email: str = "", firm_name: str = ""):
        super().__init__(parent, title, 520)
        self._path = pdf_path
        self._cname = client_name
        self._cemail = client_email
        self._firm = firm_name
        lay = vbox(self, (26, 24, 26, 22), 14)
        top = hbox(spacing=14)
        badge = QLabel()
        badge.setFixedSize(46, 46)
        badge.setAlignment(Qt.AlignCenter)
        badge.setStyleSheet("background:#E8EBF0; border:1px solid #D5DAE3; border-radius:14px;")
        badge.setPixmap(icons.pixmap("file-text", theme.BRAND, 22))
        top.addWidget(badge, 0, Qt.AlignTop)
        col = vbox(spacing=4)
        col.addWidget(label(title, "h2"))
        col.addWidget(label("Saved and ready to share via Email or WhatsApp.", "sub", wrap=True))
        top.addLayout(col, 1)
        lay.addLayout(top)

        box = QFrame()
        box.setObjectName("infoStrip")
        box.setStyleSheet("QFrame#infoStrip { background:#F3F5F8; border:1px solid #DFE3EA; border-radius:12px; }")
        bl = vbox(box, (14, 10, 14, 10), 2)
        bl.addWidget(label(pdf_path.name, "h3", wrap=True))
        p_lbl = label(str(pdf_path.parent), "muted", wrap=True)
        p_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        bl.addWidget(p_lbl)
        lay.addWidget(box)

        row = hbox(spacing=10)
        b_folder = button("Show in Folder", "folder-open")
        b_folder.clicked.connect(lambda: storage.reveal(self._path))
        b_email = button("Email to Client", "mail", "share")
        b_email.clicked.connect(self._email)
        b_open = button("Open PDF", "external-link", "primary")
        b_open.clicked.connect(self._open)
        b_done = button("Done", kind="ghost")
        b_done.clicked.connect(self.accept)
        row.addWidget(b_folder)
        row.addWidget(b_email)
        row.addStretch(1)
        row.addWidget(b_done)
        row.addWidget(b_open)
        lay.addLayout(row)

    def _email(self) -> None:
        QuickShareDialog(self, self._cname or "Client", self._cemail, [self._path], self._firm).exec()

    def _open(self) -> None:
        storage.open_path(self._path)
        self.accept()


class FeeDialog(BaseDialog):
    """Create or edit a fee entry with multiple itemized breakdown rows billed together."""

    def __init__(self, parent, ctx: AppContext, fee=None, client_id: int | None = None):
        super().__init__(parent, "Edit fee entry" if fee else "New fee entry", 690)
        self.ctx = ctx
        self.fee = fee
        self._item_rows: list[BillItemRow] = []
        self._existing_recv = float(fee["received"]) if fee else 0.0
        self.setMinimumHeight(620)
        self.resize(720, 680)

        outer = vbox(self)
        head = QWidget()
        hl = vbox(head, (26, 20, 26, 14), 2)
        hl.addWidget(label("Edit fee entry" if fee else "New fee entry", "h2"))
        hl.addWidget(label("Add one or more services — they will be combined into a single itemized bill.", "sub"))
        outer.addWidget(head)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.viewport().setAutoFillBackground(False)
        body = QWidget()
        body.setObjectName("page")
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)

        lay = vbox(body, (26, 10, 26, 18), 14)

        self.client = QComboBox()
        for c in ctx.db.list_clients():
            self.client.addItem(f"{c['name']}  ·  {c['pan']}" if c["pan"] else c["name"], c["id"])
        want = fee["client_id"] if fee else client_id
        if want:
            i = self.client.findData(want)
            if i >= 0:
                self.client.setCurrentIndex(i)

        # Client's old balance / history strip
        self.ledger_box = QFrame()
        self.ledger_box.setObjectName("ledgerBox")
        self.ledger_box.setStyleSheet(
            "QFrame#ledgerBox { background:#F3F5F8; border:1px solid #DFE3EA; border-radius:12px; }"
        )
        ll = vbox(self.ledger_box, (14, 10, 14, 10), 2)
        self.ledger_title = label("", "h3")
        self.ledger_sub = label("", "muted", wrap=True)
        ll.addWidget(self.ledger_title)
        ll.addWidget(self.ledger_sub)

        self.fy = QComboBox()
        self.fy.setEditable(True)
        self.fy.addItems(deadlines.fy_options())
        self.fy.setCurrentText(fee["fy"] if fee else deadlines.current_fy())
        self.date = clean_date_edit()
        self.date.setDate(QDate.fromString(fee["date"], Qt.ISODate) if fee else QDate.currentDate())

        lay.addWidget(Field("Client", self.client, True))
        lay.addWidget(self.ledger_box)
        r1 = hbox(spacing=14)
        r1.addWidget(Field("Financial year", self.fy), 1)
        r1.addWidget(Field("Bill date", self.date), 1)
        lay.addLayout(r1)

        # ---- Itemized Bill Breakdown box
        items_box = QFrame()
        items_box.setObjectName("itemsBox")
        items_box.setStyleSheet(
            "QFrame#itemsBox { background:#FFFFFF; border:1px solid #DFE3EA; border-radius:14px; }"
        )
        ibl = vbox(items_box, (16, 14, 16, 14), 10)
        hdr = hbox(spacing=10)
        h_svc = label("SERVICE / OPTION", "muted")
        h_svc.setFixedWidth(158)
        h_desc = label("DESCRIPTION", "muted")
        h_amt = label("AMOUNT (₹)", "muted")
        h_amt.setFixedWidth(122)
        h_sp = QLabel()
        h_sp.setFixedWidth(32)
        hdr.addWidget(h_svc)
        hdr.addWidget(h_desc, 1)
        hdr.addWidget(h_amt)
        hdr.addWidget(h_sp)
        ibl.addLayout(hdr)

        self.items_host = vbox(spacing=8)
        ibl.addLayout(self.items_host)

        self.items_err = label("", "error")
        self.items_err.hide()
        ibl.addWidget(self.items_err)

        item_foot = hbox(spacing=10)
        self.btn_add_item = button("Add item", "plus", small=True)
        self.btn_add_item.clicked.connect(lambda: self._add_item_row())
        item_foot.addWidget(self.btn_add_item)
        item_foot.addStretch(1)
        self.total_lbl = label("Total billed: ₹0", "h2")
        item_foot.addWidget(self.total_lbl)
        ibl.addLayout(item_foot)
        lay.addWidget(items_box)

        # ---- Payment inputs
        self.received = MoneyEdit("0")
        self.mode = QComboBox()
        self.mode.addItems(PAY_MODES)
        if fee:
            self.f_recv = Field(
                f"Add new instalment (₹)  ·  Already paid: {validators.inr(self._existing_recv)}",
                self.received,
            )
        else:
            self.f_recv = Field("Received now (₹)", self.received)
        r2 = hbox(spacing=14)
        r2.addWidget(self.f_recv, 1)
        r2.addWidget(Field("Payment mode", self.mode), 1)
        lay.addLayout(r2)

        self.live_summary = label("", "sub")
        lay.addWidget(self.live_summary)

        self.gen_pdf = QCheckBox("Generate PDF Bill / Receipt after saving")
        self.gen_pdf.setChecked(False)
        lay.addWidget(self.gen_pdf)
        lay.addStretch(1)

        # ---- Footer
        foot_bar = QWidget()
        fl = hbox(foot_bar, (26, 12, 26, 18), 10)
        fl.addStretch(1)
        c = button("Cancel")
        c.clicked.connect(self.reject)
        ok = button("Save bill", "check", "primary")
        ok.setDefault(True)
        ok.clicked.connect(self._ok)
        fl.addWidget(c)
        fl.addWidget(ok)
        outer.addWidget(foot_bar)

        # Load existing items (or start with 1 row)
        if fee:
            existing_items = ctx.db.list_fee_items(fee["id"])
            if existing_items:
                for it in existing_items:
                    self._add_item_row(it["category"], it["description"], float(it["amount"]))
            else:
                self._add_item_row("ITR Filing", fee["description"], float(fee["billed"]))
        else:
            self._add_item_row("ITR Filing", "", 0.0)

        self.has_client = self.client.count() > 0
        self.client.currentIndexChanged.connect(self._refresh_ledger)
        self.received.textChanged.connect(self._refresh_live)
        self._refresh_ledger()

    def _add_item_row(self, category: str = "ITR Filing", description: str = "", amount: float = 0.0) -> None:
        row = BillItemRow(category, description, amount)
        row.changed.connect(self._refresh_live)
        row.remove_clicked.connect(self._remove_item_row)
        self._item_rows.append(row)
        self.items_host.addWidget(row)
        self._sync_remove_buttons()
        self._refresh_live()

    def _remove_item_row(self, row: BillItemRow) -> None:
        if len(self._item_rows) <= 1:
            return
        self._item_rows.remove(row)
        self.items_host.removeWidget(row)
        row.hide()
        row.setParent(None)
        row.deleteLater()
        self._sync_remove_buttons()
        self._refresh_live()

    def _sync_remove_buttons(self) -> None:
        can_rm = len(self._item_rows) > 1
        for r in self._item_rows:
            r.btn_rm.setEnabled(can_rm)

    def _items_data(self) -> list[tuple[str, str, float]]:
        return [r.values() for r in self._item_rows if r.values()[2] > 0 or r.values()[1]]

    def _total_billed(self) -> float:
        return round(sum(r.amt.amount() for r in self._item_rows), 2)

    def _total_received(self) -> float:
        return round(self._existing_recv + self.received.amount(), 2) if self.fee else self.received.amount()

    def _refresh_ledger(self) -> None:
        cid = self.client.currentData()
        if cid is None:
            self.ledger_box.hide()
            return
        exclude = self.fee["id"] if self.fee else None
        old_billed, old_recv, old_bal = self.ctx.db.client_fee_summary(cid, exclude_fee_id=exclude)
        self._old_bal = old_bal
        self.ledger_box.show()
        if old_billed > 0:
            if old_bal > 0.004:
                self.ledger_title.setText(f"Previous unpaid balance (Old Dues):  {validators.inr(old_bal)}")
            else:
                self.ledger_title.setText("Previous dues:  All cleared (₹0)")
            self.ledger_sub.setText(
                f"Earlier bills: {validators.inr(old_billed)}   ·   Earlier paid: {validators.inr(old_recv)}"
            )
        else:
            self.ledger_title.setText("Previous balance:  ₹0")
            self.ledger_sub.setText("No earlier fee entries for this client.")
        self._refresh_live()

    def _refresh_live(self) -> None:
        b = self._total_billed()
        r = self._total_received()
        bal = round(b - r, 2)
        old = getattr(self, "_old_bal", 0.0)
        total = round(bal + max(old, 0.0), 2)
        self.total_lbl.setText(f"Total billed: {validators.inr(b)}")
        parts = [f"Total paid on this bill: {validators.inr(r)}", f"Remaining: {validators.inr(bal)}"]
        if old > 0.004:
            parts.append(f"Total with old dues: {validators.inr(total)}")
        self.live_summary.setText("   ·   ".join(parts))

    def _ok(self) -> None:
        self.items_err.hide()
        self.f_recv.set_error("")
        if self.client.currentData() is None:
            self.items_err.setText("Register a client first.")
            self.items_err.show()
            return
        items = [r.values() for r in self._item_rows if r.values()[2] > 0]
        if not items:
            self.items_err.setText("Enter an amount greater than ₹0 for at least one bill item.")
            self.items_err.show()
            return
        b = round(sum(amt for _, _, amt in items), 2)
        r = self._total_received()
        if r > b + 0.004:
            self.f_recv.set_error(f"Exceeds remaining balance ({validators.inr(max(b - self._existing_recv, 0))})")
            return
        self.accept()

    def items(self) -> list[tuple[str, str, float]]:
        return [r.values() for r in self._item_rows if r.values()[2] > 0]

    def values(self):
        its = self.items()
        billed = round(sum(amt for _, _, amt in its), 2)
        return (
            self.client.currentData(),
            self.fy.currentText().strip(),
            summarize_items(its),
            billed,
            self._total_received(),
            self.date.date().toString(Qt.ISODate),
        )

    def added_instalment(self) -> float:
        return self.received.amount() if self.fee else 0.0

    def payment_mode(self) -> str:
        return self.mode.currentText()


class RecordPaymentDialog(BaseDialog):
    """Record a payment with date, mode, note, and optional instant PDF."""

    def __init__(self, parent, ctx: AppContext, fee_row):
        super().__init__(parent, "Record payment", 480)
        self.fee = fee_row
        bal = round(float(fee_row["billed"]) - float(fee_row["received"]), 2)
        _, _, total_client_bal = ctx.db.client_fee_summary(fee_row["client_id"])
        self._bal = bal

        lay = vbox(self, (26, 24, 26, 22), 14)
        lay.addWidget(label(f"Record payment — {fee_row['client_name']}", "h2", wrap=True))

        info = QFrame()
        info.setObjectName("payInfo")
        info.setStyleSheet("QFrame#payInfo { background:#F3F5F8; border:1px solid #DFE3EA; border-radius:12px; }")
        il = vbox(info, (14, 10, 14, 10), 4)
        il.addWidget(label(
            f"Bill: {validators.inr(fee_row['billed'])}   ·   Already paid: {validators.inr(fee_row['received'])}   ·   Remaining: {validators.inr(bal)}",
            "h3", wrap=True))
        if total_client_bal > bal + 0.004:
            il.addWidget(label(
                f"Client's total outstanding (incl. older bills): {validators.inr(total_client_bal)}",
                "muted"))
        lay.addWidget(info)

        self.amount = MoneyEdit("Enter new instalment amount")
        self.amount.set_amount(bal)
        self.f_amt = Field("New payment received (₹)", self.amount, True)

        qrow = hbox(spacing=8)
        b_full = button(f"Full balance ({validators.inr(bal)})", kind="pay", small=True)
        b_full.clicked.connect(lambda: self.amount.set_amount(bal))
        half = round(bal / 2.0, 2)
        b_half = button(f"Half ({validators.inr(half)})", small=True)
        b_half.clicked.connect(lambda: self.amount.set_amount(half))
        qrow.addWidget(b_full)
        if bal >= 2:
            qrow.addWidget(b_half)
        qrow.addStretch(1)

        self.after_lbl = label("", "sub")
        self.amount.textChanged.connect(self._update_after)

        self.pay_date = clean_date_edit()
        self.pay_date.setDate(QDate.currentDate())
        self.mode = QComboBox()
        self.mode.addItems(PAY_MODES)
        self.note = QLineEdit()
        self.note.setPlaceholderText("e.g. UPI Ref / Cheque No. / Remarks")
        self.gen_receipt = QCheckBox("Generate PDF Bill / Receipt after recording")
        self.gen_receipt.setChecked(True)

        lay.addWidget(self.f_amt)
        lay.addLayout(qrow)
        lay.addWidget(self.after_lbl)
        r1 = hbox(spacing=14)
        r1.addWidget(Field("Payment date", self.pay_date), 1)
        r1.addWidget(Field("Mode", self.mode), 1)
        lay.addLayout(r1)
        lay.addWidget(Field("Remarks (optional)", self.note))
        lay.addWidget(self.gen_receipt)
        self._update_after()

        foot = hbox(spacing=10)
        foot.addStretch(1)
        c = button("Cancel")
        c.clicked.connect(self.reject)
        ok = button("Record payment", "check", "primary")
        ok.setDefault(True)
        ok.clicked.connect(self._ok)
        foot.addWidget(c)
        foot.addWidget(ok)
        lay.addLayout(foot)

    def _update_after(self) -> None:
        amt = self.amount.amount()
        new_paid = round(float(self.fee["received"]) + amt, 2)
        new_rem = round(max(float(self.fee["billed"]) - new_paid, 0.0), 2)
        status = "Settled in full!" if new_rem <= 0.004 else f"Remaining: {validators.inr(new_rem)}"
        self.after_lbl.setText(f"After this payment  →  Total paid: {validators.inr(new_paid)}   ·   {status}")

    def _ok(self) -> None:
        amt = self.amount.amount()
        if amt <= 0 or amt > self._bal + 0.004:
            self.f_amt.set_error(f"Enter an amount between ₹1 and {validators.inr(self._bal)}")
            return
        self.accept()

    def values(self) -> tuple[float, str, str, str]:
        return (
            self.amount.amount(),
            self.pay_date.date().toString(Qt.ISODate),
            self.mode.currentText(),
            self.note.text().strip(),
        )


class FeesPage(QWidget):
    data_changed = Signal()
    toast = Signal(str, str)

    def __init__(self, ctx: AppContext):
        super().__init__()
        self.setObjectName("page")
        self.ctx = ctx
        lay = vbox(self, (36, 30, 36, 28), 20)
        self.header = PageHeader("Fees & payments", "Create itemized bills, record instalments and share clean PDF bills.")
        b_dir = button("Bills folder", "folder-open")
        b_dir.setToolTip("Open the Bills & Receipts folder to share PDFs")
        b_dir.clicked.connect(lambda: storage.reveal(paths.bills_dir()))
        b_pdf = button("Download PDF", "file-text")
        b_pdf.setToolTip("Generate minimalist itemized PDF Bill / Receipt for selected entry")
        b_pdf.clicked.connect(self._pdf_selected)
        b = button("New fee entry", "plus", "primary")
        b.clicked.connect(lambda: self.add_fee())
        for btn in (b_dir, b_pdf, b):
            self.header.add_action(btn)
        lay.addWidget(self.header)

        stats = QGridLayout()
        stats.setSpacing(18)
        self.k_billed = StatCard("Total billed", "file-text", "#2563EB", "#EAF1FF", clickable=True)
        self.k_billed.setToolTip("Show all fee entries")
        self.k_billed.clicked.connect(lambda: self.status_filter.setCurrentIndex(0))
        self.k_recv = StatCard("Received", "check-circle", "#059669", "#E6F7F0", clickable=True)
        self.k_recv.setToolTip("Filter to paid entries")
        self.k_recv.clicked.connect(lambda: self.status_filter.setCurrentIndex(2))
        self.k_out = StatCard("Outstanding", "alert", "#DC2626", "#FEE2E2", clickable=True)
        self.k_out.setToolTip("Filter to pending dues")
        self.k_out.clicked.connect(lambda: self.status_filter.setCurrentIndex(1))
        for i, k in enumerate((self.k_billed, self.k_recv, self.k_out)):
            stats.addWidget(k, 0, i)
            stats.setColumnStretch(i, 1)
        lay.addLayout(stats)

        bar = hbox(spacing=12)
        self.client_filter = QComboBox()
        self.client_filter.setMinimumWidth(260)
        self.client_filter.currentIndexChanged.connect(self._fill)
        self.status_filter = QComboBox()
        self.status_filter.addItems(["All entries", "Pending", "Paid"])
        self.status_filter.setFixedWidth(150)
        self.status_filter.currentIndexChanged.connect(self._fill)
        bar.addWidget(self.client_filter)
        bar.addWidget(self.status_filter)
        bar.addStretch(1)
        lay.addLayout(bar)

        self.panel = card()
        pl = vbox(self.panel, (10, 6, 10, 10))
        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels(
            ["Date", "Client", "FY", "Particulars", "Billed", "Received", "Balance", "Status", "Action"])
        t = self.table
        left_headers(t)
        t.verticalHeader().setVisible(False)
        t.verticalHeader().setDefaultSectionSize(54)
        t.setShowGrid(False)
        t.setSelectionBehavior(QAbstractItemView.SelectRows)
        t.setSelectionMode(QAbstractItemView.SingleSelection)
        t.setEditTriggers(QAbstractItemView.NoEditTriggers)
        t.setFocusPolicy(Qt.NoFocus)
        hh = t.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Fixed)
        t.setColumnWidth(0, 102)
        hh.setSectionResizeMode(1, QHeaderView.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.Fixed)
        t.setColumnWidth(2, 86)
        hh.setSectionResizeMode(3, QHeaderView.Stretch)
        for i in (4, 5, 6):
            hh.setSectionResizeMode(i, QHeaderView.Fixed)
            t.setColumnWidth(i, 92)
        hh.setSectionResizeMode(7, QHeaderView.Fixed)
        t.setColumnWidth(7, 86)
        hh.setSectionResizeMode(8, QHeaderView.Fixed)
        t.setColumnWidth(8, 118)
        t.setContextMenuPolicy(Qt.CustomContextMenu)
        t.customContextMenuRequested.connect(self._menu)
        t.cellDoubleClicked.connect(lambda r, c: self.edit_fee(r) if c != 8 else None)
        pl.addWidget(t, 1)
        self.empty = empty_state("rupee", "No fee entries", "Add an entry when you bill a client.")
        pl.addWidget(self.empty, 1)
        lay.addWidget(self.panel, 1)
        lay.addWidget(label(
            "Tip: click '+ Pay' to record an instalment, 'PDF' to download/email the itemized bill, or double-click to edit items.",
            "muted"))

    def refresh(self) -> None:
        keep = self.client_filter.currentData()
        self.client_filter.blockSignals(True)
        self.client_filter.clear()
        self.client_filter.addItem("All clients", None)
        for c in self.ctx.db.list_clients():
            self.client_filter.addItem(c["name"], c["id"])
        i = self.client_filter.findData(keep)
        self.client_filter.setCurrentIndex(max(i, 0))
        self.client_filter.blockSignals(False)
        self._fill()

    def show_client(self, cid: int) -> None:
        self.refresh()
        i = self.client_filter.findData(cid)
        if i >= 0:
            self.client_filter.setCurrentIndex(i)

    def show_pending(self) -> None:
        self.refresh()
        self.client_filter.setCurrentIndex(0)
        self.status_filter.setCurrentIndex(1)

    def _fill(self) -> None:
        cid = self.client_filter.currentData()
        mode = self.status_filter.currentIndex()
        rows = [f for f in self.ctx.db.list_fees(cid)
                if mode == 0 or (mode == 1 and f["billed"] - f["received"] > 0.004)
                or (mode == 2 and f["billed"] - f["received"] <= 0.004)]
        billed = sum(f["billed"] for f in rows)
        recv = sum(f["received"] for f in rows)
        self.k_billed.set(validators.inr(billed), f"{len(rows)} entr{'y' if len(rows) == 1 else 'ies'}")
        self.k_recv.set(validators.inr(recv), f"{(recv / billed * 100) if billed else 0:.0f}% collected")
        self.k_out.set(validators.inr(billed - recv), "to be collected")
        self.table.setRowCount(len(rows))
        R = Qt.AlignRight | Qt.AlignVCenter
        for r, f in enumerate(rows):
            bal = f["billed"] - f["received"]
            try:
                d = date.fromisoformat(f["date"]).strftime("%d %b %Y")
            except ValueError:
                d = f["date"]
            first = QTableWidgetItem(d)
            first.setData(Qt.UserRole, f["id"])
            self.table.setItem(r, 0, first)
            nm = QTableWidgetItem(f["client_name"])
            font = nm.font()
            font.setWeight(font.Weight.DemiBold)
            nm.setFont(font)
            self.table.setItem(r, 1, nm)
            self.table.setItem(r, 2, QTableWidgetItem(f["fy"] or "-"))
            desc_item = QTableWidgetItem(f["description"] or "-")
            its = self.ctx.db.list_fee_items(f["id"])
            if len(its) > 1:
                tip = "\n".join(
                    f"• {it['category']}" + (f" ({it['description']})" if it["description"] else "")
                    + f": {validators.inr(it['amount'])}"
                    for it in its
                )
                desc_item.setToolTip(tip)
            self.table.setItem(r, 3, desc_item)
            for col, val in ((4, f["billed"]), (5, f["received"]), (6, bal)):
                it = QTableWidgetItem(validators.inr(val))
                it.setTextAlignment(R)
                if col == 6 and bal > 0.004:
                    it.setForeground(QColor(theme.DANGER))
                self.table.setItem(r, col, it)
            if bal <= 0.004:
                st, colr = "●  Paid", theme.SUCCESS
            elif f["received"] > 0:
                st, colr = "●  Partial", theme.WARN
            else:
                st, colr = "●  Pending", theme.DANGER
            s = QTableWidgetItem(st)
            s.setForeground(QColor(colr))
            self.table.setItem(r, 7, s)

            # Inline 1-click Action button: '+ Pay' for Pending/Partial, 'PDF' for Paid
            aw = QWidget()
            al = hbox(aw, (4, 0, 6, 0), 0)
            fid = f["id"]
            if bal > 0.004:
                bp = button("+ Pay", kind="pay", small=True)
                bp.setMinimumWidth(84)
                bp.setToolTip("Record next instalment without retyping already-paid amount")
                bp.clicked.connect(lambda _=False, x=fid: self._pay_by_id(x))
                al.addWidget(bp, 0, Qt.AlignVCenter | Qt.AlignRight)
            else:
                br = button("PDF", "file-text", small=True)
                br.setMinimumWidth(84)
                br.setToolTip("Generate / email itemized PDF Bill & Receipt")
                br.clicked.connect(lambda _=False, x=fid: self.generate_pdf_for(x))
                al.addWidget(br, 0, Qt.AlignVCenter | Qt.AlignRight)
            self.table.setCellWidget(r, 8, aw)
        self.table.setVisible(bool(rows))
        self.empty.setVisible(not rows)

    def _fid(self, row: int) -> int:
        return self.table.item(row, 0).data(Qt.UserRole)

    def _pdf_selected(self) -> None:
        r = self.table.currentRow()
        if r < 0:
            self.toast.emit("Select a fee entry from the table first", "error")
            return
        self.generate_pdf_for(self._fid(r))

    def generate_pdf_for(self, fee_id: int) -> None:
        f = self.ctx.db.get_fee(fee_id)
        if not f:
            return
        _, _, prev_bal = self.ctx.db.client_fee_summary(f["client_id"], exclude_fee_id=fee_id)
        payments = self.ctx.db.list_payments(fee_id)
        items = self.ctx.db.list_fee_items(fee_id)
        dest = pdf_bill.suggested_filename(f)
        try:
            pdf_bill.generate_pdf(
                dest, self.ctx.firm_name(), f, payments, prev_bal,
                signature_path=self.ctx.signature_path(),
                items=items,
            )
        except OSError as e:
            self.toast.emit(f"Could not create PDF: {e}", "error")
            return
        doc_title, _ = pdf_bill._auto_mode(f)
        self.ctx.db.log(f"Generated {doc_title.title()} PDF for {f['client_name']} ({dest.name})")
        PdfReadyDialog(
            self.window(), f"{doc_title.title()} PDF ready", dest,
            client_name=f["client_name"],
            client_email=f["client_email"] or "",
            firm_name=self.ctx.firm_name(),
        ).exec()

    def _pay_by_id(self, fid: int) -> None:
        f = self.ctx.db.get_fee(fid)
        if f:
            self._record_payment(f)

    def add_fee(self, client_id: int | None = None) -> None:
        d = FeeDialog(self.window(), self.ctx, None, client_id)
        if not d.has_client:
            self.toast.emit("Register a client before adding fees", "error")
            return
        if d.exec() == QDialog.Accepted:
            cid, fy, desc, billed, recv, dt = d.values()
            fid = self.ctx.db.add_fee(
                cid, fy, desc, billed, recv, dt,
                mode=d.payment_mode(), items=d.items(),
            )
            self.ctx.db.log(f"Fee entry {validators.inr(billed)} ({len(d.items())} items) added")
            self.refresh()
            self.data_changed.emit()
            self.toast.emit("Fee entry added", "success")
            if d.gen_pdf.isChecked():
                self.generate_pdf_for(fid)

    def edit_fee(self, row: int) -> None:
        f = self.ctx.db.get_fee(self._fid(row))
        if not f:
            return
        d = FeeDialog(self.window(), self.ctx, f)
        if d.exec() == QDialog.Accepted:
            cid, fy, desc, billed, recv, dt = d.values()
            self.ctx.db.update_fee(f["id"], cid, fy, desc, billed, recv, dt, items=d.items())
            added = d.added_instalment()
            if added > 0.004:
                self.ctx.db.conn.execute(
                    "INSERT INTO fee_payments(fee_id,amount,date,mode,note,created_at) "
                    "VALUES(?,?,?,?,?,datetime('now','localtime'))",
                    (f["id"], added, date.today().isoformat(), d.payment_mode(), "Additional instalment"))
                self.ctx.db.conn.commit()
            self.refresh()
            self.data_changed.emit()
            self.toast.emit("Fee entry updated", "success")
            if d.gen_pdf.isChecked():
                self.generate_pdf_for(f["id"])

    def _menu(self, pos) -> None:
        idx = self.table.indexAt(pos)
        if not idx.isValid():
            return
        self.table.selectRow(idx.row())
        f = self.ctx.db.get_fee(self._fid(idx.row()))
        if not f:
            return
        m = QMenu(self)
        a_pay = m.addAction(icons.icon("rupee", theme.TEXT_2, 16), "Record payment")
        a_pay.setEnabled(f["billed"] - f["received"] > 0.004)
        a_pdf = m.addAction(icons.icon("file-text", theme.TEXT_2, 16), "Download PDF (Bill / Receipt)")
        m.addSeparator()
        a_edit = m.addAction(icons.icon("edit", theme.TEXT_2, 16), "Edit items & details")
        a_del = m.addAction(icons.icon("trash", theme.DANGER, 16), "Delete")
        act = m.exec(self.table.viewport().mapToGlobal(pos))
        if act == a_pay:
            self._record_payment(f)
        elif act == a_pdf:
            self.generate_pdf_for(f["id"])
        elif act == a_edit:
            self.edit_fee(idx.row())
        elif act == a_del:
            if confirm(self.window(), "Delete fee entry?", "This cannot be undone.", "Delete", danger=True):
                self.ctx.db.delete_fee(f["id"])
                self.refresh()
                self.data_changed.emit()

    def _record_payment(self, f) -> None:
        d = RecordPaymentDialog(self.window(), self.ctx, f)
        if d.exec() != QDialog.Accepted:
            return
        amt, pay_date, mode, note = d.values()
        self.ctx.db.record_payment(f["id"], amt, pay_date, mode, note)
        self.ctx.db.log(f"Payment {validators.inr(amt)} ({mode}) received from {f['client_name']}")
        self.refresh()
        self.data_changed.emit()
        self.toast.emit(f"Recorded {validators.inr(amt)}", "success")
        if d.gen_receipt.isChecked():
            self.generate_pdf_for(f["id"])
