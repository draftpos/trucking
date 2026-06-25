from odoo import api, fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    trucking_default_transporter_type = fields.Selection([
        ('external', 'External Transporter'),
        ('in_house', 'In-House')
    ], string='Default Transporter Type', config_parameter='trucking.default_transporter_type', default='external')

    driver_commission_account_id = fields.Many2one(
        related='company_id.driver_commission_account_id', 
        readonly=False
    )
    driver_commission_journal_id = fields.Many2one(
        related='company_id.driver_commission_journal_id', 
        readonly=False
    )
    receive_fuel_account_id = fields.Many2one(
        related='company_id.receive_fuel_account_id',
        readonly=False
    )
    receive_fuel_journal_id = fields.Many2one(
        related='company_id.receive_fuel_journal_id',
        readonly=False
    )
