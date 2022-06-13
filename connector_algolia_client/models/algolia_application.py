import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import ustr

from algoliasearch.search_client import SearchClient

ALGOLIA_INDEX = 'algolia.index'
_logger = logging.getLogger(__name__)


class AlgoliaApplication(models.Model):
    _name = 'algolia.application'
    _description = 'Algolia Application'

    name = fields.Char(required=True)
    application_id = fields.Char(required=True)
    admin_api_key = fields.Char(required=True)
    index_ids = fields.One2many(ALGOLIA_INDEX, inverse_name='algolia_app_id', string='Index')
    index_count = fields.Integer(compute='_compute_index_count')

    def test_client_admin_connection(self):
        for rec in self:
            try:
                client = rec.get_client()
                client.list_indices()
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

    def get_client(self):
        client = SearchClient.create(self.application_id, self.admin_api_key)
        return client

    def action_get_existing_index(self):
        client = self.get_client()
        if client:
            try:
                index_list = client.list_indices()
                self.index_ids.unlink()
                if index_list.get('nbPages', 0) > 0:
                    for items in index_list['items']:
                        values = {
                            'name': items['name'],
                            'entries': items['entries'],
                            'data_size': items['dataSize'],
                            'file_size': items['fileSize'],
                            'algolia_app_id': self.id,
                            'online': True,
                            'from_algolia': True
                        }
                        self.env[ALGOLIA_INDEX].sudo().with_context(from_application=True).create(values)
                return True
            except Exception as e:
                _logger.error(msg=f'Get existing index : {e}')
                return False

    @api.depends('index_ids')
    def _compute_index_count(self):
        """
        Compute index count
        :return: number of index
        """
        for rec in self:
            rec.index_count = len(rec.index_ids)

    def action_view_index(self):
        action = {
            'name': 'Index',
            'type': 'ir.actions.act_window',
            'res_model': ALGOLIA_INDEX,
            'target': 'current',
        }
        index_ids = self.index_ids.ids
        if len(index_ids) == 1:
            index = index_ids[0]
            action['res_id'] = index
            action['view_mode'] = 'form'
            form_view = [(self.env.ref('connector_algolia_client.algolia_index_view_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
        else:
            action['view_mode'] = 'tree,form'
            action['domain'] = [('id', 'in', index_ids)]
        return action
