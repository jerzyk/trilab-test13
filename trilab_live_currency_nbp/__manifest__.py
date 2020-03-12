# -*- coding: utf-8 -*-

{
    'name': 'Trilab Live Currency Exchange Rate for NBP (Poland)',
    'author': 'Trilab',
    'website': "https://trilab.pl",
    'support': 'odoo@trilab.pl',
    'version': '1.1',
    'category': 'Accounting',
    'summary': """
        Import exchange rates from the Internet. NBP (Polish National Bank)""",
    'description': """
        Module extends built-in live currency module to use NBP (National Polish Bank) REST API to
        download current exchange rates.
        
        It downloads data from table A (middle exchange rates for popular currencies) then (if needed)
        from table B )middle exchange rates for other currencies).
        
        It uses PLN (zł) as a base currency.
        
        Module fetches rate table that is active at the moment of download.

    """,
    'depends': [
        'account',
        'currency_rate_live'
    ],
    'data': [
    ],
    'demo': [
    ],
    'images': [
        'static/description/banner.png'
    ],
    'installable': True,
    'auto_install': True,
    'license': 'OPL-1',
}
