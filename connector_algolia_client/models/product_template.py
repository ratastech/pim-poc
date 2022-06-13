# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models

FIELD_INDEX = [
    'name',
    'image',
    'description_sale',
    'list_price',
    'attribute_line_ids'
]

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    algolia_objectId = fields.Char('Object ID Algolia', copy=False)
    payload_index = fields.Char()
    depth_category = fields.Integer(compute="_compute_depth_category")
    index_history_ids = fields.One2many('index.history', 'product_id', string='Index history')

    def write(self, values):
        """
        set is_indexed False if any FIELD_INDEX change
        :param values: values changed
        :return: native write
        """
        if any([item in list(values.keys()) for item in FIELD_INDEX]) and self.index_history_ids:
            for index_history in self.index_history_ids:
                index_history.write({'is_indexed': False})
        if values.get('is_published') is False and self.index_history_ids:
            self._delete_in_odoo_index()
            self.index_history_ids.unlink()
        if values.get('active') is False:
            self.direct_delete_in_index()
            self.index_history_ids.unlink()
            for index_history in self.index_history_ids:
                index = index_history.index_id
                index.write({'product_template_ids': [(3, self.id)]})
        return super(ProductTemplate, self).write(values)

    @api.model
    def direct_delete_in_index(self, index_ids, algolia_object):
        try:
            for index_id in index_ids:
                index_id.delete_one_object(algolia_object)
        except Exception as e:
            _logger.error(msg=f'Exception delete object index : {e}')

    def unlink(self):
        index_ids = self.index_history_ids.mapped('index_id')
        algolia_object = self.algolia_objectId
        res = super(ProductTemplate, self).unlink()
        self.direct_delete_in_index(index_ids, algolia_object)
        return res

    def _delete_in_odoo_index(self):
        for rec in self:
            for index_history in rec.index_history_ids:
                index = index_history.index_id
                index.write({
                    'product_template_ids': [(3, rec.id)],
                    'delete_product_template_ids': [(4, rec.id)]
                })

    def _get_attribute_line(self, values):
        """
        Return key and values (as list) of attribute_line_ids
        :param values: dictionary
        :return: values
        """
        for attribute in self.attribute_line_ids:
            values[attribute.attribute_id.name] = attribute.value_ids.mapped('name')
        return values

    def _payload_attribute_line(self):
        result = {}
        for attribute in self.attribute_line_ids:
            att_get = 'html_color' if attribute.attribute_id.display_type == 'color' else 'name'
            result[attribute.attribute_id.name] = attribute.value_ids.mapped(att_get)
        return result

    def _payload_categories(self):
        result = {}
        for category in self.public_categ_ids:
            parents_and_self = category.parents_and_self.mapped('display_name')
            category_depth = 0
            result[f'category_lvl{category_depth}'] = result.get(f'category_lvl{category_depth}', [])
            for node in parents_and_self:
                result[f'category_lvl{category_depth}'].append(node.replace(' / ', ' > '))
                result[f'category_lvl{category_depth}'] = list(set(result[f'category_lvl{category_depth}']))
                if node != parents_and_self[-1]:
                    result[f'category_lvl{category_depth + 1}'] = result.get(f'category_lvl{category_depth + 1}', [])
                category_depth += 1
        return result

    def is_indexed(self, index_name):
        history = self.index_history_ids.filtered(lambda i: i.index_id.name == index_name)
        return history.is_indexed if history else False

    @api.model
    def get_product_payloads(self, product_ids):
        rows = []
        for product in product_ids:
            rows.append(product._get_product_payload())
        return rows

    def _get_product_payload(self):
        """
        Create payload use for product indexation
        fields : objectID, name, description, image, price, attribute_line_ids, public_categ_ids
        :return: json payload for index save_object
        """
        limit_length_id = 5
        object_id = "_".join([
            self._cr.dbname[:limit_length_id].upper(),
            'PRODUCT_TEMPLATE',
            str(self.id)
        ])
        # simple value
        if not self.default_code:
            self.default_code = object_id
        rows = {
            "objectID": self.default_code if self.default_code else object_id,
            "name": self.name,
            "image": self.env['website'].image_url(self, 'image', '512'),
            "price": self.list_price
        }
        # Get attribute line
        rows.update(self._payload_attribute_line())
        # Get categories
        rows.update(self._payload_categories())
        return rows

    @api.depends('public_categ_ids')
    def _compute_depth_category(self):
        """
        Compute depth_category for faceting
        :return: depth_category
        """
        for rec in self:
            rec.depth_category = max(
                [len(category.parents_and_self) for category in rec.public_categ_ids]) if rec.public_categ_ids else 0

    def create_index_history(self, index_id):
        history_id = self.env['index.history'].search([('index_id', '=', index_id.id), ('product_id', '=', self.id)])
        if history_id:
            _logger.info(msg=f'{"*" * 25} UPDATE HISTORY INDEX : {history_id.id} {"*" * 25}')
            history_id.write({'is_indexed': True})
        else:
            _logger.info(msg=f'{"*" * 25} CREATE HISTORY INDEX : {index_id.id} | {self.id} {"*" * 25}')
            self.env['index.history'].create({
                'product_id': self.id,
                'index_id': index_id.id,
                'is_indexed': True
            })
        return True
