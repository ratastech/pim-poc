# -*- coding: utf-8 -*-
import json

from odoo import http, _
from odoo.http import content_disposition, request


class Controllers(http.Controller):

    @http.route('/web/index/download', type="http", auth="user")
    def download_index(self, obj_id):
        index_id = request.env['algolia.index'].browse(int(obj_id))
        product_can_indexed = index_id.product_template_ids.filtered(lambda p: p.active and p.is_published)
        data = request.env['product.template'].get_product_payloads(product_can_indexed)
        name = f'{index_id.name}_{len(product_can_indexed)}_{obj_id}.json'
        response = request.make_response(
            json.dumps(data),
            [
                ('Content-Type', 'application/octet-stream'),
                ('Content-Disposition', content_disposition(name))
            ]
        )
        return response
