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
    
    # Campos solicitados integrados correctamente
    job_id = fields.Many2one(
        'hr.job', 
        string='Puesto', 
        related='employee_id.job_id', 
        readonly=True, 
        store=True
    )

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
    fecha_incidencia = fields.Date(string="Fecha Reporte de Incidencia", help="Fecha en que se reportó el incidente.")
    fecha_inicio = fields.Date(string='Fecha de Inicio de Descuento', default=fields.Date.today, required=True)

    # --- CÁLCULOS ---
    monto_descuento_quincenal = fields.Monetary(string='Monto a Descontar por Quincena', help="Monto quincenal.")
    numero_pagos_manual = fields.Integer(string="Definir Número de Quincenas", help="Opcional: Define un número de quincenas.")
    
    monto_total_letras = fields.Char(string="Monto en Letras", compute="_compute_monto_total_letras", store=False)
    numero_pagos_sugerido = fields.Integer(string='Número de Pagos Sugerido', compute='_compute_numero_pagos', store=True)

    # --- PROGRESO ---
    linea_pago_ids = fields.One2many('adeudo.convenio.linea_pago', 'convenio_id', string='Plan de Pagos')
    total_abonado = fields.Monetary(string='Total Abonado', compute='_compute_totales', store=True)
    monto_pendiente = fields.Monetary(string='Monto Pendiente', compute='_compute_totales', store=True)
    progreso_pago_porcentaje = fields.Float(string="Progreso de Pago", compute='_compute_totales', store=True, group_operator="avg")

    # --- ESTADO Y DOCUMENTOS ---
    estado = fields.Selection([
        ('borrador', 'Borrador'),
        ('en_proceso', 'En Proceso'),
        ('cerrado', 'Cerrado')
    ], string='Estado', default='borrador', tracking=True, copy=False)
    
    convenio_generado = fields.Binary(string='Convenio Generado', readonly=True, copy=False)
    convenio_filename = fields.Char(string='Nombre Archivo Convenio', default='convenio.pdf', copy=False)
    
    convenio_firmado = fields.Binary(string='Convenio Firmado', copy=False)
    convenio_firmado_filename = fields.Char(string='Nombre Archivo Firmado', copy=False)
    
    estado_convenio_firma = fields.Selection([
        ('si', 'Sí'),
        ('no', 'No')
    ], string='¿Firma Autógrafa Generada?', default='no', tracking=True)

    notas = fields.Text(string='Observaciones')
    employee_address = fields.Char(string="Dirección del Empleado", compute='_compute_employee_address')

    # -----------------------------------------------------------------
    # COMPUTADOS Y ONCHANGE
    # -----------------------------------------------------------------

    @api.depends('employee_id.address_id', 'employee_id.work_location_id')
    def _compute_employee_address(self):
        for rec in self:
            employee = rec.employee_id
            if not employee:
                rec.employee_address = ""
                continue
            address = employee.address_id or (employee.user_id.partner_id if employee.user_id else None)
            if address:
                parts = [address.street, address.street2, address.city, address.state_id.name, address.zip, address.country_id.name]
                rec.employee_address = ", ".join(filter(None, parts))
            else:
                rec.employee_address = employee.work_location_id.display_name or "Dirección no especificada"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nuevo') == 'Nuevo':
                vals['name'] = self.env['ir.sequence'].next_by_code('adeudo.convenio') or 'Nuevo'
        return super(AdeudoConvenio, self).create(vals_list)

    @api.onchange('fecha_incidencia')
    def _onchange_fecha_incidencia(self):
        if self.fecha_incidencia:
            dia = self.fecha_incidencia.day
            mes = self.fecha_incidencia.month
            ano = self.fecha_incidencia.year
            if dia <= 15:
                self.fecha_inicio = date(ano, mes, 15)
            else:
                ultimo_dia = calendar.monthrange(ano, mes)[1]
                self.fecha_inicio = date(ano, mes, ultimo_dia)

    @api.constrains('fecha_inicio')
    def _check_fecha_inicio_quincena(self):
        for rec in self:
            if rec.fecha_inicio:
                dia = rec.fecha_inicio.day
                ultimo_dia = calendar.monthrange(rec.fecha_inicio.year, rec.fecha_inicio.month)[1]
                if dia not in [15, ultimo_dia]:
                    raise ValidationError("La fecha de inicio de descuento debe ser el día 15 o el último día del mes.")

    @api.onchange('monto_total')
    def _onchange_monto_total(self):
        if self.monto_total > 0:
            self.monto_descuento_quincenal = min(self.monto_total, MAX_DESCUENTO_QUINCENAL)
        else:
            self.monto_descuento_quincenal = 0

    @api.onchange('numero_pagos_manual')
    def _onchange_numero_pagos_manual(self):
        if self.numero_pagos_manual > 0 and self.monto_total > 0:
            self.monto_descuento_quincenal = round(self.monto_total / self.numero_pagos_manual, 2)
        elif self.monto_total > 0:
            self._onchange_monto_total()

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
            
            if rec.monto_total > 0:
                rec.progreso_pago_porcentaje = (abonado / rec.monto_total) * 100
            else:
                rec.progreso_pago_porcentaje = 0
            
            if rec.monto_pendiente <= 0.01 and rec.estado == 'en_proceso' and rec.monto_total > 0:
                rec.estado = 'cerrado'

    @api.depends('monto_total', 'currency_id')
    def _compute_monto_total_letras(self):
        for rec in self:
            rec.monto_total_letras = rec.get_monto_en_letras()

    # -----------------------------------------------------------------
    # ACCIONES Y LÓGICA DE PAGO (CON AJUSTE DE FECHAS Y PICOS)
    # -----------------------------------------------------------------

    def action_confirmar(self):
        for rec in self:
            if not rec.linea_pago_ids:
                rec.action_generar_plan_pagos(auto_confirmar=False)
            
            # Generar el PDF y guardarlo antes de cambiar de estado
            report = self.env.ref('adeudo_convenio.action_report_adeudo_convenio')
            pdf_content, content_type = report.sudo()._render_qweb_pdf(report.report_name, res_ids=rec.ids)
            
            rec.write({
                'estado': 'en_proceso',
                'convenio_generado': base64.b64encode(pdf_content),
                'convenio_filename': f"Convenio_{rec.name.replace('/', '_')}.pdf"
            })
        return True

    def action_resetear_borrador(self):
        self.write({'estado': 'borrador'})

    def action_generar_plan_pagos(self, auto_confirmar=True):
        for rec in self:
            if rec.monto_descuento_quincenal <= 0:
                raise UserError("El monto a descontar por quincena debe ser mayor que cero.")
            
            # 1. Eliminar pagos pendientes anteriores
            rec.linea_pago_ids.filtered(lambda p: p.estado_pago == 'pendiente').unlink()
            
            # Calcular el monto restante
            monto_adeudado_restante = round(rec.monto_total - rec.total_abonado, 2)
            
            if monto_adeudado_restante <= 0.01:
                rec.estado = 'cerrado'
                continue

            # 2. Determinar la fecha EXACTA del primer pago
            pagos_existentes = rec.linea_pago_ids.sorted('fecha_pago')
            
            if not pagos_existentes:
                fecha_actual = rec.fecha_inicio
            else:
                ultima_fecha = pagos_existentes[-1].fecha_pago
                if ultima_fecha.day <= 15:
                    last_day = calendar.monthrange(ultima_fecha.year, ultima_fecha.month)[1]
                    fecha_actual = date(ultima_fecha.year, ultima_fecha.month, last_day)
                else:
                    next_date = ultima_fecha + timedelta(days=20)
                    fecha_actual = date(next_date.year, next_date.month, 15)

            # 3. Generar pagos en memoria
            pagos_preliminares = []
            saldo_temp = monto_adeudado_restante
            num_pago = len(pagos_existentes) + 1
            
            while saldo_temp > 0.01:
                monto_pago = min(rec.monto_descuento_quincenal, saldo_temp)
                monto_pago = round(monto_pago, 2)
                
                pagos_preliminares.append({
                    'numero_pago': num_pago,
                    'fecha_pago': fecha_actual,
                    'monto': monto_pago,
                    'estado_pago': 'pendiente',
                    'convenio_id': rec.id
                })
                
                saldo_temp -= monto_pago
                saldo_temp = round(saldo_temp, 2)
                num_pago += 1
                
                if fecha_actual.day <= 15:
                    last_day = calendar.monthrange(fecha_actual.year, fecha_actual.month)[1]
                    fecha_actual = date(fecha_actual.year, fecha_actual.month, last_day)
                else:
                    next_date = fecha_actual + timedelta(days=20)
                    fecha_actual = date(next_date.year, next_date.month, 15)

            # 4. AJUSTE DE "PICOS" (< 500 pesos)
            if len(pagos_preliminares) >= 2:
                ultimo_pago = pagos_preliminares[-1]
                if ultimo_pago['monto'] < 500.0:
                    penultimo_pago = pagos_preliminares[-2]
                    penultimo_pago['monto'] += ultimo_pago['monto']
                    penultimo_pago['monto'] = round(penultimo_pago['monto'], 2)
                    pagos_preliminares.pop()

            # 5. Crear registros
            self.env['adeudo.convenio.linea_pago'].create(pagos_preliminares)
            
            if rec.estado == 'borrador' and auto_confirmar:
                rec.action_confirmar()
                
        return True

    # -----------------------------------------------------------------
    # MÉTODOS PARA EL REPORTE QWEB (RESTABLECIDOS)
    # -----------------------------------------------------------------

    def get_monto_en_letras(self):
        """Convierte el monto total a texto para el reporte."""
        self.ensure_one()
        if num2words:
            try:
                pesos = int(self.monto_total)
                centavos = int(round((self.monto_total - pesos) * 100))
                texto_pesos = num2words(pesos, lang='es').upper()
                currency_name = self.currency_id.name.upper() or 'PESOS M.N.'
                if currency_name == 'MXN':
                    currency_name = 'PESOS M.N.'
                return f"{texto_pesos} {currency_name} {centavos:02d}/100"
            except Exception as e:
                return f"ERROR: {e}"
        else:
            return "BIBLIOTECA 'num2words' NO INSTALADA"

    def get_motivo_display(self):
        """Obtiene la etiqueta legible del motivo."""
        self.ensure_one()
        return dict(self._fields['motivo'].selection).get(self.motivo, '')

    def get_fecha_reporte(self):
        """Formatea la fecha para el reporte."""
        self.ensure_one()
        report_date = self.fecha_incidencia or self.create_date or date.today()
        return f"{report_date.day} de {report_date.strftime('%B')} del {report_date.year}"

    # -----------------------------------------------------------------
    # OTROS MÉTODOS
    # -----------------------------------------------------------------

    def action_print_report(self):
        """Lanza la acción de impresión del reporte."""
        return self.env.ref('adeudo_convenio.action_report_adeudo_convenio').report_action(self)


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
