# -*- coding: utf-8 -*-
from odoo import models, fields, api

# -----------------------------------------------------------------
# MODELO DE LÍNEAS DE PAGO
# -----------------------------------------------------------------
class AdeudoConvenioLineaPago(models.Model):
    _name = 'adeudo.convenio.linea_pago'
    _description = 'Línea de Pago Quincenal del Convenio'
    _order = 'fecha_pago, numero_pago' # Ordenar por fecha y luego número

    convenio_id = fields.Many2one('adeudo.convenio', string='Convenio', ondelete='cascade')
    currency_id = fields.Many2one('res.currency', string='Moneda', related='convenio_id.currency_id')
    
    numero_pago = fields.Integer(string='Pago #', readonly=True)
    fecha_pago = fields.Date(string='Fecha de Pago')
    monto = fields.Monetary(string='Monto del Pago')
    estado_pago = fields.Selection([
        ('pendiente', 'Pendiente'),
        ('pagado', 'Pagado'),
        ('omitido', 'Omitido')
    ], string='Estado del Pago', default='pendiente', tracking=True)
    comentario = fields.Text(string='Comentario')

    # Al cambiar el estado de una línea, forzamos el recálculo de totales en el convenio
    @api.onchange('estado_pago')
    def _onchange_estado_pago(self):
        """
        Cuando se marca una línea como 'pagado' o 'pendiente', 
        le avisamos al convenio que debe recalcular sus totales.
        """
        # Esta función se dispara "onchange", por lo que usamos self.convenio_id
        # para acceder al registro 'padre' que se está editando en la vista.
        if self.convenio_id:
             # Disparar el cómputo de totales (debe ser llamado en el objeto)
            self.convenio_id._compute_totales()

    @api.model_create_multi
    def create(self, vals_list):
        """
        Al crear una línea, disparamos el recálculo.
        """
        res = super(AdeudoConvenioLineaPago, self).create(vals_list)
        # Usamos un bucle por si se crean líneas en convenios distintos
        for convenio in res.mapped('convenio_id'):
            convenio._compute_totales()
        return res

    def write(self, vals):
        """
        Al editar (pagar/omitir) una línea, disparamos el recálculo.
        """
        convenios = self.mapped('convenio_id') # Obtenemos los convenios antes del cambio
        res = super(AdeudoConvenioLineaPago, self).write(vals)
        for convenio in convenios:
            convenio._compute_totales() # Recalculamos
        return res

    def unlink(self):
        """
        Al borrar una línea, disparamos el recálculo.
        """
        convenios = self.mapped('convenio_id')
        res = super(AdeudoConvenioLineaPago, self).unlink()
        for convenio in convenios:
            convenio._compute_totales()
        return res

