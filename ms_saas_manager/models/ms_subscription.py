# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import re
import logging

_logger = logging.getLogger(__name__)


class MsSubscription(models.Model):
    _name = 'ms.subscription'
    _description = 'SaaS Subscription'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_start desc'

    name         = fields.Char(string='Reference', readonly=True, default='New', copy=False)

    # ── Customer ────────────────────────────────────────────────────
    partner_id   = fields.Many2one('res.partner', string='Customer', required=True, tracking=True)
    email        = fields.Char(related='partner_id.email', store=True)
    phone        = fields.Char(related='partner_id.phone', store=True)
    company_name = fields.Char(string='Company Name')

    # ── Plan ────────────────────────────────────────────────────────
    template_id    = fields.Many2one('ms.plan.template', string='Plan', required=True, tracking=True)
    billing_cycle  = fields.Selection([
        ('monthly', 'Monthly'),
        ('yearly',  'Yearly'),
    ], default='monthly', required=True, tracking=True)
    extra_user_packs = fields.Integer(string='Extra User Packs (×5)', default=0)
    total_users      = fields.Integer(compute='_compute_totals', store=True, string='Total Users')
    total_amount     = fields.Float(compute='_compute_totals',  store=True, string='Amount (EGP)')

    # ── Database ────────────────────────────────────────────────────
    db_name      = fields.Char(string='Database Name', readonly=True, copy=False)
    db_id        = fields.Many2one('ms.managed.db', string='Managed DB', readonly=True)
    subdomain    = fields.Char(string='Subdomain', readonly=True,
                               help='e.g. acme → acme.msolutions-eg.com')
    url          = fields.Char(string='Customer URL', compute='_compute_url')
    admin_login  = fields.Char(related='db_id.admin_email', string='Admin Login', readonly=True)
    admin_pass   = fields.Char(related='db_id.admin_password', string='Admin Password', readonly=True)

    # ── Dates ───────────────────────────────────────────────────────
    date_start       = fields.Date(default=fields.Date.context_today, tracking=True)
    trial_end        = fields.Date(compute='_compute_trial_end', store=True)
    date_next_invoice = fields.Date(string='Next Invoice Date', tracking=True)
    date_end         = fields.Date(string='End Date', tracking=True)

    # ── State ───────────────────────────────────────────────────────
    state = fields.Selection([
        ('draft',     'Draft'),
        ('trial',     'Free Trial'),
        ('active',    'Active'),
        ('paused',    'Paused'),
        ('cancelled', 'Cancelled'),
        ('expired',   'Expired'),
    ], default='draft', tracking=True, copy=False)

    # ── Invoices ────────────────────────────────────────────────────
    invoice_ids    = fields.One2many('ms.invoice', 'subscription_id', string='Invoices')
    invoice_count  = fields.Integer(compute='_compute_invoice_count')
    total_paid     = fields.Float(compute='_compute_invoice_count', string='Total Paid')

    notes = fields.Text()

    # ── Email Verification ────────────────────────────────────────
    verify_token    = fields.Char(string='Verification Token', copy=False, index=True)
    email_verified  = fields.Boolean(string='Email Verified', default=False, copy=False)

    # ── Email Verification ────────────────────────────────────────
    verify_token    = fields.Char(string='Verification Token', copy=False, index=True)
    email_verified  = fields.Boolean(string='Email Verified', default=False, copy=False)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    # ── Compute ─────────────────────────────────────────────────────

    @api.depends('template_id', 'billing_cycle', 'extra_user_packs')
    def _compute_totals(self):
        for s in self:
            if not s.template_id:
                s.total_users = s.total_amount = 0
                continue
            s.total_users = s.template_id.max_users + (s.extra_user_packs * 5)
            if s.billing_cycle == 'monthly':
                base = s.template_id.monthly_price
                extra = s.template_id.extra_users_price * s.extra_user_packs
            else:
                base = s.template_id.yearly_price
                extra = s.template_id.extra_users_price * s.extra_user_packs * 12
            s.total_amount = base + extra

    @api.depends('template_id', 'date_start')
    def _compute_trial_end(self):
        for s in self:
            if s.template_id and s.date_start:
                s.trial_end = s.date_start + timedelta(days=s.template_id.trial_days)
            else:
                s.trial_end = False

    def _compute_url(self):
        domain = 'msolutions-eg.com'
        for s in self:
            if s.subdomain:
                s.url = f'https://{s.subdomain}.{domain}'
            else:
                s.url = False

    def _compute_invoice_count(self):
        for s in self:
            paid = s.invoice_ids.filtered(lambda i: i.state == 'paid')
            s.invoice_count = len(s.invoice_ids)
            s.total_paid = sum(paid.mapped('amount'))

    # ── Sequence ────────────────────────────────────────────────────

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('ms.subscription') or 'New'
        return super().create(vals_list)

    # ── Actions ─────────────────────────────────────────────────────

    def action_start_trial(self):
        for s in self:
            s.state = 'trial'
            s.date_start = date.today()
            s.message_post(body=_('Free trial started. Ends: %s') % s.trial_end)
            s._notify_admin()

    def action_provision_and_notify(self):
        """Called async after signup - provisions DB then sends welcome email."""
        for s in self:
            # Step 1: Provision database
            try:
                s._provision_database()
                self.env.cr.commit()
                _logger.info('Database provisioned and committed for %s', s.name)
            except Exception as e:
                self.env.cr.rollback()
                _logger.error('Provision failed for %s: %s', s.name, e)
                try:
                    s.message_post(body=_('Provisioning error: %s') % e)
                    self.env.cr.commit()
                except Exception:
                    self.env.cr.rollback()
                return

            # Step 2: Send welcome email directly via mail.mail
            try:
                admin_email = s.db_id.admin_email if s.db_id else s.email
                admin_pass = s.db_id.admin_password if s.db_id else 'N/A'
                body = (
                    '<div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">'
                    '<div style="background:#1A6B3A;padding:30px;text-align:center;">'
                    '<h1 style="color:#fff;margin:0;">Manager Solutions</h1>'
                    '<p style="color:#a3d9b1;margin:5px 0;">Cloud Accounting Platform</p>'
                    '</div>'
                    '<div style="padding:30px;background:#fff;">'
                    '<h2>Welcome, ' + str(s.partner_id.name) + '!</h2>'
                    '<p>Your <strong>' + str(s.template_id.name) + '</strong> free trial has started.</p>'
                    '<p><strong>Your system is ready at:</strong></p>'
                    '<div style="text-align:center;margin:20px 0;">'
                    '<a href="' + str(s.url) + '" style="background:#1A6B3A;color:#fff;padding:14px 28px;'
                    'border-radius:6px;text-decoration:none;font-size:16px;display:inline-block;">'
                    'Open My System</a></div>'
                    '<div style="background:#f0f7f2;border-radius:8px;padding:20px;margin:20px 0;">'
                    '<h3 style="color:#1A6B3A;margin:0 0 12px;">Your Login Credentials</h3>'
                    '<table style="width:500px;border-collapse:collapse;">'
                    '<tr><td style="padding:8px;border-bottom:1px solid #ddd;color:#666;">URL</td>'
                    '<td style="padding:8px;border-bottom:1px solid #ddd;font-weight:bold;">'
                    '<a href="' + str(s.url) + '/web/login" style="color:#1A6B3A;">' + str(s.url) + '</a></td></tr>'
                    '<tr><td style="padding:8px;border-bottom:1px solid #ddd;color:#666;">Username</td>'
                    '<td style="padding:8px;border-bottom:1px solid #ddd;font-weight:bold;">' + str(admin_email) + '</td></tr>'
                    '<tr><td style="padding:8px;border-bottom:1px solid #ddd;color:#666;">Password</td>'
                    '<td style="padding:8px;border-bottom:1px solid #ddd;font-weight:bold;">' + str(admin_pass) + '</td></tr>'
                    '</table>'
                    '<p style="color:#888;font-size:12px;margin:10px 0 0;">Please change your password after first login.</p>'
                    '</div>'
                    '<table style="width:500px;border-collapse:collapse;margin:20px 0;">'
                    '<tr><td style="padding:8px;border-bottom:1px solid #eee;"><strong>Plan</strong></td>'
                    '<td style="padding:8px;border-bottom:1px solid #eee;">' + str(s.template_id.name) + '</td></tr>'
                    '<tr><td style="padding:8px;border-bottom:1px solid #eee;"><strong>Trial Ends</strong></td>'
                    '<td style="padding:8px;border-bottom:1px solid #eee;">' + str(s.trial_end) + '</td></tr>'
                    '<tr><td style="padding:8px;"><strong>Users</strong></td>'
                    '<td style="padding:8px;">' + str(s.total_users) + ' users included</td></tr>'
                    '</table>'
                    '<p>Need help? Reply to this email and our team will assist you.</p>'
                    '</div>'
                    '<div style="background:#f2f3f4;padding:20px;text-align:center;color:#888;font-size:12px;">'
                    'Manager Solutions - <a href="https://msolutions-eg.com">msolutions-eg.com</a>'
                    '</div></div>'
                )
                mail = self.env['mail.mail'].create({
                    'subject': 'Welcome to Manager Solutions - Your Trial is Ready!',
                    'email_from': self.env.company.email or 'noreply@msolutions-eg.com',
                    'email_to': s.email,
                    'body_html': body,
                })
                mail.send()
                s.message_post(body=_('Database provisioned. Welcome email sent.'))
                self.env.cr.commit()
            except Exception as e:
                self.env.cr.rollback()
                _logger.warning('Welcome email failed for sub %s: %s', s.name, e)
                try:
                    s.message_post(body=_('DB provisioned but welcome email failed.'))
                    self.env.cr.commit()
                except Exception:
                    self.env.cr.rollback()

    def action_activate(self):
        for s in self:
            s.state = 'active'
            s._set_next_invoice_date()
            s.message_post(body=_('Subscription activated.'))

    def action_cancel(self):
        for s in self:
            s.state = 'cancelled'
            s.date_end = date.today()
            s._send_mail('ms_saas_manager.email_template_cancelled')
            s.message_post(body=_('Subscription cancelled.'))

    def action_pause(self):
        self.write({'state': 'paused'})

    def action_reactivate(self):
        for s in self:
            s.state = 'active'
            s._set_next_invoice_date()

    def action_view_invoices(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Invoices'),
            'res_model': 'ms.invoice',
            'view_mode': 'list,form',
            'domain': [('subscription_id', '=', self.id)],
        }

    def action_open_database(self):
        """Owner clicks → opens customer Odoo as admin (auto-login)."""
        self.ensure_one()
        if not self.db_id:
            return {'type': 'ir.actions.client', 'tag': 'display_notification',
                    'params': {'title': 'No Database', 'message': 'Database not provisioned yet.',
                               'type': 'warning'}}
        return self.db_id.action_open_as_admin()

    def action_change_plan(self):
        return {
            'name': _('Change Plan'),
            'type': 'ir.actions.act_window',
            'res_model': 'ms.change.plan',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_subscription_id': self.id,
                        'default_current_template_id': self.template_id.id},
        }

    def action_create_invoice(self):
        self.ensure_one()
        inv = self.env['ms.invoice'].create({
            'subscription_id': self.id,
            'partner_id': self.partner_id.id,
            'template_id': self.template_id.id,
            'billing_cycle': self.billing_cycle,
            'amount': self.total_amount,
            'due_date': date.today() + timedelta(days=7),
        })
        self._set_next_invoice_date()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ms.invoice',
            'res_id': inv.id,
            'view_mode': 'form',
        }

    # ── DB Provisioning ─────────────────────────────────────────────

    def _provision_database(self):
        """Create a new Odoo database for this customer."""
        self.ensure_one()
        if self.db_id:
            return  # already provisioned

        # Use subdomain from signup form, or auto-generate
        subdomain = self.subdomain
        if not subdomain:
            base = self.company_name or self.partner_id.name or 'client'
            subdomain = re.sub(r'[^a-z0-9]', '', base.lower())[:20] or 'client'
            self.subdomain = subdomain

        db_name = 'ms_' + re.sub(r'[^a-z0-9]', '_', subdomain.lower())

        wizard = self.env['ms.provision.wizard'].create({
            'subscription_id': self.id,
            'template_id': self.template_id.id,
            'db_name': db_name,
            'subdomain': subdomain,
            'admin_email': self.email or f'admin@{subdomain}.msolutions-eg.com',
        })
        wizard.action_provision()

    # ── Invoice scheduling ──────────────────────────────────────────

    def _set_next_invoice_date(self):
        today = date.today()
        if self.billing_cycle == 'monthly':
            self.date_next_invoice = today + relativedelta(months=1)
        else:
            self.date_next_invoice = today + relativedelta(years=1)

    # ── Cron jobs ───────────────────────────────────────────────────

    @api.model
    def _cron_check_trials(self):
        today = date.today()

        # ── 3-day reminder ──
        reminder_subs = self.search([
            ('state', '=', 'trial'),
            ('trial_end', '=', today + timedelta(days=3)),
        ])
        for s in reminder_subs:
            s._send_mail('ms_saas_manager.email_template_trial_ending')
            s.message_post(body=_('Trial ending reminder sent (3 days left).'))

        # ── Trial expired → generate invoice + suspend DB ──
        expired_subs = self.search([
            ('state', '=', 'trial'),
            ('trial_end', '<=', today),
        ])
        for s in expired_subs:
            s.state = 'expired'
            s.date_end = today

            # Auto-generate invoice
            try:
                inv = self.env['ms.invoice'].create({
                    'subscription_id': s.id,
                    'partner_id': s.partner_id.id,
                    'template_id': s.template_id.id,
                    'billing_cycle': s.billing_cycle,
                    'amount': s.total_amount,
                    'due_date': today + timedelta(days=7),
                })
                inv.action_send()
                s.message_post(body=_(
                    'Trial expired. Invoice %s auto-generated and sent.'
                ) % inv.name)
            except Exception as e:
                _logger.error('Invoice creation failed for %s: %s', s.name, e)
                s.message_post(body=_('Trial expired. Invoice creation failed: %s') % e)

            # Suspend the database
            if s.db_id and s.db_id.state == 'ready':
                s.db_id.action_suspend()
                s.message_post(body=_('Database suspended — awaiting payment.'))

            # Send trial ended email
            s._send_mail('ms_saas_manager.email_template_trial_ended')

    @api.model
    def _cron_auto_renew(self):
        today = date.today()
        for s in self.search([('state', '=', 'active'),
                               ('date_next_invoice', '<=', today)]):
            s.action_create_invoice()

    @api.model
    def _cron_cleanup_expired(self):
        """Delete databases 30 days after expiry with no payment."""
        today = date.today()
        cutoff = today - timedelta(days=30)
        expired_subs = self.search([
            ('state', '=', 'expired'),
            ('date_end', '<=', cutoff),
        ])
        for s in expired_subs:
            if s.db_id and s.db_id.state in ('suspended', 'error'):
                db_name = s.db_name
                try:
                    s.db_id.action_delete_database()
                    s.state = 'cancelled'
                    s.message_post(body=_(
                        'Database %s deleted after 30 days without payment.'
                    ) % db_name)
                except Exception as e:
                    _logger.error('DB cleanup failed for %s: %s', s.name, e)

    # ── Module Sync ────────────────────────────────────────────────

    def action_sync_modules(self):
        """Install missing plan modules on the customer database."""
        import subprocess
        self.ensure_one()
        if not self.db_id or self.db_id.state != 'ready':
            return {'type': 'ir.actions.client', 'tag': 'display_notification',
                    'params': {'title': 'Cannot Sync', 'message': 'Database not ready.',
                               'type': 'warning'}}
        script = '/opt/odoo/custom_addons/ms_saas_manager/scripts/sync_modules.py'
        log_file = open('/var/log/odoo/sync_modules.log', 'a')
        subprocess.Popen(
            ['/opt/odoo/venv/bin/python3', script, self.env.cr.dbname, str(self.id)],
            stdout=log_file, stderr=subprocess.STDOUT, close_fds=True
        )
        self.message_post(body=_('Module sync started in background...'))
        return {'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {'title': 'Sync Started',
                           'message': 'Module sync is running in background. Check chatter for results.',
                           'type': 'info'}}

    # ── Mail helpers ────────────────────────────────────────────────

    def _send_mail(self, xml_id):
        tmpl = self.env.ref(xml_id, raise_if_not_found=False)
        if tmpl:
            tmpl.send_mail(self.id, force_send=True)

    def _notify_admin(self):
        tmpl = self.env.ref('ms_saas_manager.email_template_admin_signup',
                            raise_if_not_found=False)
        if tmpl:
            tmpl.send_mail(self.id, force_send=True)
