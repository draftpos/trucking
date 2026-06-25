from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class TruckingFuelWizard(models.TransientModel):
    _name = 'trucking.fuel.wizard'
    _description = 'Issue Fuel Wizard'

    load_id = fields.Many2one('trucking.load', string='Load', required=True)
    qty = fields.Float(string='Quantity (Litres)', required=True, default=0.0)
    cost_price = fields.Float(string='Cost Price', required=True, default=1.20)
    total_cost = fields.Float(string='Total Cost', compute='_compute_total_cost')
    has_issued_fuel = fields.Boolean(related='load_id.has_issued_fuel')

    @api.depends('qty', 'cost_price')
    def _compute_total_cost(self):
        for rec in self:
            rec.total_cost = rec.qty * rec.cost_price

    def action_confirm(self):
        self.ensure_one()
        if self.qty <= 0:
            raise UserError(_("Quantity must be greater than zero."))
        import logging
        _logger = logging.getLogger(__name__)
        _logger.info("DEBUG FUEL WIZARD: total_cost=%s, load_id=%s, total_per_load=%s", self.total_cost, self.load_id.id, self.load_id.total_per_load)
        
        # Validation removed as requested by user

        # Find or create Fuel Product
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
            
            # Initial stock for fuel if we just created it
            stock_location = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1).lot_stock_id
            if stock_location:
                self.env['stock.quant']._update_available_quantity(product, stock_location, 1000.0)

        # Check stock quantity
        stock_location = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1).lot_stock_id
        if not stock_location:
            raise UserError(_("No stock location found for the company."))
            
        available_qty = product.with_context(location=stock_location.id).free_qty
        if self.qty > available_qty:
            raise ValidationError(_("Requested quantity (%(req)s) exceeds available stock (%(avail)s) for Fuel.", req=self.qty, avail=available_qty))

        # Prepare analytic distribution if load has analytic account
        analytic_dist = {}
        if self.load_id.analytic_account_id:
            analytic_dist = {str(self.load_id.analytic_account_id.id): 100}

        # Perform stock.scrap
        scrap = self.env['stock.scrap'].create({
            'product_id': product.id,
            'product_uom_id': product.uom_id.id,
            'scrap_qty': self.qty,
            'location_id': stock_location.id,
            'origin': self.load_id.name,
            'analytic_distribution': analytic_dist,
            'trucking_load_id': self.load_id.id,
        })
        scrap.action_validate()

        return {'type': 'ir.actions.act_window_close'}
