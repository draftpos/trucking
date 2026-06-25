from odoo import api, fields, models

class ResCompany(models.Model):
    _inherit = 'res.company'

    driver_commission_account_id = fields.Many2one(
        'account.account', 
        string='Driver Commission Account',
        domain="[('account_type', 'in', ['expense', 'expense_depreciation', 'expense_direct_cost'])]"
    )
    driver_commission_journal_id = fields.Many2one(
        'account.journal', 
        string='Driver Commission Journal',
        domain="[('type', 'in', ['bank', 'cash'])]"
    )
    receive_fuel_account_id = fields.Many2one(
        'account.account',
        string='Receive Fuel Account',
    )
    receive_fuel_journal_id = fields.Many2one(
        'account.journal',
        string='Receive Fuel Journal',
        domain="[('type', 'in', ['general', 'bank', 'cash'])]"
    )
