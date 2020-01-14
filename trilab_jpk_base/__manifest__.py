# -*- coding: utf-8 -*-
# noinspection PyStatementEffect
{
    'name': "Trilab JPK Base",

    'summary': """
        Base module used by all Trilab JPK modules. 
    """,

    'description': """
    Base module used by all Trilab JPK modules, provides basic data dictionaries and necessary extensions.
""",

    'author': "Trilab",
    'website': "https://trilab.pl",

    'category': 'Accounting',
    'version': '1.4.2',

    'depends': ['base', 'account'],

    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/data.xml',
        'views/menu.xml',
        'views/jpk_document_type.xml',
        'views/res_company_views.xml',
        'views/account_move_views.xml'
    ],
    'demo': [],
    'images': [
        'static/description/banner.png'
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'OPL-1',
    'post_init_hook': 'post_init_handler',
    'uninstall_hook': 'uninstall_handler',
}
