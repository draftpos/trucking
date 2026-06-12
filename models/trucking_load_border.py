from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import datetime

class TruckingLoadBorder(models.Model):
    _name = 'trucking.load.border'
    _description = 'Load Border Tracking'
    _order = 'sequence, id'

    load_id = fields.Many2one('trucking.load', string='Load', required=True, ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)
    border_id = fields.Many2one('trucking.border', string='Border', required=True)
    
    eta = fields.Datetime(string='Expected Arrival')
    etd = fields.Datetime(string='Expected Departure')
    
    ata = fields.Datetime(string='Actual Arrival')
    atd = fields.Datetime(string='Actual Departure')

    arrival_status = fields.Char(string='Arrival Status', compute='_compute_status')
    departure_status = fields.Char(string='Departure Status', compute='_compute_status')

    @api.depends('eta', 'ata', 'etd', 'atd')
    def _compute_status(self):
        for rec in self:
            # Arrival Status
            if not rec.eta or not rec.ata:
                rec.arrival_status = ''
            else:
                diff = (rec.ata - rec.eta).total_seconds()
                if diff <= 0:
                    rec.arrival_status = 'On Time'
                else:
                    hours, remainder = divmod(diff, 3600)
                    minutes = remainder // 60
                    if hours > 0:
                        rec.arrival_status = f'Delayed by {int(hours)}h {int(minutes)}m'
                    else:
                        rec.arrival_status = f'Delayed by {int(minutes)}m'

            # Departure Status
            if not rec.etd or not rec.atd:
                rec.departure_status = ''
            else:
                diff = (rec.atd - rec.etd).total_seconds()
                if diff <= 0:
                    rec.departure_status = 'On Time'
                else:
                    hours, remainder = divmod(diff, 3600)
                    minutes = remainder // 60
                    if hours > 0:
                        rec.departure_status = f'Delayed by {int(hours)}h {int(minutes)}m'
                    else:
                        rec.departure_status = f'Delayed by {int(minutes)}m'

    @api.constrains('eta', 'etd', 'ata', 'atd', 'load_id')
    def _check_dates(self):
        for rec in self:
            # 1. Departures should not be before arrivals
            if rec.eta and rec.etd and rec.etd < rec.eta:
                raise ValidationError(_(f"Border {rec.border_id.name}: Expected Departure cannot be before Expected Arrival."))
            if rec.ata and rec.atd and rec.atd < rec.ata:
                raise ValidationError(_(f"Border {rec.border_id.name}: Actual Departure cannot be before Actual Arrival."))
                
            # 2. Timelines should fall between expected loading date and expected/actual delivery date
            load = rec.load_id
            
            # Start boundary (Loading Date)
            start_date = False
            if load.date_loaded:
                start_date = fields.Datetime.from_string(load.date_loaded)
            elif load.expected_loading_date:
                start_date = load.expected_loading_date
                
            # End boundary (Delivery Date)
            end_date = False
            if load.delivery_date:
                end_date = fields.Datetime.from_string(load.delivery_date)
            elif load.expected_delivery_date:
                end_date = fields.Datetime.from_string(load.expected_delivery_date)
                
            for dt, label in [(rec.eta, 'Expected Arrival'), (rec.etd, 'Expected Departure'), (rec.ata, 'Actual Arrival'), (rec.atd, 'Actual Departure')]:
                if not dt:
                    continue
                if start_date and dt.date() < start_date.date():
                    raise ValidationError(_(f"Border {rec.border_id.name if rec.border_id else ''}: {label} cannot be before the Loading Date."))
                if end_date and dt.date() > end_date.date():
                    raise ValidationError(_(f"Border {rec.border_id.name if rec.border_id else ''}: {label} cannot be after the Delivery Date."))

    @api.onchange('eta', 'etd', 'ata', 'atd', 'load_id')
    def _onchange_dates(self):
        for rec in self:
            warning_msgs = []
            
            # 1. Departures should not be before arrivals
            if rec.eta and rec.etd and rec.etd < rec.eta:
                warning_msgs.append("Expected Departure cannot be before Expected Arrival.")
                rec.etd = False
            if rec.ata and rec.atd and rec.atd < rec.ata:
                warning_msgs.append("Actual Departure cannot be before Actual Arrival.")
                rec.atd = False
                
            # 2. Timelines should fall between expected loading date and expected/actual delivery date
            if rec.load_id:
                load = rec.load_id
                
                # Start boundary (Loading Date)
                start_date = False
                if load.date_loaded:
                    start_date = fields.Datetime.from_string(load.date_loaded)
                elif load.expected_loading_date:
                    start_date = load.expected_loading_date
                    
                # End boundary (Delivery Date)
                end_date = False
                if load.delivery_date:
                    end_date = fields.Datetime.from_string(load.delivery_date)
                elif load.expected_delivery_date:
                    end_date = fields.Datetime.from_string(load.expected_delivery_date)
                    
                # Check ETA/ETD/ATA/ATD
                for dt, label, field_name in [(rec.eta, 'Expected Arrival', 'eta'), (rec.etd, 'Expected Departure', 'etd'), (rec.ata, 'Actual Arrival', 'ata'), (rec.atd, 'Actual Departure', 'atd')]:
                    if not dt:
                        continue
                    if start_date and dt.date() < start_date.date():
                        warning_msgs.append(f"{label} cannot be before the Loading Date.")
                        setattr(rec, field_name, False)
                    if end_date and dt.date() > end_date.date():
                        warning_msgs.append(f"{label} cannot be after the Delivery Date.")
                        setattr(rec, field_name, False)

            if warning_msgs:
                return {
                    'warning': {
                        'title': _("Validation Error"),
                        'message': "\n".join(warning_msgs)
                    }
                }
