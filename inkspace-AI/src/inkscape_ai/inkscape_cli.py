"""Run Inkscape CLI with export/actions; used by the bridge."""

import os
import platform
import shutil
import signal
import subprocess
from pathlib import Path

from .bridge_config import INKSCAPE_BIN_ENV

try:
    from filelock import FileLock
except ImportError:
    FileLock = None


def resolve_inkscape() -> str:
    override = os.getenv(INKSCAPE_BIN_ENV)
    if override:
        p = Path(override).expanduser()
        if p.is_file():
            return str(p.resolve())
        res = shutil.which(override)
        if res:
            return res
        raise FileNotFoundError(f"Inkscape not found at {override}")
    for name in ("inkscape", "inkscape.exe"):
        res = shutil.which(name)
        if res:
            return res
    raise FileNotFoundError("Inkscape not found. Set INKSCAPE_BIN or add it to PATH.")


def _handle_timeout(proc: subprocess.Popen) -> None:
    if platform.system() != "Windows":
        os.killpg(proc.pid, signal.SIGTERM)
    else:
        proc.terminate()
    try:
        proc.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.communicate()


def run_inkscape(
    args: list[str],
    timeout_seconds: int = 120,
    lock_path: Path | None = None,
) -> tuple[bytes, bytes]:
    exe = resolve_inkscape()
    cmd = [exe] + args
    env = os.environ.copy()
    env["DISPLAY"] = ""

    if platform.system() != "Windows":
        popen_kw: dict = {"preexec_fn": os.setsid, "env": env}
    else:
        popen_kw = {"creationflags": 0x00000010, "env": env}

    def run() -> tuple[bytes, bytes]:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **popen_kw)
        try:
            out, err = proc.communicate(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            _handle_timeout(proc)
            raise TimeoutError("Inkscape timed out") from None
        if proc.returncode != 0:
            raise RuntimeError(f"Inkscape failed: {err.decode('utf-8', errors='replace')}")
        return out, err

    if lock_path and FileLock is not None:
        lock_file = lock_path.parent / f"{lock_path.name}.lock"
        with FileLock(str(lock_file)):
            return run()
    return run()
