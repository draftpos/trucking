from odoo import api, fields, models

class TruckingRejectWizard(models.TransientModel):
    _name = 'trucking.reject.wizard'
    _description = 'Trucking Reject Wizard'

    reason = fields.Text(string='Reason', required=True)
    load_id = fields.Many2one('trucking.load', string='Load', required=True)
    reject_type = fields.Selection([
        ('fuel', 'Fuel'), 
        ('deposit', 'Deposit'), 
        ('advance', 'Advance'),
        ('demurrage', 'Demurrage'),
        ('penalty', 'Penalty')
    ], string='Reject Type', required=True)
    charge_id = fields.Many2one('trucking.load.charge', string='Charge Line')

    def action_reject(self):
        self.ensure_one()
        load = self.load_id
        if self.reject_type == 'fuel':
            load.fuel_approval_state = 'rejected'
            load.fuel_reject_reason = self.reason
            load.message_post(body=f"<b>Fuel Approval Rejected</b><br/>Reason: {self.reason}")
            load._check_auto_in_progress()
        elif self.reject_type == 'deposit':
            load.deposit_approval_state = 'rejected'
            load.deposit_reject_reason = self.reason
            load.message_post(body=f"<b>Deposit Approval Rejected</b><br/>Reason: {self.reason}")
            load._check_auto_in_progress()
        elif self.reject_type == 'advance':
            load.advance_approval_state = 'rejected'
            load.advance_reject_reason = self.reason
            load.state = 'rejected'
            load.message_post(body=f"<b>Advance Approval Rejected</b><br/>Reason: {self.reason}")
            load._check_auto_in_progress()
        elif self.reject_type in ('demurrage', 'penalty') and self.charge_id:
            self.charge_id.with_context(reject_reason=self.reason).action_reject()
        return {'type': 'ir.actions.act_window_close'}
