# noinspection PyStatementEffect
{
    'name': "Trilab Partners Sync & Validation for Poland (GUS/REGON/KRD)",

    'summary': "Sync Partner data from GUS (Główny Urząd Statystyczny) and validate it with KRD",
    'author': 'Trilab',
    'website': "https://trilab.pl",
    'category': 'Accounting',
    'version': '13.1.9',
    'depends': [
        'base',
        'contacts'
    ],
    'external_dependencies': {
        'python': ['gusregon', 'zeep']
    },
    'data': [
        'views/res_config_settings.xml',
        'views/res_partner.xml',
        'views/krd.xml'
    ],
    'images': [
        'static/description/banner.png'
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'OPL-1',
    'price': 40.0,
    'currency': 'EUR'
}
