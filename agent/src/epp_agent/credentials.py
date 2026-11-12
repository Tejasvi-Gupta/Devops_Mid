"""Credential storage. Tests use memory; Windows uses DPAPI."""

from __future__ import annotations

import ctypes
import json
import os
from ctypes import wintypes
from pathlib import Path


class MemoryStore:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def save(self, key: str, secret: str) -> None:
        self.values[key] = secret

    def load(self, key: str) -> str | None:
        return self.values.get(key)

    def delete(self, key: str) -> None:
        self.values.pop(key, None)


class DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]


def protect(data: bytes) -> bytes:
    return _crypt(data, protect=True)


def unprotect(data: bytes) -> bytes:
    return _crypt(data, protect=False)


def _crypt(data: bytes, protect: bool) -> bytes:
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    buffer = ctypes.create_string_buffer(data)
    incoming = DATA_BLOB(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte)))
    outgoing = DATA_BLOB()
    function = crypt32.CryptProtectData if protect else crypt32.CryptUnprotectData
    if not function(ctypes.byref(incoming), None, None, None, None, 0, ctypes.byref(outgoing)):
        raise OSError("Windows credential protection failed")
    try:
        return ctypes.string_at(outgoing.pbData, outgoing.cbData)
    finally:
        kernel32.LocalFree(outgoing.pbData)


class DpapiStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def _read(self) -> dict:
        if not self.path.exists():
            return {}
        return json.loads(unprotect(self.path.read_bytes()).decode("utf-8"))

    def _write(self, values: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_bytes(protect(json.dumps(values).encode("utf-8")))

    def save(self, key: str, secret: str) -> None:
        values = self._read()
        values[key] = secret
        self._write(values)

    def load(self, key: str) -> str | None:
        return self._read().get(key)

    def delete(self, key: str) -> None:
        values = self._read()
        values.pop(key, None)
        self._write(values)


def default_store() -> MemoryStore | DpapiStore:
    if os.name != "nt":
        return MemoryStore()
    root = Path(os.environ.get("LOCALAPPDATA", ".")) / "EPPAgent"
    return DpapiStore(root / "device.bin")
