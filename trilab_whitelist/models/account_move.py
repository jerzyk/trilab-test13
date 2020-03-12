import datetime
import re

import requests

# noinspection PyProtectedMember
from odoo import release, models, _
from odoo.exceptions import UserError


class AccountMove(models.Model):

    _inherit = 'account.move'

    def action_validate_bank_account(self):
        for invoice in self:
            if not invoice.commercial_partner_id:
                raise UserError(_('Select Partner first!'))

            if not invoice.commercial_partner_id.vat:
                raise UserError(_('Partner is missing VAT number!'))

            vat = re.sub(r'[^0-9]', '', invoice.commercial_partner_id.vat)

            if not vat:
                raise UserError(_('Partner VAT number is missing or is incorrect!'))

            acc_number = re.sub(r'[^0-9]', '', invoice.invoice_partner_bank_id.sanitized_acc_number)

            if not acc_number:
                raise UserError(_('Partner account number is missing'))

            url = f'https://wl-api.mf.gov.pl/api/check/nip/{vat}/bank-account/{acc_number}'

            response = requests.get(url, params={'date': datetime.date.today().isoformat()},
                                    headers={'user-agent': '{} {}'.format(release.description, release.version)})

            if response.ok:
                result = response.json()
                if 'result' in result:
                    message = _('Whitelist validation status {}, confirmation id: {}')
                    if result['result']['accountAssigned'].upper() == 'TAK':
                        self.message_post(body=message.format(_('POSITIVE'), result['result']['requestId']))
                    else:
                        self.message_post(body=message.format(_('NEGATIVE'), result['result']['requestId']))
                else:
                    raise UserError(_('Error from MF API: {}').format(result.get('exception')))
            else:
                raise UserError(_('Error accessing MF API: [{}]{}').format(response.status_code, response.reason))

        return None
