# Hosting & Data Sync — DinoB Lab

Ghi chú toàn bộ hạ tầng đã dựng + hướng dẫn tái hiện trên máy khác.
App vẫn là static thuần (1 file `vocab-cards.html`), backend là 1 Cloudflare
Worker duy nhất phục vụ cả static assets lẫn REST API.

## Kiến trúc hiện tại

```
Trình duyệt (mỗi origin 1 kho riêng)
├── localStorage        → mọi dữ liệu text (học viên, tiến độ, units, materials)
├── localStorage["dinob_sqlite"] → bản sao SQLite (sql.js WASM, bảng kv)
├── IndexedDB dinob_img → ảnh upload (idb:*), video quay (vid:*)
└── sessionStorage      → dinob_admin, dinob_reloaded, dinob_ghrel

Cloudflare account bfd5fb76a279d2a97845bd480c435570
├── Worker dinob-api → https://dinob.io.vn (route dinob.io.vn/*)
│   ├── ASSETS       → toàn bộ file tĩnh của repo (trừ data/, .git…)
│   ├── D1 dinob-db  → bảng kv(k TEXT PRIMARY KEY, v TEXT) — đồng bộ text
│   ├── R2 dinob-media → media/<key>.bin ảnh/video + backup/dinob-data.sqlite
│   └── secret ADMIN_TOKEN → Bearer token cho mọi request ghi
│   └── workers.dev: https://dinob-api.thanhhaipk.workers.dev
├── Pages dinob-lab → https://dinob-lab.pages.dev (DỰ PHÒNG — code cũ GitHub sync)
└── GitHub repo haipk/learn-english (public) → https://haipk.github.io/learn-english/
    (bản dự phòng thứ 2; data/*.json, data/idb/ là snapshot cũ của era GitHub-sync)
```

## API server (worker/index.js)

| Endpoint | Method | Auth | Tác dụng |
|---|---|---|---|
| `/api/data` | GET | không | trả `{k: v}` toàn bộ bảng kv |
| `/api/data` | PUT | Bearer | upsert object `{k: v}` vào D1 (bỏ qua `dinob_sqlite`, `dinob_apitoken`; batch 100 stmt) |
| `/api/media` | GET | không | list `{files: [{name, size, etag}]}` trong R2 prefix `media/` |
| `/api/media/<name>` | GET/PUT | đọc không / ghi Bearer | 1 object R2 `media/<name>` |
| `/api/backup` | GET/PUT | đọc không / ghi Bearer | object R2 `backup/dinob-data.sqlite` |
| path khác | GET | không | static file qua ASSETS |

CORS `*` → mọi origin (kể cả `file://`, `github.io`) gọi được.
`vocab-cards.html` gọi `const API = "https://dinob.io.vn/api"` (absolute).

## Sync flow trong app (thay thế GitHub sync cũ)

- **Pull** khi load: GET `/api/data` → merge vào localStorage (`ghMerge`:
  remote rỗng không đè local đầy; `vocab_users` merge theo từng học viên/unit).
  Khác → hydrate + reload tối đa 3 lần/phiên.
- **Push**: debounce 3s, tối đa 1 lần/10s; trước PUT vẫn GET remote + merge
  union (máy rỗng không xóa được dữ liệu chung); trùng remote → bỏ qua.
- **Admin token** lưu `localStorage["dinob_apitoken"]` — KHÔNG nằm trong code,
  KHÔNG được export/sync. Ô nhập trên home screen (admin) → 🔗 Lưu token
  → test ghi ngay, thấy `☁ Server ✓` là OK.

## Các nút admin trên home screen

| Nút | Tác dụng | Token |
|---|---|---|
| 🔗 Lưu token | lưu `dinob_apitoken` + đẩy localStorage lên D1 ngay | cần |
| 💾 Xuất / 📥 Nhập .sqlite | backup/restore localStorage qua file local | không |
| ☁⬆ / ☁⬇ .sqlite | ghi/đọc `backup/dinob-data.sqlite` trên R2 | ⬆ cần, ⬇ không |
| ☁⬆ / ☁⬇ Ảnh/video | đồng bộ IndexedDB ↔ `media/<b64url(key)>.bin` (file >90MB bỏ qua) | ⬆ cần, ⬇ không |

## ID / thông số Cloudflare

- Account: `bfd5fb76a279d2a97845bd480c435570`, workers.dev subdomain `thanhhaipk`
- Zone `dinob.io.vn`: `28f95e8d870d5a6f061a097f0cf26b82` (DNS CNAME apex →
  `dinob-lab.pages.dev`, proxied — Worker route đè lên nên thực tế không qua Pages)
