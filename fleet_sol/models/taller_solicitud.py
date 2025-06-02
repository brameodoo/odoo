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
        string='Fecha de Asignación',
        tracking=True
    )
    fecha_ingreso_taller = fields.Datetime(
        string='Fecha de Ingreso a Taller',
        tracking=True
    )
    fecha_reparacion_terminada = fields.Datetime(
        string='Fecha de Reparación Terminada',
        tracking=True
    )
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('assigned', 'Fecha Asignada'),
        ('in_workshop', 'Ingreso a Taller'),
        ('repaired', 'Reparado'),
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
                raise UserError("Solo puedes asignar fecha a solicitudes en estado Borrador.")
            record.state = 'assigned'

    def action_ingresar_taller(self):
        for record in self:
            if record.state != 'assigned':
                raise UserError("Solo puedes marcar como 'Ingreso a Taller' solicitudes con fecha asignada.")
            record.state = 'in_workshop'
            record.fecha_ingreso_taller = fields.Datetime.now()

    def action_reparado(self):
        for record in self:
            if record.state != 'in_workshop':
                raise UserError("Solo puedes marcar como 'Reparado' solicitudes que han ingresado al taller.")
            record.state = 'repaired'
            record.fecha_reparacion_terminada = fields.Datetime.now()

    def action_cancelar(self):
        for record in self:
            if record.state == 'cancel':
                raise UserError("La solicitud ya está cancelada.")
            record.state = 'cancel'
