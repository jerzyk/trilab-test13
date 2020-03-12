# -*- coding: utf-8 -*-

# noinspection PyProtectedMember
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

from gusregon import GUS
from zeep import Client, xsd

MF_GOV_PL_WSDL = 'https://sprawdz-status-vat.mf.gov.pl/?wsdl'

KRD_ENV = {
    'prod': 'https://services.krd.pl/Chase/3.1/Search.svc?WSDL',
    'test': 'https://demo.krd.pl/Chase/3.1/Search.svc?WSDL'
}


class ResPartner(models.Model):

    _inherit = 'res.partner'

    nip_state = fields.Char(string='NIP Status', track_visibility='onchange', help="""
    Status odpowiada poniższej liście:
    N - Podmiot o podanym identyfikatorze podatkowym NIP nie jest zarejestrowany jako podatnik VAT
    C - Podmiot o podanym identyfikatorze podatkowym NIP jest zarejestrowany jako podatnik VAT czynny
    Z - Podmiot o podanym identyfikatorze podatkowym NIP jest zarejestrowany jako podatnik VAT zwolniony
    I - Błąd zapytania - Nieprawidłowy Numer Identyfikacji Podatkowej
    D - Błąd zapytania - Data spoza ustalonego zakresu
    X - Usługa nieaktywna""")

    regon = fields.Char(string='REGON')
    krs = fields.Char(string='KRS/NR Ew.')
    nip_check_date = fields.Date(string='NIP Check Date')
    gus_update_date = fields.Date(string='GUS Update Date')

    gus_nip = fields.Char(compute='_gusnip_compute', inverse='_gusnip_compute')

    def _gusnip_compute(self):
        self.gus_nip = '*unknown*'
        # pass

    @api.onchange('gus_nip')
    def gusnip_change(self):
        if self.gus_nip:
            try:
                if len(self.gus_nip) > 1:
                    if not self.gus_nip[0].isdigit():
                        if self.gus_nip.lower().startswith('pl'):
                            self.gus_nip = self.gus_nip[2:]
                        else:
                            raise ValidationError(_('Only polish Tax IDs are supported'))

                    self.gus_nip = self.gus_nip.replace(' ', '').replace('-', '')

                if not self.gus_update_date and self.validate_pl_nip(self.gus_nip):
                    for field, value in self.get_gus_data(nip=self.gus_nip).items():
                        setattr(self, field, value)
                    return {'warning': {'title': 'GUS',
                                        'message': _('Record data found in GUS and updated!')}}
            except ValidationError as e:
                return {'warning': {'title': 'GUS',
                                    'message': _('NIP is incorrect: {}').format(e.name)}}

    @staticmethod
    def validate_pl_nip(value):
        """
        Calculates a checksum with the provided algorithm.
        """
        multiple_table = (6, 5, 7, 2, 3, 4, 5, 6, 7)
        result = 0

        v_len = len(value) - 1
        if v_len != len(multiple_table):
            raise ValidationError(_('Invalid NIP Length'))

        for i in range(v_len):
            try:
                result += int(value[i]) * multiple_table[i]
            except ValueError:
                raise ValidationError(_('Only digits allowed'))

        result %= 11
        if result != int(value[-1]):
            raise ValidationError(_('Invalid NIP'))

        return True

    def get_gus_data(self, nip):
        api_key = self.env['ir.config_parameter'].sudo().get_param('trilab_gusregon.gus_api_key')

        if not api_key:
            raise ValidationError(_('Please set GUS API key in General Settings'))

        gus = GUS(api_key=api_key)

        response = gus.search(nip=nip)

        if not response:
            raise ValidationError(_('NIP is not valid'))

        poland_id = self.env.ref('base.pl')

        phone = response.get('numertelefonu')
        phone_int = response.get('numerwewnetrznytelefonu')

        if phone and phone_int:
            phone = '{} w. {}'.format(phone, phone_int)

        return {
            'name': response.get('nazwa'),
            'street': ' '.join([response.get('adsiedzulica_nazwa', ''),
                                response.get('adsiedznumernieruchomosci', ''),
                                response.get('adsiedznumerlokalu', '')]),
            'street2': response.get('adsiedznietypowemiejscelokalizacji'),
            'city': response.get('adsiedzmiejscowosc_nazwa'),
            'state_id': poland_id.state_ids.search([('name',
                                                     '=ilike',
                                                     response.get('adsiedzwojewodztwo_nazwa'))], limit=1).id,
            'zip': response.get('adsiedzkodpocztowy'),
            'country_id': poland_id.id,
            'phone': phone,
            'email': response.get('adresemail'),
            'website': response.get('adresstronyinternetowej'),
            'vat': nip,
            'regon': response.get('regon9') or response.get('regon14'),
            'krs': response.get('numerwrejestrzeewidencji'),
            'gus_update_date': fields.Date.today()
        }

    def update_gus_data(self):
        poland = self.env.ref('base.pl')

        api_key = self.env['ir.config_parameter'].sudo().get_param('trilab_gusregon.gus_api_key')

        if not api_key:
            raise ValidationError(_('Please set GUS API key in General Settings'))

        for partner in self:
            if partner.country_id.id != poland.id:
                raise ValidationError(_('Customer must be from Poland'))

            if not partner.vat:
                raise ValidationError(_('VAT is required'))

            partner.write(self.get_gus_data(nip=''.join(c for c in partner.vat if c.isdigit())))

    def check_nip(self):
        poland = self.env.ref('base.pl')

        for partner in self:
            if partner.country_id.id != poland.id or not partner.vat:
                partner.nip_state = False
                partner.nip_check_date = False
                return
            client = Client(MF_GOV_PL_WSDL)
            response = client.service.SprawdzNIP(''.join(c for c in partner.vat if c.isdigit()))
            partner.nip_state = response['Kod']
            partner.nip_check_date = fields.Date.today()

    def check_krd(self):
        self.ensure_one()
        company = self.env.user.company_id
        if not company.krd_login or not company.krd_pass:
            raise ValidationError(_('Please set KRD login and password in company settings'))
        if not self.country_id or self.country_id.code != 'PL':
            raise ValidationError(_('The company must be registered in Poland'))
        if not self.vat:
            raise ValidationError(_('VAT is required'))

        client = Client(KRD_ENV[company.krd_env])

        auth_header = xsd.Element('{http://krd.pl/Authorization}Authorization', xsd.ComplexType([
            xsd.Element('{http://krd.pl/Authorization}AuthorizationType', xsd.String()),
            xsd.Element('{http://krd.pl/Authorization}Login', xsd.String()),
            xsd.Element('{http://krd.pl/Authorization}Password', xsd.String()),
        ]))

        auth_value = auth_header(
            AuthorizationType='LoginAndPassword',
            Login=company.krd_login,
            Password=company.krd_pass)

        response = client.service.SearchNonConsumer(
            NumberType='TaxId',
            Number=self.vat,
            _soapheaders=[auth_value],
        )

        response = dict(
            Summary=response['body']['DisclosureReport']['Summary'],
            PositiveInformationSummary=response['body']['DisclosureReport']['PositiveInformationSummary'],
        )

        self.message_post(body=self.env['ir.qweb'].render('trilab_pl_partners_sync.krd_result', response))


class ResPartnercheckNip(models.TransientModel):
    _name = 'res.partner.check.nip'
    _description = 'Check NIP Wizard'

    res_partner_ids = fields.Many2many('res.partner')

    # noinspection PyShadowingNames
    @api.model
    def default_get(self, fields):
        poland = self.env.ref('base.pl')
        mode = self.env.context.get('mode')

        if mode == 'nip':
            partners = self.env['res.partner'].browse(self.env.context.get('active_ids'))
            partners = partners.filtered(lambda partner: partner.country_id.id == poland.id and partner.vat)
            partners.check_nip()
            rec = {'res_partner_ids': partners.ids}

        elif mode == 'gus':
            partners = self.env['res.partner'].browse(self.env.context.get('active_ids'))
            partners = partners.filtered(lambda partner: partner.country_id.id == poland.id and partner.vat)
            partners.update_gus_data()
            rec = {'res_partner_ids': partners.ids}

        else:
            raise UserError(_('Specified invalid check mode (context)'))

        return rec
