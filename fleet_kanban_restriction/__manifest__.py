# my_fleet_restrict_stages/__manifest__.py
{
    'name': 'Fleet Kanban Stage Restrictions',
    'version': '17.0.1.0.0',
    'category': 'Fleet',
    'summary': 'Restricts drag and drop of vehicles in Kanban view based on stage and user groups.',
    'author': 'Brame Telecom & Geminy',
    'website': 'www.grupobrame.com',
    'depends': ['fleet', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/fleet_vehicle_stage.xml',  # Para el nuevo campo en la etapa
        'views/fleet_vehicle_views.xml',
        'views/fleet_restrict_stage_settings_views.xml', # Opcional: si creas una vista de configuración
    ],
    'assets': {
        'web.assets_backend': [
            'fleet_kanban_restriction/static/src/js/fleet_kanban_controller.js',
            'fleet_kanban_restriction/static/src/xml/fleet_kanban_templates.xml',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}