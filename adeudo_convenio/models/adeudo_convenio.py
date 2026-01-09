# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from math import ceil
from datetime import date, timedelta
import calendar
import base64

try:
    from num2words import num2words
except ImportError:
    num2words = None

MAX_DESCUENTO_QUINCENAL = 1240.00

class AdeudoConvenio(models.Model):
    _name = 'adeudo.convenio'
    _description = 'Convenio de Adeudo de Empleado (Final)'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Folio', required=True, copy=False, readonly=True, default='Nuevo')
    
    # --- INFORMACIÓN GENERAL ---
    employee_id = fields.Many2one('hr.employee', string='Colaborador', required=True, tracking=True)
    
    # NUEVO: Puesto del colaborador (Relacionado)
    job_id = fields.Many2one(
        'hr.job', 
        string='Puesto', 
        related='employee_id.job_id', 
        readonly=True, 
        store=True
    )

    # NUEVO: Estatus del colaborador
    estatus_colaborador = fields.Selection([
        ('activo', 'Activo'),
        ('baja', 'Baja')
    ], string='Estatus del Colaborador', default='activo', tracking=True, required=True)

    numero_empleado = fields.Char(
        string='Número de Empleado', 
        related='employee_id.barcode', 
        readonly=False, 
        store=True,
        help="Número de empleado o credencial."
    )

    responsable_id = fields.Many2one(
        'hr.employee', 
        string='Responsable del Colaborador', 
        related='employee_id.parent_id', 
        store=True, 
        readonly=False
    )
    analista_id = fields.Many2one('res.users', string='Analista Responsable', default=lambda self: self.env.user, tracking=True)
    
    motivo = fields.Selection([
        ('herramientas', 'Herramientas'),
        ('vehicular', 'Vehicular'),
        ('prontos_pagos', 'Prontos Pagos'),
        ('almacen_sap', 'Almacén SAP'),
        ('excedente_materiales', 'Excedente de Materiales'),
        ('recolecciones', 'recolecciones')
    ], string='Motivo del Adeudo', required=True, tracking=True)

    distrito = fields.Selection([
        ('TLALNEPANTLA', 'TLALNEPANTLA'),
        ('MULTIREGION - SURPONIENTE', 'MULTIREGION - SURPONIENTE'),
        ('MULTIREGION - METRONOT', 'MULTIREGION - METRONOT'),
        ('MULTIREGION - NORPONIENTE', 'MULTIREGION - NORPONIENTE'),
        ('MULTIREGION - GUADALAJARA', 'MULTIREGION - GUADALAJARA'),
        ('CUADRILLAS VIP', 'CUADRILLAS VIP'),
        ('PE AEROPUERTO', 'PE AEROPUERTO'),
        ('PE SENDERO DIVISORIO', 'PE SENDERO DIVISORIO'),
        ('PE AGUASCALIENTES', 'PE AGUASCALIENTES'),
        ('PE SAN LUIS POTOSÍ', 'PE SAN LUIS POTOSÍ'),
        ('PE BARRANCA', 'PE BARRANCA'),
        ('PE COLOMOS', 'PE COLOMOS'),
        ('PE ESTADIO', 'PE ESTADIO'),
        ('PE LA PRIMAVERA', 'PE LA PRIMAVERA'),
        ('PE LAZARO CARDENAS', 'PE LAZARO CARDENAS'),
        ('PE LOPEZ MATEOS', 'PE LOPEZ MATEOS'),
        ('PE CHAPULTEPEC', 'PE CHAPULTEPEC'),
        ('PE MORELIA', 'PE MORELIA'),
        ('PE ARAGON', 'PE ARAGON'),
        ('PE LA NORIA', 'PE LA NORIA'),
        ('PE CERRO GORDO', 'PE CERRO GORDO'),
        ('PE CELAYA', 'PE CELAYA'),
        ('PE GUANAJUATO', 'PE GUANAJUATO'),
        ('PE IRAPUATO', 'PE IRAPUATO'),
        ('PE QUERÉTARO', 'PE QUERÉTARO'),
        ('CONSTITUCIÓN', 'CONSTITUCIÓN'),
        ('NEZA', 'NEZA'),
        ('AEROPUERTO', 'AEROPUERTO'),
        ('LOS REYES', 'LOS REYES'),
        ('TEXCOCO', 'TEXCOCO'),
        ('TULTITLAN', 'TULTITLAN'),
        ('HUEHUETOCA', 'HUEHUETOCA'),
        ('SANTA FE', 'SANTA FE'),
        ('CONDESA', 'CONDESA'),
        ('LAS AGUILAS', 'LAS AGUILAS'),
        ('PEDREGAL', 'PEDREGAL'),
        ('TLALPAN', 'TLALPAN'),
        ('LERMA', 'LERMA'),
        ('METEPEC', 'METEPEC'),
        ('QUERETARO', 'QUERETARO'),
        ('CELAYA', 'CELAYA'),
        ('GUADALAJARA', 'GUADALAJARA'),
        ('PUERTO VALLARTA', 'PUERTO VALLARTA'),
        ('AGUASCALIENTES', 'AGUASCALIENTES'),
        ('ANGELOPOLIS', 'ANGELOPOLIS')
    ], string='Distrito', required=True, tracking=True)
    
    # --- DETALLES ---
    company_id = fields.Many2one('res.company', string='Compañía', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Moneda', default=lambda self: self.env.company.currency_id, readonly=True)
    monto_total = fields.Monetary(string='Monto Total del Adeudo', required=True, tracking=True)
    fecha_incidencia = fields.Date(string="Fecha Reporte de Incidencia")
    fecha_inicio = fields.Date(string='Fecha de Inicio de Descuento', default=fields.Date.today, required=True)

    # --- CÁLCULOS ---
    monto_descuento_quincenal = fields.Monetary(string='Monto a Descontar por Quincena')
    numero_pagos_manual = fields.Integer(string="Definir Número de Quincenas")
    monto_total_letras = fields.Char(string="Monto en Letras", compute="_compute_monto_total_letras")
    numero_pagos_sugerido = fields.Integer(string='Número de Pagos Sugerido', compute='_compute_numero_pagos', store=True)

    # --- PROGRESO ---
    linea_pago_ids = fields.One2many('adeudo.convenio.linea_pago', 'convenio_id', string='Plan de Pagos')
    total_abonado = fields.Monetary(string='Total Abonado', compute='_compute_totales', store=True)
    monto_pendiente = fields.Monetary(string='Monto Pendiente', compute='_compute_totales', store=True)
    progreso_pago_porcentaje = fields.Float(string="Progreso de Pago", compute='_compute_totales', store=True)

    # --- ESTADO Y DOCUMENTOS ---
    estado = fields.Selection([
        ('borrador', 'Borrador'),
        ('en_proceso', 'En Proceso'),
        ('cerrado', 'Cerrado')
    ], string='Estado', default='borrador', tracking=True, copy=False)
    
    convenio_generado = fields.Binary(string='Convenio Generado', readonly=True)
    convenio_filename = fields.Char(string='Nombre Archivo Convenio', default='convenio.pdf')
    convenio_firmado = fields.Binary(string='Convenio Firmado')
    convenio_firmado_filename = fields.Char(string='Nombre Archivo Firmado')
    
    estado_convenio_firma = fields.Selection([
        ('si', 'Sí'),
        ('no', 'No')
    ], string='¿Firma Autógrafa Generada?', default='no', tracking=True)

    notas = fields.Text(string='Observaciones')
    employee_address = fields.Char(string="Dirección del Empleado", compute='_compute_employee_address')

    # Métodos de cálculo existentes mantenidos para funcionalidad completa...
    @api.depends('employee_id.address_id')
    def _compute_employee_address(self):
        for rec in self:
            addr = rec.employee_id.address_id
            rec.employee_address = f"{addr.street or ''}, {addr.city or ''}" if addr else "N/A"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nuevo') == 'Nuevo':
                vals['name'] = self.env['ir.sequence'].next_by_code('adeudo.convenio') or 'Nuevo'
        return super().create(vals_list)

    @api.depends('monto_total', 'monto_descuento_quincenal')
    def _compute_numero_pagos(self):
        for rec in self:
            if rec.monto_total > 0 and rec.monto_descuento_quincenal > 0:
                rec.numero_pagos_sugerido = ceil(rec.monto_total / rec.monto_descuento_quincenal)
            else:
                rec.numero_pagos_sugerido = 0

    @api.depends('linea_pago_ids.monto', 'linea_pago_ids.estado_pago', 'monto_total')
    def _compute_totales(self):
        for rec in self:
            abonado = sum(line.monto for line in rec.linea_pago_ids if line.estado_pago == 'pagado')
            rec.total_abonado = abonado
            rec.monto_pendiente = rec.monto_total - abonado
            rec.progreso_pago_porcentaje = (abonado / rec.monto_total * 100) if rec.monto_total > 0 else 0

    @api.depends('monto_total', 'currency_id')
    def _compute_monto_total_letras(self):
        for rec in self:
            rec.monto_total_letras = rec.get_monto_en_letras()

    def get_monto_en_letras(self):
        if num2words and self.monto_total:
            return num2words(self.monto_total, lang='es').upper() + " PESOS"
        return "N/A"

    def action_confirmar(self):
        self.write({'estado': 'en_proceso'})

    def action_resetear_borrador(self):
        self.write({'estado': 'borrador'})

    def action_print_report(self):
        return self.env.ref('adeudo_convenio.action_report_adeudo_convenio').report_action(self)

class AdeudoConvenioLineaPago(models.Model):
    _name = 'adeudo.convenio.linea_pago'
    _description = 'Línea de Pago de Adeudo'

    convenio_id = fields.Many2one('adeudo.convenio', ondelete='cascade')
    numero_pago = fields.Integer(string='No. Pago')
    fecha_pago = fields.Date(string='Fecha de Pago')
    monto = fields.Monetary(string='Monto')
    currency_id = fields.Many2one('res.currency', related='convenio_id.currency_id')
    estado_pago = fields.Selection([('pendiente', 'Pendiente'), ('pagado', 'Pagado')], default='pendiente')
    comentario = fields.Char(string='Comentario')
