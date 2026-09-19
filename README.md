# Candle Watch — cảnh báo 18 mẫu hình nến + xu hướng Supertrend sau phiên

App cá nhân, độc lập: mỗi chiều sau ATC quét **danh mục do chính mình nhập trên điện thoại**, nhận dạng 18 mẫu
hình nến (15 mẫu đảo chiều cổ điển + 3 mẫu khối lượng) và 2 tín hiệu xu hướng Supertrend (10,3) × EMA10 **trên nến
đã chốt**, đẩy thông báo lên điện thoại và ghi lại để xem trên giao diện tĩnh. Không máy chủ, 0 đồng.

- Giao diện: GitHub Pages từ `/docs` của repo này (địa chỉ `https://<tài-khoản>.github.io/candle-watch/`).
- Job: GitHub Actions 15:35 T2–T6 (dự phòng 16:05 / 16:45 / 18:10 nếu nguồn chốt muộn).
- Nguồn giá: DNSE/Entrade (miễn phí, không token). **Danh mục: nhập ở tab Cài đặt → dán vào GitHub Variable
  `WATCHLIST`** — không đọc API của app nào khác.

## Danh mục theo dõi — cách nhập

Trang tĩnh không tự lưu được, nên đường đi là **sao chép → dán** (một lần mỗi khi đổi danh mục):

1. Mở app → **Cài đặt → 02 Danh mục theo dõi** → gõ mã, cách nhau bởi dấu phẩy / khoảng trắng / xuống dòng
   (không phân biệt hoa thường; mã sai dạng — không phải 3–6 ký tự chữ-số — bị bỏ và được liệt kê đỏ).
2. Bấm **Chuẩn hoá & sao chép** → clipboard nhận `HPG, SSI, VNM` (đã viết hoa, bỏ trùng, xếp A→Z).
3. GitHub → repo → **Settings → Secrets and variables → Actions → tab Variables** → `WATCHLIST`
   (lần đầu: *New repository variable*, tên đúng `WATCHLIST`) → dán → Save.
4. Đổi Variable **không** tự kích hoạt workflow: **Actions → daily → Run workflow** để quét ngay, hoặc chờ 15:35.
   Nếu hôm đó job đã chạy (đã có `docs/data/daily/<ngày>.json`) thì mã mới chỉ được quét từ phiên kế tiếp
   (chạy lại với `force=true` sẽ **gửi lại** thông báo của ngày đó — chỉ dùng khi thật cần).

Job (`job/watchlist.py`): env `WATCHLIST` → `parse()` → ghi bản chụp `docs/data/watchlist.json` (giao diện đọc
để điền sẵn ô nhập, nguồn `variable`); env trống → bản chụp (`cache`); không có gì → **không quét, không lỗi**:
ghi `latest.json` tối thiểu để giao diện hiện hướng dẫn, Actions vẫn xanh. `parse()` là đặc tả chuẩn hoá —
`normalizeWatchlist()` trong `docs/app.js` phải cho cùng kết quả. Local: dòng `WATCHLIST=` trong `.env`.
Bản nháp đang gõ dở giữ trong `localStorage` của điện thoại; nút "Lấy lại danh mục job đang dùng" hiện khi
nháp khác với bản job đã đọc.

## Đọc trước khi tin vào cảnh báo — kết quả đo lại

Số đo dưới đây lấy từ một **danh mục tham chiếu 39 mã** (bản gốc app này đo trước khi tách ra); danh mục của
anh khác thì tần suất và lợi suất khác — muốn đo lại trên danh mục mình:

```
venv\Scripts\python -m scripts.replay --days 750 --md > reports/replay-<ngày>.md
venv\Scripts\python -m scripts.replay_trend
```

(`scripts/replay*.py` và `scripts/measure_extra.py` đọc `watchlist.load()` — tức `WATCHLIST` trong `.env` —
hoặc `--symbols HPG,VNM`.)

