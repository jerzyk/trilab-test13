# -*- coding: utf-8 -*-

from odoo import fields, models


class ResCompany(models.Model):

    _inherit = 'res.company'

    krd_env = fields.Selection([('prod', 'Production'), ('test', 'Testing')], default='test')
    krd_login = fields.Char('KRD Login')
    krd_pass = fields.Char('KRD Password')
