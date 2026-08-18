from odoo import models, fields

class HrRuleParameter(models.Model):
    _inherit = 'hr.rule.parameter'

    name = fields.Char(translate=True)