`scripts/replay.py` trên 39 mã × 750 ngày (~509 phiên/mã), bảng đầy đủ ở
[reports/replay-2026-09-16.md](reports/replay-2026-09-16.md):

- **Số lượng:** 4.382 lần xuất hiện ≈ **8,6 mẫu/phiên** cho cả danh mục. Vì thế job **gộp theo mã** (một
  thông báo/mã) và khi **quá 6 mã** cùng có mẫu thì gửi **một** thông báo tổng hợp (`digest_threshold`).
- **Mẫu MUA có giá trị thật** (so với mốc "mua đại rồi giữ" +0,18% / +0,41% sau 5 / 10 phiên):
  - Nhấn chìm tăng: +0,98% sau 10 phiên, t = 3,4 — nhưng 31,7 lần/tháng.
  - Sao mai Doji: +1,17% sau 5 phiên, t = 2,6 — 7,9 lần/tháng.
  - Sao mai yếu (t 1,7); Xuyên thấu, Búa, Búa ngược ≈ 0 hoặc âm.
- **Mẫu BÁN: không mẫu nào dự báo được giảm** trên dữ liệu 2024–2026 (thị trường đi lên). Ba con quạ
  đen còn +2% sau tín hiệu. Chỉ Mây đen che phủ có −0,89% sau 10 phiên (t −2,5).
- Siết "thân nến xác nhận ≥ 1,2× trung bình" giảm 25 % số lần, Nhấn chìm tăng vẫn giữ giá trị; các mẫu
  khác không khá lên.

Mặc định **bật cả 18**. Muốn bớt ồn: thêm id mẫu vào `patterns_disabled` trong `docs/data/settings.json` rồi
push (job chạy ngay khi push).

Cách đọc số: MUA và BÁN tách riêng (VN không bán khống); với BÁN, lợi suất âm sau tín hiệu = đúng;
luôn so với mốc mua-đại trên cùng chuỗi; t > 2 mới đáng để ý; chưa trừ phí, chưa tính T+2.

## Xu hướng: Supertrend (10,3) × EMA10 (job/trend.py)

Python thuần, đối chiếu với bản JS trong `docs/app.js` (cùng 26/26 tín hiệu trên 30 phiên × 39 mã). Tái lập số
đo: `scripts/replay_trend.py` → [reports/replay-trend-2026-09-18.md](reports/replay-trend-2026-09-18.md).

- **Toán:** ATR(10) kiểu Wilder/RMA (giống TradingView — bản SMA lệch ngày lật màu 1–2 phiên); dải
  `hl2 ± 3·ATR`, dải "final" chỉ siết vào, không nới ra trừ khi giá đã vượt; EMA10 mồi bằng SMA.
- **Hai tín hiệu, chỉ chiều mua:** `st_buy` = Supertrend xanh và đóng cửa > EMA10 **lần đầu kể từ đợt đỏ
  gần nhất**; `st_exit` = Supertrend lật đỏ. Thoát **chỉ** khi lật đỏ — quy tắc gốc "thoát khi rớt EMA10"
  đo được là hại (+1,24 %/lệnh, thắng 37 %, giữ 6 phiên) so với +6,71 %/lệnh khi chỉ thoát bằng Supertrend.
- **Số đo 11/2019 → 09/2026, 39 mã, khớp mở phiên sau, T+2, phí 0,4 %/vòng:** 819 lệnh (≈ 10/tháng cả
  danh mục ≈ 0,5/phiên), thắng 47 %, **+6,71 %/lệnh** (mốc mua đại rồi giữ 34 phiên +3,93 %), t = 5,9,
  PF 2,65. Cả kỳ **+212 % so với mua-và-giữ +294 %**, nhưng sụt giảm sâu nhất **−42 % so với −63 %**, trong thị
  trường 54 % thời gian; 2022 mất −11 % thay vì −40 %; 2024 (đi ngang) gần hoà. Tức là công cụ **bảo toàn vốn
  năm xấu**, không phải công cụ tối đa hoá lãi năm tốt. Tỷ lệ thắng thấp là bản chất: lệnh thắng TB +23 %,
  thua TB −7,7 %.
