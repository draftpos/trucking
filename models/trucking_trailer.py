from odoo import api, fields, models

class TruckingTrailer(models.Model):
    _name = 'trucking.trailer'
    _description = 'Trucking Trailer'
    _rec_name = 'reg_number'

    make = fields.Char(string='Make')
    model = fields.Char(string='Model')
    reg_number = fields.Char(string='Registration Number', required=True)
    partner_id = fields.Many2one('res.partner', string='Transporter / Owner')

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
        return res
