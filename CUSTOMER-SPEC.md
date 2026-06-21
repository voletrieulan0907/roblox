# Đặc tả nghiệp vụ hệ thống RBX Tool

## 1. Mục tiêu hệ thống
Hệ thống RBX Tool được xây dựng để tự động xử lý vòng đời phiên đăng nhập Roblox (session), bao gồm tiếp nhận cookie đầu vào, làm mới cookie, lưu trữ trạng thái tài khoản, và cung cấp kênh giám sát/vận hành qua Discord.

Mục tiêu chính:
- Duy trì tính liên tục của các session hợp lệ.
- Tự động cập nhật cookie mới khi cần.
- Giảm thao tác thủ công nhờ cơ chế cron và bot lệnh.
- Cung cấp khả năng theo dõi tập trung qua webhook/Discord.

## 2. Phạm vi chức năng
### 2.1 Chức năng phía người dùng (Frontend)
- Landing page giới thiệu công cụ.
- Nút tải file extension (`extension.zip`) từ backend.
- Trang làm mới cookie thủ công (`/refresh`) cho phép:
  - Nhập cookie cũ.
  - Gọi API làm mới cookie.
  - Hiển thị cookie mới và sao chép nhanh.

### 2.2 Chức năng phía hệ thống (Backend API)
- Xác thực request bằng `x-api-key` với hầu hết endpoint.
- API làm mới cookie Roblox.
- API quản lý session (tạo/cập nhật/xóa/xem danh sách).
- Phục vụ file tĩnh cho extension.

### 2.3 Chức năng vận hành (Discord)
- Gửi thông báo "hit mới" và "hit cập nhật" qua webhook.
- Cung cấp bộ slash commands để vận hành nhanh:
  - Kiểm tra trạng thái bot.
  - Chạy refresh thủ công.
  - Liệt kê session theo trạng thái.
  - Lấy cookie theo userId.
  - Cập nhật/xóa session.

## 3. Quy trình nghiệp vụ chính
## 3.1 Luồng tạo/cập nhật session từ cookie
1. Hệ thống nhận cookie Roblox từ client.
2. Backend kiểm tra cookie có hợp lệ bằng API xác thực người dùng Roblox.
3. Nếu hợp lệ, backend thực hiện quy trình đổi cookie (rotate):
   - Lấy `x-csrf-token`.
   - Lấy `rbx-authentication-ticket`.
   - Redeem ticket để nhận cookie mới.
4. Ghi dữ liệu vào database theo cơ chế `upsert` theo `userId` (không tạo trùng).
5. Gửi hoặc cập nhật bản tin webhook Discord tương ứng với bản ghi session.

Kết quả:
- Thành công: session được đặt trạng thái `ALIVE`, cookie mới được lưu.
- Thất bại: API trả lỗi; trong các luồng batch có thể chuyển trạng thái sang `DIE`.

## 3.2 Luồng bảo trì định kỳ
- Mỗi 30 phút (production), scheduler quét các session có:
  - `status = ALIVE`
  - `updatedAt` cũ hơn 5 giờ.
- Hệ thống làm mới tuần tự từng session.
- Nếu refresh thất bại, session được đánh dấu `DIE`.
- Có chống chạy chồng tác vụ để tránh refresh trùng thời điểm.

## 4. Mô hình dữ liệu
### 4.1 Bảng Session
- `userId` (duy nhất).
- `cookie`.
- `userAgent`.
- `status`: `ALIVE | PAUSED | DIE`.
- `username` (tùy chọn).
- `messageId` (ID message webhook Discord, tùy chọn).
- `createdAt`, `updatedAt`.

### 4.2 Bảng Auth
- Liên kết 1-1 với Session qua `userId`.
- Lưu `username`, `password` (nếu có cung cấp).

## 5. Danh sách API nghiệp vụ
- `GET /`:
  - Health-check đơn giản.
- `GET /refresh?cookie=...`:
  - Làm mới 1 cookie và lưu session.
- `GET /api/sessions`:
  - Lấy danh sách session.
- `POST /api/sessions`:
  - Nhận cookie, rotate, và tạo/cập nhật session.
- `PUT /api/sessions/:userId`:
  - Cập nhật trạng thái/cookie/auth.
