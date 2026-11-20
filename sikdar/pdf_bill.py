"""Minimalist monochrome PDF generator for Fee Bills and Payment Receipts.

Uses PySide6's QPdfWriter + QPainter directly at 300 DPI for razor-sharp
vector typography, hairline silver dividers, the firm's logo, and the owner's
uploaded signature.
"""
from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path

from PySide6.QtCore import QMarginsF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPageLayout, QPageSize, QPainter, QPainterPath, QPdfWriter, QPen, QPixmap

from . import paths, validators

_ONES = [
    "", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
    "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen",
    "Seventeen", "Eighteen", "Nineteen",
]
_TENS = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]


def _two(n: int) -> str:
    if n < 20:
        return _ONES[n]
    return (_TENS[n // 10] + (" " + _ONES[n % 10] if n % 10 else "")).strip()


def _three(n: int) -> str:
    h, r = divmod(n, 100)
    parts = []
    if h:
        parts.append(f"{_ONES[h]} Hundred")
    if r:
        parts.append(_two(r))
    return " ".join(parts)


def inr_words(amount: float) -> str:
    """Convert an INR amount to Indian words (Crore / Lakh / Thousand)."""
    amount = abs(round(amount, 2))
    whole = int(amount)
    paise = round((amount - whole) * 100)
    if paise == 100:
        whole, paise = whole + 1, 0
    if whole == 0 and paise == 0:
        return "Rupees Zero Only"

    parts: list[str] = []
    crore, rem = divmod(whole, 10_000_000)
    lakh, rem = divmod(rem, 100_000)
    thousand, rem = divmod(rem, 1_000)
    if crore:
        parts.append(f"{_three(crore)} Crore")
    if lakh:
        parts.append(f"{_two(lakh)} Lakh")
    if thousand:
        parts.append(f"{_two(thousand)} Thousand")
    if rem:
        parts.append(_three(rem))

    out = "Rupees " + (" ".join(parts) if parts else "Zero")
    if paise:
        out += f" and {_two(paise)} Paise"
    return out + " Only"


def _fmt_date(iso: str) -> str:
    try:
        return date.fromisoformat(iso).strftime("%d %b %Y")
    except (ValueError, TypeError):
        return iso or datetime.now().strftime("%d %b %Y")


def suggested_filename(kind: str, fee_row) -> Path:
    prefix = "Receipt" if kind == "receipt" else "Bill"
    safe = re.sub(r"[^A-Za-z0-9]+", "_", fee_row["client_name"]).strip("_")[:40] or "Client"
    dt = fee_row["date"] or date.today().isoformat()
    paths.ensure_dirs()
    return paths.bills_dir() / f"{prefix}_{fee_row['id']:04d}_{safe}_{dt}.pdf"


def generate_pdf(
    dest: Path,
    kind: str,  # "bill" | "receipt"
    firm_name: str,
    fee_row,
    payments: list,
    previous_balance: float = 0.0,
    signature_path: Path | None = None,
) -> Path:
    """Render a clean, airy, minimalist A4 PDF Bill or Receipt to `dest`."""
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)

    writer = QPdfWriter(str(dest))
    writer.setResolution(300)
    writer.setPageLayout(QPageLayout(QPageSize(QPageSize.A4), QPageLayout.Portrait, QMarginsF(0, 0, 0, 0)))
    writer.setTitle(f"{firm_name} - {'Receipt' if kind == 'receipt' else 'Bill'} #{fee_row['id']:04d}")

    p = QPainter(writer)
    p.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing | QPainter.SmoothPixmapTransform)

    W = writer.width()   # ~2480 px at 300 dpi
    H = writer.height()  # ~3508 px at 300 dpi
    M = 190              # generous page margin
    CW = W - 2 * M       # content width

    # Monochrome palette
    c_black = QColor("#111317")
    c_dark = QColor("#2D313A")
    c_muted = QColor("#6E7582")
    c_line = QColor("#D8DCE4")
    c_soft = QColor("#F3F4F7")
    c_soft2 = QColor("#EAECEF")
    c_white = QColor("#FFFFFF")

    def font(pt: float, weight: QFont.Weight = QFont.Normal) -> QFont:
        f = QFont("Segoe UI")
        f.setPointSizeF(pt)
        f.setWeight(weight)
        return f

    def hline(y_pos: float, color: QColor = c_line, width: float = 2.0) -> None:
        p.setPen(QPen(color, width))
        p.drawLine(int(M), int(y_pos), int(M + CW), int(y_pos))

    def rounded_box(rect: QRectF, radius: float, fill: QColor, border: QColor | None = None) -> None:
        path = QPainterPath()
        path.addRoundedRect(rect, radius, radius)
        p.fillPath(path, fill)
        if border:
            p.setPen(QPen(border, 2.0))
            p.drawPath(path)

    y = float(M)

    # ---------------------------------------------------- 1. HEADER WITH LOGO
    logo_size = 216
    logo_path = paths.resource_path("assets/logo.png")
    if logo_path.exists():
        pm = QPixmap(str(logo_path))
        if not pm.isNull():
            lr = QRectF(M, y, logo_size, logo_size)
            clip = QPainterPath()
            clip.addRoundedRect(lr, 36, 36)
            p.save()
            p.setClipPath(clip)
            p.drawPixmap(lr, pm, QRectF(0, 0, pm.width(), pm.height()))
            p.restore()
            p.setPen(QPen(c_line, 2.5))
            p.drawRoundedRect(lr, 36, 36)

    tx = M + logo_size + 52
    p.setPen(c_black)
    p.setFont(font(17.5, QFont.Bold))
    p.drawText(QRectF(tx, y + 18, CW * 0.54, 76), Qt.AlignLeft | Qt.AlignVCenter, firm_name.upper())
    p.setPen(c_muted)
    p.setFont(font(9.5, QFont.Medium))
    p.drawText(QRectF(tx, y + 96, CW * 0.54, 48), Qt.AlignLeft | Qt.AlignVCenter,
               "INCOME TAX & ACCOUNTING PRACTICE  ·  ESTD 2000")
    p.setFont(font(8.5))
    p.drawText(QRectF(tx, y + 146, CW * 0.54, 44), Qt.AlignLeft | Qt.AlignVCenter,
               "Direct Taxation · ITR Filing · Computation · Compliance")

    # Right side document title & number
    is_rcpt = (kind == "receipt")
    doc_title = "PAYMENT RECEIPT" if is_rcpt else "FEE BILL"
    doc_no = f"{'RCPT' if is_rcpt else 'BILL'}-{fee_row['id']:04d}"
    p.setPen(c_black)
    p.setFont(font(16.5, QFont.Bold))
    p.drawText(QRectF(M, y + 18, CW, 70), Qt.AlignRight | Qt.AlignVCenter, doc_title)

    p.setPen(c_dark)
    p.setFont(font(10, QFont.DemiBold))
    p.drawText(QRectF(M, y + 98, CW, 46), Qt.AlignRight | Qt.AlignVCenter, f"No.  {doc_no}")
    p.setPen(c_muted)
    p.setFont(font(9.5))
    p.drawText(QRectF(M, y + 146, CW, 44), Qt.AlignRight | Qt.AlignVCenter,
               f"Date:  {_fmt_date(fee_row['date'])}")

    y += logo_size + 70
    hline(y, c_black, 3.5)
    y += 76

    # ---------------------------------------------------- 2. CLIENT & META
    billed = float(fee_row["billed"])
    received = float(fee_row["received"])
    this_bal = round(billed - received, 2)
    total_due = round(this_bal + max(previous_balance, 0.0), 2)

    left_w = CW * 0.56
    p.setPen(c_muted)
    p.setFont(font(8.5, QFont.Bold))
    p.drawText(QRectF(M, y, left_w, 42), Qt.AlignLeft,
               "RECEIVED WITH THANKS FROM" if is_rcpt else "BILLED TO")

    p.setPen(c_black)
    p.setFont(font(13.5, QFont.Bold))
    p.drawText(QRectF(M, y + 52, left_w, 72), Qt.AlignLeft, fee_row["client_name"])

    cy = y + 134
    p.setPen(c_dark)
    p.setFont(font(9.5))
    details = []
    if fee_row["client_pan"]:
        details.append(f"PAN:  {fee_row['client_pan']}")
    if fee_row["client_phone"]:
        details.append(f"Phone:  {validators.format_phone(fee_row['client_phone'])}")
    if fee_row["client_email"]:
        details.append(f"Email:  {fee_row['client_email']}")
    if fee_row["client_address"]:
        details.append(fee_row["client_address"].replace("\n", ", "))
    for line in details:
        p.drawText(QRectF(M, cy, left_w, 54), Qt.AlignLeft | Qt.TextWordWrap, line)
        cy += 54

    # Right metadata box
    rx = M + CW * 0.62
    rw = CW * 0.38
    box_h = 248
    rounded_box(QRectF(rx, y, rw, box_h), 26, c_soft, c_line)
    my = y + 34
    meta_rows = [
        ("Financial Year", fee_row["fy"] or "-"),
        ("Status", "PAID IN FULL" if this_bal <= 0.004 else ("PARTIAL" if received > 0 else "PENDING")),
        ("Generated", datetime.now().strftime("%d %b %Y")),
    ]
    for k, v in meta_rows:
        p.setPen(c_muted)
        p.setFont(font(9))
        p.drawText(QRectF(rx + 36, my, rw - 72, 52), Qt.AlignLeft | Qt.AlignVCenter, k)
        p.setPen(c_black)
        p.setFont(font(9.5, QFont.Bold))
        p.drawText(QRectF(rx + 36, my, rw - 72, 52), Qt.AlignRight | Qt.AlignVCenter, v)
        my += 62

    y = max(cy, y + box_h) + 84

    # ---------------------------------------- 3. HIGHLIGHT BANNER (RECEIPT)
    if is_rcpt:
        banner = QRectF(M, y, CW, 236)
        rounded_box(banner, 30, c_soft, c_line)
        p.setPen(c_muted)
        p.setFont(font(9, QFont.Bold))
        p.drawText(QRectF(M + 48, y + 32, CW - 96, 44), Qt.AlignLeft, "AMOUNT RECEIVED")
        p.setPen(c_black)
        p.setFont(font(21, QFont.Bold))
        p.drawText(QRectF(M + 48, y + 78, CW - 96, 86), Qt.AlignLeft | Qt.AlignVCenter,
                   validators.inr(received))
        p.setPen(c_dark)
        p.setFont(font(9.5, QFont.Medium))
        p.drawText(QRectF(M + 48, y + 168, CW - 96, 44), Qt.AlignLeft | Qt.AlignVCenter,
                   inr_words(received))
        y += 296

    # ---------------------------------------------------- 4. PARTICULARS TABLE
    th = 88
    rounded_box(QRectF(M, y, CW, th), 18, c_soft2)
    p.setPen(c_dark)
    p.setFont(font(9, QFont.Bold))
    p.drawText(QRectF(M + 36, y, CW * 0.60, th), Qt.AlignLeft | Qt.AlignVCenter, "PARTICULARS")
    p.drawText(QRectF(M + CW * 0.62, y, CW * 0.16, th), Qt.AlignLeft | Qt.AlignVCenter, "FY")
    p.drawText(QRectF(M + CW * 0.78, y, CW * 0.22 - 36, th), Qt.AlignRight | Qt.AlignVCenter, "AMOUNT")
    y += th + 24

    desc = fee_row["description"] or "Professional Income Tax Consultancy Services"
    row_h = 122
    p.setPen(c_black)
    p.setFont(font(10.5, QFont.Medium))
    p.drawText(QRectF(M + 36, y, CW * 0.58, row_h), Qt.AlignLeft | Qt.AlignVCenter | Qt.TextWordWrap, desc)
    p.setPen(c_dark)
    p.setFont(font(10))
    p.drawText(QRectF(M + CW * 0.62, y, CW * 0.16, row_h), Qt.AlignLeft | Qt.AlignVCenter, fee_row["fy"] or "-")
    p.setPen(c_black)
    p.setFont(font(11, QFont.DemiBold))
    p.drawText(QRectF(M + CW * 0.78, y, CW * 0.22 - 36, row_h), Qt.AlignRight | Qt.AlignVCenter,
               validators.inr(billed))
    y += row_h + 22
    hline(y, c_line, 2.0)
    y += 56

    # ---------------------------------------------------- 5. SUMMARY TOTALS
    sum_w = CW * 0.54
    sx = M + CW - sum_w
    summary_lines: list[tuple[str, str]] = [
        ("Current Bill Amount", validators.inr(billed)),
    ]
    if previous_balance > 0.004:
        summary_lines.append(("Previous Balance (Old Dues)", validators.inr(previous_balance)))
        summary_lines.append(("Total Payable", validators.inr(billed + previous_balance)))
    summary_lines.append(("Less: Amount Received", f"- {validators.inr(received)}" if received else validators.inr(0)))

    for lbl_t, val_t in summary_lines:
        p.setPen(c_muted)
        p.setFont(font(10))
        p.drawText(QRectF(sx, y, sum_w * 0.68, 56), Qt.AlignLeft | Qt.AlignVCenter, lbl_t)
        p.setPen(c_black)
        p.setFont(font(10.5, QFont.DemiBold))
        p.drawText(QRectF(sx + sum_w * 0.68, y, sum_w * 0.32, 56), Qt.AlignRight | Qt.AlignVCenter, val_t)
        y += 66

    y += 20
    bal_rect = QRectF(sx - 28, y, sum_w + 28, 104)
    rounded_box(bal_rect, 20, c_black)
    p.setPen(c_white)
    p.setFont(font(10, QFont.Bold))
    bal_label = "NET BALANCE DUE" if total_due > 0.004 else "BALANCE DUE (SETTLED)"
    p.drawText(QRectF(sx, y, sum_w * 0.60, 104), Qt.AlignLeft | Qt.AlignVCenter, bal_label)
    p.setFont(font(13, QFont.Bold))
    p.drawText(QRectF(sx + sum_w * 0.56, y, sum_w * 0.44 - 16, 104), Qt.AlignRight | Qt.AlignVCenter,
               validators.inr(max(total_due, 0.0)))
    y += 132

    if not is_rcpt:
        p.setPen(c_muted)
        p.setFont(font(9, QFont.Medium))
        p.drawText(QRectF(M, y, CW, 48), Qt.AlignRight | Qt.AlignVCenter,
                   f"In words:  {inr_words(max(total_due, 0.0) if total_due > 0 else billed)}")
        y += 88
    else:
        y += 46

    # ---------------------------------------------------- 6. PAYMENT HISTORY
    if payments:
        p.setPen(c_black)
        p.setFont(font(10, QFont.Bold))
        p.drawText(QRectF(M, y, CW, 52), Qt.AlignLeft | Qt.AlignVCenter, "PAYMENT TRANSACTIONS")
        y += 64
        ph = 72
        rounded_box(QRectF(M, y, CW, ph), 16, c_soft)
        p.setPen(c_muted)
        p.setFont(font(8.5, QFont.Bold))
        p.drawText(QRectF(M + 30, y, CW * 0.20, ph), Qt.AlignLeft | Qt.AlignVCenter, "DATE")
        p.drawText(QRectF(M + CW * 0.22, y, CW * 0.18, ph), Qt.AlignLeft | Qt.AlignVCenter, "MODE")
        p.drawText(QRectF(M + CW * 0.40, y, CW * 0.38, ph), Qt.AlignLeft | Qt.AlignVCenter, "REMARKS")
        p.drawText(QRectF(M + CW * 0.78, y, CW * 0.22 - 30, ph), Qt.AlignRight | Qt.AlignVCenter, "AMOUNT")
        y += ph + 12

        for pay in payments[:6]:
            prh = 74
            p.setPen(c_dark)
            p.setFont(font(9.5))
            p.drawText(QRectF(M + 30, y, CW * 0.20, prh), Qt.AlignLeft | Qt.AlignVCenter, _fmt_date(pay["date"]))
            p.drawText(QRectF(M + CW * 0.22, y, CW * 0.18, prh), Qt.AlignLeft | Qt.AlignVCenter, pay["mode"] or "Cash")
            p.drawText(QRectF(M + CW * 0.40, y, CW * 0.38, prh), Qt.AlignLeft | Qt.AlignVCenter, pay["note"] or "-")
            p.setPen(c_black)
            p.setFont(font(9.5, QFont.DemiBold))
            p.drawText(QRectF(M + CW * 0.78, y, CW * 0.22 - 30, prh), Qt.AlignRight | Qt.AlignVCenter,
                       validators.inr(float(pay["amount"])))
            y += prh
            hline(y, c_soft2, 1.5)

    # ---------------------------------------------------- 7. FOOTER + SIGNATURE
    fy = H - M - 290
    hline(fy, c_line, 2.0)
    p.setPen(c_muted)
    p.setFont(font(8.5))
    p.drawText(QRectF(M, fy + 38, CW * 0.56, 140), Qt.AlignLeft | Qt.TextWordWrap,
               "Thank you for your trust in our practice.\n"
               "Please quote the Bill / Receipt number in all correspondence.")

    sig_x = M + CW * 0.60
    sig_w = CW * 0.40
    p.setPen(c_black)
    p.setFont(font(9.5, QFont.Bold))
    p.drawText(QRectF(sig_x, fy + 30, sig_w, 46), Qt.AlignRight, f"For {firm_name}")

    # Draw uploaded owner signature if present
    if signature_path and Path(signature_path).exists():
        spm = QPixmap(str(signature_path))
        if not spm.isNull():
            max_w, max_h = 460.0, 128.0
            scaled = spm.scaled(int(max_w), int(max_h), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            sw, sh = float(scaled.width()), float(scaled.height())
            sx_img = M + CW - sw
            sy_img = fy + 82 + (max_h - sh) / 2.0
            p.drawPixmap(QRectF(sx_img, sy_img, sw, sh), scaled, QRectF(0, 0, sw, sh))

    line_y = fy + 220
    p.setPen(QPen(c_line, 2.0))
    p.drawLine(int(sig_x + 110), int(line_y), int(M + CW), int(line_y))
    p.setPen(c_muted)
    p.setFont(font(8.5))
    p.drawText(QRectF(sig_x, line_y + 14, sig_w, 42), Qt.AlignRight, "Authorised Signatory")

    p.end()
    return dest
