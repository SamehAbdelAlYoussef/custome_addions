# Part of Softhealer Technologies.
import json
from odoo import http
import base64
from io import BytesIO
from odoo.tools.misc import file_open
from datetime import datetime
from odoo.tools.safe_eval import safe_eval
from odoo.http import request, route, Controller


class todo(Controller):
    @route('/todo/get_all', type='json', auth='public', methods=['POST'])
    def todo_get_all(self, name, rec, is_done):
        html = request.env['ir.ui.view']._render_template('sh_entmate_theme.todo_card',
                                           {'name': name, 'rec': rec, 'is_done': is_done})
        return html


class Main(http.Controller):
    @http.route('/get_theme_style', type='json', auth="public")
    def get_theme_style(self):
        theme_setting_rec = request.env['sh.ent.theme.config.settings'].sudo().search([
            ('id', '=', 1)], limit=1)
        
        print(theme_setting_rec.body_background_type)

        return {
                'theme_style': theme_setting_rec.theme_style,
                'sidebar_bg_color': theme_setting_rec.sidebar_color,
                'sidebar_font_color': theme_setting_rec.sidebar_font_color,
                'sidebar_img': theme_setting_rec.sidebar_img,
                'primary_color': theme_setting_rec.primary_color,
                'secondary_color': theme_setting_rec.secondary_color,
                'extra_color': theme_setting_rec.extra_color,
                'header_background_type': theme_setting_rec.header_background_type,
                'header_background_color': theme_setting_rec.header_background_color,
                'header_background_image': theme_setting_rec.header_background_image,
                'header_font_color': theme_setting_rec.header_font_color,
                'body_background_type': theme_setting_rec.body_background_type,
                'body_background_color': theme_setting_rec.body_background_color,
                'body_background_image': theme_setting_rec.body_background_image,
                'body_font_family': theme_setting_rec.body_font_family,
                'is_used_google_font': theme_setting_rec.is_used_google_font,
                'body_google_font_family': theme_setting_rec.body_google_font_family,
                'google_font': theme_setting_rec.body_google_font_family,
                'separator_style': theme_setting_rec.separator_style,
                'separator_color': theme_setting_rec.separator_color,
                'button_style': theme_setting_rec.button_style,
                'app_icon_style': theme_setting_rec.app_icon_style,
                'is_sticky_form': theme_setting_rec.is_sticky_form,
                'is_sticky_list': theme_setting_rec.is_sticky_list,
                'is_sticky_list_inside_form': theme_setting_rec.is_sticky_list_inside_form,
                'is_sticky_pivot': theme_setting_rec.is_sticky_pivot,
                'tab_style':theme_setting_rec.horizontal_tab_style,
                'predefined_list_view_boolean': theme_setting_rec.predefined_list_view_boolean,
                'predefined_list_view_style': theme_setting_rec.predefined_list_view_style,
                'list_view_border': theme_setting_rec.list_view_border,
                'list_view_even_row_color': theme_setting_rec.list_view_even_row_color,
                'list_view_odd_row_color': theme_setting_rec.list_view_odd_row_color,
                'list_view_is_hover_row': theme_setting_rec.list_view_is_hover_row,
                'list_view_hover_bg_color': theme_setting_rec.list_view_hover_bg_color,
                'login_page_style': theme_setting_rec.login_page_style,
                'login_page_background_type': theme_setting_rec.login_page_background_type,
                'login_page_background_color': theme_setting_rec.login_page_background_color,
                'login_page_box_color': theme_setting_rec.login_page_box_color,
                'progress_style': theme_setting_rec.progress_style,
                'progress_height': theme_setting_rec.progress_height,
                'progress_color': theme_setting_rec.progress_color,
                'form_element_style': theme_setting_rec.form_element_style,
                'breadcrumb_style': theme_setting_rec.breadcrumb_style,
                'checkbox_style': theme_setting_rec.checkbox_style,
                'radio_style': theme_setting_rec.radio_style,
                'scrollbar_style': theme_setting_rec.scrollbar_style,
                'kanban_box_style': theme_setting_rec.kanban_box_style,
                'backend_all_icon_style': theme_setting_rec.backend_all_icon_style,
                'chatter_type': theme_setting_rec.chatter_type,
        }
    
    
    @http.route('/api/upload/multi', type='http', auth="none", csrf=False)
    def Upload_image(self, **kwargs):

        print(f' \n\n___________________________________________\n\n')
        print(kwargs)

        theme_setting_rec = request.env['sh.ent.theme.config.settings'].sudo().search([
            ('id', '=', 1)], limit=1)

        if kwargs.get('body_background_img'):
            print("yes got")
            body_background_img = base64.b64encode(
                kwargs.get('body_background_img').read())
            if theme_setting_rec:
                theme_setting_rec.write(
                    {'body_background_image': body_background_img})

        if kwargs.get('header_background_img'):
            body_background_img = base64.b64encode(
                kwargs.get('header_background_img').read())
            if theme_setting_rec:
                theme_setting_rec.write(
                    {'header_background_image': body_background_img})

        if kwargs.get('login_page_background_img'):
            print("login page style got it")
            login_page_background_image = base64.b64encode(
                kwargs.get('login_page_background_img').read())
            if login_page_background_image:
                theme_setting_rec.write(
                    {'login_page_background_image': login_page_background_image})
                
        if kwargs.get('login_page_banner_image'):
            print("login page style banner")
            login_page_banner_image = base64.b64encode(
                kwargs.get('login_page_banner_image').read())
            print("|||||||||||||||")
            print(login_page_banner_image)
            if login_page_banner_image:
                theme_setting_rec.write(
                    {'login_page_banner_image': login_page_banner_image})
                
            

        return json.dumps({})

    @http.route('/firebase-messaging-sw.js', type='http', auth="public")
    def sw_http(self):
        """Fixed service worker for Firebase Cloud Messaging"""
        try:
            # Get Firebase config from system parameters
            config_param = request.env['ir.config_parameter'].sudo().get_param(
                'sh_push_notification.config', 
                '{}'
            )
            
            # Get VAPID key
            vapid_key = ""
            try:
                if hasattr(request.env.company, 'vapid'):
                    vapid_key = request.env.company.vapid or ""
            except:
                vapid_key = ""
            
            if config_param and config_param != '{}':
                # Parse and clean the config
                import json as json_lib
                try:
                    config_dict = json_lib.loads(config_param)
                except:
                    # Fallback to string cleaning for old format
                    config_param = config_param.replace(" ", "").replace("\n", "").replace("\t", "")
                    config_param = config_param.replace('"', "'")
                    config_dict = safe_eval(config_param)
                
                # Build JavaScript with proper escaping
                firebase_config_js = json_lib.dumps(config_dict, indent=4)
                
                js = f"""
// Firebase Cloud Messaging Service Worker
this.addEventListener('install', function(e) {{
    e.waitUntil(
        caches.open('firebase-cache').then(function(cache) {{
            return cache.addAll([
                '/sh_entmate_theme/static/index.js'
            ]);
        }})
    );
    self.skipWaiting();
}});

this.addEventListener('activate', function(event) {{
    event.waitUntil(self.clients.claim());
}});

this.addEventListener('fetch', function(e) {{
    e.respondWith(
        caches.match(e.request).then(function(response) {{
            return response || fetch(e.request);
        }})
    );
}});

importScripts('https://www.gstatic.com/firebasejs/9.0.0/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/9.0.0/firebase-messaging-compat.js');

// Firebase Configuration
const firebaseConfig = {firebase_config_js};

// Initialize Firebase
firebase.initializeApp(firebaseConfig);

// Get messaging instance
const messaging = firebase.messaging();

// Handle background messages
messaging.onBackgroundMessage(function(payload) {{
    console.log('[Firebase SW] Background message received:', payload);
    
    const notificationTitle = payload.notification?.title || 'Notification';
    const notificationOptions = {{
        body: payload.notification?.body || '',
        icon: payload.notification?.icon || '/logo.png',
        badge: '/logo.png',
        data: payload.data || {{}}
    }};
    
    return self.registration.showNotification(
        notificationTitle,
        notificationOptions
    );
}});

// Log successful initialization
console.log('[Firebase SW] Service worker initialized successfully');
"""
            else:
                # Return minimal service worker if no config
                js = """
// Minimal Service Worker
this.addEventListener('install', function(e) {
    e.waitUntil(self.skipWaiting());
});

this.addEventListener('activate', function(event) {
    event.waitUntil(self.clients.claim());
});

console.log('[Firebase SW] Minimal service worker loaded');
"""
            
            return http.request.make_response(js, [('Content-Type', 'text/javascript')])
            
        except Exception as e:
            # Fallback service worker on error
            error_js = f"""
// Error in Firebase Service Worker
console.error('[Firebase SW] Error: {str(e)}');

self.addEventListener('install', (e) => e.waitUntil(self.skipWaiting()));
self.addEventListener('activate', (e) => e.waitUntil(self.clients.claim()));

self.addEventListener('fetch', (e) => {{
    e.respondWith(fetch(e.request));
}});
"""
            return http.request.make_response(error_js, [('Content-Type', 'text/javascript')])
        
    @http.route('/web/push_token', type='http', auth="public", csrf=False)
    def getToken(self,**post):
        device_search = request.env['sh.push.notification'].sudo().search(
            [('register_id', '=', post.get('name'))], limit=1)
        
        if device_search and not request.env.user._is_public() and device_search.user_id != request.env.user.id:
            if request.env.user.has_group('base.group_portal'):
                device_search.write({'user_id':request.env.user.id,'user_type':'portal'})
            elif request.env.user:
                device_search.write({'user_id':request.env.user.id,'user_type':'internal'})
                
        if not device_search:
            vals = {
                'register_id' : post.get('name'),
                'datetime' : datetime.now()
            }
            if request.env.user._is_public():
                public_users = request.env['res.users'].sudo()
                public_groups = request.env.ref("base.group_public", raise_if_not_found=False)
                if public_groups:
                    public_users = public_groups.sudo().with_context(active_test=False).mapped("users")
                    if public_users:
                        vals.update({'user_id':public_users[0].id,'user_type':'public'})
            elif request.env.user.has_group('base.group_portal'):
                vals.update({'user_id':request.env.user.id,'user_type':'portal'})
            elif request.env.user:
                vals.update({'user_id':request.env.user.id,'user_type':'internal'})
            
            request.env['sh.push.notification'].sudo().create(vals)

    @http.route('/web/_config', type='json', auth="public")
    def sendConfig(self):
        """Send Firebase configuration to frontend"""
        try:
            # Get config from parameter
            config_param = request.env['ir.config_parameter'].sudo().get_param(
                'sh_push_notification.config', 
                '{}'
            )
            
            config_vals = {}
            if config_param and config_param != '{}':
                try:
                    # Parse JSON config
                    import json as json_lib
                    config_dict = json_lib.loads(config_param)
                    
                    config_vals['apiKey'] = config_dict.get('apiKey', '')
                    config_vals['authDomain'] = config_dict.get('authDomain', '')
                    config_vals['projectId'] = config_dict.get('projectId', '')
                    config_vals['storageBucket'] = config_dict.get('storageBucket', '')
                    config_vals['messagingSenderId'] = config_dict.get('messagingSenderId', '')
                    config_vals['appId'] = config_dict.get('appId', '')
                    config_vals['measurementId'] = config_dict.get('measurementId', '')
                except:
                    # Fallback to string parsing for old format
                    config_param = config_param.replace(" ", "").replace("\n", "").replace("\t", "")
                    config_param = config_param.replace('"', "'")
                    config_param = config_param.replace('apiKey', "'apiKey'")
                    config_param = config_param.replace('authDomain', "'authDomain'")
                    config_param = config_param.replace('projectId', "'projectId'")
                    config_param = config_param.replace('storageBucket', "'storageBucket'")
                    config_param = config_param.replace('messagingSenderId', "'messagingSenderId'")
                    config_param = config_param.replace('appId', "'appId'")
                    config_param = config_param.replace('measurementId', "'measurementId'")
                    
                    config_dict = safe_eval(config_param)
                    
                    config_vals['apiKey'] = config_dict.get('apiKey', '')
                    config_vals['authDomain'] = config_dict.get('authDomain', '')
                    config_vals['projectId'] = config_dict.get('projectId', '')
                    config_vals['storageBucket'] = config_dict.get('storageBucket', '')
                    config_vals['messagingSenderId'] = config_dict.get('messagingSenderId', '')
                    config_vals['appId'] = config_dict.get('appId', '')
                    config_vals['measurementId'] = config_dict.get('measurementId', '')
            
            # Get VAPID key
            vapid_key = ""
            try:
                if hasattr(request.env.company, 'vapid'):
                    vapid_key = request.env.company.vapid or ""
            except:
                vapid_key = ""
            
            vals = {
                'vapid': vapid_key,
                'config': config_vals
            }
            
            return json.dumps(vals)
            
        except Exception as e:
            # Return empty config on error
            return json.dumps({'vapid': '', 'config': {}})
    
    # MULTI TAB START
    @http.route(['/add/mutli/tab'], type='json', auth='public')
    def add_multi_tab(self, **kw):
        user = request.env.user

        multi_tab_ids = user.multi_tab_ids.filtered(
            lambda mt: mt.name == kw.get('name'))
        if not multi_tab_ids:
            user.sudo().write({
                'multi_tab_ids': [(0, 0,  {
                    'name': kw.get('name'),
                    'url': kw.get('url'),
                    'actionId': kw.get('actionId'),
                    'menuId': kw.get('menuId'),
                    'menu_xmlid': kw.get('menu_xmlid'),
                })]
            })

        return True

    @http.route(['/get/mutli/tab'], type='json', auth='public')
    def get_multi_tab(self, **kw):
        obj = request.env['biz.multi.tab']
        user = request.env.user
        if user.multi_tab_ids:
            record_dict = user.multi_tab_ids.sudo().read(set(obj._fields))
            return record_dict
        else:
            return False

    @http.route(['/remove/multi/tab'], type='json', auth='public')
    def remove_multi_tab(self, **kw):
        multi_tab = request.env['biz.multi.tab'].sudo().search(
            [('id', '=', kw.get('multi_tab_id'))])
        multi_tab.unlink()
        user = request.env.user
        multi_tab_count = len(user.multi_tab_ids)
        values = {
            'removeTab': True,
            'multi_tab_count': multi_tab_count,
        }
        return values

    @http.route(['/update/tab/details'], type='json', auth='public')
    def update_tabaction(self, **kw):
        tabId = kw.get('tabId')
        TabTitle = kw.get('TabTitle')
        url = kw.get('url')
        ActionId = kw.get('ActionId')
        menu_xmlid = kw.get('menu_xmlid')

        multi_tab = request.env['biz.multi.tab'].sudo().search(
            [('id', '=', tabId)])
        if multi_tab:
            multi_tab.sudo().write({
                'name': TabTitle or multi_tab.name,
                'url': url or multi_tab.url,
                'actionId': ActionId or multi_tab.ActionId,
                'menu_xmlid': menu_xmlid or multi_tab.menu_xmlid,
            })
        return True
    # MULTI TAB END


    @http.route(['/get/attachment/data'], type='json', auth='public')
    def get_attachment_data(self, **kw):
        rec_ids = kw.get('rec_ids')
        for rec in rec_ids:
            if isinstance(rec, str):
                rec_ids.remove(rec)
        if kw.get('model') and rec_ids:
            # FOR DATA SPEED ISSUE; SEARCH ATTACHMENT DATA WITH SQL QUERY
            attachments = request.env['ir.attachment'].sudo().search([
                ('res_model', '=', kw.get('model'))
            ])
            attachment_data = []
            attachment_res_id_set = set()
            for attachment in attachments:
                attachment_res_id_set.add(attachment.res_id)
            dict = {}
            for res_id in attachment_res_id_set:
                filtered_attachment_record = attachments.filtered(
                    lambda attachment: attachment.res_id == res_id)
                for fac in filtered_attachment_record:
                    if dict.get(res_id):
                        dict[res_id].append({
                            'attachment_id': fac.id,
                            'attachment_mimetype': fac.mimetype,
                            'attachment_name': fac.name,
                        })
                    else:
                        dict[res_id] = [{
                            'attachment_id': fac.id,
                            'attachment_mimetype': fac.mimetype,
                            'attachment_name': fac.name,
                        }]
            attachment_data.append(dict)
            return attachment_data

    @http.route('/recent_records/fetch', type='json', auth='user')
    def fetch_recent_records(self):
        user_id = request.env.user.id
        recent_records = request.env['sh.recent.records'].sudo().search([('sh_user_id', '=', user_id)])
        return {
            'data': [{
                'sh_model': record.sh_model,
                'record_id': record.record_id,
                'name': record.name,
            } for record in recent_records]
        }

            
