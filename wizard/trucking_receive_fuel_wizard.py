from odoo import api, fields, models, _
from odoo.exceptions import UserError

class TruckingReceiveFuelWizard(models.TransientModel):
    _name = 'trucking.receive.fuel.wizard'
    _description = 'Receive Fuel Wizard'

    load_id = fields.Many2one('trucking.load', string='Load', required=True)
    qty = fields.Float(string='Fuel QTY (Litres)', required=True, default=0.0)
    cost_price = fields.Float(string='Rate', required=True, default=1.20)
    amount = fields.Monetary(string='Amount', compute='_compute_amount', currency_field='currency_id', store=True)
    currency_id = fields.Many2one(related='load_id.currency_id')
    allow_supplier = fields.Boolean(related='load_id.company_id.trucking_allow_supplier_on_issue_fuel')
    supplier_id = fields.Many2one('res.partner', string='Supplier', domain="[('contact_type', '=', 'supplier')]")


    @api.depends('qty', 'cost_price')
    def _compute_amount(self):
        for rec in self:
            rec.amount = rec.qty * rec.cost_price

    def action_confirm(self):
        self.ensure_one()
        if not self.env.su and not self.env.user.has_group('trucking.group_trucking_issue_fuel'):
            from odoo.exceptions import AccessError
            raise AccessError(_("You do not have permission to receive fuel."))
        if self.qty <= 0 or self.cost_price <= 0:
            raise UserError(_("Quantity and Rate must be greater than zero."))
            
        company = self.env.company
        if not company.receive_fuel_account_id or not company.receive_fuel_journal_id:
            raise UserError(_("Please configure the Receive Fuel Account and Journal in the Trucking Settings."))
            
        if not self.load_id.customer_id:
            raise UserError(_("The Load must have a Customer assigned to receive fuel from them."))

        # Prepare analytic distribution from Load
        analytic_dist = self.load_id._get_load_analytic_distribution() or {}
            
        receivable_account = self.load_id.customer_id.property_account_receivable_id
        if not receivable_account:
            raise UserError(_("The Customer does not have an Account Receivable configured."))

        move = self.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': company.receive_fuel_journal_id.id,
            'date': fields.Date.context_today(self),
            'ref': f"Received Fuel for Load {self.load_id.name}",
            'line_ids': [
                (0, 0, {
                    'account_id': company.receive_fuel_account_id.id,
                    'name': f"Fuel Received {self.qty}L",
                    'debit': self.amount,
                    'credit': 0.0,
                    'analytic_distribution': analytic_dist,
                }),
                (0, 0, {
                    'account_id': receivable_account.id,
                    'partner_id': self.load_id.customer_id.id,
                    'name': f"Fuel Received {self.qty}L",
                    'debit': 0.0,
                    'credit': self.amount,
                    'analytic_distribution': analytic_dist,
                })
            ]
        })
        move.action_post()
        
        # Log to load chatter
        date_str = fields.Datetime.now().strftime('%Y-%m-%d %H:%M')
        user_name = self.env.user.name
        message = f"Fuel received on <b>{date_str}</b> by <b>{user_name}</b> from client: <b>{self.load_id.customer_id.name}</b>: <b>{self.qty} Litres</b> with a value of <b>${self.amount:.2f}</b>"
        self.load_id.message_post(body=message)
        
        # Also append to the banner logs
        current_logs = self.load_id.receive_fuel_logs or "<ul style='margin-bottom:0; padding-left:20px;'>"
        if not current_logs.endswith("</ul>"):
            current_logs += "</ul>"
        
        # Remove the closing ul to append, then add it back
        current_logs = current_logs.replace("</ul>", "")
        current_logs += f"<li>{message}</li></ul>"
        self.load_id.receive_fuel_logs = current_logs

        return {'type': 'ir.actions.act_window_close'}
