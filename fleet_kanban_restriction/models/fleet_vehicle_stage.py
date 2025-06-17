# my_fleet_restrict_stages/models/fleet_vehicle_stage.py
from odoo import fields, models

class FleetVehicleStage(models.Model):
    _inherit = 'fleet.vehicle.stage'

    is_restricted_stage = fields.Boolean(
        string="Etapa Restringida (para arrastrar)",
        help="Si está marcada, el arrastre a esta etapa puede ser restringido para ciertos usuarios."
    )