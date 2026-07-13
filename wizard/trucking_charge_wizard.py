from odoo import api, fields, models, _
from odoo.exceptions import UserError

class TruckingChargeWizard(models.TransientModel):
    _name = 'trucking.charge.wizard'
    _description = 'Add Extra Charge Wizard'

    load_id = fields.Many2one('trucking.load', string='Load', required=True)
    charge_type = fields.Selection([
        ('demurrage', 'Demurrage'),
        ('penalty', 'Penalty')
    ], string='Charge Type', required=True)
    
    amount = fields.Monetary(string='Amount', required=True, currency_field='currency_id')
    reason = fields.Char(string='Reason', required=True)
    currency_id = fields.Many2one(related='load_id.currency_id', readonly=True)

    def action_confirm(self):
        self.ensure_one()
        if self.amount <= 0:
            raise UserError(_("Amount must be strictly positive."))
            
        charge = self.env['trucking.load.charge'].create({
            'load_id': self.load_id.id,
            'charge_type': self.charge_type,
            'amount': self.amount,
            'reason': self.reason,
            'state': 'draft'
        })
        
        # Check if we should bill immediately
        timing = self.load_id.company_id.trucking_charge_billing_timing
        if timing == 'on_entry' or self.load_id.state in ['delivered', 'invoiced']:
            # Create bills now
            self._generate_standalone_bills(charge)
            
        return {'type': 'ir.actions.act_window_close'}

    def _generate_standalone_bills(self, charge):
        company = self.load_id.company_id
        
        # Get products
        if charge.charge_type == 'demurrage':
            product = company.trucking_demurrage_product_id
            if not product:
                raise UserError(_("Please configure a Default Demurrage Product in Settings."))
        else:
            product = company.trucking_penalty_product_id
            if not product:
                raise UserError(_("Please configure a Default Transporter Penalty Product in Settings."))
                
        analytic_distribution = self.load_id._get_load_analytic_distribution()
        
        # 1. Customer Invoice
        if self.load_id.customer_id:
            inv_vals = {
                'move_type': 'out_invoice',
                'partner_id': self.load_id.customer_id.id,
                'invoice_origin': self.load_id.name,
                'invoice_date': fields.Date.context_today(self),
                'invoice_line_ids': [(0, 0, {
                    'product_id': product.id,
                    'name': f"{dict(charge._fields['charge_type'].selection).get(charge.charge_type)} - {charge.reason} ({self.load_id.name})",
                    'quantity': 1,
                    'price_unit': charge.amount,
                    'analytic_distribution': analytic_distribution,
                })]
            }
            if self.load_id.sale_order_id:
                # Link to sale order line if needed, but standalone charge usually doesn't need SO link, or we append to SO
                pass 
                
            customer_invoice = self.env['account.move'].create(inv_vals)
            charge.customer_invoice_id = customer_invoice.id
            
        # 2. Transporter Bill
        if self.load_id.transporter_id:
            # We use an in_invoice (Vendor Bill) for Demurrage and Penalties, increasing the bill
            # Wait, demurrage INCREASES what we owe. Penalty INCREASES what we owe? 
            # The user said: "for penalies it should also increase what we ow the trnaporter and what the customer owes us"
            # So both are positive vendor bills.
            bill_vals = {
                'move_type': 'in_invoice',
                'partner_id': self.load_id.transporter_id.id,
                'invoice_date': fields.Date.context_today(self),
                'ref': f"{dict(charge._fields['charge_type'].selection).get(charge.charge_type)} - {self.load_id.name}",
                'invoice_line_ids': [(0, 0, {
                    'product_id': product.id,
                    'name': f"{dict(charge._fields['charge_type'].selection).get(charge.charge_type)} - {charge.reason}",
                    'quantity': 1,
                    'price_unit': charge.amount,
                    'analytic_distribution': analytic_distribution,
                })]
            }
            vendor_bill = self.env['account.move'].create(bill_vals)
            charge.vendor_bill_id = vendor_bill.id
            
        charge.state = 'billed'
