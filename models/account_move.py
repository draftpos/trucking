from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = 'account.move'

    trucking_load_id = fields.Many2one('trucking.load', string='Trucking Load')
    trucking_vehicle_id = fields.Many2one('trucking.vehicle', string='Truck Reg')
    trucking_route_id = fields.Many2one('trucking.route', string='Route')

    @api.onchange('trucking_load_id')
    def _onchange_trucking_load_id(self):
        if self.trucking_load_id:
            load = self.trucking_load_id
            self.partner_id = load.customer_id.id
            if not self.invoice_line_ids:
                if load.transporter_type == 'in_house':
                    qty = load.qty_tonnes
                else:
                    qty = load.qty_tonnes if load.bill_customer_qty == 'loaded' else load.delivered_qty
                self.invoice_line_ids = [(0, 0, {
                    'product_id': load.product_id.id,
                    'name': f"Load {load.name} - {load.route_id.name if load.route_id else ''}",
                    'quantity': qty,
                    'price_unit': load.customer_rate,
                    'analytic_distribution': load._get_load_analytic_distribution(),
                })]


    trucking_load_ids = fields.One2many('trucking.load', 'invoice_id', string='Trucking Loads')
    trucking_bill_load_ids = fields.One2many('trucking.load', 'transporter_bill_id', string='Trucking Bill Loads')
    pod = fields.Char(string='POD', compute='_compute_pod_details')
    pod_date = fields.Date(string='POD Date', compute='_compute_pod_details')

    def _compute_pod_details(self):
        for move in self:
            load = move.trucking_load_ids[:1] or move.trucking_bill_load_ids[:1]
            if load:
                move.pod = load.pod
                move.pod_date = load.pod_date
            else:
                move.pod = False
                move.pod_date = False

    def _compute_payments_widget_to_reconcile_info(self):
        super()._compute_payments_widget_to_reconcile_info()
        for move in self:
            if move.invoice_outstanding_credits_debits_widget:
                load = self.env['trucking.load'].search([
                    '|', ('transporter_bill_id', '=', move.id),
                         ('invoice_id', '=', move.id)
                ], limit=1)

                if load:
                    vals = move.invoice_outstanding_credits_debits_widget
                    if isinstance(vals, dict) and 'content' in vals:
                        filtered_content = []
                        for item in vals['content']:
                            payment_id = item.get('account_payment_id')
                            if payment_id:
                                payment = self.env['account.payment'].browse(payment_id)
                                if payment.load_id.id == load.id:
                                    filtered_content.append(item)
                            else:
                                line_id = item.get('id')
                                if line_id:
                                    move_line = self.env['account.move.line'].browse(line_id)
                                    other_load = self.env['trucking.load'].search([
                                        '|', ('transporter_bill_id', '=', move_line.move_id.id),
                                             ('invoice_id', '=', move_line.move_id.id)
                                    ], limit=1)
                                    if other_load and other_load.id == load.id:
                                        filtered_content.append(item)
                                    elif not other_load:
                                        # If it's a credit note not tied to any load, exclude it.
                                        pass
                        
                        vals['content'] = filtered_content
                        if not vals['content']:
                            move.invoice_outstanding_credits_debits_widget = False
                        else:
                            move.invoice_outstanding_credits_debits_widget = vals

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    trucking_order_no = fields.Char(string="Order No")
    trucking_route_name = fields.Char(string="Route")
