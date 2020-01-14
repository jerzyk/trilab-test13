# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):

    _inherit = 'res.config.settings'

    gus_api_key = fields.Char(string='GUS API Key', config_parameter='trilab_gusregon.gus_api_key')
