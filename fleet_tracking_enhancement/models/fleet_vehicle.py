# -*- coding: utf-8 -*-

from odoo import models, fields

class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'

    location = fields.Char(string='Location', tracking=True)
    vin_sn = fields.Char(string='vin_sn', tracking=True)
    x_studio_distrito = fields.Char(string='x_studio_distrito', tracking=True)
    category_id = fields.Many2one(string='category_id', tracking=True)
    # Añade aquí otros campos que quieras rastrear
    # Ejemplo:
    # manager_id = fields.Many2one('res.users', string='Manager', tracking=True)
    # vin_sn = fields.Char(string='VIN/SN', tracking=True)