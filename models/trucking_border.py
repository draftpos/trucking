from odoo import fields, models

class TruckingBorder(models.Model):
    _name = 'trucking.border'
    _description = 'Border Post'
    _order = 'name'

    name = fields.Char(string='Border Name', required=True)
    country_id = fields.Many2one('res.country', string='Country')
