"""Job sau phiên: idempotent theo file ngày, nguồn chưa chốt thì không ghi, mã nến cũ không xét
mẫu, push gộp theo mã / tổng hợp khi quá nhiều. DNSE, danh mục, push đều mock."""
from datetime import date, timedelta

import pytest

from job import push, run_daily as rd
from job.patterns import PATTERNS


def bar(o, h, l, c, d):
    return {"o": o, "h": h, "l": l, "c": c, "v": 1000, "d": d, "t": 0}


def base(d_end: date, n: int = 12):
    """n nến nền, nến cuối ngày d_end."""
    return [bar(100, 101.5, 99.5, 101, d_end - timedelta(days=n - 1 - k)) for k in range(n)]


def with_bull_engulfing(d_end: date):
    b = base(d_end - timedelta(days=2), 10)
    b += [bar(101, 101.3, 99.7, 100, d_end - timedelta(days=1)), bar(99.9, 101.5, 99.6, 101.2, d_end)]
    return b


@pytest.fixture
def site(tmp_path, monkeypatch):
    monkeypatch.setattr(rd, "LATEST", tmp_path / "latest.json")
    monkeypatch.setattr(rd, "STATE", tmp_path / "state.json")
    monkeypatch.setattr(rd, "DAILY", tmp_path / "daily")
    monkeypatch.setattr(rd, "BARS", tmp_path / "bars.json")
    monkeypatch.setattr(rd.watchlist, "load", lambda: ([{"symbol": "HPG", "company_name": "Hoà Phát"},
                                                         {"symbol": "VNM", "company_name": "Vinamilk"}], "cache"))
    monkeypatch.setattr(rd.settings, "load", lambda: {"patterns_disabled": [], "history_days": 30})
    return tmp_path


@pytest.fixture
def sent(monkeypatch):
    calls: list[dict] = []
    monkeypatch.setattr(push, "subscriptions", lambda: ([{"endpoint": "e1", "keys": {}}], "fallback"))
    monkeypatch.setattr(push, "configured", lambda: True)
    monkeypatch.setattr(push, "test_requested", lambda: False)
    monkeypatch.setattr(push, "send", lambda payload, subs: (calls.append(payload) or {"sent": len(subs), "gone": 0, "failed": 0, "errors": []}))
    return calls


def test_detect_signals_bo_qua_ma_nen_cu():
    today = date(2026, 9, 16)
    bars = {"HPG": with_bull_engulfing(today), "IDP": with_bull_engulfing(today - timedelta(days=9))}
    signals, stale = rd.detect_signals(bars, {"HPG": "Hoà Phát", "IDP": "IDP"}, today, set())
    assert [s["symbol"] for s in signals] == ["HPG"]
    assert signals[0]["pattern"] == "bull_engulfing" and signals[0]["name"] == PATTERNS["bull_engulfing"]["name"]
    assert len(signals[0]["candles"]) == rd.CANDLES_IN_CARD
    tc = signals[0]["trend_candles"]
    assert 0 < len(tc) <= rd.TREND_CANDLES_IN_CARD and all({"st", "up", "ema"} <= set(c) for c in tc)
    assert stale == [{"symbol": "IDP", "last_date": "2026-09-07"}]


def test_detect_signals_ton_trong_patterns_disabled():
    today = date(2026, 9, 16)
    signals, _ = rd.detect_signals({"HPG": with_bull_engulfing(today)}, {}, today, {"bull_engulfing"})
    assert signals == []


