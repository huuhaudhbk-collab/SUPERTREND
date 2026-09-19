"""Web Push qua pywebpush + VAPID — payload cho mẫu hình nến và tín hiệu xu hướng.
Nguồn địa chỉ: Worker KV (GET /subs) → fallback PUSH_SUBS_FALLBACK (JSON trong Secret).

- configured() đòi CẢ HAI khoá: thiếu public key thì lỗi im lặng (lỗi kinh điển của Web Push).
- 404/410 = trình duyệt đã huỷ đăng ký → báo Worker xoá và ghi vào state để giao diện hiện dòng đỏ.
"""
from __future__ import annotations

import hashlib
import json
import logging

import httpx
from pywebpush import WebPushException, webpush

from common.config import (
    HTTP_TIMEOUT, PUSH_SUBS_FALLBACK, VAPID_PRIVATE_KEY, VAPID_PUBLIC_KEY, VAPID_SUBJECT,
    WORKER_TOKEN, WORKER_URL,
)

from .patterns import PATTERNS
from .trend import SIGNALS as TREND_SIGNALS

# Tên hiển thị theo id — mẫu nến và tín hiệu xu hướng dùng chung một bảng tra.
NAMES = {**{pid: m["name"] for pid, m in PATTERNS.items()},
         **{pid: m["name"] for pid, m in TREND_SIGNALS.items()}}

logger = logging.getLogger(__name__)
# Tín hiệu dùng cho phiên hôm sau nên để sống qua đêm — máy tắt mạng tối vẫn nhận được sáng.
TTL_ALERT = 16 * 3600


def configured() -> bool:
    return bool(VAPID_PRIVATE_KEY and VAPID_PUBLIC_KEY)


def _worker_headers() -> dict:
    return {"Authorization": f"Bearer {WORKER_TOKEN}"}


def subscriptions() -> tuple[list[dict], str]:
    """(danh sách subscription, nguồn). Worker trước, fallback sau."""
    if WORKER_URL and WORKER_TOKEN:
        try:
            r = httpx.get(f"{WORKER_URL}/subs", headers=_worker_headers(), timeout=HTTP_TIMEOUT)
            r.raise_for_status()
            subs = r.json()
            if isinstance(subs, dict):
                subs = list(subs.values())
            return subs, "worker"
        except Exception as exc:  # noqa: BLE001
            logger.warning("Worker /subs lỗi: %s — dùng fallback", exc)
    if PUSH_SUBS_FALLBACK.strip():
        try:
            subs = json.loads(PUSH_SUBS_FALLBACK)
            return (subs if isinstance(subs, list) else [subs]), "fallback"
        except json.JSONDecodeError as exc:
            logger.error("PUSH_SUBS_FALLBACK không phải JSON: %s", exc)
    return [], "none"


def test_requested() -> bool:
    """Điện thoại bấm 'Gửi thử' → Worker đặt cờ; job đọc (và xoá) cờ này."""
    if not (WORKER_URL and WORKER_TOKEN):
        return False
    try:
        r = httpx.get(f"{WORKER_URL}/test", headers=_worker_headers(), timeout=HTTP_TIMEOUT)
        return bool(r.status_code == 200 and r.json().get("requested"))
    except Exception:  # noqa: BLE001
        return False


def _sub_id(sub: dict) -> str:
    return hashlib.sha256(sub["endpoint"].encode()).hexdigest()[:16]


def _forget(sub: dict) -> None:
    if WORKER_URL and WORKER_TOKEN:
        try:
            httpx.delete(f"{WORKER_URL}/subs/{_sub_id(sub)}", headers=_worker_headers(), timeout=HTTP_TIMEOUT)
        except Exception:  # noqa: BLE001
            pass


def send(payload: dict, subs: list[dict]) -> dict:
    """Gửi một payload tới mọi thiết bị. Trả về {sent, gone, failed, errors}."""
    res = {"sent": 0, "gone": 0, "failed": 0, "errors": []}
    if not configured():
        res["errors"].append("Thiếu VAPID_PUBLIC_KEY/VAPID_PRIVATE_KEY")
        return res
    data = json.dumps(payload, ensure_ascii=False)
    for sub in subs:
        try:
            webpush(
                subscription_info={"endpoint": sub["endpoint"], "keys": sub["keys"]},
                data=data, ttl=TTL_ALERT,
                vapid_private_key=VAPID_PRIVATE_KEY, vapid_claims={"sub": VAPID_SUBJECT},
                headers={"Urgency": "high"},
            )
            res["sent"] += 1
        except WebPushException as exc:
            status = getattr(exc.response, "status_code", None)
            if status in (404, 410):
                res["gone"] += 1
                _forget(sub)
            else:
                res["failed"] += 1
                res["errors"].append(f"{_sub_id(sub)}: {status} {exc}"[:200])
        except Exception as exc:  # noqa: BLE001
            res["failed"] += 1
            res["errors"].append(f"{_sub_id(sub)}: {exc}"[:200])
    return res