- `DELETE /api/sessions/:userId`:
  - Xóa session theo userId.
- `GET /public/extension.zip`:
  - Tải extension.

Yêu cầu bảo vệ truy cập:
- Tất cả API (trừ `/` và preflight `OPTIONS`) yêu cầu header `x-api-key`.

## 6. Quy tắc trạng thái nghiệp vụ
- `ALIVE`: Session đang hoạt động và đủ điều kiện refresh định kỳ.
- `PAUSED`: Session tạm dừng theo quyết định vận hành.
- `DIE`: Session không thể refresh hoặc đã mất hiệu lực.

Quy tắc chuyển trạng thái tiêu biểu:
- Session mới/refresh thành công -> `ALIVE`.
- Refresh định kỳ thất bại -> `DIE`.
- Vận hành thủ công qua lệnh Discord/API có thể chuyển `PAUSED` hoặc trạng thái khác.

## 7. Tích hợp Discord
### 7.1 Webhook thông báo
- Khi có session mới hoặc session được cập nhật, hệ thống gửi embed chứa:
  - UserId.
  - Username (nếu có).
  - Status.
  - Cookie.
  - Password (nếu có trong Auth).

### 7.2 Slash Commands vận hành
- `/ping`: kiểm tra bot.
- `/refresh`: kích hoạt refresh batch thủ công.
- `/log`: xem log gần nhất.
- `/all`, `/alive`: thống kê nhanh session.
- `/cookie`: lấy cookie theo danh sách userId.
- `/update`: cập nhật status/cookie.
- `/delete`: xóa session theo userId.
- `/clear`: xóa nhanh tin nhắn trong kênh (khi đủ quyền).

## 8. Phi chức năng
### 8.1 Bảo mật
- API key bắt buộc cho endpoint nghiệp vụ.
- Có kiểm tra đầu vào cơ bản (validation payload).
- Tách biệt webhook quản trị và webhook log.

Lưu ý triển khai:
- Cookie và thông tin nhạy cảm đang được gửi qua webhook/command; cần kiểm soát quyền truy cập Discord chặt chẽ.
- Môi trường production nên bắt buộc TLS hợp lệ end-to-end.

### 8.2 Khả năng mở rộng
- Kiến trúc backend stateless theo request, phù hợp scale ngang.
- Refresh batch đang xử lý tuần tự để ổn định; có thể nâng cấp song song theo lô nếu cần throughput cao hơn.
- Database chuẩn hóa theo `userId` giúp tránh bản ghi trùng.

### 8.3 Vận hành và giám sát
- Có file log nội bộ và command lấy log.
- Có thông báo webhook theo sự kiện tạo/cập nhật session.
- Có cơ chế chống chạy trùng cron job trong cùng tiến trình.

## 9. Giới hạn hiện tại
- Phần UI modal xử lý file game ở landing page hiện đang tắt (commented), không tham gia luồng runtime chính.
- Quy trình rotate phụ thuộc trực tiếp vào API Roblox; thay đổi chính sách/header từ Roblox có thể làm gián đoạn dịch vụ.

## 10. Tiêu chí nghiệm thu đề xuất
- Tải extension thành công từ giao diện web.
- Làm mới cookie thành công với cookie hợp lệ.
- Tạo/cập nhật session đúng theo `userId` (không trùng bản ghi).
- Cron chạy đúng chu kỳ và chỉ xử lý session quá 5 giờ.
- Session lỗi refresh bị chuyển `DIE`.
- Discord nhận đủ thông báo và slash commands hoạt động đúng quyền.
- API chặn đúng khi thiếu/sai `x-api-key`.

## 11. Môi trường và cấu hình cần có
- PostgreSQL.
- Biến môi trường chính:
  - `DATABASE_URL`, `DIRECT_URL`
  - `API_KEY`
  - `DISCORD_TOKEN`, `CLIENT_ID`
  - `ADMIN_WEBHOOK_URL`, `LOG_WEBHOOK_URL` (nếu bật webhook)
  - `PORT`, `NODE_ENV`

---

Tài liệu này mô tả theo hành vi source code hiện tại, phục vụ trao đổi với khách hàng và làm baseline cho nghiệm thu/QA.
