# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.addons.web.controllers.home import Home as WebHome
from odoo.addons.web.controllers.utils import is_user_internal
from odoo.http import request

import odoo

class sh_backmate_theme_mobile_Home(WebHome):

    @http.route()
    def web_client(self, s_action=None, **kw):
        
        if kw.get('sh_backmate_theme_mobile_login',False) and kw.get('db',False)  and kw.get('login',False) and kw.get('password',False):
            try:
                uid = request.session.authenticate(kw.get('db'), kw.get('login'), kw.get('password') )
                # request.params['login_success'] = True
                response = request.redirect(self._login_redirect(uid, redirect=None))
                # Set cookie here in order to use that cookie in javascript mobile
                # service to hide/show log out and switch user menu.
                response.set_cookie(
                    key='sh_backmate_theme_mobile_login_web_view',
                    value='true',
                )                
                
                return response
            except Exception as e:
                pass
            # if e.args == odoo.exceptions.AccessDenied().args:
            #     values['error'] = _("Wrong login/password")
            # else:
            #     values['error'] = e.args[0]

        # if request.session.uid and not is_user_internal(request.session.uid):
        #     return request.redirect_query('/my', query=request.params)
        return super().web_client(s_action, **kw)