def symbol_payload(symbol: str, signals: list[dict], trade_date: str) -> dict:
    """Một thông báo cho MỘT mã, gộp mọi mẫu của mã đó trong phiên. `signals` cùng hướng hay
    khác hướng đều gộp — hiếm khi một mã vừa có mẫu tăng vừa có mẫu giảm, nếu có thì nói rõ."""
    names = [NAMES[s["pattern"]] for s in signals]
    dirs = {s["direction"] for s in signals}
    if dirs == {"buy"}:
        head = "▲ MUA"
    elif dirs == {"sell"}:
        head = "▼ BÁN"
    else:
        head = "▲▼ TRÁI CHIỀU"
    title = f"{head} {symbol} · " + (names[0] if len(names) == 1 else f"{len(names)} mẫu hình")
    px = signals[0]["price"]
    chg = signals[0].get("change_pct")
    chg_txt = f" ({chg:+.1f}%)" if chg is not None else ""
    d, m = trade_date[8:10], trade_date[5:7]
    body = f"giá {px:.2f}{chg_txt} · phiên {d}/{m} · " + ", ".join(names)
    return {
        "kind": "candle", "title": title, "body": body, "symbol": symbol,
        "direction": "buy" if dirs == {"buy"} else "sell" if dirs == {"sell"} else "mixed",
        "url": "./#today", "tag": f"cw-{symbol}", "hot": True,
    }


def digest_payload(by_symbol: dict[str, list[dict]], trade_date: str) -> dict:
    """Quá nhiều mã cùng có mẫu → MỘT thông báo tổng hợp, để điện thoại không réo liên hồi.
    Thân thông báo: 'HPG ▲ Sao mai · VNM ▼ Nhấn chìm giảm · …' (mỗi mã một mẫu đầu tiên)."""
    n_buy = sum(1 for sigs in by_symbol.values() if all(s["direction"] == "buy" for s in sigs))
    n_sell = sum(1 for sigs in by_symbol.values() if all(s["direction"] == "sell" for s in sigs))
    parts = []
    for sym, sigs in by_symbol.items():
        arrow = "▲" if sigs[0]["direction"] == "buy" else "▼"
        extra = f" +{len(sigs) - 1}" if len(sigs) > 1 else ""
        parts.append(f"{sym} {arrow} {NAMES[sigs[0]['pattern']]}{extra}")
    d, m = trade_date[8:10], trade_date[5:7]
    return {
        "kind": "digest",
        "title": f"{len(by_symbol)} mã có mẫu hình · {n_buy} MUA, {n_sell} BÁN",
        "body": f"phiên {d}/{m} · " + " · ".join(parts),
        "url": "./#today", "tag": "cw-digest", "hot": True,
    }


def trend_payload(signal: dict, trade_date: str) -> dict:
    """MỖI tín hiệu xu hướng là MỘT thông báo riêng, không bao giờ gộp vào bản tổng hợp: hiếm (~1/phiên
    cả danh mục) và mang mức dừng lỗ — con số cần để đặt lệnh sáng hôm sau."""
    buy = signal["direction"] == "buy"
    sym = signal["symbol"]
    chg = signal.get("change_pct")
    chg_txt = f" ({chg:+.1f}%)" if chg is not None else ""
    d, m = trade_date[8:10], trade_date[5:7]
    if buy:
        tail = f"dừng lỗ {signal['st_line']:.2f} (−{signal['risk_pct']:.1f}%)"
    else:
        tail = f"xanh được {signal['days_in_trend']} phiên trước khi gãy"
    return {
        "kind": "trend", "title": f"{'▲ MUA' if buy else '▼ THOÁT'} {sym} · {NAMES[signal['pattern']]}",
        "body": f"giá {signal['price']:.2f}{chg_txt} · phiên {d}/{m} · {tail}",
        "symbol": sym, "direction": signal["direction"],
        "url": "./#today", "tag": f"cw-st-{sym}", "hot": True,
    }


def heartbeat_payload(n_alerts_week: int, trade_date: str) -> dict:
    return {
        "kind": "heartbeat", "title": "Candle Watch vẫn chạy",
        "body": f"Tuần này {n_alerts_week} mẫu hình · dữ liệu đến phiên {trade_date}",
        "url": "./#history", "tag": "cw-heartbeat", "hot": False,
    }


def test_payload() -> dict:
    return {"kind": "test", "title": "Thông báo thử — máy này đã nhận được",
            "body": "Khi có mẫu hình thật, thẻ như thế này sẽ hiện kể cả khi app đang đóng.",
            "url": "./#today", "tag": "cw-test"}


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    subs, src = subscriptions()
    print(f"{len(subs)} thiết bị (nguồn: {src}) · VAPID {'OK' if configured() else 'THIẾU'}")
    if "--test" in sys.argv:
        print(send(test_payload(), subs))
