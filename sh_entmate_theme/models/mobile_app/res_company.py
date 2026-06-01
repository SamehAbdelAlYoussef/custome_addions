# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import models,fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    sh_longitude_mobile=fields.Float(string="Longitude",digits=(16, 6))
    sh_latitude_mobile=fields.Float(string="Latitude",digits=(16, 6))
    sh_range_mobile=fields.Float(string="Range")