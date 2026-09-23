# Kết quả kiểm thử

Môi trường: Windows + Docker Linux engine, Odoo 18.0-20260908, PostgreSQL 16. Kiểm tra ngày 13/09/2026; chạy lại toàn bộ kiểm thử tự động, ca tích hợp và tranh chấp đồng thời ngày 14/09/2026, và chạy lại toàn bộ một lần nữa ngày 23/09/2026 sau khi thêm giao diện song ngữ Anh/Việt. Không có thanh toán hoặc email đến dịch vụ bên ngoài; email thử nghiệm vào Mailpit.

| Nhóm | Kết quả | Bằng chứng / cách chạy |
|---|---|---|
| Cài đặt module | Đạt | Cài và nâng cấp ba addon bằng Odoo; `update.log` |
| Nghiệp vụ tự động | **40/40 đạt, 0 lỗi** | `scripts/test.ps1`; database `xyz_test`; `tests.log` (18 ca logic/bảo mật, 10 ca luồng chứng từ và KPI, 12 ca song ngữ) |
| Chuyển đổi ngôn ngữ | Đạt | `scripts/language_check.py`; một tài khoản thật đổi Anh/Việt bằng nút trên thanh trên rồi đổi lại, khách đổi ngôn ngữ trang đặt lịch bằng bộ chọn website; `language.log` |
| Bản dịch đầy đủ | Đạt | `scripts/i18n_merge.py`: export ba module rồi đối chiếu, **307/307 thuật ngữ có bản dịch, 0 chuỗi còn thiếu**; `merge.log`; cài mới database rồi cập nhật module đều tự nạp `vi_VN.po`: `fresh-install-i18n.log`, `update.log` |
| Toàn luồng nhiều vai trò | Đạt | `scripts/e2e.py` trong Odoo shell; `e2e.log` |
| Điều phối đồng thời | Đạt | `scripts/concurrency.py` trên `xyz_test`; một commit, một từ chối sau retry |
| Website/Gantt | Đạt | `scripts/browser_check.py`; desktop, mobile, gửi booking, Gantt và form công việc |
| Dashboard KPI | Đạt | `scripts/dashboard_check.py`; phiên giám đốc thật, pivot và hai biểu đồ, số liệu đối chiếu lại bằng `web_read_group` |
| Khách B2B ký online | Đạt | `scripts/portal_check.py`; báo giá xuất hiện trên portal, ký thành đơn, xem lịch sử |
| Vai trò hạn chế | Đạt | `scripts/roles_check.py`; Sale theo khách, thợ theo việc, kế toán không điều phối, giám đốc chỉ đọc |
| Khôi phục | Đạt | Backup `xyz-20260913-145019.zip` khôi phục vào `xyz_restore_20260913215024`; 18 thiết bị, 25 file được kiểm tra checksum |

## Nội dung ca tích hợp
Booking → CRM/báo giá → xác nhận bằng tài khoản Sale → điều phối → chuyển kho xe → check-in/out bằng tài khoản thợ → vật tư thực tế → PDF nghiệm thu → sửa nghiệm thu → hóa đơn theo thực tế → nhắc nợ hai lần không trùng → Demo payment thất bại/một phần → kế toán thu tiền mặt phần dư → báo cáo → credit note giảm doanh thu → thiếu tồn sinh RFQ.

Ca này còn kiểm tra rollback khi thiếu tồn, không nhân đôi nghiệm thu/hóa đơn, tổng tiền ký khớp hóa đơn, không xuất hàng cho khách trước nghiệm thu, quyền đọc PDF, và được rollback toàn bộ giao dịch thử nghiệm khi kết thúc. Các kiểm tra bằng trình duyệt giữ lại booking/đơn demo để có bằng chứng xem lại.

## Kiểm thử nghiệp vụ 40 trường hợp
`test_service.py` — logic và bảo mật:
1. Booking có CRM và dòng nhân công được tính giá.
2. Xác nhận đơn lặp không sinh task thứ hai.
3. Từ chối lịch trùng.
4. Từ chối ngoài ca.
5. Check-in/out lặp không nhân đôi Timesheets.
6. Thiếu dữ liệu nghiệm thu bị từ chối.
7. Thợ không tự ghi trạng thái hoàn tất.
8. Thợ không tự đổi người phụ trách.
9. Thợ không thấy task người khác.
10. Không nhận vật tư số lượng âm.
11. Không cho thợ giả mạo chứng từ/giá vốn vật tư.
12. Người không điều phối không đọc được dữ liệu Gantt toàn công ty.
13. Thợ ghi được vật tư thực dùng trên việc của mình.
14. Hủy công việc chưa bắt đầu.
15. Từ chối hủy việc đang làm.
16. Từ chối kéo công việc sang người không hợp lệ.
17. Kế toán không ký nghiệm thu thay khách.
18. Thợ khác không đọc được PDF nghiệm thu qua ORM, kể cả khi cache đã được nạp bằng quyền cao hơn.

