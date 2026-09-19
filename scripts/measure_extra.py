"""Đo 17 ứng viên mẫu hình NGOÀI 15 mẫu cổ điển — bằng chứng cho việc chỉ thêm 3 mẫu khối lượng.

    venv\\Scripts\\python -m scripts.measure_extra                 # danh mục WATCHLIST, toàn bộ lịch sử DNSE (~4 năm)
    venv\\Scripts\\python -m scripts.measure_extra --days 750 --md

Kết quả ngày 18/09/2026 ở reports/replay-2026-09-18-khoi-luong.md. Ba mẫu được đưa vào app
(`limit_up_climax`, `limit_down_volume`, `falling_three_methods`) nằm trong job/patterns.py; 14 ứng viên còn
lại ở đây để ai muốn đo lại vẫn đo được — đừng thêm chúng vào app mà không có số liệu mới.

Cách đọc: MUA/BÁN tách riêng, với BÁN lợi suất âm = đúng; luôn so với mốc mua-đại trên cùng chuỗi;
cột "theo năm" quan trọng hơn cột tổng — mẫu chỉ thắng ở một năm là mẫu phụ thuộc thị trường.
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict

from common import dnse
from job import patterns as P, watchlist
from job.patterns import _bear, _big, _body, _bull, _lower, _rng, _upper, avg_body, avg_vol
from scripts.replay import _fwd, _stats

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

H = (1, 5, 10, 20)


def _pos(c):
    r = _rng(c)
    return (c["c"] - c["l"]) / r if r > 0 else 0.5


def _avg_rng(b, i, n=10):
    w = b[max(0, i - n): i]
    return sum(_rng(x) for x in w) / n if len(w) == n else 0.0


def _chg(b, i):
    return b[i]["c"] / b[i - 1]["c"] - 1 if i >= 1 and b[i - 1]["c"] > 0 else None


# --- đợt 1: mẫu hình thuần ---------------------------------------------------------------------
def three_outside_up(b, i, avg):
    return i >= 2 and P._bull_engulfing(b, i - 1, avg) and _bull(b[i]) and b[i]["c"] > b[i - 1]["c"]

def three_outside_down(b, i, avg):
    return i >= 2 and P._bear_engulfing(b, i - 1, avg) and _bear(b[i]) and b[i]["c"] < b[i - 1]["c"]

def rising_three(b, i, avg):
    if i < 4: return False
    a, mids, c = b[i - 4], b[i - 3:i], b[i]
    if not (_bull(a) and _big(a, avg)): return False
    tol = 0.1 * _rng(a)
    return all(_body(m) <= 0.5 * _body(a) and m["h"] <= a["h"] + tol and m["l"] >= a["l"] - tol for m in mids) \
        and _bull(c) and c["c"] > a["c"]

def _inside_break(b, i, up):
    if i < 12: return False
    m, ins, c = b[i - 2], b[i - 1], b[i]
    ar = _avg_rng(b, i - 2)
    if ar <= 0 or _rng(m) < 1.2 * ar or not (ins["h"] <= m["h"] and ins["l"] >= m["l"]): return False
    return (_bull(c) and c["c"] > m["h"]) if up else (_bear(c) and c["c"] < m["l"])

def inside_break_up(b, i, avg):   return _inside_break(b, i, True)
def inside_break_down(b, i, avg): return _inside_break(b, i, False)

def _tweezer(b, i, bottom):
    if i < 2: return False
    a, m, c = b[i - 2], b[i - 1], b[i]; tol = 0.003 * m["c"]
    if bottom: return _bear(a) and _bull(m) and abs(a["l"] - m["l"]) <= tol and _bull(c) and c["c"] > m["h"]
    return _bull(a) and _bear(m) and abs(a["h"] - m["h"]) <= tol and _bear(c) and c["c"] < m["l"]

def tweezer_bottom(b, i, avg): return _tweezer(b, i, True)
def tweezer_top(b, i, avg):    return _tweezer(b, i, False)

def _climax(b, i, avg, up, breakout):
    c = b[i]; r = _rng(c); av = avg_vol(b, i)
    if i < 20 or r <= 0 or av <= 0 or _body(c) < 2 * avg or c["v"] < 2 * av: return False
    if up and not (_bull(c) and _pos(c) >= 0.8): return False
    if not up and not (_bear(c) and _pos(c) <= 0.2): return False
    if not breakout: return True
    w = b[i - 20:i]
    return c["c"] > max(x["c"] for x in w) if up else c["c"] < min(x["c"] for x in w)

def climax_up(b, i, avg):       return _climax(b, i, avg, True, False)
def climax_up_brk(b, i, avg):   return _climax(b, i, avg, True, True)
def climax_down(b, i, avg):     return _climax(b, i, avg, False, False)
def climax_down_brk(b, i, avg): return _climax(b, i, avg, False, True)


# --- đợt 2: khối lượng -----------------------------------------------------------------------------
def _pocket(b, i, up):
    if i < 10 or _rng(b[i]) <= 0: return False
    c = b[i]; prev = b[i - 10:i]
    if up:
        downs = [x["v"] for x in prev if _bear(x)]
        return _bull(c) and bool(downs) and c["v"] > max(downs) and _pos(c) >= 0.5
    ups = [x["v"] for x in prev if _bull(x)]
    return _bear(c) and bool(ups) and c["v"] > max(ups) and _pos(c) <= 0.5

def pocket_up(b, i, avg):   return _pocket(b, i, True)
def pocket_down(b, i, avg): return _pocket(b, i, False)

def limit_up_vol15(b, i, avg):
    ch = _chg(b, i); av = avg_vol(b, i)
    return ch is not None and av > 0 and ch >= 0.065 and b[i]["v"] >= 1.5 * av

def _nr7(b, i, up):
    if i < 21: return False
    w = b[i - 7:i]
    if _rng(b[i - 1]) > min(_rng(x) for x in w): return False
    av = avg_vol(b, i); c = b[i]
    if av <= 0 or c["v"] < 1.5 * av: return False
    return (_bull(c) and c["c"] > max(x["h"] for x in w)) if up else (_bear(c) and c["c"] < min(x["l"] for x in w))

def nr7_up(b, i, avg):   return _nr7(b, i, True)
def nr7_down(b, i, avg): return _nr7(b, i, False)

def _reject(b, i, bottom):
    if i < 20: return False
    c = b[i]; r = _rng(c); av = avg_vol(b, i)
    if r <= 0 or av <= 0 or c["v"] < 1.5 * av: return False
    w = b[i - 10:i]
    if bottom: return _lower(c) >= 2 * _body(c) and _pos(c) >= 0.7 and c["l"] <= min(x["l"] for x in w)
    return _upper(c) >= 2 * _body(c) and _pos(c) <= 0.3 and c["h"] >= max(x["h"] for x in w)

def reject_bottom(b, i, avg): return _reject(b, i, True)
def reject_top(b, i, avg):    return _reject(b, i, False)


# --- đợt 3: khối lượng + vị trí ---------------------------------------------------------------------
def floor_confirm(b, i, avg):
    if i < 21: return False
    f, p, c = b[i - 1], b[i - 2], b[i]; av = avg_vol(b, i - 1)
    return p["c"] > 0 and av > 0 and f["c"] / p["c"] - 1 <= -0.065 and f["v"] >= 2 * av and _bull(c) and c["c"] > f["c"]

def gap_up_hold(b, i, avg):
    if i < 20: return False
    c, p = b[i], b[i - 1]; av = avg_vol(b, i)
    return av > 0 and c["o"] >= 1.02 * p["c"] and c["c"] >= c["o"] and _pos(c) >= 0.7 and c["v"] >= 1.5 * av

def gap_down_fail(b, i, avg):
    if i < 20: return False
    c, p = b[i], b[i - 1]; av = avg_vol(b, i)
    return av > 0 and c["o"] <= 0.98 * p["c"] and c["c"] <= c["o"] and _pos(c) <= 0.3 and c["v"] >= 1.5 * av

def dryup_bounce(b, i, avg):
    if i < 23: return False
    av = avg_vol(b, i); c = b[i]
    if av <= 0: return False
    for k in (1, 2, 3):
        x, y = b[i - k], b[i - k - 1]
        if not (x["c"] < y["c"] and x["v"] <= 0.7 * av): return False
    return _bull(c) and c["c"] > b[i - 1]["h"] and c["v"] >= 1.5 * av

def spring(b, i, avg):
    if i < 20: return False
    c = b[i]; lo = min(x["l"] for x in b[i - 20:i]); av = avg_vol(b, i)
    return av > 0 and c["l"] < lo and c["c"] > lo and _bull(c) and c["v"] >= 1.5 * av

def upthrust(b, i, avg):
    if i < 20: return False
    c = b[i]; hi = max(x["h"] for x in b[i - 20:i]); av = avg_vol(b, i)
    return av > 0 and c["h"] > hi and c["c"] < hi and _bear(c) and c["v"] >= 1.5 * av

def key_rev_up(b, i, avg):
    if i < 20: return False
    c, p = b[i], b[i - 1]; av = avg_vol(b, i)
    return av > 0 and c["o"] < p["l"] and c["c"] > p["c"] and c["v"] >= 1.5 * av

def key_rev_down(b, i, avg):
    if i < 20: return False
    c, p = b[i], b[i - 1]; av = avg_vol(b, i)
    return av > 0 and c["o"] > p["h"] and c["c"] < p["c"] and c["v"] >= 1.5 * av


CANDIDATES = [
    # (tên, hướng, hàm) — 3 mẫu ĐÃ ĐƯA VÀO APP ở đầu để so
    ("★ Trần + bùng nổ KL + phá đỉnh 20p (app)", "MUA", P._limit_up_climax),
    ("★ Sàn kèm KL ≥2× — bắt đáy (app)",         "MUA", P._limit_down_volume),
    ("★ Ba bước giảm (app)",                     "BÁN", P._falling_three_methods),
    ("Ba nến ngoài lên",              "MUA", three_outside_up),
    ("Ba nến ngoài xuống",            "BÁN", three_outside_down),
    ("Ba bước tăng",                  "MUA", rising_three),
    ("Nến trong + phá lên",           "MUA", inside_break_up),
    ("Nến trong + phá xuống",         "BÁN", inside_break_down),
    ("Nhíp đáy + xác nhận",           "MUA", tweezer_bottom),
    ("Nhíp đỉnh + xác nhận",          "BÁN", tweezer_top),
    ("Bùng nổ KL tăng (không cần trần)", "MUA", climax_up),
    ("Bùng nổ KL + phá đỉnh (không cần trần)", "MUA", climax_up_brk),
    ("Phân phối KL giảm",             "BÁN", climax_down),
    ("Phân phối KL + thủng đáy 20p",  "BÁN", climax_down_brk),
    ("Pocket pivot tăng",             "MUA", pocket_up),
    ("Pocket pivot giảm",             "BÁN", pocket_down),
    ("Nến trần kèm KL ≥1,5× (không cần phá đỉnh)", "MUA", limit_up_vol15),
    ("NR7 + phá lên kèm KL",          "MUA", nr7_up),
    ("NR7 + phá xuống kèm KL",        "BÁN", nr7_down),
    ("Rút chân KL tại đáy 10p",       "MUA", reject_bottom),
    ("Râu trên KL tại đỉnh 10p",      "BÁN", reject_top),
    ("Sàn + KL + nến xác nhận",       "MUA", floor_confirm),
    ("Gap tăng kèm KL giữ được",      "MUA", gap_up_hold),
    ("Gap giảm kèm KL",               "BÁN", gap_down_fail),
    ("Cạn cung rồi bật",              "MUA", dryup_bounce),
    ("Spring đáy 20p",                "MUA", spring),
    ("Upthrust đỉnh 20p",             "BÁN", upthrust),
    ("Key reversal lên kèm KL",       "MUA", key_rev_up),
    ("Key reversal xuống kèm KL",     "BÁN", key_rev_down),
]


def run(symbols: list[str], days: int, md: bool) -> int:
    R = defaultdict(lambda: defaultdict(list)); N = defaultdict(int)
    RY = defaultdict(lambda: defaultdict(list)); NY = defaultdict(lambda: defaultdict(int))
    B = defaultdict(list); BY = defaultdict(list); tot = 0; n_ok = 0; first = None
    with dnse.DnseClient(days=days) as c:
        for k, s in enumerate(symbols, 1):
            b = c.daily(s)
            if len(b) < 40:
                continue
            n_ok += 1; tot += len(b)
            first = b[0]["d"] if first is None or b[0]["d"] < first else first
            for i in range(len(b)):
                for h in H:
                    r = _fwd(b, i, h)
                    if r is not None:
                        B[h].append(r)
                        if h == 10:
                            BY[b[i]["d"].year].append(r)
            for i in range(P.MIN_BARS - 1, len(b)):
                avg = avg_body(b, i)
                if avg <= 0 or _rng(b[i]) <= 0:
                    continue
                y = b[i]["d"].year
                for name, d, fn in CANDIDATES:
                    if fn(b, i, avg):
                        N[name] += 1; NY[name][y] += 1
                        for h in H:
                            r = _fwd(b, i, h)
                            if r is not None:
                                R[name][h].append(r)
                                if h == 10:
                                    RY[name][y].append(r)
            if k % 10 == 0:
                print(f"  … {k}/{len(symbols)}", file=sys.stderr)
    if n_ok == 0:
        print("Không có dữ liệu."); return 1
    months = tot / n_ok / 21
    pct = lambda v: "—" if v is None else f"{v*100:+.2f}%"
    tstr = lambda v: "—" if v is None else f"{v:.1f}"
    win = lambda s: "—" if s["win"] is None else f"{s['win']*100:.0f}%"
    line = (lambda cells: "| " + " | ".join(cells) + " |") if md else (lambda cells: "  ".join(cells))
    print(f"\n{n_ok} mã · {tot // n_ok} phiên/mã (~{months:.0f} tháng, từ {first})\n")
    hdr = ["Mẫu", "Hướng", "Số lần", "/tháng", "+1p", "+5p", "+10p", "+10p đúng", "+10p t", "+20p", "+20p đúng"]
    print(line(hdr))
    if md: print("|" + "---|" * len(hdr))
    for name, d, _ in CANDIDATES:
        s1, s5, s10, s20 = (_stats(R[name][h]) for h in H)
        print(line([name, d, str(N[name]), f"{N[name]/months:.1f}", pct(s1["mean"]), pct(s5["mean"]),
                    pct(s10["mean"]), win(s10), tstr(s10["t"]), pct(s20["mean"]), win(s20)]))
    b1, b5, b10, b20 = (_stats(B[h]) for h in H)
    print(line(["**Mua đại rồi giữ**" if md else "MUA ĐẠI RỒI GIỮ", "—", str(b10["n"]), "—", pct(b1["mean"]),
                pct(b5["mean"]), pct(b10["mean"]), win(b10), tstr(b10["t"]), pct(b20["mean"]), win(b20)]))
    years = sorted(BY)
    print("\n+10 phiên theo năm (số lần · TB):\n")
    print(line(["Mẫu"] + [str(y) for y in years]))
    if md: print("|---|" + "---|" * len(years))
    for name, d, _ in CANDIDATES:
        print(line([name] + [f"{NY[name][y]} · {pct(_stats(RY[name][y])['mean'])}" for y in years]))
    print(line(["Mua đại"] + [f"— · {pct(_stats(BY[y])['mean'])}" for y in years]))
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Đo các ứng viên mẫu hình ngoài 15 mẫu cổ điển")
    p.add_argument("--symbols", default="")
    p.add_argument("--days", type=int, default=1500, help="DNSE chỉ trả tối đa ~4 năm")
    p.add_argument("--md", action="store_true")
    a = p.parse_args()
    if a.symbols:
        symbols = [s.strip().upper() for s in a.symbols.split(",") if s.strip()]
    else:
        items, src = watchlist.load()
        symbols = [it["symbol"] for it in items]
        print(f"Danh mục {len(symbols)} mã (nguồn: {src})", file=sys.stderr)
    return run(symbols, a.days, a.md)


if __name__ == "__main__":
    sys.exit(main())