def test_job_ghi_file_va_push_theo_ma(site, sent, monkeypatch):
    today = date(2026, 9, 16)
    monkeypatch.setattr(rd, "fetch_bars", lambda tickers, client=None, days=120: ({"HPG": with_bull_engulfing(today), "VNM": base(today)}, []))
    assert rd.run() == 0
    assert (site / "daily" / "2026-09-16.json").exists()
    kinds = [p["kind"] for p in sent]
    assert kinds.count("welcome") == 1          # máy mới → chào mừng
    assert kinds.count("candle") == 1           # HPG có mẫu, VNM không
    cand = next(p for p in sent if p["kind"] == "candle")
    assert cand["symbol"] == "HPG" and cand["tag"] == "cw-HPG" and "Nhấn chìm tăng" in cand["title"]
    latest = rd._load(site / "latest.json", None)
    assert latest["trade_date"] == "2026-09-16" and len(latest["signals"]) == 1
    assert latest["history"][0] == {"date": "2026-09-16", "n_buy": 1, "n_sell": 0, "n_trend_buy": 0, "n_trend_exit": 0,
                                    "items": ["HPG Nhấn chìm tăng"], "trend_items": [], "late": False}
    assert latest["patterns"]["st_buy"]["kind"] == "trend" and latest["patterns"]["bull_engulfing"]["kind"] == "candle"
    assert (site / "bars.json").exists()


def test_job_khong_chay_lai_cung_phien(site, sent, monkeypatch):
    today = date(2026, 9, 16)
    monkeypatch.setattr(rd, "fetch_bars", lambda tickers, client=None, days=120: ({"HPG": with_bull_engulfing(today)}, []))
    assert rd.run() == 0
    n = len([p for p in sent if p["kind"] == "candle"])
    assert rd.run() == 0
    assert len([p for p in sent if p["kind"] == "candle"]) == n   # không bắn lại


def test_nguon_chua_chot_thi_khong_ghi(site, sent, monkeypatch):
    today = date(2026, 9, 16)
    monkeypatch.setattr(rd, "fetch_bars", lambda tickers, client=None, days=120: ({"HPG": with_bull_engulfing(today)}, ["HPG"]))
    assert rd.run() == 0
    assert not (site / "daily" / "2026-09-16.json").exists()
    st = rd._load(site / "state.json", {})
    assert st["unsettled"]["tickers"] == ["HPG"]
    assert not [p for p in sent if p["kind"] == "candle"]


def test_qua_nhieu_ma_thi_gui_tong_hop(site, sent, monkeypatch):
    today = date(2026, 9, 16)
    syms = [f"S{i:02d}" for i in range(8)]
    monkeypatch.setattr(rd.watchlist, "load", lambda: ([{"symbol": s, "company_name": s} for s in syms], "cache"))
    monkeypatch.setattr(rd, "fetch_bars", lambda tickers, client=None, days=120: ({s: with_bull_engulfing(today) for s in syms}, []))
    assert rd.run() == 0
    kinds = [p["kind"] for p in sent]
    assert kinds.count("digest") == 1 and kinds.count("candle") == 0
    dg = next(p for p in sent if p["kind"] == "digest")
    assert dg["title"].startswith("8 mã có mẫu hình") and "S00 ▲ Nhấn chìm tăng" in dg["body"]


def with_st_exit(d_end: date):
    """60 nến tăng đều (Supertrend xanh) rồi nến sập 12 % ngày d_end → Supertrend lật đỏ."""
    b = [bar(100 + k, 101 + k, 99 + k, 100.5 + k, d_end - timedelta(days=60 - k)) for k in range(60)]
    return b + [bar(159, 159, 140, 141, d_end)]