- **Lưới lân cận** ATR {7,10,14} × hệ số {2,3,4} × EMA {10,20}: 18/18 ô dương, t > 4,8 → không khớp quá mức;
  EMA20 nhỉnh hơn EMA10 ở mọi ô, hệ số 4 tệ nhất.
- **Push:** mỗi tín hiệu xu hướng là **một thông báo riêng** (`cw-st-<mã>`), không bao giờ vào bản tổng hợp —
  hiếm và mang mức dừng lỗ (dải Supertrend) để đặt lệnh sáng hôm sau. Mẫu nến giữ quy tắc gộp.
- **Giao diện:** thẻ xu hướng đứng đầu tab Hôm nay (nến 22 phiên có đường Supertrend/EMA, ô dừng lỗ, rủi ro,
  EMA10); bảng "N xanh · M đỏ"; thẻ mẫu nến thêm dòng XU HƯỚNG (mẫu MUA khi Supertrend đỏ được ghi
  "ngược xu hướng") và ô biểu đồ 46 phiên nền xanh/đỏ có mũi tên ▲▼; tab **Biểu đồ** vẽ 130 phiên từ
  `docs/data/bars.json` (job ghi mỗi ngày), Supertrend/EMA tính lại trong trình duyệt cùng công thức.
- Tắt: thêm `st_buy` / `st_exit` vào `patterns_disabled`.

## 18 mẫu hình (job/patterns.py)

Ký hiệu nến: `body=|c−o|`, `rng=h−l`, `up=h−max(o,c)`, `lo=min(o,c)−l`. `avg_body` = trung bình thân 10 nến
trước mẫu. Thân lớn = `body ≥ 0,8·avg_body`; thân nhỏ = `body ≤ 0,3·rng`; Doji = `body ≤ 0,1·rng`;
Búa = thân nhỏ, `lo ≥ 2·body`, `up ≤ 0,1·rng`; Búa ngược = đối xứng. Nến cuối luôn là nến xác nhận đã chốt.

| id | Tên | Hướng | Điều kiện (nến −3, −2, −1) |
|---|---|---|---|
| `bull_engulfing` | Nhấn chìm tăng | MUA | −2 giảm; −1 tăng thân lớn, `o₋₁ ≤ c₋₂`, `c₋₁ ≥ o₋₂` |
| `bear_engulfing` | Nhấn chìm giảm | BÁN | −2 tăng; −1 giảm thân lớn, `o₋₁ ≥ c₋₂`, `c₋₁ ≤ o₋₂` |
| `morning_star` | Sao mai | MUA | −3 giảm thân lớn; −2 `body ≤ 0,3·body₋₃`; −1 tăng, `c₋₁ > (o₋₃+c₋₃)/2` |
| `evening_star` | Sao hôm | BÁN | đối xứng Sao mai |
| `morning_doji_star` | Sao mai Doji | MUA | như Sao mai, −2 là Doji |
| `evening_doji_star` | Sao hôm Doji | BÁN | như Sao hôm, −2 là Doji |
| `three_white_soldiers` | Ba chàng lính trắng | MUA | 3 nến tăng `body/rng > 0,6`, đóng cửa tăng dần, mở cửa trong thân nến trước |
| `three_black_crows` | Ba con quạ đen | BÁN | đối xứng |
| `hammer_confirm` | Búa + xác nhận | MUA | −2 Búa; −1 tăng, `c₋₁ > h₋₂` |
| `hanging_man_confirm` | Người treo cổ + xác nhận | BÁN | −2 Búa (cùng hình); −1 giảm, `c₋₁ < l₋₂` |
| `inv_hammer_confirm` | Búa ngược + xác nhận | MUA | −2 Búa ngược; −1 tăng, `c₋₁ > h₋₂` |
| `shooting_star_confirm` | Sao băng + xác nhận | BÁN | −2 Búa ngược; −1 giảm, `c₋₁ < l₋₂` |
| `piercing` | Xuyên thấu | MUA | −2 giảm thân lớn; −1 tăng, `o₋₁ ≤ c₋₂`, `(o₋₂+c₋₂)/2 < c₋₁ < o₋₂` |
| `dark_cloud` | Mây đen che phủ | BÁN | đối xứng Xuyên thấu |
| `three_inside_down` | Ba nến trong giảm | BÁN | −3 tăng thân lớn; −2 giảm thân trong thân −3; −1 giảm, `c₋₁ < l₋₂` |
| `limit_up_climax` | Trần + bùng nổ KL + phá đỉnh | MUA | `c/c₋₁ − 1 ≥ 6,5 %`; tăng; `body ≥ 2·avg_body`; đóng ở 20 % trên biên độ; `v ≥ 2·avg_vol₂₀`; `c > max c 20 phiên` |
| `limit_down_volume` | Sàn kèm KL bùng nổ (bắt đáy) | MUA | `c/c₋₁ − 1 ≤ −6,5 %`; `v ≥ 2·avg_vol₂₀` |
| `falling_three_methods` | Ba bước giảm | BÁN | −5 giảm thân lớn; −4..−2 `body ≤ ½·body₋₅`, nằm trong biên −5 (±10 %); −1 giảm, `c₋₁ < c₋₅` |

