# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import models,fields


class ResUsers(models.Model):
    _inherit="res.users"

    sh_restrict_geo_location_mobile=fields.Boolean(string="Geo Fence")