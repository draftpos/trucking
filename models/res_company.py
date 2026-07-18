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

    # Fuel Settings
    trucking_allow_supplier_on_issue_fuel = fields.Boolean("Allow Supplier on Issue Fuel")
    trucking_allow_zero_advance = fields.Boolean("Allow Zero Value Advance Requests", default=False)
    trucking_enable_issue_fuel = fields.Boolean("Activate Issue Fuel Feature", default=True)
    trucking_allow_fuel_adjustments = fields.Boolean("Allow Fuel Adjustments")
    trucking_in_house_fuel_process = fields.Selection([
        ('scrap', 'Deduct from Inventory (Scrap)'),
        ('bill', 'Direct Billing (Vendor Bill)')
    ], string='In-House Fuel Process', default='scrap')
    trucking_external_fuel_process = fields.Selection([
        ('scrap', 'Deduct from Inventory + Bill Transporter'),
        ('bill', 'Direct Billing (Supplier Bill + Transporter Bill)')
    ], string='External Fuel Process', default='scrap')
    
    # Analytic Settings
    trucking_auto_create_analytic_for_truck = fields.Boolean(
        string='Auto Create Analytic Account for New Trucks', 
        default=False,
        help="If enabled, an analytic account will be automatically created when a new truck is created."
    )
    trucking_analytic_strategy = fields.Selection([
        ('truck', 'By Truck Registration'),
        ('transporter_type', 'By Transporter Type (In-House vs External)'),
        ('both', 'Both Truck and Transporter Type')
    ], string='Analytic Accounting Strategy', default='both')
    
    # Label Settings
    trucking_pod_label = fields.Char("POD Label", default="POD")
    
    # Auto Invoice
    trucking_auto_create_invoice = fields.Boolean("Auto-create Sales Invoice on Delivery", default=True)
    trucking_allow_unconfirmed_pod_invoice = fields.Boolean("Allow Bulk Invoicing for Unconfirmed PODs", default=False)
    trucking_customer_invoice_stage = fields.Selection([
        ('confirm', 'On Confirm Load (Deposit Invoice only, if applicable)'),
        ('deliver', 'On Deliver (Generate all invoices at once)')
    ], string="Customer Invoice Stage (External)", default='confirm')
    
    # Penalties & Demurrage
    trucking_enable_driver_penalties = fields.Boolean("Enable Driver Penalties")
    trucking_enable_transporter_penalties = fields.Boolean("Enable External Transporter Penalties")
    trucking_enable_demurrage = fields.Boolean("Enable Demurrage for External Transporters")
    trucking_invoice_rate_source = fields.Selection([
        ('customer', 'Customer Rate'),
        ('transporter', 'Transporter Rate')
    ], string="Invoice Rate Source", default='customer')
    trucking_charge_billing_timing = fields.Selection([
        ('with_delivery', 'Bill with Main Delivery'),
        ('on_entry', 'Bill Immediately on Entry')
    ], string="Charge Billing Timing", default='with_delivery')
    trucking_demurrage_product_id = fields.Many2one(
        'product.product', 
        string='Default Demurrage Product',
        domain="[('type', '=', 'service')]",
        default=lambda self: self.env.ref('trucking.product_trucking_demurrage', raise_if_not_found=False)
    )
    trucking_penalty_product_id = fields.Many2one(
        'product.product', 
        string='Default Transporter Penalty Product',
        domain="[('type', '=', 'service')]",
        default=lambda self: self.env.ref('trucking.product_trucking_penalty', raise_if_not_found=False)
    )

    # Commission Timing
    trucking_commission_calc_trigger = fields.Selection([
        ('delivery', 'Upon Delivery'),
        ('invoice', 'Upon Invoicing/Accounting')
    ], string="Commission Calculation Trigger", default='delivery')

    # Approval Workflow
    trucking_approval_workflow = fields.Selection([
        ('combined', 'Combined Advance Approval'),
        ('separate', 'Separate Deposit and Fuel Approvals')
    ], string="Approval Workflow", default='combined')

    # Deliveries
    trucking_allow_non_expense_deliveries = fields.Boolean(
        "Allow Non-Expense Deliveries", 
        default=False,
        help="If enabled, allows delivering in-house loads without requiring any recorded expenses."
    )
    trucking_allow_excess_delivered_qty = fields.Boolean(
        "Allow Delivered Qty > Loaded Qty",
        default=False,
        help="If enabled, the system will not block delivery if the delivered quantity exceeds the loaded quantity (due to weighbridge variations)."
    )


    # Driver Commission Defaults
    trucking_default_commission_type = fields.Selection([
        ('fixed', 'Fixed Amount'),
        ('percentage', 'Percentage of Net Profit')
    ], string="Default Commission Type", default='percentage')
    trucking_default_commission_percentage = fields.Float("Default Commission Percentage (%)", default=10.0)
    trucking_default_commission_fixed = fields.Monetary("Default Fixed Commission", currency_field='currency_id', default=0.0)
    trucking_default_driver_commission_product_id = fields.Many2one(
        'product.product', 
        string='Default Driver Commission Product',
        domain="[('type', '=', 'service')]"
    )

    trucking_mandatory_field_ids = fields.One2many(
        'trucking.mandatory.field', 'company_id', string='Mandatory Fields'
    )

    @api.model_create_multi
    def create(self, vals_list):
        companies = super().create(vals_list)
        companies.sudo()._init_default_mandatory_fields()
        return companies

    def _init_default_mandatory_fields(self):
        # Only run for companies that have no mandatory fields configured
        ModelField = self.env['ir.model.fields']
        MandatoryField = self.env['trucking.mandatory.field']

        # Get field definitions from the model
        fields_to_add = {
            'inhouse': [
                'route_id', 'booking_date', 'expected_loading_date', 'expected_delivery_date',
                'date_loaded', 'vehicle_id', 'trailer_1_id', 'driver_id', 'commission_type',
                'customer_id', 'customer_rate', 'qty_tonnes', 'delivery_date'
            ],
            'external': [
                'route_id', 'booking_date', 'expected_loading_date', 'expected_delivery_date',
                'date_loaded', 'transporter_id', 'vehicle_id', 'driver_id', 'transporter_rate',
                'qty_tonnes', 'customer_id', 'customer_rate', 'delivery_date'
            ]
        }

        for company in self:
            if MandatoryField.search_count([('company_id', '=', company.id)]) > 0:
                continue

            for load_type, field_names in fields_to_add.items():
                for field_name in field_names:
                    field = ModelField.search([('model', '=', 'trucking.load'), ('name', '=', field_name)], limit=1)
                    if not field:
                        continue
                    
                    # Everything is required on save/confirm, except delivery_date which is only required on deliver
                    is_save = is_confirm = (field_name != 'delivery_date')
                    is_deliver = True

                    MandatoryField.create({
                        'company_id': company.id,
                        'load_type': load_type,
                        'field_id': field.id,
                        'is_save': is_save,
                        'is_confirm': is_confirm,
                        'is_deliver': is_deliver
                    })

    @api.model
    def _init_default_mandatory_fields_all(self):
        companies = self.search([])
        companies.sudo()._init_default_mandatory_fields()

    def _setup_default_mandatory_fields(self):
        self.ensure_one()
        if self.trucking_mandatory_field_ids:
            return  # Already set up
            
        load_model = self.env['ir.model'].search([('model', '=', 'trucking.load')], limit=1)
        if not load_model:
            return
            
        fields_inhouse = [
            'route_id', 'booking_date', 'expected_loading_date', 'expected_delivery_date', 
            'date_loaded', 'delivery_date', 'pod', 'pod_date', 'vehicle_id', 
            'trailer_1_id', 'trailer_2_id', 'driver_id', 'commission_type', 'penalty_amount'
        ]
        
        fields_external = [
            'route_id', 'booking_date', 'expected_loading_date', 'expected_delivery_date', 
            'date_loaded', 'delivery_date', 'pod', 'pod_date', 'transporter_id', 
            'vehicle_id', 'trailer_1_id', 'trailer_2_id', 'rate_per_tonne', 'total_per_load'
        ]
        
        vals_list = []
        for f_name in fields_inhouse:
            f_id = self.env['ir.model.fields'].search([('model_id', '=', load_model.id), ('name', '=', f_name)], limit=1)
            if f_id:
                vals_list.append({
                    'company_id': self.id,
                    'load_type': 'inhouse',
                    'field_id': f_id.id,
                    'is_save': True,
                    'is_confirm': True,
                    'is_deliver': True,
                })
                
        for f_name in fields_external:
            f_id = self.env['ir.model.fields'].search([('model_id', '=', load_model.id), ('name', '=', f_name)], limit=1)
            if f_id:
                vals_list.append({
                    'company_id': self.id,
                    'load_type': 'external',
                    'field_id': f_id.id,
                    'is_save': True,
                    'is_confirm': True,
                    'is_deliver': True,
                })
                
        if vals_list:
            self.env['trucking.mandatory.field'].create(vals_list)
