#!/usr/bin/env python3
"""Inkscape extension: Start MCP Server - writes current document path and optionally spawns bridge."""

import os
import subprocess
import sys
import tempfile
import time
import warnings
import json
import uuid
from pathlib import Path

import inkex

warnings.filterwarnings("ignore", category=ResourceWarning, message=".*subprocess.*is still running.*")

_DEBUG_LOG_PATH = r"e:\user\code\MCP-chatbot\debug-3ebe15.log"
_DEBUG_SESSION = "3ebe15"


def _write_live_session_record(config_dir: Path, document_path: str) -> dict:
    session = {
        "version": 1,
        "session_id": f"live-{uuid.uuid4()}",
        "document_path": document_path,
        "lock_status": "confirmed",
        "extension_pid": os.getpid(),
        "started_at": int(time.time() * 1000),
        "updated_at": int(time.time() * 1000),
        "commands_file": str((config_dir / "live_commands.jsonl").resolve()),
        "results_dir": str((config_dir / "live_results").resolve()),
    }
    (config_dir / "live_results").mkdir(parents=True, exist_ok=True)
    (config_dir / "live_session.json").write_text(json.dumps(session, indent=2), encoding="utf-8")
    return session


def _apply_live_command_in_document(svg_root, command: dict) -> dict:
    target = str(command.get("target", "")).strip()
    op = str(command.get("op", "")).strip()
    payload = command.get("payload") or {}
    if not target or not op:
        return {"success": False, "error": "Invalid command: target/op required"}
    node = svg_root.getElementById(target)
    if node is None:
        return {"success": False, "error": f"Element not found: {target}"}
    try:
        if op == "set_color":
            mode = str(payload.get("mode", "fill")).strip().lower()
            color = str(payload.get("color", "")).strip()
            if mode not in ("fill", "stroke") or not color:
                return {"success": False, "error": "set_color requires mode(fill|stroke) and color"}
            node.style[mode] = color
            return {"success": True, "applied": {"op": op, "target": target, "mode": mode, "color": color}}
        if op == "translate":
            dx = float(payload.get("dx", 0))
            dy = float(payload.get("dy", 0))
            existing = node.get("transform") or ""
            node.set("transform", f"{existing} translate({dx},{dy})".strip())
            return {"success": True, "applied": {"op": op, "target": target, "dx": dx, "dy": dy}}
        return {"success": False, "error": f"Unsupported op: {op}"}
    except Exception as e:
        return {"success": False, "error": f"Live apply failed: {e}"}


