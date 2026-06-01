from odoo import fields, models
from firebase_admin import initialize_app, _apps
from firebase_admin import credentials

class WebPushNotification(models.Model):
    _name = 'sh.push.notification'
    _description = 'Web Push Notification'

    user_id = fields.Many2one("res.users",string="User")
    user_type=fields.Selection([('public','Public'),('portal','Portal'),('internal','Internal')],string="User Type")
    datetime = fields.Datetime("Registration Time")
    register_id = fields.Char("Registration Id")

class ResCompany(models.Model):
    _inherit = 'res.company'

    enable_web_push_notification = fields.Boolean(
        "Enable Web Push Notification")

    sh_private_key_ref = fields.Char(string='Private Key Id',
                                  help="Private Key Id in the certificate")
    sh_project_id_firebase = fields.Char(string="Project Id",
                                      help='Corresponding projectId of '
                                           'firebase config')
    sh_private_key = fields.Char(string="Private Key",
                              help="Private Key value in the firebase "
                                   "certificate"
                              )
    sh_client_email = fields.Char(string="Client Email",
                               help='Client Email in the firebase config')
    sh_client_id_firebase = fields.Char(string="Client Id",
                                     help='Client Id in the firebase config')
    sh_client_cert_url = fields.Char(string="Client Certificate Url",
                                  help='Value corresponding to '
                                       'client_x509_cert_url in the '
                                       'firebase config')
    sh_vapid = fields.Char(string="Vapid", help='VapId of the firebase',
                        readonly=False)
    sh_api_key = fields.Char(string="Api Key",
                          help='Corresponding apiKey of firebase config',
                          readonly=False)
    sh_auth_domain = fields.Char(string="Auth Domain",
                              help='Corresponding authDomain of firebase '
                                   'config')
    sh_storage_bucket = fields.Char(string="Storage Bucket",
                                 help='Corresponding storageBucket of '
                                      'firebase config')
    sh_messaging_sender_id_firebase = fields.Char(string="Messaging Sender Id",
                                               help='Corresponding '
                                                    'messagingSenderId of '
                                                    'firebase config')
    sh_app_id_firebase = fields.Char(string="App Id",
                                  help='Corresponding appId of firebase config')
    sh_measurement_id_firebase = fields.Char(string="Measurement Id",
                                          help='Corresponding measurementId '
                                               'of firebase config')


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    enable_web_push_notification = fields.Boolean(
        related='company_id.enable_web_push_notification', readonly=False)

    sh_project_id_firebase = fields.Char(string="Project Id",
                                      help='Corresponding projectId of '
                                           'firebase config',
                                      related='company_id.sh_project_id_firebase',
                                      readonly=False)
    sh_private_key_ref = fields.Char(string='Private Key Id',
                                  help="Private Key Id in the certificate",
                                  related='company_id.sh_private_key_ref',
                                  readonly=False)
    sh_private_key = fields.Char(string="Private Key",
                              help="Private Key value in the firebase "
                                   "certificate",
                              related='company_id.sh_private_key', readonly=False)
    sh_client_email = fields.Char(string="Client Email", help='Client Email in '
                                                           'the firebase config',
                               related='company_id.sh_client_email',
                               readonly=False)
    sh_client_id_firebase = fields.Char(string="Client Id",
                                     help='Client Id in the firebase config',
                                     related='company_id.sh_client_id_firebase',
                                     readonly=False)
    sh_client_cert_url = fields.Char(string="Client Certificate Url",
                                  help='Value corresponding to '
                                       'client_x509_cert_url in the firebase '
                                       'config',
                                  related='company_id.sh_client_cert_url',
                                  readonly=False)
    sh_api_key = fields.Char(string="Api Key",
                          help='Corresponding apiKey of firebase config',
                          related='company_id.sh_api_key', readonly=False)
    sh_auth_domain = fields.Char(string="Auth Domain",
                              help='Corresponding authDomain of firebase '
                                   'config',
                              related='company_id.sh_auth_domain', readonly=False)

    sh_storage_bucket = fields.Char(string="Storage Bucket",
                                 help='Corresponding storageBucket of '
                                      'firebase config',
                                 related='company_id.sh_storage_bucket',
                                 readonly=False)
    sh_messaging_sender_id_firebase = fields.Char(string="Messaging Sender Id",
                                               help='Corresponding '
                                                    'messagingSenderId of '
                                                    'firebase config',
                                               related='company_id.sh_messaging_sender_id_firebase',
                                               readonly=False)
    sh_app_id_firebase = fields.Char(string="App Id",
                                  help='Corresponding appId of firebase config',
                                  related='company_id.sh_app_id_firebase',
                                  readonly=False)
    sh_measurement_id_firebase = fields.Char(string="Measurement Id",
                                          help='Corresponding measurementId '
                                               'of firebase config',
                                          related='company_id.sh_measurement_id_firebase',
                                          readonly=False)
    sh_vapid = fields.Char(string="Vapid", help='VapId of the firebase',
                        related='company_id.sh_vapid', readonly=False)

    def test_connection(self):
        """Test connection to firebase using the firebase credentials"""
        if not self.env.company.enable_web_push_notification:
            return False
        try:
            # Initialize the firebase app with the credentials
            if not _apps:
                cred = credentials.Certificate(
                    {
                        "type": "service_account",
                        "project_id": self.sh_project_id_firebase,
                        "private_key_id": self.sh_private_key_ref,
                        "private_key": self.sh_private_key.replace('\\n', '\n'),
                        "client_email": self.sh_client_email,
                        "client_id": self.sh_client_id_firebase,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                        "client_x509_cert_url": self.sh_client_cert_url,
                        "universe_domain": "googleapis.com"
                    }
                )
                initialize_app(cred)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'success',
                    'message': ("Connection successfully established"),
                }
            }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'danger',
                    'message': _(
                        "Failed to connect with firebase:%s" % e),
                }
            }
    


