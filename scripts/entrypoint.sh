#!/bin/bash
set -e
python3 - <<'PY'
import configparser
import os
config = configparser.ConfigParser()
config.read('/etc/odoo/odoo.conf')
config.set('options', 'admin_passwd', os.environ['ODOO_MASTER_PASSWORD'])
with open('/tmp/xyz-odoo.conf', 'w') as output:
    config.write(output)
os.chmod('/tmp/xyz-odoo.conf', 0o600)
PY
exec /entrypoint.sh "$@" --config=/tmp/xyz-odoo.conf
