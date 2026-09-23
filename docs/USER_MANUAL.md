# Hướng dẫn sử dụng demo XYZ

## 1. Khách hàng
Mở `/maintenance`, nhập liên hệ, thiết bị, địa chỉ, dịch vụ và thời gian mong muốn theo giờ Việt Nam. Sau khi gửi, mở Mailpit để xem email báo giá, PDF và đường dẫn portal. Trên portal, xem và ký xác nhận báo giá. Lịch đặt là yêu cầu, chưa phải lịch điều phối đã xác nhận.

Người chưa đăng nhập không được nhận danh tính hay bảng giá B2B chỉ bằng cách nhập email của khách cũ. Đăng nhập portal khách B2B để áp dụng bảng giá đã được Sale xác nhận.

## 2. Sale
Đăng nhập Sale, xem CRM hoặc XYZ Service → Bookings. Trong dữ liệu demo, booking từ website tự giao `sale@xyz.test`. Quản lý đổi người phụ trách trên booking sẽ đồng bộ cơ hội, đơn hàng, thiết bị và khách hàng. Mở báo giá, kiểm tra phí dịch vụ, giờ công dự kiến và thêm vật tư dự kiến. Chọn bảng giá và điều khoản thanh toán đúng loại khách. Khách chấp nhận online hoặc Sale xác nhận đơn sẽ tạo công việc.

Trong Products, nhóm **XYZ Website booking** cho phép chọn dịch vụ được đặt qua web, số giờ dự kiến và kỹ năng yêu cầu. Sản phẩm phải là Service, được bán và được publish lên website mới xuất hiện trong form.

## 3. Kho và mua hàng
Đăng nhập Warehouse, mở Sales Order kiểm tra phiếu giao và giữ chỗ. Trong công việc, sau khi gán thợ có kho xe, bấm **Prepare truck transfer**. Mở phiếu chuyển nội bộ, nhập lượng đã giao cho thợ và Validate. Tồn thiếu cần nhập hàng trước; Purchase → RFQ xem đề nghị bổ sung từ quy tắc min/max rồi xác nhận PO và nhận hàng.

Vật tư dư ở xe có thể giữ cho lần sau hoặc chuyển nội bộ về kho tổng. Dùng chứng từ Inventory, không sửa số tồn bằng tay để che chênh lệch.

## 4. Điều phối
XYZ Service → Dispatch board. Mỗi hàng là một thợ, hàng đầu chứa việc chưa phân công. Kéo thanh sang hàng thợ hoặc đổi thời gian; lỗi kỹ năng/ca/trùng lịch sẽ hiển thị và hoàn tác vị trí. Nhấp đúp để mở phiếu. Có thể gán thợ, nhập Planned start/end rồi bấm Schedule trong form.

Employees → hồ sơ thợ: khai báo Skills, lịch làm việc, khu vực và Truck stock location. Gantt hiển thị theo múi giờ trình duyệt; các tài khoản demo đặt múi giờ Việt Nam.

## 5. Thợ hiện trường
Đăng nhập `tech1@xyz.test` hoặc `tech2@xyz.test`. Mở XYZ Service → Field jobs, chỉ thấy việc được giao. Trong tab XYZ Service:

1. Mở liên kết bản đồ để xem địa chỉ.
2. Bấm Check in khi bắt đầu; Check out khi kết thúc. Không đóng trình duyệt để thay cho check-out.
3. Nhập lượng vật tư thực dùng; kiểm tra số liệu với khách.
4. Đánh dấu ba mục checklist, tải ảnh trước/sau, nhập tên người ký, cho khách ký trên màn hình.
5. Bấm Accept service. Hệ thống kiểm tra dữ liệu, xuất vật tư, lưu nghiệm thu và tạo hóa đơn nháp trong cùng giao dịch.

Nếu thiếu tồn hoặc dữ liệu nghiệm thu, sửa nguyên nhân rồi bấm lại. Thao tác nghiệm thu lặp không sinh thêm hóa đơn. Biên bản đã ký là dữ liệu bất biến. Trước khi ký, khách cần kiểm tra **Actual total for customer approval** (tổng tiền gồm thuế).

Quản lý có thể **Mở lại để nghiệm thu mới** khi hóa đơn còn nháp: hệ thống đảo tiêu hao, hủy hóa đơn nháp và xóa chữ ký trên phiếu để ký lại; PDF cũ vẫn giữ nguyên. Sau khi hóa đơn đã post, dùng công việc bổ sung và chứng từ điều chỉnh chuẩn Odoo.

