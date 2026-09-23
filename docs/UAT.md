# UAT và kịch bản trình diễn

## Kịch bản chính (10–15 phút)
1. Giới thiệu XYZ, phần mềm Community và các vai trò (1 phút).
2. Khách đặt máy nén khí qua website; mở email/PDF trong Mailpit (2 phút).
3. Sale thêm 2 lọc dầu vào báo giá, khách ký xác nhận; kiểm tra công việc tự sinh (2 phút).
4. Điều phối kéo Gantt sang thợ 1 trong ca; thử lịch ngoài ca để thấy từ chối (1 phút).
5. Kho chuyển 2 lọc dầu sang xe thợ 1 và xác nhận giao (1 phút).
6. Thợ check-in/out, nhập thực dùng 1 lọc dầu, điền checklist, ảnh, ký nghiệm thu (3 phút).
7. Kế toán kiểm tra hóa đơn theo giờ/vật tư thực tế, xác nhận và thanh toán demo hoặc tiền mặt (2 phút).
8. Giám đốc mở Management reports, Revenue and material cost và Receivables by customer; chỉ ra 1 lọc dầu còn trên xe và công nợ đúng sau thanh toán (1 phút).
9. Đổi ngôn ngữ: thợ bấm nút quả địa cầu trên thanh trên cùng sang English rồi về Tiếng Việt; trên trang `/maintenance` đổi ngôn ngữ bằng bộ chọn ở header để thấy cùng một trang ở hai thứ tiếng (1 phút).

## Checklist nghiệm thu thủ công
- [ ] Gửi booking có email PDF và giá đúng.
- [ ] Reload POST không nhân đôi booking/CRM/đơn.
- [ ] Khách chấp nhận online tạo đúng một task.
- [ ] Gantt kéo đổi thợ/giờ và chặn trùng lịch/sai kỹ năng/ngoài ca.
- [ ] Hai người điều phối đồng thời không giữ lịch xung đột.
- [ ] Thợ 2 không thấy task, ảnh hoặc PDF của thợ 1.
- [ ] Kho tổng → xe → khách khớp số lượng, vật tư dư có thể trả.
- [ ] Không nghiệm thu khi thiếu tồn/ảnh/checklist/chữ ký.
- [ ] Bấm nghiệm thu hai lần không nhân đôi xuất kho/hóa đơn.
- [ ] Hóa đơn đúng phí + giờ thực tế + vật tư thực tế.
- [ ] Thanh toán demo thành công/thất bại/một phần; công nợ khớp.
- [ ] Tiền mặt do kế toán xác nhận, thợ không tự xác nhận.
- [ ] Email nhắc nợ không gửi lặp mốc.
- [ ] Dashboard khớp dữ liệu nguồn.
- [ ] Sao lưu/khôi phục đủ database và file đính kèm.
- [ ] Chrome desktop và trình duyệt điện thoại thao tác được.
- [ ] Đổi được Anh/Việt trên thanh trên cùng và trên trang website; menu, nhãn trường, thông báo lỗi và biên bản PDF theo đúng ngôn ngữ đã chọn.

Các ô chỉ đánh dấu sau khi trực tiếp chạy và lưu bằng chứng; không coi code đã viết là UAT đã đạt.
