"""Danh mục theo dõi — nhập tay trên điện thoại (tab Cài đặt), dán vào GitHub Actions Variable
`WATCHLIST`, workflow đưa vào env, job đọc ở đây. Không gọi mạng.

Thứ tự: env WATCHLIST có nội dung → parse, ghi bản chụp docs/data/watchlist.json (giao diện đọc để
điền sẵn ô nhập) → nguồn "variable"; env trống → bản chụp → "cache"; không có gì → ([], "none").
Danh mục rỗng KHÔNG phải lỗi: đó là trạng thái bình thường trước khi người dùng nhập mã lần đầu.

`parse` là đặc tả chuẩn hoá — JS trong docs/app.js (normalizeWatchlist) phải cho ra cùng kết quả:
tách theo dấu phẩy / chấm phẩy / khoảng trắng / xuống dòng, viết hoa, chỉ nhận 3–6 ký tự chữ-số,
bỏ trùng, sắp xếp A→Z.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime

from common import config
from common.config import SITE_DATA, TZ

logger = logging.getLogger(__name__)

CACHE = SITE_DATA / "watchlist.json"
SYMBOL_RE = re.compile(r"^[A-Z0-9]{3,6}$")
SPLIT_RE = re.compile(r"[\s,;]+")


def parse(text: str) -> list[str]:
    """Chuỗi người dùng gõ → danh sách mã hợp lệ, không trùng, A→Z. Token sai dạng bị bỏ qua."""
    out: set[str] = set()
    for tok in SPLIT_RE.split(text or ""):
        t = tok.strip().upper()
        if t and SYMBOL_RE.match(t):
            out.add(t)
    return sorted(out)


def load() -> tuple[list[dict], str]:
    """(danh sách {symbol, company_name, exchange}, nguồn) — nguồn là "variable" | "cache" | "none"."""
    text = (config.WATCHLIST or "").strip()
    if text:
        symbols = parse(text)
        if symbols:
            items = [{"symbol": s, "company_name": "", "exchange": ""} for s in symbols]
            CACHE.parent.mkdir(parents=True, exist_ok=True)
            CACHE.write_text(json.dumps({
                "fetched_at": datetime.now(TZ).isoformat(timespec="seconds"),
                "source": "variable", "items": items,
            }, ensure_ascii=False, indent=1), encoding="utf-8")
            return items, "variable"
        logger.warning("WATCHLIST có nội dung nhưng không có mã hợp lệ: %r — dùng bản chụp", text[:80])
    try:
        items = json.loads(CACHE.read_text(encoding="utf-8")).get("items") or []
        return items, ("cache" if items else "none")
    except (FileNotFoundError, ValueError):
        return [], "none"
