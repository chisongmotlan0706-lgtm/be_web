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

Upload file báo cáo hoa hồng Shopee (`.csv`, `.xlsx`, `.xls`), **gộp theo `ID đơn hàng`**, rồi **upsert** vào `public.affiliate_commission_orders`. Sau đó **đồng bộ phân tầng** vào `public.affiliate_commission_order_splits` (migration **`006`**, **`008`**, **`027`**): mỗi đơn có dòng **chủ tool** và dòng **đại lý** (nếu có) theo `%` `hoa_hong` trong `app_config_kv`. Tra cứu **chỉ field global**: `sub_id1` = `convert_results.id_zl` → `id_globalgroup` → `zalo_groups.id_global`; đơn: `convert_results.id_globalzalo` → `affiliate_commission_orders.id_global` (user affiliate); split **agency**: `zalo_groups.id_globalzalo` (đại lý); split **platform_owner**: `zalo_groups.id_global_main` (chủ tool). Đơn lưu **`id_global`** (không `id_zl`); splits lưu **`id_global`** người nhận. Đơn **Đã hủy**: cập nhật split, `amount = 0`. Đơn **`Đã cộng tiền`**: bỏ qua (`skipped_already_paid`). Bill Conversion / RPC đồng bộ theo `id_global`.

Đơn đã có trong DB mà **`order_status` từ file trùng `order_status` trong DB** — coi là **không đổi trạng thái** → **bỏ qua upsert và không đồng bộ splits** (không so các field khác như tiền, thời gian đặt, `sub_id1`…; không so `source_filename`). Đơn **mới** hoặc **đổi trạng thái** so với DB → upsert như bình thường. Response có `skipped_unchanged`.

Response thêm: `skipped_already_paid`, `import_batch_id` (uuid mỗi lần import có ít nhất một đơn upsert), `split_sync` (`splits_rows_upserted`, `orders_splits_status_only`, `splits_rows_deleted`), `skipped_unchanged`.

### `POST /commission-report/import-preview`

Nhận cùng file như endpoint import nhưng **không ghi DB**. Trả `would_upsert`, `would_skip_unchanged`, `skipped_already_paid` (số đơn trong file đã là **Đã cộng tiền** trong DB — **không** ghi DB), `preview_counts` (tổng / lỗi split / Đã hủy / đổi trạng thái), và `preview_items` (mọi đơn trong nhóm upsert từ file — **sắp xếp ưu tiên**: lỗi split → Đã hủy → đổi trạng thái → sẽ cập nhật → không đổi). Trường `is_unchanged`: **chỉ** khi `order_status` file trùng DB.

Mỗi phần tử `preview_items` gồm (tối thiểu): `order_id`, `order_status`, `net_affiliate_commission`, **`id_global`**, `name`, `hh_user`, **`id_globalgroup`**, **`group_id_global`**, **`agency_id_global`**, `agency_name`, `agency_amount`, **`owner_id_global_main`**, `owner_amount`, `split_issue` (`thieu_convert_results`, `thieu_id_globalzalo`, `thieu_id_globalgroup`, `thieu_id_global_main`, `thieu_id_globalzalo_nhom`), `order_status_transition`, `is_unchanged`. `lookup.missing_convert_results` = số `sub_id1` không có `convert_results.id_zl`.

### `POST /commission-report/sync-hh-to-zalo`

Gọi RPC `sync_commission_hh_to_zalo()` **không tham số** (mặc định `p_restrict_order_ids = NULL`): đồng bộ **tất cả** đơn `order_status = 'Hoàn thành'` đủ điều kiện (giữ hành vi cũ / nâng cao).

### `POST /commission-report/sync-hh-to-zalo-bill-preview`

Upload **Bill Conversion** Shopee (`.csv` / `.xlsx` / `.xls`). Parser: cột `ID đơn hàng`, `Trạng thái đặt hàng`; chỉ lấy các dòng **`Trạng thái đặt hàng = Hoàn thành`**, `order_id` unique. **Không ghi DB**. Trả `preview_items` (đối chiếu DB: có đơn, trạng thái, `id_global`, có `zalo_contacts`, `eligible`, `skip_reason`, `hh_user`, `splits_total`) và các số đếm.

### `POST /commission-report/sync-hh-to-zalo-bill-apply`

