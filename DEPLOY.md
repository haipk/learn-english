# Hosting & Data Sync — DinoB Lab

Ghi chú toàn bộ hạ tầng đã dựng + hướng dẫn tái hiện trên máy khác.
App vẫn là static thuần — KHÔNG có backend, KHÔNG cần build.

## Kiến trúc hiện tại

```
Trình duyệt (mỗi origin 1 kho riêng)
├── localStorage        → mọi dữ liệu text (học viên, tiến độ, units, materials)
├── localStorage["dinob_sqlite"] → bản sao SQLite (sql.js WASM, bảng kv)
├── IndexedDB dinob_img → ảnh upload (idb:*), video quay (vid:*)
└── sessionStorage      → dinob_admin, dinob_reloaded

GitHub repo  haipk/learn-english (public, branch main)
├── data/app-data.json       ← sync TỰ ĐỘNG toàn bộ localStorage
├── data/dinob-data.sqlite   ← backup SQLite thủ công (nút ☁⬆/☁⬇ .sqlite)
└── data/idb/<base64url(key)>.bin  ← ảnh/video IndexedDB (nút ☁⬆/☁⬇ Ảnh/video)

Hosting (2 bản chạy song song, đọc/ghi cùng repo)
├── https://haipk.github.io/learn-english/   (GitHub Pages, dự phòng)
└── https://dinob.io.vn/                     (Cloudflare Pages, chính)
    └── project: dinob-lab → https://dinob-lab.pages.dev
```

## GitHub sync (trong vocab-cards.html)

- **Pull** khi load app: đọc `data/app-data.json` (repo public → không cần
  token) rồi MERGE vào localStorage (remote rỗng không đè local đầy;
  `vocab_users` merge theo từng học viên/unit). Nếu dữ liệu khác → hydrate +
  reload tối đa 3 lần/phiên (`dinob_reloaded`).
- **Push**: debounce 3s sau mỗi lần ghi; trước khi PUT merge với remote
  (union — máy rỗng không xóa được dữ liệu chung), bỏ qua nếu nội dung giống
  hệt, giới hạn 1 push/phút + flush khi đóng tab. Retry 1 lần khi sha đổi.
- **Token** lưu ở `localStorage["dinob_ghtoken"]` từng trình duyệt admin —
  KHÔNG nằm trong code, KHÔNG được export vào sqlite (đã chặn trong code).

## GitHub token (bắt buộc cho ghi)

Tạo tại https://github.com/settings/personal-access-tokens (fine-grained):

1. Repository access → **Only select repositories** → `haipk/learn-english`
   (KHÔNG chọn "Public repositories (read-only)" — sẽ không có quyền ghi)
2. Permissions → **Repository permissions** → **Contents → Read and write**
3. Generate → dán vào ô "GitHub token (PAT)" trên home screen (admin) →
   🔗 Lưu token. Thấy `☁ GitHub ✓` là OK.

⚠️ Token cũ `github_pat_11AL...` đã LỘ trong git history (commit `aff3d74`,
nằm trong file sqlite backup) → phải REVOKE, tạo token mới.

## Các nút admin trên home screen

| Nút | Tác dụng | Token |
|---|---|---|
| 🔗 Lưu token | lưu PAT + đẩy localStorage lên `data/app-data.json` ngay | cần |
| 💾 Xuất / 📥 Nhập .sqlite | backup/restore localStorage qua file | không |
| ☁⬆ / ☁⬇ .sqlite | đẩy/kéo `data/dinob-data.sqlite` | ⬆ cần, ⬇ không |
| ☁⬆ / ☁⬇ Ảnh/video | đồng bộ IndexedDB ↔ `data/idb/*.bin` (file >45MB bỏ qua) | ⬆ cần, ⬇ không |

## Cloudflare Pages (direct upload, đã deploy thủ công)

Account `bfd5fb76a279d2a97845bd480c435570`, zone `dinob.io.vn`
(`28f95e8d870d5a6f061a097f0cf26b82`), project `dinob-lab`.

Flow deploy tay (đã làm, làm lại khi cần update code):

1. `GET /accounts/{acc}/pages/projects/dinob-lab/upload-token` → JWT (~30 phút)
2. Upload file: `POST /client/v4/pages/assets/upload` (Bearer JWT), body là
   **MẢNG** `[{key: <sha256-32>, value: <base64>, base64: true,
   metadata: {contentType}}]` — KHÔNG phải object {hash: b64}.
3. `POST /pages/assets/upsert-hashes` `{hashes: [...]}` để đăng ký hash.
4. `POST /accounts/{acc}/pages/projects/dinob-lab/deployments`
   (multipart/form-data), field `manifest` = JSON `{"<b>/</b>index.html":
   "<hash>", ...}` — key BẮT BUỘC có leading `/` (thiếu → site 404 toàn tập).

DNS: CNAME apex `dinob.io.vn` → `dinob-lab.pages.dev` (2 A record GitHub
Pages cũ đã xóa). Domain status: active, SSL Google CA.

→ Đơn giản hơn nếu có API token: `npx wrangler pages deploy . --project-name=dinob-lab`

## Dựng lại trên máy mới — checklist

1. `git clone https://github.com/haipk/learn-english.git` (hoặc chỉ cần mở web)
2. Mở https://dinob.io.vn/ → đăng nhập → `app-data.json` tự kéo về (reload 1 lần)
3. Bấm **☁⬇ Ảnh/video ← GitHub** để kéo ảnh/video IndexedDB về (~243MB)
4. (Tuỳ chọn) ☁⬇ .sqlite ← GitHub nếu muốn bản sqlite thay vì JSON
5. Admin muốn ghi/đồng bộ: tạo token mới như mục trên → 🔗 Lưu token

## Vấn đề đã gặp & cách sửa (đừng lặp lại)

- **279 commit "Sync app data" trong 1 giờ**: tab có token bị vòng lặp
  pull→hydrate→reload→push. Đã vá: so sánh nội dung trước PUT + max 1
  push/phút + max 3 reload/phiên.
- **`app-data.json` cứ bị bản rỗng đè**: máy thin-data ghi đè. Đã vá: push
  merge union với remote.
- **Token lọt vào sqlite backup**: đã chặn `dinob_ghtoken` khỏi export/sync;
  file backup trên repo đã scrub (nhưng history vẫn chứa → revoke token).
- **Pages deploy 404**: sai format upload + manifest thiếu leading `/`.

## Giới hạn còn lại

- localStorage tách theo origin: `file://`, `github.io`, `dinob.io.vn` là 3
  kho khác nhau — dữ liệu không tự nhảy giữa các origin, phải sync qua GitHub.
- Repo đang ~243MB (video trong git history). Quá ~1GB cân nhắc Git LFS
  hoặc chỉ sync ảnh bỏ video.
- Ảnh/video chỉ đi khi admin bấm ☁⬆ — không tự động như JSON sync.
