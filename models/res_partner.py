from odoo import api, fields, models, _
from odoo.exceptions import AccessError

class ResPartner(models.Model):
    _inherit = 'res.partner'

    total_transporter_balance = fields.Monetary(string='Total Transporter Balance', compute='_compute_trucking_balances')
    total_customer_balance = fields.Monetary(string='Total Customer Balance', compute='_compute_trucking_balances')
    total_overdue_pods = fields.Integer(string='Total Overdue PODs', compute='_compute_trucking_balances')
    is_blacklisted_transporter = fields.Boolean(string="Blacklisted Transporter", default=False, tracking=True)
    is_supplier = fields.Boolean(string="Is a Supplier", default=False)
    is_customer = fields.Boolean(string="Is a Customer", default=False)
    contact_type = fields.Selection([
        ('customer', 'Customer'),
        ('transporter', 'Transporter'),
        ('driver', 'Driver'),
        ('supplier', 'Supplier')
    ], string='Contact Type')
    
    load_count = fields.Integer(string='Load Count', compute='_compute_load_stats')
    current_month_profit = fields.Monetary(string='Current Month Profit', compute='_compute_load_stats', currency_field='currency_id')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('is_supplier') or vals.get('contact_type') == 'supplier':
                if not self.env.su and not self.env.user.has_group('trucking.group_trucking_transporter_creator'):
                    raise AccessError(_("You do not have permission to create Transporters. Please contact an administrator."))
        return super(ResPartner, self).create(vals_list)

    @api.model
    def get_views(self, views, options=None):
        res = super(ResPartner, self).get_views(views, options)
        if self.env.context.get('res_partner_search_mode') == 'supplier':
            if not self.env.user.has_group('trucking.group_trucking_transporter_creator'):
                import lxml.etree as ET
                for view_type, view_data in res.get('views', {}).items():
                    if 'arch' in view_data:
                        doc = ET.fromstring(view_data['arch'])
                        doc.set('create', '0')
                        view_data['arch'] = ET.tostring(doc, encoding='unicode')
        return res

    def action_blacklist_transporter(self):
        for record in self:
            record.is_blacklisted_transporter = True

    def action_unblacklist_transporter(self):
        for record in self:
            record.is_blacklisted_transporter = False

    def _compute_trucking_balances(self):
        for partner in self:
            loads_as_transporter = self.env['trucking.load'].search([('transporter_id', '=', partner.id)])
            loads_as_customer = self.env['trucking.load'].search([('customer_id', '=', partner.id)])
            
            partner.total_transporter_balance = sum(loads_as_transporter.mapped('transporter_balance'))
            partner.total_customer_balance = sum(loads_as_customer.mapped('customer_balance'))
            partner.total_overdue_pods = len(loads_as_transporter.filtered(lambda l: l.state == 'overdue')) + len(loads_as_customer.filtered(lambda l: l.state == 'overdue'))

    def _compute_load_stats(self):
        today = fields.Date.context_today(self)
        start_of_month = today.replace(day=1)
        
        for partner in self:
            loads = self.env['trucking.load'].search([('customer_id', '=', partner.id)])
            partner.load_count = len(loads)
            
            # Current month loads based on date_loaded
            current_month_loads = loads.filtered(
                lambda l: l.date_loaded and l.date_loaded >= start_of_month
            )
            partner.current_month_profit = sum(current_month_loads.mapped('gross_profit'))

    def action_view_trucking_loads(self):
        self.ensure_one()
        return {
            'name': _('Loads'),
            'type': 'ir.actions.act_window',
            'res_model': 'trucking.load',
            'view_mode': 'list,form',
            'domain': [('customer_id', '=', self.id)],
            'context': {'default_customer_id': self.id},
        }