def _process_live_queue_once(config_dir: Path, document) -> int:
    commands_file = config_dir / "live_commands.jsonl"
    if not commands_file.exists():
        return 0
    try:
        lines = [ln for ln in commands_file.read_text(encoding="utf-8").splitlines() if ln.strip()]
    except OSError:
        return 0
    if not lines:
        return 0
    processed = 0
    results_dir = config_dir / "live_results"
    results_dir.mkdir(parents=True, exist_ok=True)
    for line in lines:
        try:
            cmd = json.loads(line)
        except json.JSONDecodeError:
            continue
        cmd_id = str(cmd.get("command_id", f"unknown-{processed}"))
        res = _apply_live_command_in_document(document.getroot(), cmd)
        res.update({
            "command_id": cmd_id,
            "session_id": cmd.get("session_id"),
            "target": cmd.get("target"),
            "op": cmd.get("op"),
            "transport": "extension_live_dom_once",
            "timestamp": int(time.time() * 1000),
        })
        try:
            (results_dir / f"{cmd_id}.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            pass
        processed += 1
    try:
        commands_file.write_text("", encoding="utf-8")
    except OSError:
        pass
    return processed


def _debug_session_log(hypothesis_id: str, location: str, message: str, data: dict | None = None) -> None:
    # region agent log
    try:
        payload = {
            "sessionId": _DEBUG_SESSION,
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data or {},
            "timestamp": int(time.time() * 1000),
        }
        with open(_DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        pass
    # endregion


def _agent_log(hypothesis_id: str, location: str, message: str, data: dict | None = None) -> None:
    payload = {
        "sessionId": "a3fd08",
        "runId": "pre-fix",
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data or {},
        "timestamp": int(time.time() * 1000),
    }
    try:
        with open(r"e:\user\code\MCP-chatbot\debug-a3fd08.log", "a", encoding="utf-8") as f:
            f.write(json.dumps(payload) + "\n")
    except Exception:
        pass


def _sanitize_fs_path_str(s: str) -> str:
    """Drop control/DEL chars Inkscape occasionally embeds in xml:base / doc paths."""
    out: list[str] = []
    for c in str(s).strip():
        o = ord(c)
        if o < 32 or o == 127:
            continue
        out.append(c)
    return "".join(out)


def _path_from_file_uri(s: str) -> Path | None:
    low = _sanitize_fs_path_str(s)
    if not low.lower().startswith("file:"):
        return None
    rest = low[5:]
    while rest and rest[0] in "/\\":
        rest = rest[1:]
    try:
        p = Path(rest)
        return p if p.exists() else None
    except OSError:
        return None


def _inkscape_base_to_dir(base: str) -> Path | None:
    base = _sanitize_fs_path_str(base)
    if not base:
        return None
    p = _path_from_file_uri(base)
    if p is None:
        try:
            p = Path(base).expanduser()
        except OSError:
            return None
    if p.is_dir():
        return p
    if p.is_file():
        return p.parent
    return None


def _safe_dir_for_relative_docname(base_dir: Path | None) -> Path | None:
    if base_dir is None:
        return None
    try:
        base_dir.resolve().relative_to(Path(tempfile.gettempdir()).resolve())
        return None
    except ValueError:
        return base_dir


def _normalize_inkscape_path_candidate(raw: str | None, base_dir: Path | None) -> str | None:
    if not raw:
        return None
    r = _sanitize_fs_path_str(str(raw))
    if not r or "bound method" in r:
        return None
    fu = _path_from_file_uri(r)
    if fu is not None:
        if fu.is_file():
            return str(fu.resolve())
        return None
    p = Path(r).expanduser()
    if p.is_file():
        return str(p.resolve())
    if base_dir is not None and not p.is_absolute():
        q = (base_dir / r).resolve()
        if q.is_file():
            return str(q)
    return None


def _path_str_looks_like_temp_export(path_str: str) -> bool:
    """Temp / extension-export heuristic without requiring the path to exist on disk."""
    try:
        s = _sanitize_fs_path_str(path_str)
        if not s:
            return True
        name = Path(s).name.lower()
        if "ink_ext_" in name or name.startswith("ink_ext_"):
            return True
        ab = os.path.normcase(os.path.abspath(Path(s).expanduser()))
        td = os.path.normcase(os.path.abspath(str(Path(tempfile.gettempdir()).resolve())))
        return ab == td or ab.startswith(td + os.sep)
    except OSError:
        return False


def _is_probable_inkscape_temp_path(path_str: str) -> bool:
    try:
        p = Path(path_str).expanduser()
        if not p.is_file():
            return False
        pr = p.resolve()
        temp_root = Path(tempfile.gettempdir()).resolve()
        try:
            pr.relative_to(temp_root)
            in_temp = True
        except ValueError:
            in_temp = False
        name_lower = pr.name.lower()
        ink_ext = "ink_ext_" in name_lower or name_lower.startswith("ink_ext_")
        return bool(in_temp or ink_ext)
    except OSError:
        return False


def _resolve_effect_document_path(ext: inkex.EffectExtension) -> str | None:
    """Prefer a real saved path. Uses Inkscape's DOCUMENT_PATH env when set (see inkex InkscapeExtension.document_path)."""
    candidates: list[str] = []

    env_dp = _sanitize_fs_path_str(os.environ.get("DOCUMENT_PATH", "") or "")
    if env_dp:
        candidates.append(env_dp)

    doc = getattr(ext, "document", None)
    root = doc.getroot() if doc else None
    cand_bases: list[Path] = []
    if doc is not None and hasattr(doc, "get_document_base"):
        try:
            b = doc.get_document_base()
            if b:
                d = _inkscape_base_to_dir(str(b))
                if d:
                    cand_bases.append(d)
        except Exception:
            pass
    if root is not None and getattr(root, "base", None):
        try:
            d = _inkscape_base_to_dir(str(root.base))
            if d and d not in cand_bases:
                cand_bases.append(d)
        except Exception:
            pass
    rel_base = None
    rel_base_debug: list[dict] = []
    for d in cand_bases:
        sb = _safe_dir_for_relative_docname(d)
        rel_base_debug.append({"dir_preview": str(d)[:160], "picked_safe": sb is not None})
        if sb is not None:
            rel_base = sb
            break
    def _probe(raw: str | None) -> dict:
        if not raw:
            return {"raw": None, "normalized": None}
        norm = _normalize_inkscape_path_candidate(str(raw), rel_base)
        out = {"raw_preview": str(raw)[:220], "normalized_preview": (norm or "")[:220]}
        if norm:
            out["is_probable_temp"] = _is_probable_inkscape_temp_path(norm)
        return out

    if root is not None:
        try:
            docname = root.get(inkex.addNS("docname", "sodipodi"))
        except Exception:
            docname = None
        if not docname:
            docname = root.get("sodipodi:docname")
        if docname:
            candidates.append(docname)
        if doc is not None and hasattr(doc, "get_document_base"):
            try:
                base = doc.get_document_base()
                if base:
                    candidates.append(base)
            except Exception:
                pass
        if hasattr(root, "get_document_base"):
            try:
                base = root.get_document_base()
                if base:
                    candidates.append(base)
            except Exception:
                pass
        if getattr(root, "base", None):
            candidates.append(str(root.base))

    spi = getattr(ext, "svg_path", None)
    if spi is not None:
        try:
            p = spi() if callable(spi) else spi
            if p:
                candidates.append(str(p))
        except Exception:
            pass
    if hasattr(ext.options, "input_file") and ext.options.input_file:
        candidates.append(str(ext.options.input_file))

    probes = [_probe(c) for c in candidates]
    _debug_session_log(
        "H1",
        "start_mcp.py:_resolve_effect_document_path",
        "candidates_order_and_probe",
        {
            "candidate_count": len(candidates),
            "document_path_env_preview": env_dp[:220] if env_dp else None,
            "rel_base_preview": str(rel_base)[:220] if rel_base else None,
            "rel_base_debug": rel_base_debug,
            "cand_bases_preview": [str(x)[:160] for x in cand_bases],
            "probes": probes,
        },
    )

    seen: set[str] = set()
    resolved_existing: list[str] = []
    for raw in candidates:
        if not raw:
            continue
        res = _normalize_inkscape_path_candidate(str(raw), rel_base)
        if res and res not in seen:
            seen.add(res)
            resolved_existing.append(res)

    if env_dp and not _path_str_looks_like_temp_export(env_dp):
        try:
            pe = Path(_sanitize_fs_path_str(env_dp)).expanduser()
            try:
                canon = str(pe.resolve(strict=False))
            except TypeError:
                canon = str(pe.resolve())
        except OSError:
            canon = str(Path(_sanitize_fs_path_str(env_dp)).expanduser())
        if canon not in seen:
            seen.add(canon)
            resolved_existing.insert(0, canon)
        _debug_session_log(
            "H1",
            "start_mcp.py:_resolve_effect_document_path",
            "document_path_trusted_nonexistent",
            {"canon_preview": canon[:240], "is_file_on_disk": Path(canon).is_file()},
        )

    chosen = None
    chosen_reason = "none"
    for path in resolved_existing:
        if not _is_probable_inkscape_temp_path(path):
            chosen = path
            chosen_reason = "first_non_temp"
            break
    if chosen is None and resolved_existing:
        chosen = resolved_existing[0]
        chosen_reason = "fallback_first_existing"
    _debug_session_log(
        "H4",
        "start_mcp.py:_resolve_effect_document_path",
        "pick_result",
        {
            "runId": "post-fix-verify",
            "resolved_existing_count": len(resolved_existing),
            "chosen_reason": chosen_reason,
            "chosen_preview": (chosen or "")[:240],
            "resolved_all_preview": [x[:120] for x in resolved_existing[:6]],
        },
    )
    return chosen


def is_process_running(pid: int) -> bool:
    """Check if a process with the given PID is still running."""
    try:
        if os.name == "nt":
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}"],
                capture_output=True,
                text=True,
                timeout=2
            )
            return str(pid) in result.stdout
        else:
            os.kill(pid, 0)
            return True
    except (OSError, subprocess.TimeoutExpired, subprocess.SubprocessError):
        return False


