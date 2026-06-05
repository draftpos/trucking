from odoo import models

class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    def _create_payment_vals_from_wizard(self, batch_result):
        payment_vals = super()._create_payment_vals_from_wizard(batch_result)
        
        move_lines = batch_result.get('lines', self.env['account.move.line'])
        moves = move_lines.mapped('move_id')
        
        if moves:
            load = self.env['trucking.load'].search([
                '|', ('transporter_bill_id', 'in', moves.ids),
                     ('invoice_id', 'in', moves.ids)
            ], limit=1)
            
            if load:
                payment_vals['load_id'] = load.id
                
        return payment_vals
