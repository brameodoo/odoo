# my_fleet_restrict_stages/models/res_config_settings.py
from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    fleet_restricted_stage_allowed_groups = fields.Many2many(
        'res.groups',
        string="Grupos permitidos para etapas restringidas de Flota",
        config_parameter='fleet_kanban_restriction.allowed_groups_for_restricted_stages',
        help="Los usuarios de estos grupos podrán arrastrar vehículos a etapas marcadas como restringidas."
    )