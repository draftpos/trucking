from odoo import api, fields, models

class TruckingVehicle(models.Model):
    _name = 'trucking.vehicle'
    _description = 'Trucking Vehicle'
    _rec_name = 'reg_number'

    make = fields.Char(string='Make')
    model = fields.Char(string='Model')
    reg_number = fields.Char(string='Reg Number', required=True)
    partner_id = fields.Many2one('res.partner', string='Transporter / Owner', required=True)
    trailer_1_reg = fields.Char(string='Trailer 1 Reg No (Old)')
    trailer_2_reg = fields.Char(string='Trailer 2 Reg No (Old)')
    trailer_1_id = fields.Many2one('trucking.trailer', string='Trailer 1 Reg')
    trailer_2_id = fields.Many2one('trucking.trailer', string='Trailer 2 Reg')
    ownership_type = fields.Selection([
        ('company', 'Company Owned'),
        ('external', 'External Transporter Owned')
    ], string='Ownership', default='external', required=True)

    @api.onchange('ownership_type')
    def _onchange_ownership_type(self):
        if self.ownership_type == 'company':
            self.partner_id = self.env.company.partner_id
    @api.depends('reg_number', 'make', 'model')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"[{rec.reg_number}] {rec.make or ''} {rec.model or ''}".strip()

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        # When creating from a Many2one field with Create and Edit, Odoo often passes default_name
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
        
        records = super().create(vals_list)
        
        for record in records:
            if self.env.company.trucking_auto_create_analytic_for_truck and record.reg_number:
                analytic_plan = self.env.ref('analytic.analytic_plan_projects', raise_if_not_found=False)
                if not analytic_plan:
                    analytic_plan = self.env['account.analytic.plan'].sudo().search([], limit=1)
                    
                analytic_acc = self.env['account.analytic.account'].sudo().search([('name', '=', record.reg_number)], limit=1)
                if not analytic_acc and analytic_plan:
                    self.env['account.analytic.account'].sudo().create({
                        'name': record.reg_number,
                        'plan_id': analytic_plan.id,
                        'company_id': self.env.company.id,
                    })
                    
        return records

    def write(self, vals):
        if vals.get('ownership_type') == 'company':
            vals['partner_id'] = self.env.company.partner_id.id
        return super().write(vals)
