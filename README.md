# XYZ · ERP bảo dưỡng thiết bị công nghiệp

Odoo 18 Community, PostgreSQL 16, Docker Compose, Mailpit; toàn bộ addon tự phát triển và thư viện miễn phí. Kế hoạch học phần: [plan.md](plan.md).

## Chạy trên Windows

Yêu cầu Docker engine hoạt động (Docker Desktop trên máy hiện tại hoặc Docker Engine trong WSL2).

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start.ps1
```

- Website: http://localhost:8069/maintenance
- Quản trị: http://localhost:8069/odoo
- Email demo: http://localhost:8025
- Mật khẩu sinh ngẫu nhiên lưu trong `local-credentials.txt` (không đưa lên Git).
- Tài khoản nội bộ: `admin`, `manager@xyz.test`, `sale@xyz.test`, `dispatch@xyz.test`, `warehouse@xyz.test`, `accountant@xyz.test`, `director@xyz.test`, `tech1@xyz.test` … `tech4@xyz.test`.
- Portal demo: `customer1@xyz.test` (B2B) và `customer6@xyz.test` (khách lẻ), cùng mật khẩu demo.

Container web chỉ bind localhost. Để UAT trên điện thoại cùng mạng, tạo `compose.override.yaml` đổi binding sang IP mạng nội bộ của máy và chỉ mở firewall cho mạng riêng. Không triển khai cấu hình demo ra Internet.

## Cập nhật và kiểm thử

```powershell
docker compose stop odoo
docker compose run --rm odoo odoo -d xyz_demo -u xyz_service_core,xyz_service_stock_billing,xyz_service_reporting --stop-after-init
docker compose up -d odoo
powershell -ExecutionPolicy Bypass -File scripts/test.ps1
```

Kiểm thử chạy trên database `xyz_test`, tách `xyz_demo`. Xem [hướng dẫn sử dụng](docs/USER_MANUAL.md), [UAT](docs/UAT.md) và [trạng thái triển khai](docs/STATUS.md) trước khi nghiệm thu.

Kiểm thử trình duyệt và ghi video:

```powershell
python -m pip install -r scripts/requirements-dev.txt
python -m playwright install chromium
python scripts/browser_check.py
python scripts/portal_check.py
python scripts/roles_check.py
python scripts/dashboard_check.py
python scripts/language_check.py
```

Các script trình duyệt tạo yêu cầu/đơn demo mới để kiểm tra luồng. Ca tích hợp ORM chạy qua `scripts/e2e.py` trong Odoo shell và rollback sau khi kiểm tra, không giữ lại giao dịch tiền thử nghiệm.

Sao lưu và thử khôi phục (database mới, không ghi đè demo):

```powershell
powershell -ExecutionPolicy Bypass -File scripts/backup.ps1
powershell -ExecutionPolicy Bypass -File scripts/restore-check.ps1 -Archive backups/xyz-YYYYMMDD-HHMMSS.zip
```

Video và ảnh kiểm thử nằm trong `docs/evidence/`; đây là bằng chứng tự động, không thay thế video thuyết minh 10–15 phút của nhóm.

## Ngôn ngữ

Tiếng Anh là ngôn ngữ nguồn của cả ba addon; tiếng Việt nạp từ `i18n/vi_VN.po` khi cài mới hoặc cập nhật module, nên hệ thống ra tiếng Việt ngay, không cần thao tác thêm. Người dùng đổi ngôn ngữ bằng nút quả địa cầu trên thanh trên cùng (Shift+L); khách đổi ngôn ngữ trang đặt lịch bằng bộ chọn ở header website. Xem mục 8 trong [hướng dẫn sử dụng](docs/USER_MANUAL.md).

Khi thêm hoặc sửa chuỗi tiếng Anh, export lại ba module rồi chạy `scripts/i18n_merge.py` để cập nhật `i18n/vi_VN.po`; chữ nghiệp vụ riêng của dự án nằm trong `scripts/i18n_terms.json`, còn thiếu chỗ nào thì công cụ in ra danh sách cần dịch thay vì im lặng bỏ qua. `scripts/i18n.py` nạp bản dịch vào database đang chạy, `scripts/language_check.py` kiểm tra việc chuyển ngôn ngữ bằng trình duyệt.

## Cấu trúc

- `addons/xyz_service_core`: website booking, CRM/Sales/Project, thiết bị, Gantt, giờ công, chữ ký và PDF.
- `addons/xyz_service_stock_billing`: kho xe, vật tư thực dùng, hóa đơn, tiền mặt và nhắc nợ.
- `addons/xyz_service_reporting`: pivot/graph tổng hợp.
- `scripts`: khởi tạo, dữ liệu demo, kiểm thử và sao lưu.

Không sửa Odoo core. Thư viện Gantt: vis-timeline 7.7.3, bản standalone đóng gói cục bộ, giấy phép MIT trong `static/lib`. Các giao dịch thanh toán và email chỉ phục vụ demo.
