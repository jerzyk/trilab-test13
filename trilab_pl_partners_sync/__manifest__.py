# noinspection PyStatementEffect
{
    'name': "Trilab Partners Sync for Poland (GUS/WHITELIST/KRD)",

    'summary': "Sync Partner data from GUS (Główny Urząd Statystyczny) and validate it with GUS/MF WHITELIST/KRD ",
    'author': 'Trilab',
    'website': "https://trilab.pl",
    'category': 'Accounting',
    'version': '2.2',
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
    'price': 100.0,
    'currency': 'EUR'
}
