# -*- coding: utf-8 -*-
import json
import time
import threading
import re
import logging
from unidecode import unidecode

from odoo import api, fields, models
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import UserError

DEFAULT_RANKING_SORTING = ['typo', 'geo', 'words', 'filters', 'proximity', 'attribute', 'exact', 'custom']
_logger = logging.getLogger(__name__)


class AlgoliaIndex(models.Model):
    _name = 'algolia.index'
    _description = 'Algolia Index'

    name = fields.Char(required=True)
    batch = fields.Integer('Batch', default=5000)
    online = fields.Boolean()
    from_algolia = fields.Boolean()
    auto_indexation = fields.Boolean()
    algolia_app_id = fields.Many2one('algolia.application')
    product_domain = fields.Char(string='Domain', default=["&", ["is_published", "=", True], ["active", "=", True]])
    product_template_ids = fields.Many2many('product.template', string='Product',
                                            relation='product_template_algolia_index')
    product_count = fields.Integer(string='Product Count', compute='_compute_product_count')
    delete_product_template_ids = fields.Many2many('product.template', string='Product',
                                                   relation='product_template_algolia_index_to_delete')
    entries = fields.Integer()
    data_size = fields.Integer()
    file_size = fields.Integer()
    use_virtual_replicas = fields.Boolean()

    @api.depends('product_template_ids')
    def _compute_product_count(self):
        for rec in self:
            rec.product_count = len(rec.product_template_ids)

    @api.model
    def create(self, values):
        active_id = self.env.context.get('active_id', False)
        values['name'] = unidecode(values['name']).replace(' ', '_')
        if not values.get('algolia_app_id', False) and active_id:
            values['algolia_app_id'] = active_id
        if values.get('product_domain', False):
            domain = safe_eval(values['product_domain'])
            product_ids = self.env['product.template'].search(domain).ids
            values['product_template_ids'] = [(6, 0, product_ids)]
        return super(AlgoliaIndex, self).create(values)

    def unlink(self):
        for rec in self:
            if rec.online:
                client = rec.algolia_app_id.get_client()
                index_algolia = client.init_index(rec.name)
                if index_algolia:
                    index_algolia.delete()
            history_ids = self.env['index.history'].search([('index_id', '=', rec.id)])
            if history_ids:
                history_ids.unlink()
        return super(AlgoliaIndex, self).unlink()

    def write(self, values):
        if values.get('domain', False):
            domain = safe_eval(values['domain'])
            product_ids = self.env['product.template'].search(domain).ids
            values['product_template_ids'] = [(6, 0, product_ids)]
        product_template_ids = values.get('product_template_ids', False)
        if product_template_ids and product_template_ids[0][0] == 6:
            added = list(set(values['product_template_ids'][0][2]) - set(self.product_template_ids.ids))
            self._disable_indexation(added)
            deleted = list(set(self.product_template_ids.filtered(lambda p: p.is_indexed(self.name)).ids) - set(
                values['product_template_ids'][0][2]))
            if deleted:
                delete_list = self.delete_product_template_ids.ids + deleted
                values['delete_product_template_ids'] = [(6, 0, delete_list)]
                self._disable_indexation(delete_list)
        return super(AlgoliaIndex, self).write(values)

    @api.model
    def _disable_indexation(self, product_list):
        for p in self.env['product.template'].search([('id', 'in', product_list)]):
            index_history = p.index_history_ids.filtered(lambda i: i.id == self.id)
            if index_history:
                index_history.write({'is_indexed': False})

    def update_index(self):
        self._init_index(update=True)
        if self.delete_product_template_ids:
            self.delete_index_object()

    def delete_index_object(self):
        try:
            client = self.algolia_app_id.get_client()
            index = client.init_index(self.name)
            object_ids = self.delete_product_template_ids.mapped('algolia_objectId')
            index.delete_objects(object_ids)
            for product in self.delete_product_template_ids:
                history_line_id = product.index_history_ids.filtered(lambda l: l.index_id.id == self.id)
                product.write({'index_history_ids': [(3, history_line_id.id)]})
            self.write({'delete_product_template_ids': [(5,)]})
        except Exception as e:
            _logger.error(msg=f'Exception delete object : {e}')

    def delete_one_object(self, object_id):
        try:
            client = self.algolia_app_id.get_client()
            index = client.init_index(self.name)
            index.delete_object(object_id)
        except Exception as e:
            _logger.error(msg=f'Exception delete object : {e}')

    def _init_index(self, update, manual=False):
        if update:
            product_can_indexed = self.product_template_ids.filtered(
                lambda p: p.active and p.is_published and not p.is_indexed(self.name))
        else:
            product_can_indexed = self.product_template_ids.filtered(
                lambda p: p.active and p.is_published)
        if manual:
            self.write({'online': True})
            for product in product_can_indexed:
                product.create_index_history(index_id=self)
        else:
            data = self.env['product.template'].get_product_payloads(product_can_indexed)
            try:
                if data:
                    client = self.algolia_app_id.get_client()
                    index_algolia = client.init_index(self.name)
                    index_algolia.save_objects(data, {'autoGenerateObjectIDIfNotExist': True})
                    self.write({'online': True})
                    for product in product_can_indexed:
                        product.create_index_history(index_id=self)
            except Exception as e:
                _logger.error(msg=f'Exception Initialization index : {e}')

    def init_indexation_manually(self):
        t = threading.Thread(self._init_index(False, True))
        t.daemon = True
        t.start()
        return True

    def init_indexation(self, update=False):
        t = threading.Thread(self._init_index(update))
        t.daemon = True
        t.start()
        return True

    def _get_faceting(self):
        attribute_list = []
        category_list = []
        if self.product_template_ids:
            category_depth = max([p.depth_category for p in self.product_template_ids])
            category_list = [f"category_lvl{category_level}" for category_level in range(category_depth)]
        if self.product_template_ids.attribute_line_ids:
            attribute_list = self.product_template_ids.attribute_line_ids.mapped('attribute_id.name')
        res = category_list + attribute_list
        return res

    def _get_index_setting(self):
        attributes_for_faceting = self._get_faceting()
        values = {
            'attributesForFaceting': attributes_for_faceting,
            'searchableAttributes': [
                'name',
                'price'
            ],
        }
        # ADD Replicas
        replicas = [f'{self.name}_price_asc', f'{self.name}_price_desc']
        if self.use_virtual_replicas:
            replicas = [f'virtual({item})' for item in replicas]
        values['replicas'] = replicas
        return values

    def _set_settings(self, index, result=False):
        wait = result.raw_responses[0] if result and result.raw_responses else False
        settings = self._get_index_setting()
        if wait:
            task_index = index.set_settings(settings).wait(wait['taskID'])
        else:
            task_index = index.set_settings(settings)
        return task_index, settings['replicas']

    def configure_index(self):
        client = self.algolia_app_id.get_client()
        index = client.init_index(self.name)
        task_index, replicas = self._set_settings(index)
        attributes_for_faceting = self._get_faceting()
        values = {
            'attributesForFaceting': attributes_for_faceting,
            'searchableAttributes': [
                'name',
                'price'
            ],
        }
        for replica in replicas:
            ranking = [
                'typo',
                'geo',
                'words',
                'filters',
                'proximity',
                'attribute',
                'exact',
                'custom'
            ]
            if 'asc' in replica:
                search = re.search(f'{self.name}_(.*)_asc', replica)
                price = f'asc({search.group(1)})'
            else:
                search = re.search(f'{self.name}_(.*)_desc', replica)
                price = f'desc({search.group(1)})'
            ranking.append(price)
            values['ranking'] = ranking
            index_replicas = client.init_index(replica)
            index_replicas.set_settings(values)
            time.sleep(2)

    @api.model
    def run_auto_indexation(self):
        for index in self.search([('auto_indexation', '=', True)]):
            index.update_index()

    def action_export_data(self):
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/index/download?obj_id={self.id}',
            'target': 'new',
        }


class IndexHistory(models.Model):
    _name = 'index.history'

    index_id = fields.Many2one('algolia.index', 'Index', ondelete='cascade')
    product_id = fields.Many2one('product.template', 'Product', ondelete='cascade')
    is_indexed = fields.Boolean('Is indexed')
    name = fields.Char(string='Index', compute='_compute_name')

    @api.depends('index_id', 'is_indexed')
    def _compute_name(self):
        for rec in self:
            rec.name = f'Index : {rec.index_id.name} | {"OK" if rec.is_indexed else "NOK"}'

    @api.model
    def create(self, values):
        res = super(IndexHistory, self).create(values)
        object_id = "_".join([
            self._cr.dbname[:5].upper(),
            'PRODUCT_TEMPLATE',
            str(res.product_id.id)
        ])
        res.product_id.with_context(update_algolia=True).write({'algolia_objectId': object_id})
        return res
