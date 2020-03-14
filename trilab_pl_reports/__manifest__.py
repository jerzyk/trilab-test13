# -*- coding: utf-8 -*-
# noinspection PyStatementEffect
{
    'name': "Trilab PL Financial Reports",

    'summary': """
        Trilab PL Financial Reports: Balance and P&L
        """,

    'description': """
        Structure for the financial reports Balance and P&L according to polish account rules and in accordance
         to electronic reports for IRS.
    """,

    'author': "Trilab",
    'website': "https://trilab.pl",

    'category': 'Accounting',
    'version': '1.0',

    'depends': ['account_accountant'],

    'data': [
        'data/trilab_financial_reports.xml',
    ],
    'images': [
        'static/description/banner.png'
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'OPL-1'
}
