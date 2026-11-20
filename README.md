# Sikdar Consultancy – Income Tax Practice Manager

A Windows desktop app for an Indian income-tax consultancy. Python + PySide6 (Qt), SQLite, fully offline.

## Run

```bat
pip install -r requirements.txt
python main.py          :: or double-click run.bat
build.bat               :: builds dist\Sikdar Consultancy\Sikdar Consultancy.exe
```

## Features

| Area | What it does |
|---|---|
| **Owner login** | First launch asks you to create the owner ID + password. Scrypt-hashed, 5-attempt lockout (30 s), auto-lock when idle (configurable), `Ctrl+L` to sign out. |
| **Client registration** | Name, phone, email, **photo upload** (auto-cropped), Aadhaar, PAN, DOB, address, **Income-Tax portal password**, status, notes. PAN / Aadhaar / phone / email validated; duplicate PAN blocked. |
| **Secure portal passwords** | Encrypted (Fernet) – a random data key is wrapped by your owner password, so they're unreadable without logging in. Reveal / copy buttons; clipboard auto-clears after 30 s. |
| **Per-client folders** | Each client gets **Returns, Computation, Other**. Add, rename, delete folders; upload by button or drag-and-drop; open, rename, delete files. Deletes go to the Recycle Bin. Real folders on disk. |
| **Dashboard** | Client / document / task / outstanding-fee stats, upcoming deadlines, **Income Tax Quick Links** (e-Filing, CBDT Calendar, e-Pay Tax, TRACES, GST, PAN, Refund), recent clients & activity. |
| **Deadlines & tasks** | **Editable statutory calendar** (double-click any advance tax, ITR, audit or TDS date to extend or reset it) + your own tasks linked to clients. |
| **Fees & payments** | Billing per client / FY, record part-payments, paid / partial / pending status, Indian ₹ formatting. |
| **Settings** | Firm name, change owner ID/password, default folder template for new clients, backup / restore (zip), CSV export. |

Shortcuts: `Ctrl+N` new client · `Ctrl+F` search clients · `Ctrl+L` lock.

## Where is my data?

`Documents\Sikdar Consultancy\`

```
Data\sikdar.db       database
Data\photos\         client photos
Clients\0001 - Name\Returns | Computation | Other
Backups\             suggested backup location
```

**Back up regularly** (Settings → Back up now). Copy the zip to a pen-drive / cloud drive.

> The statutory dates are the standard due dates; CBDT often extends them – always confirm on incometax.gov.in.
