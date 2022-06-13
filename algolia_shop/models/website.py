# -*- coding: utf-8 -*-

from odoo import fields, models


class Website(models.Model):
    _inherit = 'website'

    algolia_app_id = fields.Many2one('algolia.application')
    algolia_index_id = fields.Many2one('algolia.index')
