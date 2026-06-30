from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class TruckingLoad(models.Model):
    @api.model
    def default_get(self, fields_list):
        res = super(TruckingLoad, self).default_get(fields_list)
        company = self.env.company
        if 'commission_type' in fields_list and not res.get('commission_type'):
            res['commission_type'] = company.trucking_default_commission_type or 'percentage'
        if 'commission_percentage' in fields_list and not res.get('commission_percentage'):
            res['commission_percentage'] = company.trucking_default_commission_percentage or 0.0
        if 'driver_commission_amount' in fields_list and not res.get('driver_commission_amount'):
            res['driver_commission_amount'] = company.trucking_default_commission_fixed or 0.0
        return res
    _name = 'trucking.load'
    _description = 'Trucking Load'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

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

    advance_approval_state = fields.Selection([
        ('none', 'None'),
        ('requested', 'Requested'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], string='Advance Approval Status', default='none', tracking=True)
    advance_reject_reason = fields.Text(string='Advance Reject Reason')

    trucking_approval_workflow = fields.Selection(
        related='company_id.trucking_approval_workflow', readonly=True
    )

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
    date_loaded = fields.Datetime(string='Date Loaded', default=fields.Datetime.now)
    booking_date = fields.Date(string='Booking Date', default=fields.Date.context_today)
    expected_loading_date = fields.Datetime(string='Expected Loading Date')
    is_delayed_loading = fields.Boolean(string='Delayed Loading', default=False, tracking=True)

    transporter_type = fields.Selection([
        ('external', 'External Transporter'),
        ('in_house', 'In-House')
    ], string='Transporter Type', default=lambda self: self.env['ir.config_parameter'].sudo().get_param('trucking.default_transporter_type', default='external'), tracking=True)
    is_walk_in = fields.Boolean(string='Walk In Customer', default=False)
    driver_id = fields.Many2one('res.partner', string='Driver', domain="[('is_driver', '=', True)]")
    expected_delivery_date = fields.Datetime(string='Expected Delivery Date')
    customer_id = fields.Many2one('res.partner', string='Customer', tracking=True)
    transporter_id = fields.Many2one('res.partner', string='Transporter', tracking=True)
    vehicle_id = fields.Many2one('trucking.vehicle', string='Truck Reg')
    trailer_1_reg = fields.Char(string='Trailer 1 Reg (Old)')
    trailer_2_reg = fields.Char(string='Trailer 2 Reg (Old)')
    trailer_1_id = fields.Many2one('trucking.trailer', string='Trailer 1 Reg')
    trailer_2_id = fields.Many2one('trucking.trailer', string='Trailer 2 Reg')
    qty_tonnes = fields.Float(string='Qty Tonnes', default=lambda self: None)
    rate_per_tonne = fields.Monetary(string='Rate per Tonne', currency_field='currency_id', default=0.0)
    total_per_load = fields.Monetary(string='Total per Load', compute='_compute_total_per_load', store=True, currency_field='currency_id')

    transporter_display = fields.Char(string='Transporter', compute='_compute_transporter_display')
    transporter_balance_display = fields.Char(string='Transporter Bal...', compute='_compute_transporter_display')

    @api.depends('transporter_type', 'transporter_id', 'transporter_balance', 'currency_id')
    def _compute_transporter_display(self):
        for rec in self:
            if rec.transporter_type == 'in_house':
                rec.transporter_display = 'In-House'
                rec.transporter_balance_display = 'In-House'
            else:
                rec.transporter_display = rec.transporter_id.name if rec.transporter_id else ''
                currency = rec.currency_id or self.env.company.currency_id
                rec.transporter_balance_display = f"{currency.symbol or ''} {rec.transporter_balance:,.2f}"

    route_id = fields.Many2one('trucking.route', string='Route')
    is_cross_border_route = fields.Boolean(related='route_id.is_cross_border')
    border_tracking_ids = fields.One2many('trucking.load.border', 'load_id', string='Border Tracking')
    tracking_progress_html = fields.Html(string='Progress Tracker', compute='_compute_tracking_progress')

    product_id = fields.Many2one('product.product', string='Cargo', domain="[('type', '=', 'service')]", default=lambda self: self.env.ref('trucking.product_trucking_service', raise_if_not_found=False))

    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    # 2. Payment Details
    deposit_amount = fields.Monetary(string='Deposit Amount', currency_field='currency_id')
    total_advance = fields.Monetary(string='Total Advance', compute='_compute_total_advance', currency_field='currency_id')

    @api.depends('fuel_amount', 'deposit_amount')
    def _compute_total_advance(self):
        for rec in self:
            rec.total_advance = rec.fuel_amount + rec.deposit_amount
    fuel_litres = fields.Float(string='Fuel Litres')
    fuel_unit_price = fields.Float(string='Fuel Cost Price')
    fuel_issue_price = fields.Float(string='Fuel Issue Price')
    fuel_issue_date = fields.Datetime('Fuel Issue Date')
    fuel_issue_user_id = fields.Many2one('res.users', 'Fuel Issued By')
    fuel_amount = fields.Monetary(string='Fuel Amount', compute='_compute_fuel_amount', store=True, currency_field='currency_id')
    balance = fields.Monetary(string='Balance', compute='_compute_balance', store=True, currency_field='currency_id')
    journal_id = fields.Many2one('account.journal', string='Cash/Bank Acc', domain="[('type', 'in', ('bank', 'cash'))]")

    # 3. Delivery Info
    delivery_date = fields.Datetime(string='Date Delivered')
    pod = fields.Char(string='POD')
    pol = fields.Char(string='POL (Proof of Loading)')
    pod_date = fields.Date(string='POD Date')
    pod_confirmed = fields.Boolean(string='POD Confirmed')

    @api.constrains('pod', 'pod_confirmed')
    def _check_pod_confirmed(self):
        for rec in self:
            if rec.pod_confirmed and not rec.pod:
                raise ValidationError(_("You cannot confirm the POD if the POD number/value is empty."))

    @api.onchange('pod')
    def _onchange_pod(self):
        for rec in self:
            if rec.pod and not rec.pod_date:
                rec.pod_date = fields.Date.context_today(rec)
    expense_ids = fields.One2many('trucking.load.expense', 'load_id', string='Expenses')
    total_expenses = fields.Monetary(string='Total Expenses', compute='_compute_total_expenses', store=True)

    driver_commission_amount = fields.Monetary(string='Driver Commission', currency_field='currency_id', tracking=True, compute='_compute_driver_commission_amount_dynamic', store=True, readonly=False)
    driver_commission_move_id = fields.Many2one('account.move', string='Commission Journal Entry', readonly=True)
    total_commission = fields.Monetary(string='Total Commission', compute='_compute_total_commission', store=True)
    total_all_expenses = fields.Monetary(string='Total Expenses & Commission', compute='_compute_total_all_expenses', store=True)

    @api.depends('driver_commission_amount')
    def _compute_total_commission(self):
        for rec in self:
            rec.total_commission = rec.driver_commission_amount

    @api.depends('expense_ids.amount')
    def _compute_total_expenses(self):
        for rec in self:
            rec.total_expenses = sum(rec.expense_ids.mapped('amount'))

    @api.depends('total_expenses', 'total_commission', 'issued_fuel_cost')
    def _compute_total_all_expenses(self):
        for rec in self:
            rec.total_all_expenses = rec.total_expenses + rec.total_commission + rec.issued_fuel_cost

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
    display_total_per_load = fields.Char(string='Total per load', compute='_compute_display_total', store=False)
    customer_deposit = fields.Monetary(string='Customer Deposit', compute='_compute_customer_deposit', store=False, currency_field='currency_id')
    paid = fields.Monetary(string='Paid', compute='_compute_invoiced_amount', store=True, currency_field='currency_id')
    customer_rate = fields.Monetary(string='Rate', currency_field='currency_id', default=lambda self: None)
    customer_balance = fields.Monetary(string='Customer Bal', compute='_compute_invoiced_amount', store=True, currency_field='currency_id')
    gross_profit = fields.Monetary(string='Gross Profit', compute='_compute_gross_profit', store=True, currency_field='currency_id')

    # Billing Policy
    bill_customer_qty = fields.Selection([('loaded', 'Loaded Qty'), ('delivered', 'Delivered Qty')], string='Bill Customer By')
    bill_transporter_qty = fields.Selection([('loaded', 'Loaded Qty'), ('delivered', 'Delivered Qty')], string='Bill Transporter By')

    client_invoicing_rule = fields.Selection([
        ('paid_in_full', 'Paid in Full'),
        ('deposit_split', 'Deposit / Split')
    ], string='Client Invoicing Rule', default='paid_in_full')
    deposit_percentage = fields.Float(string='Deposit Percentage (%)', default=50.0)

    def _check_billing_policy(self):
        # Validation moved to action_deliver
        pass

    # Relations for automations
    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order', readonly=True)
    sale_order_id = fields.Many2one('sale.order', string='Sales Order', readonly=True)
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account', readonly=True)

    # External Transporter Rates
    rate_per_tonne_transporter = fields.Float(string='Rate per Tonne (Transporter)', tracking=True)
    rate_per_tonne_client = fields.Float(string='Rate per Tonne (Client)', tracking=True)

    # Fuel Tracking
    fuel_vendor_bill_id = fields.Many2one('account.move', string='Fuel Vendor Bill', readonly=True)
    fuel_sales_invoice_id = fields.Many2one('account.move', string='Fuel Sales Invoice', readonly=True)
    fuel_scrap_id = fields.Many2one('stock.scrap', string='Fuel Stock Scrap', readonly=True)
    issued_fuel_qty = fields.Float(string='Issued Fuel Qty', readonly=True)
    issued_fuel_rate = fields.Float(string='Issued Fuel Rate', readonly=True)
    issued_fuel_supplier_id = fields.Many2one('res.partner', string='Issued Fuel Supplier', readonly=True)
    
    # Driver Commissions & Penalties
    commission_type = fields.Selection([
        ('fixed', 'Fixed Amount'),
        ('percentage', 'Percentage of Net Profit')
    ], string='Commission Type', default='fixed', tracking=True)
    trucking_enable_driver_penalties = fields.Boolean(related='company_id.trucking_enable_driver_penalties')
    penalty_amount = fields.Float(string='Penalty Amount', tracking=True)
    penalty_reason = fields.Char(string='Penalty Reason', tracking=True)

    commission_percentage = fields.Float(string='Commission Percentage (%)', tracking=True)

    @api.depends('commission_type', 'commission_percentage', 'gross_profit', 'penalty_amount')
    def _compute_driver_commission_amount_dynamic(self):
        for rec in self:
            if rec.commission_type == 'percentage':
                net = rec.gross_profit - rec.penalty_amount
                if net > 0:
                    rec.driver_commission_amount = net * (rec.commission_percentage / 100.0)
                else:
                    rec.driver_commission_amount = 0.0

    mandatory_fields_json = fields.Char(string='Mandatory Fields JSON', compute='_compute_mandatory_fields_json')

    @api.depends('transporter_type', 'company_id')
    def _compute_mandatory_fields_json(self):
        import json
        for rec in self:
            company = rec.company_id or self.env.company
            load_type = 'inhouse' if rec.transporter_type == 'in_house' else 'external'
            
            mandatory_records = self.env['trucking.mandatory.field'].search([
                ('company_id', '=', company.id),
                ('load_type', '=', load_type)
            ])
            
            data = {
                'save': [],
                'confirm': [],
                'delivery': []
            }
            
            for m in mandatory_records:
                if m.is_save:
                    data['save'].append(m.field_id.name)
                if m.is_confirm:
                    data['confirm'].append(m.field_id.name)
                if m.is_deliver:
                    data['delivery'].append(m.field_id.name)
                    
            rec.mandatory_fields_json = json.dumps(data)

    def _check_mandatory_fields(self, stage):
        for rec in self:
            company = rec.company_id or self.env.company
            
            load_type = 'inhouse' if rec.transporter_type == 'in_house' else 'external'
            domain = [
                ('company_id', '=', company.id),
                ('load_type', '=', load_type)
            ]
            
            if stage == 'save':
                domain.append(('is_save', '=', True))
            elif stage == 'confirm':
                domain.append(('is_confirm', '=', True))
            elif stage == 'delivery':
                domain.append(('is_deliver', '=', True))
                
            mandatory_records = self.env['trucking.mandatory.field'].search(domain)
            fields_to_check = mandatory_records.mapped('field_id')
                    
            missing_fields = []
            for field in fields_to_check:
                field_name = field.name
                # Special check for falsey values. For numeric fields 0 is valid. 
                # For relational fields, empty recordset is falsey.
                val = rec[field_name]
                import logging
                logging.getLogger(__name__).info(f"CHECKING {field_name}: {val} {type(val)}")
                if isinstance(val, models.BaseModel) and not val:
                    missing_fields.append(field.field_description)
                elif not isinstance(val, models.BaseModel):
                    if val is False or val is None or val == '' or val == 0.0:
                        missing_fields.append(field.field_description)
            
            if missing_fields:
                stage_name = stage.capitalize()
                missing_str = ", ".join(missing_fields)
                raise UserError(f"The following fields are mandatory for {rec.transporter_type.replace('_', ' ').title()} loads on {stage_name}: {missing_str}")

    fuel_scrap_ids = fields.One2many('stock.scrap', 'trucking_load_id', string='Fuel Issues')
    has_issued_fuel = fields.Boolean(compute='_compute_has_issued_fuel', string='Has Issued Fuel')
    issued_fuel_cost = fields.Monetary(string='Issued Fuel Cost', compute='_compute_issued_fuel_cost', store=True, currency_field='currency_id')
    fuel_issue_logs = fields.Html(compute='_compute_fuel_issue_logs', string='Fuel Issue Logs')
    receive_fuel_logs = fields.Html(string='Receive Fuel Logs', readonly=True)

    @api.depends('fuel_scrap_ids')
    def _compute_has_issued_fuel(self):
        for rec in self:
            rec.has_issued_fuel = bool(rec.fuel_scrap_ids)

    @api.depends('fuel_scrap_ids.state', 'fuel_scrap_ids.scrap_qty', 'fuel_scrap_ids.product_id.standard_price')
    def _compute_issued_fuel_cost(self):
        for rec in self:
            cost = 0.0
            for scrap in rec.fuel_scrap_ids:
                if scrap.state == 'done':
                    if scrap.origin and scrap.origin.startswith('Reversal'):
                        cost -= scrap.scrap_qty * scrap.product_id.standard_price
                    else:
                        cost += scrap.scrap_qty * scrap.product_id.standard_price
            rec.issued_fuel_cost = cost

    @api.depends('fuel_scrap_ids', 'fuel_scrap_ids.scrap_qty', 'fuel_scrap_ids.create_date', 'fuel_scrap_ids.create_uid')
    def _compute_fuel_issue_logs(self):
        for rec in self:
            logs = []
            for scrap in rec.fuel_scrap_ids:
                date_str = scrap.create_date.strftime('%Y-%m-%d %H:%M') if scrap.create_date else 'Unknown Date'
                user_name = scrap.create_uid.name if scrap.create_uid else 'System'
                cost = scrap.scrap_qty * scrap.product_id.standard_price if scrap.state == 'done' else 0.0
                logs.append(f"<li>Fuel issued on <b>{date_str}</b> by <b>{user_name}</b>: <b>{scrap.scrap_qty} Litres</b> with a cost of <b>${cost:.2f}</b></li>")
            if logs:
                rec.fuel_issue_logs = "<ul style='margin-bottom:0; padding-left:20px;'>" + "".join(logs) + "</ul>"
            else:
                rec.fuel_issue_logs = False
    @api.onchange('transporter_type')
    def _onchange_transporter_type_expenses(self):
        if self.transporter_type == 'in_house':
            # Load from configured defaults
            defaults = self.env['trucking.default.expense'].search([])
            if defaults:
                for d in defaults:
                    has_acc = any(exp.account_id.id == d.account_id.id for exp in self.expense_ids)
                    if not has_acc:
                        self.expense_ids = [(0, 0, {
                            'account_id': d.account_id.id,
                            'supplier_id': d.supplier_id.id,
                            'journal_id': d.journal_id.id if d.journal_id else False,
                            'amount': 0.0,
                        })]
            else:
                # Ensure Default Supplier exists
                default_supplier = self.env['res.partner'].sudo().search([('name', '=', 'Default Supplier')], limit=1)
                if not default_supplier:
                    default_supplier = self.env['res.partner'].sudo().create({'name': 'Default Supplier', 'is_supplier': True})
                    
                # Ensure Driver Commission account exists
                driver_comp_account = self.env['account.account'].sudo().search([('name', '=', 'Driver Commission'), ('account_type', '=', 'expense')], limit=1)
                if not driver_comp_account:
                    expense_group = self.env.ref('account.data_account_type_expenses', raise_if_not_found=False)
                    driver_comp_account = self.env['account.account'].sudo().create({
                        'name': 'Driver Commission',
                        'code': '600100',
                        'account_type': 'expense',
                    })

                has_comp = any(exp.account_id.id == driver_comp_account.id for exp in self.expense_ids)
                if not has_comp:
                    self.expense_ids = [(0, 0, {
                        'account_id': driver_comp_account.id,
                        'supplier_id': default_supplier.id,
                        'amount': 0.0,
                    })]

                # Ensure Fuel Expense Account exists
                fuel_account = self.env['account.account'].sudo().search([('name', '=', 'Fuel Expense Account'), ('account_type', '=', 'expense')], limit=1)
                if not fuel_account:
                    fuel_account = self.env['account.account'].sudo().create({
                        'name': 'Fuel Expense Account',
                        'code': '600002',
                        'account_type': 'expense',
                    })

                has_fuel = any(exp.account_id.id == fuel_account.id for exp in self.expense_ids)
                if not has_fuel:
                    self.expense_ids = [(0, 0, {
                        'account_id': fuel_account.id,
                        'supplier_id': default_supplier.id,
                        'amount': 0.0,
                    })]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('trucking.load') or _('New')
            
            # Ensure analytic account for truck
            if vals.get('vehicle_id') and not vals.get('analytic_account_id'):
                truck = self.env['trucking.vehicle'].browse(vals['vehicle_id'])
                if truck.reg_number:
                    plan_name = "In-House Transporters"
                    analytic_plan = self.env['account.analytic.plan'].sudo().search([('name', '=', plan_name)], limit=1)
                    if not analytic_plan:
                        analytic_plan = self.env['account.analytic.plan'].sudo().create({'name': plan_name})
                        
                    analytic_acc = self.env['account.analytic.account'].sudo().search([('name', '=', truck.reg_number)], limit=1)
                    if not analytic_acc:
                        analytic_acc = self.env['account.analytic.account'].sudo().create({
                            'name': truck.reg_number,
                            'plan_id': analytic_plan.id,
                        })
                    vals['analytic_account_id'] = analytic_acc.id

        records = super(TruckingLoad, self).create(vals_list)
        records._check_mandatory_fields('save')
        records._action_post_driver_commission()
        return records

    def write(self, vals):
        if 'vehicle_id' in vals:
            for rec in self:
                vehicle_id = vals.get('vehicle_id') or rec.vehicle_id.id
                if vehicle_id:
                    truck = self.env['trucking.vehicle'].browse(vehicle_id)
                    if truck.reg_number:
                        analytic_plan = self.env['account.analytic.plan'].sudo().search([], limit=1)
                        if analytic_plan:
                            analytic_acc = self.env['account.analytic.account'].sudo().search([('name', '=', truck.reg_number)], limit=1)
                            if not analytic_acc:
                                analytic_acc = self.env['account.analytic.account'].sudo().create({
                                    'name': truck.reg_number,
                                    'plan_id': analytic_plan.id,
                                })
                            vals['analytic_account_id'] = analytic_acc.id
        
        if 'pod_confirmed' in vals and vals['pod_confirmed']:
            for rec in self:
                rec.message_post(body=f"POD Confirmed.")

        if 'pod' in vals and vals['pod'] and 'pod_date' not in vals:
            # If the user is saving a POD and no date is set, default to today
            vals['pod_date'] = fields.Date.context_today(self)
        
        res = super(TruckingLoad, self).write(vals)
        self._check_mandatory_fields('save')
        if 'driver_commission_amount' in vals or 'vehicle_id' in vals or 'state' in vals or 'driver_id' in vals or 'commission_type' in vals or 'commission_percentage' in vals:
            self._action_post_driver_commission()
        return res

    def _action_post_driver_commission(self):
        for rec in self:
            if not rec.driver_commission_amount or rec.driver_commission_amount <= 0:
                continue
            
            # Check timing
            company = rec.company_id or self.env.company
            if company.trucking_commission_calc_trigger == 'invoice' and rec.state != 'invoiced':
                continue
            if company.trucking_commission_calc_trigger == 'delivery' and rec.state not in ('delivered', 'invoiced'):
                continue
                
            journal_id = company.driver_commission_journal_id
            product_id = company.trucking_default_driver_commission_product_id
            
            if not journal_id or not product_id:
                raise ValidationError("Please configure the Driver Commission Journal and Default Product in Settings.")
                
            # Determine analytic account
            analytic_dict = {}
            if rec.vehicle_id:
                truck_reg = rec.vehicle_id.reg_number
                analytic_acc = self.env['account.analytic.account'].search([('name', '=', truck_reg)], limit=1)
                if not analytic_acc:
                    analytic_plan = self.env['account.analytic.plan'].search([], limit=1)
                    analytic_acc = self.env['account.analytic.account'].create({
                        'name': truck_reg,
                        'plan_id': analytic_plan.id if analytic_plan else False,
                    })
                if analytic_acc:
                    analytic_dict = {str(analytic_acc.id): 100}
                    
            if not rec.driver_id:
                continue

            move_vals = {
                'move_type': 'in_invoice',
                'journal_id': journal_id.id,
                'invoice_date': fields.Date.context_today(self),
                'partner_id': rec.driver_id.id,
                'ref': f"Commission - {rec.name}",
                'trucking_load_id': rec.id,
                'trucking_vehicle_id': rec.vehicle_id.id if rec.vehicle_id else False,
                'trucking_route_id': rec.route_id.id if rec.route_id else False,
                'invoice_line_ids': [
                    (0, 0, {
                        'name': f"Driver Commission - Load {rec.name}",
                        'product_id': product_id.id,
                        'price_unit': rec.driver_commission_amount,
                        'quantity': 1,
                        'analytic_distribution': analytic_dict,
                    })
                ]
            }
            
            if rec.driver_commission_move_id:
                if rec.driver_commission_move_id.state == 'posted':
                    rec.driver_commission_move_id.button_draft()
                rec.driver_commission_move_id.write({
                    'partner_id': rec.driver_id.id,
                    'trucking_load_id': rec.id,
                    'trucking_vehicle_id': rec.vehicle_id.id if rec.vehicle_id else False,
                    'trucking_route_id': rec.route_id.id if rec.route_id else False,
                    'invoice_line_ids': [(5, 0, 0)] + move_vals['invoice_line_ids']
                })
                rec.driver_commission_move_id.action_post()
            else:
                move = self.env['account.move'].create(move_vals)
                move.action_post()
                rec.driver_commission_move_id = move.id


    @api.constrains('trailer_1_id', 'trailer_2_id')
    def _check_trailers(self):
        for rec in self:
            if rec.trailer_1_id and rec.trailer_2_id and rec.trailer_1_id == rec.trailer_2_id:
                raise UserError(_("Trailer 1 and Trailer 2 cannot be the same!"))

    @api.constrains('booking_date', 'date_loaded', 'delivery_date')
    def _check_dates(self):
        for rec in self:
            if rec.date_loaded and rec.booking_date and rec.date_loaded.date() < rec.booking_date:
                raise UserError(_("Date Loaded cannot be before Booking Date."))
            if rec.delivery_date and rec.date_loaded and rec.delivery_date.date() < rec.date_loaded.date():
                raise UserError(_("Delivery Date cannot be before Date Loaded."))

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

    @api.onchange('trailer_1_id', 'trailer_2_id')
    def _onchange_trailers(self):
        if self.trailer_1_id and self.trailer_2_id and self.trailer_1_id == self.trailer_2_id:
            self.trailer_2_id = False
            return {
                'warning': {
                    'title': _("Validation Error"),
                    'message': _("Trailer is taken on slot 1, choose another trailer or contact transporter to request more information.")
                }
            }

    @api.onchange('route_id')
    def _onchange_route_id(self):
        if self.route_id and self.route_id.is_cross_border:
            # Clear existing borders
            self.border_tracking_ids = [(5, 0, 0)]
            # Copy borders from route
            new_lines = []
            for rb in self.route_id.border_ids:
                new_lines.append((0, 0, {
                    'sequence': rb.sequence,
                    'border_id': rb.border_id.id,
                }))
            self.border_tracking_ids = new_lines

    @api.depends('border_tracking_ids.ata', 'border_tracking_ids.atd', 'state', 'date_loaded', 'delivery_date', 'route_id')
    def _compute_tracking_progress(self):
        for rec in self:
            if not rec.route_id:
                rec.tracking_progress_html = "<div class='text-muted'>No tracking data available for this route.</div>"
                continue
            
            nodes = []
            
            # 1. Source Node
            source_departed = bool(rec.date_loaded or rec.state in ('in_progress', 'delivered', 'invoiced'))
            source_status = f"Departed on {rec.date_loaded.strftime('%b %d')}" if source_departed and rec.date_loaded else "Departed" if source_departed else "Pending"
            nodes.append({
                'name': rec.route_id.source if rec.route_id.source else 'Source',
                'status': source_status,
                'arrived': source_departed,
                'departed': source_departed,
                'type': 'source'
            })
            
            # 2. Border Nodes (only if cross border)
            if rec.route_id.is_cross_border:
                for border in rec.border_tracking_ids.sorted('sequence'):
                    if border.atd:
                        time_str = border.atd.strftime('%b %d, %H:%M')
                        status = f"Departed at {time_str}"
                        if 'Delayed' in (border.departure_status or ''):
                            status += f"<br/><span style='color: #ef4444; font-size: 11px;'>{border.departure_status}</span>"
                    elif border.ata:
                        time_str = border.ata.strftime('%b %d, %H:%M')
                        status = f"Arrived at {time_str}"
                        if 'Delayed' in (border.arrival_status or ''):
                            status += f"<br/><span style='color: #ef4444; font-size: 11px;'>{border.arrival_status}</span>"
                    else:
                        status = "Pending"
                        
                    nodes.append({
                        'name': border.border_id.name,
                        'status': status,
                        'arrived': bool(border.ata or border.atd),
                        'departed': bool(border.atd),
                        'type': 'border'
                    })
                    
            # 3. Destination Node
            dest_arrived = bool(rec.delivery_date or rec.state in ('delivered', 'invoiced'))
            dest_status = f"Arrived on {rec.delivery_date.strftime('%b %d')}" if dest_arrived and rec.delivery_date else "Arrived" if dest_arrived else "Pending"
            nodes.append({
                'name': rec.route_id.destination if rec.route_id.destination else 'Destination',
                'status': dest_status,
                'arrived': dest_arrived,
                'departed': dest_arrived,
                'type': 'destination'
            })
            
            current_node_idx = -1
            for i, n in enumerate(nodes):
                if n['arrived'] or n['departed']:
                    current_node_idx = i
                    
            html = '<div style="display: flex; justify-content: space-between; width: 100%; padding: 10px 0; background: #f8f9fa; border-radius: 10px;">'

            total = len(nodes)
            for idx, node in enumerate(nodes):
                is_last = (idx == total - 1)
                
                color = "#cbd5e1"
                icon = ""
                
                # Assign icons
                if node['type'] in ('source', 'destination'):
                    icon = '<i class="fa fa-building"></i>'
                else:
                    if node['departed']:
                        icon = '&#10003;'
                    elif node['arrived']:
                        icon = '&#9679;'
                        
                # Assign colors
                if node['departed']:
                    color = "#10b981"
                elif node['arrived']:
                    color = "#3b82f6"
                    
                show_truck = (idx == current_node_idx)
                # Used fa-flip-horizontal so the truck faces right
                truck_html = '<div style="font-size: 14px; color: #10b981; height: 24px; display: flex; align-items: flex-end; justify-content: center;"><i class="fa fa-truck fa-flip-horizontal"></i></div>' if show_truck else '<div style="height: 24px;"></div>'

                html += f'<div style="flex: 1; position: relative; text-align: center;">'
                
                # Line to the next node
                if not is_last:
                    line_color = "#10b981" if node['departed'] else "#cbd5e1"
                    html += f'<div style="position: absolute; top: 41px; left: 50%; width: 100%; height: 4px; background-color: {line_color}; z-index: 0;"></div>'
                    
                html += f"""
                    <div style="display: flex; flex-direction: column; align-items: center; position: relative; z-index: 1;">
                        {truck_html}
                        <div style="width: 20px; height: 20px; border-radius: 50%; background-color: {color}; color: white; display: flex; align-items: center; justify-content: center; font-weight: bold; border: 3px solid #f8f9fa; box-sizing: content-box; font-size: 10px;">
                            {icon}
                        </div>
                        <div style="margin-top: 10px; font-weight: bold; font-size: 14px; word-wrap: break-word; max-width: 90%;">{node['name']}</div>
                        <div style="font-size: 12px; color: #64748b;">{node['status']}</div>
                    </div>
                </div>
                """

            html += "</div>"
            rec.tracking_progress_html = html

    @api.depends('qty_tonnes', 'rate_per_tonne', 'transporter_type')
    def _compute_total_per_load(self):
        for rec in self:
            rec.total_per_load = rec.qty_tonnes * rec.rate_per_tonne

    @api.depends('fuel_litres', 'fuel_unit_price')
    def _compute_fuel_amount(self):
        for rec in self:
            rec.fuel_amount = rec.fuel_litres * rec.fuel_issue_price

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

    @api.constrains('trailer_1_id', 'trailer_2_id')
    def _check_duplicate_trailers(self):
        for rec in self:
            if rec.trailer_1_id and rec.trailer_2_id and rec.trailer_1_id == rec.trailer_2_id:
                raise ValidationError(_("Trailer is taken on slot 1, choose another trailer or contact transporter to request more information."))

    @api.constrains('fuel_litres', 'fuel_amount', 'fuel_scrap_ids')
    def _check_fuel_conflict(self):
        for rec in self:
            if rec.fuel_amount > 0 and rec.has_issued_fuel:
                raise ValidationError(_("You cannot enter a manual Fuel Amount (Advance) when Fuel has already been issued via scrapping, and vice versa. Please remove one."))

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

    @api.depends('invoice_id', 'invoice_id.amount_total', 'invoice_id.amount_residual', 'payment_ids.state', 'payment_ids.amount', 'qty_tonnes', 'customer_rate', 'bill_customer_qty', 'delivered_qty', 'transporter_type')
    def _compute_invoiced_amount(self):
        for rec in self:
            domain = [('load_id', '=', rec.id), ('partner_type', '=', 'customer'), ('state', '!=', 'draft')]
            manual_payments = self.env['account.payment'].search(domain)
            manual_paid = sum(manual_payments.mapped('amount'))
            
            if rec.transporter_type == 'in_house':
                so_qty = rec.qty_tonnes
            else:
                so_qty = rec.qty_tonnes if rec.bill_customer_qty == 'loaded' else rec.delivered_qty
                
            rec.invoiced_amount = so_qty * rec.customer_rate
            
            if rec.sale_order_id:
                invoices = rec.sale_order_id.invoice_ids.filtered(lambda i: i.state == 'posted')
                invoiced_so = sum(invoices.mapped('amount_total'))
                residual_so = sum(invoices.mapped('amount_residual'))
                
                uninvoiced_amount = rec.invoiced_amount - invoiced_so
                rec.customer_balance = uninvoiced_amount + residual_so - manual_paid
                rec.paid = rec.invoiced_amount - rec.customer_balance
            else:
                rec.paid = manual_paid
                rec.customer_balance = rec.invoiced_amount - rec.paid

    def _compute_display_total(self):
        for rec in self:
            symbol = rec.currency_id.symbol or '$'
            formatted_total = f"{symbol}{rec.invoiced_amount:,.2f}"
            if rec.client_invoicing_rule == 'deposit_split':
                deposit_amt = rec.invoiced_amount * (rec.deposit_percentage / 100.0)
                formatted_deposit = f"{symbol}{deposit_amt:,.2f}"
                rec.display_total_per_load = f"{formatted_total} ({int(rec.deposit_percentage)}% deposit {formatted_deposit})"
            else:
                rec.display_total_per_load = formatted_total

    def _compute_customer_deposit(self):
        for rec in self:
            if rec.client_invoicing_rule == 'deposit_split':
                rec.customer_deposit = rec.invoiced_amount * (rec.deposit_percentage / 100.0)
            else:
                rec.customer_deposit = 0.0

    @api.depends('invoiced_amount', 'total_per_load', 'total_all_expenses', 'transporter_type')
    def _compute_gross_profit(self):
        for rec in self:
            if rec.transporter_type == 'in_house':
                rec.gross_profit = rec.invoiced_amount - rec.total_all_expenses
            else:
                rec.gross_profit = rec.invoiced_amount - rec.total_per_load - rec.total_all_expenses

    def action_deliver(self):
        self._check_mandatory_fields('delivery')
        for rec in self:
            if rec.transporter_type == 'external' and (not rec.bill_customer_qty or not rec.bill_transporter_qty):
                raise UserError(_("Please choose a Billing Policy before delivering."))
            if rec.state not in ('in_progress', 'overdue'):
                continue
                
            if rec.transporter_type == 'in_house':
                if not any(exp.amount > 0 for exp in rec.expense_ids):
                    raise UserError(_("For In-House loads, you must record at least one expense with an amount greater than zero before delivering."))
                    
            if rec.transporter_type == 'external' and rec.delivered_qty <= 0:
                raise UserError(_("Please set a valid Delivered Qty before delivering."))
            if not rec.product_id:
                raise UserError(_("Please select a Product for billing."))

            # 1. Calculate Analytic Distribution
            analytic_distribution = rec._get_load_analytic_distribution()

            # 2. Create or Update Sales Order
            if rec.transporter_type == 'in_house':
                so_qty = rec.qty_tonnes
            else:
                so_qty = rec.qty_tonnes if rec.bill_customer_qty == 'loaded' else rec.delivered_qty

            if not rec.sale_order_id:
                so = self.env['sale.order'].create({
                    'partner_id': rec.customer_id.id,
                    'order_line': [(0, 0, {
                        'product_id': rec.product_id.id,
                        'name': f"Load {rec.name} - {rec.route_id.name if rec.route_id else ''}",
                        'product_uom_qty': so_qty,
                        'qty_delivered': so_qty,
                        'price_unit': rec.customer_rate,
                        'tax_ids': False,
                        'analytic_distribution': analytic_distribution,
                    })]
                })
                if so.state in ('draft', 'sent'):
                    so.action_confirm()
                rec.sale_order_id = so.id
            else:
                so = rec.sale_order_id
                # Update SO with final delivered quantities
                if so.order_line:
                    line = so.order_line[0]
                    line.product_uom_qty = so_qty
                    line.qty_delivered = so_qty
                    if analytic_distribution:
                        line.analytic_distribution = analytic_distribution

            # Create Invoice from SO if not already created by automation
            company = rec.company_id or self.env.company
            invoice = False
            if company.trucking_auto_create_invoice:
                if rec.client_invoicing_rule == 'deposit_split':
                    invoice = so._create_invoices(final=True)
                    if analytic_distribution:
                        for line in invoice.invoice_line_ids:
                            line.analytic_distribution = analytic_distribution
                    if invoice.state == 'draft':
                        invoice.action_post()
                else:
                    if not so.invoice_ids:
                        invoice = so._create_invoices()
                        if analytic_distribution:
                            for line in invoice.invoice_line_ids:
                                line.analytic_distribution = analytic_distribution
                        invoice.action_post()
                    else:
                        invoice = so.invoice_ids.filtered(lambda i: i.state != 'cancel')
                        if invoice:
                            invoice = invoice[0]
                            if invoice.state == 'draft':
                                invoice.action_post()
                rec.invoice_id = invoice.id if invoice else False

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

            if rec.transporter_type == 'external':
                po_qty = rec.qty_tonnes if rec.bill_transporter_qty == 'loaded' else rec.delivered_qty

                po_lines = [(0, 0, {
                    'product_id': rec.product_id.id,
                    'name': f"Freight Load {rec.name}",
                    'product_qty': po_qty,
                    'qty_received': po_qty,
                    'price_unit': rec.rate_per_tonne,
                    'tax_ids': False,
                    'analytic_distribution': analytic_distribution,
                })]
                
                if rec.shortages > 0:
                    po_lines.append((0, 0, {
                        'product_id': rec.product_id.id,
                        'name': f"Shortages Deduction - Load {rec.name}",
                        'product_qty': 1,
                        'qty_received': 1,
                        'price_unit': -rec.shortages,
                        'tax_ids': False,
                        'analytic_distribution': analytic_distribution,
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
                        if analytic_distribution:
                            for line in bill.invoice_line_ids:
                                line.analytic_distribution = analytic_distribution
                        bill.action_post()
                    else:
                        if analytic_distribution:
                            for line in bill.invoice_line_ids:
                                line.analytic_distribution = analytic_distribution
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
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Success',
                    'message': 'Invoices generated successfully!',
                    'type': 'success',
                    'sticky': False,
                    'next': {'type': 'ir.actions.client', 'tag': 'reload'},
                }
            }

    def _get_load_analytic_distribution(self):
        self.ensure_one()
        strategy = self.company_id.trucking_analytic_strategy or 'both'
        distribution = {}
        
        if strategy in ('truck', 'both') and self.vehicle_id:
            truck_plan = self.env['account.analytic.plan'].sudo().search([('name', '=', 'Vehicles')], limit=1)
            if not truck_plan:
                truck_plan = self.env['account.analytic.plan'].sudo().search([], limit=1)
            if truck_plan:
                truck_acc = self.env['account.analytic.account'].sudo().search([('name', '=', self.vehicle_id.reg_number), ('plan_id', '=', truck_plan.id)], limit=1)
                if not truck_acc:
                    truck_acc = self.env['account.analytic.account'].sudo().create({
                        'name': self.vehicle_id.reg_number,
                        'plan_id': truck_plan.id,
                    })
                distribution[str(truck_acc.id)] = 100
                
        if strategy in ('transporter_type', 'both') and self.transporter_type:
            account_name = "In-House Transporters" if self.transporter_type == 'in_house' else "External Transporters"
            type_plan = self.env['account.analytic.plan'].sudo().search([('name', '=', 'Transporter Type')], limit=1)
            if not type_plan:
                type_plan = self.env['account.analytic.plan'].sudo().create({'name': 'Transporter Type'})
            if type_plan:
                type_acc = self.env['account.analytic.account'].sudo().search([('name', '=', account_name), ('plan_id', '=', type_plan.id)], limit=1)
                if not type_acc:
                    type_acc = self.env['account.analytic.account'].sudo().create({
                        'name': account_name,
                        'plan_id': type_plan.id,
                    })
                distribution[str(type_acc.id)] = 100
                
        return distribution if distribution else False


    def action_confirm_load(self):
        self._check_mandatory_fields('confirm')
        for rec in self:
            today = fields.Date.context_today(self)
            if rec.date_loaded and rec.date_loaded.date() > today:
                rec.state = 'upcoming'
            else:
                rec.state = 'in_progress'

            if rec.client_invoicing_rule == 'deposit_split':
                if not rec.sale_order_id:
                    so_qty = rec.qty_tonnes
                    so = self.env['sale.order'].create({
                        'partner_id': rec.customer_id.id,
                        'order_line': [(0, 0, {
                            'product_id': rec.product_id.id,
                            'name': f"Load {rec.name} - {rec.route_id.name if rec.route_id else ''}",
                            'product_uom_qty': so_qty,
                            'qty_delivered': 0,
                            'price_unit': rec.customer_rate,
                            'tax_ids': False,
                            'analytic_distribution': rec._get_load_analytic_distribution(),
                        })]
                    })
                    if so.state in ('draft', 'sent'):
                        so.action_confirm()
                    rec.sale_order_id = so.id

                company = rec.company_id or self.env.company
                if company.trucking_auto_create_invoice and rec.sale_order_id:
                    wizard = self.env['sale.advance.payment.inv'].with_context(active_ids=[rec.sale_order_id.id], active_model='sale.order').create({
                        'advance_payment_method': 'percentage',
                        'amount': rec.deposit_percentage,
                    })
                    wizard.create_invoices()
                    if rec.sale_order_id.invoice_ids:
                        invoice = rec.sale_order_id.invoice_ids.sorted('create_date', reverse=True)[0]
                        if invoice.state == 'draft':
                            invoice.action_post()
                        rec.invoice_id = invoice.id

    def _check_auto_in_progress(self):
        for rec in self:
            if rec.state in ('draft', 'pending_approval', 'rejected'):
                if rec.trucking_approval_workflow == 'combined':
                    is_ok = rec.advance_approval_state in ('none', 'approved')
                    is_approved = rec.advance_approval_state == 'approved'
                else:
                    fuel_ok = rec.fuel_approval_state in ('none', 'approved')
                    deposit_ok = rec.deposit_approval_state in ('none', 'approved')
                    is_ok = fuel_ok and deposit_ok
                    is_approved = rec.fuel_approval_state == 'approved' or rec.deposit_approval_state == 'approved'
                
                if is_ok and is_approved:
                    today = fields.Date.context_today(self)
                    if rec.date_loaded and rec.date_loaded.date() > today:
                        rec.state = 'upcoming'
                    else:
                        rec.state = 'in_progress'

    def action_request_advance_approval(self):
        for rec in self:
            if not rec.vehicle_id or not rec.trailer_1_id:
                raise UserError(_("Truck Reg and Trailer 1 Reg are required before requesting advance approval."))
            if rec.total_advance <= 0:
                raise UserError(_("Total advance must be greater than zero to request approval."))
            rec.advance_approval_state = 'requested'
            rec.state = 'pending_approval'

    def action_approve_advance(self):
        for rec in self:
            rec.advance_approval_state = 'approved'
            
            # Fuel Payment / Fuel Issue Logic
            if rec.issued_fuel_supplier_id:
                # New Flow: Supplier Fuel Issued
                company = self.env.company
                process = company.trucking_in_house_fuel_process if rec.transporter_type == 'in_house' else company.trucking_external_fuel_process
                if not process:
                    process = 'scrap'
                
                product = self.env['product.product'].search([('default_code', '=', 'FUEL')], limit=1)
                if not product:
                    product = self.env['product.product'].create({
                        'name': 'Fuel',
                        'default_code': 'FUEL',
                        'type': 'consu',
                        'is_storable': True,
                        'standard_price': 1.20,
                        'list_price': 1.98,
                        'uom_id': self.env.ref('uom.product_uom_litre').id if self.env.ref('uom.product_uom_litre', raise_if_not_found=False) else self.env.ref('uom.product_uom_unit').id,
                    })
                    stock_location = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1).lot_stock_id
                    if stock_location:
                        self.env['stock.quant']._update_available_quantity(product, stock_location, 1000.0)

                analytic_dist = rec._get_load_analytic_distribution() or {}
                qty = rec.fuel_litres
                cost_price = rec.fuel_unit_price
                issue_price = rec.fuel_issue_price
                supplier_to_use = rec.issued_fuel_supplier_id
                
                scrap = False
                vendor_bill = False
                sales_invoice = False
                
                if process == 'scrap':
                    stock_location = self.env['stock.warehouse'].search([('company_id', '=', company.id)], limit=1).lot_stock_id
                    if stock_location:
                        available_qty = product.with_context(location=stock_location.id).free_qty
                        if qty > available_qty:
                            raise ValidationError(_("Requested quantity (%(req)s) exceeds available stock (%(avail)s) for Fuel.", req=qty, avail=available_qty))
                            
                        scrap = self.env['stock.scrap'].create({
                            'product_id': product.id,
                            'product_uom_id': product.uom_id.id,
                            'scrap_qty': qty,
                            'location_id': stock_location.id,
                            'origin': rec.name,
                            'analytic_distribution': analytic_dist,
                            'trucking_load_id': rec.id,
                            'supplier_id': supplier_to_use.id,
                        })
                        scrap.action_validate()
                        
                if process == 'bill':
                    vendor_bill = self.env['account.move'].create({
                        'move_type': 'in_invoice',
                        'partner_id': supplier_to_use.id,
                        'invoice_date': fields.Date.context_today(self),
                        'ref': f"Fuel for {rec.name}",
                        'invoice_line_ids': [(0, 0, {
                            'product_id': product.id,
                            'quantity': qty,
                            'price_unit': cost_price,
                            'analytic_distribution': analytic_dist,
                        })]
                    })
                    vendor_bill.action_post()
                    
                if rec.transporter_type == 'external':
                    if not rec.transporter_id:
                        raise UserError(_("External transporter must be set on the load to issue fuel."))
                    sales_invoice = self.env['account.move'].create({
                        'move_type': 'out_invoice',
                        'partner_id': rec.transporter_id.id,
                        'invoice_date': fields.Date.context_today(self),
                        'ref': f"Fuel Advance {rec.name}",
                        'invoice_line_ids': [(0, 0, {
                            'product_id': product.id,
                            'quantity': qty,
                            'price_unit': issue_price,
                            'analytic_distribution': analytic_dist,
                        })]
                    })
                    sales_invoice.action_post()
                    
                rec.write({
                    'has_issued_fuel': True,
                    'fuel_scrap_id': scrap.id if scrap else False,
                    'fuel_vendor_bill_id': vendor_bill.id if vendor_bill else False,
                    'fuel_sales_invoice_id': sales_invoice.id if sales_invoice else False,
                })
                
                total_val = qty * cost_price
                rec.message_post(body=f"<b>Fuel Request Approved</b><br/>{qty}L issued from {supplier_to_use.name} at {cost_price}/L. Total: ${total_val:.2f}.")

            else:
                # Old Flow: Cash/Bank Advance
                if rec.fuel_amount > 0 and not rec.fuel_payment_id:
                    if not rec.journal_id:
                        raise UserError(_("Please select a Cash/Bank Account (Journal) in the Payment Details section before approving the advance."))
                    payment_fuel = self.env['account.payment'].create({
                        'payment_type': 'outbound',
                        'partner_type': 'supplier',
                        'partner_id': rec.transporter_id.id,
                        'amount': rec.fuel_amount,
                        'journal_id': rec.journal_id.id,
                        'memo': f"Fuel Advance - Load {rec.name}",
                        'date': fields.Date.context_today(self),
                        'load_id': rec.id,
                    })
                    payment_fuel.action_post()
                    rec.fuel_payment_id = payment_fuel.id
                
            # Deposit Payment
            if rec.deposit_amount > 0 and not rec.deposit_payment_id:
                if not rec.journal_id:
                    raise UserError(_("Please select a Cash/Bank Account (Journal) in the Payment Details section before approving the advance."))
                payment_deposit = self.env['account.payment'].create({
                    'payment_type': 'outbound',
                    'partner_type': 'supplier',
                    'partner_id': rec.transporter_id.id,
                    'amount': rec.deposit_amount,
                    'journal_id': rec.journal_id.id,
                    'memo': f"Deposit Advance - Load {rec.name}",
                    'date': fields.Date.context_today(self),
                    'load_id': rec.id,
                })
                payment_deposit.action_post()
                rec.deposit_payment_id = payment_deposit.id
                
            rec._check_auto_in_progress()

    def action_reject_advance(self):
        self.ensure_one()
        return {
            'name': _('Reject Advance Request'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'trucking.reject.wizard',
            'target': 'new',
            'context': {
                'default_load_id': self.id,
                'default_reject_type': 'advance',
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
        
        # Accounting metrics for Revenue, Net Profit, and Cost
        aml_domain = [('parent_state', '=', 'posted'), ('account_id.internal_group', 'in', ['income', 'expense'])]
        if date_filter != 'all':
            aml_domain.append(('date', '>=', start_date))
        
        amls = self.env['account.move.line'].search(aml_domain)
        
        total_revenue = 0.0
        total_expense = 0.0
        
        for aml in amls:
            if aml.account_id.internal_group == 'income':
                total_revenue += (aml.credit - aml.debit)
            elif aml.account_id.internal_group == 'expense':
                total_expense += (aml.debit - aml.credit)
                
        net_profit = total_revenue - total_expense
        cost = total_expense
        
        total_invoices = cost
        gross_profit = net_profit
        total_load_value = total_revenue
        
        overdue_loads = all_loads.filtered(lambda l: 
            (l.transporter_type == 'in_house' and l.state in ('delivered', 'invoiced') and not l.pod_confirmed) or
            (l.transporter_type != 'in_house' and l.state in ['draft', 'in_progress', 'overdue', 'pending_approval', 'rejected', 'upcoming'] and l.expected_delivery_date and l.expected_delivery_date.date() < today)
        )
        
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
        upcoming = all_loads.filtered(lambda l: l.state in ['draft', 'in_progress', 'pending_approval', 'upcoming'] and l.expected_delivery_date and l.expected_delivery_date.date() >= today)
        upcoming_list = [{
            'id': l.id,
            'name': l.name,
            'customer': l.customer_id.name,
            'date': l.expected_delivery_date.strftime('%Y-%m-%d'),
            'days_left': (l.expected_delivery_date.date() - today).days
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

    def action_create_consolidated_invoice(self):
        for rec in self:
            pass
        if not self:
            return
            
        customers = self.mapped('customer_id')
        if len(customers) > 1:
            raise UserError("You can only create a consolidated invoice for loads belonging to the SAME customer.")
            
        unconfirmed_pods = self.filtered(lambda l: not l.pod_confirmed)
        if unconfirmed_pods:
            raise UserError(f"The following loads do not have confirmed PODs: {', '.join(unconfirmed_pods.mapped('name'))}")
            
        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': customers[0].id,
            'invoice_line_ids': [],
        }
        
        for load in self:
            line_vals = {
                'name': f"Load {load.name} - {load.route_id.name}" if load.route_id else f"Load {load.name}",
                'quantity': load.qty_tonnes or 1.0,
                'price_unit': load.customer_rate,
                'tax_ids': [(5, 0, 0)],  # Explicitly clear taxes
                'trucking_order_no': load.name,
                'trucking_route_name': load.route_id.name if load.route_id else '',
            }
            if load.product_id:
                line_vals['product_id'] = load.product_id.id
                
            invoice_vals['invoice_line_ids'].append((0, 0, line_vals))
            
        invoice = self.env['account.move'].create(invoice_vals)
        
        self.write({'invoice_id': invoice.id, 'state': 'invoiced'})
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'target': 'current',
        }



    def action_reverse_issued_fuel(self):
        for rec in self:
            # Cancel documents
            if rec.fuel_vendor_bill_id and rec.fuel_vendor_bill_id.state == 'posted':
                rec.fuel_vendor_bill_id.button_draft()
                rec.fuel_vendor_bill_id.button_cancel()
            if rec.fuel_sales_invoice_id and rec.fuel_sales_invoice_id.state == 'posted':
                rec.fuel_sales_invoice_id.button_draft()
                rec.fuel_sales_invoice_id.button_cancel()
            
            # Stock Scraps
            if not rec.fuel_scrap_ids and not rec.fuel_vendor_bill_id:
                raise UserError(_("No fuel issued to reverse."))
            for scrap in rec.fuel_scrap_ids:
                if scrap.state == 'done':
                    # Create a return scrap (put back to stock)
                    return_scrap = self.env['stock.scrap'].create({
                        'product_id': scrap.product_id.id,
                        'product_uom_id': scrap.product_uom_id.id,
                        'scrap_qty': scrap.scrap_qty,
                        'location_id': scrap.scrap_location_id.id, # From scrap
                        'scrap_location_id': scrap.location_id.id, # To stock
                        'origin': f"Reversal of {scrap.name}",
                        'trucking_load_id': rec.id,
                    })
                    return_scrap.action_validate()
            
            # Log the reversal
            supplier_name = rec.issued_fuel_supplier_id.name if rec.issued_fuel_supplier_id else 'N/A'
            total_amount = rec.issued_fuel_qty * rec.issued_fuel_rate
            rec.message_post(body=f"<b>Fuel Reversed</b><br/>User reversed fuel issuance of <b>{rec.issued_fuel_qty}L</b> from <b>{supplier_name}</b> for a total of <b>${total_amount:.2f}</b>.")

            # Clear fields
            rec.has_issued_fuel = False
            rec.fuel_vendor_bill_id = False
            rec.fuel_sales_invoice_id = False
            rec.fuel_scrap_id = False
            rec.issued_fuel_qty = 0.0
            rec.issued_fuel_rate = 0.0
            rec.issued_fuel_supplier_id = False
            
            rec.message_post(body="Issued Fuel has been reversed.")

    def action_reverse_received_fuel(self):
        for rec in self:
            # Find journal entries related to receiving fuel for this load
            moves = self.env['account.move'].search([
                ('ref', 'ilike', f"Receive Fuel: {rec.name}"),
                ('state', '=', 'posted')
            ])
            if not moves:
                raise UserError(_("No received fuel journal entries found to reverse."))
            for move in moves:
                # Reverse the move
                reversal = self.env['account.move.reversal'].with_context(active_model='account.move', active_ids=move.ids).create({
                    'reason': 'Reversing Received Fuel',
                    'date': fields.Date.context_today(self),
                    'journal_id': move.journal_id.id,
                })
                reversal.reverse_moves()
            rec.message_post(body="Received Fuel journal entries have been reversed.")
            rec.receive_fuel_logs = False # Clear logs

    def action_request_fuel_approval(self):
        for rec in self:
            if not rec.vehicle_id or not rec.trailer_1_id:
                raise UserError(_("Truck Reg and Trailer 1 Reg are required before requesting fuel approval."))
            if rec.fuel_amount <= 0 and not rec.company_id.trucking_allow_zero_advance:
                raise UserError(_("Fuel amount must be greater than zero to request approval."))
            rec.fuel_approval_state = 'requested'
            rec.state = 'pending_approval'

    def action_approve_fuel(self):
        for rec in self:
            rec.fuel_approval_state = 'approved'
            
            if rec.issued_fuel_supplier_id:
                # New Flow: Supplier Fuel Issued
                company = self.env.company
                process = company.trucking_in_house_fuel_process if rec.transporter_type == 'in_house' else company.trucking_external_fuel_process
                if not process:
                    process = 'scrap'
                
                product = self.env['product.product'].search([('default_code', '=', 'FUEL')], limit=1)
                if not product:
                    product = self.env['product.product'].create({
                        'name': 'Fuel',
                        'default_code': 'FUEL',
                        'type': 'consu',
                        'is_storable': True,
                        'standard_price': 1.20,
                        'list_price': 1.98,
                        'uom_id': self.env.ref('uom.product_uom_litre').id if self.env.ref('uom.product_uom_litre', raise_if_not_found=False) else self.env.ref('uom.product_uom_unit').id,
                    })
                    stock_location = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1).lot_stock_id
                    if stock_location:
                        self.env['stock.quant']._update_available_quantity(product, stock_location, 1000.0)

                analytic_dist = rec._get_load_analytic_distribution() or {}
                qty = rec.fuel_litres
                cost_price = rec.fuel_unit_price
                issue_price = rec.fuel_issue_price
                supplier_to_use = rec.issued_fuel_supplier_id
                
                scrap = False
                vendor_bill = False
                sales_invoice = False
                
                if process == 'scrap':
                    stock_location = self.env['stock.warehouse'].search([('company_id', '=', company.id)], limit=1).lot_stock_id
                    if stock_location:
                        available_qty = product.with_context(location=stock_location.id).free_qty
                        if qty > available_qty:
                            raise ValidationError(_("Requested quantity (%(req)s) exceeds available stock (%(avail)s) for Fuel.", req=qty, avail=available_qty))
                            
                        scrap = self.env['stock.scrap'].create({
                            'product_id': product.id,
                            'product_uom_id': product.uom_id.id,
                            'scrap_qty': qty,
                            'location_id': stock_location.id,
                            'origin': rec.name,
                            'analytic_distribution': analytic_dist,
                            'trucking_load_id': rec.id,
                            'supplier_id': supplier_to_use.id,
                        })
                        scrap.action_validate()
                        
                if process == 'bill':
                    vendor_bill = self.env['account.move'].create({
                        'move_type': 'in_invoice',
                        'partner_id': supplier_to_use.id,
                        'invoice_date': fields.Date.context_today(self),
                        'ref': f"Fuel for {rec.name}",
                        'invoice_line_ids': [(0, 0, {
                            'product_id': product.id,
                            'quantity': qty,
                            'price_unit': cost_price,
                            'analytic_distribution': analytic_dist,
                        })]
                    })
                    vendor_bill.action_post()
                    
                if rec.transporter_type == 'external':
                    if not rec.transporter_id:
                        raise UserError(_("External transporter must be set on the load to issue fuel."))
                    sales_invoice = self.env['account.move'].create({
                        'move_type': 'out_invoice',
                        'partner_id': rec.transporter_id.id,
                        'invoice_date': fields.Date.context_today(self),
                        'ref': f"Fuel Advance {rec.name}",
                        'invoice_line_ids': [(0, 0, {
                            'product_id': product.id,
                            'quantity': qty,
                            'price_unit': issue_price,
                            'analytic_distribution': analytic_dist,
                        })]
                    })
                    sales_invoice.action_post()
                    
                rec.write({
                    'has_issued_fuel': True,
                    'fuel_scrap_id': scrap.id if scrap else False,
                    'fuel_vendor_bill_id': vendor_bill.id if vendor_bill else False,
                    'fuel_sales_invoice_id': sales_invoice.id if sales_invoice else False,
                })
                
                total_val = qty * cost_price
                rec.message_post(body=f"<b>Fuel Request Approved</b><br/>{qty}L issued from {supplier_to_use.name} at {cost_price}/L. Total: ${total_val:.2f}.")

            else:
                # Old Flow: Cash/Bank Advance
                if not rec.journal_id:
                    raise UserError(_("Please select a Cash/Bank Account (Journal) in the Payment Details section before approving fuel."))
                
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
            if not rec.vehicle_id or not rec.trailer_1_id:
                raise UserError(_("Truck Reg and Trailer 1 Reg are required before requesting deposit approval."))
            if rec.deposit_amount <= 0:
                raise UserError(_("Deposit amount must be greater than zero to request approval."))
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

    def action_dummy(self):
        return True
