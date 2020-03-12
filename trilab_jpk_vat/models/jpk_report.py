# -*- coding: utf-8 -*-
import datetime
import re
from itertools import groupby

from lxml import etree

# noinspection PyProtectedMember
from odoo import models, api, _, release, fields
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, date_utils


class JpkReport(models.AbstractModel):
    _inherit = 'account.report'
    _name = 'account.report.jpk_vat'
    _description = 'JPK VAT Report'

    filter_multi_company = None
    filter_date = {'date_from': '', 'date_to': '', 'filter': 'last_month'}
    # filter_pl_vat_date = {'date_from': '', 'date_to': '', 'filter': 'last_month'}
    filter_correction_number = '0'
    filter_all_entries = False

    grouping_columns = ['nrkontrahenta', 'nazwakontrahenta', 'adreskontrahenta', 'dowodsprzedazyzakupu',
                        'datawystawienia', 'datasprzedazy', 'datazakupu', 'datawplywu']

    all_columns = grouping_columns + ['jpkmarkup', 'kwota']

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def _get_columns_name(self, options):
        columns_header = [
            {'name': 'Sekcja JPK'},
            {'name': '#'},
            {'name': 'NrKontrahenta'},
            {'name': 'NazwaKontrahenta'},
            {'name': 'AdresKontrahenta'},
            {'name': 'DowodSprzedazyZakupu'},
            {'name': 'DataWystawienia'},
            {'name': 'DataSprzedazy'},
            {'name': 'DataZakupu'},
            {'name': 'DataWplywu'},
            {'name': 'JPKMarkup'},
            {'name': 'kwota', 'class': 'number'}]
        return columns_header

    # noinspection PyUnusedLocal
    @api.model
    def _get_lines(self, options, line_id=None):
        context = self.env.context

        # noinspection SqlResolve
        query = """SELECT aat.jpk_section                             AS JPKSection,
       COALESCE(p.vat, 'brak')                     AS NrKontrahenta,
       p.name                                      AS NazwaKontrahenta,
       p.street || ', ' || p.zip || ', ' || p.city AS AdresKontrahenta,
       (CASE
            WHEN aj.type = 'sale'
                THEN am.name
            ELSE aml.ref
           END)                                    AS DowodSprzedazyZakupu,
       am.invoice_date                             AS DataWystawienia,
       am.pl_vat_date                              AS DataSprzedazy,
       am.date                                     AS DataZakupu,
       am.pl_vat_date                              AS DataWplywu,
       (CASE
            WHEN aml.tax_line_id IS NOT NULL
                then TRUE
            ELSE FALSE
           END)                                    AS isTax,
       aat.jpk_markup                              AS JPKMarkup,
       SUM(CASE
               WHEN am.type = 'out_refund'
                   THEN - aml.balance
               WHEN am.type = 'in_refund'
                   THEN aml.balance
               ELSE ABS(aml.balance)
           END)                                    AS kwota
FROM account_move AS am
         LEFT JOIN res_partner p ON am.partner_id = p.id
         LEFT JOIN account_journal aj ON am.journal_id = aj.id
         LEFT JOIN account_move_line aml ON aml.move_id = am.id
         LEFT JOIN account_account_tag_account_move_line_rel aatmr ON aatmr.account_move_line_id = aml.id
         LEFT JOIN account_account_tag aat ON aat.id = aatmr.account_account_tag_id
         LEFT JOIN jpk_document_type dt ON dt.id = aat.jpk_document_type
WHERE dt.name = 'JPK_VAT'
  AND aml.tax_exigible = TRUE
 AND aj.type IN %s
 AND am.pl_vat_date >= %s
 AND am.pl_vat_date <= %s
 AND am.company_id = %s
GROUP BY am.id, JPKSection, NrKontrahenta, NazwaKontrahenta, AdresKontrahenta, DowodSprzedazyZakupu, DataWystawienia,
         isTax, JPKMarkup
ORDER BY JPKsection, DataWystawienia, DowodSprzedazyZakupu"""

        # params = (('sale', 'purchase'), context.get('pl_vat_date_from'), context.get('pl_vat_date_to'),
        #           self.env.user.company_id.id)
        params = (('sale', 'purchase'), context.get('date_from'), context.get('date_to'),
                  self.env.user.company_id.id)
        self.env.cr.execute(query, params)

        dict_output = context.get('dict_output', False)

        if dict_output:
            lines = {}
        else:
            lines = []

        for jpk_section, group in groupby(self.env.cr.dictfetchall(), lambda x: x['jpksection']):
            section = []
            counter = 1

            for sk, sub_group in groupby(group, lambda x: [x[k] for k in self.grouping_columns]):

                if context.get('print_mode', False):
                    # e.g. excel output
                    for counter, row in enumerate(sub_group):
                        lines.append({
                            'id': '{}:{}:{}'.format(jpk_section, counter, row['jpkmarkup']),
                            # 'caret_options': 'account.move.line',
                            'model': 'account.move.line',
                            # 'depth': 1,
                            'name': row['jpksection'],
                            # 'parent_id': master_line['id'],
                            'columns': [{}] + [{'name': row[k]} for k in self.all_columns],
                            'unfoldable': False,
                            'unfolded': False,
                            'isTax': row['istax']
                        })
                else:
                    master_line = None

                    for row in sub_group:
                        # update dates for rows
                        if jpk_section == 'SprzedazWiersz':
                            row['datawplywu'] = row['datazakupu'] = None
                        elif jpk_section == 'ZakupWiersz':
                            row['datasprzedazy'] = row['datawystawienia'] = None

                        if not master_line:
                            if dict_output:
                                master_line = {
                                    'data': row,
                                    'counter': counter,
                                    'children': []
                                }
                            else:
                                master_line = {
                                    'id': 'hierarchy',
                                    # 'parent_id': '{}:{}'.format(jpk_section, counter),
                                    # 'caret_options': 'account.move.line',
                                    'model': 'account.move.line',
                                    'name': jpk_section,
                                    'level': 1,
                                    'columns': [{'name': counter}] + [{'name': row[k]} for k in self.grouping_columns] +
                                               [{}, {}],
                                    'unfoldable': False,
                                    'unfolded': True,
                                    'children': []
                                }

                        if dict_output:
                            master_line['children'].append(row)
                        else:
                            master_line['children'].append({
                                'id': '{}:{}:{}'.format(jpk_section, counter, row['jpkmarkup']),
                                # 'caret_options': 'account.move.line',
                                # 'model': 'account.move.line',
                                'depth': 1,
                                # 'name': row['jpkmarkup'],
                                'parent_id': master_line['id'],
                                'columns': [{}] * (len(self.grouping_columns) + 1) + [{'name': row['jpkmarkup']},
                                                                                      {'name': row['kwota']}],
                                'unfoldable': False,
                                'unfolded': False,
                                'isTax': row['istax']
                            })

                    section.append(master_line)
                    counter += 1

            if not context.get('print_mode', False):
                if dict_output:
                    lines[jpk_section] = section
                else:
                    for master in section:
                        children = master.pop('children')
                        lines.append(master)
                        lines.extend(children)

        return lines

    @api.model
    def _create_hierarchy(self, lines):
        return lines

    @api.model
    def _get_report_name(self):
        return _('Jednolity Plik Kontrolny - VAT')

    # # noinspection DuplicatedCode
    # @api.model
    # def _init_filter_pl_vat_date(self, options, previous_options=None):
    #     if self.filter_pl_vat_date is None:
    #         return
    #
    #     # Default values.
    #     mode = self.filter_pl_vat_date.get('mode', 'range')
    #     options_filter = self.filter_pl_vat_date.get('filter') or ('today' if mode == 'single' else 'fiscalyear')
    #     date_from = self.filter_pl_vat_date.get('date_from') and fields.Date.from_string(self.filter_pl_vat_date['date_from'])
    #     date_to = self.filter_pl_vat_date.get('date_to') and fields.Date.from_string(self.filter_pl_vat_date['date_to'])
    #     # Handle previous_options.
    #     if previous_options and previous_options.get('pl_vat_date') and previous_options['pl_vat_date'].get('filter') \
    #             and not (previous_options['pl_vat_date']['filter'] == 'today' and mode == 'range'):
    #
    #         options_filter = previous_options['pl_vat_date']['filter']
    #         if options_filter == 'custom':
    #             if previous_options['pl_vat_date']['date_from'] and mode == 'range':
    #                 date_from = fields.Date.from_string(previous_options['pl_vat_date']['date_from'])
    #             if previous_options['pl_vat_date']['date_to']:
    #                 date_to = fields.Date.from_string(previous_options['pl_vat_date']['date_to'])
    #
    #     # Create date option for each company.
    #     period_type = False
    #     if 'today' in options_filter:
    #         date_to = fields.Date.context_today(self)
    #         date_from = date_utils.get_month(date_to)[0]
    #     elif 'month' in options_filter:
    #         date_from, date_to = date_utils.get_month(fields.Date.context_today(self))
    #         period_type = 'month'
    #     elif 'quarter' in options_filter:
    #         date_from, date_to = date_utils.get_quarter(fields.Date.context_today(self))
    #         period_type = 'quarter'
    #     elif 'year' in options_filter:
    #         company_fiscalyear_dates = self.env.company.compute_fiscalyear_dates(fields.Date.context_today(self))
    #         date_from = company_fiscalyear_dates['date_from']
    #         date_to = company_fiscalyear_dates['date_to']
    #     elif not date_from:
    #         # options_filter == 'custom' && mode == 'single'
    #         date_from = date_utils.get_month(date_to)[0]
    #
    #     options['pl_vat_date'] = self._get_dates_period(options, date_from, date_to, mode, period_type=period_type)
    #     if 'last' in options_filter:
    #         options['pl_vat_date'] = self._get_dates_previous_period(options, options['pl_vat_date'])
    #     options['pl_vat_date']['filter'] = options_filter
    #
    # @api.model
    # def _get_options(self, previous_options=None):
    #     options = super(JpkReport, self)._get_options(previous_options)
    #
    #     if self.filter_pl_vat_date:
    #         self._init_filter_pl_vat_date(options, previous_options=previous_options)
    #
    #     return options

    # @api.model
    # def _build_options(self, previous_options=None):
    #     if not previous_options:
    #         previous_options = {}
    #     # noinspection PyProtectedMember
    #     options = super(JpkReport, self)._build_options(previous_options)
    #
    #     # for key, value in options.items():
    #     #     if key in previous_options and value is not None and previous_options[key] is not None \
    #     #             and key == 'pl_vat_date':
    #     #         options[key]['filter'] = 'custom'
    #     #         if previous_options[key].get('filter', 'custom') != 'custom':
    #     #             # just copy filter and let the system compute the correct date from it
    #     #             options[key]['filter'] = previous_options[key]['filter']
    #     #         elif value.get('pl_vat_date_from') is not None and not previous_options[key].get('pl_vat_date_from'):
    #     #             date = fields.Date.from_string(previous_options[key]['pl_vat_date_from'])
    #     #             company_fiscalyear_dates = self.env.user.company_id.compute_fiscalyear_dates(date)
    #     #             options[key]['pl_vat_date_from'] = company_fiscalyear_dates['pl_vat_date_from']\
    #     #                 .strftime(DEFAULT_SERVER_DATE_FORMAT)
    #     #             options[key]['pl_vat_date_to'] = previous_options[key]['pl_vat_date']
    #     #         elif value.get('pl_vat_date') is not None and not previous_options[key].get('pl_vat_date'):
    #     #             options[key]['pl_vat_date'] = previous_options[key]['pl_vat_date_to']
    #     #         else:
    #     #             options[key] = previous_options[key]
    #     return options

    # def _set_context(self, options):
    #     # noinspection PyProtectedMember
    #     ctx = super(JpkReport, self)._set_context(options)
    #     if options.get('pl_vat_date') and options['pl_vat_date'].get('pl_vat_date_from'):
    #         ctx['pl_vat_date_from'] = options['pl_vat_date']['pl_vat_date_from']
    #     if options.get('pl_vat_date'):
    #         ctx['pl_vat_date_to'] = options['pl_vat_date'].get('pl_vat_date_to') or options['pl_vat_date'].get('pl_vat_date')
    #     return ctx

    def _get_reports_buttons(self):
        buttons = [{'name': _('Export (XLSX)'), 'action': 'print_xlsx'},
                   {'name': _('Export XML'), 'action': 'print_xml'}]

        module = self.env['ir.module.module'].search([['name', '=', 'trilab_jpk_transfer']])

        if module and module.state == 'installed':
            buttons.append({'name': _('Export XML and send'), 'action': 'transfer_xml'})

        return buttons

    # def _apply_date_filter(self, options):
    #     # noinspection PyProtectedMember
    #     super(JpkReport, self)._apply_date_filter(options)
    #
    #     def create_vals(_period_vals):
    #         vals = {'string': period_vals['string']}
    #         if options['pl_vat_date'].get('pl_vat_date_from') is None:
    #             vals['pl_vat_date'] = (_period_vals['date_to'] or _period_vals['date_from'])\
    #                 .strftime(DEFAULT_SERVER_DATE_FORMAT)
    #         else:
    #             vals['pl_vat_date_from'] = _period_vals['date_from'].strftime(DEFAULT_SERVER_DATE_FORMAT)
    #             vals['pl_vat_date_to'] = _period_vals['date_to'].strftime(DEFAULT_SERVER_DATE_FORMAT)
    #         vals['filter'] = _period_vals['period_type']
    #         return vals
    #
    #     # ===== Date Filter =====
    #     if not options.get('pl_vat_date') or not options['pl_vat_date'].get('filter'):
    #         return
    #     options_filter = options['pl_vat_date']['filter']
    #
    #     date_from = None
    #     date_to = fields.Date.context_today(self)
    #     period_type = None
    #     if options_filter == 'custom':
    #         if self.has_single_date_filter(options):
    #             date_from = None
    #             date_to = fields.Date.from_string(options['pl_vat_date']['pl_vat_date'])
    #         else:
    #             date_from = fields.Date.from_string(options['pl_vat_date']['pl_vat_date_from'])
    #             date_to = fields.Date.from_string(options['pl_vat_date']['pl_vat_date_to'])
    #     elif 'today' in options_filter:
    #         if not self.has_single_date_filter(options):
    #             date_from = self.env.user.company_id.compute_fiscalyear_dates(date_to)['date_from']
    #     elif 'month' in options_filter:
    #         period_type = 'month'
    #         date_from, date_to = date_utils.get_month(date_to)
    #     elif 'quarter' in options_filter:
    #         period_type = 'quarter'
    #         date_from, date_to = date_utils.get_quarter(date_to)
    #     elif 'year' in options_filter:
    #         company_fiscalyear_dates = self.env.user.company_id.compute_fiscalyear_dates(date_to)
    #         date_from = company_fiscalyear_dates['date_from']
    #         date_to = company_fiscalyear_dates['date_to']
    #     else:
    #         raise UserError('Programmation Error: Unrecognized parameter %s in date filter!' % str(options_filter))
    #
    #     period_vals = self._get_dates_period(options, date_from, date_to, period_type)
    #     if 'last' in options_filter:
    #         period_vals = self._get_dates_previous_period(options, period_vals)
    #
    #     options['pl_vat_date'].update(create_vals(period_vals))

    def get_html(self, options, line_id=None, additional_context=None):
        return super(JpkReport, self).get_html(options, line_id, additional_context)

    def get_xml(self, options):
        tns = 'http://jpk.mf.gov.pl/wzor/2017/11/13/1113/'
        jpk = etree.Element(etree.QName(tns, 'JPK'), nsmap={'tns': tns})
        header = etree.SubElement(jpk, etree.QName(tns, 'Naglowek'))

        etree.SubElement(header, etree.QName(tns, 'KodFormularza'),
                         attrib={'kodSystemowy': 'JPK_VAT (3)', 'wersjaSchemy': '1-1'}).text = 'JPK_VAT'
        etree.SubElement(header, etree.QName(tns, 'WariantFormularza')).text = '3'
        etree.SubElement(header, etree.QName(tns, 'CelZlozenia')).text = '{}'.format(
            options.get('correction_number', 0))
        etree.SubElement(header, etree.QName(tns, 'DataWytworzeniaJPK')).text = datetime.datetime.now().isoformat()
        etree.SubElement(header, etree.QName(tns, 'DataOd')).text = options['date']['date_from']
        etree.SubElement(header, etree.QName(tns, 'DataDo')).text = options['date']['date_to']
        etree.SubElement(header, etree.QName(tns, 'NazwaSystemu')).text = \
            "%s %s" % (release.description, release.version)

        company = self.env.user.company_id
        podmiot = etree.SubElement(jpk, etree.QName(tns, 'Podmiot1'))
        try:
            etree.SubElement(podmiot, etree.QName(tns, 'NIP')).text = re.sub(r'\D', '', company.vat)
        except TypeError:
            raise UserError(_("Make sure that Company's VAT number is correct"))

        etree.SubElement(podmiot, etree.QName(tns, 'PelnaNazwa')).text = company.name
        etree.SubElement(podmiot, etree.QName(tns, 'Email')).text = self.env.user.email

        ctx = self._set_context(options)

        # deactivating the prefetching saves ~35% on get_lines running time
        ctx.update({'no_format': True, 'print_mode': False, 'prefetch_fields': False, 'dict_output': True})
        # noinspection PyProtectedMember
        sections = self.with_context(ctx)._get_lines(options)

        # SprzedazWiersz
        section_count = 0
        section_sum = 0.0

        for line in sections.get('SprzedazWiersz', []):
            section_count += 1
            sale_row = etree.SubElement(jpk, etree.QName(tns, 'SprzedazWiersz'))
            etree.SubElement(sale_row, etree.QName(tns, 'LpSprzedazy')).text = str(line['counter'])
            etree.SubElement(sale_row, etree.QName(tns, 'NrKontrahenta')).text = line['data']['nrkontrahenta']
            etree.SubElement(sale_row, etree.QName(tns, 'NazwaKontrahenta')).text = line['data']['nazwakontrahenta']
            etree.SubElement(sale_row, etree.QName(tns, 'AdresKontrahenta')).text = line['data']['adreskontrahenta']
            etree.SubElement(sale_row, etree.QName(tns, 'DowodSprzedazy')).text = line['data']['dowodsprzedazyzakupu']
            etree.SubElement(sale_row, etree.QName(tns, 'DataWystawienia')).text = \
                line['data']['datawystawienia'].isoformat()

            if line['data']['datasprzedazy'] and line['data']['datawystawienia'] \
                    and line['data']['datasprzedazy'] != line['data']['datawystawienia']:
                etree.SubElement(sale_row, etree.QName(tns, 'DataSprzedazy')).text = \
                    line['data']['datasprzedazy'].isoformat()

            for child in line['children']:
                if child['istax']:
                    section_sum += child['kwota']
                etree.SubElement(sale_row, etree.QName(tns, child['jpkmarkup'])).text = '{:.2f}'.format(child['kwota'])

        section = etree.SubElement(jpk, etree.QName(tns, 'SprzedazCtrl'))
        etree.SubElement(section, etree.QName(tns, 'LiczbaWierszySprzedazy')).text = '{:d}'.format(section_count)
        etree.SubElement(section, etree.QName(tns, 'PodatekNalezny')).text = '{:.2f}'.format(section_sum)

        # ZakupWiersz
        section_count = 0
        section_sum = 0.0

        for line in sections.get('ZakupWiersz', []):
            section_count += 1
            purchase_row = etree.SubElement(jpk, etree.QName(tns, 'ZakupWiersz'))
            etree.SubElement(purchase_row, etree.QName(tns, 'LpZakupu')).text = str(line['counter'])
            etree.SubElement(purchase_row, etree.QName(tns, 'NrDostawcy')).text = line['data']['nrkontrahenta']
            etree.SubElement(purchase_row, etree.QName(tns, 'NazwaDostawcy')).text = line['data']['nazwakontrahenta']
            etree.SubElement(purchase_row, etree.QName(tns, 'AdresDostawcy')).text = line['data']['adreskontrahenta']
            etree.SubElement(purchase_row, etree.QName(tns, 'DowodZakupu')).text = line['data']['dowodsprzedazyzakupu']
            etree.SubElement(purchase_row, etree.QName(tns, 'DataZakupu')).text = line['data']['datazakupu'].isoformat()

            if line['data']['datawplywu'] and line['data']['datazakupu'] \
                    and line['data']['datawplywu'] != line['data']['datazakupu']:
                etree.SubElement(purchase_row, etree.QName(tns, 'DataWplywu')).text = \
                    line['data']['datawplywu'].isoformat()

            for child in line['children']:
                if child['istax']:
                    section_sum += child['kwota']
                etree.SubElement(purchase_row, etree.QName(tns, child['jpkmarkup'])).text = \
                    '{:.2f}'.format(child['kwota'])

        section = etree.SubElement(jpk, etree.QName(tns, 'ZakupCtrl'))
        etree.SubElement(section, etree.QName(tns, 'LiczbaWierszyZakupow')).text = '{:d}'.format(section_count)
        etree.SubElement(section, etree.QName(tns, 'PodatekNaliczony')).text = '{:.2f}'.format(section_sum)

        return etree.tostring(jpk, encoding='UTF8', pretty_print=True)

    def transfer_xml(self, options):
        date = options.get('date', {}).get('string', '')

        transfer_id = self.env['jpk.transfer'].create_with_document({
            'name': f'JPK VAT {date}',
            'jpk_type': 'JPK',
            'file_name': 'jpk_vat_{}.xml'.format(date),
            'data': self.get_xml(options),
            'document_type': 'trilab_jpk_base.jpk_vat_doc_type',
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'jpk.transfer',
            'views': [[False, 'form']],
            'res_id': transfer_id.id,
            # 'target': 'new'
        }
