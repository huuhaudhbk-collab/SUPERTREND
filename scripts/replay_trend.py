"""Tua lịch sử tín hiệu xu hướng Supertrend × EMA10 (job/trend.py) — backtest theo LỆNH, chỉ mua.

    venv\\Scripts\\python -m scripts.replay_trend                       # danh mục WATCHLIST, 2500 ngày (~7 năm)
    venv\\Scripts\\python -m scripts.replay_trend --symbols HPG,VNM --days 750
    venv\\Scripts\\python -m scripts.replay_trend --md > reports/replay-trend.md
    venv\\Scripts\\python -m scripts.replay_trend --exit both           # biến thể: thoát cả khi rớt EMA10

Quy tắc mô phỏng (giữ sát thực tế VN):
  * Vào khi job phát st_buy, ra khi job phát st_exit (mặc định) — hoặc `--exit both`: ra thêm khi đóng cửa
    rớt dưới EMA10 (đo được là hại: +1,24 %/lệnh so với +6,63 %).
  * Khớp ở GIÁ MỞ CỬA phiên kế tiếp (tín hiệu chỉ biết sau ATC); T+2: bán sớm nhất khi i ≥ mua + 2.
  * Phí 0,15 % mỗi chiều + thuế bán 0,1 % (≈ 0,4 %/vòng). Chưa tính trượt giá.
  * Mốc 1: "mua đại rồi giữ k phiên" trên cùng chuỗi giá, k = trung vị số phiên giữ (không phí → so với
    cột gross là công bằng nhất). Mốc 2: mua-và-giữ cả kỳ cùng mã: lợi suất, sụt giảm sâu nhất.
  * 39 mã này được chọn HÔM NAY (mã lớn còn sống khoẻ) → cả hai phía đều hưởng lợi hậu nghiệm; phép so
    sánh vẫn công bằng vì cùng chuỗi giá, nhưng con số tuyệt đối cao hơn thực tế.
"""
from __future__ import annotations

import argparse
import math
import sys
from collections import defaultdict

from common import dnse
from job import trend, watchlist

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

FEE, TAX = 0.0015, 0.001


