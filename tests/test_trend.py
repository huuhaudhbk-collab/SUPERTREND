"""Supertrend × EMA10: toán tay tính, luật dải final, hai tín hiệu, trạng thái bảng xu hướng."""
from datetime import date, timedelta

from job import trend


def bar(o, h, l, c, k, v=1000):
    return {"o": o, "h": h, "l": l, "c": c, "v": v, "d": date(2026, 1, 1) + timedelta(days=k), "t": 0}


def flat(n, px=100.0, start=0):
    return [bar(px, px + 1, px - 1, px, start + k) for k in range(n)]


def test_ema_moi_bang_sma():
    b = [bar(c, c, c, c, k) for k, c in enumerate([1, 2, 3, 4, 5])]
    assert trend.ema(b, 3) == [None, None, 2.0, 3.0, 4.0]


def test_atr_wilder_tay_tinh():
    # TR: 2, 2, rồi nến gap (16,12,14) sau đóng 12 → TR = max(4, 4, 0) = 4 → (2·1 + 4)/2 = 3
    b = [bar(11, 12, 10, 11, 0), bar(12, 13, 11, 12, 1), bar(14, 16, 12, 14, 2)]
    assert trend.atr_wilder(b, 2) == [None, 2.0, 3.0]


def test_supertrend_xanh_dai_duoi_khong_giam_va_sap_thi_do():
    up = [bar(100 + k, 101 + k, 99 + k, 100.5 + k, k) for k in range(40)]
    st = trend.supertrend(up)
    first = next(i for i, s in enumerate(st) if s and s["up"])
    assert first > 0
    for i in range(first + 1, len(up)):
        assert st[i]["up"] and st[i]["line"] >= st[i - 1]["line"] - 1e-9
    crash = up + [bar(139, 139, 120, 121, 40)]
    assert trend.supertrend(crash)[-1]["up"] is False


def _green_after_red(n_green: int):
    """60 nến đi ngang, 12 nến sập (đỏ), rồi n_green nến tăng đều → lật xanh và vượt EMA."""
    b = flat(60)
    px = 100.0
    for k in range(12):
        px -= 3
        b.append(bar(px + 1, px + 1.5, px - 1, px, 60 + k))
    for k in range(n_green):
        px += 2.5
        b.append(bar(px - 1, px + 1, px - 1.5, px, 72 + k))
    return b


def rising(n, start=0):
    return [bar(100 + k, 101 + k, 99 + k, 100.5 + k, start + k) for k in range(n)]


def test_di_ngang_hoan_toan_thi_khong_bao_gi():
    # Khởi tạo màu đỏ, giá không vượt nổi dải trên (giá + 3 ATR) → đỏ mãi, không tín hiệu nào
    b = flat(60)
    assert trend.supertrend(b)[-1]["up"] is False and trend.detect_at(b, -1) == []


def test_st_exit_dung_phien_lat_do():
    b = rising(60)
    assert trend.supertrend(b)[-1]["up"] is True
    # sập 12 % (> 3 ATR) → lật đỏ đúng phiên đó, phiên sau không báo lại
    b2 = b + [bar(159, 159, 140, 141, 60)]
    assert trend.detect_at(b2, -1) == ["st_exit"]
    assert "st_exit" not in trend.detect_at(b2 + [bar(141, 142, 139, 140, 61)], -1)


def test_st_buy_chi_bao_mot_lan_sau_dot_do():
    hits = []
    for n in range(1, 25):
        b = _green_after_red(n)
        hits.append((n, "st_buy" in trend.detect_at(b, -1)))
    firsts = [n for n, h in hits if h]
    assert len(firsts) == 1, f"phải báo MUA đúng một lần, thực tế ở các phiên {firsts}"


def test_khong_bao_khi_chua_du_warmup():
    assert trend.detect_at(flat(trend.WARMUP - 1), -1) == []


def test_disabled_duoc_ton_trong():
    b = rising(60) + [bar(159, 159, 140, 141, 60)]
    assert trend.detect_at(b, -1, {"st_exit"}) == []


def test_state_va_candles_cho_the():
    b = _green_after_red(20)
    s = trend.state_at(b)
    assert s["up"] is True and s["days"] >= 1 and s["above_ema"] is True
    assert s["since"] == b[len(b) - s["days"]]["d"].isoformat()
    cs = trend.candles_for_card(b)
    assert len(cs) == trend.BARS_IN_CARD and cs[-1]["up"] is True and cs[-1]["st"] == s["line"]


def test_sig_trong_candles_khop_detect_at():
    b = rising(60) + [bar(159, 159, 140, 141, 60)] + _green_after_red(20)[-20:]
    cs = trend.candles_for_card(b, n=len(b))
    want = {"st_buy": "buy", "st_exit": "exit"}
    for j, c in enumerate(cs):
        hits = trend.detect_at(b, j)
        assert c["sig"] == (want[hits[0]] if hits else None), f"phiên {j}: {c['sig']} ≠ {hits}"
    assert any(c["sig"] == "exit" for c in cs)
