# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

import base64
import functools
import io
import json
import logging
import os
import unicodedata

try:
    from werkzeug.utils import send_file
except ImportError:
    from odoo.tools._vendor.send_file import send_file

import odoo
import odoo.modules.registry
from odoo import http, _
from odoo.exceptions import AccessError, UserError
from odoo.http import request, Response
from odoo.modules import get_resource_path
from odoo.tools import file_open, file_path, replace_exceptions
from odoo.tools.mimetypes import guess_mimetype
from odoo.tools.image import image_guess_size_from_field_name


_logger = logging.getLogger(__name__)

BAD_X_SENDFILE_ERROR = """\
Odoo is running with --x-sendfile but is receiving /web/filestore requests.

With --x-sendfile enabled, NGINX should be serving the
/web/filestore route, however Odoo is receiving the
request.

This usually indicates that NGINX is badly configured,
please make sure the /web/filestore location block exists
in your configuration file and that it is similar to:

    location /web/filestore {{
        internal;
        alias {data_dir}/filestore;
    }}
"""


from odoo.addons.web.controllers.binary import Binary


class shFlutterAttachment(Binary):

    @http.route()
    # pylint: disable=redefined-builtin,invalid-name
    def content_common(self, xmlid=None, model='ir.attachment', id=None, field='raw',
                       filename=None, filename_field='name', mimetype=None, unique=False,
                       download=False, access_token=None, nocache=False, **post):
        
        
        # -------------------------------------------------------------------------
        # if called from flutter we have added sudo() in order to download 
        # record = record.sudo()
        # private attachment.
        # -------------------------------------------------------------------------
        print(f"\n\n=111111111=>> filename: {filename}")
        if not filename:
            attahment=request.env['ir.attachment'].sudo().browse(id)
            print(f"\n\n==2222222222>> attahment: {attahment}")
            filename = attahment.name if attahment else ''
        filename, extension = os.path.splitext(filename)
        print(f"\n\n=333333=>> filename: {filename}")
        print(f"\n\n==444444444444>> extension: {extension}")
        print(f"\n\n=555555555555=>> post: {post}")
        if post.get('sh_unique',False) == 'hhlf2B1uquNUr0N29io5KsEnm6q2YLdL69PC5rbJQtGToNWjWm' and model == 'ir.attachment':
        #if True:
            with replace_exceptions(UserError, by=request.not_found()):
                record = request.env['ir.binary']._find_record(xmlid, model, id and int(id), access_token)
                # softhealer custom code we have just added below line from the standard method
                record = record.sudo()

                # Softhealer custom code.

                stream = request.env['ir.binary']._get_stream_from(record, field, filename, filename_field, mimetype)
            send_file_kwargs = {'as_attachment': download}
            if unique:
                send_file_kwargs['immutable'] = True
                send_file_kwargs['max_age'] = http.STATIC_CACHE_LONG
            if nocache:
                send_file_kwargs['max_age'] = None
            # send_file_kwargs['sh_filename'] = filename
            # send_file_kwargs['sh_extension'] = extension
            res = stream.get_response(**send_file_kwargs)
            #res.headers['Content-Security-Policy'] = "default-src 'none'"
            res.headers['Content-Security-Policy'] = "default-src 'none'"
            res.headers['X-Content-Type-Options'] = 'nosniff'
            res.headers['sh_filename'] = filename
            res.headers['sh_extension'] = extension
            print(f"\n\n response==>> res: {res}")
            print(f"\n\n response==>> res.headers: {res.headers}")
            print(f"\n\n response==>> stream: {stream}")
            print(f"\n\n response==>> send_file_kwargs: {send_file_kwargs}")

            return res
        # -------------------------------------------------------------------------
        # if called from flutter we have added sudo() in order to download 
        # record = record.sudo()
        # private attachment.
        # ------------------------------------------------------------------------- 
        print(f"\n\n content_common==>> xmlid: {xmlid}")
        print(f"\n\n content_common==>> model: {model}")
        print(f"\n\n content_common==>> id: {id}")
        print(f"\n\n content_common==>> field: {field}")
        print(f"\n\n content_common==>> filename: {filename}")

        print(f"\n\n content_common==>> filename_field: {filename_field}")
        print(f"\n\n content_common==>> mimetype: {mimetype}")
        print(f"\n\n content_common==>> unique: {unique}")
        print(f"\n\n content_common==>> download: {download}")
        print(f"\n\n content_common==>> access_token: {access_token}")        
        print(f"\n\n content_common==>> nocache: {nocache}")        
        print(f"\n\n content_common==>> post: {post}")        
        return super(shFlutterAttachment,self).content_common(xmlid, model, id, field,
                       filename, filename_field, mimetype, unique,
                       download, access_token, nocache, **post)
    