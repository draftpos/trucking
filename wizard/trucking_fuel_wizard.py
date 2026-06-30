from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class TruckingFuelWizard(models.TransientModel):
    _name = 'trucking.fuel.wizard'
    _description = 'Issue Fuel Wizard'

    load_id = fields.Many2one('trucking.load', string='Load', required=True)
    qty = fields.Float(string='Quantity (Litres)', required=True, default=0.0)
    cost_price = fields.Float(string='Cost Price', required=True, default=1.20)
    issue_price = fields.Float(string='Issue Price (Sell)', required=True, default=1.50)
    total_cost = fields.Float(string='Total Cost', compute='_compute_total_cost')
    total_selling = fields.Float(string='Total Selling', compute='_compute_total_cost')
    has_issued_fuel = fields.Boolean(related='load_id.has_issued_fuel')
    supplier_id = fields.Many2one('res.partner', string='Supplier', domain=[('supplier_rank', '>', 0)])
    allow_supplier = fields.Boolean(related='load_id.company_id.trucking_allow_supplier_on_issue_fuel')

    @api.depends('qty', 'cost_price', 'issue_price')
    def _compute_total_cost(self):
        for rec in self:
            rec.total_cost = rec.qty * rec.cost_price
            rec.total_selling = rec.qty * rec.issue_price

    def action_confirm(self):
        self.ensure_one()
        if self.qty <= 0:
            raise UserError(_("Quantity must be greater than zero."))
        
        supplier_to_use = self.supplier_id
        if not supplier_to_use:
            default_supplier = self.env['res.partner'].sudo().search([('name', '=', 'Default Supplier')], limit=1)
            if not default_supplier:
                default_supplier = self.env['res.partner'].sudo().create({'name': 'Default Supplier', 'supplier_rank': 1})
            supplier_to_use = default_supplier

        # Update Load tracking fields but DO NOT issue accounting documents yet
        self.load_id.write({
            'issued_fuel_qty': self.qty,
            'issued_fuel_rate': self.cost_price,
            'fuel_issue_price': self.issue_price,
            'fuel_issue_date': fields.Datetime.now(),
            'fuel_issue_user_id': self.env.user.id,
            'issued_fuel_supplier_id': supplier_to_use.id,
            'fuel_litres': self.qty,
            'fuel_unit_price': self.cost_price,
            'fuel_amount': self.qty * self.issue_price,
        })
        
        # Trigger fuel approval request automatically
        self.load_id.action_request_fuel_approval()
        
        # Log to Chatter
        total_val = self.qty * self.cost_price
        self.load_id.message_post(body=f"<b>Fuel Issue Requested</b><br/>{self.qty}L requested from {supplier_to_use.name} at {self.cost_price}/L. Total: ${total_val:.2f}.")

        return {'type': 'ir.actions.act_window_close'}
