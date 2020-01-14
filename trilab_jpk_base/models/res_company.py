# -*- coding: utf-8 -*-
from odoo import fields, models


class Company(models.Model):
    _inherit = "res.company"

    pl_tax_office_id = fields.Many2one('jpk.taxoffice', string='PL Tax Office')
    pl_county = fields.Char('County')
    pl_community = fields.Char('Community')
    pl_post = fields.Char('Post')
