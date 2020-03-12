# -*- coding: utf-8 -*-

# noinspection PyProtectedMember
from odoo import fields, models, _


class AccountMove(models.Model):
    _inherit = "account.move"

    pl_vat_date = fields.Date(string=_('VAT Date'), index=True)

    def post(self):
        response = super(AccountMove, self).post()

        for move in self:
            if move.is_invoice(include_receipts=True):
                date = None
                if move.invoice_date:
                    if move.type in ('out_invoice', 'out_refund') and hasattr(move, 'x_invoice_sale_date'):
                        date = move.x_invoice_sale_date
                    elif move.type in ('in_invoice', 'in_refund'):
                        date = move.invoice_date
                else:
                    date = move.date
                move.write({'pl_vat_date': date})

        return response
