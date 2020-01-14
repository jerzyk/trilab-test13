# -*- coding: utf-8 -*-
from datetime import timedelta

# noinspection PyProtectedMember
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, formatLang
from odoo.exceptions import ValidationError
import json
import logging

_logger = logging.getLogger(__name__)


# noinspection DuplicatedCode,PyProtectedMember
class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.depends('refund_invoice_id')
    def compute_original_invoice_line_ids(self):
        for invoice in self:
            if invoice.type not in ['in_refund', 'out_refund'] or not invoice.refund_invoice_id:
                invoice.original_invoice_line_ids = False
                return
            if not invoice.selected_correction_invoice:
                invoice.original_invoice_line_ids = invoice.refund_invoice_id.invoice_line_ids\
                    .filtered(lambda l: not l.exclude_from_invoice_tab).ids
            else:
                invoice.original_invoice_line_ids = invoice.selected_correction_invoice.corrected_invoice_line_ids\
                    .filtered(lambda l: not l.exclude_from_invoice_tab).ids

    @api.constrains('refund_invoice_id', 'selected_correction_invoice')
    def check_correction_invoice(self):
        for invoice in self:
            if invoice.refund_invoice_id and not invoice.selected_correction_invoice:
                if self.search([('refund_invoice_id', '=', self.refund_invoice_id.id),
                                ('selected_correction_invoice', '=', False)], count=True) > 1:
                    raise ValidationError(_('It is not possible to issue two direct corrections for one invoice.'))
            if invoice.refund_invoice_id and invoice.selected_correction_invoice:
                if self.search([('refund_invoice_id', '=', self.refund_invoice_id.id),
                                ('selected_correction_invoice', '=', invoice.selected_correction_invoice.id)],
                               count=True) > 1:
                    raise ValidationError(_('It is not possible to issue two direct corrections for one correction.'))

    @api.constrains('state')
    def clock_moving_back(self):
        for invoice in self:
            if invoice.state not in ['draft', 'cancel']:
                continue
            if invoice.correction_invoices_len:
                raise ValidationError(_('An invoice cannot be modified if it is associated with corrections.\n'
                                        'Delete corrections or create a new correction to an existing correction'))

    def get_connected_corrections(self):
        selected_invoice = self
        corrections = self.env['account.move']
        while True:
            correction = self.search([('selected_correction_invoice', '=', selected_invoice.id)])
            if not correction:
                break
            selected_invoice = correction
            corrections += selected_invoice
        return corrections

    def compute_correction_invoices_len(self):
        for invoice in self:
            if invoice.type in ['in_invoice', 'out_invoice']:
                invoice.correction_invoices_len = len(invoice.correction_invoices_ids)
            else:
                corrections = invoice.get_connected_corrections()
                invoice.correction_invoices_len = len(corrections)

    correction_invoices_ids = fields.One2many('account.move', 'refund_invoice_id')
    correction_invoices_len = fields.Integer(compute=compute_correction_invoices_len, store=False)
    refund_invoice_id = fields.Many2one('account.move')
    invoice_line_ids = fields.One2many(domain=[('exclude_from_invoice_tab', '=', False)])

    original_invoice_line_ids = fields.Many2many(comodel_name='account.move.line',
                                                 string='Original Invoice Lines',
                                                 compute=compute_original_invoice_line_ids,
                                                 readonly=True, store=False, track_visibility=False)
    original_amount_untaxed = fields.Monetary(string='Original Untaxed Amount', readonly=True,
                                              related='refund_invoice_id.amount_untaxed', track_visibility=False)
    original_amount_by_group = fields.Binary(string='Original Tax amount by group',
                                             related='refund_invoice_id.amount_by_group', track_visibility=False)
    original_amount_total = fields.Monetary(string='Original Total', readonly=True,
                                            related='refund_invoice_id.amount_total', track_visibility=False)

    corrected_invoice_line_ids = fields.One2many(comodel_name='account.move.line', inverse_name='move_id',
                                                 domain=[('exclude_from_invoice_tab', '=', False),
                                                         ('corrected_line', '=', True)])
    corrected_amount_untaxed = fields.Monetary(string='Corrected Untaxed Amount', readonly=True)
    corrected_amount_by_group = fields.Binary(string='Corrected Tax amount by group')
    corrected_amount_total = fields.Monetary(string='Corrected Total', readonly=True)

    selected_correction_invoice = fields.Many2one('account.move')

    x_invoice_sale_date = fields.Date(string='Sale date')
    x_invoice_amount_summary = fields.Binary(string="Tax amount summary", compute='_compute_invoice_taxes_by_group')

    @api.model
    def create(self, vals):
        invoice = super(AccountMove, self).create(vals)
        if invoice.type in ['in_refund', 'out_refund']:
            invoice.refund_invoice_id = vals.get('reversed_entry_id')

            if invoice.selected_correction_invoice:
                invoice.invoice_line_ids.unlink()
                for line in invoice.selected_correction_invoice.corrected_invoice_line_ids:
                    copied = line.copy(default={'move_id': invoice.id,
                                                'price_unit': -line.price_unit,
                                                'corrected_line': False})
                    copied.price_unit = -line.price_unit
                    copied.run_onchanges()
                for line in invoice.selected_correction_invoice.corrected_invoice_line_ids:
                    copied = line.copy(default={'move_id': invoice.id,
                                                'price_unit': line.price_unit,
                                                'corrected_line': True})
                    copied.price_unit = line.price_unit
                    copied.run_onchanges()
            else:
                for line in invoice.invoice_line_ids:
                    copied = line.copy(default={'corrected_line': True, 'move_id': invoice.id})
                    copied.price_unit = -line.price_unit
                    copied.run_onchanges()

        invoice._onchange_invoice_line_ids()
        invoice._compute_invoice_taxes_by_group()

        return invoice

    @api.constrains('corrected_invoice_line_ids', 'type')
    def constrains_correction_data(self):
        for invoice in self:
            if invoice.type in ['in_refund', 'out_refund'] and invoice.corrected_invoice_line_ids:

                for line in invoice.invoice_line_ids:
                    line.run_onchanges()

                invoice._onchange_invoice_line_ids()
                invoice._compute_invoice_taxes_by_group()

    def correction_invoices_view(self):
        view_data = {
            'name': _("Correction Invoices"),
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'type': 'ir.actions.act_window'
        }

        if self.type in ['in_invoice', 'out_invoice']:
            view_data['domain'] = [('id', 'in', self.correction_invoices_ids.ids)]

        else:
            view_data['domain'] = [('id', 'in', self.get_connected_corrections().ids)]

        return view_data

    def action_reverse(self):
        ctx = dict(self.env.context)
        rec = self

        if self.refund_invoice_id:
            ctx['active_id'] = self.refund_invoice_id.id
            ctx['active_ids'] = [self.refund_invoice_id.id]
            rec = self.refund_invoice_id
        rec = rec.with_context(ctx)
        action = rec.env.ref('account.action_view_account_move_reversal').read()[0]
        if rec.is_invoice():
            action['name'] = _('Credit Note')

        return action

    # changes in existing methods

    def _check_balanced(self):
        pass

    def post(self):
        date_format = self.env['res.lang']._lang_get(self.env.user.lang).date_format

        for move in self:
            if not move.line_ids.filtered(lambda _line: not _line.display_type):
                raise UserError(_('You need to add a line before posting.'))

            if move.auto_post and move.date > fields.Date.today():
                raise UserError(_("This move is configured to be auto-posted on %s") % move.date.strftime(date_format))

            if not move.partner_id:
                if move.is_sale_document():
                    raise UserError(_("The field 'Customer' is required, please complete it "
                                      "to validate the Customer Invoice."))

                elif move.is_purchase_document():
                    raise UserError(_("The field 'Vendor' is required, please complete it "
                                      "to validate the Vendor Bill."))

            if not move.invoice_date and move.is_invoice(include_receipts=True):
                move.invoice_date = fields.Date.context_today(self)
                move.with_context(check_move_validity=False)._onchange_invoice_date()

            if (move.company_id.tax_lock_date and move.date <= move.company_id.tax_lock_date)\
                    and (move.line_ids.tax_ids or move.line_ids.tag_ids):
                move.date = move.company_id.tax_lock_date + timedelta(days=1)
                move.with_context(check_move_validity=False)._onchange_currency()

        self.mapped('line_ids').create_analytic_lines()

        for move in self:
            if move.auto_post and move.date > fields.Date.today():
                raise UserError(_("This move is configured to be auto-posted on {}"
                                  .format(move.date.strftime(date_format))))

            move.message_subscribe([p.id for p in [move.partner_id, move.commercial_partner_id]
                                    if p not in move.sudo().message_partner_ids])

            to_write = {'state': 'posted'}

            if move.name == '/':
                # Get the journal's sequence.
                sequence = move._get_sequence()
                if not sequence:
                    raise UserError(_('Please define a sequence on your journal.'))

                # Consume a new number.
                to_write['name'] = sequence.next_by_id(sequence_date=move.date)

            move.write(to_write)

            # Compute 'ref' for 'out_invoice'.
            if move.type == 'out_invoice' and not move.invoice_payment_ref:
                to_write = {
                    'invoice_payment_ref': move._get_invoice_computed_reference(),
                    'line_ids': []
                }
                for line in move.line_ids.filtered(lambda _line:
                                                   _line.account_id.user_type_id.type in ('receivable', 'payable')):
                    to_write['line_ids'].append((1, line.id, {'name': to_write['invoice_payment_ref']}))
                move.write(to_write)

            if move == move.company_id.account_opening_move_id and \
                    not move.company_id.account_bank_reconciliation_start:
                move.company_id.account_bank_reconciliation_start = move.date

        for move in self:
            if not move.partner_id:
                continue
            if move.type.startswith('out_'):
                move.partner_id._increase_rank('customer_rank')
            elif move.type.startswith('in_'):
                move.partner_id._increase_rank('supplier_rank')
            else:
                continue

    def _compute_payments_widget_to_reconcile_info(self):
        for move in self:
            move.invoice_outstanding_credits_debits_widget = json.dumps(False)
            move.invoice_has_outstanding = False

            if move.state != 'posted' or move.invoice_payment_state != 'not_paid' or\
                    not move.is_invoice(include_receipts=True):
                continue
            pay_term_line_ids = move.line_ids.filtered(lambda _line:
                                                       _line.account_id.user_type_id.type in ('receivable', 'payable'))

            domain = [('account_id', 'in', pay_term_line_ids.mapped('account_id').ids),
                      '|', ('move_id.state', '=', 'posted'),
                      '&', ('move_id.state', '=', 'draft'),
                      ('journal_id.post_at', '=', 'bank_rec'),
                      ('partner_id', '=', move.commercial_partner_id.id),
                      ('reconciled', '=', False),
                      '|', ('amount_residual', '!=', 0.0),
                      ('amount_residual_currency', '!=', 0.0)]

            if move.is_inbound():
                if move.amount_total < 0:
                    domain.extend([('credit', '=', 0), ('debit', '>', 0)])
                    type_payment = _('Outstanding debits')
                else:
                    domain.extend([('credit', '>', 0), ('debit', '=', 0)])
                    type_payment = _('Outstanding credits')
            else:
                if move.amount_total < 0:
                    domain.extend([('credit', '>', 0), ('debit', '=', 0)])
                    type_payment = _('Outstanding credits')
                else:
                    domain.extend([('credit', '=', 0), ('debit', '>', 0)])
                    type_payment = _('Outstanding debits')

            info = {'title': '', 'outstanding': True, 'content': [], 'move_id': move.id}
            lines = self.env['account.move.line'].search(domain)
            currency_id = move.currency_id
            if len(lines) != 0:
                for line in lines:
                    # get the outstanding residual value in invoice currency
                    if line.currency_id and line.currency_id == move.currency_id:
                        amount_to_show = abs(line.amount_residual_currency)
                    else:
                        currency = line.company_id.currency_id
                        amount_to_show = currency._convert(abs(line.amount_residual), move.currency_id, move.company_id,
                                                           line.date or fields.Date.today())
                    if float_is_zero(amount_to_show, precision_rounding=move.currency_id.rounding):
                        continue

                    info['content'].append({
                        'journal_name': line.ref or line.move_id.name,
                        'amount': amount_to_show,
                        'currency': currency_id.symbol,
                        'id': line.id,
                        'position': currency_id.position,
                        'digits': [69, move.currency_id.decimal_places],
                        'payment_date': fields.Date.to_string(line.date),
                    })

                info['title'] = type_payment
                move.invoice_outstanding_credits_debits_widget = json.dumps(info)
                move.invoice_has_outstanding = True

    def _compute_invoice_taxes_by_group(self):
        for invoice in self:
            lang_env = invoice.with_context(lang=invoice.partner_id.lang).env
            tax_lines = invoice.line_ids.filtered(lambda _line: _line.tax_line_id)
            pln = self.env.ref('base.PLN')
            sign = -1 if invoice.type.endswith('_refund') else 1
            res = {}
            summary = {'base': 0.0, 'amount': 0.0, 'in_pln': 0.0}

            # There are as many tax line as there are repartition lines
            done_taxes = set()
            for line in tax_lines:
                res.setdefault(line.tax_line_id.tax_group_id, {'base': 0.0, 'amount': 0.0, 'in_pln': 0.0})
                res[line.tax_line_id.tax_group_id]['amount'] += line.price_subtotal
                res[line.tax_line_id.tax_group_id]['in_pln'] += -line.balance
                summary['amount'] += line.price_subtotal
                summary['in_pln'] += -line.balance
                tax_key_add_base = tuple(invoice._get_tax_key_for_group_add_base(line))
                if tax_key_add_base not in done_taxes:
                    # The base should be added ONCE
                    res[line.tax_line_id.tax_group_id]['base'] += line.tax_base_amount
                    summary['base'] += line.tax_base_amount
                    done_taxes.add(tax_key_add_base)

            res = sorted(res.items(), key=lambda l: l[0].sequence)

            invoice.amount_by_group = [(
                group.name,
                amounts['amount'] * sign,
                amounts['base'] * sign,
                formatLang(lang_env, amounts['amount'] * sign, currency_obj=invoice.currency_id),
                formatLang(lang_env, amounts['base'] * sign, currency_obj=invoice.currency_id),
                len(res),
                group.id,
                formatLang(lang_env, amounts['in_pln'] * sign, currency_obj=pln),
            ) for group, amounts in res]

            invoice.x_invoice_amount_summary = {
                'base': formatLang(lang_env, summary['base'] * sign, currency_obj=invoice.currency_id),
                'amount': formatLang(lang_env, summary['amount'] * sign, currency_obj=invoice.currency_id),
                'in_pln': formatLang(lang_env, summary['in_pln'] * sign, currency_obj=pln),
                'total': formatLang(lang_env, (summary['base'] + summary['amount']) * sign,
                                    currency_obj=invoice.currency_id)
            }

    def action_reverse_pl(self):
        action = self.env.ref('trilab_invoice.action_view_account_move_reversal_pl').read()[0]

        if self.is_invoice():
            action['name'] = _('Credit Note PL')

        return action
