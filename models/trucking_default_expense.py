from odoo import api, fields, models

class TruckingDefaultExpense(models.Model):
    _name = 'trucking.default.expense'
    _description = 'Default Trucking Expense'

    account_id = fields.Many2one('account.account', string='Account Name', required=True, domain="[('account_type', 'in', ['expense', 'expense_depreciation', 'expense_direct_cost'])]")
    supplier_id = fields.Many2one('res.partner', string='Supplier', required=True, domain="[('is_supplier', '=', True)]")
    journal_id = fields.Many2one('account.journal', string='Cash/Bank', domain="[('type', 'in', ('bank', 'cash'))]")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