#----------------------------------------------------------
# Odoo quick create web Controllers
#----------------------------------------------------------
class QuickCreate(http.Controller):

    @http.route(['/create/quick/action'], type='json', auth='user', methods=['POST'])
    def create_quick_action_records(self,data):
        action_vals={
            'name': data.get('name'),
            'icon': data.get('icon'),
            'sequence': data.get('sequence'),
            'model_id': data.get('model_id'),
            'sh_user_id': request.env.user.id,
        }
        new_record=request.env['sh.quick.create'].sudo().create(action_vals)
        return True


        # return mentioned_dict
    
    @http.route(['/get/quick/action/data'], type='json', auth='user', methods=['POST'])
    def get_quick_action_data(self):
        final_data_list=[]
        total_data=request.env['sh.quick.create'].sudo().search([('sh_user_id','=',request.env.user.id)],order='sequence asc')
        for action in total_data:
            data_dict={
                'id':action.id,
                'name':action.name,
                'model_id':action.model_id.id,
                'icon':action.icon,
                'sequence':action.sequence,
                'model_name':action.model_name,
            }
            final_data_list.append(data_dict)

        allow_model_dict={}
        models=request.env['ir.model'].sudo().search([])

        for model in models:
            allow_model_dict[model.id]=model.display_name

        if not final_data_list:
            final_data_list=False

        return final_data_list,allow_model_dict

    
    @http.route(['/get/edit/quick/action/data'], type='json', auth='user', methods=['POST'])
    def get_edit_quick_action_data(self,action_id):
        data=request.env['sh.quick.create'].sudo().browse(action_id)

        final_data_list=[]
        data_dict={
            'id':data.id,
            'name':data.name,
            'model_id':data.model_id.id,
            'icon':data.icon,
            'sequence':data.sequence,
            'model_name':data.model_name,
        }
        final_data_list.append(data_dict)
        return final_data_list

    
    @http.route(['/unlink/quick/action/data'], type='json', auth='user', methods=['POST'])
    def unlink_quick_action_data(self,action_id):
        data=request.env['sh.quick.create'].sudo().browse(action_id)
        data.sudo().unlink()
       
        return True
    
    @http.route(['/update/quick/action'], type='json', auth='user', methods=['POST'])
    def update_quick_action_data(self,data,action_id):
        current_record=request.env['sh.quick.create'].sudo().browse(action_id)
        action_vals={
            'name': data.get('name'),
            'icon': data.get('icon'),
            'sequence': data.get('sequence'),
            'model_id': data.get('model_id'),
            'sh_user_id': request.env.user.id,
        }
        current_record.sudo().write(action_vals)
        return True
