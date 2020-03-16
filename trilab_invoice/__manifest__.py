# -*- coding: utf-8 -*-

# noinspection PyStatementEffect
{
    'name': 'Trilab Invoice PL',
    'author': 'Trilab',
    'website': "https://trilab.pl",
    'version': '2.5.6',
    'category': 'Accounting',
    'summary': 'Base module to manage invoice in PL',
    'description': '''Base module to manage invoices and invoice correction
    according to Polish law and best practices''',
    'depends': [
        'web',
        'account',
        'sale'
    ],
    'data': [
        'views/web_layout.xml',
        'views/account_move.xml',
        'views/account_move_reversal.xml',
        'views/account_move_views.xml',
    ],
    'images': [
        'static/description/banner.png',
        'static/description/invoice.png'
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'OPL-1',
    'price': 140.0,
    'currency': 'EUR'
}
