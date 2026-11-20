"""Statutory Income-Tax calendar helper and official quick links.

Dates default to the standard statutory due dates, and any entry can be edited
or extended by the owner (persisted in SQLite via `statutory_overrides`).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass
class Statutory:
    key: str
    due: date
    default_due: date
    title: str
    kind: str  # 'ITR' | 'TAX' | 'TDS' | 'AUDIT'
    edited: bool = False
    note: str = ""


@dataclass(frozen=True)
class QuickLink:
    title: str
    subtitle: str
    url: str
    category: str


QUICK_LINKS: list[QuickLink] = [
    QuickLink("Income Tax e-Filing", "ITR, AIS, e-Verify & notices",
              "https://www.incometax.gov.in/iec/foportal/", "Portal"),
    QuickLink("CBDT Tax Calendar", "Official due dates & extensions",
              "https://incometaxindia.gov.in/Pages/deadline.aspx", "Calendar"),
    QuickLink("e-Pay Tax (Challan 280)", "Advance, Self-Assessment & TDS",
              "https://eportal.incometax.gov.in/iec/foservices/#/e-pay-tax-prelogin/user-details", "Payment"),
    QuickLink("TRACES Portal", "Form 16, 16A, 26AS & TDS",
              "https://www.tdscpc.gov.in/", "TDS"),
    QuickLink("Income Tax India", "Acts, Rules & Circulars",
              "https://incometaxindia.gov.in/", "Reference"),
    QuickLink("GST Portal", "Returns, notices & search",
              "https://www.gst.gov.in/", "GST"),
    QuickLink("PAN Services (Protean)", "New PAN, reprint & status",
              "https://www.onlineservices.nsdl.com/paam/endUserRegisterContact.html", "PAN"),
    QuickLink("Refund Status (NSDL)", "Track tax refund dispatch",
              "https://tin.tin.nsdl.com/oltas/refund-status-pan.html", "Refund"),
]


def _ay(year_of_due: int) -> str:
    return f"AY {year_of_due}-{str(year_of_due + 1)[-2:]}"


def upcoming(today: date | None = None, horizon_days: int = 400,
             overrides: dict | None = None) -> list[Statutory]:
    today = today or date.today()
    overrides = overrides or {}
    items: list[Statutory] = []
    for y in (today.year - 1, today.year, today.year + 1):
        fy_label = f"FY {y - 1}-{str(y)[-2:]}"
        defs = [
            (f"{y}-ADV-4", date(y, 3, 15), "Advance Tax - 4th instalment (100%)", "TAX"),
            (f"{y}-ADV-1", date(y, 6, 15), "Advance Tax - 1st instalment (15%)", "TAX"),
            (f"{y}-ADV-2", date(y, 9, 15), "Advance Tax - 2nd instalment (45%)", "TAX"),
            (f"{y}-ADV-3", date(y, 12, 15), "Advance Tax - 3rd instalment (75%)", "TAX"),
            (f"{y}-ITR-NONAUDIT", date(y, 7, 31), f"ITR due - non-audit cases ({_ay(y)}, {fy_label})", "ITR"),
            (f"{y}-AUDIT", date(y, 9, 30), f"Tax audit report due ({_ay(y)})", "AUDIT"),
            (f"{y}-ITR-AUDIT", date(y, 10, 31), f"ITR due - audit cases ({_ay(y)})", "ITR"),
            (f"{y}-ITR-BELATED", date(y, 12, 31), f"Belated / revised return last date ({_ay(y - 1)})", "ITR"),
            (f"{y}-TDS-Q1", date(y, 7, 31), "TDS return - Q1 (Apr-Jun)", "TDS"),
            (f"{y}-TDS-Q2", date(y, 10, 31), "TDS return - Q2 (Jul-Sep)", "TDS"),
            (f"{y}-TDS-Q3", date(y, 1, 31), "TDS return - Q3 (Oct-Dec)", "TDS"),
            (f"{y}-TDS-Q4", date(y, 5, 31), "TDS return - Q4 (Jan-Mar)", "TDS"),
        ]
        for key, def_due, title, kind in defs:
            ov = overrides.get(key)
            if ov:
                try:
                    due = date.fromisoformat(ov["due_date"])
                except ValueError:
                    due = def_due
                items.append(Statutory(
                    key=key, due=due, default_due=def_due,
                    title=ov["title"] or title, kind=kind,
                    edited=True, note=ov["note"] or "",
                ))
            else:
                items.append(Statutory(key=key, due=def_due, default_due=def_due,
                                       title=title, kind=kind))
    out = [s for s in items if -30 <= (s.due - today).days <= horizon_days]
    # Keep upcoming (0..horizon) first, plus recently overdue edited dates if any
    out = [s for s in out if (s.due - today).days >= 0 or s.edited]
    out.sort(key=lambda s: (s.due, s.title))
    return out


def current_fy(today: date | None = None) -> str:
    today = today or date.today()
    start = today.year if today.month >= 4 else today.year - 1
    return f"{start}-{str(start + 1)[-2:]}"


def fy_options(count: int = 6) -> list[str]:
    today = date.today()
    start = today.year if today.month >= 4 else today.year - 1
    return [f"{y}-{str(y + 1)[-2:]}" for y in range(start + 1, start - count, -1)]
