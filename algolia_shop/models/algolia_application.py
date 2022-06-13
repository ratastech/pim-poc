# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import ustr

from algoliasearch.search_client import SearchClient


class AlgoliaApplication(models.Model):
    _inherit = 'algolia.application'

    search_api_key = fields.Char(required=True)

    def test_client_search_connection(self):
        for rec in self:
            try:
                if not rec.index_ids:
                    UserError(_("Please initialize the application and create at least one index"))
                client = SearchClient.create(rec.application_id, rec.search_api_key)
                index = client.init_index(rec.index_ids[0].name)
                index.search('test_client_search_connection')
            except UserError as e:
                # let UserErrors (messages) bubble up
                raise e
            except Exception as e:
                raise UserError(_("Connection Test Failed! Here is what we got instead:\n %s") % ustr(e))

            title = _("Connection Test Succeeded!")
            message = _("Everything seems properly set up!")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': title,
                    'message': message,
                    'sticky': False,
                }
            }
