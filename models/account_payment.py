from odoo import models, fields, api

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    load_id = fields.Many2one('trucking.load', string='Order Number (Load)', domain="['|', ('transporter_id', '=', partner_id), ('customer_id', '=', partner_id)]")

    @api.depends('journal_id', 'payment_type', 'payment_method_line_id')
    def _compute_outstanding_account_id(self):
        super()._compute_outstanding_account_id()
        for pay in self:
            if not pay.outstanding_account_id and pay.journal_id.default_account_id:
                pay.outstanding_account_id = pay.journal_id.default_account_id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('load_id') and vals.get('partner_id'):
                load = self.env['trucking.load'].browse(vals['load_id'])
                if vals['partner_id'] == load.transporter_id.id:
                    vals['partner_type'] = 'supplier'
                elif vals['partner_id'] == load.customer_id.id:
                    vals['partner_type'] = 'customer'
        return super().create(vals_list)

    def write(self, vals):
        res = super().write(vals)
        for rec in self:
            if rec.load_id and rec.partner_id:
                if rec.partner_id == rec.load_id.transporter_id and rec.partner_type != 'supplier':
                    rec.partner_type = 'supplier'
                elif rec.partner_id == rec.load_id.customer_id and rec.partner_type != 'customer':
                    rec.partner_type = 'customer'
        return res

    @api.onchange('load_id')
    def _onchange_load_id(self):
        if self.load_id:
            self.memo = f"{self.load_id.name}"

    def action_post(self):
        for rec in self:
            from_invoice = self.env.context.get('active_model') == 'account.move'
            if rec.partner_type == 'supplier' and not rec.load_id and not self.env.context.get('ignore_load_warning') and not from_invoice:
                return {
                    'name': 'Missing Order Number',
                    'type': 'ir.actions.act_window',
                    'res_model': 'payment.load.warning.wizard',
                    'view_mode': 'form',
                    'target': 'new',
                    'context': {'default_payment_id': rec.id}
                }
        res = super().action_post()
        for rec in self:
            if not rec.load_id:
                continue

            if rec.partner_type == 'supplier' and rec.load_id.transporter_bill_id and rec.load_id.transporter_bill_id.state == 'posted':
                bill = rec.load_id.transporter_bill_id
                payable_account = bill.line_ids.filtered(lambda l: l.account_id.account_type == 'liability_payable')
                if payable_account:
                    payable_account = payable_account[0].account_id
                    if not rec.move_id:
                        continue
                    payment_lines = rec.move_id.line_ids.filtered(lambda l: l.account_id == payable_account and not l.reconciled)
                    for line in payment_lines:
                        bill_lines = bill.line_ids.filtered(lambda l: l.account_id == payable_account and not l.reconciled)
                        if bill_lines:
                            try:
                                (bill_lines[0] | line).reconcile()
                            except Exception as e:
                                import logging
                                logging.getLogger(__name__).error(f"Reconciliation error: {e}")
                            pass
                            
            if rec.partner_type == 'customer' and rec.load_id.invoice_id and rec.load_id.invoice_id.state == 'posted':
                invoice = rec.load_id.invoice_id
                receivable_account = invoice.line_ids.filtered(lambda l: l.account_id.account_type == 'asset_receivable')
                if receivable_account:
                    receivable_account = receivable_account[0].account_id
                    payment_lines = rec.move_id.line_ids.filtered(lambda l: l.account_id == receivable_account and not l.reconciled)
                    for line in payment_lines:
                        inv_lines = invoice.line_ids.filtered(lambda l: l.account_id == receivable_account and not l.reconciled)
                        if inv_lines:
                            try:
                                (inv_lines[0] | line).reconcile()
                            except Exception as e:
                                import logging
                                logging.getLogger(__name__).error(f"Reconciliation error: {e}")
                            pass
        return res
