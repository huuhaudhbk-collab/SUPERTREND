"""Job sau phiên — chạy trong GitHub Actions 15:35 T2–T6 (hoặc local: python -m job.run_daily).

Luồng: danh mục (Variable WATCHLIST, nhập tay trên điện thoại) → nến ngày DNSE cho từng mã → nhận dạng 18 mẫu nến + 2 tín hiệu xu hướng
(Supertrend × EMA10, job/trend.py) trên NẾN CUỐI ĐÃ CHỐT → Web Push (xu hướng: mỗi tín hiệu một thông
báo riêng; mẫu nến: gộp theo mã / tổng hợp) → ghi docs/data/latest.json, bars.json, state.json,
daily/<ngày>.json.

Idempotent: nếu hôm nay đã có file daily và không có --force thì thoát (các cron dự phòng chạy
lại chỉ khi lần trước bị GitHub trễ/bỏ hoặc nguồn chưa chốt). Không có CSDL: file daily theo
ngày chính là chốt chống bắn trùng.

Nguồn chưa chốt (bẫy DNSE 14/09/2026): mỗi mã có nến hôm nay phải có
nến 1' chạm ATC 14:45 mới được tin; ≥ 20 % mã thanh khoản thiếu → KHÔNG ghi file hôm nay, cron
sau thử lại. Mã ít khớp lệnh (IDP, TDM…) mang nến cũ nhiều ngày → ghi vào `stale`, KHÔNG xét
mẫu — nếu xét thì một mẫu cũ sẽ được "phát hiện lại" mỗi ngày.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timedelta

from common import dnse
from common.config import SITE_DATA, TZ

from . import patterns, push, settings, trend, watchlist

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("job")

LATEST = SITE_DATA / "latest.json"
BARS = SITE_DATA / "bars.json"
STATE = SITE_DATA / "state.json"
DAILY = SITE_DATA / "daily"

# Số nến gửi kèm mỗi tín hiệu để giao diện vẽ mini-chart (≥ 2 nến nền + tối đa 5 nến của mẫu).
CANDLES_IN_CARD = 7
# Nến xu hướng (có Supertrend/EMA) gửi kèm thẻ mẫu nến cho ô biểu đồ rộng bên dưới nến mẫu.
# Ô này svg 300 px nên chứa được 46 nến; thẻ xu hướng svg 132 px giữ trend.BARS_IN_CARD (22).
TREND_CANDLES_IN_CARD = 46
# Nến ngày lấy về: 200 ngày lịch ≈ 135 phiên — Supertrend/EMA cần ≥ 40 phiên warm-up, mẫu nến cần 12.
FETCH_DAYS = 200
# Số nến mỗi mã ghi vào docs/data/bars.json cho tab Biểu đồ (≈ 300 KB cho 39 mã, ghi đè mỗi ngày).
BARS_IN_CHART = 130
# Mã có ít nhất ngần này nến 1' trong ngày mới đủ thanh khoản để "bỏ phiếu" nguồn đã chốt chưa.
LIQUID_MIN_BARS = 30
# Tỷ lệ mã thanh khoản thiếu nến ATC từ mức này trở lên → coi nguồn chưa chốt.
UNSETTLED_RATIO = 0.2
# Nhiều hơn ngần này mã cùng có mẫu → gửi MỘT thông báo tổng hợp thay vì mỗi mã một cái.
DIGEST_THRESHOLD_DEFAULT = 6


def _load(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default


def _dump(path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=1, default=str), encoding="utf-8")


def fetch_bars(tickers: list[str], client=None, days: int = FETCH_DAYS) -> tuple[dict[str, list[dict]], list[str]]:
    """Nến ngày cho từng mã + danh sách mã thanh khoản mà nến HÔM NAY chưa chốt (rỗng = nguồn ổn).
    """
    bars: dict[str, list[dict]] = {}
    voters: list[str] = []
    lacking: list[str] = []
    today = dnse.today_vn()
    with (client or dnse.DnseClient(days=days)) as c:
        for i, t in enumerate(sorted(tickers), 1):
            b = c.daily(t)
            if not b:
                continue
            if b[-1]["d"] == today:
                minutes = c.today_minutes(t)
                if len(minutes) >= LIQUID_MIN_BARS:
                    voters.append(t)
                    if not dnse.session_settled(minutes):
                        lacking.append(t)
                b[-1] = dnse.merge_today(b[-1], minutes)
            bars[t] = b
            if i % 10 == 0:
                log.info("giá: %d/%d mã", i, len(tickers))
    unsettled = lacking if voters and len(lacking) / len(voters) >= UNSETTLED_RATIO else []
    if lacking and not unsettled:
        log.info("Mã thiếu nến ATC nhưng nguồn nhìn chung đã chốt (%d/%d): %s",
                 len(lacking), len(voters), ", ".join(lacking))
    return bars, unsettled


def _candles_for_card(bars: list[dict], n: int = CANDLES_IN_CARD) -> list[dict]:
    return [{"d": b["d"].isoformat(), "o": b["o"], "h": b["h"], "l": b["l"], "c": b["c"], "v": b["v"]}
            for b in bars[-n:]]


def detect_signals(bars_by_symbol: dict[str, list[dict]], names: dict[str, str], trade_date,
                   disabled: set[str]) -> tuple[list[dict], list[dict]]:
    """(tín hiệu của phiên trade_date — mẫu nến `kind: candle` và xu hướng `kind: trend`,
    danh sách mã có nến cuối cũ hơn trade_date)."""
    signals: list[dict] = []
    stale: list[dict] = []
    for sym in sorted(bars_by_symbol):
        b = bars_by_symbol[sym]
        if b[-1]["d"] != trade_date:
            stale.append({"symbol": sym, "last_date": b[-1]["d"].isoformat()})
            continue
        hits = patterns.detect_at(b, len(b) - 1, disabled)
        thits = trend.detect_at(b, len(b) - 1, disabled)
        if not hits and not thits:
            continue
        prev = b[-2]["c"] if len(b) > 1 and b[-2]["c"] else None
        chg = (b[-1]["c"] / prev - 1) * 100 if prev else None
        common = {"symbol": sym, "company_name": names.get(sym, ""), "price": b[-1]["c"],
                  "change_pct": round(chg, 2) if chg is not None else None, "volume": b[-1]["v"]}
        for pid in hits:
            meta = patterns.PATTERNS[pid]
            signals.append({
                **common, "kind": "candle",
                "pattern": pid, "name": meta["name"], "direction": meta["direction"],
                "bars": meta["bars"], "hint": meta["hint"], "advice": meta["advice"],
                "caution": meta.get("caution", ""), "candles": _candles_for_card(b),
                # 46 nến kèm dải Supertrend/EMA10 — giao diện vẽ biểu đồ xu hướng ngay dưới nến mẫu
                "trend_candles": trend.candles_for_card(b, n=TREND_CANDLES_IN_CARD),
            })
        if thits:
            state = trend.state_at(b) or {}
            for pid in thits:
                meta = trend.SIGNALS[pid]
                signals.append({
                    **common, "kind": "trend",
                    "pattern": pid, "name": meta["name"], "direction": meta["direction"],
                    "bars": meta["bars"], "hint": meta["hint"], "advice": meta["advice"],
                    "caution": meta.get("caution", ""), "candles": trend.candles_for_card(b),
                    "st_line": state.get("line"), "ema": state.get("ema"),
                    "risk_pct": round((1 - state["line"] / b[-1]["c"]) * 100, 1) if state.get("line") else None,
                    # với st_exit: số phiên xanh TRƯỚC phiên gãy (phiên đỏ hôm nay là phiên 1 của đợt đỏ)
                    "days_in_trend": _green_days_before(b) if pid == "st_exit" else state.get("days"),
                })
    # Xu hướng trước, rồi MUA trước BÁN, trong mỗi nhóm theo mã — thứ tự này là thứ tự thẻ trên giao diện
    signals.sort(key=lambda s: (s["kind"] != "trend", s["direction"] != "buy", s["symbol"]))
    return signals, stale


def _green_days_before(b: list[dict]) -> int:
    """Số phiên Supertrend xanh liên tiếp ngay trước nến cuối (nến cuối vừa lật đỏ)."""
    st = trend.supertrend(b)
    k = len(b) - 2
    n = 0
    while k >= 0 and st[k] is not None and st[k]["up"]:
        n += 1
        k -= 1
    return n


def trend_board(bars_by_symbol: dict[str, list[dict]]) -> list[dict]:
    """Trạng thái Supertrend của mọi mã (kể cả mã nến cũ) — bảng 'N xanh · M đỏ' trên giao diện."""
    out = []
    for sym in sorted(bars_by_symbol):
        s = trend.state_at(bars_by_symbol[sym])
        if s:
            out.append({"symbol": sym, **s})
    return out


def bars_for_chart(bars_by_symbol: dict[str, list[dict]], n: int = BARS_IN_CHART) -> dict[str, list[list]]:
    """{mã: [[ngày, o, h, l, c, v], …]} n nến cuối — giao diện tự tính Supertrend/EMA để vẽ tab Biểu đồ."""
    return {sym: [[b["d"].isoformat(), b["o"], b["h"], b["l"], b["c"], b["v"]] for b in bars[-n:]]
            for sym, bars in sorted(bars_by_symbol.items())}


def _history(days: int) -> list[dict]:
    """Đếm MUA/BÁN của các phiên gần nhất từ file daily — giao diện tab Lịch sử đọc ở đây."""
    out: list[dict] = []
    if not DAILY.exists():
        return out
    for f in sorted(DAILY.glob("*.json"), reverse=True)[:days]:
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        sig = d.get("signals") or []
        cand = [s for s in sig if s.get("kind", "candle") == "candle"]
        tr = [s for s in sig if s.get("kind") == "trend"]
        out.append({
            "date": d.get("trade_date") or f.stem,
            "n_buy": sum(1 for s in cand if s["direction"] == "buy"),
            "n_sell": sum(1 for s in cand if s["direction"] == "sell"),
            "n_trend_buy": sum(1 for s in tr if s["direction"] == "buy"),
            "n_trend_exit": sum(1 for s in tr if s["direction"] == "sell"),
            "items": [f"{s['symbol']} {s['name']}" for s in cand],
            "trend_items": [f"{s['symbol']} {s['name']}" for s in tr],
            "late": bool(d.get("late")),
        })
    return out


def _send_alerts(signals: list[dict], trade_iso: str, subs: list[dict], digest_threshold: int) -> dict:
    """Xu hướng: MỖI tín hiệu một thông báo riêng, không bao giờ vào bản tổng hợp (quyết định 18/09/2026).
    Mẫu nến: một thông báo/mã; quá `digest_threshold` mã → một thông báo tổng hợp."""
    res = {"sent": 0, "gone": 0, "failed": 0, "errors": [], "mode": "none", "n_symbols": 0, "n_trend": 0}
    payloads = [push.trend_payload(s, trade_iso) for s in signals if s.get("kind") == "trend"]
    res["n_trend"] = len(payloads)
    by_sym: dict[str, list[dict]] = {}
    for s in signals:
        if s.get("kind", "candle") == "candle":
            by_sym.setdefault(s["symbol"], []).append(s)
    res["n_symbols"] = len(by_sym)
    if by_sym:
        if len(by_sym) > digest_threshold:
            res["mode"] = "digest"
            payloads.append(push.digest_payload(by_sym, trade_iso))
        else:
            res["mode"] = "per_symbol"
            payloads += [push.symbol_payload(sym, sigs, trade_iso) for sym, sigs in by_sym.items()]
    elif payloads:
        res["mode"] = "trend_only"
    for p in payloads:
        r = push.send(p, subs)
        for k in ("sent", "gone", "failed"):
            res[k] += r[k]
        res["errors"] += r["errors"]
    return res


def run(force: bool = False, dry_run: bool = False, no_push: bool = False) -> int:
    now = datetime.now(TZ)
    st = _load(STATE, {})

    if not dry_run and not no_push:
        _welcome_new_devices(st, now)

    cfg = settings.load()
    disabled = set(cfg.get("patterns_disabled") or [])
    digest_threshold = int(cfg.get("digest_threshold") or DIGEST_THRESHOLD_DEFAULT)

    items, wl_source = watchlist.load()
    names = {it["symbol"]: it.get("company_name", "") for it in items}
    tickers = sorted(names)
    patterns_meta = {pid: {"name": m["name"], "direction": m["direction"], "bars": m["bars"], "hint": m["hint"],
                           "caution": m.get("caution", ""), "kind": m.get("kind", "candle")}
                     for pid, m in {**patterns.PATTERNS, **trend.SIGNALS}.items()}
    if not tickers:
        # Chưa nhập danh mục — không phải lỗi. Vẫn ghi latest.json để giao diện có file mà hiện hướng dẫn.
        log.warning("Chưa có danh mục: Variable WATCHLIST trống và docs/data/watchlist.json rỗng — không quét gì")
        if not dry_run:
            _dump(LATEST, {
                "generated_at": now.isoformat(timespec="seconds"), "trade_date": None,
                "watchlist": {"n": 0, "source": wl_source, "symbols": []},
                "source": {"dnse_ok": False, "dnse_error": "", "n_priced": 0, "unsettled": [], "late": False},
                "settings": {k: v for k, v in cfg.items() if not k.startswith("_")},
                "patterns": patterns_meta, "trend": [], "stale": [], "signals": [], "push": {"skipped": True},
                "history": _history(int(cfg.get("history_days") or 30)),
            })
            st.update({"last_run": now.isoformat(timespec="seconds"), "watchlist": {"n": 0, "source": wl_source},
                       "watchlist_error": "chưa có danh mục"})
            _dump(STATE, st)
        return 0
    st.pop("watchlist_error", None)
    log.info("Danh mục %d mã (nguồn %s)", len(tickers), wl_source)

    bars, unsettled = fetch_bars(tickers)
    if not bars:
        log.error("DNSE không trả về gì: %s", dnse.last_error)
        st.update({"dnse_error": dnse.last_error, "last_run": now.isoformat(timespec="seconds")})
        _dump(STATE, st)
        return 3
    trade_date = max(b[-1]["d"] for b in bars.values())
    trade_iso = trade_date.isoformat()
    daily_file = DAILY / f"{trade_iso}.json"
    if daily_file.exists() and not force:
        log.info("Đã có %s — không chạy lại (dùng --force nếu muốn)", daily_file.name)
        return 0
    if unsettled and not force:
        msg = (f"Nguồn chưa chốt phiên {trade_iso}: {len(unsettled)}/{len(bars)} mã chưa có nến ATC "
               f"({', '.join(unsettled[:8])}{'…' if len(unsettled) > 8 else ''}) — chờ cron sau")
        log.warning(msg)
        st.update({"last_run": now.isoformat(timespec="seconds"),
                   "unsettled": {"trade_date": trade_iso, "tickers": unsettled,
                                 "at": now.isoformat(timespec="seconds")}})
        _dump(STATE, st)
        return 0
    late = bool(st.pop("unsettled", None))   # lần trước phải chờ → ghi nhớ để tab Lịch sử hiện "nguồn chốt muộn"
    if (now.date() - trade_date).days > 4:
        log.warning("Phiên gần nhất %s cách hôm nay quá 4 ngày — DNSE có thể chưa cập nhật", trade_iso)

    signals, stale = detect_signals(bars, names, trade_date, disabled)
    board = trend_board(bars)
    log.info("Phiên %s: %d tín hiệu (%d xu hướng) trên %d mã, %d mã nến cũ, Supertrend %d xanh / %d đỏ",
             trade_iso, len(signals), sum(1 for s in signals if s["kind"] == "trend"),
             len({s["symbol"] for s in signals}), len(stale),
             sum(1 for t in board if t["up"]), sum(1 for t in board if not t["up"]))

    push_res: dict = {"skipped": True}
    if not dry_run and not no_push:
        subs, src = push.subscriptions()
        push_res = {"source": src, "n_devices": len(subs)}
        if subs and push.configured():
            push_res.update(_send_alerts(signals, trade_iso, subs, digest_threshold))
            if now.weekday() == 0:  # thứ Hai: nhịp tim để biết đường dây còn sống
                week_n = _signals_last_week(now) + len(signals)
                push_res["heartbeat"] = push.send(push.heartbeat_payload(week_n, trade_iso), subs)["sent"]
            if push.test_requested():
                push_res["test"] = push.send(push.test_payload(), subs)["sent"]
        elif not push.configured():
            push_res["errors"] = ["Thiếu khoá VAPID"]
        if push_res.get("gone"):
            st["push_gone_at"] = now.isoformat(timespec="seconds")

    latest = {
        "generated_at": now.isoformat(timespec="seconds"), "trade_date": trade_iso,
        # symbols: giao diện điền sẵn ô nhập danh mục ở tab Cài đặt
        "watchlist": {"n": len(tickers), "source": wl_source, "symbols": tickers},
        "source": {"dnse_ok": bool(dnse.last_ok), "dnse_error": dnse.last_error,
                   "n_priced": len(bars), "unsettled": unsettled, "late": late},
        "settings": {k: v for k, v in cfg.items() if not k.startswith("_")},
        "patterns": patterns_meta,
        "trend": board, "stale": stale, "signals": signals, "push": push_res,
    }

    if dry_run:
        print(json.dumps({k: v for k, v in latest.items() if k not in ("signals", "patterns", "trend")},
                         ensure_ascii=False, indent=1, default=str))
        print(f"  Supertrend: {sum(1 for t in board if t['up'])} xanh / {sum(1 for t in board if not t['up'])} đỏ")
        for s in signals:
            print(f"  {'▲' if s['direction'] == 'buy' else '▼'} {s['symbol']:<5} {s['name']:<30} "
                  f"giá {s['price']:.2f} ({s['change_pct']:+.1f}%)" if s["change_pct"] is not None
                  else f"  {s['symbol']} {s['name']}")
        return 0

    _dump(daily_file, {"trade_date": trade_iso, "generated_at": latest["generated_at"], "late": late,
                       "signals": signals, "stale": stale})
    latest["history"] = _history(int(cfg.get("history_days") or 30))
    _dump(LATEST, latest)
    # Nến cho tab Biểu đồ — file riêng để latest.json không phình; giao diện tải khi mở tab.
    BARS.write_text(json.dumps({"trade_date": trade_iso, "bars": bars_for_chart(bars)}, ensure_ascii=False,
                               separators=(",", ":")), encoding="utf-8")
    st.update({"last_run": now.isoformat(timespec="seconds"), "last_trade_date": trade_iso,
               "dnse_error": dnse.last_error, "push": push_res,
               "watchlist": {"n": len(tickers), "source": wl_source}})
    _dump(STATE, st)
    log.info("Xong: %d mã, %d tín hiệu, push %s", len(bars), len(signals), push_res)
    return 0


def _welcome_new_devices(st: dict, now: datetime) -> None:
    """Máy mới đăng ký → gửi ngay một thông báo chào mừng, TRƯỚC bước idempotent, để người dùng
    chỉ cần Re-run là biết đường dây thông."""
    subs, src = push.subscriptions()
    st["devices"] = {"n": len(subs), "source": src, "vapid": push.configured(),
                     "checked_at": now.isoformat(timespec="seconds")}
    if not subs or not push.configured():
        _dump(STATE, st)
        return
    known = set(st.get("known_subs") or [])
    new = [s for s in subs if push._sub_id(s) not in known]
    if new:
        payload = {"kind": "welcome", "title": "Đã kết nối — máy này sẽ nhận cảnh báo",
                   "body": "Mẫu hình nến + xu hướng Supertrend sau phiên 15:35 các ngày T2–T6, nhịp tim mỗi thứ Hai.",
                   "url": "./#today", "tag": "cw-welcome"}
        r = push.send(payload, new)
        log.info("Chào mừng %d máy mới (nguồn %s): %s", len(new), src, r)
        st["welcome"] = {"at": now.isoformat(timespec="seconds"), **r}
    st["known_subs"] = sorted(known | {push._sub_id(s) for s in subs})
    _dump(STATE, st)


def _signals_last_week(now: datetime) -> int:
    n = 0
    for i in range(1, 8):
        f = DAILY / f"{(now - timedelta(days=i)).date().isoformat()}.json"
        if f.exists():
            try:
                n += len(json.loads(f.read_text(encoding="utf-8")).get("signals") or [])
            except Exception:  # noqa: BLE001
                pass
    return n


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="chạy lại dù hôm nay đã có file")
    ap.add_argument("--dry-run", action="store_true", help="in kết quả, không ghi file, không push")
    ap.add_argument("--no-push", action="store_true", help="ghi file nhưng không gửi thông báo")
    a = ap.parse_args()
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(run(force=a.force, dry_run=a.dry_run, no_push=a.no_push))


if __name__ == "__main__":
    main()
