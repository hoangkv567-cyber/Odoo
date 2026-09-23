{
    'name': 'XYZ Industrial Field Service',
    'version': '18.0.1.1.0',
    'license': 'LGPL-3',
    'depends': ['website_sale', 'crm', 'sale_project', 'hr_timesheet', 'hr_skills'],
    'data': [
        'security/groups.xml', 'security/ir.model.access.csv', 'security/rules.xml',
        'data/languages.xml', 'data/defaults.xml', 'views/service_views.xml', 'views/website.xml',
        'report/acceptance.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'xyz_service_core/static/lib/vis-timeline.min.js',
            'xyz_service_core/static/lib/vis-timeline.min.css',
            'xyz_service_core/static/src/dispatch.js',
            'xyz_service_core/static/src/dispatch.xml',
            'xyz_service_core/static/src/language_switch.js',
            'xyz_service_core/static/src/language_switch.xml',
            'xyz_service_core/static/src/service.scss',
        ],
    },
    'application': True,
    'installable': True,
}
