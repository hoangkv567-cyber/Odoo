# Kế hoạch ERP bảo dưỡng thiết bị công nghiệp XYZ

## Mục tiêu và lựa chọn đã chốt
Nhóm 5: hai sinh viên biết Odoo, làm toàn thời gian trong 8 tuần, hướng dẫn bởi Mr. Hiếu. Xây dựng demo học phần bằng phần mềm miễn phí: Odoo 18 Community, PostgreSQL 16, Docker Compose, Mailpit. Dùng Project/Timesheets làm nền cho Field Service; tự xây Gantt kéo thả bằng vis-timeline. Thợ dùng web responsive, khách ký trên màn hình; thanh toán giả lập, không VNPay thật hay hóa đơn điện tử pháp lý.

Luồng: Đặt lịch → CRM và báo giá tự động → xác nhận đơn → giữ vật tư và điều phối → thực địa → nghiệm thu → hóa đơn → thanh toán và báo cáo.

## Nghiệp vụ và thiết kế
- Hai nhóm dịch vụ: máy nén khí và hệ thống lạnh. Booking lưu liên hệ, địa chỉ, thiết bị, dịch vụ, thời gian mong muốn. Giá tính tại server; khách mới dùng giá lẻ, B2B do Sale xác nhận. Booking không cam kết lịch. Một đơn có một lần bảo dưỡng, một thiết bị, một thợ chính.
- Báo giá gồm phí cố định, giờ công và vật tư dự kiến; hóa đơn theo giờ công/vật tư đã nghiệm thu. Email PDF qua Mailpit, portal khách chấp nhận báo giá.
- Kho tổng và hai vị trí nội bộ trên xe. Giữ chỗ khi xác nhận đơn, chuyển nội bộ trước đi công trình, xuất lượng thực dùng sang khách, trả phần dư bằng chứng từ. Không cho tồn âm. Min/max tự sinh RFQ, nhân viên xác nhận PO.
- Gantt theo thợ, kéo đổi lịch/người, lọc kỹ năng/khu vực; server chặn trùng lịch, ngoài ca và sai kỹ năng, kể cả cập nhật đồng thời. Không tối ưu tuyến đường.
- Thợ xem việc được giao, mở bản đồ, check-in/out ra Timesheets; không chạy hai bộ đếm. Checklist, ảnh trước/sau, vật tư và chữ ký bắt buộc khi nghiệm thu. Biên bản PDF lưu dữ liệu tại thời điểm ký; sửa phải nghiệm thu lại.
- Trạng thái: chờ điều phối, đã lên lịch, đang thực hiện, chờ nghiệm thu, hoàn tất, hủy.
- Nghiệm thu tạo đúng một hóa đơn nháp. Kế toán kiểm tra/xác nhận, ghi nhận và đối soát thanh toán. Thợ chỉ khai báo thu tiền mặt, kế toán xác nhận. B2B 30 ngày, khách lẻ trả ngay; nhắc nợ ngày 1/7/14 không gửi trùng.
- Vai trò: Sale chỉ dữ liệu được giao; thợ chỉ việc được giao; điều phối toàn bộ lịch; kho chứng từ kho/mua; kế toán toàn công nợ; giám đốc báo cáo; khách chỉ portal của mình. Kiểm tra cả file đính kèm và đường dẫn trực tiếp.
- Addon `xyz_service_core`: booking, thiết bị, Project, Gantt, thực địa, nghiệm thu. `xyz_service_stock_billing`: kho xe, tiêu hao, hóa đơn, nhắc nợ. `xyz_service_reporting`: KPI. Không sửa Odoo core; dùng ORM/controller của Odoo, không REST API riêng.

## Lộ trình và phân công
35 giờ/người/tuần, tổng 560 giờ; dành 20% cho kiểm thử, sửa lỗi và tài liệu.

| Tuần | Sinh viên A | Sinh viên B | Nghiệm thu |
|---|---|---|---|
| 1 | Docker, Git, website | Quy trình, dữ liệu, nguyên mẫu Gantt | Dựng lại được môi trường, Gantt lưu lịch |
| 2 | Booking, CRM, báo giá, PDF, portal | Công việc từ đơn, quyền | Booking đến đơn và một công việc |
| 3 | Liên kết Sales/vật tư | Kho xe, giữ chỗ, RFQ | Kho tổng → xe → khách, trả dư |
| 4 | Giao diện lịch | Kỹ năng, ca, xung đột | Kéo thả có kiểm tra tại server |
| 5 | Portal, PDF | Timer, checklist, ảnh, ký | Hoàn thành trên điện thoại |
| 6 | Hóa đơn, thanh toán, nhắc nợ | Đối chiếu kho, nghiệm thu, tiền mặt | Toàn luồng đến thu tiền |
| 7 | Dashboard | Phân quyền, backup/restore | KPI khớp, không truy cập chéo |
| 8 | Báo cáo, hướng dẫn | UAT, sửa lỗi, video | Bàn giao chạy lại được |

Demo hằng tuần với Mr. Hiếu; cuối tuần 6 chốt luồng chính; tuần 7–8 không thêm chức năng.

## Kiểm thử và tiêu chí
- Booking/nhấn nút lặp không tạo trùng CRM, đơn, task, timesheet, hóa đơn.
- Bảng giá khách lẻ/B2B chính xác; không tin giá từ trình duyệt.
- Gantt chặn trùng lịch, ngoài ca, sai kỹ năng, hai điều phối đồng thời.
- Kho thiếu không âm; chỉ hóa đơn vật tư thực xuất; phát sinh cần ký.
- Timer không trùng; thiếu checklist/ảnh/chữ ký không nghiệm thu.
- Thanh toán thành công/thất bại/một phần phản ánh đúng công nợ.
- Hủy trước thực hiện giải phóng giữ chỗ; hàng đã chuyển phải trả bằng phiếu.
- ACL/record rules/controller/ảnh/PDF không truy cập chéo.
- Backup cả database và filestore, thử restore.
- KPI: doanh thu chưa thuế của hóa đơn posted trừ hoàn tiền; giá vốn vật tư thực xuất trừ trả; số việc/giờ công theo thợ; tỷ lệ đúng hạn; công nợ trong/quá hạn.

Dữ liệu đích: 10 khách, 10 thiết bị, 2 nhóm dịch vụ, 15 vật tư, 3 nhà cung cấp, 4 thợ, 2 kho xe. Kiểm thử tự động tập trung logic và bảo mật; UAT thủ công Gantt, mobile, chữ ký.

## Giả định và bàn giao
Một công ty, VND, Asia/Ho_Chi_Minh, mạng nội bộ, dữ liệu giả lập. Không hợp đồng định kỳ, nhiều thợ/task, mobile offline. Chốt dependency khi đã kiểm thử và giữ giấy phép. Ưu tiên luồng chính hơn trang trí. Bàn giao source, Compose, dữ liệu, backup, hướng dẫn cài/khôi phục/sử dụng, sơ đồ nghiệp vụ, bảng đối chiếu đề bài, test/UAT, hạn chế, slide và video 10–15 phút.

## Theo dõi triển khai
Tình trạng thực tế và phần chưa hoàn thành được ghi riêng trong `docs/STATUS.md`; kế hoạch này không phải tuyên bố mọi chức năng đã nghiệm thu.
