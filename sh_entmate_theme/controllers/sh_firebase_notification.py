import json
from odoo import http
from odoo.http import request
from datetime import datetime


class Main(http.Controller):

    @http.route('/firebase-messaging-sw.js', type='http', auth="public")
    def sw_http(self):
        """Returns the Firebase service worker script.
                :return: The Firebase service worker script.
                :rtype: str"""
        if request.env.company and request.env.company.enable_web_push_notification:
            firebase_js = """
                    this.addEventListener('fetch', function(e) {
                      e.respondWith(
                        caches.match(e.request).then(function(response) {
                          return response || fetch(e.request);
                        })
                      );
                    });
                    importScripts('https://www.gstatic.com/firebasejs/8.4.2/firebase-app.js');
                    importScripts('https://www.gstatic.com/firebasejs/8.4.2/firebase-messaging.js');
                    var firebaseConfig = {
                        apiKey: '%s',
                        authDomain: '%s',
                        projectId: '%s',
                        storageBucket: '%s',
                        messagingSenderId: '%s',
                        appId: '%s',
                        measurementId: '%s',
                    };
                    firebase.initializeApp(firebaseConfig);
                    const messaging = firebase.messaging();
                    messaging.setBackgroundMessageHandler(function(payload) {
                    const notificationTitle = "Background Message Title";
                    const notificationOptions = {
                        body: payload.notification.body,
                        icon:'/mail_push_notification/static/description/icon.png',
                    };
                    return self.registration.showNotification(
                        notificationTitle,
                        notificationOptions,
                    );
                    });
                    """ % (
                request.env.company.sh_api_key, request.env.company.sh_auth_domain,
                request.env.company.sh_project_id_firebase,
                request.env.company.sh_storage_bucket,
                request.env.company.sh_messaging_sender_id_firebase,
                request.env.company.sh_app_id_firebase,
                request.env.company.sh_measurement_id_firebase)
        else:
            firebase_js = """
                        this.addEventListener('fetch', function(e) {
                          e.respondWith(
                            caches.match(e.request).then(function(response) {
                              return response || fetch(e.request);
                            })
                          );
                        });
                    """
        return http.request.make_response(firebase_js, [
            ('Content-Type', 'text/javascript')])

    @http.route('/push_notification', type='http', auth="public",csrf=False)
    def get_registration_tokens(self, **post):
        """Handles registration tokens for push notifications.
         Create a new registration token if it doesn't already exist
        :param post: POST request data containing registration token.
        :type post: dict
       """
        device_search = request.env['sh.push.notification'].sudo().search(
            [('register_id', '=', post.get('name'))], limit=1)

        if device_search and not request.env.user._is_public() and device_search.user_id != request.env.user.id:
            if request.env.user.has_group('base.group_portal'):
                device_search.write({'user_id': request.env.user.id, 'user_type': 'portal'})
            elif request.env.user:
                device_search.write({'user_id': request.env.user.id, 'user_type': 'internal'})

        if not device_search:
            vals = {
                'register_id': post.get('name'),
                'datetime': datetime.now()
            }
            if request.env.user._is_public():
                public_users = request.env['res.users'].sudo()
                public_groups = request.env.ref("base.group_public", raise_if_not_found=False)
                if public_groups:
                    public_users = public_groups.sudo().with_context(active_test=False).mapped("users")
                    if public_users:
                        vals.update({'user_id': public_users[0].id, 'user_type': 'public'})
            elif request.env.user.has_group('base.group_portal'):
                vals.update({'user_id': request.env.user.id, 'user_type': 'portal'})
            elif request.env.user:
                vals.update({'user_id': request.env.user.id, 'user_type': 'internal'})

            request.env['sh.push.notification'].sudo().create(vals)

    @http.route('/firebase_config_details', type='json', auth="public")
    def send_datas(self):
        """Sends Firebase configuration details.
        :return: JSON containing Firebase configuration details.
        :rtype: str"""
        if request.env.company and request.env.company.enable_web_push_notification:
            return json.dumps({
                'vapid': request.env.company.sh_vapid,
                'config': {
                    'apiKey': request.env.company.sh_api_key,
                    'authDomain': request.env.company.sh_auth_domain,
                    'projectId': request.env.company.sh_project_id_firebase,
                    'storageBucket': request.env.company.sh_storage_bucket,
                    'messagingSenderId': request.env.company.sh_messaging_sender_id_firebase,
                    'appId': request.env.company.sh_app_id_firebase,
                    'measurementId': request.env.company.sh_measurement_id_firebase
                }
            })

    @http.route('/firebase_credentials', type="json", auth="public")
    def firebase_credentials(self, **kw):
        """ Retrieve Firebase credentials for the current company."""
        return {'id': request.env.company.id,
                'push_notification': request.env.company.enable_web_push_notification}