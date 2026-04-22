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

## 6. Cấu trúc thư mục

```text
api_bot_aff/
├─ app/
│  ├─ main.py                 # FastAPI app + health check + include router
│  ├─ config.py               # Đọc biến môi trường
│  ├─ db.py                   # Khởi tạo Supabase client
│  └─ routers/
│     └─ getorder.py          # Endpoint /getorder
├─ requirements.txt
└─ README.md
```

## 7. Ghi chú vận hành

- Không commit file `.env` lên git.
- Nếu API trả lỗi `500`, kiểm tra lại `SUPABASE_URL`, `SUPABASE_KEY` và quyền truy cập bảng `convert_results`.
