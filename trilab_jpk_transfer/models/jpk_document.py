import base64

from odoo import api, fields, models, _
from ..unidecode.unidecode import unidecode


class JPKTDocument(models.Model):
    _name = 'jpk.document'
    _description = _('JPK Document')

    transfer_id = fields.Many2one('jpk.transfer', required=1, ondelete='cascade')
    transfer_state = fields.Selection(related='transfer_id.state', string='Transfer State')
    document_type_id = fields.Many2one('jpk.document.type', required=1)

    name = fields.Char(related='original_file_id.name', readonly=1)
    active = fields.Boolean(related='transfer_id.active', store=True)
    original_file_id = fields.Many2one('ir.attachment', required=1, string='Original File')
    original_file_id_datas = fields.Binary(related='original_file_id.datas', readonly=0, string='Original File Data')
    original_file_id_name = fields.Char(related='original_file_id.name', readonly=0, string='Original File Filename')
    iv = fields.Char('Initialization Vector - IV', size=50)
    zip_file_id = fields.Many2one('ir.attachment')
    zip_file_id_datas = fields.Binary(related='zip_file_id.datas')
    zip_file_id_name = fields.Char(related='zip_file_id.name', string='ZIP File Name')

    file_part_ids = fields.One2many('jpk.file.part', 'transfer_document_id')

    @api.onchange('original_file_id_datas')
    def create_attachment(self):
        if not self.original_file_id and self.original_file_id_datas:
            self.original_file_id = self.env['ir.attachment'].create(dict(
                name=self.original_file_id_name,
                datas=self.original_file_id_datas
            )).id

    def create_with_attachment(self, data):

        file_name = data.get('file_name')

        file_name = unidecode(file_name).replace(' ', '_')

        attachment_id = self.env['ir.attachment'].create([{
            'name': file_name,
            'datas': base64.encodebytes(data.get('data')),
            'res_model': 'jpk.transfer',
            'res_id': data.get('transfer_id'),
            'type': 'binary',
        }])

        return self.env['jpk.document'].create([{
            'transfer_id': data.get('transfer_id'),
            'document_type_id': self.env.ref(data.get('document_type')).id,
            'name': file_name,
            'original_file_id': attachment_id.id
        }])
