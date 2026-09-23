from odoo import models


class Attachment(models.Model):
    _inherit = 'ir.attachment'

    def read(self, fields=None, load='_classic_read'):
        # HTTP downloads call attachment.check(); enforce the same parent boundary
        # for direct ORM/RPC reads, including values already in the ORM cache.
        if not self.env.su:
            for attachment in self.sudo():
                if attachment.res_model in ('xyz.acceptance', 'project.task') and attachment.res_id:
                    self.env[attachment.res_model].browse(attachment.res_id).check_access('read')
        return super().read(fields=fields, load=load)
