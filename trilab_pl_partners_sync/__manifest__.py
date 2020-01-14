# noinspection PyStatementEffect
{
    'name': "Trilab Partners Sync for Poland",

    'summary': "Sync Partner data from GUS (Główny Urząd Statystyczny) and validate it with ",
    'author': 'Trilab',
    'website': "https://trilab.pl",
    'category': 'Accounting',
    'version': '1.5',
    'depends': [
        'base',
        'contacts'
    ],
    'external_dependencies': {
        'python': ['gusregon', 'zeep']
    },
    'data': [
        'views/res_config_settings.xml',
        'views/res_partner.xml'
    ],
    'images': [
        'static/description/banner.png'
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'OPL-1',
    'price': 20.0,
    'currency': 'EUR'
}