- Worker `dinob-api`: routes `dinob.io.vn/*` và `dinob.io.vn/api/*`
- D1 `dinob-db`: `823c6b31-2057-4920-8d7b-7bb7d97083cd`, bảng `kv`
- ADMIN_TOKEN: secret Worker — giá trị đang dùng được set lúc deploy
  (tạo mới bằng `openssl rand -base64 24` rồi PUT lại worker với binding
  `{"type":"secret_text","name":"ADMIN_TOKEN","text":"<mới>"}` — nhớ cho user
  nhập lại trong app)

## Deploy lại code lên Worker (không cần wrangler login)

Flow REST API (đúng như đã làm — khác Pages!):

1. Manifest: mỗi file `/path` → `{hash, size}` với
   `hash = sha256(base64(nội dung file) + extension).hex[:32]`
2. `POST /accounts/{acc}/workers/scripts/dinob-api/assets-upload-session`
   body `{manifest}` → trả `{jwt, buckets[[hash…]]}` — chỉ file MỚI cần upload
3. Upload mỗi bucket: `POST /client/v4/accounts/{acc}/workers/assets/upload?base64=true`
   (Bearer jwt), multipart form: field name = `<hash>`, value = base64 nội dung.
   Bucket cuối trả `jwt` hoàn tất.
4. `PUT /accounts/{acc}/workers/scripts/dinob-api`, multipart:
   - `metadata` (JSON): `{main_module:"index.js", compatibility_date, bindings:[
     {type:"d1",name:"DB",id:"<d1-id>"}, {type:"assets",name:"ASSETS"},
     {type:"secret_text",name:"ADMIN_TOKEN",text:"<token>"}],
     assets:{jwt:"<jwt bước 3>"}}`
   - `index.js`: nội dung `worker/index.js`

Nếu có wrangler + login thì chỉ cần `npx wrangler deploy` (config `wrangler.jsonc`).

## TODO còn lại

- **Bật R2**: Dashboard → Storage & Databases → R2 → Enable (1 lần). Sau đó:
  `wrangler r2 bucket create dinob-media` (hoặc qua API), bỏ comment khối
  `r2_buckets` trong `wrangler.jsonc`, thêm binding `{type:"r2_bucket",
  name:"MEDIA", bucket_name:"dinob-media"}` vào metadata rồi deploy lại.
  Khi đó seed media: với mỗi file `data/idb/<name>` trong repo →
  `PUT /api/media/<name>` (Bearer) — file `.bin` giữ nguyên tên.
- Có thể bỏ route `/api/*` riêng vì `dinob.io.vn/*` đã phủ (route cụ thể hơn
  vẫn ăn trước nên giữ cũng không hại).

## Dựng lại trên máy mới — checklist

1. Mở https://dinob.io.vn/ → đăng nhập → `/api/data` tự kéo về (reload 1 lần)
2. Bấm **☁⬇ Ảnh/video ← server** để kéo media từ R2 (khi R2 đã seed)
3. Admin muốn ghi: nhập ADMIN_TOKEN → 🔗 Lưu token → `☁ Server ✓`
4. Nếu Cloudflare chết, dự phòng: `haipk.github.io/learn-english` hoặc mở
   `vocab-cards.html` local — app chạy độc lập với localStorage/IndexedDB.

## Vấn đề đã gặp & cách sửa (đừng lặp lại)

- **279 commit "Sync app data"**: tab token bị vòng lặp push → vá bằng
  so-sánh-nội-dung + rate limit + max reload. (Đã moot — không còn GitHub sync.)
- **`app-data.json` bị bản rỗng đè**: vá bằng merge union — giữ nguyên trong
  API sync mới.
- **Token GitHub lọt vào sqlite backup**: đã chặn `dinob_apitoken` khỏi
  export + push; token `github_pat_11AL...` trong git history → đã yêu cầu revoke.
- **Pages deploy 404**: sai format upload + manifest thiếu leading `/`.
- **Worker deploy lỗi 10021**: binding `secret_text` bắt buộc field `text`.
- **workers.dev trả error 1042**: phải bật workers.dev subdomain của account
  (đã bật: `thanhhaipk`).
- **R2 chưa enable**: API trả 10042 — phải bật tay trong Dashboard, code đã
  guard trả 503 khi `env.MEDIA` thiếu.
