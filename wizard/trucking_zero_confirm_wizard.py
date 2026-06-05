from odoo import api, fields, models

class TruckingZeroConfirmWizard(models.TransientModel):
    _name = 'trucking.zero.confirm.wizard'
    _description = 'Confirm Zero Amount Request'

    load_id = fields.Many2one('trucking.load', string='Load', required=True)
    request_type = fields.Selection([('fuel', 'Fuel'), ('deposit', 'Deposit')], string='Type', required=True)
    message = fields.Text(string='Message', readonly=True)

    def action_confirm(self):
        self.ensure_one()
        if self.request_type == 'fuel':
            self.load_id.write({
                'fuel_approval_state': 'requested',
                'state': 'pending_approval'
            })
        elif self.request_type == 'deposit':
            self.load_id.write({
                'deposit_approval_state': 'requested',
                'state': 'pending_approval'
            })
