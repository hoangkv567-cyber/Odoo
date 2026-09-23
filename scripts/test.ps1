$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
docker compose run --rm odoo odoo -d xyz_test -i xyz_service_reporting -u xyz_service_core,xyz_service_stock_billing,xyz_service_reporting --without-demo=all --test-enable --test-tags /xyz_service_core,/xyz_service_stock_billing,/xyz_service_reporting --stop-after-init
if ($LASTEXITCODE) { throw 'Odoo tests failed' }
