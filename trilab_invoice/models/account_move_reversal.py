# noinspection PyProtectedMember
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountMoveReversal(models.TransientModel):

    _inherit = 'account.move.reversal'

    selected_correction_invoice = fields.Many2one('account.move')

    @api.model
    def default_get(self, fields_list):
        res = super(AccountMoveReversal, self).default_get(fields_list)

        if 'active_ids' in self.env.context:
            if len(self.env.context['active_ids']) > 1:
                raise ValidationError(_('Single invoice only'))

            move_ids = self.env['account.move'].browse(self.env.context['active_ids'])

            if move_ids.type in ['in_refund', 'out_refund']:
                res['selected_correction_invoice'] = move_ids.id
                move_ids = move_ids.refund_invoice_id

            res['refund_method'] = (len(move_ids) > 1 or move_ids.type == 'entry') and 'cancel' or 'refund'
            res['residual'] = len(move_ids) == 1 and move_ids.amount_residual or 0
            res['currency_id'] = len(move_ids.currency_id) == 1 and move_ids.currency_id.id or False
            res['move_type'] = len(move_ids) == 1 and move_ids.type or False

        return res

    @api.depends('move_id')
    def _compute_from_moves(self):

        move_ids = self.env.context['active_ids']
        if self.selected_correction_invoice:
            move_ids = self.selected_correction_invoice.refund_invoice_id.id

        move_ids = self.env['account.move'].browse(move_ids) \
            if self.env.context.get('active_model') == 'account.move' else self.move_id

        for record in self:
            record.residual = len(move_ids) == 1 and move_ids.amount_residual or 0
            record.currency_id = len(move_ids.currency_id) == 1 and move_ids.currency_id or False
            record.move_type = len(move_ids) == 1 and move_ids.type or False

    def reverse_moves(self):
        ctx = dict(self.env.context)

        if self.selected_correction_invoice:
            ctx['active_id'] = self.selected_correction_invoice.refund_invoice_id.id
            ctx['active_ids'] = [self.selected_correction_invoice.refund_invoice_id.id]

        rec = self.with_context(ctx)

        moves = self.env['account.move'].browse(self.env.context['active_ids']) \
            if self.env.context.get('active_model') == 'account.move' else rec.move_id

        default_values_list = []
        for move in moves:
            default_values_list.append({
                'ref': rec.reason,
                'date': rec.date or move.date,
                'invoice_date': move.is_invoice(include_receipts=True) and (rec.date or move.date) or False,
                'journal_id': rec.journal_id and rec.journal_id.id or move.journal_id.id,
                'invoice_payment_term_id': None,
                'auto_post': True if rec.date > fields.Date.context_today(rec) else False,
                'selected_correction_invoice': rec.selected_correction_invoice.id
            })

        if rec.refund_method == 'cancel':
            if any([vals.get('auto_post', False) for vals in default_values_list]):
                # noinspection PyProtectedMember
                new_moves = moves._reverse_moves(default_values_list)
            else:
                # noinspection PyProtectedMember
                new_moves = moves._reverse_moves(default_values_list, cancel=True)

        elif rec.refund_method == 'modify':
            # noinspection PyProtectedMember
            moves._reverse_moves(default_values_list, cancel=True)
            moves_vals_list = []
            for move in moves.with_context(include_business_fields=True):
                moves_vals_list.append(move.copy_data({
                    'invoice_payment_ref': move.name,
                    'date': rec.date or move.date,
                })[0])
            new_moves = self.env['account.move'].create(moves_vals_list)

        elif rec.refund_method == 'refund':
            # noinspection PyProtectedMember
            new_moves = moves.with_context(check_move_validity=False)._reverse_moves(default_values_list)

        else:
            return

        action = {
            'name': _('Reverse Moves'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
        }

        if len(new_moves) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': new_moves.id,
            })

        else:
            action.update({
                'view_mode': 'tree,form',
                'domain': [('id', 'in', new_moves.ids)],
            })

        return action
