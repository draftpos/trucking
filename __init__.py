from . import models
from . import wizard
from odoo import api, SUPERUSER_ID

def post_init_hook(env):
    companies = env['res.company'].search([])
    companies.sudo()._init_default_mandatory_fields()

