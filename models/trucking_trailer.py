from odoo import api, fields, models

class TruckingTrailer(models.Model):
    _name = 'trucking.trailer'
    _description = 'Trucking Trailer'
    _rec_name = 'reg_number'

    make = fields.Char(string='Make')
    model = fields.Char(string='Model')
    reg_number = fields.Char(string='Registration Number', required=True)
    partner_id = fields.Many2one('res.partner', string='Transporter / Owner')
    ownership_type = fields.Selection([
        ('company', 'Company Owned'),
        ('external', 'External Transporter Owned')
    ], string='Ownership', default='external', required=True)

    @api.onchange('ownership_type')
    def _onchange_ownership_type(self):
        if self.ownership_type == 'company':
            self.partner_id = self.env.company.partner_id
        else:
            self.partner_id = False
    @api.depends('reg_number', 'make', 'model')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"[{rec.reg_number}] {rec.make or ''} {rec.model or ''}".strip()

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'default_name' in self.env.context and not res.get('reg_number'):
            res['reg_number'] = self.env.context.get('default_name')
        elif 'name' in self.env.context and not res.get('reg_number'):
            res['reg_number'] = self.env.context.get('name')
            
        if res.get('ownership_type') == 'company' and not res.get('partner_id'):
            res['partner_id'] = self.env.company.partner_id.id
            
        return res

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('ownership_type') == 'company':
                vals['partner_id'] = self.env.company.partner_id.id
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('ownership_type') == 'company':
            vals['partner_id'] = self.env.company.partner_id.id
        return super().write(vals)
