"""Per-client document storage on the real filesystem.

Each client owns a directory under Clients/. Directories directly inside it are
the client's folders (Returns, Computation, Other by default; the owner can add,
rename or delete them). Deletions go to the Windows Recycle Bin when possible.
"""
from __future__ import annotations

import ctypes
import os
import re
import shutil
import subprocess
import sys
from ctypes import wintypes
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from . import paths

DEFAULT_FOLDERS = ["Returns", "Computation", "Other"]
_INVALID = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)),
             *(f"LPT{i}" for i in range(1, 10))}


class StorageError(Exception):
    pass


@dataclass
class FileInfo:
    name: str
    size: int
    modified: datetime
    path: Path


def clean_name(name: str, what: str = "Name") -> str:
    name = (name or "").strip()
    if not name:
        raise StorageError(f"{what} cannot be empty.")
    if _INVALID.search(name):
        raise StorageError(f'{what} cannot contain any of these characters:  < > : " / \\ | ? *')
    if name.endswith((".", " ")):
        raise StorageError(f"{what} cannot end with a dot or space.")
    if name.split(".")[0].upper() in _RESERVED:
        raise StorageError(f"'{name}' is a reserved Windows name.")
    if len(name) > 100:
        raise StorageError(f"{what} is too long (max 100 characters).")
    return name


def make_client_folder_name(client_id_hint: int, name: str) -> str:
    base = _INVALID.sub("", name).strip(" .") or "Client"
    return f"{client_id_hint:04d} - {base[:60].strip(' .')}"


def client_root(folder_name: str) -> Path:
    return paths.clients_dir() / folder_name


def ensure_client(folder_name: str, folders: list[str] | None = None) -> Path:
    root = client_root(folder_name)
    root.mkdir(parents=True, exist_ok=True)
    for f in (folders if folders is not None else DEFAULT_FOLDERS):
        (root / f).mkdir(exist_ok=True)
    return root


def rename_client_root(old: str, new: str) -> None:
    src, dst = client_root(old), client_root(new)
    if old == new:
        return
    if dst.exists():
        raise StorageError("A client folder with that name already exists.")
    if src.exists():
        src.rename(dst)
    else:
        dst.mkdir(parents=True)


def list_folders(folder_name: str) -> list[tuple[str, int]]:
    root = client_root(folder_name)
    if not root.exists():
        return []
    out = []
    for d in sorted((p for p in root.iterdir() if p.is_dir()), key=lambda p: p.name.lower()):
        out.append((d.name, sum(1 for f in d.iterdir() if f.is_file())))
    return out


def add_folder(folder_name: str, name: str) -> str:
    name = clean_name(name, "Folder name")
    target = client_root(folder_name) / name
    if target.exists():
        raise StorageError(f"A folder named '{name}' already exists.")
    target.mkdir(parents=True)
    return name


def rename_folder(folder_name: str, old: str, new: str) -> str:
    new = clean_name(new, "Folder name")
    root = client_root(folder_name)
    src, dst = root / old, root / new
    if old == new:
        return new
    if dst.exists() and old.lower() != new.lower():
        raise StorageError(f"A folder named '{new}' already exists.")
    src.rename(dst)
    return new


def delete_folder(folder_name: str, name: str) -> None:
    _recycle(client_root(folder_name) / name)


def list_files(folder_name: str, folder: str) -> list[FileInfo]:
    d = client_root(folder_name) / folder
    if not d.exists():
        return []
    files = []
    for p in d.iterdir():
        if p.is_file():
            st = p.stat()
            files.append(FileInfo(p.name, st.st_size, datetime.fromtimestamp(st.st_mtime), p))
    files.sort(key=lambda f: f.modified, reverse=True)
    return files


def _unique(target: Path) -> Path:
    if not target.exists():
        return target
    stem, suffix, i = target.stem, target.suffix, 2
    while True:
        cand = target.with_name(f"{stem} ({i}){suffix}")
        if not cand.exists():
            return cand
        i += 1


def add_files(folder_name: str, folder: str, sources: list[str]) -> int:
    dest = client_root(folder_name) / folder
    dest.mkdir(parents=True, exist_ok=True)
    n = 0
    for s in sources:
        sp = Path(s)
        if sp.is_file():
            shutil.copy2(sp, _unique(dest / sp.name))
            n += 1
    return n


def rename_file(folder_name: str, folder: str, old: str, new: str) -> None:
    new = clean_name(new, "File name")
    d = client_root(folder_name) / folder
    if (d / new).exists() and old.lower() != new.lower():
        raise StorageError(f"A file named '{new}' already exists.")
    (d / old).rename(d / new)


def delete_file(path: Path) -> None:
    _recycle(path)


def open_path(path: Path) -> None:
    if sys.platform == "win32":
        os.startfile(str(path))  # noqa: S606
    else:  # pragma: no cover - dev convenience
        subprocess.Popen(["xdg-open", str(path)])


def reveal(path: Path) -> None:
    if sys.platform == "win32":
        if path.is_file():
            subprocess.Popen(["explorer", "/select,", str(path)])
        else:
            os.startfile(str(path))  # noqa: S606
    else:  # pragma: no cover
        subprocess.Popen(["xdg-open", str(path if path.is_dir() else path.parent)])


# ----------------------------------------------------------- recycle bin
class _SHFILEOPSTRUCTW(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND), ("wFunc", wintypes.UINT),
        ("pFrom", wintypes.LPCWSTR), ("pTo", wintypes.LPCWSTR),
        ("fFlags", ctypes.c_ushort), ("fAnyOperationsAborted", wintypes.BOOL),
        ("hNameMappings", ctypes.c_void_p), ("lpszProgressTitle", wintypes.LPCWSTR),
    ]


def _recycle(path: Path) -> None:
    """Move to Recycle Bin (Windows), falling back to permanent delete."""
    if not path.exists():
        return
    if sys.platform == "win32":
        FO_DELETE, FOF_ALLOWUNDO, FOF_NOCONFIRMATION, FOF_SILENT, FOF_NOERRORUI = (
            3, 0x40, 0x10, 0x4, 0x400)
        op = _SHFILEOPSTRUCTW()
        op.wFunc = FO_DELETE
        op.pFrom = str(path.resolve()) + "\0\0"
        op.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT | FOF_NOERRORUI
        try:
            if ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op)) == 0 and not path.exists():
                return
        except Exception:
            pass
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=True)
    else:
        path.unlink(missing_ok=True)


def delete_client_root(folder_name: str) -> None:
    _recycle(client_root(folder_name))


def human_size(n: int) -> str:
    size = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{int(size)} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{n} B"


def copy_files_to_clipboard(file_paths: list[Path]) -> None:
    """Copy local file paths onto the OS clipboard so Ctrl+V attaches them in Gmail/Outlook."""
    from PySide6.QtCore import QMimeData, QUrl
    from PySide6.QtGui import QGuiApplication

    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(Path(p).resolve())) for p in file_paths if Path(p).exists()])
    QGuiApplication.clipboard().setMimeData(mime)


def open_email_draft(to_email: str, subject: str, body: str, via: str = "mailto") -> None:
    """Open a pre-addressed email compose window (default Mail app or Gmail Web)."""
    from urllib.parse import quote
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QDesktopServices

    to_q = quote(to_email.strip())
    su_q = quote(subject)
    bd_q = quote(body)
    if via == "gmail":
        url = f"https://mail.google.com/mail/?view=cm&fs=1&to={to_q}&su={su_q}&body={bd_q}"
    else:
        url = f"mailto:{to_q}?subject={su_q}&body={bd_q}"
    QDesktopServices.openUrl(QUrl(url))
