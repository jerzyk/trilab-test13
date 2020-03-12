# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):

    _inherit = 'res.config.settings'

    gus_api_key = fields.Char(string='GUS API Key', config_parameter='trilab_gusregon.gus_api_key')

    krd_env = fields.Selection(related='company_id.krd_env', readonly=False)
    krd_login = fields.Char('KRD Login', related='company_id.krd_login', readonly=False)
    krd_pass = fields.Char('KRD Password', related='company_id.krd_pass', readonly=False)
