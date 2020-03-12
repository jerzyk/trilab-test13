# -*- coding: utf-8 -*-

import logging
from datetime import datetime

import requests

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = 'res.company'

    currency_provider = fields.Selection(selection_add=[('nbp', 'NBP (Poland)')])

    @api.model
    def create(self, vals):
        """
            Change the default provider depending on the company data.
        """
        if vals.get('country_id') and 'currency_provider' not in vals:
            cc = self.env['res.country'].browse(vals['country_id']).code.upper()
            if cc == 'PL':
                vals['currency_provider'] = 'nbp'
        return super(ResCompany, self).create(vals)

    @api.model
    def set_special_defaults_on_install(self):
        """
            At module installation, set NBP as default provider for each polish company.
        """

        super(ResCompany, self).set_special_defaults_on_install()

        for company in self.env['res.company'].search([('country_id.code', '=', 'PL')]):
            # if company.country_id.code == 'PL':
            # Sets NBP as the default provider for every polish company that was already installed
            company.currency_provider = 'nbp'

    def _parse_nbp_data(self, available_currencies):
        """
            This method is used to update the currencies by using NBP (Natinal Polish Bank) service API.
            Rates are given against PLN
        """

        # this is url to fetch active (at the moment of fetch) average currency exchange table
        request_url = 'http://api.nbp.pl/api/exchangerates/tables/{}/?format=json'
        available_currency_codes = available_currencies.mapped('name')

        result = {}

        try:
            # there are 3 tables with currencies:
            #   A - most used ones average,
            #   B - exotic currencies average,
            #   C - common bid/sell
            # we will parse first one and if there are unmatched currencies, proceed with second one

            for table_type in ['A', 'B']:

                if not available_currency_codes:
                    break

                response = requests.get(request_url.format(table_type))
                response_data = response.json()

                for exchange_table in response_data:
                    # there *should not be* be a more than one table in response, but let's be on a safe side
                    # and parse this in a loop as response is a list

                    # effective date of this table
                    table_date = datetime.strptime(exchange_table['effectiveDate'], '%Y-%m-%d').date()

                    # add base currency
                    if 'PLN' not in result:
                        result['PLN'] = (1.0, table_date)

                    for rec in exchange_table['rates']:
                        if rec['code'] in available_currency_codes:
                            result[rec['code']] = (1.0/rec['mid'], table_date)
                            available_currency_codes.remove(rec['code'])

        except (requests.RequestException, ValueError):
            # connection error, the request wasn't successful or date was not parsed
            return False

        return result

