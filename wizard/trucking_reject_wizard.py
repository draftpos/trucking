from odoo import api, fields, models

class TruckingRejectWizard(models.TransientModel):
    _name = 'trucking.reject.wizard'
    _description = 'Trucking Reject Wizard'

    reason = fields.Text(string='Reason', required=True)
    load_id = fields.Many2one('trucking.load', string='Load', required=True)
    reject_type = fields.Selection([('fuel', 'Fuel'), ('deposit', 'Deposit'), ('advance', 'Advance')], string='Reject Type', required=True)

    def action_reject(self):
        self.ensure_one()
        load = self.load_id
        if self.reject_type == 'fuel':
            load.fuel_approval_state = 'rejected'
            load.fuel_reject_reason = self.reason
            load.state = 'rejected'
            load.message_post(body=f"<b>Fuel Approval Rejected</b><br/>Reason: {self.reason}")
        elif self.reject_type == 'deposit':
            load.deposit_approval_state = 'rejected'
            load.deposit_reject_reason = self.reason
            load.state = 'rejected'
            load.message_post(body=f"<b>Deposit Approval Rejected</b><br/>Reason: {self.reason}")
        elif self.reject_type == 'advance':
            load.advance_approval_state = 'rejected'
            load.advance_reject_reason = self.reason
            load.state = 'rejected'
            load.message_post(body=f"<b>Advance Approval Rejected</b><br/>Reason: {self.reason}")
        return {'type': 'ir.actions.act_window_close'}
