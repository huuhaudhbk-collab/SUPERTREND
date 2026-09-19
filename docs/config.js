/* Cấu hình giao diện — sửa sau khi sinh khoá VAPID (venv\Scripts\python -m job.gen_vapid).
   VAPID_PUBLIC phải trùng với Secret VAPID_PUBLIC_KEY trên GitHub.
   WORKER_URL là địa chỉ Cloudflare Worker (tuỳ chọn) — để trống = dùng PUSH_SUBS_FALLBACK. */
window.CW_CONFIG = {
  VAPID_PUBLIC: "BGuPvXsdl_-5GvLihPZt4cnVXQdl0TUIsDmVpvwn2FA7V8B-xmcCzwde6zD-va4cn9fH31Ifa2ln2H6PIbTGKLU",
  WORKER_URL: "",
};