## 6. Kế toán
Mở hóa đơn liên kết công việc, kiểm tra phí cố định + giờ công thực tế + vật tư thực xuất rồi Confirm/Post. Dùng Register Payment theo quy trình Odoo hoặc đường dẫn thanh toán portal với Demo provider.

Tiền mặt: thợ nhập **Cash reported by technician**; kế toán kiểm tra tiền đã nhận và bấm **Confirm cash receipt**. Cần cấu hình cash journal và tài khoản thanh toán phù hợp. Tài khoản kế toán phải có email: Odoo ghi chú “Invoice paid” lên đơn hàng khi thu tiền và sẽ báo lỗi cấu hình người gửi nếu thiếu email. Thanh toán một phần để lại số dư công nợ. Demo provider không giao dịch với ngân hàng thật.

Nhắc nợ tự động chỉ gửi cho hóa đơn XYZ posted còn dư nợ; mốc 1/7/14 ngày quá hạn, ghi log để tránh gửi trùng. Email xem trong Mailpit.

## 7. Giám đốc
Đăng nhập `director@xyz.test`, mở XYZ Service → Management reports cho pivot theo thợ/khách/tháng và biểu đồ số việc, giờ công theo thợ; hai mục con **Revenue and material cost** (doanh thu và giá vốn theo tháng) và **Receivables by customer** (công nợ trong hạn và quá hạn theo khách) mở sẵn dạng biểu đồ. Dữ liệu demo đã có ba công việc lịch sử đã xuất hóa đơn (thu đủ, quá hạn, thu một phần) nên KPI có số ngay sau khi khởi động; chạy thêm luồng UAT sẽ tăng tiếp số liệu. Chọn các chỉ tiêu giờ công, vật tư, doanh thu, công nợ, hoàn thành và phần trăm đúng hạn. Doanh thu trừ credit note đã post; chi phí vật tư trừ lượng trả. Đây là tài khoản xem báo cáo, không có quyền điều phối hoặc sửa chứng từ.

## 8. Chuyển đổi ngôn ngữ Anh – Việt
Tiếng Anh là ngôn ngữ nguồn của hệ thống, tiếng Việt là bản dịch đi kèm trong `i18n/vi_VN.po` của từng addon và được nạp tự động khi cài mới hoặc cập nhật module. Hai ngôn ngữ đều có sẵn, không phải cài thêm gì.

- Trong giao diện quản trị: bấm nút quả địa cầu trên thanh trên cùng (phím tắt Shift+L) rồi chọn English (US) hoặc Vietnamese / Tiếng Việt. Lựa chọn được ghi vào hồ sơ người dùng và trang tự tải lại; nhân viên tự đổi được, không cần quyền quản trị.
- Trên website: khách bấm bộ chọn ngôn ngữ ở header trang `/maintenance`; địa chỉ đổi giữa `/maintenance` (tiếng Việt, mặc định của website) và `/en/maintenance` (tiếng Anh). Khách chưa đăng nhập vẫn đổi được, và lựa chọn chỉ ảnh hưởng phiên của khách đó.
- Hồ sơ người dùng: Preferences → Language. Đây cũng là nơi quản trị viên gán ngôn ngữ cho tài khoản mới.
- Hóa đơn, email và biên bản PDF lấy theo ngôn ngữ của người nhận. Tài khoản demo được đặt sẵn tiếng Việt và múi giờ Việt Nam.
- Nếu tiếng Việt chưa được bật hoặc bản dịch mới sửa chưa hiện ra: chạy `scripts/i18n.py` trong Odoo shell (thêm `XYZ_I18N_FORCE=1` để nạp lại từ đầu), rồi kiểm tra lại bằng `scripts/language_check.py`.
- Muốn thêm ngôn ngữ khác: Settings → Translations → Load a Translation, hoặc bổ sung `i18n/<lang>.po` cho từng addon rồi cập nhật module.

## 9. Vận hành
Chạy `scripts/start.ps1` để khởi động; `docker compose stop` để dừng, giữ nguyên dữ liệu. Không dùng `docker compose down -v` vì sẽ xóa volume dữ liệu. Mật khẩu và `.env` nằm ngoài Git. Ghi nhận giới hạn hiện tại tại STATUS.md.