`test_flows.py` — luồng chứng từ theo tiêu chí kế hoạch:
19. Giá khách lẻ và B2B lấy từ bảng giá của khách; booking không có trường giá để trình duyệt tự gửi.
20. Gantt từ chối thợ thiếu kỹ năng và chấp nhận lại sau khi gán kỹ năng.
21. Nghiệm thu tạo đúng một hóa đơn nháp và đúng một biên bản; bấm lại không nhân đôi.
22. Phiếu giao hàng theo báo giá không được xác nhận trước khi khách ký; sau khi chuyển vật tư lên xe, chỉ lượng thực dùng ra tới khách, phần dư vẫn nằm trên xe.
23. Thiếu tồn trên xe thì nghiệm thu bị từ chối, không xuất âm, không tạo hóa đơn.
24. Hủy việc đã chuyển hàng lên xe bị từ chối cho tới khi có phiếu trả.
25. Hủy việc chưa thực hiện giải phóng giữ chỗ và trả tồn kho tổng về như cũ.
26. Nhắc nợ mốc 1/7/14 chỉ ghi log một lần cho mỗi mốc dù cron chạy lặp.
27. Kế toán xác nhận tiền mặt xóa đúng số dư; thợ không tự xác nhận.
28. Báo cáo KPI khớp hóa đơn (doanh thu, công nợ trong hạn/quá hạn), giờ công, giá vốn vật tư, và giảm đúng khi có credit note hoặc trả vật tư.

`test_i18n.py` — giao diện song ngữ Anh/Việt:
29. `en_US` và `vi_VN` đều được cài, đang bật và chọn được trong hồ sơ người dùng.
30. Nhãn trường của model đổi theo ngôn ngữ (Safety checked / Đã kiểm tra an toàn).
31. Nhãn lựa chọn trạng thái công việc đổi theo ngôn ngữ (Awaiting dispatch / Chờ điều phối).
32. Chuỗi trong view đổi theo ngôn ngữ, kể cả nút gọi quy trình trong form công việc.
33. Tên menu, action và nhóm quyền đổi theo ngôn ngữ.
34. Trang website đặt lịch và trang cảm ơn đổi theo ngôn ngữ.
35. Chuỗi viết trong mã Python (`_()`) đổi theo ngôn ngữ.
36. Kỹ thuật viên tự đổi được `res.users.lang` của chính mình, không cần quyền quản trị.
37. Biên bản nghiệm thu PDF render khác nhau giữa `en_US` và `vi_VN`.

`test_i18n.py` — KPI của addon báo cáo (file riêng, nên có ca riêng):
38. Nhãn chỉ tiêu KPI đổi theo ngôn ngữ (Overdue AR / Công nợ quá hạn, Current AR / Công nợ trong hạn, On-time rate / Tỷ lệ đúng hạn).
39. Tên model và tên menu báo cáo đổi theo ngôn ngữ.
40. Tiêu đề hai biểu đồ (doanh thu, công nợ theo khách) đổi theo ngôn ngữ.

## Bằng chứng giao diện
- `evidence/website-desktop.png`, `website-mobile.png`: website và form responsive.
- `evidence/dispatch.png`, `service-form.png`: Gantt và phiếu công việc.
- `evidence/technician-mobile.png`: phiếu thợ ở viewport 390px với nút Check in.
- `evidence/accountant.png`, `director-report.png`: giao diện theo vai trò, chụp lại cùng ngày 14/09/2026.
- `evidence/portal-signature.png`, `portal-confirmed.png`: khách ký và đơn được xác nhận.
- `evidence/dashboard-pivot.png`, `dashboard-revenue.png`, `dashboard-receivables.png`: dashboard KPI của giám đốc tại thời điểm chụp (11 dòng dữ liệu: doanh thu 3.577.000 ₫, giá vốn vật tư 275.000 ₫, 8 giờ công, 3 việc hoàn tất, 2 đúng hạn, công nợ trong hạn 571.000 ₫ và quá hạn 1.278.900 ₫).
- `evidence/language-backend-vi.png`, `language-backend-en.png`, `language-backend-switched-back.png`: cùng màn hình công việc hiện trường ở tiếng Việt, ở tiếng Anh và sau khi quay lại tiếng Việt bằng nút đổi ngôn ngữ trên thanh trên cùng (chụp 23/09/2026).
- `evidence/language-website-vi.png`, `language-website-en.png`: trang đặt lịch công khai ở hai ngôn ngữ qua bộ chọn trên header website.
- `evidence/demo-booking-dispatch.webm`, `demo-portal-signature.webm`: video kiểm thử tự động.

Log `.log` lưu cục bộ và được bỏ qua bởi Git; không đưa log đăng nhập/session vào báo cáo công khai. UAT với người dùng thật và điện thoại vật lý chưa được đánh dấu hoàn tất.
