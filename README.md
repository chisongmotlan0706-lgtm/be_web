# API Bot Affiliate

Backend API sử dụng FastAPI để đọc dữ liệu đơn hàng affiliate từ Supabase (`public.convert_results`).

## 1. Yêu cầu hệ thống

- Python 3.10+ (khuyến nghị 3.11)
- `pip` hoặc `pip3`

## 2. Cài đặt

```bash
pip install -r requirements.txt
```

## 3. Biến môi trường

Tạo file `.env` tại thư mục gốc project:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_key
```

## 4. Chạy local

```bash
uvicorn app.main:app --reload
```

API mặc định chạy tại: `http://127.0.0.1:8000`

## 5. API endpoints

### `GET /`

Health check endpoint.

**Response mẫu**

```json
{ "status": "ok" }
```

### `GET /commission-report/orders?limit=200`

Đọc các bản ghi đã lưu trong `public.affiliate_commission_orders`, sắp xếp theo `order_placed_at` giảm dần.

**Query params**

- `limit` (optional): mặc định `200`, tối đa `1000`.
- `placed_within_days` (optional): nếu có, chỉ lấy đơn có `order_placed_at` từ **00:00 (lịch Việt Nam) của ngày `(hôm nay − N)`** đến **thời điểm hiện tại** (UTC so sánh với DB); giá trị: `1`, `3`, `7`, `14`. Ví dụ `1` = từ 0h hôm qua (VN) đến bây giờ. Bỏ qua = không lọc theo thời gian.

**Response mẫu**

```json
{
  "count": 2,
  "items": [
    {
      "id": "uuid",
      "order_id": "260422FDNE5GDN",
      "order_status": "Dang cho xu ly",
      "order_placed_at": "2026-04-22T11:07:00+00:00",
      "net_affiliate_commission": 37044.4,
      "sub_id1": "123",
      "source_filename": "report.csv"
    }
  ]
}
```

### `POST /commission-report/import`

Upload file báo cáo hoa hồng Shopee (`.csv`, `.xlsx`, `.xls`), **gộp theo `ID đơn hàng`**, rồi **upsert** vào bảng `public.affiliate_commission_orders`. Sau đó **đồng bộ phân tầng** vào `public.affiliate_commission_order_splits` (migration **`006`**, **`008`** tắt RLS nếu cần): mỗi đơn có dòng **chủ tool** (`id_zl_main` từ `zalo_groups` theo `group_id`) **25%** `net_affiliate_commission` và dòng **đại lý** **15%** khi tra được `sub_id1` → `convert_results.group` → `zalo_groups.group_id` → `id_zl` đại lý. Đơn **Đã hủy** (trạng thái chứa “hủy”): cập nhật `order_status` trên split và đặt `amount = 0`, `net_affiliate_commission_at_split = 0`. Đơn trong DB đã **`order_status = "Đã cộng tiền"`**: **không làm gì** (không update `order_placed_at` / `source_filename`, không upsert) — đếm trong `skipped_already_paid`.

Đơn đã có trong DB mà **`order_status` từ file trùng `order_status` trong DB** — coi là **không đổi trạng thái** → **bỏ qua upsert và không đồng bộ splits** (không so các field khác như tiền, thời gian đặt, `sub_id1`…; không so `source_filename`). Đơn **mới** hoặc **đổi trạng thái** so với DB → upsert như bình thường. Response có `skipped_unchanged`.

Response thêm: `skipped_already_paid`, `import_batch_id` (uuid mỗi lần import có ít nhất một đơn upsert), `split_sync` (`splits_rows_upserted`, `orders_splits_status_only`, `splits_rows_deleted`), `skipped_unchanged`.

### `POST /commission-report/import-preview`

Nhận cùng file như endpoint import nhưng **không ghi DB**. Trả `would_upsert`, `would_skip_unchanged`, `skipped_already_paid` (số đơn trong file đã là **Đã cộng tiền** trong DB — **không** ghi DB), `preview_counts` (tổng / lỗi split / Đã hủy / đổi trạng thái), và `preview_items` (mọi đơn trong nhóm upsert từ file — **sắp xếp ưu tiên**: lỗi split → Đã hủy → đổi trạng thái → sẽ cập nhật → không đổi). Trường `is_unchanged`: **chỉ** khi `order_status` file trùng DB.

### `POST /commission-report/sync-hh-to-zalo`

Gọi RPC `sync_commission_hh_to_zalo` trên Supabase (**một transaction**): các đơn `order_status = 'Hoàn thành'` có `id_zl` affiliate khớp `zalo_contacts.id_from` được cộng vào `zalo_contacts.available_amount` theo từng `id_from`:

- **`SUM(hh_user)`** trên các đơn đó (affiliate);
- **cộng thêm** **`SUM(amount)`** từ `affiliate_commission_order_splits` gắn các đơn đó, **theo từng `id_zl` người nhận split**, chỉ khi `id_zl` đó cũng tồn tại trong `zalo_contacts` (nếu thiếu contact, phần split đó **không** được cộng nhưng đơn vẫn chuyển **Đã cộng tiền** nếu affiliate hợp lệ).

