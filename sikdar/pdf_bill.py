"""Minimalist monochrome PDF generator for unified Fee Bills & Payment Receipts.

Automatically formats as:
  - FEE BILL             (when no payment received yet)
  - FEE BILL & RECEIPT   (when partially paid)
  - PAYMENT RECEIPT      (when paid in full)

Includes itemized service breakdown (`fee_items`), previous unpaid dues,
payment transaction history, amount in Indian words, firm logo, and the
owner's uploaded authorised signature.
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


def _auto_mode(fee_row) -> tuple[str, str]:
    """Return (doc_title, file_prefix) automatically from payment status."""
    billed = float(fee_row["billed"])
    received = float(fee_row["received"])
    if received <= 0.004:
        return "FEE BILL", "Bill"
    if billed - received <= 0.004:
        return "PAYMENT RECEIPT", "Receipt"
    return "FEE BILL & RECEIPT", "Bill_Receipt"


def suggested_filename(fee_row, kind: str | None = None) -> Path:
    _, auto_prefix = _auto_mode(fee_row)
    prefix = {"bill": "Bill", "receipt": "Receipt"}.get(kind or "", auto_prefix)
    safe = re.sub(r"[^A-Za-z0-9]+", "_", fee_row["client_name"]).strip("_")[:40] or "Client"
    dt = fee_row["date"] or date.today().isoformat()
    paths.ensure_dirs()
    return paths.bills_dir() / f"{prefix}_{fee_row['id']:04d}_{safe}_{dt}.pdf"


def generate_pdf(
    dest: Path,
    firm_name: str,
    fee_row,
    payments: list,
    previous_balance: float = 0.0,
    signature_path: Path | None = None,
    items: list | None = None,
) -> Path:
    """Render a clean, airy, minimalist A4 PDF Bill / Receipt with itemized breakdown."""
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)

    doc_title, file_prefix = _auto_mode(fee_row)
    billed = float(fee_row["billed"])
    received = float(fee_row["received"])
    this_bal = round(billed - received, 2)
    total_due = round(this_bal + max(previous_balance, 0.0), 2)
    is_paid = this_bal <= 0.004

    writer = QPdfWriter(str(dest))
    writer.setResolution(300)
    writer.setPageLayout(QPageLayout(QPageSize(QPageSize.A4), QPageLayout.Portrait, QMarginsF(0, 0, 0, 0)))
    writer.setTitle(f"{firm_name} - {file_prefix} #{fee_row['id']:04d}")

    p = QPainter(writer)
    p.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing | QPainter.SmoothPixmapTransform)

    W = writer.width()   # ~2480 px at 300 dpi
    H = writer.height()  # ~3508 px at 300 dpi
    M = 185              # generous page margin
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
    logo_size = 208
    logo_path = paths.resource_path("assets/logo.png")
    if logo_path.exists():
        pm = QPixmap(str(logo_path))
        if not pm.isNull():
            lr = QRectF(M, y, logo_size, logo_size)
            clip = QPainterPath()
            clip.addRoundedRect(lr, 34, 34)
            p.save()
            p.setClipPath(clip)
            p.drawPixmap(lr, pm, QRectF(0, 0, pm.width(), pm.height()))
            p.restore()
            p.setPen(QPen(c_line, 2.5))
            p.drawRoundedRect(lr, 34, 34)

    tx = M + logo_size + 50
    p.setPen(c_black)
    p.setFont(font(17, QFont.Bold))
    p.drawText(QRectF(tx, y + 16, CW * 0.54, 72), Qt.AlignLeft | Qt.AlignVCenter, firm_name.upper())
    p.setPen(c_muted)
    p.setFont(font(9.2, QFont.Medium))
    p.drawText(QRectF(tx, y + 92, CW * 0.54, 46), Qt.AlignLeft | Qt.AlignVCenter,
               "INCOME TAX & ACCOUNTING PRACTICE  ·  ESTD 2000")
    p.setFont(font(8.5))
    p.drawText(QRectF(tx, y + 140, CW * 0.54, 42), Qt.AlignLeft | Qt.AlignVCenter,
               "Direct Taxation · GST · ITR Filing · Computation · Compliance")

    # Right side document title & number
    doc_no = f"{'RCPT' if is_paid else 'BILL'}-{fee_row['id']:04d}"
    p.setPen(c_black)
    p.setFont(font(15.5, QFont.Bold))
    p.drawText(QRectF(M, y + 16, CW, 68), Qt.AlignRight | Qt.AlignVCenter, doc_title)

    p.setPen(c_dark)
    p.setFont(font(10, QFont.DemiBold))
    p.drawText(QRectF(M, y + 92, CW, 46), Qt.AlignRight | Qt.AlignVCenter, f"No.  {doc_no}")
    p.setPen(c_muted)
    p.setFont(font(9.5))
    p.drawText(QRectF(M, y + 140, CW, 42), Qt.AlignRight | Qt.AlignVCenter,
               f"Date:  {_fmt_date(fee_row['date'])}")

    y += logo_size + 62
    hline(y, c_black, 3.5)
    y += 66

    # ---------------------------------------------------- 2. CLIENT & META
    left_w = CW * 0.56
    p.setPen(c_muted)
    p.setFont(font(8.5, QFont.Bold))
    p.drawText(QRectF(M, y, left_w, 40), Qt.AlignLeft,
               "RECEIVED WITH THANKS FROM" if is_paid else "BILLED TO")

    p.setPen(c_black)
    p.setFont(font(13.5, QFont.Bold))
    p.drawText(QRectF(M, y + 48, left_w, 70), Qt.AlignLeft, fee_row["client_name"])

    cy = y + 128
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
        p.drawText(QRectF(M, cy, left_w, 50), Qt.AlignLeft | Qt.TextWordWrap, line)
        cy += 50

    # Right metadata box
    rx = M + CW * 0.62
    rw = CW * 0.38
    box_h = 236
    rounded_box(QRectF(rx, y, rw, box_h), 24, c_soft, c_line)
    my = y + 30
    meta_rows = [
        ("Financial Year", fee_row["fy"] or "-"),
        ("Status", "PAID IN FULL" if is_paid else ("PARTIAL" if received > 0 else "PENDING")),
        ("Generated", datetime.now().strftime("%d %b %Y")),
    ]
    for k, v in meta_rows:
        p.setPen(c_muted)
        p.setFont(font(9))
        p.drawText(QRectF(rx + 34, my, rw - 68, 50), Qt.AlignLeft | Qt.AlignVCenter, k)
        p.setPen(c_black)
        p.setFont(font(9.5, QFont.Bold))
        p.drawText(QRectF(rx + 34, my, rw - 68, 50), Qt.AlignRight | Qt.AlignVCenter, v)
        my += 58

    y = max(cy, y + box_h) + 68

    # ---------------------------------------- 3. PAID BANNER (ONLY IF PAID)
    if is_paid:
        banner = QRectF(M, y, CW, 264)
        rounded_box(banner, 26, c_soft, c_line)
        p.setPen(c_muted)
        p.setFont(font(8.8, QFont.Bold))
        p.drawText(QRectF(M + 52, y + 36, CW - 104, 40), Qt.AlignLeft | Qt.AlignVCenter, "AMOUNT RECEIVED")
        p.setPen(c_black)
        p.setFont(font(15.5, QFont.Bold))
        p.drawText(QRectF(M + 52, y + 90, CW - 104, 68), Qt.AlignLeft | Qt.AlignVCenter,
                   validators.inr(received))
        p.setPen(c_dark)
        p.setFont(font(9.2, QFont.Medium))
        p.drawText(QRectF(M + 52, y + 184, CW - 104, 44), Qt.AlignLeft | Qt.AlignVCenter,
                   inr_words(received))
        y += 322

    # ---------------------------------------- 4. ITEMIZED BREAKDOWN TABLE
    # Normalise breakdown items (fallback to legacy single description row)
    norm_items: list[tuple[str, str, float]] = []
    if items:
        for it in items:
            cat = (it["category"] if hasattr(it, "keys") else it[0]) or "Service"
            desc = (it["description"] if hasattr(it, "keys") else it[1]) or ""
            amt = float(it["amount"] if hasattr(it, "keys") else it[2])
            norm_items.append((cat, desc, amt))
    if not norm_items:
        norm_items = [("Consultancy", fee_row["description"] or "Professional Tax Consultancy Services", billed)]

    th = 82
    rounded_box(QRectF(M, y, CW, th), 16, c_soft2)
    p.setPen(c_dark)
    p.setFont(font(8.8, QFont.Bold))
    p.drawText(QRectF(M + 30, y, CW * 0.06, th), Qt.AlignLeft | Qt.AlignVCenter, "#")
    p.drawText(QRectF(M + CW * 0.08, y, CW * 0.24, th), Qt.AlignLeft | Qt.AlignVCenter, "SERVICE")
    p.drawText(QRectF(M + CW * 0.33, y, CW * 0.45, th), Qt.AlignLeft | Qt.AlignVCenter, "DESCRIPTION")
    p.drawText(QRectF(M + CW * 0.78, y, CW * 0.22 - 30, th), Qt.AlignRight | Qt.AlignVCenter, "AMOUNT")
    y += th + 14

    # Compact row height gracefully if there are many items so everything fits comfortably on A4
    row_h = 94 if len(norm_items) <= 4 else (76 if len(norm_items) <= 7 else 64)
    for idx, (cat, desc, amt) in enumerate(norm_items, start=1):
        p.setPen(c_muted)
        p.setFont(font(9.5, QFont.Medium))
        p.drawText(QRectF(M + 30, y, CW * 0.06, row_h), Qt.AlignLeft | Qt.AlignVCenter, f"{idx}.")
        p.setPen(c_black)
        p.setFont(font(10, QFont.DemiBold))
        p.drawText(QRectF(M + CW * 0.08, y, CW * 0.24, row_h), Qt.AlignLeft | Qt.AlignVCenter | Qt.TextWordWrap, cat)
        p.setPen(c_dark)
        p.setFont(font(9.8))
        p.drawText(QRectF(M + CW * 0.33, y, CW * 0.44, row_h), Qt.AlignLeft | Qt.AlignVCenter | Qt.TextWordWrap,
                   desc or "-")
        p.setPen(c_black)
        p.setFont(font(10.5, QFont.DemiBold))
        p.drawText(QRectF(M + CW * 0.78, y, CW * 0.22 - 30, row_h), Qt.AlignRight | Qt.AlignVCenter,
                   validators.inr(amt))
        y += row_h
        hline(y, c_soft2 if idx < len(norm_items) else c_line, 1.5 if idx < len(norm_items) else 2.2)

    y += 46

    # ---------------------------------------------------- 5. SUMMARY TOTALS
    sum_w = CW * 0.54
    sx = M + CW - sum_w
    summary_lines: list[tuple[str, str]] = [
        ("Current Bill Total", validators.inr(billed)),
    ]
    if previous_balance > 0.004:
        summary_lines.append(("Previous Balance (Old Dues)", validators.inr(previous_balance)))
        summary_lines.append(("Total Payable", validators.inr(billed + previous_balance)))
    if received > 0.004:
        summary_lines.append(("Less: Amount Received", f"- {validators.inr(received)}"))

    for lbl_t, val_t in summary_lines:
        p.setPen(c_muted)
        p.setFont(font(9.8))
        p.drawText(QRectF(sx, y, sum_w * 0.68, 52), Qt.AlignLeft | Qt.AlignVCenter, lbl_t)
        p.setPen(c_black)
        p.setFont(font(10.2, QFont.DemiBold))
        p.drawText(QRectF(sx + sum_w * 0.68, y, sum_w * 0.32, 52), Qt.AlignRight | Qt.AlignVCenter, val_t)
        y += 58

    y += 16
    bal_rect = QRectF(sx - 26, y, sum_w + 26, 98)
    rounded_box(bal_rect, 18, c_black)
    p.setPen(c_white)
    p.setFont(font(10, QFont.Bold))
    bal_label = "NET BALANCE DUE" if total_due > 0.004 else "BALANCE DUE (SETTLED)"
    p.drawText(QRectF(sx, y, sum_w * 0.60, 98), Qt.AlignLeft | Qt.AlignVCenter, bal_label)
    p.setFont(font(12.8, QFont.Bold))
    p.drawText(QRectF(sx + sum_w * 0.56, y, sum_w * 0.44 - 16, 98), Qt.AlignRight | Qt.AlignVCenter,
               validators.inr(max(total_due, 0.0)))
    y += 136

    if not is_paid:
        p.setPen(c_muted)
        p.setFont(font(9, QFont.Medium))
        p.drawText(QRectF(M, y, CW, 48), Qt.AlignRight | Qt.AlignVCenter,
                   f"In words:  {inr_words(max(total_due, 0.0) if total_due > 0 else billed)}")
        y += 78
    else:
        y += 32

    # ---------------------------------------------------- 6. PAYMENT HISTORY
    footer_top = H - M - 280
    if payments and y + 170 < footer_top:
        p.setPen(c_black)
        p.setFont(font(9.8, QFont.Bold))
        p.drawText(QRectF(M, y, CW, 48), Qt.AlignLeft | Qt.AlignVCenter, "PAYMENT TRANSACTIONS")
        y += 56
        ph = 66
        rounded_box(QRectF(M, y, CW, ph), 14, c_soft)
        p.setPen(c_muted)
        p.setFont(font(8.5, QFont.Bold))
        p.drawText(QRectF(M + 28, y, CW * 0.20, ph), Qt.AlignLeft | Qt.AlignVCenter, "DATE")
        p.drawText(QRectF(M + CW * 0.22, y, CW * 0.18, ph), Qt.AlignLeft | Qt.AlignVCenter, "MODE")
        p.drawText(QRectF(M + CW * 0.40, y, CW * 0.38, ph), Qt.AlignLeft | Qt.AlignVCenter, "REMARKS")
        p.drawText(QRectF(M + CW * 0.78, y, CW * 0.22 - 28, ph), Qt.AlignRight | Qt.AlignVCenter, "AMOUNT")
        y += ph + 8

        for pay in payments:
            prh = 64
            if y + prh > footer_top - 24:
                break
            p.setPen(c_dark)
            p.setFont(font(9.3))
            p.drawText(QRectF(M + 28, y, CW * 0.20, prh), Qt.AlignLeft | Qt.AlignVCenter, _fmt_date(pay["date"]))
            p.drawText(QRectF(M + CW * 0.22, y, CW * 0.18, prh), Qt.AlignLeft | Qt.AlignVCenter, pay["mode"] or "Cash")
            p.drawText(QRectF(M + CW * 0.40, y, CW * 0.38, prh), Qt.AlignLeft | Qt.AlignVCenter, pay["note"] or "-")
            p.setPen(c_black)
            p.setFont(font(9.3, QFont.DemiBold))
            p.drawText(QRectF(M + CW * 0.78, y, CW * 0.22 - 28, prh), Qt.AlignRight | Qt.AlignVCenter,
                       validators.inr(float(pay["amount"])))
            y += prh
            hline(y, c_soft2, 1.5)

    # ---------------------------------------------------- 7. FOOTER + SIGNATURE
    fy = footer_top
    hline(fy, c_line, 2.0)
    p.setPen(c_muted)
    p.setFont(font(8.5))
    p.drawText(QRectF(M, fy + 36, CW * 0.56, 140), Qt.AlignLeft | Qt.TextWordWrap,
               "Thank you for your trust in our practice.\n"
               "Please quote the Bill / Receipt number in all correspondence.")

    sig_x = M + CW * 0.60
    sig_w = CW * 0.40
    p.setPen(c_black)
    p.setFont(font(9.5, QFont.Bold))
    p.drawText(QRectF(sig_x, fy + 28, sig_w, 44), Qt.AlignRight, f"For {firm_name}")

    if signature_path and Path(signature_path).exists():
        spm = QPixmap(str(signature_path))
        if not spm.isNull():
            max_w, max_h = 460.0, 122.0
            scaled = spm.scaled(int(max_w), int(max_h), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            sw, sh = float(scaled.width()), float(scaled.height())
            sx_img = M + CW - sw
            sy_img = fy + 80 + (max_h - sh) / 2.0
            p.drawPixmap(QRectF(sx_img, sy_img, sw, sh), scaled, QRectF(0, 0, sw, sh))

    line_y = fy + 214
    p.setPen(QPen(c_line, 2.0))
    p.drawLine(int(sig_x + 110), int(line_y), int(M + CW), int(line_y))
    p.setPen(c_muted)
    p.setFont(font(8.5))
    p.drawText(QRectF(sig_x, line_y + 14, sig_w, 42), Qt.AlignRight, "Authorised Signatory")

    p.end()
    return dest
