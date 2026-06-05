from odoo import fields, models

class TruckingRoute(models.Model):
    _name = 'trucking.route'
    _description = 'Trucking Route'

    name = fields.Char(string='Route Name', required=True, help="e.g. Harare to Bulawayo")
    distance = fields.Float(string='Distance (km)')