Cùng định dạng file; parse lại `order_id` rồi gọi RPC `sync_commission_hh_to_zalo(p_restrict_order_ids => …)` — chỉ đơn nằm trong danh sách **và** đủ điều kiện như RPC (DB `Hoàn thành`, có `id_global`, có contact theo `zalo_contacts.id_global`). Trả payload RPC + `source_filename`, `restrict_order_count`, `preview_eligible_count`.

Chi tiết RPC (cộng `hh_user` + splits, ghi log, chỉ `UPDATE` trạng thái đơn thuộc tập **eligible** — xem migration **`029_sync_commission_hh_to_zalo_global.sql`**):

- **`SUM(hh_user)`** trên các đơn eligible (affiliate theo `id_global`);
- **cộng thêm** **`SUM(amount)`** từ `affiliate_commission_order_splits` gắn các đơn đó, **theo từng `id_global` người nhận split**, chỉ khi `id_global` đó tồn tại trong `zalo_contacts`.

Sau đó đổi `order_status` thành **`Đã cộng tiền`** (chỉ các đơn trong tập eligible), ghi `public.commission_payout_sync_log`. Response: `sync_batch_id`, `orders_updated`, `orders_skipped_no_contact`, `contacts[]`, `total_amount_added`.

Cần migration **`003`**, **`004`**, **`005`**, **`006`**, **`007`**, **`018`**.

### `GET /commission-report/payout-sync-logs?limit=500&placed_within_days=7`

Đọc `public.commission_payout_sync_log`, sắp xếp `created_at` giảm dần.

**Query params**

- `limit` (optional): mặc định `500`, tối đa `2000`.
- `placed_within_days` (optional): `1`, `3`, `7`, `14` — lọc `created_at` từ 00:00 VN của `(hôm nay − N)` đến hiện tại; bỏ qua = tất cả.

### `GET /commission-report/order-splits?limit=500&placed_within_days=7`

Đọc `public.affiliate_commission_order_splits`, sắp xếp `created_at` giảm dần. Mỗi dòng được bổ sung **`d_name`** từ `zalo_contacts` theo **`id_global`** trên split (nếu không có contact thì `d_name` null).

**Query params**

- `limit` (optional): mặc định `500`, tối đa `2000`.
- `order_id` (optional): lọc đúng một đơn (`order_id` trong bảng splits).
- `placed_within_days` (optional): `1`, `3`, `7`, `14` — lọc `created_at` từ 00:00 VN của `(hôm nay − N)` đến hiện tại; bỏ qua = tất cả.

### `GET /zalo-groups?limit=500`

Đọc `public.zalo_groups` (chỉ bản ghi **`deleted_at` null**), lọc theo **`id_global_main`** của user đăng nhập (`auth_users.id_globalzalo`, fallback `id_zl`), sắp xếp `updated_at` giảm dần.

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

### `GET /bot-group?limit=200`

Đọc `public.bot_group`, sắp xếp `priority` tăng dần rồi `id` (gồm `max_rep`, `current_rep` nếu đã migration **`022`**).

### `POST /bot-group`

Tạo dòng: JSON `name_bot` (nullable), `type_bot` (`REP` | `GHI`), `priority` (1–100), `max_rep` (optional, bigint hoặc null). **`id_bot` do server sinh** — chuỗi số ngẫu nhiên đúng **16 ký tự**; `current_rep` = `null` khi tạo.

### `PUT /bot-group/{id}`

Cập nhật `name_bot`, `type_bot`, `priority`, `max_rep` — **không** cập nhật `id_bot` hay `current_rep`.

### `DELETE /bot-group/{id}`

Xóa cứng theo `id`. Migration: **`021_bot_group.sql`** + **`022_bot_group_max_rep_current_rep.sql`** (cột `max_rep`, `current_rep`).

**Form-data**

- `file`: file báo cáo.

**Quy tắc gộp + enrich**