def _stats(xs: list[float]) -> dict:
    n = len(xs)
    if not n:
        return {"n": 0, "mean": None, "win": None, "t": None, "med": None}
    mean = sum(xs) / n
    win = sum(1 for x in xs if x > 0) / n
    med = sorted(xs)[n // 2]
    if n < 2:
        return {"n": n, "mean": mean, "win": win, "t": None, "med": med}
    sd = math.sqrt(sum((x - mean) ** 2 for x in xs) / (n - 1))
    return {"n": n, "mean": mean, "win": win, "t": mean / (sd / math.sqrt(n)) if sd > 0 else None, "med": med}


def backtest(bars: list[dict], exit_mode: str, fee: float, tax: float) -> tuple[list[dict], int]:
    """Trả (lệnh, i0). Lệnh: entry_i, exit_i, gross, net, hold, year, open."""
    st, em = trend.supertrend(bars), trend.ema(bars)
    i0 = trend.WARMUP
    trades: list[dict] = []
    n = len(bars)
    if n <= i0 + 5:
        return trades, i0
    pos = None

    def hold(i):
        return st[i] is not None and em[i] is not None and st[i]["up"] and bars[i]["c"] > em[i]

    def mk(pos, exit_i, exit_px, open_):
        gross = exit_px / pos["px"] - 1
        net = exit_px * (1 - fee - tax) / (pos["px"] * (1 + fee)) - 1
        return {"entry_i": pos["i"], "exit_i": exit_i, "gross": gross, "net": net, "hold": exit_i - pos["i"],
                "year": bars[pos["i"]]["d"].year, "open": open_}

    for i in range(i0, n):
        if pos is None:
            if "st_buy" in trend.detect_at(bars, i) and i + 1 < n:
                pos = {"i": i + 1, "px": bars[i + 1]["o"]}
        elif i >= pos["i"] + 2:
            leave = (not st[i]["up"]) if exit_mode == "st" else (not hold(i))
            if leave:
                if i + 1 < n:
                    trades.append(mk(pos, i + 1, bars[i + 1]["o"], False))
                else:
                    trades.append(mk(pos, n - 1, bars[n - 1]["c"], True))
                pos = None
    if pos is not None:
        trades.append(mk(pos, n - 1, bars[n - 1]["c"], True))
    return trades, i0


def equity(bars, trades, i0, fee):
    """Đường vốn theo đóng cửa (vốn 1.0 tại i0) và mua-và-giữ, để tính lợi suất cả kỳ + sụt giảm sâu nhất."""
    n = len(bars)
    eq, bh = [], []
    base, ti = 1.0, 0
    for i in range(i0, n):
        while ti < len(trades) and trades[ti]["exit_i"] < i:
            base *= 1 + trades[ti]["net"]
            ti += 1
        cur = trades[ti] if ti < len(trades) and i >= trades[ti]["entry_i"] else None
        if cur:
            eq.append(base * (1 + cur["net"]) if i == cur["exit_i"] else base * (bars[i]["c"] / bars[cur["entry_i"]]["o"]) / (1 + fee))
        else:
            eq.append(base)
        bh.append(bars[i]["c"] / bars[i0]["c"])
    return eq, bh


def mdd(xs):
    peak, worst = -1e9, 0.0
    for v in xs:
        peak = max(peak, v)
        worst = min(worst, v / peak - 1)
    return worst


def run(symbols: list[str], days: int, md: bool, exit_mode: str, fee: float, tax: float) -> int:
    all_net, all_gross, holds = [], [], []
    per_sym, per_year = [], defaultdict(lambda: {"net": [], "strat": [], "bh": []})
    series: dict[str, tuple] = {}
    with dnse.DnseClient(days=days) as c:
        for k, sym in enumerate(symbols, 1):
            bars = c.daily(sym)
            if len(bars) < trend.WARMUP + 60:
                print(f"  {sym:<6} thiếu dữ liệu ({len(bars)} nến)", file=sys.stderr)
                continue
            trades, i0 = backtest(bars, exit_mode, fee, tax)
            eq, bh = equity(bars, trades, i0, fee)
            series[sym] = (bars, i0)
            nets = [t["net"] for t in trades]
            s = _stats(nets)
            per_sym.append({"sym": sym, "n": len(trades), "win": s["win"], "mean": s["mean"], "strat": eq[-1] - 1,
                            "bh": bh[-1] - 1, "mdd": mdd(eq), "bh_mdd": mdd(bh), "sessions": len(bars) - i0})
            for t in trades:
                all_net.append(t["net"]); all_gross.append(t["gross"]); holds.append(t["hold"])
                per_year[t["year"]]["net"].append(t["net"])
            # lợi suất theo năm: vốn cuối năm / vốn đầu năm
            y0, e0, b0 = None, None, None
            for j, i in enumerate(range(i0, len(bars))):
                y = bars[i]["d"].year
                if y != y0:
                    if y0 is not None:
                        per_year[y0]["strat"].append(eq[j - 1] / e0 - 1); per_year[y0]["bh"].append(bh[j - 1] / b0 - 1)
                    y0, e0, b0 = y, eq[j], bh[j]
            per_year[y0]["strat"].append(eq[-1] / e0 - 1); per_year[y0]["bh"].append(bh[-1] / b0 - 1)
            if k % 10 == 0:
                print(f"  ... {k}/{len(symbols)} mã", file=sys.stderr)
    if not per_sym:
        print("Không lấy được dữ liệu mã nào.")
        return 1
    s, g = _stats(all_net), _stats(all_gross)
    wins, losses = [x for x in all_net if x > 0], [x for x in all_net if x <= 0]
    pf = (sum(wins) / -sum(losses)) if losses and sum(losses) < 0 else None
    med_hold = int(_stats(holds)["med"] or 0)
    base = []
    for bars, i0 in series.values():
        base += [bars[i + med_hold]["c"] / bars[i]["c"] - 1 for i in range(i0, len(bars) - med_hold)]
    bs = _stats(base)
    months = sum(p["sessions"] for p in per_sym) / 21 / len(per_sym)
    avg = lambda key: sum(p[key] for p in per_sym) / len(per_sym)  # noqa: E731
    pct = lambda v: "—" if v is None else f"{v * 100:+.2f}%"  # noqa: E731
    f1 = lambda v: "—" if v is None else f"{v:.2f}"  # noqa: E731
    line = (lambda cells: "| " + " | ".join(cells) + " |") if md else (lambda cells: "  ".join(cells))

    print(f"\n{len(per_sym)} mã · {days} ngày (~{months:.0f} tháng, TB {months * 21:.0f} phiên/mã) · thoát: "
          f"{'chỉ khi Supertrend đỏ' if exit_mode == 'st' else 'Supertrend đỏ HOẶC rớt EMA10'} · phí {fee * 100:.2f}%/chiều + thuế {tax * 100:.1f}%\n")
    print(f"Lệnh mua: {s['n']} ({s['n'] / months:.1f}/tháng cả danh mục ≈ {s['n'] / months / 21:.2f}/phiên) · thắng {pct(s['win'])} · "
          f"lãi TB/lệnh net {pct(s['mean'])} (gross {pct(g['mean'])}) · t = {f1(s['t'])} · PF {f1(pf)} · giữ TB {f1(_stats(holds)['mean'])} phiên, trung vị {med_hold}")
    print(f"Mốc 1 — mua đại rồi giữ {med_hold} phiên (không phí): {pct(bs['mean'])} · thắng {pct(bs['win'])} (n = {bs['n']})")
    print(f"Mốc 2 — cả kỳ, TB mã: chiến lược {pct(avg('strat'))} (MDD {pct(avg('mdd'))}) · mua-và-giữ {pct(avg('bh'))} (MDD {pct(avg('bh_mdd'))}) · "
          f"thắng B&H {sum(1 for p in per_sym if p['strat'] > p['bh'])}/{len(per_sym)} mã\n")
    hdr = ["Năm", "Lệnh", "Lãi TB/lệnh", "Thắng", "Chiến lược", "Mua-và-giữ"]
    print(line(hdr))
    if md:
        print("|" + "---|" * len(hdr))
    for y in sorted(per_year):
        v = per_year[y]; ys = _stats(v["net"])
        print(line([str(y), str(ys["n"]), pct(ys["mean"]), "—" if ys["win"] is None else f"{ys['win'] * 100:.0f}%",
                    pct(sum(v["strat"]) / len(v["strat"])) if v["strat"] else "—", pct(sum(v["bh"]) / len(v["bh"])) if v["bh"] else "—"]))
    print()
    hdr = ["Mã", "Lệnh", "Thắng", "Lãi TB/lệnh", "Chiến lược", "Mua-và-giữ", "MDD CL", "MDD B&H"]
    print(line(hdr))
    if md:
        print("|" + "---|" * len(hdr))
    for p in sorted(per_sym, key=lambda p: -p["strat"]):
        print(line([p["sym"], str(p["n"]), "—" if p["win"] is None else f"{p['win'] * 100:.0f}%", pct(p["mean"]),
                    pct(p["strat"]), pct(p["bh"]), pct(p["mdd"]), pct(p["bh_mdd"])]))
    print("\nĐáng dùng khi: lãi TB/lệnh > mốc 1 và t > 2; lợi suất ÷ |MDD| không kém mua-và-giữ; lưới tham số lân cận không gãy "
          "(lưới 18 tổ hợp xem supertrend-lab). Tỷ lệ thắng thấp là bản chất hệ thống theo xu hướng.")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Tua lịch sử Supertrend × EMA10")
    p.add_argument("--symbols", default="")
    p.add_argument("--days", type=int, default=2500)
    p.add_argument("--md", action="store_true")
    p.add_argument("--exit", choices=["st", "both"], default="st")
    p.add_argument("--no-fee", action="store_true")
    a = p.parse_args()
    symbols = [s.strip().upper() for s in a.symbols.split(",") if s.strip()] if a.symbols else [it["symbol"] for it in watchlist.load()[0]]
    if not symbols:
        print("Không có mã nào để chạy.")
        return 2
    return run(symbols, a.days, a.md, a.exit, 0.0 if a.no_fee else FEE, 0.0 if a.no_fee else TAX)


if __name__ == "__main__":
    sys.exit(main())
