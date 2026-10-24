from __future__ import annotations

import hashlib
import json
import os
import tempfile
import threading
import time
from pathlib import Path
from typing import Protocol

import keyring
from cryptography.fernet import Fernet, InvalidToken
from keyring.errors import PasswordDeleteError


SERVICE_NAME = 'Cofi Studio'
GOOGLE_FLOW_SESSION_PREFIX = 'google-flow-session:'
GOOGLE_FLOW_KEY_PREFIX = 'google-flow-key:'


class KeyringBackend(Protocol):
    def get_password(self, service: str, username: str) -> str | None: ...

    def set_password(self, service: str, username: str, password: str) -> None: ...

    def delete_password(self, service: str, username: str) -> None: ...


class KeyringSecretStore:
    def __init__(
        self,
        *,
        keyring_backend: KeyringBackend | None = None,
        storage_dir: str | Path | None = None,
    ):
        self._keyring = keyring_backend or keyring
        self._storage_dir = Path(storage_dir) if storage_dir is not None else Path.cwd() / 'data' / 'secrets' / 'google-flow'
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._write_lock = threading.RLock()

    def _session_path(self, account_id: str) -> Path:
        safe_name = hashlib.sha256(account_id.encode('utf-8')).hexdigest()
        return self._storage_dir / f'{safe_name}.enc'

    @staticmethod
    def _decode_session(raw: str) -> dict | None:
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            return None
        return value if isinstance(value, dict) else None

    def get_google_session(self, account_id: str) -> dict | None:
        encrypted_path = self._session_path(account_id)
        if encrypted_path.is_file():
            key = self._keyring.get_password(SERVICE_NAME, f'{GOOGLE_FLOW_KEY_PREFIX}{account_id}')
            if not key:
                return None
            try:
                decrypted = Fernet(key.encode('ascii')).decrypt(encrypted_path.read_bytes()).decode('utf-8')
            except (InvalidToken, OSError, ValueError, UnicodeDecodeError):
                return None
            return self._decode_session(decrypted)

        # Backward compatibility for sessions saved by early Cofi Studio builds.
        raw = self._keyring.get_password(SERVICE_NAME, f'{GOOGLE_FLOW_SESSION_PREFIX}{account_id}')
        if not raw:
            return None
        return self._decode_session(raw)

    def _get_or_create_key(self, account_id: str) -> bytes:
        username = f'{GOOGLE_FLOW_KEY_PREFIX}{account_id}'
        existing = self._keyring.get_password(SERVICE_NAME, username)
        if existing:
            return existing.encode('ascii')

        key = Fernet.generate_key()
        self._keyring.set_password(SERVICE_NAME, username, key.decode('ascii'))
        return key

    def _delete_keyring_entry(self, username: str) -> None:
        try:
            self._keyring.delete_password(SERVICE_NAME, username)
        except PasswordDeleteError:
            pass

    def set_google_session(self, account_id: str, session: dict) -> None:
        with self._write_lock:
            key = self._get_or_create_key(account_id)
            payload = json.dumps(session, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
            encrypted = Fernet(key).encrypt(payload)
            destination = self._session_path(account_id)
            temporary: Path | None = None
            try:
                with tempfile.NamedTemporaryFile(
                    mode='wb',
                    dir=self._storage_dir,
                    prefix=f'.{destination.stem}.',
                    suffix='.tmp',
                    delete=False,
                ) as handle:
                    temporary = Path(handle.name)
                    handle.write(encrypted)
                    handle.flush()
                    os.fsync(handle.fileno())

                # Several generation workers can refresh the same account at once.
                # Unique temp files prevent workers/processes from stealing each
                # other's source file; short retries cover transient Windows sharing
                # locks from another atomic replace or security scanner.
                for attempt in range(5):
                    try:
                        os.replace(temporary, destination)
                        temporary = None
                        break
                    except PermissionError:
                        if attempt == 4:
                            raise
                        time.sleep(0.02 * (attempt + 1))
            finally:
                if temporary is not None:
                    try:
                        temporary.unlink()
                    except FileNotFoundError:
                        pass

        # Remove any legacy large keyring blob after the encrypted write succeeds.
        self._delete_keyring_entry(f'{GOOGLE_FLOW_SESSION_PREFIX}{account_id}')

    def delete_google_session(self, account_id: str) -> None:
        session_path = self._session_path(account_id)
        try:
            import stat
            try:
                os.chmod(str(session_path), stat.S_IWRITE)
            except OSError:
                pass
            session_path.unlink()
        except (FileNotFoundError, PermissionError):
            pass
        self._delete_keyring_entry(f'{GOOGLE_FLOW_KEY_PREFIX}{account_id}')
        self._delete_keyring_entry(f'{GOOGLE_FLOW_SESSION_PREFIX}{account_id}')