**Ba mẫu khối lượng (16–18)** được chọn sau khi đo 17 ứng viên trên toàn bộ lịch sử DNSE (08/2022 → 09/2026,
[reports/replay-2026-09-18-khoi-luong.md](reports/replay-2026-09-18-khoi-luong.md)). Chúng khác 15 mẫu cổ điển ở hai
chiều mà nến Nhật không có: **khối lượng** và **biên độ ±7 % của sàn VN** — và đó là hai chiều duy nhất đo ra giá trị ổn định:

- **Trần + bùng nổ KL + phá đỉnh**: 188 lần (3,9/tháng), +2,76 % sau 10 phiên (t 3,2), **thắng mua-đại 5/5 năm** kể cả cú
  sập 2022. Tách riêng từng điều kiện đều ≈ mua đại; giá trị nằm ở chỗ cả ba cùng xảy ra. Ngưỡng 6,5 % dùng chung cho
  HOSE/HNX/UPCOM (sàn khác biên rộng hơn nên vẫn qua) — cố ý.
- **Sàn kèm KL ≥ 2×**: 184 lần, +2,12 %/10p, +5,13 %/20p (60 % đúng) — nhưng 2022 (cú sập) và 2024 (đi ngang) âm ở 10p.
  Bán tháo kiệt sức chỉ trả tiền khi trùng đáy thật; thẻ cảnh báo ghi rõ "rủi ro cao".
- **Ba bước giảm**: 750 ngày ra −5,48 % (22 lần) nhưng 4 năm chỉ −0,78 % (56 lần), 2023–2024 sai chiều. Đưa vào để
  theo dõi, **khuyên tắt** — tắt bằng `patterns_disabled` trong `docs/data/settings.json`.

14 ứng viên còn lại (Ba nến ngoài, Nến trong, Nhíp, Pocket pivot, NR7, Spring, Upthrust, Key reversal, Gap…) đo ra ≈ mua
đại hoặc sai chiều — script `scripts/measure_extra.py` giữ lại để đo lại được.

Ba chỗ cố ý (áp cho 15 mẫu cổ điển):

1. **Không lọc xu hướng (MA), không lọc %K** — "mẫu xuất hiện là báo". Supertrend là tín hiệu riêng, có số đo riêng,
   không phải bộ lọc chồng lên mẫu nến.
