"""Cài đặt: docs/data/settings.json (commit trong repo) → Cloudflare Worker KV nếu có (GĐ 2)
→ mặc định trong code."""
from __future__ import annotations

import json
import logging

import httpx

from common.config import HTTP_TIMEOUT, SITE_DATA, WORKER_TOKEN, WORKER_URL

logger = logging.getLogger(__name__)

DEFAULTS = {
    "patterns_disabled": [],   # id mẫu bị tắt (xem job/patterns.py::PATTERNS)
    "history_days": 30,        # số phiên hiện ở tab Lịch sử
}

LOCAL = SITE_DATA / "settings.json"


def load() -> dict:
    s = dict(DEFAULTS)
    if LOCAL.exists():
        try:
            s.update(json.loads(LOCAL.read_text(encoding="utf-8")))
        except Exception as exc:  # noqa: BLE001
            logger.warning("settings.json hỏng: %s", exc)
    if WORKER_URL and WORKER_TOKEN:
        try:
            r = httpx.get(f"{WORKER_URL}/settings", headers={"Authorization": f"Bearer {WORKER_TOKEN}"},
                          timeout=HTTP_TIMEOUT)
            if r.status_code == 200 and r.text.strip():
                s.update(r.json())
                s["_source"] = "worker"
        except Exception as exc:  # noqa: BLE001
            logger.warning("Worker /settings không trả lời: %s — dùng bản local", exc)
    s["patterns_disabled"] = sorted({str(p) for p in (s.get("patterns_disabled") or [])})
    return s
