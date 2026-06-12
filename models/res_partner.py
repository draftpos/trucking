from odoo import api, fields, models

class ResPartner(models.Model):
    _inherit = 'res.partner'

    total_transporter_balance = fields.Monetary(string='Total Transporter Balance', compute='_compute_trucking_balances')
    total_customer_balance = fields.Monetary(string='Total Customer Balance', compute='_compute_trucking_balances')
    total_overdue_pods = fields.Integer(string='Total Overdue PODs', compute='_compute_trucking_balances')
    is_blacklisted_transporter = fields.Boolean(string="Blacklisted Transporter", default=False, tracking=True)

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