2. **Không đòi gap** ở Sao mai/Sao hôm: nến ngày VN hầu như không gap, điều kiện đó gần như không bao giờ
   thoả. Thay bằng điều kiện thân nến giữa.
3. **Mẫu 1 nến bắt buộc kèm nến xác nhận.** Theo Bulkowski, Búa/Búa ngược/Sao băng/Người treo cổ đứng
   một mình thiên về tiếp diễn hơn đảo chiều. Búa và Người treo cổ cùng hình → phân biệt bằng màu nến
   xác nhận. Một bộ nến có thể khớp nhiều mẫu — ghi cả, gộp theo mã.

Nến nào biên độ 0 (đứng giá, trần/sàn không khớp) → không nhận mẫu, không ném lỗi.

## Job sau phiên (job/run_daily.py)

1. `watchlist.load()`: env `WATCHLIST` → bản chụp `docs/data/watchlist.json`. Rỗng → ghi `latest.json` tối thiểu,
   thoát 0, không quét.
2. `fetch_bars()`: nến ngày 200 ngày lịch (~135 phiên, đủ warm-up 40 phiên cho Supertrend/EMA) + nến 1'
   hôm nay; ≥ 20 % mã thanh khoản (≥ 30 nến 1') thiếu nến ATC 14:45 → **nguồn chưa chốt**, ghi
   `state.unsettled`, không ghi file, cron sau thử lại.
3. `trade_date` = ngày nến cuối lớn nhất. Đã có `docs/data/daily/<ngày>.json` → thoát (idempotent).
4. Mã có nến cuối **cũ hơn** `trade_date` (không khớp lệnh hôm nay) → vào `stale`, **không xét mẫu**.
   Không có bước này, một mẫu cũ của mã kém thanh khoản sẽ được "phát hiện lại" mỗi ngày.
5. `patterns.detect_at(bars, -1)` + `trend.detect_at(bars, -1)` cho từng mã → tín hiệu `kind: candle`
   (kèm 7 nến + 46 nến xu hướng) / `kind: trend` (kèm 22 nến có dải Supertrend + EMA, `st_line`, `risk_pct`,
   `days_in_trend`). `trend_board()` → trạng thái Supertrend của mọi mã (`latest.trend`).
6. Push: xu hướng → **mỗi tín hiệu một thông báo riêng** (`cw-st-<mã>`); mẫu nến → một thông báo/mã
   (`cw-<mã>`, gộp tên mẫu), > `digest_threshold` mã → một thông báo tổng hợp. Thứ Hai gửi thêm nhịp tim.
   Máy mới đăng ký → chào mừng ngay ở đầu job.
7. Ghi `latest.json` (giao diện đọc; có `watchlist.symbols`), `bars.json` (130 nến/mã cho tab Biểu đồ),
   `daily/<ngày>.json`, `state.json`.

Chạy tay: `run-daily-local.bat` (= `--force --no-push`), `--dry-run` chỉ in.

## Giao diện (docs/)

Bốn tab: **Hôm nay** (thẻ xu hướng Supertrend đứng đầu, bảng mã xanh/đỏ, rồi thẻ mẫu nến theo mã; chưa có
danh mục → hộp hướng dẫn sang Cài đặt), **Lịch sử** (30 phiên, đếm xu hướng / mẫu nến riêng), **Biểu đồ**
(130 phiên có Supertrend, EMA10, vùng xanh/đỏ, mũi tên mua/thoát, chạm xem giá), **Cài đặt** (01 đăng ký thông
báo, **02 danh mục theo dõi**, 03 xu hướng, 04/05 mẫu MUA/BÁN với glyph, số lần/tháng và trạng thái bật/tắt).

Không có Worker thì công tắc mẫu chỉ hiển thị; đổi trong `docs/data/settings.json` rồi push.
Đăng ký thông báo: bấm "Bật thông báo" → sao chép đoạn mã → dán vào GitHub Secret `PUSH_SUBS_FALLBACK`
(một lần mỗi máy; nhiều máy thì nối vào cùng một mảng JSON).

Tông màu/chữ: nền kem `#F7F4EC`, xanh rêu `#1F3A2E`, thẻ pastel, Archivo + Source Serif 4 italic.
Logo "Sao mai": `docs/icons/logo.svg`; PNG sinh bằng `scripts/make_icons.py` (cần Pillow).

## Deploy lần đầu (tài khoản GitHub mới)

1. Tạo repo **public** `candle-watch` (viết thường — đường dẫn GitHub Pages phân biệt hoa/thường), push toàn bộ
   (trừ `venv/`, `.env` — đã có trong `.gitignore`).
2. Settings → Pages → Source `Deploy from a branch`, branch `main`, folder **`/docs`** (không phải root).
3. `venv\Scripts\python -m job.gen_vapid` → 3 dòng. Dán `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`,
   `VAPID_SUBJECT` vào Settings → Secrets and variables → Actions → **Secrets**; public key cũng phải nằm trong
   `docs/config.js` (`VAPID_PUBLIC`) — push.
4. Tab **Variables** → `WATCHLIST` = danh sách mã (lấy từ nút "Chuẩn hoá & sao chép" trong app, hoặc gõ tay
   `HPG, VNM`).
5. Mở app trên điện thoại → Cài đặt → Bật thông báo → Sao chép → dán vào Secret `PUSH_SUBS_FALLBACK`
   (giữ nguyên cả `[` `]` — đó là **danh sách** máy).
6. Actions → daily → Run workflow. Nghiệm thu: `docs/data/state.json` có `devices.n = 1`, điện thoại nhận thông
   báo chào mừng; `latest.json.watchlist.n` đúng số mã; 15:35 hôm sau `latest.json.trade_date` đúng ngày.
   Thử push không cần GitHub: `PUSH_SUBS_FALLBACK='[…]' venv\Scripts\python -m job.push --test`.

## Bẫy đã gặp, đừng dẫm lại

- **DNSE trả nến hôm nay dừng giữa phiên, HTTP 200**: job phải soi nến 1' có chạm ATC chưa.
- **Mã ít thanh khoản mang nến cũ nhiều ngày** → không xét mẫu, chỉ ghi `stale`.
- **DNSE trả giá đã điều chỉnh cổ tức** — cố ý giữ, mẫu hình dùng tỷ lệ nên không ảnh hưởng.
- **Giá theo nghìn đồng** (`PRICE_UNIT = 1.0`).
- Console Windows cp1252 → script phải `reconfigure(encoding="utf-8")` trước khi in chữ có dấu.
- Chrome headless không cho cửa sổ hẹp dưới ~500px → muốn chụp 390px phải bọc trong iframe.
- **GitHub cron trễ 10–30 phút** là bình thường; đừng dựa vào đúng phút.
- Thiếu `VAPID_PUBLIC_KEY` thì thông báo im lặng không tới — `push.configured()` đòi cả hai khoá.
- Đổi **Variable** trên GitHub không kích hoạt workflow (push code/settings thì có).
- PWA đã cài giữ JS cũ → khi đổi `docs/app.js`/`styles.css` phải tăng `?v=` trong `index.html` và đóng hẳn app.

## Kiểm thử

```
venv\Scripts\python -m pytest tests -q      # 84 test: 18 mẫu dương/âm, Supertrend/EMA tay tính, job idempotent, push gộp/riêng, danh mục
node --check docs/app.js
```

## Không làm (đã cân nhắc)

- Không quét trong phiên (nến chưa chốt sẽ "vẽ lại"). Không lọc ADX/MA/%K cho mẫu nến.
- Không thoát xu hướng khi rớt EMA10 (đo được là hại). Không đo Supertrend tuần.
- Không máy chủ/Worker: trang không tự ghi được danh mục nên dùng sao chép → dán Variable; muốn bấm-là-lưu
  cần Worker hoặc token GitHub trong trang (chưa cần).
