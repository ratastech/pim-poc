# -*- coding: utf-8 -*-


import json
import logging

from unidecode import unidecode

from odoo import http
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.http_routing.models.ir_http import slug

_logger = logging.getLogger(__name__)


class PimWebsiteSale(WebsiteSale):

    def _prepare_product_values(self, product, category, search, **kwargs):
        res = super(PimWebsiteSale, self)._prepare_product_values(product, category, search, **kwargs)
        attribute_ids = product.sudo().attribute_set_id.attribute_ids
        custom_values = {}
        for attribute in attribute_ids:
            field = attribute.name
            if attribute.attribute_type in ('multiselect', 'select'):
                custom_values[attribute.display_name] = product[field].sudo().mapped('name')
            else:
                custom_values[field] = product[field]
        return {**res, 'custom_values': custom_values}
