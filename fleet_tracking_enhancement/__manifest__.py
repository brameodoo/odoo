# -*- coding: utf-8 -*-
{
    'name': "Fleet Tracking Enhancement",
    'summary': """
        Añade seguimiento de cambios al Chatter para campos específicos del módulo Fleet.
    """,
    'description': """
        Este módulo extiende el modelo fleet.vehicle para habilitar el seguimiento
        de cambios en campos como 'location' y otros en el Chatter.
    """,
    'author': "Brame Telecom",
    'website': "http://www.grupobrame.com",
    'category': 'Fleet',
    'version': '1.0',
    'depends': ['fleet'],
    'data': [
        'views/fleet_vehicle_inherit_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}