from odoo import api, fields, models, _
from odoo.exceptions import UserError

class TruckingLoadCharge(models.Model):
    _name = 'trucking.load.charge'
    _description = 'Trucking Load Extra Charges (Demurrage/Penalty)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    load_id = fields.Many2one('trucking.load', string='Load', required=True, ondelete='cascade', tracking=True)
    charge_type = fields.Selection([
        ('demurrage', 'Demurrage'),
        ('penalty', 'Penalty')
    ], string='Charge Type', required=True, tracking=True)
    
    amount = fields.Monetary(string='Amount', required=True, tracking=True, currency_field='currency_id')
    reason = fields.Char(string='Reason', required=True, tracking=True)
    
    currency_id = fields.Many2one(related='load_id.currency_id', store=True, readonly=True)
    company_id = fields.Many2one(related='load_id.company_id', store=True, readonly=True)
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('billed', 'Billed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)
    
    vendor_bill_id = fields.Many2one('account.move', string='Transporter Vendor Bill', readonly=True)
    customer_invoice_id = fields.Many2one('account.move', string='Customer Invoice', readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                prefix = 'DEM' if vals.get('charge_type') == 'demurrage' else 'PEN'
                vals['name'] = self.env['ir.sequence'].next_by_code('trucking.load.charge.seq') or f'{prefix}/New'
        return super().create(vals_list)

    def action_cancel(self):
        for rec in self:
            if rec.state == 'billed':
                raise UserError(_("You cannot cancel a charge that has already been billed."))
            rec.state = 'cancelled'

    def action_draft(self):
        for rec in self:
            rec.state = 'draft'
