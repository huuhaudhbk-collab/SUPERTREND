"""Tua lịch sử: mỗi mẫu xuất hiện bao nhiêu lần, và sau đó giá đi đâu — CHẠY TRƯỚC KHI BẬT PUSH.

    venv\\Scripts\\python -m scripts.replay                       # danh mục WATCHLIST, 750 ngày
    venv\\Scripts\\python -m scripts.replay --symbols HPG,VNM --days 365
    venv\\Scripts\\python -m scripts.replay --md > reports/replay.md  # bảng Markdown để dán README

Cách đọc (bài học 11/09/2026 — bộ lọc ADX/MA từng bị gỡ vì con số không tái lập được):
  * MUA và BÁN tách riêng: VN không bán khống, tín hiệu BÁN chỉ có giá trị "thoát hàng", nên với
    BÁN, lợi suất ÂM sau tín hiệu = tín hiệu đúng.
  * Luôn so với mốc "mua đại rồi giữ k phiên" trên CÙNG chuỗi giá — mẫu nào không hơn mốc này
    thì không có giá trị dự báo, dù tỷ lệ đúng trông đẹp.
  * t-stat > 2 mới đáng để ý; n < 30 thì con số chỉ để tham khảo.
  * Lợi suất tính từ giá đóng cửa nến xác nhận (lúc app báo) tới đóng cửa k phiên sau — chưa trừ
    phí, chưa tính T+2 (mua T, bán sớm nhất T+2 chiều... thực tế là phiên T+3).
"""
from __future__ import annotations

import argparse
import math
import sys
from collections import defaultdict

from common import dnse
from job import watchlist
from job.patterns import PATTERNS, scan_history

# Console Windows mặc định cp1252 → chữ có dấu làm print() chết. Ép UTF-8 một lần ở đây.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

HORIZONS = (1, 5, 10)
SESSIONS_PER_MONTH = 21.0


def _stats(rets: list[float]) -> dict:
    n = len(rets)
    if n == 0:
        return {"n": 0, "mean": None, "win": None, "t": None}
    mean = sum(rets) / n
    win = sum(1 for r in rets if r > 0) / n
    if n < 2:
        return {"n": n, "mean": mean, "win": win, "t": None}
    var = sum((r - mean) ** 2 for r in rets) / (n - 1)
    sd = math.sqrt(var)
    t = mean / (sd / math.sqrt(n)) if sd > 0 else None
    return {"n": n, "mean": mean, "win": win, "t": t}


def _fwd(bars: list[dict], i: int, k: int) -> float | None:
    if i + k >= len(bars):
        return None
    return bars[i + k]["c"] / bars[i]["c"] - 1.0


def run(symbols: list[str], days: int, md: bool) -> int:
    per_pat: dict[str, dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))
    count: dict[str, int] = defaultdict(int)
    base: dict[int, list[float]] = defaultdict(list)
    total_bars = 0
    n_ok = 0
    with dnse.DnseClient(days=days) as c:
        for k, sym in enumerate(symbols, 1):
            bars = c.daily(sym)
            if len(bars) < 40:
                print(f"  {sym:<6} thiếu dữ liệu ({len(bars)} nến)", file=sys.stderr)
                continue
            n_ok += 1
            total_bars += len(bars)
            for h in HORIZONS:
                for i in range(len(bars) - h):
                    base[h].append(_fwd(bars, i, h))
            for hit in scan_history(bars):
                pid, i = hit["pattern"], hit["i"]
                count[pid] += 1
                for h in HORIZONS:
                    r = _fwd(bars, i, h)
                    if r is not None:
                        per_pat[pid][h].append(r)
            if k % 10 == 0:
                print(f"  ... {k}/{len(symbols)} mã", file=sys.stderr)

    if n_ok == 0:
        print("Không lấy được dữ liệu mã nào.")
        return 1
    months = total_bars / n_ok / SESSIONS_PER_MONTH
    grand = sum(count.values())

    def pct(v):
        return "—" if v is None else f"{v * 100:+.2f}%"

    def tstr(v):
        return "—" if v is None else f"{v:.1f}"

    def line(cells):
        return ("| " + " | ".join(cells) + " |") if md else "  ".join(cells)

    hdr = ["Mẫu", "Hướng", "Số lần", "/tháng*", "+1p TB", "+5p TB", "+5p đúng", "+5p t", "+10p TB", "+10p đúng", "+10p t"]
    print(f"\n{n_ok} mã · {days} ngày (~{months:.0f} tháng, TB {total_bars / n_ok:.0f} phiên/mã) · "
          f"tổng {grand} lần xuất hiện ≈ {grand / months:.1f} thông báo/tháng cho cả danh mục "
          f"(~{grand / months / SESSIONS_PER_MONTH:.2f} mỗi phiên)\n")
    print(line(hdr))
    if md:
        print("|" + "---|" * len(hdr))
    for direction, label in (("buy", "MUA"), ("sell", "BÁN")):
        for pid, meta in PATTERNS.items():
            if meta["direction"] != direction:
                continue
            s1, s5, s10 = (_stats(per_pat[pid][h]) for h in HORIZONS)
            print(line([
                meta["name"], label, str(count[pid]), f"{count[pid] / months:.1f}",
                pct(s1["mean"]), pct(s5["mean"]),
                "—" if s5["win"] is None else f"{s5['win'] * 100:.0f}%", tstr(s5["t"]),
                pct(s10["mean"]),
                "—" if s10["win"] is None else f"{s10['win'] * 100:.0f}%", tstr(s10["t"]),
            ]))
    b1, b5, b10 = (_stats(base[h]) for h in HORIZONS)
    print(line(["**Mua đại rồi giữ**" if md else "MUA ĐẠI RỒI GIỮ", "—", str(b5["n"]), "—",
                pct(b1["mean"]), pct(b5["mean"]), f"{b5['win'] * 100:.0f}%", tstr(b5["t"]),
                pct(b10["mean"]), f"{b10['win'] * 100:.0f}%", tstr(b10["t"])]))
    print("\n* /tháng = số lần xuất hiện mỗi tháng trên CẢ danh mục. "
          "Với BÁN, lợi suất âm = tín hiệu đúng; 'đúng' của BÁN đọc ngược (100% − số in).")
    print("Mẫu MUA đáng giữ: +5p/+10p TB cao hơn mốc mua-đại và t > 2. "
          "Mẫu BÁN đáng giữ: +5p/+10p TB THẤP hơn mốc mua-đại và t < −2.")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Tua lịch sử 15 mẫu hình nến")
    p.add_argument("--symbols", default="", help="Danh sách mã, cách nhau bởi dấu phẩy (mặc định: WATCHLIST)")
    p.add_argument("--days", type=int, default=750)
    p.add_argument("--md", action="store_true", help="In bảng Markdown")
    a = p.parse_args()
    if a.symbols:
        symbols = [s.strip().upper() for s in a.symbols.split(",") if s.strip()]
    else:
        items, src = watchlist.load()
        symbols = [it["symbol"] for it in items]
        print(f"Danh mục {len(symbols)} mã (nguồn: {src})", file=sys.stderr)
    if not symbols:
        print("Không có mã nào để chạy.")
        return 2
    return run(symbols, a.days, a.md)


if __name__ == "__main__":
    sys.exit(main())
