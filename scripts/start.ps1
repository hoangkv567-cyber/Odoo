$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not (Test-Path .env)) {
    $dbSecret = [guid]::NewGuid().ToString('N')
    $masterSecret = [guid]::NewGuid().ToString('N')
    "POSTGRES_PASSWORD=$dbSecret`nODOO_MASTER_PASSWORD=$masterSecret`nODOO_DB=xyz_demo" | Set-Content -Encoding ascii .env
}
docker compose up -d db mailpit
if ($LASTEXITCODE) { throw 'Cannot start database' }
docker compose stop odoo
docker compose run --rm odoo odoo -d xyz_demo -i xyz_service_reporting -u xyz_service_core,xyz_service_stock_billing,xyz_service_reporting --without-demo=all --stop-after-init
if ($LASTEXITCODE) { throw 'Odoo initialization failed' }
docker compose up -d --wait odoo
if ($LASTEXITCODE) { throw 'Odoo web service did not become healthy' }
if (-not (Test-Path local-credentials.txt)) {
    $demoSecret = [guid]::NewGuid().ToString('N').Substring(0, 20)
    "Demo password: $demoSecret`nUsers: admin, manager@xyz.test, sale@xyz.test, dispatch@xyz.test, warehouse@xyz.test, accountant@xyz.test, tech1@xyz.test through tech4@xyz.test" | Set-Content -Encoding ascii local-credentials.txt
}
$env:XYZ_DEMO_PASSWORD = ((Get-Content local-credentials.txt -First 1) -replace '^Demo password: ', '')
"exec(open('/opt/xyz/seed.py', encoding='utf-8').read())" | docker compose run --rm -T -e XYZ_DEMO_PASSWORD odoo odoo shell -d xyz_demo --no-http
if ($LASTEXITCODE) { throw 'Demo data initialization failed' }
Remove-Item Env:XYZ_DEMO_PASSWORD
docker compose up -d --wait odoo
Write-Host 'Odoo: http://localhost:8069/maintenance | Mailpit: http://localhost:8025'
