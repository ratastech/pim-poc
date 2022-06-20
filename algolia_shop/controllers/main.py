# -*- coding: utf-8 -*-


import json
import logging

from unidecode import unidecode

from odoo import http
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.http_routing.models.ir_http import slug
import odoo.tools.safe_eval

_logger = logging.getLogger(__name__)


class AlgoliaWebsiteSale(WebsiteSale):

    @http.route([
        '''/shop''',
        '''/shop/page/<int:page>''',
        '''/shop/category/<model("product.public.category"):category>''',
        '''/shop/category/<model("product.public.category"):category>/page/<int:page>'''
    ], type='http', auth="public", website=True, sitemap=WebsiteSale.sitemap_shop)
    def shop(self, page=0, category=None, search='', ppg=False, **post):
        result = super(AlgoliaWebsiteSale, self).shop(page, category, search, ppg, **post)
        # INITIALIZATION
        website_id = request.website
        if not website_id.algolia_index_id:
            return result
        index_id = website_id.algolia_index_id
        index_product_ids = index_id.product_template_ids

        def get_att(type_att):
            return index_product_ids.attribute_line_ids.filtered(
                lambda a: a.attribute_id.display_type == type_att).mapped('attribute_id.name')

        type_attribute = {i: get_att(i) for i in ['color', 'select', 'radio']}
        try:
            client = website_id.algolia_app_id.get_client()
            index_list = client.list_indices()
            if website_id.algolia_index_id.name not in [item['name'] for item in index_list['items']]:
                return result
            # Attribute
            attrib_values_name = []
            attribute_line_name = index_product_ids.attribute_line_ids.mapped('attribute_id.name')
            attribute_line_name = [
                [item, unidecode(item).lower().replace(' ', '_').replace('+', '_').replace('(', '_').replace(')', '_')]
                for item in attribute_line_name]
            max_depth_category = max([p.depth_category for p in index_product_ids])
            # FROM FILTER
            for attrib in result.qcontext.get('attrib_values', []):
                attribut_id = request.env['product.attribute'].sudo().browse(attrib[0]).exists()
                value_id = request.env['product.attribute.value'].sudo().browse(attrib[1]).exists()
                attrib_values_name.append([attribut_id.name, value_id.name])
            # VALUES
            values = {

                'category': category.display_name.replace(' / ', ' > ') if category else False,
                'search': search,
                'page': page,
                'attribute_name': json.dumps(dict()),
                'max_depth_category': max_depth_category,
                'attribute_line_name_data': json.dumps(dict()),
                # 'json': json,
                'type_attribute': json.dumps(dict())
            }

            return request.render("algolia_shop.algo_shop", values)
        except Exception as e:
            _logger.error(msg=f'Exception, redirect to native shop : {e}')
            return result

    @http.route(['/website/index'], type='json', auth='none', website=True)
    def get_website_index_information(self):
        website_id = request.website
        if website_id and website_id.algolia_app_id and website_id.algolia_index_id:
            app_id = website_id.algolia_app_id
            return {
                'app_id': app_id.application_id,
                'search_key': app_id.search_api_key,
                'index': website_id.algolia_index_id.name
            }
        return False

    @http.route(['/shop/engine/product/<string:default_code>'], type='http', auth="public", website=True)
    def engine_product(self, default_code):
        product_id = request.env['product.template'].search([('default_code', '=', default_code)])
        return request.redirect("/shop/product/%s" % slug(product_id))

    @http.route(['/shop/engine/cart/update'], type='http', auth="public", methods=['GET', 'POST'], website=True,
                csrf=False)
    def engine_cart_update(self, **kw):
        default_code = kw.get('object_id')
        product_id = request.env['product.template'].search([('default_code', '=', default_code)])
        return self.cart_update(product_id=product_id.product_variant_id.id)