Sau đó đổi `order_status` thành **`Đã cộng tiền`**, ghi `public.commission_payout_sync_log` (mỗi contact một dòng trong batch). Response: `sync_batch_id`, `orders_updated`, `orders_skipped_no_contact`, `contacts[]`, `total_amount_added`.

Cần migration **`003`**, **`004`** (log + RPC), **`005`** (RLS log nếu cần), **`006`** (bảng splits), **`007_sync_commission_hh_to_zalo_splits.sql`** (RPC gộp splits). Cột `zalo_contacts.available_amount`.

### `GET /commission-report/payout-sync-logs?limit=500&placed_within_days=7`

Đọc `public.commission_payout_sync_log`, sắp xếp `created_at` giảm dần.

**Query params**

- `limit` (optional): mặc định `500`, tối đa `2000`.
- `placed_within_days` (optional): `1`, `3`, `7`, `14` — lọc `created_at` từ 00:00 VN của `(hôm nay − N)` đến hiện tại; bỏ qua = tất cả.

### `GET /commission-report/order-splits?limit=500&placed_within_days=7`

Đọc `public.affiliate_commission_order_splits`, sắp xếp `created_at` giảm dần. Mỗi dòng được bổ sung **`d_name`** từ `zalo_contacts.d_name` theo `id_zl` = `id_from` (nếu không có contact thì `d_name` null).

**Query params**

- `limit` (optional): mặc định `500`, tối đa `2000`.
- `order_id` (optional): lọc đúng một đơn (`order_id` trong bảng splits).
- `placed_within_days` (optional): `1`, `3`, `7`, `14` — lọc `created_at` từ 00:00 VN của `(hôm nay − N)` đến hiện tại; bỏ qua = tất cả.

### `GET /zalo-groups?limit=500`

Đọc `public.zalo_groups` (chỉ bản ghi **`deleted_at` null**), sắp xếp `updated_at` giảm dần.

**Query params**

- `limit` (optional): mặc định `500`, tối đa `2000`.

### `PATCH /zalo-groups/{id}`

Cập nhật **`group_name`** và **`status`** (`ACTIVE` \| `INACTIVE` \| `PENDING`) theo khóa **`id`** (bigint). Chỉ áp dụng khi nhóm chưa xóa mềm.

### `DELETE /zalo-groups/{id}`

**Xóa cứng**: xóa bản ghi khỏi `public.zalo_groups` theo **`id`**. Trả `404` nếu không có dòng tương ứng.

### `GET /commission-config?limit=200`

Lấy danh sách cấu hình từ bảng `public.commission_config`.

**Query params**

- `limit` (optional): mặc định `200`, tối đa `1000`.
- `scope` (`global` | `group` | `id_from` | `group_id_from`, optional): lọc theo scope.
- `is_active` (boolean, optional): lọc theo trạng thái.

### `POST /commission-config`

Tạo mới một rule commission config.

### `PUT /commission-config/{config_id}`

Cập nhật toàn bộ trường rule theo `config_id`.

### `PATCH /commission-config/{config_id}/active`

Bật/tắt nhanh trạng thái `is_active`.

### `GET /commission-split-config`

Đọc singleton `%` phân tầng (`commission_split_config`).

### `PUT /commission-split-config`

Cập nhật `agency_pct`, `owner_pct`.

### `GET /app-config-kv?limit=200&category=&search=`

Đọc `public.app_config_kv` (key + `value_1`…`value_5`). Lọc `category` (đúng chuỗi), `search` (ilike trên `config_key`).

### `POST /app-config-kv`

Tạo dòng cấu hình KV (body JSON).

### `PUT /app-config-kv/{id}`

Cập nhật theo `id`.

### `DELETE /app-config-kv/{id}`

Xóa cứng theo `id`.

**Form-data**

- `file`: file báo cáo.

**Quy tắc gộp + enrich**

- `net_affiliate_commission`: **tổng** cột `Hoa hồng ròng tiếp thị liên kết(₫)` theo từng đơn.
- `order_status`, `sub_id1`: lấy **dòng đầu tiên** của đơn trong file (thứ tự gốc).
- `order_status_transition`: nếu đơn đã tồn tại và `order_status` trong DB **khác** trạng thái từ file thì ghi `"cũ -> mới"`; nếu **không đổi** thì `NULL` (xóa chuỗi cũ).
- Đơn đã có trong DB với `order_status = "Đã cộng tiền"`: **không ghi DB** (không upsert, không update). Response đếm trong `skipped_already_paid`.
- `order_placed_at`: **mốc sớm nhất** trong các dòng cùng đơn. Cột thời gian trong file Shopee là **M/D/YYYY** (tháng trước, ngày sau), giờ 24h, coi là **giờ wall Việt Nam** (`Asia/Ho_Chi_Minh`); parse ưu tiên `dayfirst=False`, dòng không parse được thì thử `dayfirst=True`; sau đó chuyển **UTC** rồi lưu `timestamptz`.
- Enrich khi import:
  - dùng `sub_id1` tra `convert_results.id_zl` để lấy `zl`,
  - dùng `zl` tra `zalo_contacts` để lấy `id_from`, `name`,
  - lưu `id_from` vào `affiliate_commission_orders.id_zl` và `name` vào `affiliate_commission_orders.name`.
  - `hh_user` và số tiền split agency/owner: đọc một dòng `app_config_kv` với `config_key = hoa_hong`, `is_active = true`; `value_1`…`value_4` là phần trăm 0–100 (parse từ text). Công thức trên `net_affiliate_commission` (làm tròn 4 chữ số): `net * (100 - value_4) * value_k / 10000` với `value_3` → user (`hh_user`), `value_1` → agency, `value_2` → owner. Không có dòng active → `hh_user` và split amounts = 0; `lookup.matched_commission_config` / `missing_commission_config` đếm theo từng dòng có `zalo_contacts`.

