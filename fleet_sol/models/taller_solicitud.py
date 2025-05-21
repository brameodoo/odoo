from odoo import models, fields, api
from odoo.exceptions import UserError

class TallerSolicitud(models.Model):
    _name = 'taller.solicitud'
    _description = 'Solicitud de Taller'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Referencia',
        required=True,
        copy=False,
        readonly=True,
        index=True,
        default='New'
    )
    analista_id = fields.Many2one(
        'hr.employee',
        string='Analista',
        required=True,
        default=lambda self: self.env.user.employee_id
    )
    vehiculo_id = fields.Many2one(
        'fleet.vehicle',
        string='Vehículo',
        required=True
    )
    descripcion_falla = fields.Text(
        string='Descripción de la Falla',
        required=True
    )
    telefono_analista = fields.Char(
        related='analista_id.work_phone',
        string='Teléfono del Analista',
        readonly=True
    )
    fecha_solicitud = fields.Datetime(
        string='Fecha de Solicitud',
        default=fields.Datetime.now,
        readonly=True
    )
    fecha_asignacion = fields.Datetime(
        string='Fecha de Asignación'
    )
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('confirmed', 'Confirmado'),
        ('cancel', 'Cancelado')
    ], string='Estado', default='draft', tracking=True)

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('taller.solicitud') or 'New'
        return super().create(vals)

    def action_confirmar(self):
        for record in self:
            if record.state != 'draft':
                raise UserError("Solo puedes confirmar solicitudes en estado Borrador.")
            record.state = 'confirmed'

    def action_cancelar(self):
        for record in self:
            if record.state == 'cancel':
                raise UserError("La solicitud ya está cancelada.")
            record.state = 'cancel'
