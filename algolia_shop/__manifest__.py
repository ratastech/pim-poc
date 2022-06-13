# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2019 eTech Consulting (<http://www.etechconsulting-mg.com>). All Rights Reserved
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    'name': 'Algolia : Website Sale Shop',
    'version': '13.0.1.0.0',
    'category': 'website',
    'sequence': -10,
    'summary': 'Use Algolia index for website sale shop',
    'author': 'eTech Consulting',
    'website': 'http://www.etechconsulting-mg.com',
    'depends': ['website_sale', 'connector_algolia_client'],
    'data': [
        # SECURITY
        # ASSETS
        # 'views/assets.xml',
        # VIEWS
        'views/template.xml',
        'views/algolia_application_views.xml',
        'views/website_views.xml'
    ],
    "assets": {
        'web.assets_frontend': [
            'https://cdn.jsdelivr.net/npm/algoliasearch@4.5.1/dist/algoliasearch-lite.umd.js',
            'https://cdn.jsdelivr.net/npm/instantsearch.js@4.8.3/dist/instantsearch.production.min.js',
            'https://cdn.jsdelivr.net/npm/instantsearch.css@7/themes/algolia-min.css',
            '/algolia_shop/static/src/scss/algolia_shop.scss',
            '/algolia_shop/static/src/js/algolia_widget.js',
        ],
    },
    'qweb': [],
    'demo': [],
    'application': True,
}