def test_xu_huong_di_rieng_khong_gop_vao_tong_hop(site, sent, monkeypatch):
    today = date(2026, 9, 16)
    syms = [f"S{i:02d}" for i in range(8)]
    bars = {s: with_bull_engulfing(today) for s in syms}
    bars["HPG"] = with_st_exit(today)
    monkeypatch.setattr(rd.watchlist, "load", lambda: ([{"symbol": s, "company_name": s} for s in bars], "cache"))
    monkeypatch.setattr(rd, "fetch_bars", lambda tickers, client=None, days=120: (bars, []))
    assert rd.run() == 0
    kinds = [p["kind"] for p in sent]
    assert kinds.count("digest") == 1 and kinds.count("trend") == 1 and kinds.count("candle") == 0
    tr = next(p for p in sent if p["kind"] == "trend")
    assert tr["title"] == "▼ THOÁT HPG · Supertrend lật đỏ" and tr["tag"] == "cw-st-HPG"
    assert "xanh được" in tr["body"] and "phiên 16/09" in tr["body"]
    dg = next(p for p in sent if p["kind"] == "digest")
    assert "HPG" not in dg["body"] and dg["title"].startswith("8 mã có mẫu hình")
    latest = rd._load(site / "latest.json", None)
    assert latest["signals"][0]["kind"] == "trend" and latest["signals"][0]["symbol"] == "HPG"   # xu hướng đứng đầu
    assert latest["history"][0]["n_trend_exit"] == 1 and latest["history"][0]["trend_items"] == ["HPG Supertrend lật đỏ"]
    assert {t["symbol"] for t in latest["trend"]} == set(bars)
    hpg = next(t for t in latest["trend"] if t["symbol"] == "HPG")
    assert hpg["up"] is False and hpg["days"] == 1 and hpg["since"] == "2026-09-16"


def test_trend_payload_mua_kem_dung_lo():
    sig = {"symbol": "DCM", "pattern": "st_buy", "direction": "buy", "price": 32.6, "change_pct": 5.7,
           "st_line": 29.58, "risk_pct": 9.3, "days_in_trend": 1}
    p = push.trend_payload(sig, "2026-09-03")
    assert p["title"] == "▲ MUA DCM · Supertrend xanh + trên EMA10"
    assert p["body"] == "giá 32.60 (+5.7%) · phiên 03/09 · dừng lỗ 29.58 (−9.3%)"
    assert p["kind"] == "trend" and p["tag"] == "cw-st-DCM"


def test_symbol_payload_gop_nhieu_mau():
    sigs = [{"pattern": "morning_star", "direction": "buy", "price": 26.5, "change_pct": 2.1},
            {"pattern": "morning_doji_star", "direction": "buy", "price": 26.5, "change_pct": 2.1}]
    p = push.symbol_payload("HPG", sigs, "2026-09-16")
    assert p["title"] == "▲ MUA HPG · 2 mẫu hình"
    assert p["body"] == "giá 26.50 (+2.1%) · phiên 16/09 · Sao mai, Sao mai Doji"
    assert p["direction"] == "buy"


def test_chua_co_danh_muc_thi_ghi_latest_rong_va_thoat_0(site, monkeypatch):
    """Danh mục trống là trạng thái bình thường trước khi nhập mã: Actions xanh, latest.json có để giao
    diện hiện hướng dẫn, không ghi file daily, không gọi DNSE."""
    monkeypatch.setattr(rd.watchlist, "load", lambda: ([], "none"))
    monkeypatch.setattr(rd, "fetch_bars", lambda *a, **k: (_ for _ in ()).throw(AssertionError("không được gọi DNSE")))
    assert rd.run(no_push=True) == 0
    latest = rd._load(site / "latest.json", None)
    assert latest["trade_date"] is None and latest["watchlist"] == {"n": 0, "source": "none", "symbols": []}
    assert latest["signals"] == [] and "bull_engulfing" in latest["patterns"]
    assert not (site / "daily").exists()
    assert rd._load(site / "state.json", {})["watchlist_error"] == "chưa có danh mục"


def test_latest_mang_symbols_de_giao_dien_dien_san(site, sent, monkeypatch):
    today = date(2026, 9, 16)
    monkeypatch.setattr(rd, "fetch_bars", lambda tickers, client=None, days=120: ({"HPG": base(today), "VNM": base(today)}, []))
    assert rd.run() == 0
    assert rd._load(site / "latest.json", None)["watchlist"] == {"n": 2, "source": "cache", "symbols": ["HPG", "VNM"]}
