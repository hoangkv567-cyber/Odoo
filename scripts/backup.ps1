$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$backupDir = Join-Path (Get-Location).Path 'backups'
New-Item -ItemType Directory -Force $backupDir | Out-Null
docker compose stop odoo
try {
    "import odoo.service.db; from datetime import datetime; target='/backup/xyz-' + datetime.now().strftime('%Y%m%d-%H%M%S') + '.zip'; out=open(target, 'wb'); odoo.service.db.dump_db('xyz_demo', out, 'zip'); out.close(); print(target)" | docker compose run --rm -T -v "${backupDir}:/backup" odoo odoo shell -d xyz_demo --no-http
    if ($LASTEXITCODE) { throw 'Backup failed' }
} finally {
    docker compose up -d odoo
}
