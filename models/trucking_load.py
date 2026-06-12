from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class TruckingLoad(models.Model):
    _name = 'trucking.load'
    _description = 'Trucking Load'
    _order = 'name desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Header / State
    name = fields.Char(string='Order No', required=True, copy=False, readonly=True, default=lambda self: self.env['ir.sequence'].next_by_code('trucking.load') or _('New'))
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending_approval', 'Pending Approval'),
        ('rejected', 'Rejected'),
        ('upcoming', 'Upcoming'),
        ('in_progress', 'In Progress'),
        ('overdue', 'In Progress (Overdue)'),
        ('delivered', 'Delivered'),
        ('invoiced', 'Delivered and Invoiced'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    fuel_approval_state = fields.Selection([
        ('none', 'None'),
        ('requested', 'Requested'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], string='Fuel Approval Status', default='none', tracking=True)
    fuel_reject_reason = fields.Text(string='Fuel Reject Reason')

    deposit_approval_state = fields.Selection([
        ('none', 'None'),
        ('requested', 'Requested'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], string='Deposit Approval Status', default='none', tracking=True)
    deposit_reject_reason = fields.Text(string='Deposit Reject Reason')

    # 1. Loading Details
    date_loaded = fields.Date(string='Date Loaded', default=fields.Date.context_today)
    booking_date = fields.Date(string='Booking Date', default=fields.Date.context_today)
    expected_loading_date = fields.Datetime(string='Expected Loading Date')
    is_delayed_loading = fields.Boolean(string='Delayed Loading', default=False, tracking=True)

    expected_delivery_date = fields.Date(string='Expected Delivery Date', required=True)
    customer_id = fields.Many2one('res.partner', string='Customer', required=True, tracking=True)
    transporter_id = fields.Many2one('res.partner', string='Transporter', required=True, tracking=True)
    vehicle_id = fields.Many2one('trucking.vehicle', string='Truck Reg', required=True, domain="[('partner_id', '=', transporter_id)]")
    trailer_1_reg = fields.Char(string='Trailer 1 Reg (Old)')
    trailer_2_reg = fields.Char(string='Trailer 2 Reg (Old)')
    trailer_1_id = fields.Many2one('trucking.trailer', string='Trailer 1 Reg', required=True)
    trailer_2_id = fields.Many2one('trucking.trailer', string='Trailer 2 Reg')
    qty_tonnes = fields.Float(string='Qty Tonnes', required=True, default=0.0)
    rate_per_tonne = fields.Monetary(string='Rate per Tonne', currency_field='currency_id', required=True, default=0.0)
    total_per_load = fields.Monetary(string='Total per Load', compute='_compute_total_per_load', store=True, currency_field='currency_id')
    route_id = fields.Many2one('trucking.route', string='Route')
    product_id = fields.Many2one('product.product', string='Product', domain="[('type', '=', 'service')]", default=lambda self: self.env.ref('trucking.product_trucking_service', raise_if_not_found=False))

    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    # 2. Payment Details
    deposit_amount = fields.Monetary(string='Deposit Amount', currency_field='currency_id')
    fuel_litres = fields.Float(string='Fuel Litres')
    fuel_unit_price = fields.Float(string='Fuel Unit Price')
    fuel_amount = fields.Monetary(string='Fuel Amount', compute='_compute_fuel_amount', store=True, currency_field='currency_id')
    balance = fields.Monetary(string='Balance', compute='_compute_balance', store=True, currency_field='currency_id')
    journal_id = fields.Many2one('account.journal', string='Cash/Bank Acc', domain="[('type', 'in', ('bank', 'cash'))]")

    # 3. Delivery Info
    delivery_date = fields.Date(string='Delivery Date')
    pod = fields.Char(string='POD')
    delivered_qty = fields.Float(string='Delivered Qty')
    variance_qty = fields.Float(string='Variance Qty', compute='_compute_variance_qty', store=True)
    variance_value = fields.Monetary(string='Variance Value', compute='_compute_variance_value', store=True, currency_field='currency_id')
    shortages = fields.Monetary(string='Shortages', currency_field='currency_id')
    transporter_balance = fields.Monetary(string='Transporter Balance', compute='_compute_transporter_balance', store=True, currency_field='currency_id')

    transporter_bill_id = fields.Many2one('account.move', string='Transporter Bill', readonly=True)
    fuel_payment_id = fields.Many2one('account.payment', string='Fuel Payment', readonly=True)
    deposit_payment_id = fields.Many2one('account.payment', string='Deposit Payment', readonly=True)

    # 4. Customer Recovery Details
    invoice_id = fields.Many2one('account.move', string='Invoice No', readonly=True)
    invoiced_amount = fields.Monetary(string='Invoiced Amount', compute='_compute_invoiced_amount', store=True, currency_field='currency_id')
    paid = fields.Monetary(string='Paid', compute='_compute_invoiced_amount', store=True, currency_field='currency_id')
    customer_rate = fields.Monetary(string='Rate', currency_field='currency_id', required=True, default=0.0)
    customer_balance = fields.Monetary(string='Customer Bal', compute='_compute_invoiced_amount', store=True, currency_field='currency_id')
    gross_profit = fields.Monetary(string='Gross Profit', compute='_compute_gross_profit', store=True, currency_field='currency_id')

    # Billing Policy
    bill_customer_qty = fields.Selection([('loaded', 'Loaded Qty'), ('delivered', 'Delivered Qty')], string='Bill Customer By')
    bill_transporter_qty = fields.Selection([('loaded', 'Loaded Qty'), ('delivered', 'Delivered Qty')], string='Bill Transporter By')

    def _check_billing_policy(self):
        # Validation moved to action_deliver
        pass

    # Relations for automations
    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order', readonly=True)
    sale_order_id = fields.Many2one('sale.order', string='Sales Order', readonly=True)
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account', readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('trucking.load') or _('New')
        return super().create(vals_list)

    @api.model
    def _cron_check_delayed_loading(self):
        now = fields.Datetime.now()
        # Find loads that are not yet delayed and are not in a final state
        loads = self.search([
            ('expected_loading_date', '<', now),
            ('is_delayed_loading', '=', False),
            ('state', 'in', ('draft', 'upcoming', 'in_progress'))
        ])
        for load in loads:
            # If no date_loaded is set, or if it doesn't match the expected loading date
            if not load.date_loaded or load.date_loaded != load.expected_loading_date.date():
                load.is_delayed_loading = True

    @api.onchange('vehicle_id')
    def _onchange_vehicle_id(self):
        if self.vehicle_id:
            if self.vehicle_id.trailer_1_id:
                self.trailer_1_id = self.vehicle_id.trailer_1_id
            elif self.vehicle_id.trailer_1_reg and not self.trailer_1_id:
                # Fallback for old data
                self.trailer_1_reg = self.vehicle_id.trailer_1_reg

            if self.vehicle_id.trailer_2_id:
                self.trailer_2_id = self.vehicle_id.trailer_2_id
            elif self.vehicle_id.trailer_2_reg and not self.trailer_2_id:
                self.trailer_2_reg = self.vehicle_id.trailer_2_reg

    @api.depends('qty_tonnes', 'rate_per_tonne')
    def _compute_total_per_load(self):
        for rec in self:
            rec.total_per_load = rec.qty_tonnes * rec.rate_per_tonne

    @api.depends('fuel_litres', 'fuel_unit_price')
    def _compute_fuel_amount(self):
        for rec in self:
            rec.fuel_amount = rec.fuel_litres * rec.fuel_unit_price

    @api.depends('deposit_amount', 'fuel_amount')
    def _compute_balance(self):
        for rec in self:
            rec.balance = rec.deposit_amount - rec.fuel_amount

    @api.depends('qty_tonnes', 'delivered_qty')
    def _compute_variance_qty(self):
        for rec in self:
            rec.variance_qty = rec.qty_tonnes - rec.delivered_qty

    @api.depends('variance_qty', 'rate_per_tonne', 'bill_transporter_qty')
    def _compute_variance_value(self):
        for rec in self:
            if rec.bill_transporter_qty == 'delivered' and rec.variance_qty > 0:
                rec.variance_value = rec.variance_qty * rec.rate_per_tonne
            else:
                rec.variance_value = 0.0

    @api.constrains('customer_rate')
    def _check_customer_rate(self):
        for rec in self:
            if rec.customer_rate <= 0.0:
                raise ValidationError(_("Please input Customer Recovery Rate (must be greater than 0)."))

    @api.constrains('deposit_amount', 'fuel_amount', 'shortages', 'total_per_load')
    def _check_advance_amounts(self):
        for rec in self:
            if rec.deposit_amount + rec.fuel_amount + rec.shortages > rec.total_per_load:
                raise ValidationError(_("The total of Deposit Amount, Fuel Amount, and Shortages cannot exceed the Total per Load."))

    @api.constrains('delivered_qty', 'qty_tonnes')
    def _check_delivered_qty(self):
        for rec in self:
            if rec.delivered_qty > rec.qty_tonnes:
                raise ValidationError(_("Delivered Qty cannot exceed Loaded Qty (Qty Tonnes)."))

    payment_ids = fields.One2many('account.payment', 'load_id', string='Payments')

    @api.depends('total_per_load', 'deposit_amount', 'fuel_amount', 'shortages', 'transporter_bill_id.amount_residual', 'transporter_bill_id.state', 'payment_ids.state', 'payment_ids.amount', 'delivered_qty', 'qty_tonnes', 'rate_per_tonne', 'bill_transporter_qty')
    def _compute_transporter_balance(self):
        for rec in self:
            if rec.transporter_bill_id and rec.transporter_bill_id.state == 'posted':
                rec.transporter_balance = rec.transporter_bill_id.amount_residual
            else:
                exclude_ids = [p.id for p in [rec.fuel_payment_id, rec.deposit_payment_id] if p]
                domain = [('load_id', '=', rec.id), ('state', '!=', 'draft')]
                if exclude_ids:
                    domain.append(('id', 'not in', exclude_ids))
                manual_payments = self.env['account.payment'].search(domain)
                manual_paid = sum(manual_payments.mapped('amount'))
                variance_val = (rec.qty_tonnes - rec.delivered_qty) * rec.rate_per_tonne if rec.bill_transporter_qty == 'delivered' else 0.0
                rec.transporter_balance = rec.total_per_load - variance_val - rec.deposit_amount - rec.fuel_amount - rec.shortages - manual_paid

    @api.depends('invoice_id', 'invoice_id.amount_total', 'invoice_id.amount_residual', 'payment_ids.state', 'payment_ids.amount')
    def _compute_invoiced_amount(self):
        for rec in self:
            domain = [('load_id', '=', rec.id), ('partner_type', '=', 'customer'), ('state', '!=', 'draft')]
            manual_payments = self.env['account.payment'].search(domain)
            manual_paid = sum(manual_payments.mapped('amount'))
            
            if rec.invoice_id and rec.invoice_id.state == 'posted':
                rec.invoiced_amount = rec.invoice_id.amount_total
                rec.customer_balance = rec.invoice_id.amount_residual
                rec.paid = rec.invoiced_amount - rec.customer_balance
            else:
                so_qty = rec.qty_tonnes if rec.bill_customer_qty == 'loaded' else rec.delivered_qty
                rec.invoiced_amount = so_qty * rec.customer_rate
                rec.paid = manual_paid
                rec.customer_balance = rec.invoiced_amount - rec.paid

    @api.depends('invoiced_amount', 'total_per_load')
    def _compute_gross_profit(self):
        for rec in self:
            rec.gross_profit = rec.invoiced_amount - rec.total_per_load

    def action_deliver(self):
        for rec in self:
            if not rec.bill_customer_qty or not rec.bill_transporter_qty:
                raise UserError(_("Please choose a Billing Policy before delivering."))
            if rec.state not in ('in_progress', 'overdue'):
                continue
            
            if not rec.delivery_date:
                raise UserError(_("Please set the Delivery Date before delivering."))
            if not rec.pod:
                raise UserError(_("Please provide a POD (Proof of Delivery) before delivering."))
            if rec.delivered_qty <= 0:
                raise UserError(_("Please set a valid Delivered Qty before delivering."))
            if rec.customer_rate <= 0:
                raise UserError(_("Please set a valid Customer Rate in Customer Recovery Details before delivering."))
            if not rec.product_id:
                raise UserError(_("Please select a Product for billing."))

            # 1. Create Analytic Account
            analytic_plan = self.env['account.analytic.plan'].search([], limit=1)
            analytic_acc = self.env['account.analytic.account'].create({
                'name': f"Load {rec.name}",
                'partner_id': rec.customer_id.id,
                'plan_id': analytic_plan.id if analytic_plan else False,
            })
            rec.analytic_account_id = analytic_acc.id

            # 2. Create Sales Order
            so_qty = rec.qty_tonnes if rec.bill_customer_qty == 'loaded' else rec.delivered_qty
            so = self.env['sale.order'].create({
                'partner_id': rec.customer_id.id,
                'order_line': [(0, 0, {
                    'product_id': rec.product_id.id,
                    'name': f"Load {rec.name} - {rec.route_id.name if rec.route_id else ''}",
                    'product_uom_qty': so_qty,
                    'qty_delivered': so_qty,
                    'price_unit': rec.customer_rate,
                    'tax_ids': False,
                    'analytic_distribution': {str(analytic_acc.id): 100} if analytic_acc else False,
                })]
            })
            if so.state in ('draft', 'sent'):
                so.action_confirm()
                
            rec.sale_order_id = so.id

            # Create Invoice from SO if not already created by automation
            if not so.invoice_ids:
                invoice = so._create_invoices()
                invoice.action_post()
            else:
                invoice = so.invoice_ids[0]
                if invoice.state == 'draft':
                    invoice.action_post()
            rec.invoice_id = invoice.id

            # Auto-reconcile existing customer payments
            if invoice and invoice.state == 'posted':
                receivable_account = invoice.line_ids.filtered(lambda l: l.account_id.account_type == 'asset_receivable')
                if receivable_account:
                    receivable_account = receivable_account[0].account_id
                    domain = [('load_id', '=', rec.id), ('partner_type', '=', 'customer'), ('state', '!=', 'draft')]
                    customer_payments = self.env['account.payment'].search(domain)
                    for payment in customer_payments:
                        if payment.move_id:
                            payment_lines = payment.move_id.line_ids.filtered(lambda l: l.account_id == receivable_account and not l.reconciled)
                            for line in payment_lines:
                                inv_lines = invoice.line_ids.filtered(lambda l: l.account_id == receivable_account and not l.reconciled)
                                if inv_lines:
                                    try:
                                        (inv_lines[0] | line).reconcile()
                                    except Exception as e:
                                        import logging
                                        logging.getLogger(__name__).error(f"Reconciliation error: {e}")
                                        pass

            po_qty = rec.qty_tonnes if rec.bill_transporter_qty == 'loaded' else rec.delivered_qty

            po_lines = [(0, 0, {
                'product_id': rec.product_id.id,
                'name': f"Freight Load {rec.name}",
                'product_qty': po_qty,
                'qty_received': po_qty,
                'price_unit': rec.rate_per_tonne,
                'tax_ids': False,
                'analytic_distribution': {str(analytic_acc.id): 100} if analytic_acc else False,
            })]
            
            if rec.shortages > 0:
                po_lines.append((0, 0, {
                    'product_id': rec.product_id.id,
                    'name': f"Shortages Deduction - Load {rec.name}",
                    'product_qty': 1,
                    'qty_received': 1,
                    'price_unit': -rec.shortages,
                    'tax_ids': False,
                    'analytic_distribution': {str(analytic_acc.id): 100} if analytic_acc else False,
                }))
                
            po = self.env['purchase.order'].create({
                'partner_id': rec.transporter_id.id,
                'order_line': po_lines
            })
            if po.state in ('draft', 'sent', 'to approve'):
                po.button_confirm()
                
            rec.purchase_order_id = po.id
            
            # Create Bill if not already created by automation
            if not po.invoice_ids:
                po.action_create_invoice()
            
            bill = po.invoice_ids[0] if po.invoice_ids else False
            
            if bill:
                if bill.state == 'draft':
                    bill.invoice_date = rec.delivery_date
                    bill.ref = rec.name
                    bill.action_post()
                
                rec.transporter_bill_id = bill.id

                payable_account = bill.line_ids.filtered(lambda l: l.account_id.account_type == 'liability_payable')
                if payable_account:
                    payable_account = payable_account[0].account_id
                    domain = [('load_id', '=', rec.id), ('partner_type', '=', 'supplier'), ('state', '!=', 'draft')]
                    supplier_payments = self.env['account.payment'].search(domain)
                    for payment in supplier_payments:
                        if payment.move_id:
                            payment_lines = payment.move_id.line_ids.filtered(lambda l: l.account_id == payable_account and not l.reconciled)
                            for line in payment_lines:
                                bill_lines = bill.line_ids.filtered(lambda l: l.account_id == payable_account and not l.reconciled)
                                if bill_lines:
                                    try:
                                        (bill_lines[0] | line).reconcile()
                                    except Exception as e:
                                        import logging
                                        logging.getLogger(__name__).error(f"Reconciliation error: {e}")
                                        pass
            
            rec.state = 'invoiced'

    def action_confirm_load(self):
        for rec in self:
            today = fields.Date.context_today(self)
            if rec.date_loaded and rec.date_loaded > today:
                rec.state = 'upcoming'
            else:
                rec.state = 'in_progress'

    def _check_auto_in_progress(self):
        for rec in self:
            if rec.state in ('draft', 'pending_approval', 'rejected'):
                fuel_ok = rec.fuel_approval_state in ('none', 'approved')
                deposit_ok = rec.deposit_approval_state in ('none', 'approved')
                if fuel_ok and deposit_ok and (rec.fuel_approval_state == 'approved' or rec.deposit_approval_state == 'approved'):
                    today = fields.Date.context_today(self)
                    if rec.date_loaded and rec.date_loaded > today:
                        rec.state = 'upcoming'
                    else:
                        rec.state = 'in_progress'

    def action_request_fuel_approval(self):
        for rec in self:
            if rec.fuel_amount <= 0:
                # Return Wizard
                return {
                    'name': 'Confirm Zero Fuel Request',
                    'type': 'ir.actions.act_window',
                    'res_model': 'trucking.zero.confirm.wizard',
                    'view_mode': 'form',
                    'target': 'new',
                    'context': {
                        'default_load_id': rec.id,
                        'default_request_type': 'fuel',
                        'default_message': 'Oops! You have not entered an amount for fuel. Are you sure you want to set the fuel amount to zero?'
                    }
                }
            rec.fuel_approval_state = 'requested'
            rec.state = 'pending_approval'

    def action_approve_fuel(self):
        for rec in self:
            if not rec.journal_id:
                raise UserError(_("Please select a Cash/Bank Account (Journal) in the Payment Details section before approving fuel."))
            rec.fuel_approval_state = 'approved'
            if rec.fuel_amount > 0 and not rec.fuel_payment_id:
                payment = self.env['account.payment'].create({
                    'payment_type': 'outbound',
                    'partner_type': 'supplier',
                    'partner_id': rec.transporter_id.id,
                    'amount': rec.fuel_amount,
                    'journal_id': rec.journal_id.id,
                    'memo': f"Fuel Advance - Load {rec.name}",
                    'date': fields.Date.context_today(self),
                    'load_id': rec.id,
                })
                payment.action_post()
                rec.fuel_payment_id = payment.id
            rec._check_auto_in_progress()

    def action_reject_fuel(self):
        self.ensure_one()
        return {
            'name': _('Reject Fuel Request'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'trucking.reject.wizard',
            'target': 'new',
            'context': {
                'default_load_id': self.id,
                'default_reject_type': 'fuel',
            }
        }

    def action_request_deposit_approval(self):
        for rec in self:
            if rec.deposit_amount <= 0:
                # Return Wizard
                return {
                    'name': 'Confirm Zero Deposit Request',
                    'type': 'ir.actions.act_window',
                    'res_model': 'trucking.zero.confirm.wizard',
                    'view_mode': 'form',
                    'target': 'new',
                    'context': {
                        'default_load_id': rec.id,
                        'default_request_type': 'deposit',
                        'default_message': 'Oops! You have not entered an amount for deposit. Are you sure you want to set the deposit amount to zero?'
                    }
                }
            rec.deposit_approval_state = 'requested'
            rec.state = 'pending_approval'

    def action_approve_deposit(self):
        for rec in self:
            if not rec.journal_id:
                raise UserError(_("Please select a Cash/Bank Account (Journal) in the Payment Details section before approving the deposit."))
            rec.deposit_approval_state = 'approved'
            if rec.deposit_amount > 0 and not rec.deposit_payment_id:
                payment = self.env['account.payment'].create({
                    'payment_type': 'outbound',
                    'partner_type': 'supplier',
                    'partner_id': rec.transporter_id.id,
                    'amount': rec.deposit_amount,
                    'journal_id': rec.journal_id.id,
                    'memo': f"Deposit Advance - Load {rec.name}",
                    'date': fields.Date.context_today(self),
                    'load_id': rec.id,
                })
                payment.action_post()
                rec.deposit_payment_id = payment.id
            rec._check_auto_in_progress()

    def action_reject_deposit(self):
        self.ensure_one()
        return {
            'name': _('Reject Deposit Request'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'trucking.reject.wizard',
            'target': 'new',
            'context': {
                'default_load_id': self.id,
                'default_reject_type': 'deposit',
            }
        }

    @api.model
    def _cron_check_overdue_loads(self):
        today = fields.Date.context_today(self)
        overdue_loads = self.search([
            ('state', '=', 'in_progress'),
            ('expected_delivery_date', '<', today)
        ])
        for load in overdue_loads:
            load.state = 'overdue'

    @api.model
    def _cron_check_upcoming_loads(self):
        today = fields.Date.context_today(self)
        upcoming_loads = self.search([
            ('state', '=', 'upcoming'),
            ('date_loaded', '<=', today)
        ])
        for load in upcoming_loads:
            load.state = 'in_progress'

    @api.model
    def get_dashboard_data(self, date_filter='all'):
        domain = []
        today = fields.Date.context_today(self)
        
        from dateutil.relativedelta import relativedelta
        import calendar

        if date_filter == 'week':
            start_date = today - relativedelta(days=today.weekday())
            domain = [('create_date', '>=', start_date)]
        elif date_filter == 'month':
            start_date = today.replace(day=1)
            domain = [('create_date', '>=', start_date)]
        elif date_filter == 'year':
            start_date = today.replace(month=1, day=1)
            domain = [('create_date', '>=', start_date)]

        loads = self.search(domain)
        all_loads = self.search([]) if domain else loads

        total_delivered = len(loads.filtered(lambda l: l.state in ('delivered', 'invoiced')))
        in_progress = len(loads.filtered(lambda l: l.state in ('in_progress', 'overdue')))
        
        delivered_on_time = len(loads.filtered(lambda l: l.state in ('delivered', 'invoiced') and l.delivery_date and l.expected_delivery_date and l.delivery_date <= l.expected_delivery_date))
        delayed_deliveries = len(loads.filtered(lambda l: l.state in ('delivered', 'invoiced') and l.delivery_date and l.expected_delivery_date and l.delivery_date > l.expected_delivery_date))
        
        trucking_product_id = self.env.ref('trucking.product_trucking_service', raise_if_not_found=False)
        if trucking_product_id:
            # For invoices, we might want to apply date_filter on invoice_date, but let's keep simple for now
            invoice_domain = [
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('invoice_line_ids.product_id', '=', trucking_product_id.id)
            ]
            if date_filter != 'all':
                invoice_domain.append(('invoice_date', '>=', start_date))
            total_invoices = self.env['account.move'].search_count(invoice_domain)
        else:
            total_invoices = len(loads.filtered(lambda l: l.state == 'invoiced'))
            
        gross_profit = sum(loads.mapped('gross_profit'))
        total_load_value = sum(loads.mapped('total_per_load'))
        
        overdue_loads = all_loads.filtered(lambda l: l.state in ['draft', 'in_progress', 'overdue', 'pending_approval', 'rejected', 'upcoming'] and l.expected_delivery_date and l.expected_delivery_date < today)
        
        overdue_list = [{
            'id': l.id,
            'name': l.name,
            'customer': l.customer_id.name,
            'transporter': l.transporter_id.name,
            'expected_delivery_date': l.expected_delivery_date.strftime('%Y-%m-%d') if l.expected_delivery_date else '',
        } for l in overdue_loads[:10]]
        
        approval_loads = all_loads.filtered(lambda l: l.state in ['pending_approval', 'rejected'])
        approvals_list = []
        for l in approval_loads[:10]:
            reason = []
            if l.fuel_approval_state == 'requested':
                reason.append('Fuel Req')
            elif l.fuel_approval_state == 'rejected':
                reason.append('Fuel Rej')
                
            if l.deposit_approval_state == 'requested':
                reason.append('Deposit Req')
            elif l.deposit_approval_state == 'rejected':
                reason.append('Deposit Rej')
                
            approvals_list.append({
                'id': l.id,
                'name': l.name,
                'customer': l.customer_id.name,
                'status_text': ' | '.join(reason) if reason else l.state.replace('_', ' ').title(),
                'state': l.state,
            })

        # Chart Data: Profitability over the last 6 months
        monthly_data = {'labels': [], 'profit': [], 'revenue': []}
        for i in range(5, -1, -1):
            target_month = today - relativedelta(months=i)
            start_of_month = target_month.replace(day=1)
            end_of_month = start_of_month + relativedelta(day=31)
            
            month_loads = all_loads.filtered(lambda l: l.create_date and start_of_month <= l.create_date.date() <= end_of_month)
            monthly_data['labels'].append(target_month.strftime('%b %Y'))
            monthly_data['profit'].append(round(sum(month_loads.mapped('gross_profit')), 2))
            monthly_data['revenue'].append(round(sum(month_loads.mapped('total_per_load')), 2))

        # Chart Data: Status Breakdown
        status_counts = {}
        for l in all_loads:
            state = dict(self._fields['state'].selection).get(l.state, l.state)
            status_counts[state] = status_counts.get(state, 0) + 1
            
        status_breakdown = {
            'labels': list(status_counts.keys()),
            'data': list(status_counts.values())
        }

        # Live Feed: Last 10 modified loads
        recent_loads = self.search([], order='write_date desc', limit=10)
        live_feed = [{
            'id': l.id,
            'name': l.name,
            'message': f"Updated {dict(self._fields['state'].selection).get(l.state, l.state)}",
            'time': l.write_date.strftime('%Y-%m-%d %H:%M') if l.write_date else '',
            'state': l.state
        } for l in recent_loads]

        # Upcoming Deliveries: All future deliveries
        upcoming = all_loads.filtered(lambda l: l.state in ['draft', 'in_progress', 'pending_approval', 'upcoming'] and l.expected_delivery_date and l.expected_delivery_date >= today)
        upcoming_list = [{
            'id': l.id,
            'name': l.name,
            'customer': l.customer_id.name,
            'date': l.expected_delivery_date.strftime('%Y-%m-%d'),
            'days_left': (l.expected_delivery_date - today).days
        } for l in upcoming.sorted('expected_delivery_date')[:30]]

        return {
            'metrics': {
                'total_delivered': total_delivered,
                'in_progress': in_progress,
                'total_invoices': total_invoices,
                'gross_profit': gross_profit,
                'total_load_value': total_load_value,
                'overdue_loads': len(overdue_loads),
                'delivered_on_time': delivered_on_time,
                'delayed_deliveries': delayed_deliveries
            },
            'overdue_list': overdue_list,
            'approvals_list': approvals_list,
            'monthly_data': monthly_data,
            'status_breakdown': status_breakdown,
            'live_feed': live_feed,
            'upcoming_deliveries': upcoming_list
        }
