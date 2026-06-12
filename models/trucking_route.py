from odoo import api, fields, models

class TruckingRoute(models.Model):
    _name = 'trucking.route'
    _description = 'Trucking Route'

    source = fields.Char(string='Source', required=True)
    destination = fields.Char(string='Destination', required=True)
    name = fields.Char(string='Route Name', compute='_compute_name', store=True)
    distance = fields.Float(string='Distance (km)')
    is_cross_border = fields.Boolean(string='Cross Border Route', default=False)
    border_ids = fields.One2many('trucking.route.border', 'route_id', string='Borders')

    @api.depends('source', 'destination')
    def _compute_name(self):
        for rec in self:
            if rec.source and rec.destination:
                rec.name = f"{rec.source} TO {rec.destination}"
            elif rec.source:
                rec.name = rec.source
            elif rec.destination:
                rec.name = rec.destination
            else:
                rec.name = 'New Route'

class TruckingRouteBorder(models.Model):
    _name = 'trucking.route.border'
    _description = 'Route Border Sequence'
    _order = 'sequence, id'

    route_id = fields.Many2one('trucking.route', string='Route', required=True, ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)
    border_id = fields.Many2one('trucking.border', string='Border', required=True)
