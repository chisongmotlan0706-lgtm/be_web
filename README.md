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

### `GET /getorder?limit=100`

Lấy danh sách bản ghi mới nhất từ bảng `convert_results`, sắp xếp theo `created_at` giảm dần.

**Query params**

- `limit` (number, optional): số lượng bản ghi cần lấy, mặc định `100`, giới hạn `1..1000`.
- `group` (string, optional): lọc theo cột `group`.
- `date_preset` (`today` | `yesterday` | `custom`, optional): lọc theo `created_at` (UTC).
- `from_date`, `to_date` (date `YYYY-MM-DD`, optional): bắt buộc khi `date_preset=custom`.

**Response mẫu**

```json
{
  "count": 2,
  "items": [
    {
      "id": 1,
      "title": "San pham A",
      "price": 120000,
      "created_at": "2026-04-22T10:00:00+00:00"
    }
  ]
}
```

### `GET /commission-report/orders?limit=200`

Đọc các bản ghi đã lưu trong `public.affiliate_commission_orders`, sắp xếp theo `order_placed_at` giảm dần.

**Query params**

- `limit` (optional): mặc định `200`, tối đa `1000`.
- `placed_within_days` (optional): nếu có, chỉ lấy đơn có `order_placed_at` trong **N ngày gần đây** (UTC); giá trị hợp lệ: `1`, `3`, `7`, `14`. Bỏ qua tham số = không lọc theo thời gian (tất cả trong giới hạn `limit`).

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

Upload file báo cáo hoa hồng Shopee (`.csv`, `.xlsx`, `.xls`), **gộp theo `ID đơn hàng`**, rồi **upsert** vào bảng `public.affiliate_commission_orders`.

### `POST /commission-report/sync-hh-to-zalo`

Gọi RPC `sync_commission_hh_to_zalo` trên Supabase (**một transaction**): các đơn `order_status = 'Hoàn thành'` có `id_zl` khớp `zalo_contacts.id_from` được cộng `SUM(hh_user)` vào `zalo_contacts.available_amount`, sau đó đổi `order_status` thành **`Đã cộng tiền`**. Response gồm `orders_updated`, `orders_skipped_no_contact`, `contacts[]` (mỗi phần tử: `id_from`, `name`, `amount_added`, `order_count`, `available_amount_after`), `total_amount_added`.

Cần chạy migration `003_sync_commission_hh_to_zalo.sql` và có cột `zalo_contacts.available_amount`.

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

**Form-data**

- `file`: file báo cáo.

**Quy tắc gộp + enrich**

- `net_affiliate_commission`: **tổng** cột `Hoa hồng ròng tiếp thị liên kết(₫)` theo từng đơn.
- `order_status`, `sub_id1`: lấy **dòng đầu tiên** của đơn trong file (thứ tự gốc).
- `order_status_transition`: nếu đơn đã tồn tại và `order_status` trong DB **khác** trạng thái từ file thì ghi `"cũ -> mới"`; nếu **không đổi** thì `NULL` (xóa chuỗi cũ).
- Đơn đã có trong DB với `order_status = "Đã cộng tiền"` thì **bỏ qua** (không upsert); response có `skipped_already_paid`.
- `order_placed_at`: **mốc sớm nhất** trong các dòng cùng đơn (sau khi parse datetime).
- Enrich khi import:
  - dùng `sub_id1` tra `convert_results.id_zl` để lấy `zl`,
  - dùng `zl` tra `zalo_contacts` để lấy `id_from`, `name`,
  - lưu `id_from` vào `affiliate_commission_orders.id_zl` và `name` vào `affiliate_commission_orders.name`.

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

## 6. Cấu trúc thư mục

```text
api_bot_aff/
├─ app/
│  ├─ main.py                 # FastAPI app + health check + include router
│  ├─ config.py               # Đọc biến môi trường
│  ├─ db.py                   # Khởi tạo Supabase client
│  ├─ commission_report.py    # Doc file + gop theo order_id
│  └─ routers/
│     ├─ getorder.py          # Endpoint /getorder
│     ├─ commission_import.py # GET /commission-report/orders, POST import + sync-hh-to-zalo
│     └─ commission_config.py # CRUD commission_config
├─ supabase/
│  └─ migrations/
│     ├─ 001_affiliate_commission_orders.sql
│     ├─ 002_order_status_transition.sql
│     └─ 003_sync_commission_hh_to_zalo.sql
├─ requirements.txt
└─ README.md
```

## 7. Ghi chú vận hành

- Không commit file `.env` lên git.
- Nếu API trả lỗi `500`, kiểm tra lại `SUPABASE_URL`, `SUPABASE_KEY` và quyền truy cập bảng `convert_results`.
- Import / đọc bảng `affiliate_commission_orders` cần quyền Supabase phù hợp (ghi + đọc). Thường dùng **service role** trên server nếu bật RLS; không đưa service role lên frontend.
