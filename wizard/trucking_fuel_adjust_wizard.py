from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class TruckingFuelAdjustWizard(models.TransientModel):
    _name = 'trucking.fuel.adjust.wizard'
    _description = 'Adjust Fuel Wizard'

    load_id = fields.Many2one('trucking.load', string='Load', required=True)
    qty = fields.Float(string='Adjust Quantity (Litres)', required=True, default=0.0)
    cost_price = fields.Float(string='Cost Price', required=True, default=0.0)
    issue_price = fields.Float(string='Issue Price (Sell)', required=True, default=0.0)
    total_cost = fields.Float(string='Total Cost', compute='_compute_total_cost')
    supplier_id = fields.Many2one('res.partner', string='Supplier', domain=[('supplier_rank', '>', 0)])
    allow_supplier = fields.Boolean(related='load_id.company_id.trucking_allow_supplier_on_issue_fuel')

    @api.model
    def default_get(self, fields_list):
        res = super(TruckingFuelAdjustWizard, self).default_get(fields_list)
        if 'load_id' in res:
            load = self.env['trucking.load'].browse(res['load_id'])
            if load.has_issued_fuel:
                res['qty'] = load.issued_fuel_qty
                res['cost_price'] = load.issued_fuel_rate
                res['issue_price'] = load.fuel_issue_price
                if load.issued_fuel_supplier_id:
                    res['supplier_id'] = load.issued_fuel_supplier_id.id
        return res

    @api.depends('qty', 'cost_price')
    def _compute_total_cost(self):
        for rec in self:
            rec.total_cost = rec.qty * rec.cost_price

    def action_confirm(self):
        self.ensure_one()
        if not self.env.su and not self.env.user.has_group('trucking.group_trucking_issue_fuel'):
            from odoo.exceptions import AccessError
            raise AccessError(_("You do not have permission to adjust fuel."))
        if self.qty <= 0:
            raise UserError(_("Quantity must be greater than zero."))
            
        if not self.load_id.has_issued_fuel:
            raise UserError(_("No fuel has been issued yet to adjust. Use Issue Fuel instead."))
            
        old_qty = self.load_id.issued_fuel_qty
        old_rate = self.load_id.issued_fuel_rate
        old_supplier = self.load_id.issued_fuel_supplier_id.name if self.load_id.issued_fuel_supplier_id else 'N/A'

        # Reverse existing fuel
        self.load_id.with_context(is_adjust=True).action_reverse_issued_fuel()
        
        # Now re-issue the new fuel using the Issue Fuel Wizard logic
        issue_wizard = self.env['trucking.fuel.wizard'].create({
            'load_id': self.load_id.id,
            'qty': self.qty,
            'cost_price': self.cost_price,
            'issue_price': self.issue_price,
            'supplier_id': self.supplier_id.id if self.supplier_id else False,
        })
        issue_wizard.action_confirm()
        
        self.load_id.fuel_banner_text = 'Fuel Adjusted'
        
        # Log the adjustment
        new_supplier = self.supplier_id.name if self.supplier_id else 'N/A'
        
        date_str = fields.Datetime.now().strftime('%Y-%m-%d %H:%M')
        user_name = self.env.user.name
        log_msg = f"<li><span class='text-warning'>Fuel adjusted on <b>{date_str}</b> by <b>{user_name}</b> from <b>{old_qty}L</b> ({old_supplier}) to <b>{self.qty}L</b> ({new_supplier}).</span></li>"
        
        # Overwrite the old logs entirely with the adjustment banner!
        self.load_id.fuel_issue_logs = f"<ul style='margin-bottom:0; padding-left:20px;'>{log_msg}</ul>"

        msg = f"<b>Fuel Adjusted</b><br/>User adjusted fuel.<br/>" \
              f"<b>Original:</b> {old_qty}L from {old_supplier} at ${old_rate:.2f}/L.<br/>" \
              f"<b>New:</b> {self.qty}L from {new_supplier} at ${self.cost_price:.2f}/L."
        self.load_id.message_post(body=msg)

        return {'type': 'ir.actions.act_window_close'}
