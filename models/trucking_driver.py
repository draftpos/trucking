from odoo import api, fields, models

class TruckingDriver(models.Model):
    _name = 'trucking.driver'
    _description = 'Trucking Driver'

    name = fields.Char(string='Driver Name', required=True)
    phone = fields.Char(string='Phone Number')
    address = fields.Text(string='Address')
    license_number = fields.Char(string='License Number')
    active = fields.Boolean(default=True)
