"""Filesystem locations used by the application.

Everything lives in a single, easy-to-back-up folder:

    Documents/Sikdar Consultancy/
        Data/      -> sikdar.db, photos/
        Clients/   -> one folder per client (Returns / Computation / Other ...)
        Backups/   -> zip backups
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "Sikdar Consultancy"
APP_VERSION = "1.1.0"


def resource_path(rel: str) -> Path:
    """Resolve a bundled asset path in both dev and PyInstaller builds."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base / rel


def home_dir() -> Path:
    override = os.environ.get("SIKDAR_HOME")
    base = Path(override) if override else Path.home() / "Documents" / APP_NAME
    return base


def data_dir() -> Path:
    return home_dir() / "Data"


def clients_dir() -> Path:
    return home_dir() / "Clients"


def photos_dir() -> Path:
    return data_dir() / "photos"


def backups_dir() -> Path:
    return home_dir() / "Backups"


def bills_dir() -> Path:
    return home_dir() / "Bills & Receipts"


def db_path() -> Path:
    return data_dir() / "sikdar.db"


def signature_path() -> Path:
    return data_dir() / "signature.png"


def ensure_dirs() -> None:
    for d in (data_dir(), clients_dir(), photos_dir(), backups_dir(), bills_dir()):
        d.mkdir(parents=True, exist_ok=True)