def kill_process(pid: int) -> bool:
    """Kill a process by PID. Returns True if successful."""
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/PID", str(pid)], 
                         capture_output=True, timeout=5)
        else:
            os.kill(pid, 15)
        return True
    except Exception:
        return False


def kill_processes_on_port(port: int = 9877) -> int:
    """Kill all processes using the specified port. Returns number killed."""
    killed = 0
    try:
        if os.name == "nt":
            result = subprocess.run(
                ["netstat", "-ano"],
                capture_output=True,
                text=True,
                timeout=5
            )
            for line in result.stdout.splitlines():
                if f":{port}" in line and "LISTENING" in line:
                    parts = line.split()
                    if len(parts) >= 5:
                        try:
                            pid = int(parts[-1])
                            if pid > 0:
                                kill_process(pid)
                                killed += 1
                        except (ValueError, IndexError):
                            pass
        else:
            result = subprocess.run(
                ["lsof", "-ti", f":{port}"],
                capture_output=True,
                text=True,
                timeout=5
            )
            for pid_str in result.stdout.strip().split():
                try:
                    pid = int(pid_str)
                    kill_process(pid)
                    killed += 1
                except ValueError:
                    pass
    except Exception:
        pass
    return killed


def check_port_in_use(port: int = 9877) -> bool:
    """Check if a port is already in use."""
    import socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(("localhost", port))
        sock.close()
        return result == 0
    except Exception:
        return False


