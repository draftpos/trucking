from odoo import models, fields

class TruckingMandatoryField(models.Model):
    _name = 'trucking.mandatory.field'
    _description = 'Trucking Mandatory Field Matrix'

    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    load_type = fields.Selection([
        ('inhouse', 'In-House'),
        ('external', 'External')
    ], string='Load Type', required=True)
    field_id = fields.Many2one('ir.model.fields', string='Field', required=True, ondelete='cascade')
    
    is_save = fields.Boolean(string='Save', default=False)
    is_confirm = fields.Boolean(string='Confirm', default=False)
    is_deliver = fields.Boolean(string='Deliver', default=False)

