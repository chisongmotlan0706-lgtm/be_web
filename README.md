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

**Quy tắc gộp**

- `net_affiliate_commission`: **tổng** cột `Hoa hồng ròng tiếp thị liên kết(₫)` theo từng đơn.
- `order_status`, `sub_id1`: lấy **dòng đầu tiên** của đơn trong file (thứ tự gốc).
- `order_placed_at`: **mốc sớm nhất** trong các dòng cùng đơn (sau khi parse datetime).

**Response mẫu**

```json
{
  "upserted": 120,
  "unique_orders": 120,
  "source_filename": "AffiliateCommissionReport202604231103.csv"
}
```

**Database**

Chạy migration SQL một lần trong Supabase SQL Editor:

- `supabase/migrations/001_affiliate_commission_orders.sql`

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
│     ├─ commission_import.py # GET /commission-report/orders, POST /commission-report/import
│     └─ commission_config.py # CRUD commission_config
├─ supabase/
│  └─ migrations/
│     └─ 001_affiliate_commission_orders.sql
├─ requirements.txt
└─ README.md
```

## 7. Ghi chú vận hành

- Không commit file `.env` lên git.
- Nếu API trả lỗi `500`, kiểm tra lại `SUPABASE_URL`, `SUPABASE_KEY` và quyền truy cập bảng `convert_results`.
- Import / đọc bảng `affiliate_commission_orders` cần quyền Supabase phù hợp (ghi + đọc). Thường dùng **service role** trên server nếu bật RLS; không đưa service role lên frontend.
