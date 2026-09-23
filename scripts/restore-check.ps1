param([Parameter(Mandatory=$true)][string]$Archive)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$archivePath = (Resolve-Path -LiteralPath $Archive).Path
$restoreName = 'xyz_restore_' + (Get-Date -Format 'yyyyMMddHHmmss')
$env:XYZ_RESTORE_DB = $restoreName
"import os; import odoo.service.db; odoo.service.db.restore_db(os.environ['XYZ_RESTORE_DB'], '/backup/input.zip', copy=True); print('Restored to ' + os.environ['XYZ_RESTORE_DB'])" | docker compose run --rm -T -e XYZ_RESTORE_DB -v "${archivePath}:/backup/input.zip:ro" odoo odoo shell -d xyz_demo --no-http
if ($LASTEXITCODE) { throw 'Restore failed' }
"import os, hashlib; files=env['ir.attachment'].search([('store_fname', '!=', False)]); missing=[a.id for a in files if not os.path.isfile(a._full_path(a.store_fname))]; assert not missing, missing; corrupt=[a.id for a in files if hashlib.sha1(open(a._full_path(a.store_fname), 'rb').read()).hexdigest() != a.checksum]; assert not corrupt, corrupt; print('RESTORE PASS: equipment=', env['xyz.equipment'].search_count([]), 'verified files=', len(files))" | docker compose run --rm -T odoo odoo shell -d $restoreName --no-http
if ($LASTEXITCODE) { throw 'Restored database verification failed' }
Remove-Item Env:XYZ_RESTORE_DB
