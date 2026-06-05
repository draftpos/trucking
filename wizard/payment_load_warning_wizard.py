from odoo import models, fields, api

class PaymentLoadWarningWizard(models.TransientModel):
    _name = 'payment.load.warning.wizard'
    _description = 'Payment Load Warning Wizard'

    payment_id = fields.Many2one('account.payment', required=True)

    def action_continue(self):
        return self.payment_id.with_context(ignore_load_warning=True).action_post()
