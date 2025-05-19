# -*- coding: utf-8 -*-

from odoo import models, fields

class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'

    location = fields.Char(string='Location', tracking=True)
    vin_sn = fields.Char(string='vin_sn', tracking=True)
    x_studio_distrito = fields.Char(string='x_studio_distrito', tracking=True)
    category_id = fields.Many2one(string='category_id', tracking=True)
    mobility_card = fields.Char(string='mobility_card', tracking=True)
    next_assignation_date = fields.Date(string='next_assignation_date', tracking=True)
    order_date = fields.Date(string='order_date', tracking=True)
    acquisition_date = fields.Date(string= 'acquisition_date', tracking=True)
    odometer = fields.Float(string='odometer', tracking=True)
    manager_id = fields.Many2one(string='manager_id', tracking=True)
    # Añade aquí otros campos que quieras rastrear
    # Ejemplo:
    # manager_id = fields.Many2one('res.users', string='Manager', tracking=True)
    # vin_sn = fields.Char(string='VIN/SN', tracking=True)
