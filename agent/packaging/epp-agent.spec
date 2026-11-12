# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the Windows agent.

Build from the repository root on Windows after installing packaging deps:

  backend\\.venv\\Scripts\\python.exe -m pip install pyinstaller httpx
  backend\\.venv\\Scripts\\pyinstaller.exe agent\\packaging\\epp-agent.spec

The built executable lands in agent/dist/epp-agent.exe. This workspace has not
run that build. Prefer a disposable Windows VM for any smoke test that pairs
and runs the agent against a real catalog install.
"""

from pathlib import Path

block_cipher = None
repo = Path(SPECPATH).resolve().parents[1]
agent_src = repo / "agent" / "src"

a = Analysis(
    [str(agent_src / "epp_agent" / "__main__.py")],
    pathex=[str(agent_src)],
    binaries=[],
    datas=[],
    hiddenimports=["epp_agent", "epp_agent.commands", "epp_agent.credentials", "epp_agent.detect", "epp_agent.execute", "epp_agent.loop", "epp_agent.versions"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="epp-agent",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
