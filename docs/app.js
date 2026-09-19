/* Candle Watch — giao diện điện thoại. JS thuần, đọc data/latest.json do job sau phiên ghi.
   Không nhận dạng gì ở đây: thứ hiện trên màn hình đúng bằng thứ đã rung chuông. */
(function () {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const CFG = window.CW_CONFIG || {};
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const dmy = (iso) => iso ? iso.slice(0, 10).split("-").reverse().slice(0, 2).join("/") : "—";
  const dow = (iso) => ["Chủ nhật", "Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy"][new Date(iso + "T00:00:00").getDay()];
  const px = (v) => v == null ? "—" : Number(v).toFixed(2);
  const pad2 = (n) => String(n).padStart(2, "0");

  // Kết quả đo lại 39 mã × 750 ngày (reports/replay-2026-09-16.md): số lần/tháng và một dòng nhận xét.
  const REPLAY = {
    bull_engulfing:        { pm: 31.7, note: "Đo 2 năm: +0,98% sau 10 phiên, hơn mua-và-giữ (t 3,4) — có giá trị nhưng ồn." },
    morning_star:          { pm: 18.3, note: "Đo 2 năm: +0,45% sau 5 phiên (t 1,7) — yếu." },
    morning_doji_star:     { pm: 7.9,  note: "Đo 2 năm: +1,17% sau 5 phiên (t 2,6) — mẫu MUA tốt nhất." },
    three_white_soldiers:  { pm: 0.1,  note: "Gần như không xuất hiện trên nến ngày VN (3 lần/2 năm)." },
    hammer_confirm:        { pm: 7.6,  note: "Đo 2 năm: âm sau 5 và 10 phiên — không có giá trị dự báo." },
    inv_hammer_confirm:    { pm: 4.7,  note: "Đo 2 năm: ≈ 0 — không có giá trị dự báo." },
    piercing:              { pm: 11.9, note: "Đo 2 năm: ≈ 0 — không có giá trị dự báo." },
    bear_engulfing:        { pm: 41.9, note: "Đo 2 năm: giá vẫn tăng sau tín hiệu — không dự báo được giảm." },
    evening_star:          { pm: 9.9,  note: "Đo 2 năm: −0,33% sau 5 phiên (t −0,9) — yếu." },
    evening_doji_star:     { pm: 4.1,  note: "Đo 2 năm: không dự báo được giảm." },
    three_black_crows:     { pm: 1.4,  note: "Đo 2 năm: sau tín hiệu giá TĂNG +2% — ngược kỳ vọng." },
    hanging_man_confirm:   { pm: 2.6,  note: "Đo 2 năm: −0,75% sau 5 phiên rồi bật lại — yếu." },
    shooting_star_confirm: { pm: 13.0, note: "Đo 2 năm: không dự báo được giảm." },
    dark_cloud:            { pm: 16.0, note: "Đo 2 năm: −0,89% sau 10 phiên (t −2,5) — mẫu BÁN duy nhất có chút giá trị." },
    three_inside_down:     { pm: 9.7,  note: "Đo 2 năm: không dự báo được giảm." },
    // 3 mẫu khối lượng (reports/replay-2026-09-18-khoi-luong.md, 08/2022 → 09/2026)
    limit_up_climax:       { pm: 3.8,  note: "Đo 4 năm: +2,76% sau 10 phiên (t 3,2), thắng mua-và-giữ cả 5/5 năm kể cả cú sập 2022 — tín hiệu MUA vững nhất." },
    limit_down_volume:     { pm: 3.8,  note: "Đo 4 năm: +2,12% sau 10 phiên, +5,13% sau 20 phiên (60% đúng) — nhưng phụ thuộc thị trường, xem cảnh báo." },
    falling_three_methods: { pm: 1.1,  note: "Đo 4 năm: 56 lần, −0,78% sau 10 phiên (t −0,8) — 2 năm đúng chỉ 2026 (−9,8%), 2023–2024 sai chiều. Chưa ổn định." },
    // 2 tín hiệu xu hướng (reports/replay-trend-2026-09-18.md, 11/2019 → 09/2026, 39 mã, khớp mở phiên sau, T+2, có phí)
    st_buy:                { pm: 10.4, note: "Đo 7 năm: +6,71%/lệnh, thắng 47%, PF 2,65 — hơn mua đại rồi giữ 34 phiên (+3,93%). Lãi đến từ ít lệnh thắng to; 5/10 lệnh thua nhỏ." },
    st_exit:               { pm: 10.2, note: "Điểm thoát duy nhất của hệ thống. Thoát sớm hơn khi rớt EMA10 đo được là hại (+1,24%/lệnh so với +6,71%)." },
  };

  // Nến mẫu để vẽ glyph ở tab Cài đặt (o,h,l,c) — chỉ để nhận diện hình, không phải dữ liệu.
  const SAMPLES = {
    bull_engulfing: [[10, 10.3, 8.6, 9], [8.9, 11.4, 8.7, 11.2]],
    bear_engulfing: [[9, 10.3, 8.8, 10], [10.1, 10.3, 7.8, 8]],
    morning_star: [[11, 11.2, 8.9, 9.2], [9.1, 9.5, 8.5, 8.9], [9.3, 11.1, 9.2, 10.9]],
    evening_star: [[9, 11.2, 8.9, 10.9], [11, 11.5, 10.6, 11.2], [10.8, 10.9, 8.8, 9.1]],
    morning_doji_star: [[11, 11.2, 8.9, 9.2], [9.0, 9.5, 8.5, 9.02], [9.3, 11.1, 9.2, 10.9]],
    evening_doji_star: [[9, 11.2, 8.9, 10.9], [11.1, 11.5, 10.6, 11.08], [10.8, 10.9, 8.8, 9.1]],
    three_white_soldiers: [[8, 9.2, 7.9, 9], [8.6, 10.1, 8.5, 9.9], [9.4, 11, 9.3, 10.8]],
    three_black_crows: [[11, 11.1, 9.8, 10], [10.5, 10.6, 9.2, 9.4], [9.8, 9.9, 8.4, 8.6]],
    hammer_confirm: [[9.4, 9.65, 8.3, 9.6], [9.6, 10.6, 9.5, 10.5]],
    hanging_man_confirm: [[10.4, 10.65, 9.3, 10.6], [10.5, 10.6, 8.9, 9.1]],
    inv_hammer_confirm: [[9.4, 10.6, 9.35, 9.6], [9.7, 10.9, 9.6, 10.8]],
    shooting_star_confirm: [[10.4, 11.6, 10.35, 10.6], [10.5, 10.55, 9.4, 9.6]],
    piercing: [[11, 11.2, 9.3, 9.5], [9.4, 10.7, 9.2, 10.5]],
    dark_cloud: [[9.5, 11.2, 9.3, 11], [11.1, 11.3, 9.5, 10]],
    three_inside_down: [[9, 10.7, 8.9, 10.5], [10.2, 10.3, 9.5, 9.6], [9.6, 9.7, 8.6, 8.8]],
    limit_up_climax: [[9.6, 9.9, 9.4, 9.7], [9.7, 10.4, 9.6, 10.4]],
    limit_down_volume: [[10.4, 10.6, 10.1, 10.3], [10.3, 10.35, 9.55, 9.6]],
    falling_three_methods: [[10.8, 10.9, 9.4, 9.5], [9.6, 10.1, 9.5, 10.0], [10.0, 10.4, 9.9, 10.3], [10.3, 10.5, 10.1, 10.4], [10.3, 10.35, 8.9, 9.0]],
  };

  let D = null;

  // ---------------------------------------------------------------- mini-chart
  /* Vẽ n nến; `patBars` nến cuối tô màu (thuộc mẫu), nến cuối cùng khung vàng (nến xác nhận).
     W×H là kích thước SVG. Nến ngoài mẫu vẽ rỗng viền xám để mắt bám vào mẫu. */
  function miniChart(candles, patBars, W, H, thin) {
    const n = candles.length;
    if (!n) return "";
    const hi = Math.max(...candles.map((c) => c.h)), lo = Math.min(...candles.map((c) => c.l));
    const span = (hi - lo) || 1;
    const top = 6, bottom = H - 8;
    const y = (v) => bottom - (v - lo) / span * (bottom - top);
    const slot = W / n, bw = Math.max(6, Math.min(12, slot * 0.5));
    let out = `<line x1="0" y1="${H - 4}" x2="${W}" y2="${H - 4}" stroke="#D9D3C3" stroke-width="1"></line>`;
    candles.forEach((c, i) => {
      const cx = slot * i + slot / 2, inPat = i >= n - patBars, last = i === n - 1;
      const bull = c.c >= c.o, col = bull ? "#2E7D4F" : "#B84A3A";
      const yo = y(c.o), yc = y(c.c), bt = Math.min(yo, yc), bh = Math.max(1.5, Math.abs(yo - yc));
      const sw = thin ? 1.5 : 2;
      if (inPat) {
        out += `<line x1="${cx}" y1="${y(c.h)}" x2="${cx}" y2="${y(c.l)}" stroke="${col}" stroke-width="${sw}"></line>`;
        out += `<rect x="${cx - bw / 2}" y="${bt}" width="${bw}" height="${bh}" fill="${col}"></rect>`;
      } else {
        out += `<line x1="${cx}" y1="${y(c.h)}" x2="${cx}" y2="${y(c.l)}" stroke="#4B5A52" stroke-width="1.5"></line>`;
        out += `<rect x="${cx - bw / 2 + 1}" y="${bt}" width="${bw - 2}" height="${bh}" fill="#F7F4EC" stroke="#4B5A52" stroke-width="1.5"></rect>`;
      }
      if (last && !thin) out += `<rect x="${cx - bw / 2 - 3}" y="${y(c.h) - 3}" width="${bw + 6}" height="${y(c.l) - y(c.h) + 6}" rx="3" fill="none" stroke="#C99A2E" stroke-width="2"></rect>`;
    });
    return out;
  }
  const glyph = (pid, bars) => {
    if (TREND_GLYPH[pid]) return `<svg viewBox="0 0 56 36" aria-hidden="true">${trendChart(TREND_GLYPH[pid], 56, 36, true)}</svg>`;
    const cs = (SAMPLES[pid] || []).map((a) => ({ o: a[0], h: a[1], l: a[2], c: a[3] }));
    return `<svg viewBox="0 0 56 36" aria-hidden="true">${miniChart(cs, bars || cs.length, 56, 36, true)}</svg>`;
  };

  // ---------------------------------------------------------------- xu hướng: mini-chart có đường
  /* Nến kèm dải Supertrend (xanh/đỏ, ngắt đoạn khi đổi màu) và EMA10; nến cuối khung vàng.
     `cs` là candles của tín hiệu xu hướng: {o,h,l,c,st,up,ema}.
     `bands` = tô nền từng nến theo màu Supertrend (cùng màu tab Biểu đồ) — dùng cho ô rộng trong thẻ. */
  function trendChart(cs, W, H, thin, bands) {
    const n = cs.length; if (!n) return "";
    const vals = cs.flatMap((c) => [c.h, c.l, c.st, c.ema]).filter((v) => v != null);
    const hi = Math.max(...vals), lo = Math.min(...vals), span = (hi - lo) || 1;
    const pad = !thin && cs.some((c) => c.sig) ? 8 : 0;   // chừa chỗ cho mũi tên trên/dưới nến
    const top = 5 + pad, bottom = H - 7 - pad, y = (v) => bottom - (v - lo) / span * (bottom - top);
    const slot = W / n, bw = Math.max(2, Math.min(8, slot * 0.55));
    let out = "";
    if (bands) cs.forEach((c, i) => { if (c.up != null) out += `<rect x="${(slot * i).toFixed(1)}" y="0" width="${(slot + 0.5).toFixed(1)}" height="${H - 3}" fill="${c.up ? "#E3EEDF" : "#F4E6E0"}"></rect>`; });
    out += `<line x1="0" y1="${H - 3}" x2="${W}" y2="${H - 3}" stroke="#D9D3C3" stroke-width="1"></line>`;
    cs.forEach((c, i) => {
      const cx = slot * i + slot / 2, col = c.c >= c.o ? "#2E7D4F" : "#B84A3A";
      const yo = y(c.o), yc = y(c.c), bt = Math.min(yo, yc), bh = Math.max(1.2, Math.abs(yo - yc));
      out += `<line x1="${cx}" y1="${y(c.h)}" x2="${cx}" y2="${y(c.l)}" stroke="${col}" stroke-width="${thin ? 1 : 1.3}" opacity=".85"></line>`;
      out += `<rect x="${cx - bw / 2}" y="${bt}" width="${bw}" height="${bh}" fill="${col}" opacity=".85"></rect>`;
      if (i === n - 1 && !thin) out += `<rect x="${cx - bw / 2 - 3}" y="${y(c.h) - 3}" width="${bw + 6}" height="${y(c.l) - y(c.h) + 6}" rx="3" fill="none" stroke="#C99A2E" stroke-width="2"></rect>`;
    });
    const ema = cs.map((c, i) => c.ema == null ? null : `${(slot * i + slot / 2).toFixed(1)},${y(c.ema).toFixed(1)}`).filter(Boolean).join(" ");
    if (ema) out += `<polyline points="${ema}" fill="none" stroke="#5B6FA8" stroke-width="${thin ? 1.2 : 1.6}" stroke-linejoin="round"></polyline>`;
    let seg = [], segUp = null;
    const flush = () => { if (seg.length) out += `<polyline points="${seg.join(" ")}" fill="none" stroke="${segUp ? "#2E7D4F" : "#B84A3A"}" stroke-width="${thin ? 1.6 : 2.2}" stroke-linejoin="round"></polyline>`; seg = []; };
    cs.forEach((c, i) => { if (c.st == null) return; if (segUp !== null && c.up !== segUp) flush(); segUp = c.up; seg.push(`${(slot * i + slot / 2).toFixed(1)},${y(c.st).toFixed(1)}`); });
    flush();
    // Mũi tên tín hiệu (job tính sẵn `sig`): ▲ MUA dưới nến, ▼ lật đỏ trên nến — cùng màu tab Biểu đồ
    if (!thin) cs.forEach((c, i) => {
      if (!c.sig) return;
      const cx = slot * i + slot / 2, hw = Math.min(5, slot * 0.6);
      if (c.sig === "buy") { const t = y(c.l) + 3; out += `<polygon points="${cx},${t} ${cx - hw},${t + 7} ${cx + hw},${t + 7}" fill="#1F3A2E"></polygon>`; }
      else { const t = y(c.h) - 3; out += `<polygon points="${cx},${t} ${cx - hw},${t - 7} ${cx + hw},${t - 7}" fill="#9A3B2E"></polygon>`; }
    });
    return out;
  }
  // Chuỗi mẫu vẽ glyph hai tín hiệu ở tab Cài đặt: [o,h,l,c,st,up,ema]
  const TREND_GLYPH = {
    st_buy: [[9.0, 9.2, 8.7, 8.8, 9.6, false, 9.3], [8.8, 9.0, 8.5, 8.6, 9.5, false, 9.2], [8.6, 9.1, 8.5, 9.0, 9.4, false, 9.1], [9.0, 9.6, 8.9, 9.5, 8.5, true, 9.1], [9.5, 10.1, 9.4, 10.0, 8.6, true, 9.3], [10.0, 10.5, 9.9, 10.4, 8.9, true, 9.6]],
    st_exit: [[9.0, 9.6, 8.9, 9.5, 8.5, true, 9.1], [9.5, 10.1, 9.4, 10.0, 8.7, true, 9.3], [10.0, 10.3, 9.7, 9.8, 8.9, true, 9.5], [9.8, 9.9, 9.2, 9.3, 8.9, true, 9.5], [9.3, 9.4, 8.6, 8.7, 9.9, false, 9.4], [8.7, 8.9, 8.3, 8.4, 9.9, false, 9.2]],
  };
  for (const k in TREND_GLYPH) TREND_GLYPH[k] = TREND_GLYPH[k].map((a) => ({ o: a[0], h: a[1], l: a[2], c: a[3], st: a[4], up: a[5], ema: a[6] }));

  // ---------------------------------------------------------------- tải dữ liệu
  async function load() {
    try {
      const r = await fetch("data/latest.json", { cache: "no-cache" });
      if (!r.ok) throw new Error("Chưa có data/latest.json — job sau phiên chưa chạy lần nào.");
      D = await r.json();
    } catch (err) {
      $("strip").innerHTML = `<span class="v">Chưa có dữ liệu</span><span class="note">${esc(err.message)}</span>`;
      $("todayBody").innerHTML = `<div class="empty"><b>Job chưa chạy lần nào</b>Nhập danh mục ở <a href="#settings">Cài đặt</a> và dán vào GitHub; sau lần job chạy đầu tiên, kết quả sẽ hiện ở đây.</div>`;
      renderSettings();
      return;
    }
    renderToday(); renderHistory(); renderSettings();
    BARSD = null;   // nến cho tab Biểu đồ tải lại lần mở tab kế tiếp (phiên mới)
    if ($("p-chart").classList.contains("on")) renderChart();
  }

  // ---------------------------------------------------------------- Hôm nay
  function renderToday() {
    const all = D.signals || [], stale = D.stale || [], src = D.source || {};
    const trend = all.filter((s) => s.kind === "trend"), sig = all.filter((s) => s.kind !== "trend");
    const nSym = new Set(all.map((s) => s.symbol)).size;
    $("todaySub").textContent = `Mẫu hình nến và xu hướng trên nến đã chốt — ${D.watchlist ? D.watchlist.n : "?"} mã đang theo dõi.`;
    const gen = D.generated_at ? D.generated_at.slice(11, 16) : "";
    let note = `Nguồn DNSE chốt lúc ${gen}`;
    if (src.late) note += " · nguồn chốt muộn, chạy lại ở cron dự phòng";
    if (stale.length) note += ` · ${stale.length} mã chưa khớp lệnh hôm nay (${stale.slice(0, 4).map((s) => s.symbol).join(", ")}${stale.length > 4 ? "…" : ""})`;
    if (src.dnse_error) note += ` · <b>DNSE lỗi: ${esc(src.dnse_error)}</b>`;
    if (D.watchlist && D.watchlist.source === "cache") note += " · danh mục lấy từ bản chụp — Variable WATCHLIST trên GitHub đang trống?";
    if (!D.watchlist || !D.watchlist.n) {
      // Chưa nhập danh mục: không có gì để quét — chỉ dẫn sang tab Cài đặt
      $("strip").innerHTML = `<span class="k">Chưa có danh mục</span><span class="v">0 mã theo dõi</span><span class="note">Job chạy lúc ${gen || "—"} nhưng chưa có mã nào để quét.</span>`;
      $("trendBody").innerHTML = ""; $("boardBody").innerHTML = "";
      $("todayBody").innerHTML = `<div class="empty"><b>Nhập danh mục để bắt đầu</b>Vào <a href="#settings">Cài đặt → Danh mục theo dõi</a>, gõ các mã, bấm "Chuẩn hoá &amp; sao chép" rồi dán vào GitHub Variable <span class="mono">WATCHLIST</span>. Từ lần job chạy kế tiếp, tín hiệu sẽ hiện ở đây.</div>`;
      return;
    }
    const parts = [];
    if (trend.length) parts.push(`${trend.length} xu hướng`);
    if (sig.length) parts.push(`${sig.length} mẫu nến`);
    $("strip").innerHTML =
      `<span class="k">Phiên ${dmy(D.trade_date)}</span><svg aria-hidden="true"><use href="#i-arrow"/></svg>` +
      `<span class="v">${src.n_priced || 0} mã đã quét</span><svg aria-hidden="true"><use href="#i-arrow"/></svg>` +
      `<span class="v">${parts.length ? `${parts.join(" · ")} · ${nSym} mã` : "không có tín hiệu"}</span>` +
      `<span class="note">${note}</span>`;

    renderTrendCards(trend);
    renderBoard();

    if (!sig.length) {
      $("todayBody").innerHTML = `<div class="seclabel"><div class="kicker">Mẫu hình nến · 18 mẫu</div></div><div class="empty"><b>Không có mẫu hình nào hôm nay</b>Đã quét ${src.n_priced || 0} mã trên nến đã chốt phiên ${dmy(D.trade_date)}. Không có gì để làm — đó cũng là một câu trả lời.</div>`;
      return;
    }
    // Gộp theo mã: một thẻ một mã, nhiều mẫu thì liệt kê thêm
    const bySym = new Map();
    sig.forEach((s) => { if (!bySym.has(s.symbol)) bySym.set(s.symbol, []); bySym.get(s.symbol).push(s); });
    const state = new Map((D.trend || []).map((t) => [t.symbol, t]));
    let i = 0;
    $("todayBody").innerHTML = `<div class="seclabel"><div class="kicker">Mẫu hình nến · 18 mẫu</div><span class="chip soft">${sig.length} mẫu · ${bySym.size} mã</span></div><div class="cards">` + [...bySym.entries()].map(([sym, list]) => {
      const s = list[0], buy = s.direction === "buy";
      const dirs = new Set(list.map((x) => x.direction));
      const chip = dirs.size > 1 ? `<span class="chip sell">TRÁI CHIỀU</span>` : `<span class="chip ${buy ? "buy" : "sell"}">${buy ? "MUA" : "BÁN"}</span>`;
      const chg = s.change_pct, ccls = chg > 0 ? "up" : chg < 0 ? "down" : "flat";
      const extra = list.length > 1 ? `<div class="more">Cùng phiên còn: <b>${list.slice(1).map((x) => esc(x.name)).join(", ")}</b></div>` : "";
      const rp = REPLAY[s.pattern] || {};
      const tr = state.get(sym);
      // Dòng XU HƯỚNG: mẫu MUA khi Supertrend đỏ là mua ngược xu hướng — nói thẳng để người dùng tự cân nhắc
      const trLine = tr ? `<div class="${tr.up ? "a" : "c"}"><span>Xu hướng</span><span>Supertrend ${tr.up ? "xanh" : "đỏ"} từ ${dmy(tr.since)} (${tr.days} phiên)${buy && !tr.up ? " — mẫu MUA ngược xu hướng, cân nhắc bỏ qua" : ""} · <a href="#chart" data-chart="${esc(sym)}">biểu đồ</a></span></div>` : "";
      // Ô biểu đồ rộng dưới nến mẫu: 46 phiên có dải Supertrend/EMA10, nền tô xanh/đỏ theo Supertrend
      // (cùng hàm vẽ với thẻ xu hướng). latest.json cũ chưa có trend_candles thì bỏ qua, thẻ hiện như cũ.
      const tc = s.trend_candles || [];
      const wide = tc.length ? `<div class="chart wide"><svg viewBox="0 0 300 72" preserveAspectRatio="none" aria-hidden="true">${trendChart(tc, 300, 72, false, true)}</svg>
          <div class="legend"><span class="st">Supertrend</span><span class="ema">EMA10</span><span class="bg">Nền = màu Supertrend</span><span class="tri">▲ mua · ▼ lật đỏ</span><span>${tc.length} phiên</span></div></div>` : "";
      i += 1;
      return `<div class="card ${dirs.size > 1 ? "sell" : buy ? "buy" : "sell"}">
        <div class="top"><div class="num">${pad2(i)}</div><h3>${esc(sym)} · ${esc(s.name)}</h3>${chip}</div>
        <div class="desc">${esc(s.hint)}${s.company_name ? ` <span class="mute">— ${esc(s.company_name)}</span>` : ""}</div>
        <div class="chart"><svg viewBox="0 0 132 72" aria-hidden="true">${miniChart(s.candles || [], s.bars || 2, 132, 72, false)}</svg>
          <div class="px"><div class="k">Đóng cửa</div><div class="v">${px(s.price)}</div><div class="c ${ccls}">${chg == null ? "—" : (chg > 0 ? "+" : "") + chg.toFixed(1) + "% hôm nay"}</div></div></div>
        ${wide}
        <div class="kv"><div class="a"><span>Gợi ý</span><span>${esc(s.advice)}</span></div>${trLine}<div class="w"><span>Lưu ý</span><span>${esc(rp.note || "")}</span></div>${s.caution ? `<div class="c"><span>Cảnh báo</span><span>${esc(s.caution)}</span></div>` : ""}</div>
        ${extra}</div>`;
    }).join("") + `</div>`;
  }

  /* Thẻ xu hướng: mỗi tín hiệu một thẻ (đúng như mỗi tín hiệu một thông báo), nến 22 phiên có đường
     Supertrend/EMA, 4 ô số: dải Supertrend (= dừng lỗ), rủi ro tới dừng lỗ, EMA10, khối lượng. */
  function renderTrendCards(trend) {
    if (!trend.length) {
      $("trendBody").innerHTML = `<div class="seclabel"><div class="kicker">Xu hướng · Supertrend</div><span class="new">Mới</span></div><div class="empty"><b>Không có tín hiệu xu hướng mới</b>Không mã nào lật màu Supertrend hay vượt EMA10 lần đầu trong phiên ${dmy(D.trade_date)}. Bảng dưới cho biết mã nào đang xanh.</div>`;
      return;
    }
    let i = 0;
    $("trendBody").innerHTML = `<div class="seclabel"><div class="kicker">Xu hướng · Supertrend</div><span class="new">Mới</span></div><div class="cards">` + trend.map((s) => {
      const buy = s.direction === "buy", chg = s.change_pct, ccls = chg > 0 ? "up" : chg < 0 ? "down" : "flat", rp = REPLAY[s.pattern] || {};
      i += 1;
      return `<div class="card ${buy ? "buy" : "sell"}">
        <div class="top"><div class="num">${pad2(i)}</div><h3>${esc(s.symbol)} · ${esc(s.name)}</h3><span class="chip ${buy ? "buy" : "sell"}">${buy ? "MUA" : "THOÁT"}</span></div>
        <div class="desc">${esc(s.hint)}${s.company_name ? ` <span class="mute">— ${esc(s.company_name)}</span>` : ""}</div>
        <div class="chart"><svg viewBox="0 0 132 72" aria-hidden="true">${trendChart(s.candles || [], 132, 72, false)}</svg>
          <div class="px"><div class="k">Đóng cửa</div><div class="v">${px(s.price)}</div><div class="c ${ccls}">${chg == null ? "—" : (chg > 0 ? "+" : "") + chg.toFixed(1) + "% hôm nay"}</div></div></div>
        <div class="lv"><div><span class="k">${buy ? "Dừng lỗ · dải Supertrend" : "Dải Supertrend (nay là kháng cự)"}</span><span class="v">${px(s.st_line)}</span></div><div><span class="k">${buy ? "Rủi ro tới dừng lỗ" : "Xanh được"}</span><span class="v">${buy ? (s.risk_pct == null ? "—" : "−" + s.risk_pct + "%") : (s.days_in_trend == null ? "—" : s.days_in_trend + " phiên")}</span></div><div><span class="k">EMA10</span><span class="v">${px(s.ema)}</span></div><div><span class="k">Khối lượng</span><span class="v">${s.volume == null ? "—" : (s.volume / 1e3).toFixed(0) + "k"}</span></div></div>
        <div class="kv"><div class="a"><span>Gợi ý</span><span>${buy && s.st_line != null ? `Mua phiên sau; đặt dừng lỗ ${px(s.st_line)}; khối lượng = 1% vốn ÷ ${s.risk_pct}%.` : esc(s.advice)}</span></div><div class="w"><span>Lưu ý</span><span>${esc(rp.note || "")}</span></div></div>
        <button type="button" class="linkbtn" data-chart="${esc(s.symbol)}">Xem biểu đồ Supertrend ${esc(s.symbol)} →</button></div>`;
    }).join("") + `</div>`;
  }

  /* Bảng 39 mã: xanh đậm = xanh và giá trên EMA10 (điều kiện mua còn nguyên); số nhỏ = số phiên ở trạng thái đó. */
  function renderBoard() {
    const tr = D.trend || [];
    if (!tr.length) { $("boardBody").innerHTML = ""; return; }
    const up = tr.filter((t) => t.up).length;
    $("boardBody").innerHTML = `<div class="seclabel"><div class="kicker">Xu hướng ${tr.length} mã theo Supertrend (10,3)</div></div><div class="cards"><div class="card info">
      <div class="top"><h3>${up} xanh · ${tr.length - up} đỏ</h3><span class="chip soft">phiên ${dmy(D.trade_date)}</span></div>
      <div class="desc">Xanh đậm = xanh và giá đang trên EMA10 (điều kiện mua còn nguyên). Số nhỏ là số phiên ở trạng thái đó. Bấm mã để mở biểu đồ.</div>
      <div class="board">${tr.map((t) => `<span class="${t.up ? "g" + (t.above_ema ? " w" : "") : "r"}" data-chart="${esc(t.symbol)}" title="${t.up ? "xanh" : "đỏ"} từ ${dmy(t.since)} · dải ${px(t.line)}">${esc(t.symbol)} <small>${t.days}</small></span>`).join("")}</div></div></div>`;
  }

  // ---------------------------------------------------------------- Lịch sử
  function renderHistory() {
    const hist = D.history || [];
    $("histKicker").textContent = `${hist.length} phiên gần nhất`;
    const nb = hist.reduce((a, h) => a + h.n_buy, 0), ns = hist.reduce((a, h) => a + h.n_sell, 0);
    const nt = hist.reduce((a, h) => a + (h.n_trend_buy || 0) + (h.n_trend_exit || 0), 0);
    const per = hist.length ? ((nb + ns + nt) / hist.length).toFixed(1) : "—";
    $("totals").innerHTML =
      `<div class="tot" style="background:var(--peach);border-color:var(--peach-line)"><div class="k">Xu hướng</div><div class="v">${nt}</div></div>` +
      `<div class="tot" style="background:var(--sage);border-color:var(--sage-line)"><div class="k">Mẫu nến</div><div class="v">${nb + ns}</div></div>` +
      `<div class="tot" style="background:var(--strip);border-color:var(--strip-line)"><div class="k">Mỗi phiên</div><div class="v">${per}</div></div>`;
    if (!hist.length) { $("days").innerHTML = `<div class="empty"><b>Chưa có phiên nào</b>Job ghi lại đây sau mỗi phiên đã quét.</div>`; return; }
    $("days").innerHTML = hist.map((h) => {
      const chips = [];
      if (h.n_trend_buy) chips.push(`<span class="chip trend">${h.n_trend_buy} MUA · XU HƯỚNG</span>`);
      if (h.n_trend_exit) chips.push(`<span class="chip trend">${h.n_trend_exit} THOÁT</span>`);
      if (h.n_buy) chips.push(`<span class="chip buy">${h.n_buy} MUA</span>`);
      if (h.n_sell) chips.push(`<span class="chip sell">${h.n_sell} BÁN</span>`);
      if (!chips.length) chips.push(`<span class="chip soft">Không có</span>`);
      if (h.late) chips.push(`<span class="chip late">Nguồn chốt muộn</span>`);
      const tl = h.trend_items && h.trend_items.length ? `<b>Xu hướng:</b> ${h.trend_items.map(esc).join(" · ")}` : "";
      const cl = h.items && h.items.length ? `${tl ? "<br>" : ""}Mẫu nến: ${h.items.map(esc).join(" · ")}` : "";
      return `<div class="day"><div class="top"><b>${dow(h.date)} ${dmy(h.date)}</b>${chips.join("")}</div><div class="list">${tl || cl ? tl + cl : "Đã quét, không tín hiệu nào."}</div></div>`;
    }).join("");
  }

  // ---------------------------------------------------------------- Cài đặt
  function renderSettings() {
    const pats = (D && D.patterns) || null;
    const disabled = new Set(((D && D.settings) || {}).patterns_disabled || []);
    const ids = pats ? Object.keys(pats) : Object.keys(SAMPLES);
    const row = (pid) => {
      const m = pats ? pats[pid] : { name: pid, hint: "" };
      const off = disabled.has(pid), rp = REPLAY[pid] || {};
      return `<div class="prow${off ? " off" : ""}">${glyph(pid, m.bars)}<div class="t"><div class="n">${esc(m.name)}</div><div class="h">${esc(m.hint)}</div></div><div class="f">${rp.pm != null ? rp.pm.toFixed(1) + "/th" : ""}</div><div class="tg ${off ? "off" : "on"}" title="${off ? "Đang tắt" : "Đang bật"}"></div></div>`;
    };
    const isTrend = (p) => (pats ? pats[p].kind === "trend" : !!TREND_GLYPH[p]);
    const trends = pats ? ids.filter(isTrend) : Object.keys(TREND_GLYPH);
    const cand = ids.filter((p) => !isTrend(p));
    const buys = cand.filter((p) => !pats || pats[p].direction === "buy"), sells = cand.filter((p) => pats && pats[p].direction === "sell");
    const trow = (pid) => pats ? row(pid) : `<div class="prow">${glyph(pid)}<div class="t"><div class="n">${pid}</div></div><div class="f"></div><div class="tg on"></div></div>`;
    $("trendRows").innerHTML = trends.map(trow).join(""); $("trendCount").textContent = `${trends.length} tín hiệu`;
    $("buyRows").innerHTML = buys.map(row).join(""); $("buyCount").textContent = `${buys.length} mẫu`;
    $("sellRows").innerHTML = sells.map(row).join(""); $("sellCount").textContent = `${sells.length} mẫu`;
    renderWatchlist();
    fetch("data/state.json", { cache: "no-cache" }).then((r) => r.ok ? r.json() : null).then((st) => {
      if (!st) return;
      const dv = st.devices || {}, p = st.push || {};
      let s = `Job chạy lần cuối ${st.last_run ? st.last_run.slice(0, 16).replace("T", " ") : "—"} · ${dv.n || 0} máy đã đăng ký (${dv.source || "—"}) · VAPID ${dv.vapid ? "OK" : "THIẾU"}`;
      if (p.mode) s += ` · lần báo gần nhất: ${p.mode === "digest" ? "tổng hợp" : p.mode === "per_symbol" ? p.n_symbols + " mã" : "không có mẫu"}, gửi ${p.sent || 0}`;
      if (st.push_gone_at) s += ` · <b style="color:var(--sell)">có máy đã huỷ đăng ký (${st.push_gone_at.slice(0, 10)}) — bấm Đăng ký lại</b>`;
      $("stateFoot").innerHTML = s;
    }).catch(() => {});
  }

  // ---------------------------------------------------------------- danh mục theo dõi
  /* Không có máy chủ nên trang không tự lưu được: người dùng gõ mã, bấm sao chép, dán vào GitHub Variable
     WATCHLIST; job đọc từ đó và ghi lại `latest.watchlist.symbols` để lần sau ô này điền sẵn.
     normalizeWatchlist phải cho cùng kết quả với job/watchlist.py::parse (tách theo , ; khoảng trắng,
     xuống dòng; viết hoa; 3–6 ký tự chữ-số; bỏ trùng; A→Z). Bản nháp giữ trong localStorage. */
  const WL_DRAFT = "cw_wl_draft";
  function normalizeWatchlist(text) {
    const ok = new Set(), bad = [];
    String(text || "").split(/[\s,;]+/).forEach((t) => {
      const u = t.trim().toUpperCase();
      if (!u) return;
      if (/^[A-Z0-9]{3,6}$/.test(u)) ok.add(u); else bad.push(u);
    });
    return { symbols: [...ok].sort(), bad };
  }
  const jobSymbols = () => (D && D.watchlist && D.watchlist.symbols) || [];
  function wlDraft() { try { return localStorage.getItem(WL_DRAFT); } catch (_) { return null; } }
  function wlSaveDraft(v) { try { if (v == null) localStorage.removeItem(WL_DRAFT); else localStorage.setItem(WL_DRAFT, v); } catch (_) { /* riêng tư / bị chặn — bỏ qua */ } }
  function wlUpdate() {
    const { symbols, bad } = normalizeWatchlist($("wlTxt").value);
    $("wlCount").textContent = symbols.length ? `${symbols.length} mã` : "";
    let s = symbols.length ? `<b>${symbols.length} mã hợp lệ:</b> ${symbols.join(", ")}` : "Chưa có mã nào.";
    if (bad.length) s += ` · <span class="bad">bỏ qua ${bad.length}: ${bad.map(esc).join(", ")}</span> (mã gồm 3–6 chữ/số)`;
    $("wlState").innerHTML = s;
    const cur = jobSymbols();
    $("wlReset").hidden = !cur.length || cur.join(",") === symbols.join(",");
  }
  function renderWatchlist() {
    const cur = jobSymbols();
    const draft = wlDraft();
    if (!$("wlTxt").value) $("wlTxt").value = draft != null ? draft : cur.join(", ");
    wlUpdate();
    if (D && D.watchlist) {
      const src = D.watchlist.source === "variable" ? "Variable WATCHLIST" : D.watchlist.source === "cache" ? "bản chụp trong repo" : "chưa có";
      $("wlJob").innerHTML = cur.length ? `Job đang theo dõi <b>${cur.length} mã</b> (nguồn: ${src}, đọc lúc ${D.generated_at ? D.generated_at.slice(0, 16).replace("T", " ") : "—"}).`
        : `Job chưa có danh mục (nguồn: ${src}) — sau khi dán Variable, bấm <i>Run workflow</i> hoặc chờ 15:35.`;
    } else {
      $("wlJob").textContent = "Job chưa chạy lần nào — danh mục sẽ hiện ở đây sau lần chạy đầu.";
    }
  }
  $("wlTxt").addEventListener("input", () => { wlSaveDraft($("wlTxt").value); wlUpdate(); });
  $("wlReset").addEventListener("click", () => { $("wlTxt").value = jobSymbols().join(", "); wlSaveDraft(null); wlUpdate(); });
  $("wlCopy").addEventListener("click", async () => {
    const { symbols, bad } = normalizeWatchlist($("wlTxt").value);
    if (!symbols.length) { toast("Chưa có mã hợp lệ", "Gõ ít nhất một mã, VD HPG."); return; }
    const code = symbols.join(", ");
    $("wlTxt").value = code; wlSaveDraft(code); wlUpdate();
    try { await navigator.clipboard.writeText(code); }
    catch (_) { $("wlTxt").select(); document.execCommand("copy"); }
    toast(`Đã sao chép ${symbols.length} mã`, `Dán vào GitHub → Settings → Variables → WATCHLIST.${bad.length ? ` Đã bỏ ${bad.length} mã sai dạng.` : ""}`);
  });

  // ---------------------------------------------------------------- push
  const b64ToU8 = (s) => { const p = "=".repeat((4 - s.length % 4) % 4); const b = atob((s + p).replace(/-/g, "+").replace(/_/g, "/")); return Uint8Array.from(b, (c) => c.charCodeAt(0)); };
  const SW = "sw.js?v=1";
  async function pushStatus() {
    const st = $("pushState");
    if (!("serviceWorker" in navigator) || !("PushManager" in window)) { st.textContent = "Trình duyệt này không hỗ trợ thông báo đẩy."; $("pushBtn").disabled = true; return; }
    if (!CFG.VAPID_PUBLIC) { st.textContent = "Chưa có VAPID_PUBLIC trong config.js."; $("pushBtn").disabled = true; return; }
    const reg = await navigator.serviceWorker.ready;
    const sub = await reg.pushManager.getSubscription();
    if (sub) {
      st.textContent = CFG.WORKER_URL ? "Máy này đã đăng ký · máy chủ tạm của GitHub đánh thức được kể cả khi app đóng."
        : "Máy này đã tạo địa chỉ nhận · đảm bảo đoạn mã bên dưới đã được dán vào GitHub.";
      $("pushBtn").textContent = "Đăng ký lại"; $("testBtn").hidden = !CFG.WORKER_URL;
      if (!CFG.WORKER_URL) showSubCode(sub);
    } else { st.textContent = "Máy này chưa đăng ký nhận thông báo."; }
  }
  function showSubCode(sub) {
    const code = JSON.stringify([sub.toJSON()]);
    $("subCodeWrap").innerHTML = `<div class="subcode"><b>Đoạn mã đăng ký của máy này.</b> Dán vào GitHub → Settings → Secrets and variables → Actions → <span class="mono">PUSH_SUBS_FALLBACK</span> (nhiều máy thì nối các đoạn trong cùng một mảng JSON). Làm một lần mỗi máy.
      <textarea id="subTxt" readonly></textarea><div class="btns" style="margin-top:6px"><button type="button" class="btn" id="copySub">Sao chép</button></div></div>`;
    $("subTxt").value = code;
    $("copySub").addEventListener("click", async () => {
      try { await navigator.clipboard.writeText(code); toast("Đã sao chép", "Dán vào GitHub Secret PUSH_SUBS_FALLBACK."); }
      catch (_) { $("subTxt").select(); document.execCommand("copy"); toast("Đã sao chép", ""); }
    });
  }
  const swReady = () => Promise.race([
    navigator.serviceWorker.ready,
    new Promise((_, rej) => setTimeout(() => rej(new Error("Phần chạy nền chưa sẵn sàng — đóng hẳn app, mở lại rồi bấm lần nữa")), 8000)),
  ]);
  $("pushBtn").addEventListener("click", async () => {
    const st = $("pushState"), btn = $("pushBtn");
    btn.disabled = true;
    try {
      if (Notification.permission === "denied") { st.textContent = "Điện thoại đang CHẶN thông báo của trang này. Mở Cài đặt trình duyệt → Cài đặt trang web → Thông báo → bật, rồi bấm lại."; return; }
      st.textContent = "Đang xin quyền thông báo… (nếu hiện hộp thoại, bấm Cho phép)";
      const perm = await Notification.requestPermission();
      if (perm !== "granted") { st.textContent = "Anh chưa cho phép. Bấm lại và chọn Cho phép."; return; }
      st.textContent = "Đang chuẩn bị phần chạy nền…";
      if (!navigator.serviceWorker.controller) { try { await navigator.serviceWorker.register(SW); } catch (_) { /* thử tiếp */ } }
      const reg = await swReady();
      st.textContent = "Đang tạo địa chỉ nhận với Google…";
      let sub = await reg.pushManager.getSubscription();
      if (!sub) sub = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: b64ToU8(CFG.VAPID_PUBLIC) });
      if (CFG.WORKER_URL) {
        const r = await fetch(CFG.WORKER_URL + "/subscribe", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(Object.assign({ ua: navigator.userAgent.slice(0, 120) }, sub.toJSON())) });
        if (!r.ok) throw new Error("Worker trả lỗi " + r.status);
        toast("Đã đăng ký máy này", "Từ giờ cảnh báo sau phiên sẽ tới đây.");
      } else {
        toast("Đã tạo địa chỉ nhận", "Sao chép đoạn mã bên dưới và dán vào GitHub — một lần cho máy này.");
      }
      await pushStatus();
    } catch (err) {
      st.textContent = "Không đăng ký được: " + (err && err.message ? err.message : err) + " — chụp màn hình dòng này gửi lại.";
    } finally { btn.disabled = false; }
  });
  $("testBtn").addEventListener("click", async () => {
    try {
      const r = await fetch(CFG.WORKER_URL + "/test", { method: "POST" });
      toast(r.ok ? "Đã yêu cầu gửi thử" : "Gửi thử lỗi " + r.status, r.ok ? "Thông báo thật sẽ tới trong vài giây." : "");
    } catch (err) { alert(err.message); }
  });
  let toastTimer = null;
  function toast(t, b) { $("toastTitle").textContent = t; $("toastBody").textContent = b || ""; $("toast").classList.add("on"); clearTimeout(toastTimer); toastTimer = setTimeout(() => $("toast").classList.remove("on"), 5000); }
  $("toast").addEventListener("click", () => $("toast").classList.remove("on"));

  // ---------------------------------------------------------------- Biểu đồ
  /* Toán chỉ báo chép từ job/trend.py (cùng công thức, cùng tham số) — nến dạng [d,o,h,l,c,v]. */
  const O = 1, H = 2, L = 3, C = 4;
  function ema(bars, n) {
    const out = new Array(bars.length).fill(null); if (bars.length < n) return out;
    let v = 0; for (let i = 0; i < n; i++) v += bars[i][C]; v /= n; out[n - 1] = v;
    const a = 2 / (n + 1); for (let i = n; i < bars.length; i++) { v = a * bars[i][C] + (1 - a) * v; out[i] = v; }
    return out;
  }
  function atrWilder(bars, n) {
    const out = new Array(bars.length).fill(null); if (bars.length < n) return out;
    const tr = bars.map((b, i) => i === 0 ? b[H] - b[L] : Math.max(b[H] - b[L], Math.abs(b[H] - bars[i - 1][C]), Math.abs(b[L] - bars[i - 1][C])));
    let v = 0; for (let i = 0; i < n; i++) v += tr[i]; v /= n; out[n - 1] = v;
    for (let i = n; i < bars.length; i++) { v = (v * (n - 1) + tr[i]) / n; out[i] = v; }
    return out;
  }
  function supertrend(bars, n, mult) {
    const atr = atrWilder(bars, n), out = new Array(bars.length).fill(null); let prev = null;
    for (let i = 0; i < bars.length; i++) {
      if (atr[i] == null) continue;
      const b = bars[i], hl2 = (b[H] + b[L]) / 2, bu = hl2 + mult * atr[i], bl = hl2 - mult * atr[i];
      let fu = bu, fl = bl, up;
      if (prev === null) up = false;
      else { const pc = bars[i - 1][C]; fu = (bu < prev.fu || pc > prev.fu) ? bu : prev.fu; fl = (bl > prev.fl || pc < prev.fl) ? bl : prev.fl; up = prev.up ? !(b[C] < fl) : (b[C] > fu); }
      prev = { up, line: up ? fl : fu, fu, fl }; out[i] = prev;
    }
    return out;
  }
  let BARSD = null, barsLoading = null;
  const cv = $("chart"), ctx = cv.getContext("2d"), tip = $("tip");
  const cur = { sym: "", n: 120, end: 0, hover: -1, calc: null, layout: null };
  function loadBars() {
    if (BARSD) return Promise.resolve(BARSD);
    if (!barsLoading) barsLoading = fetch("data/bars.json", { cache: "no-cache" }).then((r) => { if (!r.ok) throw new Error("Chưa có data/bars.json — job chưa chạy bản mới."); return r.json(); })
      .then((j) => { BARSD = j; return j; }).catch((err) => { $("r-lab").textContent = err.message; barsLoading = null; throw err; });
    return barsLoading;
  }
  function calc(sym) {
    const bars = BARSD.bars[sym], st = supertrend(bars, 10, 3), em = ema(bars, 10);
    const buys = [], exits = []; let armed = false;
    for (let i = 1; i < bars.length; i++) {
      if (!st[i] || !st[i - 1] || em[i] == null) continue;
      if (!st[i].up && st[i - 1].up) { exits.push(i); armed = true; }
      else if (!st[i].up) armed = true;
      else if (armed && bars[i][C] > em[i]) { buys.push(i); armed = false; }
    }
    return { bars, st, em, buys, exits };
  }
  function openChart(sym) { cur.sym = sym; cur.end = 0; switchTab("chart"); }
  function renderChart() {
    loadBars().then(() => {
      const syms = Object.keys(BARSD.bars).sort();
      const state = new Map(((D && D.trend) || []).map((t) => [t.symbol, t]));
      if (!$("c-sym").options.length) $("c-sym").innerHTML = syms.map((s) => { const t = state.get(s); return `<option value="${s}">${s}${t ? (t.up ? " · xanh" : " · đỏ") : ""}</option>`; }).join("");
      if (!cur.sym || !BARSD.bars[cur.sym]) cur.sym = syms.includes("HPG") ? "HPG" : syms[0];
      $("c-sym").value = cur.sym;
      cur.calc = calc(cur.sym);
      const bars = cur.calc.bars, total = bars.length, n = cur.n === 0 ? total : Math.min(cur.n, total);
      if (cur.end === 0 || cur.end > total) cur.end = total;
      $("r-off").max = total - n; $("r-off").value = cur.end - n;
      const t = state.get(cur.sym);
      $("chartSub").textContent = `${cur.sym}${t ? ` — Supertrend ${t.up ? "xanh" : "đỏ"} từ ${dmy(t.since)}, dải ${px(t.line)}` : ""} · chạm vào nến để xem giá.`;
      draw(n);
      const last = bars[total - 1], s = cur.calc.st[total - 1], e = cur.calc.em[total - 1];
      $("cstat").innerHTML = `<div class="tot" style="background:var(--strip);border-color:var(--strip-line)"><div class="k">Đóng cửa ${dmy(last[0])}</div><div class="v">${px(last[C])}</div></div>` +
        (s ? `<div class="tot" style="background:${s.up ? "var(--sage)" : "var(--blush)"};border-color:${s.up ? "var(--sage-line)" : "var(--blush-line)"}"><div class="k">Dải Supertrend</div><div class="v">${px(s.line)}</div></div>` : "") +
        (e != null ? `<div class="tot" style="background:var(--blue);border-color:var(--blue-line)"><div class="k">EMA10 · giá ${last[C] > e ? "trên" : "dưới"}</div><div class="v">${px(e)}</div></div>` : "");
    }).catch(() => {});
  }
  function draw(n) {
    const { bars, st, em, buys, exits } = cur.calc;
    const dpr = window.devicePixelRatio || 1, W = cv.clientWidth, Hh = cv.clientHeight;
    if (!W) return;
    cv.width = W * dpr; cv.height = Hh * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const end = cur.end, start = Math.max(0, end - n);
    const padL = 6, padR = 50, padT = 10, padB = 22, pw = W - padL - padR, ph = Hh - padT - padB;
    let lo = Infinity, hi = -Infinity;
    for (let i = start; i < end; i++) { lo = Math.min(lo, bars[i][L], st[i] ? st[i].line : Infinity, em[i] ?? Infinity); hi = Math.max(hi, bars[i][H], st[i] ? st[i].line : -Infinity, em[i] ?? -Infinity); }
    const span = (hi - lo) || 1; lo -= span * .04; hi += span * .04;
    const bw = pw / n, x = (i) => padL + (i - start + .5) * bw, y = (v) => padT + (hi - v) / (hi - lo) * ph;
    cur.layout = { start, end, bw, padL, x, y };
    ctx.clearRect(0, 0, W, Hh); ctx.fillStyle = "#fff"; ctx.fillRect(0, 0, W, Hh);
    for (let i = start; i < end; i++) if (st[i]) { ctx.fillStyle = st[i].up ? "#E3EEDF" : "#F4E6E0"; ctx.fillRect(x(i) - bw / 2, padT, bw + .5, ph); }
    ctx.font = "10px Archivo, Arial, sans-serif"; ctx.fillStyle = "#4B5A52"; ctx.strokeStyle = "#E7E2D6"; ctx.lineWidth = 1;
    for (let k = 0; k <= 4; k++) { const v = lo + (hi - lo) * k / 4, yy = Math.round(y(v)) + .5; ctx.beginPath(); ctx.moveTo(padL, yy); ctx.lineTo(padL + pw, yy); ctx.stroke(); ctx.textAlign = "left"; ctx.fillText(v.toFixed(2), padL + pw + 5, yy + 3); }
    let lastM = ""; const every = n > 200 ? 3 : n > 90 ? 2 : 1; ctx.textAlign = "center";
    for (let i = start; i < end; i++) { const ym = bars[i][0].slice(0, 7); if (ym !== lastM) { lastM = ym; const m = +ym.slice(5, 7); if ((m - 1) % every === 0) { const xx = Math.round(x(i)) + .5; ctx.strokeStyle = "#E7E2D6"; ctx.beginPath(); ctx.moveTo(xx, padT); ctx.lineTo(xx, padT + ph); ctx.stroke(); ctx.fillStyle = "#4B5A52"; ctx.fillText(m === 1 ? ym.slice(0, 4) : "T" + m, xx, Hh - 7); } } }
    const cw = Math.max(1, bw * .66);
    for (let i = start; i < end; i++) { const b = bars[i], col = b[C] >= b[O] ? "#2E7D4F" : "#B84A3A", xx = x(i); ctx.strokeStyle = col; ctx.fillStyle = col; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(xx, y(b[H])); ctx.lineTo(xx, y(b[L])); ctx.stroke(); const yo = y(b[O]), yc = y(b[C]), top = Math.min(yo, yc), hh = Math.max(1, Math.abs(yo - yc)); if (cw >= 3) ctx.fillRect(xx - cw / 2, top, cw, hh); else { ctx.beginPath(); ctx.moveTo(xx, top); ctx.lineTo(xx, top + hh); ctx.stroke(); } }
    ctx.strokeStyle = "#5B6FA8"; ctx.lineWidth = 1.5; ctx.beginPath(); let pen = false;
    for (let i = start; i < end; i++) { if (em[i] == null) { pen = false; continue; } if (!pen) { ctx.moveTo(x(i), y(em[i])); pen = true; } else ctx.lineTo(x(i), y(em[i])); }
    ctx.stroke();
    ctx.lineWidth = 2; let segUp = null; ctx.beginPath();
    for (let i = start; i < end; i++) { const s = st[i]; if (!s) continue; if (segUp === null || s.up !== segUp) { if (segUp !== null) { ctx.strokeStyle = segUp ? "#2E7D4F" : "#B84A3A"; ctx.stroke(); } ctx.beginPath(); ctx.moveTo(x(i), y(s.line)); segUp = s.up; } else ctx.lineTo(x(i), y(s.line)); }
    if (segUp !== null) { ctx.strokeStyle = segUp ? "#2E7D4F" : "#B84A3A"; ctx.stroke(); }
    const tri = (xx, yy, upDir, col) => { ctx.fillStyle = col; ctx.beginPath(); if (upDir) { ctx.moveTo(xx, yy); ctx.lineTo(xx - 5, yy + 9); ctx.lineTo(xx + 5, yy + 9); } else { ctx.moveTo(xx, yy); ctx.lineTo(xx - 5, yy - 9); ctx.lineTo(xx + 5, yy - 9); } ctx.closePath(); ctx.fill(); };
    for (const i of buys) if (i >= start && i < end) tri(x(i), y(bars[i][L]) + 4, true, "#1F3A2E");
    for (const i of exits) if (i >= start && i < end) tri(x(i), y(bars[i][H]) - 4, false, "#9A3B2E");
    if (cur.hover >= start && cur.hover < end) { const xx = Math.round(x(cur.hover)) + .5; ctx.strokeStyle = "#4B5A52"; ctx.setLineDash([3, 3]); ctx.beginPath(); ctx.moveTo(xx, padT); ctx.lineTo(xx, padT + ph); ctx.stroke(); ctx.setLineDash([]); }
    $("r-lab").textContent = `${dmy(bars[start][0])} → ${dmy(bars[end - 1][0])} · ${end - start} phiên`;
  }
  function onMove(cx, cy) {
    const Ly = cur.layout; if (!Ly || !cur.calc) return;
    const rect = cv.getBoundingClientRect(), p = cx - rect.left, i = Math.floor((p - Ly.padL) / Ly.bw) + Ly.start;
    if (i < Ly.start || i >= Ly.end) { cur.hover = -1; tip.style.display = "none"; draw(Ly.end - Ly.start); return; }
    cur.hover = i;
    const { bars, st, em, buys, exits } = cur.calc, b = bars[i], s = st[i], e = em[i];
    tip.innerHTML = `<b>${dmy(b[0])}</b><br>M ${px(b[O])} · C ${px(b[H])} · T ${px(b[L])} · Đ <b>${px(b[C])}</b><br>KL ${(b[5] / 1e3).toFixed(0)}k` +
      (s ? `<br><span style="color:${s.up ? "#2E7D4F" : "#B84A3A"}">Supertrend ${s.up ? "xanh" : "đỏ"} ${px(s.line)}</span>` : "") + (e != null ? `<br><span style="color:#5B6FA8">EMA10 ${px(e)}</span>` : "") +
      (buys.includes(i) ? "<br><b>▲ Tín hiệu MUA</b>" : exits.includes(i) ? "<br><b>▼ Supertrend lật đỏ</b>" : "");
    tip.style.display = "block";
    const tw = tip.offsetWidth, left = p + 12 + tw > rect.width ? p - tw - 12 : p + 12;
    tip.style.left = left + "px"; tip.style.top = Math.max(6, Math.min(cy - rect.top - 16, rect.height - tip.offsetHeight - 44)) + "px";
    draw(Ly.end - Ly.start);
  }
  cv.addEventListener("mousemove", (ev) => onMove(ev.clientX, ev.clientY));
  cv.addEventListener("mouseleave", () => { cur.hover = -1; tip.style.display = "none"; if (cur.layout && cur.calc) draw(cur.layout.end - cur.layout.start); });
  cv.addEventListener("touchstart", (ev) => { const t = ev.touches[0]; onMove(t.clientX, t.clientY); }, { passive: true });
  cv.addEventListener("touchmove", (ev) => { const t = ev.touches[0]; onMove(t.clientX, t.clientY); }, { passive: true });
  $("c-sym").addEventListener("change", () => { cur.sym = $("c-sym").value; cur.end = 0; renderChart(); });
  $("c-range").addEventListener("click", (ev) => { const b = ev.target.closest("button"); if (!b) return; cur.n = +b.dataset.n; cur.end = 0; [...$("c-range").children].forEach((x) => x.setAttribute("aria-pressed", x === b ? "true" : "false")); renderChart(); });
  $("r-off").addEventListener("input", (ev) => { if (!cur.calc) return; const total = cur.calc.bars.length, n = cur.n === 0 ? total : Math.min(cur.n, total); cur.end = Math.min(total, +ev.target.value + n); draw(n); });
  window.addEventListener("resize", () => { if (cur.calc && $("p-chart").classList.contains("on")) renderChart(); });
  document.addEventListener("click", (ev) => { const el = ev.target.closest("[data-chart]"); if (!el) return; ev.preventDefault(); openChart(el.dataset.chart); });

  // ---------------------------------------------------------------- tab + boot
  const tabs = document.querySelectorAll('nav[role="tablist"] button');
  function switchTab(name) {
    tabs.forEach((x) => x.setAttribute("aria-selected", x.dataset.tab === name ? "true" : "false"));
    document.querySelectorAll(".panel").forEach((p) => p.classList.toggle("on", p.id === "p-" + name));
    $("main").scrollTop = 0;
    if (name === "chart") renderChart();
  }
  tabs.forEach((b) => b.addEventListener("click", () => switchTab(b.dataset.tab)));
  function applyHash() { const m = /^#(today|history|chart|settings)$/.exec(location.hash); if (m) switchTab(m[1]); }
  window.addEventListener("hashchange", applyHash);

  if ("serviceWorker" in navigator) navigator.serviceWorker.register(SW).catch(() => {});
  load().then(() => { applyHash(); pushStatus(); });
  document.addEventListener("visibilitychange", () => { if (document.visibilityState === "visible") load(); });
})();
