"""Application context: ties the database, vault, and storage together."""
from __future__ import annotations

import csv
import json
import shutil
import sqlite3
import tempfile
import time
import uuid
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QImage

from . import paths, security, storage, validators
from .db import Database


class AuthError(Exception):
    pass


class AppContext:
    MAX_ATTEMPTS = 5
    LOCKOUT_SECONDS = 30

    def __init__(self) -> None:
        paths.ensure_dirs()
        self.db = Database(paths.db_path())
        self.vault: security.Vault | None = None
        self._failed = 0
        self._locked_until = 0.0

    # ------------------------------------------------------------ auth
    def is_setup(self) -> bool:
        return bool(self.db.get_meta("owner_id"))

    def setup_owner(self, owner_id: str, password: str, firm_name: str,
                    recovery_code: str = "", recovery_hint: str = "") -> None:
        rec, vault = security.create_record(password)
        meta = {
            "owner_id": owner_id.strip().lower(),
            "pw_salt": rec.salt, "pw_verifier": rec.verifier, "pw_wrapped": rec.wrapped_key,
            "firm_name": firm_name.strip() or paths.APP_NAME,
            "autolock_minutes": "15",
            "default_folders": json.dumps(storage.DEFAULT_FOLDERS),
        }
        if recovery_code.strip():
            rrec, _ = security.create_record(recovery_code.strip(), vault.data_key)
            meta.update({
                "rec_salt": rrec.salt, "rec_verifier": rrec.verifier,
                "rec_wrapped": rrec.wrapped_key, "rec_hint": recovery_hint.strip(),
            })
        self.db.set_meta_many(meta)
        self.vault = vault
        self.db.log("Owner account created")

    def _record(self) -> security.VaultRecord:
        return security.VaultRecord(
            self.db.get_meta("pw_salt"), self.db.get_meta("pw_verifier"),
            self.db.get_meta("pw_wrapped"))

    def lock_remaining(self) -> int:
        return max(0, int(self._locked_until - time.time() + 0.999))

    def login(self, owner_id: str, password: str) -> None:
        if self.lock_remaining():
            raise AuthError(f"Too many attempts. Try again in {self.lock_remaining()} seconds.")
        ok_id = owner_id.strip().lower() == self.db.get_meta("owner_id")
        vault = security.unlock(password, self._record()) if ok_id else None
        if not ok_id:
            security.unlock(password, self._record())  # keep timing similar
        if vault is None:
            self._failed += 1
            if self._failed >= self.MAX_ATTEMPTS:
                self._failed = 0
                self._locked_until = time.time() + self.LOCKOUT_SECONDS
                raise AuthError(f"Too many attempts. Locked for {self.LOCKOUT_SECONDS} seconds.")
            left = self.MAX_ATTEMPTS - self._failed
            raise AuthError(f"Incorrect ID or password. {left} attempt(s) left.")
        self._failed = 0
        self.vault = vault
        self.db.log("Owner signed in")

    def logout(self) -> None:
        self.vault = None

    def owner_id(self) -> str:
        return self.db.get_meta("owner_id")

    def firm_name(self) -> str:
        return self.db.get_meta("firm_name", paths.APP_NAME)

    def change_credentials(self, current_password: str, new_id: str, new_password: str | None) -> None:
        vault = security.unlock(current_password, self._record())
        if vault is None:
            raise AuthError("Current password is incorrect.")
        meta = {"owner_id": new_id.strip().lower()}
        if new_password:
            rec, vault = security.create_record(new_password, vault.data_key)
            meta.update({"pw_salt": rec.salt, "pw_verifier": rec.verifier,
                         "pw_wrapped": rec.wrapped_key})
        self.db.set_meta_many(meta)
        self.vault = vault
        self.db.log("Owner credentials updated")

    # ------------------------------------------------- password recovery
    def has_recovery_code(self) -> bool:
        return bool(self.db.get_meta("rec_verifier"))

    def recovery_hint(self) -> str:
        return self.db.get_meta("rec_hint", "")

    def set_recovery_code(self, current_password: str, code: str, hint: str) -> None:
        vault = security.unlock(current_password, self._record())
        if vault is None:
            raise AuthError("Current owner password is incorrect.")
        code = code.strip()
        if len(code) < 4:
            raise AuthError("Recovery code must be at least 4 characters.")
        rrec, _ = security.create_record(code, vault.data_key)
        self.db.set_meta_many({
            "rec_salt": rrec.salt,
            "rec_verifier": rrec.verifier,
            "rec_wrapped": rrec.wrapped_key,
            "rec_hint": hint.strip(),
        })
        self.db.log("Updated password recovery code & hint")

    def remove_recovery_code(self, current_password: str) -> None:
        if not self.verify_owner_password(current_password):
            raise AuthError("Current owner password is incorrect.")
        self.db.set_meta_many({
            "rec_salt": "", "rec_verifier": "", "rec_wrapped": "", "rec_hint": "",
        })
        self.db.log("Removed password recovery code")

    def reset_password_with_recovery(self, code: str, new_password: str) -> None:
        if not self.has_recovery_code():
            raise AuthError("No recovery code is configured.")
        rrec = security.VaultRecord(
            self.db.get_meta("rec_salt"),
            self.db.get_meta("rec_verifier"),
            self.db.get_meta("rec_wrapped"),
        )
        vault = security.unlock(code.strip(), rrec)
        if vault is None:
            raise AuthError("Incorrect recovery code.")
        if len(new_password) < 8:
            raise AuthError("New password must be at least 8 characters.")
        # Re-wrap the SAME data_key so all encrypted client portal passwords stay readable!
        pw_rec, new_vault = security.create_record(new_password, vault.data_key)
        self.db.set_meta_many({
            "pw_salt": pw_rec.salt,
            "pw_verifier": pw_rec.verifier,
            "pw_wrapped": pw_rec.wrapped_key,
        })
        self._failed = 0
        self._locked_until = 0.0
        self.vault = new_vault
        self.db.log("Owner password reset using recovery code")

    # --------------------------------------------------------- settings
    def default_folders(self) -> list[str]:
        try:
            lst = json.loads(self.db.get_meta("default_folders", ""))
            return [str(x) for x in lst] or list(storage.DEFAULT_FOLDERS)
        except (ValueError, TypeError):
            return list(storage.DEFAULT_FOLDERS)

    def set_default_folders(self, folders: list[str]) -> None:
        self.db.set_meta("default_folders", json.dumps(folders))

    def autolock_minutes(self) -> int:
        try:
            return int(self.db.get_meta("autolock_minutes", "15"))
        except ValueError:
            return 15

    # ----------------------------------------------------------- photos
    @staticmethod
    def photo_path(name: str) -> Path | None:
        if not name:
            return None
        p = paths.photos_dir() / name
        return p if p.exists() else None

    @staticmethod
    def save_photo(src: str) -> str:
        """Centre-crop to a square, shrink to 512px and store as JPEG."""
        img = QImage(src)
        if img.isNull():
            raise ValueError("That file is not a valid image.")
        side = min(img.width(), img.height())
        img = img.copy(QRect((img.width() - side) // 2, (img.height() - side) // 2, side, side))
        if side > 512:
            img = img.scaled(512, 512, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        name = f"{uuid.uuid4().hex}.jpg"
        img.save(str(paths.photos_dir() / name), "JPG", 90)
        return name

    @staticmethod
    def remove_photo(name: str) -> None:
        if name:
            (paths.photos_dir() / name).unlink(missing_ok=True)

    # -------------------------------------------------------- signature
    @staticmethod
    def signature_path() -> Path | None:
        p = paths.signature_path()
        return p if p.exists() else None

    @staticmethod
    def save_signature(src: str) -> Path:
        """Scale signature image cleanly (preserving transparency) and save as PNG."""
        img = QImage(src)
        if img.isNull():
            raise ValueError("That file is not a valid image.")
        if img.width() > 640 or img.height() > 260:
            img = img.scaled(640, 260, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        dst = paths.signature_path()
        dst.parent.mkdir(parents=True, exist_ok=True)
        img.save(str(dst), "PNG")
        return dst

    @staticmethod
    def remove_signature() -> None:
        paths.signature_path().unlink(missing_ok=True)

    # ---------------------------------------------------------- clients
    def add_client(self, data: dict[str, Any], photo_src: str | None) -> int:
        assert self.vault
        row = dict(data)
        row["portal_password"] = self.vault.encrypt(row.get("portal_password", ""))
        row["gst_password"] = self.vault.encrypt(row.get("gst_password", ""))
        row["photo"] = self.save_photo(photo_src) if photo_src else ""
        row["folder_name"] = f"tmp-{uuid.uuid4().hex[:8]}"
        cid = self.db.add_client(row)
        folder = storage.make_client_folder_name(cid, row["name"])
        try:
            storage.ensure_client(folder, self.default_folders())
        except OSError:
            self.db.delete_client(cid)
            raise
        self.db.update_client(cid, {"folder_name": folder})
        self.db.log(f"Registered client {row['name']}")
        return cid

    def update_client(self, cid: int, data: dict[str, Any], photo_src: str | None,
                      remove_photo: bool) -> None:
        assert self.vault
        old = self.db.get_client(cid)
        if old is None:
            return
        row = dict(data)
        row["portal_password"] = self.vault.encrypt(row.get("portal_password", ""))
        row["gst_password"] = self.vault.encrypt(row.get("gst_password", ""))
        if photo_src:
            row["photo"] = self.save_photo(photo_src)
            self.remove_photo(old["photo"])
        elif remove_photo:
            row["photo"] = ""
            self.remove_photo(old["photo"])
        new_folder = storage.make_client_folder_name(cid, row["name"])
        if new_folder != old["folder_name"]:
            storage.rename_client_root(old["folder_name"], new_folder)
            row["folder_name"] = new_folder
        self.db.update_client(cid, row)
        self.db.log(f"Updated client {row['name']}")

    def delete_client(self, cid: int) -> None:
        c = self.db.get_client(cid)
        if c is None:
            return
        storage.delete_client_root(c["folder_name"])
        self.remove_photo(c["photo"])
        self.db.delete_client(cid)
        self.db.log(f"Deleted client {c['name']}")

    def portal_password(self, client_row) -> str:
        return self.vault.decrypt(client_row["portal_password"]) if self.vault else ""

    def gst_password(self, client_row) -> str:
        val = client_row["gst_password"] if "gst_password" in client_row.keys() else ""
        return self.vault.decrypt(val) if (self.vault and val) else ""

    # ---------------------------------------------------- data tools
    def export_clients_csv(self, dest: str, include_passwords: bool) -> int:
        rows = self.db.list_clients()
        with open(dest, "w", newline="", encoding="utf-8-sig") as fh:
            w = csv.writer(fh)
            head = ["Name", "Phone", "Email", "PAN", "Aadhaar", "GST Portal ID", "DOB", "Address", "Status"]
            if include_passwords:
                head += ["ITR Portal Password", "GST Portal Password"]
            w.writerow(head)
            for r in rows:
                gst_id = r["gst_id"] if "gst_id" in r.keys() else ""
                line = [r["name"], r["phone"], r["email"], r["pan"],
                        validators.format_aadhar(r["aadhar"]), gst_id, r["dob"], r["address"], r["status"]]
                if include_passwords:
                    line += [self.portal_password(r), self.gst_password(r)]
                w.writerow(line)
        return len(rows)

    def backup(self, dest: str) -> dict[str, int]:
        """Create a complete, atomic .zip backup of everything (DB + transactions + files)."""
        self.db.conn.commit()
        base = paths.home_dir()
        counts = {
            "clients": self.db.count_clients(),
            "fees": int(self.db.conn.execute("SELECT COUNT(*) FROM fees").fetchone()[0]),
            "payments": int(self.db.conn.execute("SELECT COUNT(*) FROM fee_payments").fetchone()[0]),
            "tasks": int(self.db.conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]),
            "files": 0,
        }
        # Take an atomic SQLite snapshot using the online backup API
        tmp_dir = Path(tempfile.mkdtemp(prefix="sikdar_bk_"))
        snap_db = tmp_dir / "sikdar.db"
        try:
            dst_conn = sqlite3.connect(str(snap_db))
            try:
                self.db.conn.backup(dst_conn)
                dst_conn.commit()
            finally:
                dst_conn.close()

            with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
                z.write(snap_db, "Data/sikdar.db")
                for sub in ("Data", "Clients", "Bills & Receipts"):
                    root = base / sub
                    if not root.exists():
                        continue
                    for p in sorted(root.rglob("*")):
                        rel = p.relative_to(base).as_posix()
                        if p.is_dir():
                            # Preserve empty client folders (Returns, Computation, Other, etc.)
                            z.writestr(rel.rstrip("/") + "/", "")
                        elif p.is_file():
                            if rel == "Data/sikdar.db" or p.name.endswith(("-wal", "-shm", "-journal")):
                                continue
                            z.write(p, rel)
                            counts["files"] += 1
                manifest = {
                    "app": paths.APP_NAME,
                    "version": paths.APP_VERSION,
                    "created": datetime.now().isoformat(timespec="seconds"),
                    "counts": counts,
                }
                z.writestr("MANIFEST.json", json.dumps(manifest, indent=2))
                z.writestr(
                    "MANIFEST.txt",
                    f"{paths.APP_NAME} full backup\n"
                    f"Created: {datetime.now():%Y-%m-%d %H:%M:%S}\n"
                    f"Clients: {counts['clients']} | Fees: {counts['fees']} | "
                    f"Transactions: {counts['payments']} | Tasks: {counts['tasks']} | "
                    f"Files: {counts['files']}\n",
                )
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        self.db.set_meta("last_backup", datetime.now().strftime("%d %b %Y, %I:%M %p"))
        self.db.log(f"Created full backup ({counts['clients']} clients, {counts['payments']} transactions)")
        return counts

    def restore(self, src: str) -> None:
        """Replace Data/, Clients/, and Bills & Receipts/ from a backup zip and reload DB."""
        with zipfile.ZipFile(src) as z:
            names = z.namelist()
            if "Data/sikdar.db" not in names:
                raise ValueError("This is not a valid Sikdar Consultancy backup file.")
            for n in names:
                if n.startswith("/") or ".." in Path(n).parts:
                    raise ValueError("Backup file contains unsafe paths.")
            self.db.close()
            self.vault = None
            base = paths.home_dir()
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            for sub in ("Data", "Clients", "Bills & Receipts"):
                cur = base / sub
                if cur.exists():
                    cur.rename(base / f"{sub}.before-restore-{stamp}")
            z.extractall(base)
        paths.ensure_dirs()
        self.db = Database(paths.db_path())

    def verify_owner_password(self, password: str) -> bool:
        return security.unlock(password, self._record()) is not None

    def clear_user_data(self, password: str) -> None:
        """Wipe all client records, documents, photos, fees, transactions, tasks & PDFs.
        Preserves admin credentials, firm profile, signature & default folders."""
        if not self.verify_owner_password(password):
            raise AuthError("Incorrect owner password.")
        # Delete all client-related DB tables
        for tbl in ("fee_items", "fee_payments", "fees", "tasks", "clients",
                    "statutory_overrides", "statutory_custom", "activity"):
            self.db.conn.execute(f"DELETE FROM {tbl}")
        self.db.conn.execute("DELETE FROM sqlite_sequence WHERE name IN "
                             "('fee_items','fee_payments','fees','tasks','clients','statutory_custom','activity')")
        self.db.conn.commit()
        # Move client folders, photos, and generated bills/receipts to Recycle Bin
        for folder in (paths.clients_dir(), paths.photos_dir(), paths.bills_dir()):
            if folder.exists():
                for child in list(folder.iterdir()):
                    storage._recycle(child)
        paths.ensure_dirs()
        self.db.log("Cleared all client & transaction data")

    def clear_all_data(self, password: str) -> None:
        """Factory reset: wipe all client data, transactions, files AND admin account/settings."""
        if not self.verify_owner_password(password):
            raise AuthError("Incorrect owner password.")
        self.db.close()
        self.vault = None
        for folder in (paths.clients_dir(), paths.bills_dir(), paths.data_dir()):
            if folder.exists():
                storage._recycle(folder)
        paths.ensure_dirs()
        self.db = Database(paths.db_path())
