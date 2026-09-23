# Trạng thái triển khai

Cập nhật: 23/09/2026. Đây là bản demo học phần chạy cục bộ, không phải hệ thống sản xuất đã được doanh nghiệp nghiệm thu.

## Đã triển khai
- Odoo 18 Community, PostgreSQL 16 và Mailpit qua Compose, image khóa digest; healthcheck và volume dữ liệu.
- Website XYZ, booking có CSRF và mã gửi chống trùng được ký, CRM, báo giá PDF/email, bảng giá VND khách lẻ/B2B và portal ký đơn.
- Đơn hàng sinh công việc; Gantt kéo thả, lọc khu vực/kỹ năng, kiểm tra ca và tranh chấp lịch.
- Kho tổng, hai kho xe, giữ chỗ, phiếu bàn giao, tiêu hao thực tế và min/max sinh RFQ.
- Phiếu thực địa riêng, dùng được trên mobile; timer, checklist, ảnh, chữ ký và tổng tiền nghiệm thu.
- PDF nghiệm thu bất biến; sửa trước khi post hóa đơn có đảo tiêu hao, hủy nháp và lưu lần ký mới.
- Hóa đơn theo thực tế, thanh toán Demo, tiền mặt có xác nhận kế toán và nhắc nợ chống trùng.
- Quyền Sale, điều phối, kho, thợ, kế toán, giám đốc và portal; kế toán không được điều phối, giám đốc chỉ đọc báo cáo.
- Pivot/graph với doanh thu sau hoàn tiền, giá vốn sau trả vật tư, giờ công, tỷ lệ đúng hạn, và công nợ trong hạn/quá hạn theo khách hàng; dashboard có ba đồ thị (số việc và giờ công theo thợ, doanh thu và giá vốn theo tháng, công nợ theo khách).
- Giao diện song ngữ Anh/Việt: tiếng Anh là ngôn ngữ nguồn của cả ba addon, tiếng Việt nạp từ `i18n/vi_VN.po` (307 thuật ngữ) ngay khi cài hoặc cập nhật module; người dùng đổi ngôn ngữ ở nút quả địa cầu trên thanh trên cùng (phím tắt Shift+L), khách đổi ngôn ngữ website ở bộ chọn trên header. Tiếng Việt là mặc định của website và của các tài khoản demo; PDF nghiệm thu và email lấy theo ngôn ngữ người nhận.
- Script khởi tạo, dữ liệu mẫu, kiểm thử, sao lưu và khôi phục; thêm công cụ đồng bộ bản dịch (`scripts/i18n_merge.py`) và kiểm tra chuyển ngôn ngữ (`scripts/language_check.py`).
- Hướng dẫn, báo cáo triển khai, kịch bản UAT, ảnh và hai video kiểm thử giao diện.

## Đã kiểm chứng
Chi tiết tại [TEST_RESULTS.md](TEST_RESULTS.md): 40 kiểm thử nghiệp vụ (18 ca logic/bảo mật, 10 ca luồng chứng từ/KPI và 12 ca song ngữ), ca tích hợp nhiều vai trò, tranh chấp hai giao dịch, trình duyệt desktop/mobile, portal ký báo giá, quyền truy cập, chụp dashboard KPI, chuyển đổi Anh/Việt trên giao diện và website, và khôi phục database/filestore.

Địa chỉ chạy: http://localhost:8069/maintenance. Email demo: http://localhost:8025. Mật khẩu nằm trong `local-credentials.txt`, không đưa lên Git. Dữ liệu demo ban đầu có 10 khách, 10 thiết bị, 15 vật tư, 3 nhà cung cấp, 4 thợ và 2 kho xe, cộng ba công việc lịch sử đã nghiệm thu và xuất hóa đơn (một đã thu đủ, một quá hạn, một thu một phần) để dashboard KPI có số liệu ngay sau khi khởi động; kiểm thử trình duyệt tạo thêm yêu cầu/đơn mẫu.

## Cần nhóm thực hiện trước khi nộp nghiệm thu
- Chạy buổi UAT đóng vai trực tiếp với Mr. Hiếu theo `UAT.md`, điền người kiểm thử/ngày/kết quả.
- Kiểm tra trên điện thoại thật cùng mạng; hiện bằng chứng mobile được tạo bằng Chromium giả lập viewport 390px.
- Thay ảnh thử nghiệm bằng ảnh thiết bị do nhóm chuẩn bị, rà soát cách trình bày biên bản.
- Quay video thuyết minh toàn luồng 10–15 phút. Hai video `.webm` đã có là ghi hình kiểm thử tự động, không có lời thuyết minh.

## Giới hạn chủ động
Một công ty, VND, một thiết bị và một thợ chính cho mỗi đơn. Không VNPay thật, hóa đơn điện tử pháp lý, mobile native/offline, tối ưu tuyến đường, hợp đồng bảo trì định kỳ hoặc theo dõi GPS thời gian thực. Sau khi hóa đơn đã post, dùng công việc/chứng từ điều chỉnh mới. Các app Field Service/Planning Enterprise được thay bằng chức năng tự phát triển, không sử dụng giấy phép Enterprise.