- `net_affiliate_commission`: **tổng** cột `Hoa hồng ròng tiếp thị liên kết(₫)` theo từng đơn.
- `order_status`, `sub_id1`: lấy **dòng đầu tiên** của đơn trong file (thứ tự gốc).
- `order_status_transition`: nếu đơn đã tồn tại và `order_status` trong DB **khác** trạng thái từ file thì ghi `"cũ -> mới"`; nếu **không đổi** thì `NULL` (xóa chuỗi cũ).
- Đơn đã có trong DB với `order_status = "Đã cộng tiền"`: **không ghi DB** (không upsert, không update). Response đếm trong `skipped_already_paid`.
- `order_placed_at`: **mốc sớm nhất** trong các dòng cùng đơn. Cột thời gian trong file Shopee là **M/D/YYYY** (tháng trước, ngày sau), giờ 24h, coi là **giờ wall Việt Nam** (`Asia/Ho_Chi_Minh`); parse ưu tiên `dayfirst=False`, dòng không parse được thì thử `dayfirst=True`; sau đó chuyển **UTC** rồi lưu `timestamptz`.
- Enrich khi import (**chỉ field global**; Bill Conversion / RPC chưa đổi):
  - `sub_id1` trên file = **`convert_results.id_zl`**; từ dòng convert lấy **`id_globalzalo`**, **`id_globalgroup`** (backfill: `fe_bot_aff/scripts/fill-convert-results-global-ids.js`).
  - User đơn: **`convert_results.id_globalzalo`** → `zalo_contacts` → `affiliate_commission_orders.id_global`, `name`, `hh_user`.
  - Split **agency** `id_global` = **`zalo_groups.id_globalzalo`** (theo `id_globalgroup`); split **owner** `id_global` = **`id_global_main`**.
  - Upsert ghi **`id_zl = null`** trên đơn/splits; **`group_id`** split = `id_global` nhóm; migration **`027`**.
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
    "missing_zalo_contacts": 6,
    "matched_commission_config": 109,
    "missing_commission_config": 0,
    "hoa_hong": { "ok": true, "value_1": 15, "value_2": 25, "value_3": 60, "value_4": 0 }
  }
}
```

**`import-preview` — ví dụ một phần tử `preview_items`**

```json
{
  "order_id": "260422FDNE5GDN",
  "order_status": "Hoàn thành",
  "id_global": "global_zalo_id",
  "id_globalgroup": "global_group_id",
  "group_id_global": "global_group_id",
  "agency_id_global": "agency_global",
  "owner_id_global_main": "owner_global",
  "split_issue": null
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
- `supabase/migrations/029_sync_commission_hh_to_zalo_global.sql` (RPC Bill/Sync HH dùng `id_global`, vẫn hỗ trợ `p_restrict_order_ids`)
- `supabase/migrations/026_commission_global_columns.sql`, `028_zalo_groups_id_globalzalo.sql` (cột global: `auth_users.id_globalzalo`, `convert_results.id_globalzalo` / `id_globalgroup`, `affiliate_commission_orders.id_global`, `affiliate_commission_order_splits.id_global`, `zalo_groups.id_global` / `id_global_main` / `id_globalzalo`, `zalo_contacts.id_global` / `id_global_gr` — `IF NOT EXISTS`)
- `supabase/migrations/027_import_global_only_splits.sql` (import: `splits.id_zl` nullable; splits chỉ bắt buộc `id_global` trong logic app)
- `supabase/migrations/030_withdraw_requests_global_only.sql` (withdraw_requests: chuẩn hóa `id_global`, unique pending theo `id_global`, index cột global)
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
│     ├─ 017_app_config_kv_labels.sql
│     ├─ 026_commission_global_columns.sql
│     └─ 027_import_global_only_splits.sql
├─ requirements.txt
└─ README.md
```

## 7. Ghi chú vận hành

- Không commit file `.env` lên git.
- Nếu API trả lỗi `500`, kiểm tra lại `SUPABASE_URL`, `SUPABASE_KEY` và quyền truy cập bảng `convert_results`.
- Import / đọc bảng `affiliate_commission_orders` và ghi `affiliate_commission_order_splits` cần quyền Supabase phù hợp (ghi + đọc). Thường dùng **service role** trên server nếu bật RLS; không đưa service role lên frontend.
- Cột global (`026_commission_global_columns.sql`): sau khi chạy migration, có thể backfill `convert_results.id_globalzalo` / `id_globalgroup` bằng script trong repo FE (`fe_bot_aff/scripts/fill-convert-results-global-ids.js`, xem `README-fill-convert-global.md`).
- JWT access token có thể chứa claim **`id_globalzalo`** (khi user có giá trị); `GET/PATCH /auth/me` trả **`id_globalzalo`** cho client.
