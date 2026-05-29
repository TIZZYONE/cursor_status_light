#!/usr/bin/env python3
"""Cursor Hook：快速写入 status（比 PowerShell 冷启动快）。"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

STATUS_DIR = Path.home() / ".cursor" / "status"
BUSY_LIKE = frozenset({"busy", "thinking", "ai", "demo"})
ALLOWED = frozenset({"demo", "thinking", "ai", "busy", "success", "error", "alarm", "traffic", "off"})
ALIASES = {"working": "busy", "done": "success", "idle": "success"}
SESSION_KEYS = (
    "conversation_id",
    "conversationId",
    "chat_id",
    "chatId",
    "session_id",
    "sessionId",
    "agentId",
    "composer_id",
    "composerId",
    "thread_id",
    "threadId",
)


def utc_ts() -> str:
    t = datetime.now(timezone.utc)
    ms = t.microsecond // 1000
    return t.strftime("%Y-%m-%dT%H:%M:%S.") + f"{ms:03d}Z"


def session_key(obj: dict | None) -> str:
    if not obj:
        return "default"
    for key in SESSION_KEYS:
        val = obj.get(key)
        if val:
            return str(val)
    parts: list[str] = []
    roots = obj.get("workspace_roots")
    if isinstance(roots, list):
        parts.extend(str(x) for x in roots if x)
    for key in ("cwd", "workspace_folder"):
        val = obj.get(key)
        if val:
            parts.append(str(val))
    if parts:
        return "ws_" + sha256("|".join(parts).encode()).hexdigest()[:16]
    return "default"


def sanitize(name: str) -> str:
    name = re.sub(r'[\\/:*?"<>|]', "_", name).strip()
    return name or "default"


def workspace_hint(obj: dict | None) -> str | None:
    """供双击绿灯时匹配对应 Cursor 窗口标题。"""
    if not obj:
        return None
    roots = obj.get("workspace_roots")
    if isinstance(roots, list):
        for root in roots:
            if root:
                return str(root)
    for key in ("cwd", "workspace_folder"):
        val = obj.get(key)
        if val:
            return str(val)
    return None


def write_json(path: Path, data: dict) -> None:
    path.write_text(
        json.dumps(data, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )


def maybe_log(status: str, session_id: str) -> None:
    if not os.environ.get("CURSOR_LIGHT_HOOK_LOG"):
        return
    log_path = STATUS_DIR / "hook.log"
    line = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {status} | {session_id}\n"
    try:
        with log_path.open("a", encoding="utf-8") as f:
            f.write(line)
        lines = log_path.read_text(encoding="utf-8").splitlines()
        if len(lines) > 200:
            log_path.write_text("\n".join(lines[-200:]) + "\n", encoding="utf-8")
    except OSError:
        pass


def main() -> None:
    raw_status = sys.argv[1] if len(sys.argv) > 1 else "busy"
    status = ALIASES.get(raw_status, raw_status)
    if status not in ALLOWED:
        status = "busy"

    raw = sys.stdin.read()
    obj: dict | None = None
    if raw.strip():
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            obj = None

    session_id = sanitize(session_key(obj))
    STATUS_DIR.mkdir(parents=True, exist_ok=True)
    ts = utc_ts()
    payload = {"status": status, "ts": ts}
    ws = workspace_hint(obj)
    if ws:
        payload["workspace"] = ws

    write_json(STATUS_DIR / f"{session_id}.json", payload)

    default_path = STATUS_DIR / "default.json"
    hb = STATUS_DIR / "_heartbeat.json"
    if status in BUSY_LIKE:
        write_json(hb, {"ts": ts})
        # 有真实会话 id 时，删掉无 id 时遗留的 default busy，避免多文件聚合一直黄
        if session_id != "default" and default_path.exists():
            try:
                default_path.unlink()
            except OSError:
                pass
    elif status == "success":
        if hb.exists():
            hb.unlink(missing_ok=True)
        if session_id != "default":
            write_json(default_path, payload)
    elif status == "error" and session_id != "default" and default_path.exists():
        try:
            default_path.unlink()
        except OSError:
            pass

    maybe_log(status, session_id)


if __name__ == "__main__":
    main()
