# -*- coding: utf-8 -*-
# noinspection PyStatementEffect
{
    'name': "Trilab JPK VAT",

    'summary': """
        Generate JPK VAT XML
        """,

    'description': """
        Report and generate XML for JPK (Jednolity Plik Kontrolny) required for accounting reporting in Poland
    """,

    'author': "Trilab",
    'website': "https://trilab.pl",

    'category': 'Accounting',
    'version': '1.9',

    'depends': ['base', 'account', 'account_reports', 'trilab_jpk_base'],

    'data': [
        'data/jpk.xml',
        'data/trilab_vat_reports.xml',
        'views/views.xml',
        'views/account.xml',
    ],
    'images': [
        'static/description/banner.png'
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'OPL-1',
    'price': 240.0,
    'currency': 'EUR'

}
