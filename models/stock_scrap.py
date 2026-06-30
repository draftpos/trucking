from odoo import fields, models

class StockScrap(models.Model):
    _inherit = 'stock.scrap'

    trucking_load_id = fields.Many2one('trucking.load', string="Trucking Load")
    supplier_id = fields.Many2one('res.partner', string="Supplier")
