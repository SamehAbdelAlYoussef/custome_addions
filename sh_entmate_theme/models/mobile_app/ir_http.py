# -*- coding: utf-8 -*-
from odoo import models
from odoo.http import request
from odoo.tools.image import image_data_uri


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        info = super().session_info()
        if request and request.session:
            info["session_id"] = request.session.sid
            info["avatar_128"] = image_data_uri(self.env.user.avatar_128)
            info["sh_restrict_geo_location_mobile"] = self.env.user.sh_restrict_geo_location_mobile
            info["sh_longitude_mobile"] = self.env.company.sudo().sh_longitude_mobile
            info["sh_latitude_mobile"] = self.env.company.sudo().sh_latitude_mobile
            info["sh_range_mobile"] = self.env.company.sudo().sh_range_mobile

            is_installed_sh_backmate_theme=self.env['ir.module.module'].sudo().search([
                    ('name', 'in', ['sh_backmate_theme','sh_backmate_theme_adv','sh_entmate_theme']),
                    ('state', '=', 'installed')
                ], limit = 1).sudo().ids
            info["is_installed_sh_backmate_theme"] = 0
            if is_installed_sh_backmate_theme:
                info["is_installed_sh_backmate_theme"] = 1
        return info
