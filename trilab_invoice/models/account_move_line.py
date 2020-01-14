# -*- coding: utf-8 -*-

from odoo import api, fields, models


class AccountMoveLine(models.Model):

    _inherit = 'account.move.line'

    _sql_constraints = [
        (
            'check_credit_debit',
            'CHECK(True)',
            'Wrong credit or debit value in accounting entry!'
        )
    ]

    corrected_line = fields.Boolean()

    def compute_inverse_values(self):
        for line in self:
            sign = -1 if line.corrected_line else 1
            line.price_unit_inverse = sign * line.price_unit
            line.price_subtotal_inverse = sign * line.price_subtotal
            line.price_total_inverse = sign * line.price_total

    @api.onchange('price_unit_inverse', 'price_subtotal_inverse', 'price_total_inverse')
    def set_inverse_values(self):
        for line in self:
            line.price_unit = -line.price_unit_inverse
            line.price_subtotal = -line.price_subtotal_inverse
            line.price_total = -line.price_total_inverse

    price_unit_inverse = fields.Float(compute=compute_inverse_values, store=False, readonly=False)
    price_subtotal_inverse = fields.Float(compute=compute_inverse_values, store=False, readonly=False)
    price_total_inverse = fields.Float(compute=compute_inverse_values, store=False, readonly=False)

    def run_onchanges(self):
        self._onchange_mark_recompute_taxes()
        self._onchange_balance()
        self._onchange_debit()
        self._onchange_credit()
        self._onchange_amount_currency()
        self._onchange_price_subtotal()
        self._onchange_currency()
