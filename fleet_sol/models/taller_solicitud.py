# -*- coding: utf-8 -*-
# models/taller_solicitud.py

from odoo import models, fields, api, _ # Asegúrate de importar _ para traducciones
from odoo.exceptions import UserError
import logging # Importar el módulo de logging

_logger = logging.getLogger(__name__) # ¡Esta línea faltaba o estaba mal colocada!

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
            
            record.state = 'assigned' # Cambiar el estado a 'assigned'

            # --- Lógica para enviar el correo electrónico ---
            try:
                # Buscar la plantilla de correo por su ID externo
                template = self.env.ref('fleet_sol.email_template_solicitud_asignada', raise_if_not_found=False)

                if template:
                    # Enviar el correo usando la plantilla
                    template.send_mail(record.id, force_send=True, raise_exception=True)
                    _logger.info(f"Correo de asignación de fecha enviado para la solicitud {record.name} al analista {record.analista_id.name}.")
                else:
                    _logger.warning("No se encontró la plantilla de correo 'fleet_sol.email_template_solicitud_asignada'. "
                                    "Asegúrate de que el archivo XML de la plantilla esté cargado y el ID sea correcto.")
            except Exception as e:
                _logger.error(f"Error al enviar el correo de asignación de fecha para la solicitud {record.name}: {e}")
                # Opcional: Mostrar un UserError si quieres que el usuario vea el problema en la interfaz
                # raise UserError(_("No se pudo enviar el correo de notificación: %s") % e)

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
