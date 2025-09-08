# __manifest__.py
{
    'name': 'Customer API',
    'version': '17.0.1.0.0',
    'category': 'Website',
    'summary': 'REST API for customer management and e-commerce',
    'description': '''
        This module provides REST API endpoints for:
        - Customer creation and authentication
        - Product listing
        - Shopping cart management
    ''',
    'depends': [
        'base',
        'sale',
        'website',
        'product',
        'portal',
        'website_sale',
        'auth_signup',
    ],
    'data': [
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}