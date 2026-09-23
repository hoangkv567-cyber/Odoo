"""Complete the Vietnamese translation files of this project.

A fresh `--i18n-export` only knows the terms the database stores (model fields, views, data
records). Python and JavaScript terms are never stored in the database, so they only exist in
the shipped .po file — that is why this tool always merges three sources:

1. the export, which is the authoritative list of terms of a module,
2. the .po file already shipped with the module (keeps code/JS wording),
3. Odoo's own Vietnamese catalogue, reusing official wording for standard terms,
4. `i18n_terms.json` next to this script, `{"English term": "bản dịch"}`, for the business
   specific wording that no official catalogue can know.

Entries that end up without a translation are dropped, so a shipped catalogue never looks more
complete than it is; they are listed in the report instead.

Usage (inside the Odoo container, the host `addons/` folder is mounted read-write):

    python3 /opt/xyz/i18n_merge.py /mnt/extra-addons --exports=/tmp/po

Refresh the term list first, one file per module:

    odoo -d xyz_demo --i18n-export=/tmp/po/xyz_service_core.po \\
         --modules=xyz_service_core --language=vi_VN --stop-after-init

Running those two commands for each of the three modules is the whole maintenance flow: only *newly added* English source
strings ever end up in the TODO report: everything else keeps its shipped wording.
"""
import json
import sys
from pathlib import Path

MODULES = ('xyz_service_core', 'xyz_service_stock_billing', 'xyz_service_reporting')
EXPORT_DIR = '_i18n'
HEADER = [
    '# Translation of Odoo Server.',
    '# This file contains the translation of the following modules:',
    '# \t* %s',
    'msgid ""',
    'msgstr ""',
    '"Project-Id-Version: Odoo Server 18.0\\n"',
    '"Report-Msgid-Bugs-To: \\n"',
    '"Language-Team: Vietnamese\\n"',
    '"Language: vi_VN\\n"',
    '"MIME-Version: 1.0\\n"',
    '"Content-Type: text/plain; charset=UTF-8\\n"',
    '"Content-Transfer-Encoding: 8bit\\n"',
    '"Plural-Forms: nplurals=1; plural=0;\\n"',
]


def addons_roots():
    roots = []
    try:
        import odoo.addons as core_addons
        roots.extend(Path(path) for path in core_addons.__path__)
    except ImportError:
        pass
    fallback = Path('/usr/lib/python3/dist-packages/odoo/addons')
    if fallback.is_dir():
        roots.append(fallback)
    return roots


def unquote(text):
    text = text.strip()
    if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
        text = text[1:-1]
    return text.replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\')


def quote(text):
    return text.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')


def read_po(path):
    """Return the entries of a .po file as dicts with comments, msgid and msgstr."""
    entries = []
    comments, entry, key = [], None, None
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        if line.startswith('#'):
            comments.append(line.rstrip())
        elif line.startswith('msgid '):
            entry = {'comments': comments, 'msgid': unquote(line[6:]), 'msgstr': ''}
            entries.append(entry)
            comments, key = [], 'msgid'
        elif line.startswith('msgstr ') and entry is not None:
            entry['msgstr'] = unquote(line[7:])
            key = 'msgstr'
        elif line.startswith('"') and entry is not None and key:
            entry[key] += unquote(line)
    return [entry for entry in entries if entry['msgid']]


def translations_of(path):
    return {entry['msgid']: entry['msgstr'] for entry in read_po(path) if entry['msgstr']}


def core_terms(roots):
    terms = {}
    for root in roots:
        for path in root.glob('*/i18n/vi.po'):
            for msgid, msgstr in translations_of(path).items():
                terms.setdefault(msgid, msgstr)
    return terms


def dump_value(key, value):
    """Write a msgid/msgstr, wrapping long values the way Odoo does."""
    escaped = quote(value)
    if len(escaped) <= 76 or ' ' not in escaped:
        return ['%s "%s"' % (key, escaped)]
    head, tail = escaped[:70], escaped[70:]
    split = head.rfind(' ')
    if split <= 0:
        split = head.rfind('\\') or len(head)
    return ['%s "%s"' % (key, head[:split + 1]), '"%s"' % (head[split + 1:] + tail)]


def write_po(path, module, entries):
    lines = [line % module if '%s' in line else line for line in HEADER]
    for entry in entries:
        lines.append('')
        lines.append('#. module: %s' % module)
        lines.extend(comment for comment in entry['comments'] if comment.startswith('#: '))
        lines.extend(dump_value('msgid', entry['msgid']))
        lines.extend(dump_value('msgstr', entry['msgstr']))
    lines.append('')
    path.write_text('\n'.join(lines), encoding='utf-8')


def default_overrides():
    path = Path(__file__).with_name('i18n_terms.json')
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}


def main(modules_dir, overrides=None, export_dir=None):
    modules_dir = Path(modules_dir)
    export_dir = Path(export_dir) if export_dir else modules_dir / EXPORT_DIR
    sources = core_terms(addons_roots())
    sources.update(overrides if overrides is not None else default_overrides())
    print('Known Vietnamese terms: %d (Odoo core + business wording)' % len(sources))
    remaining = 0
    for module in MODULES:
        export = export_dir / ('%s.po' % module)
        shipped = modules_dir / module / 'i18n' / 'vi_VN.po'
        if not export.exists():
            raise FileNotFoundError('Missing export %s, run --i18n-export first' % export)
        entries = read_po(export)
        # The export only knows what the database was told about. Terms that live in Python or
        # JavaScript and were never loaded (a module that has not been updated since the code
        # changed) would be dropped here, so every shipped term the export does not mention is
        # carried over instead of being thrown away.
        exported = {entry['msgid'] for entry in entries}
        carried = [entry for entry in read_po(shipped) if entry['msgid'] not in exported] if shipped.exists() else []
        for entry in entries:
            entry['msgstr'] = entry['msgstr'] or sources.get(entry['msgid'], '')
        translated = [entry for entry in entries + carried if entry['msgstr']]
        keep = translations_of(shipped) if shipped.exists() else {}
        reused = sum(1 for entry in translated if entry['msgid'] in keep)
        pending = [entry for entry in entries if not entry['msgstr']]
        write_po(shipped, module, translated)
        remaining += len(pending)
        print('%s: %d/%d translated (%d already in the shipped file, %d from Odoo/wording, '
              '%d kept outside the export, %d to translate)'
              % (module, len(translated) - len(carried), len(entries), reused, len(translated) - len(carried) - reused,
                 len(carried), len(pending)))
        for entry in pending:
            reference = next((comment[3:] for comment in entry['comments'] if comment.startswith('#: ')), '?')
            print('  TODO [%s] %s' % (reference, entry['msgid']))
    print('Terms still to translate: %d' % remaining)


if __name__ == '__main__':
    arguments = [argument for argument in sys.argv[1:] if not argument.startswith('--')]
    options = [argument for argument in sys.argv[1:] if argument.startswith('--')]
    extra, exports = None, None
    for option in options:
        if option.startswith('--overrides='):
            extra = json.loads(Path(option.split('=', 1)[1]).read_text(encoding='utf-8'))
        elif option.startswith('--exports='):
            exports = option.split('=', 1)[1]
    main(arguments[0] if arguments else 'addons', extra, exports)