def find_inkscape_bin() -> str | None:
    """Find Inkscape executable. Returns path or None."""
    inkscape_bin = os.getenv("INKSCAPE_BIN")
    if inkscape_bin and Path(inkscape_bin).exists():
        return inkscape_bin
    
    if os.name == "nt":
        common_paths = [
            r"C:\Program Files\Inkscape\bin\inkscape.exe",
            r"C:\Program Files (x86)\Inkscape\bin\inkscape.exe",
        ]
        for path in common_paths:
            if Path(path).exists():
                return path
    
    try:
        result = subprocess.run(
            ["where", "inkscape"] if os.name == "nt" else ["which", "inkscape"],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0:
            path = result.stdout.strip().splitlines()[0]
            if Path(path).exists():
                return path
    except Exception:
        pass
    
    return None


def _can_import_inkscape_ai(python_exe: str) -> bool:
    try:
        result = subprocess.run(
            [python_exe, "-c", "import inkscape_ai"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        return result.returncode == 0
    except Exception:
        return False


def resolve_bridge_python() -> str:
    env_python = os.getenv("INKSCAPE_AI_BRIDGE_PYTHON", "").strip()
    candidates = [c for c in (env_python, sys.executable, "python", "py") if c]
    for candidate in candidates:
        check_cmd = [candidate, "-3"] if candidate == "py" else [candidate]
        exe = " ".join(check_cmd).strip()
        try:
            if candidate == "py":
                result = subprocess.run(
                    ["py", "-3", "-c", "import inkscape_ai"],
                    capture_output=True,
                    text=True,
                    timeout=3,
                )
                # region agent log
                _agent_log("H6", "start_mcp.py:resolve_bridge_python", "Checked py launcher candidate", {"candidate": "py -3", "returncode": result.returncode})
                # endregion
                if result.returncode == 0:
                    return "py -3"
            else:
                can_import = _can_import_inkscape_ai(candidate)
                # region agent log
                _agent_log("H6", "start_mcp.py:resolve_bridge_python", "Checked python candidate", {"candidate": candidate, "can_import": can_import})
                # endregion
                if can_import:
                    return candidate
        except Exception:
            continue
    # region agent log
    _agent_log("H6", "start_mcp.py:resolve_bridge_python", "Falling back to sys.executable", {"fallback": sys.executable})
    # endregion
    return sys.executable


class StartMCPServer(inkex.EffectExtension):
    def add_arguments(self, pars):
        pars.add_argument("--spawn_bridge", type=inkex.Boolean, default=True)
        pars.add_argument("--live_preview", type=inkex.Boolean, default=False)
        pars.add_argument("--allow_temp_target", type=inkex.Boolean, default=False)

    def effect(self):
        # region agent log
        _agent_log("H1", "start_mcp.py:effect", "Extension effect entered", {"spawn_bridge": bool(getattr(self.options, "spawn_bridge", False))})
        # endregion
        doc_path = _resolve_effect_document_path(self)
        config_dir = Path.home() / ".config" / "inkscape-ai"
        config_dir.mkdir(parents=True, exist_ok=True)
        lock_file = config_dir / "bridge_start.lock"

        if doc_path:
            _agent_log(
                "H2",
                "start_mcp.py:resolved_doc",
                "Resolved document path for bridge",
                {"doc_path": doc_path, "is_probable_temp": _is_probable_inkscape_temp_path(doc_path)},
            )
            doc_path = str(Path(doc_path).expanduser().resolve())
            if not Path(doc_path).exists():
                if _path_str_looks_like_temp_export(doc_path):
                    _agent_log("H2", "start_mcp.py:doc_path", "Document path resolved to missing temp-like path", {"doc_path": doc_path})
                    doc_path = None
                else:
                    _agent_log(
                        "H2",
                        "start_mcp.py:doc_path",
                        "Trusted non-temp path does not exist yet; keeping path for session lock",
                        {"doc_path": doc_path},
                    )

        if not doc_path:
            if self.options.allow_temp_target:
                temp_doc = config_dir / "temp_document.svg"
                try:
                    if hasattr(self, "document") and self.document:
                        with open(temp_doc, "wb") as f:
                            self.document.write(f)
                        doc_path = str(temp_doc.resolve())
                        _agent_log("H2", "start_mcp.py:temp_doc", "Fell back to temp document", {"temp_doc": doc_path})
                except Exception:
                    _agent_log("H2", "start_mcp.py:temp_doc_error", "Failed to write temp document")
                    pass
            else:
                status_file = config_dir / "extension_status.txt"
                status_file.write_text(
                    "ERROR\nCould not use a real file: save your document as .svg first, then run Start MCP Server again.\n"
                    "Optional: enable 'Allow temp target (testing)' to use ~/.config/inkscape-ai/temp_document.svg.",
                    encoding="utf-8",
                )
                inkex.errormsg(
                    "Save your document first (File → Save As… to a .svg file), then run Start MCP Server.\n\n"
                    "For extension/dev testing only: enable “Allow temp target (testing)” in the dialog."
                )
                return
        
        if doc_path:
            doc_path = str(Path(doc_path).expanduser().resolve())
            (config_dir / "current_document").write_text(doc_path, encoding="utf-8")
            live_session = _write_live_session_record(config_dir, doc_path)
            processed_live = 0
            if hasattr(self, "document") and self.document is not None:
                processed_live = _process_live_queue_once(config_dir, self.document)
                if processed_live > 0:
                    try:
                        with open(doc_path, "wb") as f:
                            self.document.write(f)
                    except Exception:
                        pass
            _debug_session_log(
                "H3",
                "start_mcp.py:effect",
                "persisted_current_document",
                {
                    "doc_path_preview": doc_path[:260],
                    "is_probable_temp": _is_probable_inkscape_temp_path(doc_path),
                    "live_session_id": live_session.get("session_id"),
                    "processed_live_commands": processed_live,
                },
            )

            status_file = config_dir / "extension_status.txt"
            try:
                if self.options.spawn_bridge:
                    # Prevent duplicate launches from rapid repeated clicks.
                    if lock_file.exists():
                        age_s = time.time() - lock_file.stat().st_mtime
                        if age_s < 10:
                            # region agent log
                            _agent_log("H1", "start_mcp.py:lock", "Startup blocked by active lock", {"lock_age_s": round(age_s, 3)})
                            # endregion
                            inkex.errormsg("Bridge startup already in progress. Please wait a moment.")
                            return
                    lock_file.write_text(str(time.time()), encoding="utf-8")
                    pid_file = config_dir / "bridge_pid.txt"
                    old_pid = None
                    
                    killed_count = kill_processes_on_port(9877)
                    # region agent log
                    _agent_log("H4", "start_mcp.py:port_cleanup", "Port cleanup executed", {"killed_count": killed_count})
                    # endregion
                    if killed_count > 0:
                        time.sleep(0.3)
                    
                    if pid_file.exists():
                        try:
                            old_pid = int(pid_file.read_text().strip())
                            if is_process_running(old_pid):
                                kill_process(old_pid)
                                time.sleep(0.2)
                        except (ValueError, Exception):
                            pass
                    
                    python_exe = resolve_bridge_python()
                    bridge_cmd = python_exe.split(" ") + ["-m", "inkscape_ai.bridge"]
                    env = os.environ.copy()
                    prior_doc = os.environ.get("INKSCAPE_DOCUMENT", "")
                    env["INKSCAPE_DOCUMENT"] = doc_path
                    _debug_session_log(
                        "H5",
                        "start_mcp.py:effect",
                        "bridge_spawn_env_INKSCAPE_DOCUMENT",
                        {
                            "set_to_preview": doc_path[:260],
                            "prior_process_env_preview": (prior_doc or "")[:260],
                            "spawn_bridge": True,
                        },
                    )
                    if "py -3" in python_exe:
                        env["PYTHONUTF8"] = "1"
                    repo_src = str((Path(__file__).resolve().parents[1] / "src").resolve())
                    env["PYTHONPATH"] = f"{repo_src}{os.pathsep}{env.get('PYTHONPATH', '')}".rstrip(os.pathsep)
                    # region agent log
                    _agent_log("H7", "start_mcp.py:env", "Prepared PYTHONPATH for bridge", {"repo_src": repo_src, "repo_src_exists": Path(repo_src).exists()})
                    # endregion
                    
                    inkscape_bin = find_inkscape_bin()
                    if inkscape_bin:
                        env["INKSCAPE_BIN"] = inkscape_bin
                    
                    if self.options.live_preview:
                        env["INKSCAPE_LIVE_PREVIEW"] = "1"
                    if self.options.allow_temp_target:
                        env["INKSCAPE_AI_ALLOW_TEMP_WRITES"] = "1"
                    log_file = config_dir / "bridge.log"
                    with open(log_file, "w") as log:
                        kwargs = {
                            "env": env,
                            "stdout": log,
                            "stderr": log,
                        }
                        if os.name == "nt":
                            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
                            if hasattr(subprocess, "DETACHED_PROCESS"):
                                kwargs["creationflags"] |= subprocess.DETACHED_PROCESS
                        else:
                            kwargs["start_new_session"] = True
                        proc = subprocess.Popen(bridge_cmd, **kwargs)
                        # region agent log
                        _agent_log("H3", "start_mcp.py:spawn", "Bridge process spawned", {"pid": proc.pid, "python_exe": python_exe})
                        # endregion
                        with open(pid_file, "w") as f:
                            f.write(str(proc.pid))
                        
                        time.sleep(0.5)
                        bridge_running = check_port_in_use(9877) or is_process_running(proc.pid)
                        # region agent log
                        _agent_log("H4", "start_mcp.py:post_spawn_check", "Bridge readiness checked", {"bridge_running": bridge_running, "pid": proc.pid})
                        # endregion
                        
                        action_taken = "restarted" if old_pid or killed_count > 0 else "started"
                        if bridge_running:
                            status_msg = f"MCP bridge {action_taken} successfully.\nPID: {proc.pid}\nDocument: {Path(doc_path).name}\nBridge listening on port 9877."
                            if killed_count > 0:
                                status_msg += f"\nCleaned up {killed_count} old bridge process(es)."
                            status_file.write_text(
                                f"SUCCESS\n{status_msg}",
                                encoding="utf-8"
                            )
                            inkex.errormsg(f"MCP Server {action_taken}!\nPID: {proc.pid}")
                        else:
                            status_file.write_text(
                                f"WARNING\nBridge process started (PID: {proc.pid}) but is not ready yet.\nDocument: {Path(doc_path).name}\nIf this persists, click Start MCP Server again to restart bridge.",
                                encoding="utf-8"
                            )
                            inkex.errormsg(f"MCP Server started (PID: {proc.pid})\nMay need a moment to initialize.")
                else:
                    status_file.write_text(
                        f"SUCCESS\nMCP Server configured.\nDocument path saved: {doc_path}",
                        encoding="utf-8"
                    )
                    inkex.errormsg(f"MCP Server configured.\nDocument: {Path(doc_path).name}")
            except Exception as e:
                # region agent log
                _agent_log("H5", "start_mcp.py:exception", "Exception during startup", {"error": str(e)})
                # endregion
                error_file = config_dir / "bridge_error.txt"
                with open(error_file, "w") as f:
                    f.write(f"Error starting bridge: {e}\n")
                    import traceback
                    f.write(traceback.format_exc())
                status_file.write_text(
                    f"ERROR\nError starting MCP bridge: {e}\nCheck {error_file} for details.",
                    encoding="utf-8"
                )
                inkex.errormsg(f"Error: {str(e)[:100]}\nSee {error_file.name} for details.")
            finally:
                if lock_file.exists():
                    try:
                        lock_file.unlink()
                    except Exception:
                        pass
        else:
            status_file = config_dir / "extension_status.txt"
            status_file.write_text(
                "ERROR\nCould not determine document path.",
                encoding="utf-8"
            )
            inkex.errormsg("Error: Could not determine document path.\nPlease save your document first.")


if __name__ == "__main__":
    StartMCPServer().run()
