"""Activate the supported languages and load their translations.

Run inside `odoo shell -d <database>`:

    "exec(open('/opt/xyz/i18n.py', encoding='utf-8').read())"

English (en_US) is the source language of this project, Vietnamese (vi_VN) is the
translation. Activating a language only flips `res.lang.active`; the terms itself come from
the `i18n/<lang>.po` files of every installed module, which the installer only reads for
languages that are already active. A database installed before Vietnamese existed therefore
keeps an English core interface, so this script loads the .po files of all installed modules
once and remembers the work in an ir.config_parameter.
"""
import os

from odoo import fields

SUPPORTED = ('vi_VN',)
PARAM = 'xyz.i18n.loaded'
force = os.environ.get('XYZ_I18N_FORCE') == '1'

Lang = env['res.lang']
languages = Lang.with_context(active_test=False).search([('code', 'in', SUPPORTED)])
missing = set(SUPPORTED) - set(languages.mapped('code'))
if missing:
    raise RuntimeError('Languages missing from res.lang: %s' % ', '.join(sorted(missing)))

activated = languages.filtered(lambda lang: not lang.active)
if activated:
    activated.write({'active': True})
    print('Activated: %s' % ', '.join(activated.mapped('code')))

marker = env['ir.config_parameter'].sudo().get_param(PARAM) or ''
wanted = ','.join(sorted(languages.mapped('code')))
if force or marker != wanted:
    wizard = env['base.language.install'].create({
        'lang_ids': [fields.Command.set(languages.ids)],
        'overwrite': False,
    })
    wizard.lang_install()
    env['ir.config_parameter'].sudo().set_param(PARAM, wanted)
    print('Loaded translations for: %s' % wanted)
else:
    print('Translations already loaded for: %s (set XYZ_I18N_FORCE=1 to reload)' % wanted)

env.cr.commit()

# Evidence: the same terms must resolve differently in the source and the translated language.
samples = [
    ('base term', env['res.partner'].with_context(lang='vi_VN').fields_get(['name'])['name']['string']),
    ('module label', env['project.task'].with_context(lang='vi_VN').fields_get(['xyz_checked_safety'])['xyz_checked_safety']['string']),
    ('selection', dict(env['project.task'].with_context(lang='vi_VN').fields_get(['xyz_state'])['xyz_state']['selection'])['new']),
]
for label, value in samples:
    print('%s: %s' % (label, value))
source = env['project.task'].with_context(lang='en_US').fields_get(['xyz_checked_safety'])['xyz_checked_safety']['string']
installed = Lang.with_context(active_test=False).search([('code', 'in', ('en_US',) + SUPPORTED)])
active = ', '.join('%s (%s)' % (lang.name, lang.code) for lang in installed.filtered('active'))
if source != samples[1][1]:
    print('LANGUAGE PASS: active [%s]; source "%s" is shown as "%s" in vi_VN' % (active, source, samples[1][1]))
else:
    raise RuntimeError('Vi translation was not loaded for xyz_checked_safety: %r' % source)
