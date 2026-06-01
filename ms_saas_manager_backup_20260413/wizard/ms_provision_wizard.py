# -*- coding: utf-8 -*-
import re
import secrets
import string
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class MsProvisionWizard(models.TransientModel):
    _name = 'ms.provision.wizard'
    _description = 'Provision Customer Database'

    subscription_id = fields.Many2one('ms.subscription', required=True)
    template_id     = fields.Many2one('ms.plan.template', required=True)
    db_name         = fields.Char(string='Database Name')
    subdomain       = fields.Char(string='Subdomain')
    admin_email     = fields.Char(string='Admin Email')
    admin_password  = fields.Char(string='Admin Password')
    language        = fields.Selection([
        ('en_US', 'English'),
        ('ar_001', 'Arabic'),
    ], default='en_US', string='Language')

    @api.onchange('subscription_id')
    def _onchange_subscription(self):
        if self.subscription_id:
            sub = self.subscription_id
            # Auto-generate DB name from company or partner name
            base = sub.company_name or sub.partner_id.name or 'client'
            slug = re.sub(r'[^a-z0-9]', '', base.lower())[:20] or 'client'
            self.db_name  = f'ms_{slug}'
            self.subdomain = slug
            self.admin_email = sub.email or f'admin@{slug}.msolutions-eg.com'
            self.admin_password = self._generate_password()

    @staticmethod
    def _generate_password(length=12):
        chars = string.ascii_letters + string.digits + '!@#$'
        return ''.join(secrets.choice(chars) for _ in range(length))

    def action_provision(self):
        self.ensure_one()
        sub = self.subscription_id

        # Validate DB name
        db_name = self.db_name or f'ms_client_{sub.id}'
        subdomain = self.subdomain or f'client{sub.id}'
        admin_email = self.admin_email or sub.email or 'admin@example.com'
        admin_password = self.admin_password or self._generate_password()

        # Sanitize
        db_name   = re.sub(r'[^a-z0-9_]', '_', db_name.lower())
        subdomain = re.sub(r'[^a-z0-9\-]', '-', subdomain.lower())

        # Check DB name not already taken
        existing = self.env['ms.managed.db'].search([('name', '=', db_name)])
        if existing:
            raise UserError(_('Database "%s" already exists. Choose a different name.') % db_name)

        # Create managed DB record
        managed_db = self.env['ms.managed.db'].create({
            'name':            db_name,
            'subdomain':       subdomain,
            'subscription_id': sub.id,
            'template_id':     self.template_id.id,
            'admin_email':     admin_email,
            'admin_password':  admin_password,
            'state':           'provisioning',
        })

        # Link to subscription
        sub.write({
            'db_name':  db_name,
            'subdomain': subdomain,
            'db_id':    managed_db.id,
        })

        # Run provisioning (this takes a few minutes)
        success = managed_db.provision(sub, admin_email, admin_password, self.language)

        if success:
            sub.message_post(
                body=_(
                    'Database provisioned: <b>%s</b><br/>'
                    'URL: <a href="https://%s.msolutions-eg.com">https://%s.msolutions-eg.com</a><br/>'
                    'Admin: %s'
                ) % (db_name, subdomain, subdomain, admin_email)
            )
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('✅ Database Ready!'),
                    'message': _(
                        'Database %s created at https://%s.msolutions-eg.com'
                    ) % (db_name, subdomain),
                    'type': 'success',
                    'sticky': True,
                },
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('❌ Provisioning Failed'),
                    'message': _('Check the error log in Managed Databases.'),
                    'type': 'danger',
                    'sticky': True,
                },
            }
