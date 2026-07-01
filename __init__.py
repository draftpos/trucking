from . import models
from . import wizard
from odoo import api, SUPERUSER_ID

def post_init_hook(env):
    companies = env['res.company'].search([])
    for company in companies:
        company._setup_default_mandatory_fields()
