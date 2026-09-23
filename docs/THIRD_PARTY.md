# Thành phần nguồn mở

| Thành phần | Bản dùng | Nguồn |
|---|---|---|
| Odoo Community | 18.0, image khóa digest trong Compose | https://github.com/odoo/odoo/tree/18.0 |
| PostgreSQL | 16, image khóa digest | https://www.postgresql.org/about/licence/ |
| Mailpit | 1.27, image khóa digest | https://github.com/axllent/mailpit |
| vis-timeline | 7.7.3, standalone UMD | https://github.com/visjs/vis-timeline/tree/v7.7.3 |
| Playwright (chỉ kiểm thử) | 1.62.0 | https://github.com/microsoft/playwright-python |

Addon XYZ khai báo LGPL-3 trong manifest. Giữ giấy phép MIT đi kèm vis-timeline tại `addons/xyz_service_core/static/lib/LICENSE.MIT.txt`. Bundle thư viện giữ nguyên thông tin bản quyền đầu file. Không có addon Enterprise hoặc addon mua từ Odoo Apps.

Docker Engine/Compose có thể dùng trong Linux/WSL2. Workspace hiện dùng Docker Desktop đã có trên máy; điều kiện sử dụng Docker Desktop do người vận hành quản lý theo giấy phép tương ứng.
