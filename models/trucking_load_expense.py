from odoo import api, fields, models, _
from odoo.exceptions import UserError

class TruckingLoadExpense(models.Model):
    _name = 'trucking.load.expense'
    _description = 'Trucking Load Expense'

    load_id = fields.Many2one('trucking.load', string='Load', required=True, ondelete='cascade')
    account_id = fields.Many2one('account.account', string='Account Name', required=True, domain="[('account_type', 'in', ['expense', 'expense_depreciation', 'expense_direct_cost'])]")
    supplier_id = fields.Many2one('res.partner', string='Supplier', required=True, domain="[('is_supplier', '=', True)]")
    amount = fields.Monetary(string='Amount', currency_field='currency_id', default=lambda self: None)
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    doc_no = fields.Char(string='Doc No')
    journal_id = fields.Many2one('account.journal', string='Cash/Bank', domain="[('type', 'in', ('bank', 'cash'))]")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('paid', 'Paid')
    ], string='Status', default='draft', readonly=True)
    
    currency_id = fields.Many2one('res.currency', related='load_id.currency_id', readonly=True)
    company_id = fields.Many2one('res.company', related='load_id.company_id', readonly=True)

    move_id = fields.Many2one('account.move', string='Vendor Bill', readonly=True)
    payment_id = fields.Many2one('account.payment', string='Payment', readonly=True)

    def action_create_expense(self):
        for rec in self:
            if rec.state != 'draft':
                continue
            if rec.amount <= 0 or not rec.journal_id:
                continue
            # Create HR Expense
            employee = self.env.user.employee_id
            if not employee:
                employee = self.env['hr.employee'].search([], limit=1)
                
            product = self.env['product.product'].search([('default_code', '=', 'TRK_EXP')], limit=1)
            if not product:
                product = self.env['product.product'].create({
                    'name': 'Trucking Expense',
                    'default_code': 'TRK_EXP',
                    'can_be_expensed': True,
                    'type': 'service',
                })
                
            # 1. Analytic Account from Truck Reg
            analytic_dict = False
            truck_reg = rec.load_id.vehicle_id.reg_number if rec.load_id.vehicle_id else False
            if truck_reg:
                analytic_acc = self.env['account.analytic.account'].search([('name', '=', truck_reg)], limit=1)
                if not analytic_acc:
                    analytic_plan = self.env['account.analytic.plan'].search([], limit=1)
                    analytic_acc = self.env['account.analytic.account'].create({
                        'name': truck_reg,
                        'plan_id': analytic_plan.id if analytic_plan else False,
                    })
                analytic_dict = {str(analytic_acc.id): 100}

            expense_vals = {
                'name': rec.doc_no or f"Expense for Load {rec.load_id.name} ({rec.supplier_id.name})",
                'employee_id': employee.id if employee else False,
                'date': rec.date,
                'total_amount': rec.amount,
                'product_id': product.id,
                'account_id': rec.account_id.id,
                'payment_mode': 'company_account',
                'analytic_distribution': analytic_dict,
                'journal_id': rec.journal_id.id if rec.journal_id else False,
            }
            hr_exp = self.env['hr.expense'].create(expense_vals)
            
            # Prevent infinite recursion by changing state before calling actions
            rec.write({'state': 'paid'})

            # Submit, Approve, and Post directly on hr.expense
            hr_exp_sudo = hr_exp.sudo()
            if hasattr(hr_exp_sudo, 'action_submit'):
                hr_exp_sudo.action_submit()
            if hasattr(hr_exp_sudo, 'action_approve'):
                hr_exp_sudo.action_approve()
            if hasattr(hr_exp_sudo, 'action_post'):
                hr_exp_sudo.action_post()

            rec.move_id = hr_exp.account_move_id.id if hasattr(hr_exp, 'account_move_id') else False
            if rec.move_id and rec.move_id.state == 'draft':
                if analytic_dict:
                    for line in rec.move_id.line_ids:
                        line.analytic_distribution = analytic_dict
                rec.move_id.action_post()

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if rec.state == 'draft' and rec.amount > 0 and rec.journal_id:
                rec.action_create_expense()
        return records

    def write(self, vals):
        res = super().write(vals)
        if 'state' not in vals:
            for rec in self:
                if rec.state == 'draft' and rec.amount > 0 and rec.journal_id:
                    rec.action_create_expense()
        return res
