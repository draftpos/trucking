from odoo import api, fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    trucking_default_transporter_type = fields.Selection([
        ('external', 'External Transporter'),
        ('in_house', 'In-House')
    ], string='Default Transporter Type', config_parameter='trucking.default_transporter_type', default='external')

    driver_commission_account_id = fields.Many2one(
        related='company_id.driver_commission_account_id', 
        readonly=False
    )
    driver_commission_journal_id = fields.Many2one(
        related='company_id.driver_commission_journal_id', 
        readonly=False
    )
    receive_fuel_account_id = fields.Many2one(
        related='company_id.receive_fuel_account_id',
        readonly=False
    )
    receive_fuel_journal_id = fields.Many2one(
        related='company_id.receive_fuel_journal_id',
        readonly=False
    )

    trucking_allow_supplier_on_issue_fuel = fields.Boolean(
        related='company_id.trucking_allow_supplier_on_issue_fuel', readonly=False
    )
    trucking_allow_zero_advance = fields.Boolean(
        related='company_id.trucking_allow_zero_advance', readonly=False
    )
    trucking_enable_issue_fuel = fields.Boolean(
        related='company_id.trucking_enable_issue_fuel', readonly=False
    )
    trucking_allow_fuel_adjustments = fields.Boolean(
        related='company_id.trucking_allow_fuel_adjustments', readonly=False
    )
    trucking_in_house_fuel_process = fields.Selection(
        related='company_id.trucking_in_house_fuel_process', readonly=False
    )
    trucking_external_fuel_process = fields.Selection(
        related='company_id.trucking_external_fuel_process', readonly=False
    )
    trucking_pod_label = fields.Char(
        related='company_id.trucking_pod_label', readonly=False
    )
    trucking_auto_create_invoice = fields.Boolean(
        related='company_id.trucking_auto_create_invoice', readonly=False
    )
    trucking_allow_unconfirmed_pod_invoice = fields.Boolean(
        related='company_id.trucking_allow_unconfirmed_pod_invoice', readonly=False
    )
    trucking_customer_invoice_stage = fields.Selection(
        related='company_id.trucking_customer_invoice_stage', readonly=False
    )
    trucking_enable_driver_penalties = fields.Boolean(
        related='company_id.trucking_enable_driver_penalties', readonly=False
    )
    trucking_enable_transporter_penalties = fields.Boolean(
        related='company_id.trucking_enable_transporter_penalties', readonly=False
    )
    trucking_enable_demurrage = fields.Boolean(
        related='company_id.trucking_enable_demurrage', readonly=False
    )
    trucking_charge_billing_timing = fields.Selection(
        related='company_id.trucking_charge_billing_timing', readonly=False
    )
    trucking_demurrage_product_id = fields.Many2one(
        related='company_id.trucking_demurrage_product_id', readonly=False
    )
    trucking_penalty_product_id = fields.Many2one(
        related='company_id.trucking_penalty_product_id', readonly=False
    )

    trucking_commission_calc_trigger = fields.Selection(
        related='company_id.trucking_commission_calc_trigger', readonly=False
    )
    trucking_approval_workflow = fields.Selection(
        related='company_id.trucking_approval_workflow', readonly=False
    )
    trucking_allow_non_expense_deliveries = fields.Boolean(
        related='company_id.trucking_allow_non_expense_deliveries', readonly=False
    )
    trucking_allow_excess_delivered_qty = fields.Boolean(
        related='company_id.trucking_allow_excess_delivered_qty', readonly=False
    )
    trucking_analytic_strategy = fields.Selection(
        related='company_id.trucking_analytic_strategy', readonly=False
    )


    trucking_default_commission_type = fields.Selection(related='company_id.trucking_default_commission_type', readonly=False)
    trucking_default_commission_percentage = fields.Float(related='company_id.trucking_default_commission_percentage', readonly=False)
    trucking_default_commission_fixed = fields.Monetary(related='company_id.trucking_default_commission_fixed', readonly=False)
    trucking_default_driver_commission_product_id = fields.Many2one(
        related='company_id.trucking_default_driver_commission_product_id', 
        readonly=False
    )


    
    
    

    trucking_mandatory_field_ids = fields.One2many(related='company_id.trucking_mandatory_field_ids', readonly=False)
