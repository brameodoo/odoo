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

# Monto máximo permitido para descuento quincenal según políticas internas
MAX_DESCUENTO_QUINCENAL = 1240.00

class AdeudoConvenio(models.Model):
    _name = 'adeudo.convenio'
    _description = 'Convenio de Adeudo de Empleado'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Folio', required=True, copy=False, readonly=True, default='Nuevo')
    
    # --- INFORMACIÓN DEL COLABORADOR ---
    employee_id = fields.Many2one('hr.employee', string='Colaborador', required=True, tracking=True)
    
    # Campo relacionado para el puesto
    job_id = fields.Many2one(
        'hr.job', 
        string='Puesto', 
        related='employee_id.job_id', 
        readonly=True, 
        store=True
    )

    # Nuevo campo para el estatus del colaborador
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
    
    analista_id = fields.Many2one(
        'res.users', 
        string='Analista Responsable', 
        default=lambda self: self.env.user, 
        tracking=True
    )
    
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
    
    # --- DETALLES ECONÓMICOS ---
    company_id = fields.Many2one('res.company', string='Compañía', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Moneda', default=lambda self: self.env.company.currency_id, readonly=True)
    monto_total = fields.Monetary(string='Monto Total del Adeudo', required=True, tracking=True)
    fecha_incidencia = fields.Date(string="Fecha Reporte de Incidencia")
    fecha_inicio = fields.Date(string='Fecha de Inicio de Descuento', default=fields.Date.today, required=True)

    # --- CÁLCULOS Y PLANIFICACIÓN ---
    monto_descuento_quincenal = fields.Monetary(string='Monto a Descontar por Quincena')
    numero_pagos_manual = fields.Integer(string="Definir Número de Quincenas")
    
    monto_total_letras = fields.Char(string="Monto en Letras", compute="_compute_monto_total_letras")
    numero_pagos_sugerido = fields.Integer(string='Número de Pagos Sugerido', compute='_compute_numero_pagos', store=True)

    # --- LÍNEAS DE PAGO Y PROGRESO ---
    linea_pago_ids = fields.One2many('adeudo.convenio.linea_pago', 'convenio_id', string='Plan de Pagos')
    total_abonado = fields.Monetary(string='Total Abonado', compute='_compute_totales', store=True)
    monto_pendiente = fields.Monetary(string='Monto Pendiente', compute='_compute_totales', store=True)
    progreso_pago_porcentaje = fields.Float(string="Progreso de Pago", compute='_compute_totales', store=True)

    # --- ESTADO Y ARCHIVOS ---
    estado = fields.Selection([
        ('borrador', 'Borrador'),
        ('en_proceso', 'En Proceso'),
        ('cerrado', 'Cerrado')
    ], string='Estado', default='borrador', tracking=True, copy=False)
    
    convenio_generado = fields.Binary(string='Convenio Generado', readonly=True, copy=False)
    convenio_filename = fields.Char(string='Nombre Archivo Convenio', default='convenio.pdf')
    
    convenio_firmado = fields.Binary(string='Convenio Firmado')
    convenio_firmado_filename = fields.Char(string='Nombre Archivo Firmado')
    
    estado_convenio_firma = fields.Selection([
        ('si', 'Sí'),
        ('no', 'No')
    ], string='¿Firma Autógrafa Generada?', default='no', tracking=True)

    notas = fields.Text(string='Observaciones')

    # -----------------------------------------------------------------
    # MÉTODOS DE ACCIÓN (BOTONES)
    # -----------------------------------------------------------------

    def action_generar_plan_pagos(self, auto_confirmar=False):
        """Genera o recalcula el plan de pagos basado en los montos definidos."""
        for rec in self:
            if rec.monto_descuento_quincenal <= 0:
                raise UserError("El monto a descontar por quincena debe ser mayor que cero.")
            
            # 1. Limpiar pagos pendientes previos
            rec.linea_pago_ids.filtered(lambda p: p.estado_pago == 'pendiente').unlink()
            
            monto_adeudado = round(rec.monto_total - rec.total_abonado, 2)
            if monto_adeudado <= 0.01:
                rec.estado = 'cerrado'
                continue

            # 2. Lógica de fechas (quincenas)
            pagos_existentes = rec.linea_pago_ids.sorted('fecha_pago')
            if not pagos_existentes:
                fecha_actual = rec.fecha_inicio
            else:
                ultima_fecha = pagos_existentes[-1].fecha_pago
                if ultima_fecha.day <= 15:
                    last_day = calendar.monthrange(ultima_fecha.year, ultima_fecha.month)[1]
                    fecha_actual = date(ultima_fecha.year, ultima_fecha.month, last_day)
                else:
                    fecha_actual = (ultima_fecha + timedelta(days=20)).replace(day=15)

            # 3. Creación de líneas
            pagos_list = []
            saldo_temp = monto_adeudado
            num_pago = len(pagos_existentes) + 1
            
            while saldo_temp > 0.01:
                monto_pago = min(rec.monto_descuento_quincenal, saldo_temp)
                monto_pago = round(monto_pago, 2)
                
                pagos_list.append({
                    'numero_pago': num_pago,
                    'fecha_pago': fecha_actual,
                    'monto': monto_pago,
                    'estado_pago': 'pendiente',
                    'convenio_id': rec.id
                })
                
                saldo_temp -= monto_pago
                saldo_temp = round(saldo_temp, 2)
                num_pago += 1
                
                # Calcular siguiente quincena
                if fecha_actual.day <= 15:
                    last_day = calendar.monthrange(fecha_actual.year, fecha_actual.month)[1]
                    fecha_actual = date(fecha_actual.year, fecha_actual.month, last_day)
                else:
                    fecha_actual = (fecha_actual + timedelta(days=20)).replace(day=15)

            # 4. Ajuste de picos menores a 500 pesos
            if len(pagos_list) >= 2:
                ultimo = pagos_list[-1]
                if ultimo['monto'] < 500.0:
                    pagos_list[-2]['monto'] = round(pagos_list[-2]['monto'] + ultimo['monto'], 2)
                    pagos_list.pop()

            self.env['adeudo.convenio.linea_pago'].create(pagos_list)
        return True

    def action_confirmar(self):
        """Pasa el convenio a estado En Proceso."""
        for rec in self:
            if not rec.linea_pago_ids:
                rec.action_generar_plan_pagos()
            rec.write({'estado': 'en_proceso'})
        return True

    def action_resetear_borrador(self):
        """Regresa el registro a Borrador."""
        self.write({'estado': 'borrador'})

    def action_print_report(self):
        """Lanza la acción de impresión del reporte."""
        return self.env.ref('adeudo_convenio.action_report_adeudo_convenio').report_action(self)

    # -----------------------------------------------------------------
    # CÁLCULOS COMPUTADOS Y ONCHANGES
    # -----------------------------------------------------------------

    @api.depends('monto_total', 'monto_descuento_quincenal')
    def _compute_numero_pagos(self):
        for rec in self:
            if rec.monto_descuento_quincenal > 0:
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

    @api.depends('monto_total')
    def _compute_monto_total_letras(self):
        for rec in self:
            if num2words and rec.monto_total:
                rec.monto_total_letras = num2words(rec.monto_total, lang='es').upper() + " PESOS"
            else:
                rec.monto_total_letras = "N/A"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nuevo') == 'Nuevo':
                vals['name'] = self.env['ir.sequence'].next_by_code('adeudo.convenio') or 'Nuevo'
        return super().create(vals_list)


class AdeudoConvenioLineaPago(models.Model):
    _name = 'adeudo.convenio.linea_pago'
    _description = 'Detalle de Cuotas de Pago'

    convenio_id = fields.Many2one('adeudo.convenio', ondelete='cascade')
    numero_pago = fields.Integer(string='No. Pago')
    fecha_pago = fields.Date(string='Fecha de Pago')
    monto = fields.Monetary(string='Monto')
    currency_id = fields.Many2one('res.currency', related='convenio_id.currency_id')
    estado_pago = fields.Selection([
        ('pendiente', 'Pendiente'), 
        ('pagado', 'Pagado')
    ], default='pendiente', string='Estado de Pago')
    comentario = fields.Char(string='Comentario')