**Response mẫu**

```json
{
  "upserted": 120,
  "unique_orders": 120,
  "source_filename": "AffiliateCommissionReport202604231103.csv",
  "lookup": {
    "sub_id1_count": 120,
    "matched_convert_results": 115,
    "missing_convert_results": 5,
    "matched_zalo_contacts": 109,
    "missing_zalo_contacts": 6
  }
}
```

**Database**

Chạy migration SQL một lần trong Supabase SQL Editor:

- `supabase/migrations/001_affiliate_commission_orders.sql`
- `supabase/migrations/002_order_status_transition.sql` (cột `order_status_transition`)
- `supabase/migrations/003_sync_commission_hh_to_zalo.sql` (RPC đồng bộ HH → `zalo_contacts`)
- `supabase/migrations/004_commission_payout_sync_log.sql` (bảng log + RPC ghi log + `sync_batch_id`)
- `supabase/migrations/005_commission_payout_sync_log_rls_fix.sql` (nếu lỗi RLS khi gọi RPC — `SECURITY DEFINER` + tắt RLS bảng log)
- `supabase/migrations/006_affiliate_commission_order_splits.sql` (bảng `affiliate_commission_order_splits` — phân tầng sau import)
- `supabase/migrations/007_sync_commission_hh_to_zalo_splits.sql` (RPC đồng bộ: `hh_user` + splits)
- `supabase/migrations/008_affiliate_commission_order_splits_rls_fix.sql` (tắt RLS bảng splits nếu Supabase chặn insert/select)
- `supabase/migrations/009_zalo_groups_status.sql` (cột `status` cho nhóm — nếu chưa có)
- `supabase/migrations/010_zalo_groups_rls_disable.sql` (tắt RLS `zalo_groups` nếu cần)

## 6. Cấu trúc thư mục

```text
api_bot_aff/
├─ app/
│  ├─ main.py                 # FastAPI app + health check + include router
│  ├─ config.py               # Đọc biến môi trường
│  ├─ db.py                   # Khởi tạo Supabase client
│  ├─ commission_report.py    # Doc file + gop theo order_id
│  └─ routers/
│     ├─ commission_import.py # GET orders + payout-sync-logs, POST import + sync-hh-to-zalo
│     ├─ commission_config.py # CRUD commission_config
│     ├─ commission_split_config.py # GET/PUT commission_split_config
│     ├─ app_config_kv.py     # CRUD app_config_kv (key + value_1..5 + label_1..5)
│     └─ zalo_groups.py       # GET /zalo-groups, PATCH /zalo-groups/{id}, DELETE (xóa cứng)
├─ supabase/
│  └─ migrations/
│     ├─ 001_affiliate_commission_orders.sql
│     ├─ 002_order_status_transition.sql
│     ├─ 003_sync_commission_hh_to_zalo.sql
│     ├─ 004_commission_payout_sync_log.sql
│     ├─ 005_commission_payout_sync_log_rls_fix.sql
│     ├─ 006_affiliate_commission_order_splits.sql
│     ├─ 007_sync_commission_hh_to_zalo_splits.sql
│     ├─ 008_affiliate_commission_order_splits_rls_fix.sql
│     ├─ 009_zalo_groups_status.sql
│     ├─ 010_zalo_groups_rls_disable.sql
│     ├─ 014_zalo_contacts_id_group_groups_id_zl_main.sql
│     ├─ 015_commission_split_config.sql
│     ├─ 016_app_config_kv.sql
│     └─ 017_app_config_kv_labels.sql
├─ requirements.txt
└─ README.md
```

## 7. Ghi chú vận hành

- Không commit file `.env` lên git.
- Nếu API trả lỗi `500`, kiểm tra lại `SUPABASE_URL`, `SUPABASE_KEY` và quyền truy cập bảng `convert_results`.
- Import / đọc bảng `affiliate_commission_orders` và ghi `affiliate_commission_order_splits` cần quyền Supabase phù hợp (ghi + đọc). Thường dùng **service role** trên server nếu bật RLS; không đưa service role lên frontend.
