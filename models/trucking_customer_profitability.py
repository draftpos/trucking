from odoo import api, fields, models, tools

class TruckingCustomerProfitability(models.Model):
    _name = 'trucking.customer.profitability'
    _description = 'Customer and Truck Profitability Report'
    _auto = False

    load_id = fields.Many2one('trucking.load', string='Load', readonly=True)
    name = fields.Char(string='Order No', readonly=True)
    customer_id = fields.Many2one('res.partner', string='Customer', readonly=True)
    transporter_id = fields.Many2one('res.partner', string='Transporter', readonly=True)
    vehicle_id = fields.Many2one('trucking.vehicle', string='Truck', readonly=True)
    driver_id = fields.Many2one('res.partner', string='Driver', readonly=True)
    date_loaded = fields.Date(string='Date Loaded', readonly=True)
    delivery_date = fields.Date(string='Delivery Date', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('upcoming', 'Upcoming'),
        ('in_progress', 'In Progress'),
        ('overdue', 'In Progress (Overdue)'),
        ('delivered', 'Delivered'),
        ('invoiced', 'Delivered and Invoiced'),
        ('cancelled', 'Cancelled'),
    ], string='Status', readonly=True)
    
    invoiced_amount = fields.Float(string='Invoiced Amount', readonly=True)
    expense_amount = fields.Float(string='Expense Amount', readonly=True)
    transporter_cost = fields.Float(string='Transporter Cost', readonly=True)
    total_cost = fields.Float(string='Total Cost', readonly=True)
    net_profit = fields.Float(string='Gross Profit', readonly=True)
    load_count = fields.Integer(string='Loads', readonly=True)
    
    company_id = fields.Many2one('res.company', string='Company', readonly=True)

    def _query(self, with_clause='', fields={}, groupby='', from_clause=''):
        return """
            SELECT
                l.id as id,
                l.id as load_id,
                l.name as name,
                l.customer_id as customer_id,
                l.transporter_id as transporter_id,
                l.vehicle_id as vehicle_id,
                l.driver_id as driver_id,
                l.date_loaded as date_loaded,
                l.delivery_date as delivery_date,
                l.state as state,
                l.company_id as company_id,
                1 as load_count,
                COALESCE(l.invoiced_amount, 0.0) as invoiced_amount,
                (COALESCE(l.total_all_expenses, 0.0) + COALESCE(l.issued_fuel_cost, 0.0)) as expense_amount,
                COALESCE(l.total_per_load, 0.0) as transporter_cost,
                (COALESCE(l.total_all_expenses, 0.0) + COALESCE(l.issued_fuel_cost, 0.0) + COALESCE(l.total_per_load, 0.0)) as total_cost,
                (COALESCE(l.invoiced_amount, 0.0) - COALESCE(l.total_all_expenses, 0.0) - COALESCE(l.issued_fuel_cost, 0.0) - COALESCE(l.total_per_load, 0.0)) as net_profit
            FROM
                trucking_load l
        """

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (%s)""" % (self._table, self._query()))
